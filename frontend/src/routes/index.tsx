import React from 'react'
import { Routes, Route } from 'react-router-dom'
import ChatPage from '../pages/ChatPage'
import StockPage from '../pages/StockPage'
import NotFoundPage from '../pages/NotFoundPage'

const AppRoutes: React.FC = () => (
  <Routes>
    <Route path="/" element={<ChatPage />} />
    <Route path="/market" element={<StockPage />} />
    <Route path="*" element={<NotFoundPage />} />
  </Routes>
)

export default AppRoutes
