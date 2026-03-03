/**
 * useStockChat — state and SSE wiring for the Market Intelligence chat.
 *
 * Mirrors useChat but:
 *   • Uses /stock/chat endpoint
 *   • Tracks BotStockStreamingMessage instead of BotStreamingMessage
 *   • Uses a separate sessionStorage key so client IDs don't collide
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { postStockChat } from '../services/api'
import type {
  BotStockStreamingMessage,
  BotErrorMessage,
  ProviderEventPayload,
  StatusEntry,
  StreamEndPayload,
  StreamStartPayload,
  StockArticle,
  StockMessage,
  UserMessage,
} from '../types'
import { useSSE } from './useSSE'

function getStockClientId(): string {
  const key = 'stockMarketChatClientId'
  const stored = sessionStorage.getItem(key)
  if (stored) return stored
  const id =
    typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Date.now().toString(36)
  sessionStorage.setItem(key, id)
  return id
}

function uid(): string {
  return Math.random().toString(36).slice(2)
}

function now(): Date {
  return new Date()
}

function fmtTime(d: Date): string {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export interface UseStockChatReturn {
  clientId: string
  messages: StockMessage[]
  isBusy: boolean
  statusLog: StatusEntry[]
  sendMessage: (text: string) => Promise<void>
  cancelJob: () => void
  clearMessages: () => void
}

export function useStockChat(): UseStockChatReturn {
  const clientId = useRef(getStockClientId()).current
  const [messages, setMessages] = useState<StockMessage[]>([])
  const [isBusy, setIsBusy] = useState(false)
  const [statusLog, setStatusLog] = useState<StatusEntry[]>([])
  const jobToMsgId = useRef<Map<string, string>>(new Map())
  const tokenBuffer = useRef<string>('')
  const flushTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const flushTokenBuffer = useCallback(() => {
    if (!tokenBuffer.current) return
    const batch = tokenBuffer.current
    tokenBuffer.current = ''
    setMessages(prev => {
      const idx = [...prev].reverse().findIndex(
        m => m.role === 'bot' && m.type === 'stock_streaming' && !(m as BotStockStreamingMessage).isComplete
      )
      if (idx === -1) return prev
      const realIdx = prev.length - 1 - idx
      const updated = [...prev]
      const msg = { ...(updated[realIdx] as BotStockStreamingMessage) }
      msg.text += batch
      updated[realIdx] = msg
      return updated
    })
  }, [])

  const addLog = useCallback((text: string, level: StatusEntry['level'] = 'info') => {
    setStatusLog(prev => [
      ...prev.slice(-99),
      { id: uid(), time: fmtTime(now()), text, level },
    ])
  }, [])

  const addMessage = useCallback((msg: StockMessage) => {
    setMessages(prev => [...prev, msg])
  }, [])

  const updateStreamingMessage = useCallback(
    (jobId: string, updater: (m: BotStockStreamingMessage) => BotStockStreamingMessage) => {
      const msgId = jobToMsgId.current.get(jobId)
      if (!msgId) return
      setMessages(prev =>
        prev.map(m =>
          m.id === msgId && m.role === 'bot' && m.type === 'stock_streaming'
            ? updater(m as BotStockStreamingMessage)
            : m
        )
      )
    },
    []
  )

  // ── SSE handlers ──────────────────────────────────────────────────────────

  const handleStreamStart = useCallback(
    (data: StreamStartPayload) => {
      addLog(`Market analysis started: ${data.date}`, 'info')
      const msgId = uid()
      jobToMsgId.current.set(data.job_id, msgId)
      const msg: BotStockStreamingMessage = {
        id: msgId,
        role: 'bot',
        type: 'stock_streaming',
        jobId: data.job_id,
        date: data.date,
        text: '',
        articles: [],
        isComplete: false,
        hasError: false,
        timestamp: now(),
      }
      addMessage(msg)
      setIsBusy(true)
      // Start the token-flush interval so tokens are batched into state updates
      tokenBuffer.current = ''
      if (flushTimerRef.current) clearInterval(flushTimerRef.current)
      flushTimerRef.current = setInterval(flushTokenBuffer, 50)
    },
    [addMessage, addLog, flushTokenBuffer]
  )

  const handleStreamToken = useCallback((token: string) => {
    // Accumulate into buffer; the flush interval will commit to state in batches
    tokenBuffer.current += token
  }, [])

  const handleStreamEnd = useCallback(
    (data: StreamEndPayload) => {
      // Stop the interval and flush any remaining buffered tokens
      if (flushTimerRef.current) {
        clearInterval(flushTimerRef.current)
        flushTimerRef.current = null
      }
      flushTokenBuffer()
      const hasError = Boolean(data.error)
      addLog(
        hasError ? `Analysis error: ${data.error}` : `Analysis complete — ${data.articles.length} sources`,
        hasError ? 'error' : 'success'
      )
      updateStreamingMessage(data.job_id, m => ({
        ...m,
        articles: data.articles as StockArticle[],
        isComplete: true,
        hasError,
        errorText: data.error,
      }))
      setIsBusy(false)
    },
    [addLog, updateStreamingMessage, flushTokenBuffer]
  )

  const handleResult = useCallback(
    (data: { job_id: string; payload: { type: string; content?: string } }) => {
      const p = data.payload
      if (p.type === 'text') {
        addMessage({ id: uid(), role: 'bot', type: 'text', content: p.content ?? '', timestamp: now() })
      }
      setIsBusy(false)
    },
    [addMessage]
  )

  const handleProviderEvent = useCallback(
    (type: string, data: ProviderEventPayload) => {
      const label =
        type === 'started'
          ? `⏳ ${data.provider} fetching…`
          : type === 'done'
          ? `✅ ${data.provider} → ${data.count ?? 0} articles`
          : `❌ ${data.provider}: ${data.error ?? 'failed'}`
      addLog(label, type === 'error' ? 'error' : type === 'done' ? 'success' : 'info')
    },
    [addLog]
  )

  useSSE(clientId, {
    onStatus: (text: string) => addLog(text, 'info'),
    onStreamStart: handleStreamStart,
    onStreamToken: handleStreamToken,
    onStreamEnd: handleStreamEnd,
    onResult: handleResult as any,
    onProviderEvent: handleProviderEvent,
    onConnected: () => addLog('Market SSE connected', 'success'),
    onDisconnected: () => addLog('Market SSE disconnected', 'warn'),
  })

  // Clear flush interval on unmount
  useEffect(() => {
    return () => {
      if (flushTimerRef.current) {
        clearInterval(flushTimerRef.current)
      }
    }
  }, [])

  // ── Public actions ────────────────────────────────────────────────────────

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isBusy) return

      const trimmed = text.trim()
      addMessage({ id: uid(), role: 'user', content: trimmed, timestamp: now() } as UserMessage)
      setIsBusy(true)

      try {
        const { job_id } = await postStockChat(trimmed, clientId)
        addLog(`Market job created: ${job_id}`, 'info')
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        addMessage({ id: uid(), role: 'bot', type: 'error', content: msg, timestamp: now() } as BotErrorMessage)
        addLog(`Request failed: ${msg}`, 'error')
        setIsBusy(false)
      }
    },
    [clientId, isBusy, addMessage, addLog]
  )

  const cancelJob = useCallback(() => {
    setMessages(prev =>
      prev.map(m => {
        if (m.role === 'bot' && m.type === 'stock_streaming' && !(m as BotStockStreamingMessage).isComplete) {
          return { ...(m as BotStockStreamingMessage), isComplete: true, hasError: true, errorText: 'Cancelled.' }
        }
        return m
      })
    )
    setIsBusy(false)
    addLog('Market analysis cancelled.', 'warn')
  }, [addLog])

  const clearMessages = useCallback(() => setMessages([]), [])

  return { clientId, messages, isBusy, statusLog, sendMessage, cancelJob, clearMessages }
}
