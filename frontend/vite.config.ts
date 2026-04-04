import { createHash } from 'crypto'
import fs from 'fs'
import path from 'path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'
import { vitePrerenderPlugin } from 'vite-prerender-plugin'

// Social media crawlers aggressively cache OG images by URL. Appending a
// content hash as a query string forces re-fetch when the image changes.
function ogImageHashPlugin(): Plugin {
  return {
    name: 'og-image-hash',
    apply: 'build',
    transformIndexHtml(html) {
      const content = fs.readFileSync(path.resolve(__dirname, 'public/og-image.jpg'))
      const hash = createHash('md5').update(content).digest('base64url').slice(0, 8)
      return html.replaceAll('og-image.jpg', `og-image.jpg?v=${hash}`)
    },
  }
}

// vite-prerender-plugin dynamically imports the prerender entry at build time.
// The loaded module graph (React, source-map WASM) keeps Node alive after the
// build finishes. Force exit once all plugins (including VitePWA) are done.
function forceExitAfterBuild(): Plugin {
  return {
    name: 'force-exit-after-build',
    apply: 'build',
    enforce: 'post',
    closeBundle() {
      setTimeout(() => process.exit(0), 100)
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  envDir: path.resolve(__dirname, '..'), // Load .env from project root
  plugins: [
    ogImageHashPlugin(),
    react(),
    tailwindcss(),
    vitePrerenderPlugin({
      renderTarget: '#root',
      prerenderScript: path.resolve(__dirname, 'src/prerender.tsx'),
      additionalPrerenderRoutes: ['/privacy'],
    }),
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
            purpose: 'any',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: '/icons/icon-maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
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
            urlPattern: /^\/api\//,
            handler: 'NetworkOnly',
          },
        ],
      },
    }),
    // Must be AFTER VitePWA so its closeBundle runs after SW generation
    forceExitAfterBuild(),
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
      '/api': 'http://localhost:8000',
    },
  },
})
