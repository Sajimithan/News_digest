import React, { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { useStockStore } from '../../store/stockStore'
import styles from './StockInput.module.css'

// ── Calendar helpers (same as ChatInput) ────────────────────────────────────
const PAD = (n: number) => String(n).padStart(2, '0')
const toISO = (y: number, m: number, d: number) => `${y}-${PAD(m + 1)}-${PAD(d)}`
const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
]
const DAYS = ['Su','Mo','Tu','We','Th','Fr','Sa']

interface CalendarPickerProps { onPick: (iso: string) => void; onClose: () => void }

const CalendarPicker: React.FC<CalendarPickerProps> = ({ onPick, onClose }) => {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [onClose])

  const prevMonth = () => {
    if (month === 0) { setMonth(11); setYear(y => y - 1) }
    else setMonth(m => m - 1)
  }
  const nextMonth = () => {
    const ny = month === 11 ? year + 1 : year
    const nm = month === 11 ? 0 : month + 1
    if (ny > today.getFullYear() || (ny === today.getFullYear() && nm > today.getMonth())) return
    setMonth(nm)
    if (month === 11) setYear(y => y + 1)
  }

  const firstDow = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (number | null)[] = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]
  while (cells.length % 7 !== 0) cells.push(null)

  const isToday  = (d: number) => d === today.getDate() && month === today.getMonth() && year === today.getFullYear()
  const isFuture = (d: number) => {
    const dt = new Date(year, month, d); dt.setHours(0,0,0,0)
    const t  = new Date();               t.setHours(0,0,0,0)
    return dt > t
  }
  const isAtFutureMonth =
    year > today.getFullYear() ||
    (year === today.getFullYear() && month > today.getMonth())

  return (
    <div ref={ref} className={styles.calendar}>
      <div className={styles.calHeader}>
        <button className={styles.calNav} onClick={prevMonth} aria-label="Previous month">‹</button>
        <span className={styles.calTitle}>{MONTHS[month]} {year}</span>
        <button className={styles.calNav} onClick={nextMonth} disabled={isAtFutureMonth} aria-label="Next month">›</button>
      </div>
      <div className={styles.calGrid}>
        {DAYS.map(d => <span key={d} className={styles.calDayLabel}>{d}</span>)}
        {cells.map((d, i) => {
          if (d === null) return <span key={`e${i}`} />
          const disabled = isFuture(d)
          return (
            <button
              key={i}
              className={[styles.calDay, isToday(d) ? styles.calToday : '', disabled ? styles.calDisabled : ''].join(' ')}
              disabled={disabled}
              onClick={() => { onPick(toISO(year, month, d)); onClose() }}
            >{d}</button>
          )
        })}
      </div>
    </div>
  )
}

// ── Quick-prompt chips ───────────────────────────────────────────────────────
function todayISO() {
  const t = new Date()
  return `${t.getFullYear()}-${PAD(t.getMonth() + 1)}-${PAD(t.getDate())}`
}
function yesterdayISO() {
  const t = new Date(); t.setDate(t.getDate() - 1)
  return `${t.getFullYear()}-${PAD(t.getMonth() + 1)}-${PAD(t.getDate())}`
}

// ── CalendarIcon ─────────────────────────────────────────────────────────────
const CalendarIcon = () => (
  <svg viewBox="0 0 20 20" width="15" height="15" fill="none" aria-hidden="true"
       stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="3" width="16" height="15" rx="2" />
    <line x1="6" y1="1" x2="6" y2="5" />
    <line x1="14" y1="1" x2="14" y2="5" />
    <line x1="2" y1="8" x2="18" y2="8" />
  </svg>
)

// ── SendIcon ─────────────────────────────────────────────────────────────────
const SendIcon = () => (
  <svg viewBox="0 0 20 20" width="15" height="15" fill="currentColor" aria-hidden="true">
    <path d="M2 2l16 8-16 8V12l10-2L2 8V2z" />
  </svg>
)

// ── StockInput ───────────────────────────────────────────────────────────────
const StockInput: React.FC = () => {
  const { sendMessage, isBusy } = useStockStore()
  const [text, setText] = useState('')
  const [showCal, setShowCal] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const submit = (overrideText?: string) => {
    const trimmed = (overrideText ?? text).trim()
    if (!trimmed || isBusy) return
    sendMessage(trimmed)
    setText('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
  }

  const handleInput = () => {
    const el = textareaRef.current; if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 140) + 'px'
  }

  const handleDatePick = (iso: string) => {
    setShowCal(false)
    const cmd = `analyze ${iso}`
    setText(cmd)
    setTimeout(() => submit(cmd), 0)
  }

  const handleQuick = (iso: string) => {
    const cmd = `analyze ${iso}`
    submit(cmd)
  }

  return (
    <div className={styles.wrapper}>
      {showCal && <CalendarPicker onPick={handleDatePick} onClose={() => setShowCal(false)} />}

      <div className={styles.quickChips}>
        <button className={styles.chip} onClick={() => handleQuick(todayISO())}   disabled={isBusy}>Today</button>
        <button className={styles.chip} onClick={() => handleQuick(yesterdayISO())} disabled={isBusy}>Yesterday</button>
        <button className={styles.chip} onClick={() => setShowCal(true)} disabled={isBusy}>
          <CalendarIcon /> Pick date
        </button>
      </div>

      <div className={styles.inputRow}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          value={text}
          onChange={e => setText(e.target.value)}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          placeholder='Ask about a date, e.g. "analyze 2025-01-20" or type a question…'
          rows={1}
          disabled={isBusy}
        />
        <button
          className={styles.sendBtn}
          onClick={() => submit()}
          disabled={!text.trim() || isBusy}
          aria-label="Send"
        >
          {isBusy ? <span className={styles.spinner} /> : <SendIcon />}
        </button>
      </div>
    </div>
  )
}

export default StockInput
