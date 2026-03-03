/** Shared TypeScript types for the Tech News Chatbot frontend. */

// ── News ─────────────────────────────────────────────────────────────────────
interface NewsArticle {
  source: string
  title: string
  link: string
}

export type { NewsArticle }

/** A single classified article returned by the Topic Classifier. */
export interface ClassifiedArticle {
  title:      string
  source:     string
  link:       string
  topic:      string
  confidence: number
  reason:     string
}

// ── Messages ─────────────────────────────────────────────────────────────────

/** A message sent by the user. */
export interface UserMessage {
  id: string
  role: 'user'
  content: string
  timestamp: Date
}

/** A plain-text response from the bot (or a help message). */
export interface BotTextMessage {
  id: string
  role: 'bot'
  type: 'text'
  content: string
  timestamp: Date
}

/** A plain list of news articles (no LLM). */
export interface BotNewsMessage {
  id: string
  role: 'bot'
  type: 'news'
  date: string
  items: [string, string, string][]   // [source, title, link]
  timestamp: Date
}

/**
 * A streaming LLM summary.
 * Tokens accumulate in ``text``; articles arrive with ``stream_end``.
 */
export interface BotStreamingMessage {
  id: string
  role: 'bot'
  type: 'streaming'
  jobId: string
  date: string
  text: string          // accumulated markdown text
  articles: NewsArticle[]
  isComplete: boolean
  hasError: boolean
  errorText?: string    // actual error message from backend
  timestamp: Date
}

export interface BotErrorMessage {
  id: string
  role: 'bot'
  type: 'error'
  content: string
  timestamp: Date
}

export interface BotClassificationMessage {
  id: string
  role: 'bot'
  type: 'classification'
  date: string
  classified: ClassifiedArticle[]
  topicCounts: Record<string, number>
  timestamp: Date
}

// ── Stock / Market Intelligence types ────────────────────────────────────────

export interface StockArticle {
  source: string
  title: string
  link: string
  tickers?: string
  sentiment?: string
}

/**
 * A streaming stock market analysis response.
 * The LLM streams a two-section markdown:
 *   1. Market Summary
 *   2. Future Trend Prediction
 */
export interface BotStockStreamingMessage {
  id: string
  role: 'bot'
  type: 'stock_streaming'
  jobId: string
  date: string
  text: string
  articles: StockArticle[]
  isComplete: boolean
  hasError: boolean
  errorText?: string
  timestamp: Date
}

export type StockMessage =
  | UserMessage
  | BotTextMessage
  | BotErrorMessage
  | BotStockStreamingMessage

export type Message =
  | UserMessage
  | BotTextMessage
  | BotNewsMessage
  | BotStreamingMessage
  | BotErrorMessage
  | BotClassificationMessage

// ── SSE event payloads ────────────────────────────────────────────────────────

export interface StreamStartPayload {
  job_id: string
  date: string
}

export interface StreamEndPayload {
  job_id: string
  articles: NewsArticle[] | StockArticle[]
  error?: string
}

export interface StatusPayload {
  job_id?: string
  message?: string
}

export interface ProviderEventPayload {
  job_id: string
  provider: string
  count?: number
  error?: string
}

export interface ResultPayload {
  job_id: string
  payload: {
    type: 'text' | 'news' | 'stream_summary' | 'classification' | 'stock_news' | 'stock_stream_summary'
    content?: string
    date?: string
    items?: [string, string, string][]
    articles?: NewsArticle[]
    classified?: ClassifiedArticle[]
    topic_counts?: Record<string, number>
  }
}

// ── Status log ───────────────────────────────────────────────────────────────

export interface StatusEntry {
  id: string
  time: string
  text: string
  level: 'info' | 'success' | 'error' | 'warn'
}
