import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 3000,
    // Proxy all API and SSE requests to the FastAPI backend during development.
    // The SSE endpoint needs changeOrigin so cookies / headers pass through.
    proxy: {
      '/chat':           'http://localhost:8000',
      '/update':         'http://localhost:8000',
      '/news':           'http://localhost:8000',
      '/health':         'http://localhost:8000',
      '/job':            'http://localhost:8000',
      '/debug':          'http://localhost:8000',
      '/stock':          'http://localhost:8000',
      '/events': {
        target:       'http://localhost:8000',
        changeOrigin: true,
        // SSE needs these headers to stay alive
        headers: {
          'Connection': 'keep-alive',
          'Cache-Control': 'no-cache',
        },
      },
    },
  },

  build: {
    // Output to ../app/static so FastAPI can serve the React build directly.
    outDir: '../frontend/dist',
    emptyOutDir: true,
  },
})
