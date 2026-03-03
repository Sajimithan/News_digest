import React from 'react'
import AppLayout from '../components/layout/AppLayout'
import StockChatContainer from '../components/Stock/StockChatContainer'

const StockPage: React.FC = () => (
  <AppLayout centerContent={<StockChatContainer />} />
)

export default StockPage
