/**
 * REST API client.
 *
 * All paths are relative so the Vite proxy (dev) and the FastAPI static server
 * (production) both work without any configuration change.
 */

export interface ChatRequest {
  message: string
  client_id: string
}

export interface ChatResponse {
  job_id: string
}

export interface UpdateRequest {
  client_id: string
}

/** POST /chat — submit a user message, get back a job_id immediately. */
export async function postChat(
  message: string,
  clientId: string
): Promise<ChatResponse> {
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, client_id: clientId } satisfies ChatRequest),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const msg = body?.error?.message ?? `HTTP ${res.status}`
    throw new Error(msg)
  }

  return res.json() as Promise<ChatResponse>
}

/** POST /update — trigger a news update for today. */
export async function postUpdate(clientId: string): Promise<ChatResponse> {
  const res = await fetch('/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: clientId } satisfies UpdateRequest),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`)
  }

  return res.json() as Promise<ChatResponse>
}

/** POST /stock/chat — submit a market/stock analysis query. */
export async function postStockChat(
  message: string,
  clientId: string
): Promise<ChatResponse> {
  const res = await fetch('/stock/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, client_id: clientId } satisfies ChatRequest),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const msg = body?.error?.message ?? `HTTP ${res.status}`
    throw new Error(msg)
  }

  return res.json() as Promise<ChatResponse>
}
