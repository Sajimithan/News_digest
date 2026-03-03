/**
 * useSSE — manages the per-client EventSource connection.
 *
 * Registers named-event listeners for every SSE event type the backend sends.
 * Handlers are passed via the callbacks object; they are stable because the
 * hook uses a ref internally, so callers don't need to memoize them.
 *
 * Events handled:
 *   status           — job queued, running, etc.
 *   stream_start     — LLM streaming summary is about to begin
 *   stream_token     — one markdown token from the LLM
 *   stream_end       — streaming complete; carries article links
 *   result           — plain news list / text result (non-streaming path)
 *   provider_started — a news provider started fetching
 *   provider_done    — a news provider finished
 *   provider_error   — a news provider failed
 *   job_done         — aggregation job complete
 */

import { useCallback, useEffect, useRef } from 'react'
import type {
  ProviderEventPayload,
  ResultPayload,
  StreamEndPayload,
  StreamStartPayload,
} from '../types'

export interface SSECallbacks {
  onStatus?: (text: string) => void
  onStreamStart?: (data: StreamStartPayload) => void
  onStreamToken?: (token: string) => void
  onStreamEnd?: (data: StreamEndPayload) => void
  onResult?: (data: ResultPayload) => void
  onProviderEvent?: (type: string, data: ProviderEventPayload) => void
  onJobDone?: (data: unknown) => void
  onConnected?: () => void
  onDisconnected?: () => void
}

export function useSSE(clientId: string, callbacks: SSECallbacks): void {
  // Store callbacks in a ref so we never need to re-create the EventSource
  // when the callback functions change reference between renders.
  const cbRef = useRef<SSECallbacks>(callbacks)
  cbRef.current = callbacks

  const parse = useCallback(<T>(raw: string): T | null => {
    try {
      return JSON.parse(raw) as T
    } catch {
      return null
    }
  }, [])

  useEffect(() => {
    if (!clientId) return

    const es = new EventSource(`/events?client_id=${encodeURIComponent(clientId)}`)

    es.addEventListener('status', (e: MessageEvent) => {
      cbRef.current.onStatus?.(e.data as string)
    })

    es.addEventListener('stream_start', (e: MessageEvent) => {
      const data = parse<StreamStartPayload>(e.data)
      if (data) cbRef.current.onStreamStart?.(data)
    })

    es.addEventListener('stream_token', (e: MessageEvent) => {
      // Tokens are raw strings (no JSON wrapper) for maximum throughput
      cbRef.current.onStreamToken?.(e.data as string)
    })

    es.addEventListener('stream_end', (e: MessageEvent) => {
      const data = parse<StreamEndPayload>(e.data)
      if (data) cbRef.current.onStreamEnd?.(data)
    })

    es.addEventListener('result', (e: MessageEvent) => {
      const data = parse<ResultPayload>(e.data)
      if (data) cbRef.current.onResult?.(data)
    })

    es.addEventListener('provider_started', (e: MessageEvent) => {
      const data = parse<ProviderEventPayload>(e.data)
      if (data) cbRef.current.onProviderEvent?.('started', data)
    })

    es.addEventListener('provider_done', (e: MessageEvent) => {
      const data = parse<ProviderEventPayload>(e.data)
      if (data) cbRef.current.onProviderEvent?.('done', data)
    })

    es.addEventListener('provider_error', (e: MessageEvent) => {
      const data = parse<ProviderEventPayload>(e.data)
      if (data) cbRef.current.onProviderEvent?.('error', data)
    })

    es.addEventListener('job_done', (e: MessageEvent) => {
      const data = parse<unknown>(e.data)
      cbRef.current.onJobDone?.(data)
    })

    es.onopen = () => cbRef.current.onConnected?.()
    es.onerror = () => cbRef.current.onDisconnected?.()

    return () => {
      es.close()
    }
  }, [clientId, parse])
}
