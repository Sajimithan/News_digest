import React, { useState } from "react";
import { useChatStore } from "../../store";
import styles from "./StatusLog.module.css";

const ICONS: Record<string, string> = {
  info: "ℹ️",
  success: "✅",
  warn: "⚠️",
  error: "❌",
};

const StatusLog: React.FC = () => {
  const { statusLog: entries } = useChatStore();
  const [open, setOpen] = useState(false);

  if (entries.length === 0) return null;

  return (
    <div className={styles.panel}>
      <button className={styles.toggle} onClick={() => setOpen((o) => !o)}>
        <span className={styles.toggleIcon}>{open ? "▾" : "▸"}</span>
        <span>Activity log</span>
        <span className={styles.count}>{entries.length}</span>
      </button>

      {open && (
        <ul className={styles.list}>
          {entries.map((e) => (
            <li key={e.id} className={`${styles.entry} ${styles[e.level]}`}>
              <span className={styles.entryIcon}>
                {ICONS[e.level] ?? "•"}
              </span>
              <span className={styles.entryText}>{e.text}</span>
              <span className={styles.entryTime}>{e.time}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default StatusLog;
