import React, { createContext, useContext, type ReactNode } from 'react'
import { useStockChat, type UseStockChatReturn } from '../hooks/useStockChat'

const StockChatContext = createContext<UseStockChatReturn | null>(null)

export const StockChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const chat = useStockChat()
  return <StockChatContext.Provider value={chat}>{children}</StockChatContext.Provider>
}

export function useStockStore(): UseStockChatReturn {
  const ctx = useContext(StockChatContext)
  if (!ctx) throw new Error('useStockStore must be used within <StockChatProvider>')
  return ctx
}
