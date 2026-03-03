/**
 * StockMessageBubble — renders a single message in the Market Intelligence chat.
 * Handles: user messages, streaming stock analysis, text/error responses.
 */
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { StockArticle, BotStockStreamingMessage, StockMessage } from '../../types'
import styles from './StockMessageBubble.module.css'

// Market chart / trend icon for the bot avatar
const MarketBotIcon = () => (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" aria-hidden="true">
    <polyline
      points="3,17 8,11 13,15 21,5"
      stroke="#4ade80"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <polyline
      points="15,5 21,5 21,11"
      stroke="#4ade80"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

function StockArticleLinks({ articles }: { articles: StockArticle[] }) {
  if (!articles.length) return null
  return (
    <div className={styles.sources}>
      <p className={styles.sourcesHeading}>📎 Sources</p>
      <ul className={styles.sourcesList}>
        {articles.map((a, i) => (
          <li key={i}>
            <a href={a.link} target="_blank" rel="noopener noreferrer">
              {a.title}
            </a>
            {a.tickers && <span className={styles.tickers}> [{a.tickers}]</span>}
            {a.sentiment && (
              <span
                className={`${styles.sentiment} ${
                  a.sentiment.toLowerCase().includes('bullish')
                    ? styles.bullish
                    : a.sentiment.toLowerCase().includes('bearish')
                    ? styles.bearish
                    : styles.neutral
                }`}
              >
                {a.sentiment}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function StockStreamingBubble({ message }: { message: BotStockStreamingMessage }) {
  const showCursor = !message.isComplete && !message.hasError

  return (
    <div className={`${styles.row} ${styles.rowBot}`}>
      <div className={styles.avatar}>
        <MarketBotIcon />
      </div>
      <div className={`${styles.bubble} ${styles.bubbleBot} ${styles.bubbleStreaming}`}>
        {/* Loading spinner */}
        {!message.text && !message.isComplete && !message.hasError && (
          <div className={styles.thinkingDots}>
            <span /><span /><span />
          </div>
        )}

        {message.text && (
          <div className={styles.streamText}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
            {showCursor && <span className={styles.cursor} aria-hidden="true" />}
          </div>
        )}

        {message.hasError && (
          <p className={styles.errorText}>
            ⚠️ {message.errorText || 'Analysis failed.'}
          </p>
        )}

        {message.isComplete && !message.hasError && (
          <StockArticleLinks articles={message.articles} />
        )}
      </div>
    </div>
  )
}

interface Props {
  message: StockMessage
}

export default function StockMessageBubble({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className={`${styles.row} ${styles.rowUser}`}>
        <div className={`${styles.bubble} ${styles.bubbleUser}`}>{message.content}</div>
      </div>
    )
  }

  if (message.type === 'stock_streaming') {
    return <StockStreamingBubble message={message} />
  }

  if (message.type === 'text') {
    return (
      <div className={`${styles.row} ${styles.rowBot}`}>
        <div className={styles.avatar}><MarketBotIcon /></div>
        <div className={`${styles.bubble} ${styles.bubbleBot}`}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      </div>
    )
  }

  if (message.type === 'error') {
    return (
      <div className={`${styles.row} ${styles.rowBot}`}>
        <div className={styles.avatar}>⚠️</div>
        <div className={`${styles.bubble} ${styles.bubbleBot} ${styles.bubbleError}`}>
          {message.content}
        </div>
      </div>
    )
  }

  return null
}
