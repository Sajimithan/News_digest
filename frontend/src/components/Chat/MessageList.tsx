import React, { useEffect, useRef } from "react";
import { useChatStore } from "../../store";
import MessageBubble from "./MessageBubble";
import styles from "./MessageList.module.css";

const MessageList: React.FC = () => {
  const { messages } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className={styles.list}>
      {messages.length === 0 && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>📰</div>
          <p className={styles.emptyTitle}>Tech News Digest</p>
          <p className={styles.emptyHint}>
            Type a date like <code>2025-06-01</code> and I'll fetch the latest
            tech news for that day and give you a live summary.
          </p>
        </div>
      )}
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default MessageList;
