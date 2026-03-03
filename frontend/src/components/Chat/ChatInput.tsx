import React, { useState, useRef, useEffect, KeyboardEvent } from "react";
import { useChatStore } from "../../store";
import IconButton from "../common/IconButton";
import styles from "./ChatInput.module.css";

// ── tiny helpers ────────────────────────────────────────────────────────────
const PAD = (n: number) => String(n).padStart(2, "0");
const toISO = (y: number, m: number, d: number) =>
  `${y}-${PAD(m + 1)}-${PAD(d)}`;
const MONTHS = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
];
const DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

// ── CalendarPicker ───────────────────────────────────────────────────────────
interface CalendarPickerProps {
  onPick: (iso: string) => void;
  onClose: () => void;
}

const CalendarPicker: React.FC<CalendarPickerProps> = ({ onPick, onClose }) => {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  const prevMonth = () => {
    if (month === 0) { setMonth(11); setYear(y => y - 1); }
    else setMonth(m => m - 1);
  };
  const nextMonth = () => {
    const ny = month === 11 ? year + 1 : year;
    const nm = month === 11 ? 0 : month + 1;
    // Don't navigate past current month
    if (ny > today.getFullYear() || (ny === today.getFullYear() && nm > today.getMonth())) return;
    setMonth(nm); if (month === 11) setYear(y => y + 1);
  };

  // Build grid: blanks for days before the 1st, then day numbers
  const firstDow = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  // Pad to full weeks
  while (cells.length % 7 !== 0) cells.push(null);

  const isToday = (d: number) =>
    d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
  const isFuture = (d: number) => {
    const dt = new Date(year, month, d);
    dt.setHours(0,0,0,0);
    const t = new Date(); t.setHours(0,0,0,0);
    return dt > t;
  };
  const isAtFutureMonth =
    year > today.getFullYear() ||
    (year === today.getFullYear() && month > today.getMonth());

  return (
    <div ref={ref} className={styles.calendar}>
      {/* Header */}
      <div className={styles.calHeader}>
        <button className={styles.calNav} onClick={prevMonth} aria-label="Previous month">‹</button>
        <span className={styles.calTitle}>{MONTHS[month]} {year}</span>
        <button
          className={styles.calNav}
          onClick={nextMonth}
          disabled={isAtFutureMonth}
          aria-label="Next month"
        >›</button>
      </div>
      {/* Day labels */}
      <div className={styles.calGrid}>
        {DAYS.map(d => <span key={d} className={styles.calDayLabel}>{d}</span>)}
        {cells.map((d, i) => {
          if (d === null) return <span key={`e${i}`} />;
          const disabled = isFuture(d);
          return (
            <button
              key={i}
              className={[
                styles.calDay,
                isToday(d) ? styles.calToday : "",
                disabled ? styles.calDisabled : "",
              ].join(" ")}
              disabled={disabled}
              onClick={() => { onPick(toISO(year, month, d)); onClose(); }}
            >
              {d}
            </button>
          );
        })}
      </div>
    </div>
  );
};

// ── Quick-chip helpers ───────────────────────────────────────────────────────
function todayISO() {
  const t = new Date()
  return `${t.getFullYear()}-${PAD(t.getMonth() + 1)}-${PAD(t.getDate())}`
}
function yesterdayISO() {
  const t = new Date(); t.setDate(t.getDate() - 1)
  return `${t.getFullYear()}-${PAD(t.getMonth() + 1)}-${PAD(t.getDate())}`
}

// ── CalendarChipIcon ─────────────────────────────────────────────────────────
const CalendarChipIcon = () => (
  <svg viewBox="0 0 20 20" width="13" height="13" fill="none" aria-hidden="true"
       stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="3" width="16" height="15" rx="2" />
    <line x1="6" y1="1" x2="6" y2="5" />
    <line x1="14" y1="1" x2="14" y2="5" />
    <line x1="2" y1="8" x2="18" y2="8" />
  </svg>
)

// ── ClassifyIcon — hierarchy / sitemap SVG ────────────────────────────────
const ClassifyIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    width="17"
    height="17"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.7"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {/* root box */}
    <rect x="8" y="1" width="8" height="5" rx="1" />
    {/* vertical stem from root */}
    <line x1="12" y1="6" x2="12" y2="9" />
    {/* horizontal bar */}
    <line x1="5" y1="9" x2="19" y2="9" />
    {/* left stem */}
    <line x1="5" y1="9" x2="5" y2="11" />
    {/* right stem */}
    <line x1="19" y1="9" x2="19" y2="11" />
    {/* left child box */}
    <rect x="1" y="11" width="8" height="5" rx="1" />
    {/* right child box */}
    <rect x="15" y="11" width="8" height="5" rx="1" />
    {/* left-left leaf stem */}
    <line x1="3" y1="16" x2="3" y2="18" />
    {/* left-right leaf stem */}
    <line x1="7" y1="16" x2="7" y2="18" />
    {/* right-left leaf stem */}
    <line x1="17" y1="16" x2="17" y2="18" />
    {/* right-right leaf stem */}
    <line x1="21" y1="16" x2="21" y2="18" />
    {/* leaf circles */}
    <circle cx="3"  cy="20" r="1.5" />
    <circle cx="7"  cy="20" r="1.5" />
    <circle cx="17" cy="20" r="1.5" />
    <circle cx="21" cy="20" r="1.5" />
  </svg>
);

// ── ChatInput ────────────────────────────────────────────────────────────────
const ChatInput: React.FC = () => {
  const { sendMessage, isBusy } = useChatStore();
  const [text, setText] = useState("");
  const [showCal, setShowCal] = useState(false);
  const [classifyMode, setClassifyMode] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = (overrideText?: string) => {
    const trimmed = (overrideText ?? text).trim();
    if (!trimmed || isBusy) return;
    sendMessage(trimmed);
    setText("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  };

  const handleDatePick = (iso: string) => {
    setShowCal(false);
    if (classifyMode) {
      const cmd = `classify ${iso}`;
      setText(cmd);
      setTimeout(() => submit(cmd), 0);
    } else {
      setText(iso);
      setTimeout(() => submit(iso), 0);
    }
  };

  const handleQuickChip = (iso: string) => {
    submit(iso);
  };

  const toggleClassifyMode = () => {
    const entering = !classifyMode;
    setClassifyMode(entering);
    if (entering) setShowCal(true);
  };

  return (
    <div className={styles.wrapper}>
      {/* Quick-date chips */}
      {!classifyMode && (
        <div className={styles.quickChips}>
          <button
            className={styles.chip}
            onClick={() => handleQuickChip(todayISO())}
            disabled={isBusy}
            type="button"
          >
            Today
          </button>
          <button
            className={styles.chip}
            onClick={() => handleQuickChip(yesterdayISO())}
            disabled={isBusy}
            type="button"
          >
            Yesterday
          </button>
          <button
            className={styles.chip}
            onClick={() => setShowCal(s => !s)}
            disabled={isBusy}
            type="button"
          >
            <CalendarChipIcon /> Pick date
          </button>
        </div>
      )}

      {/* Classify mode banner */}
      {classifyMode && (
        <div className={styles.classifyBanner}>
          <span style={{display:'flex',alignItems:'center',gap:'6px'}}><ClassifyIcon /> Classify mode — pick a date from the calendar to auto-classify that day</span>
          <button
            className={styles.classifyBannerClose}
            onClick={() => { setClassifyMode(false); setShowCal(false); }}
            aria-label="Exit classify mode"
            type="button"
          >×</button>
        </div>
      )}

      <div className={`${styles.inputRow} ${isBusy ? styles.busy : ""} ${classifyMode ? styles.classifyActive : ""}`}>
        <textarea
          ref={textareaRef}
          className={styles.textarea}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={
            isBusy ? "Waiting for response…"
            : classifyMode ? "Pick a date above — or type a message manually"
            : "Ask about a date  (e.g. 2025-06-01)"
          }
          rows={1}
          disabled={isBusy}
        />

        {/* Classify toggle */}
        <button
          className={`${styles.classifyBtn} ${classifyMode ? styles.classifyBtnActive : ""}`}
          onClick={toggleClassifyMode}
          disabled={isBusy}
          aria-label="Toggle classify mode"
          aria-pressed={classifyMode}
          title={classifyMode ? "Exit classify mode" : "Classify news by topic"}
          type="button"
        >
          <ClassifyIcon />
        </button>

        {/* Calendar toggle */}
        <div className={styles.calWrap}>
          <IconButton
            active={showCal}
            onClick={() => setShowCal(s => !s)}
            disabled={isBusy}
            aria-label="Pick a date"
            title="Pick a date"
          >
            <CalIcon />
          </IconButton>
          {showCal && (
            <CalendarPicker
              onPick={handleDatePick}
              onClose={() => setShowCal(false)}
            />
          )}
        </div>

        {/* Send */}
        <IconButton
          variant="primary"
          onClick={() => submit()}
          disabled={!text.trim() || isBusy}
          aria-label="Send"
        >
          <SendIcon />
        </IconButton>
      </div>
      <p className={styles.hint}>
        Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> new line ·{" "}
        {classifyMode
          ? <><strong style={{display:'inline-flex',alignItems:'center',gap:'4px'}}><ClassifyIcon /> Classify on</strong> — pick a date to auto-classify</>
          : <span style={{display:'inline-flex',alignItems:'center',gap:'4px'}}><ClassifyIcon /> classify · 📅 pick a date</span>
        }
      </p>
    </div>
  );
};

const CalIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
    <line x1="16" y1="2" x2="16" y2="6"/>
    <line x1="8" y1="2" x2="8" y2="6"/>
    <line x1="3" y1="10" x2="21" y2="10"/>
  </svg>
);

const SendIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

export default ChatInput;
