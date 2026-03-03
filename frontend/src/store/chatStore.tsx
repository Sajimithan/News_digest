import React, { createContext, useContext, type ReactNode } from 'react'
import { useChat, type UseChatReturn } from '../hooks/useChat'

const ChatContext = createContext<UseChatReturn | null>(null)

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const chat = useChat()
  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>
}

export function useChatStore(): UseChatReturn {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChatStore must be used within <ChatProvider>')
  return ctx
}
