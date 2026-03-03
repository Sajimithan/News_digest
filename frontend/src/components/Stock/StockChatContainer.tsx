import React, { useEffect, useRef } from 'react'
import { useStockStore } from '../../store/stockStore'
import StockMessageBubble from './StockMessageBubble'
import StockInput from './StockInput'
import styles from './StockChatContainer.module.css'

const EmptyState: React.FC = () => (
  <div className={styles.empty}>
    <div className={styles.emptyIcon}>
      <svg viewBox="0 0 48 48" width="48" height="48" fill="none" aria-hidden="true">
        <polyline points="4,38 16,22 26,32 48,8" stroke="oklch(0.55 0.14 145)" strokeWidth="3"
          strokeLinecap="round" strokeLinejoin="round" />
        <polyline points="34,8 48,8 48,22" stroke="oklch(0.55 0.14 145)" strokeWidth="3"
          strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
    <p className={styles.emptyTitle}>Market Intelligence</p>
    <p className={styles.emptyHint}>
      Ask about today's market, pick a past date, or type "analyze YYYY-MM-DD" to get a full summary with trend predictions.
    </p>
    <div className={styles.examples}>
      <span>analyze today</span>
      <span>What happened yesterday?</span>
      <span>analyze 2025-01-20</span>
    </div>
  </div>
)

const StockChatContainer: React.FC = () => {
  const { messages } = useStockStore()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className={styles.container}>
      <div className={styles.messages}>
        {messages.length === 0
          ? <EmptyState />
          : messages.map(msg => (
              <StockMessageBubble key={msg.id} message={msg} />
            ))
        }
        <div ref={bottomRef} />
      </div>
      <StockInput />
    </div>
  )
}

export default StockChatContainer
