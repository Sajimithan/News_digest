/**
 * useChat — central state for the chat UI.
 *
 * Manages:
 *   • clientId  (stable UUID, generated once per page load)
 *   • messages  (the full conversation history)
 *   • isBusy    (true while an unfinished streaming or job is in flight)
 *   • statusLog (debug/info SSE events shown in the status panel)
 *
 * Wires the useSSE hook internally, so consumers only need to call
 * ``sendMessage(text)`` and render ``messages``.
 */

import { useCallback, useRef, useState } from 'react'
import { postChat } from '../services/api'
import type {
  BotStreamingMessage,
  BotClassificationMessage,
  Message,
  ProviderEventPayload,
  ResultPayload,
  StatusEntry,
  StreamEndPayload,
  StreamStartPayload,
} from '../types'
import { useSSE } from './useSSE'

/** Generate or load a stable client ID for this browser session. */
function getClientId(): string {
  const key = 'techNewsChatClientId'
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

/** Matches messages that have a real news / date intent. */
const NEWS_INTENT_RE =
  /\b(\d{4}-\d{2}-\d{2}|today|yesterday|update|news|summarize|show|fetch|article|headline|classif|categoris|categoriz|topic)\b/i

const HELP_TEXT = `I can help you explore tech news! Try:
- **today** — summarise today's tech news
- **yesterday** — summarise yesterday's tech news
- **2026-02-20** — summarise a specific date
- **update news** — fetch fresh articles for today
- **today update** — fetch + summarise today`

export interface UseChatReturn {
  clientId: string
  messages: Message[]
  isBusy: boolean
  statusLog: StatusEntry[]
  sendMessage: (text: string) => Promise<void>
  cancelJob: () => void
  clearMessages: () => void
}

export function useChat(): UseChatReturn {
  const clientId = useRef(getClientId()).current
  const [messages, setMessages] = useState<Message[]>([])
  const [isBusy, setIsBusy] = useState(false)
  const [statusLog, setStatusLog] = useState<StatusEntry[]>([])

  // Track which job_id maps to which streaming message id, so we can
  // update the right bubble when tokens arrive.
  const jobToMsgId = useRef<Map<string, string>>(new Map())

  // ── Status log helpers ──────────────────────────────────────────────────
  const addLog = useCallback((text: string, level: StatusEntry['level'] = 'info') => {
    setStatusLog(prev => [
      ...prev.slice(-99),   // keep last 100 entries
      { id: uid(), time: fmtTime(now()), text, level },
    ])
  }, [])

  // ── Message helpers ─────────────────────────────────────────────────────
  const addMessage = useCallback((msg: Message) => {
    setMessages(prev => [...prev, msg])
  }, [])

  const updateStreamingMessage = useCallback(
    (jobId: string, updater: (msg: BotStreamingMessage) => BotStreamingMessage) => {
      const msgId = jobToMsgId.current.get(jobId)
      if (!msgId) return
      setMessages(prev =>
        prev.map(m =>
          m.id === msgId && m.role === 'bot' && m.type === 'streaming'
            ? updater(m as BotStreamingMessage)
            : m
        )
      )
    },
    []
  )

  // ── SSE handlers ────────────────────────────────────────────────────────

  const handleStreamStart = useCallback(
    (data: StreamStartPayload) => {
      addLog(`Stream started: ${data.date}`, 'info')
      const msgId = uid()
      jobToMsgId.current.set(data.job_id, msgId)

      const msg: BotStreamingMessage = {
        id: msgId,
        role: 'bot',
        type: 'streaming',
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
    },
    [addMessage, addLog]
  )

  const handleStreamToken = useCallback(
    (token: string) => {
      // Find the latest in-progress streaming message (LIFO order)
      setMessages(prev => {
        const idx = [...prev].reverse().findIndex(
          m => m.role === 'bot' && m.type === 'streaming' && !(m as BotStreamingMessage).isComplete
        )
        if (idx === -1) return prev
        const realIdx = prev.length - 1 - idx
        const updated = [...prev]
        const msg = { ...(updated[realIdx] as BotStreamingMessage) }
        msg.text += token
        updated[realIdx] = msg
        return updated
      })
    },
    []
  )

  const handleStreamEnd = useCallback(
    (data: StreamEndPayload) => {
      const hasError = Boolean(data.error)
      addLog(
        hasError ? `Stream error: ${data.error}` : `Stream complete — ${data.articles.length} links`,
        hasError ? 'error' : 'success'
      )
      updateStreamingMessage(data.job_id, msg => ({
        ...msg,
        articles: data.articles,
        isComplete: true,
        hasError,
        errorText: data.error,
      }))
      setIsBusy(false)
    },
    [addLog, updateStreamingMessage]
  )

  const handleResult = useCallback(
    (data: ResultPayload) => {
      const p = data.payload
      if (p.type === 'text') {
        addMessage({ id: uid(), role: 'bot', type: 'text', content: p.content ?? '', timestamp: now() })
      } else if (p.type === 'news') {
        addMessage({
          id: uid(),
          role: 'bot',
          type: 'news',
          date: p.date ?? '',
          items: p.items ?? [],
          timestamp: now(),
        })
      } else if (p.type === 'classification') {
        const msg: BotClassificationMessage = {
          id: uid(),
          role: 'bot',
          type: 'classification',
          date: p.date ?? '',
          classified: p.classified ?? [],
          topicCounts: p.topic_counts ?? {},
          timestamp: now(),
        }
        addMessage(msg)
      }
      setIsBusy(false)
    },
    [addMessage]
  )

  const handleStatus = useCallback(
    (text: string) => addLog(text, 'info'),
    [addLog]
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
    onStatus: handleStatus,
    onStreamStart: handleStreamStart,
    onStreamToken: handleStreamToken,
    onStreamEnd: handleStreamEnd,
    onResult: handleResult,
    onProviderEvent: handleProviderEvent,
    onConnected: () => addLog('SSE connected', 'success'),
    onDisconnected: () => addLog('SSE disconnected', 'warn'),
  })

  // ── Public actions ──────────────────────────────────────────────────────

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isBusy) return

      const trimmed = text.trim()
      addMessage({ id: uid(), role: 'user', content: trimmed, timestamp: now() })

      // ── Client-side pre-screen ─────────────────────────────────────────
      // If the message has no news intent, answer locally — no API call.
      if (!NEWS_INTENT_RE.test(trimmed)) {
        addMessage({ id: uid(), role: 'bot', type: 'text', content: HELP_TEXT, timestamp: now() })
        return
      }

      setIsBusy(true)

      try {
        const { job_id } = await postChat(trimmed, clientId)
        addLog(`Job created: ${job_id}`, 'info')
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        addMessage({ id: uid(), role: 'bot', type: 'error', content: msg, timestamp: now() })
        addLog(`Request failed: ${msg}`, 'error')
        setIsBusy(false)
      }
    },
    [clientId, isBusy, addMessage, addLog]
  )

  /** Immediately abort the current busy state (client-side cancel). */
  const cancelJob = useCallback(() => {
    // Mark any in-progress streaming message as cancelled
    setMessages(prev =>
      prev.map(m => {
        if (m.role === 'bot' && m.type === 'streaming' && !(m as BotStreamingMessage).isComplete) {
          return {
            ...(m as BotStreamingMessage),
            isComplete: true,
            hasError: true,
            errorText: 'Cancelled.',
          } as BotStreamingMessage
        }
        return m
      })
    )
    setIsBusy(false)
    addLog('Job cancelled by user.', 'warn')
  }, [addLog])

  const clearMessages = useCallback(() => setMessages([]), [])

  return { clientId, messages, isBusy, statusLog, sendMessage, cancelJob, clearMessages }
}
