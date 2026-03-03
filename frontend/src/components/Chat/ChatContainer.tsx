import React from "react";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";
import styles from "./ChatContainer.module.css";

const ChatContainer: React.FC = () => (
  <div className={styles.container}>
    <MessageList />
    <ChatInput />
  </div>
);

export default ChatContainer;
