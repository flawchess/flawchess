import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/auth': {
        target: 'http://localhost:8000',
        // Don't proxy /auth/callback — that's a frontend route for OAuth redirect
        bypass(req) {
          if (req.url?.startsWith('/auth/callback')) return req.url
        },
      },
      '/analysis': 'http://localhost:8000',
      '/games': 'http://localhost:8000',
      '/imports': 'http://localhost:8000',
      '/position-bookmarks': 'http://localhost:8000',
      '/stats': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
