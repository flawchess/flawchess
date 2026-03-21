import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: { enabled: true },
      manifest: {
        name: 'FlawChess',
        short_name: 'FlawChess',
        description: 'Chess opening analysis by position',
        theme_color: '#0a0a0a',
        background_color: '#0a0a0a',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        // Only use navigateFallback for paths that don't hit the backend.
        // Allowlist approach: only SPA routes get index.html fallback.
        // Everything else (API, OAuth callbacks) passes through to the server.
        navigateFallback: null,
        runtimeCaching: [
          {
            urlPattern: /^\/(?:auth|analysis|games|imports|position-bookmarks|stats|users|health)\//,
            handler: 'NetworkOnly',
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,
    hmr: {
      clientPort: process.env.TUNNEL ? 443 : undefined,
    },
    allowedHosts: process.env.TUNNEL ? true : [],
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
      '/users': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
