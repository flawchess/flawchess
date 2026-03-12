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
      '/auth': 'http://localhost:8000',
      '/analysis': 'http://localhost:8000',
      '/games': 'http://localhost:8000',
      '/imports': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
