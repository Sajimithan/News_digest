import React from "react";
import { BrowserRouter } from "react-router-dom";
import { ChatProvider } from "./store";
import { StockChatProvider } from "./store/stockStore";
import AppRoutes from "./routes";

const App: React.FC = () => (
  <BrowserRouter>
    <ChatProvider>
      <StockChatProvider>
        <AppRoutes />
      </StockChatProvider>
    </ChatProvider>
  </BrowserRouter>
);

export default App;
