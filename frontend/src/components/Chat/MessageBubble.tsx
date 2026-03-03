/**
 * MessageBubble — renders a single chat message.
 *
 * Supports all message types:
 *   user           → right-aligned, plain text
 *   bot/text       → left-aligned, markdown rendered
 *   bot/news       → left-aligned, article list
 *   bot/streaming  → left-aligned, live markdown + blinking cursor + links on complete
 *   bot/error      → left-aligned, red error card
 *   bot/classification → left-aligned, topic breakdown table + article list
 */

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type {
  BotClassificationMessage,
  BotNewsMessage,
  BotStreamingMessage,
  BotTextMessage,
  ClassifiedArticle,
  Message,
  NewsArticle,
} from '../../types'
import styles from './MessageBubble.module.css'

// Speech bubble with reply arrow — used as the bot summary/streaming avatar
const BotAvatarIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    {/* Speech bubble filled */}
    <path
      fill="var(--accent)"
      d="M4 2h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6l-4 4V4a2 2 0 0 1 2-2z"
    />
    {/* Reply arrow cut-out using avatar background color */}
    <path
      fill="var(--surface-2)"
      d="M10 8l-4 4 4 4v-2.5c3.5 0 5.5 1 6.5 3.5C16 13 14 10 10 10V8z"
    />
  </svg>
)

interface Props {
  message: Message
}

function ArticleLinks({ articles }: { articles: NewsArticle[] }) {
  if (!articles.length) return null
  return (
    <div className={styles.linkSection}>
      <p className={styles.linksHeading}>📎 Sources</p>
      <ul className={styles.linkList}>
        {articles.map((a, i) => (
          <li key={i} className={styles.linkItem}>
            <span className={styles.source}>{a.source}</span>
            <a href={a.link} target="_blank" rel="noopener noreferrer" className={styles.link}>
              {a.title}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

function UserBubble({ message }: { message: Extract<Message, { role: 'user' }> }) {
  return (
    <div className={`${styles.row} ${styles.rowUser}`}>
      <div className={`${styles.bubble} ${styles.bubbleUser}`}>
        {message.content}
      </div>
    </div>
  )
}

function TextBubble({ message }: { message: BotTextMessage }) {
  return (
    <div className={`${styles.row} ${styles.rowBot}`}>
      <div className={styles.avatar}>🤖</div>
      <div className={`${styles.bubble} ${styles.bubbleBot}`}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content}
        </ReactMarkdown>
      </div>
    </div>
  )
}

function NewsBubble({ message }: { message: BotNewsMessage }) {
  return (
    <div className={`${styles.row} ${styles.rowBot}`}>
      <div className={styles.avatar}>📰</div>
      <div className={`${styles.bubble} ${styles.bubbleBot}`}>
        <p className={styles.newsDate}>News for <strong>{message.date}</strong></p>
        {message.items.length === 0 ? (
          <p className={styles.empty}>No articles found for this date.</p>
        ) : (
          <ul className={styles.linkList}>
            {message.items.map(([source, title, link], i) => (
              <li key={i} className={styles.linkItem}>
                <span className={styles.source}>{source}</span>
                <a href={link} target="_blank" rel="noopener noreferrer" className={styles.link}>
                  {title}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function StreamingBubble({ message }: { message: BotStreamingMessage }) {
  const showCursor = !message.isComplete && !message.hasError

  return (
    <div className={`${styles.row} ${styles.rowBot}`}>
      <div className={styles.avatar}><BotAvatarIcon /></div>
      <div className={`${styles.bubble} ${styles.bubbleBot} ${styles.bubbleStreaming}`}>
        {/* Loading state — show spinner before first token arrives */}
        {!message.text && !message.isComplete && !message.hasError && (
          <div className={styles.thinkingDots}>
            <span />
            <span />
            <span />
          </div>
        )}

        {/* Streaming or complete markdown */}
        {message.text && (
          <div className={styles.streamText}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.text}
            </ReactMarkdown>
            {showCursor && <span className={styles.cursor} aria-hidden="true" />}
          </div>
        )}

        {/* Error overlay */}
        {message.hasError && (
          <p className={styles.streamError}>
            ⚠️ {message.errorText || 'Summary generation failed. Try fetching news first.'}
          </p>
        )}

        {/* Article links shown after streaming is complete */}
        {message.isComplete && !message.hasError && (
          <ArticleLinks articles={message.articles} />
        )}
      </div>
    </div>
  )
}

function ErrorBubble({ message }: { message: Extract<Message, { type: 'error' }> }) {
  return (
    <div className={`${styles.row} ${styles.rowBot}`}>
      <div className={styles.avatar}>⚠️</div>
      <div className={`${styles.bubble} ${styles.bubbleError}`}>
        {message.content}
      </div>
    </div>
  )
}

// ── Topic colour map (one accent per category) ────────────────────────────
const TOPIC_COLORS: Record<string, string> = {
  AI_ML:                   '#7c3aed',
  CYBERSECURITY:           '#dc2626',
  CLOUD_DEVOPS:            '#0284c7',
  PROGRAMMING_FRAMEWORKS:  '#059669',
  MOBILE_DEVICES:          '#d97706',
  OPEN_SOURCE:             '#16a34a',
  DATA_INFRA:              '#0891b2',
  BIG_TECH_BUSINESS:       '#7c2d12',
  GAMING:                  '#9333ea',
  SCIENCE_TECH:            '#0f766e',
  OTHER:                   '#6b7280',
}

function TopicPill({ topic }: { topic: string }) {
  const color = TOPIC_COLORS[topic] ?? TOPIC_COLORS.OTHER
  return (
    <span
      className={styles.topicPill}
      style={{ background: color + '22', color, borderColor: color + '66' }}
    >
      {topic.replace(/_/g, ' ')}
    </span>
  )
}

function ClassificationBubble({ message }: { message: BotClassificationMessage }) {
  const sorted = Object.entries(message.topicCounts)
    .filter(([, c]) => c > 0)
    .sort((a, b) => b[1] - a[1])

  return (
    <div className={`${styles.row} ${styles.rowBot}`}>
      <div className={styles.avatar}>🏷️</div>
      <div className={`${styles.bubble} ${styles.bubbleBot} ${styles.bubbleClassification}`}>
        {/* Header */}
        <p className={styles.classificationTitle}>
          Topic breakdown — <strong>{message.date}</strong>
          <span className={styles.classificationCount}>{message.classified.length} articles</span>
        </p>

        {/* Topic count pills */}
        {sorted.length > 0 && (
          <div className={styles.topicCountRow}>
            {sorted.map(([topic, count]) => (
              <span key={topic} className={styles.topicCountBadge}
                style={{
                  background: (TOPIC_COLORS[topic] ?? TOPIC_COLORS.OTHER) + '22',
                  color: TOPIC_COLORS[topic] ?? TOPIC_COLORS.OTHER,
                  borderColor: (TOPIC_COLORS[topic] ?? TOPIC_COLORS.OTHER) + '66',
                }}
              >
                {topic.replace(/_/g, ' ')} {count}
              </span>
            ))}
          </div>
        )}

        {/* Per-article list */}
        <ul className={styles.classificationList}>
          {message.classified.map((art: ClassifiedArticle, i: number) => (
            <li key={i} className={styles.classificationItem}>
              <TopicPill topic={art.topic} />
              <div className={styles.classificationItemBody}>
                <a
                  href={art.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.classificationLink}
                >
                  {art.title}
                </a>
                <span className={styles.classificationMeta}>
                  {art.source} · {(art.confidence * 100).toFixed(0)}% · {art.reason}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default function MessageBubble({ message }: Props) {
  if (message.role === 'user') return <UserBubble message={message} />
  if (message.type === 'text') return <TextBubble message={message} />
  if (message.type === 'news') return <NewsBubble message={message} />
  if (message.type === 'streaming') return <StreamingBubble message={message} />
  if (message.type === 'error') return <ErrorBubble message={message} />
  if (message.type === 'classification') return <ClassificationBubble message={message} />
  return null
}
