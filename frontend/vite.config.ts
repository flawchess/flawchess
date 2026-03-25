import fs from 'fs'
import path from 'path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'
import { vitePrerenderPlugin } from 'vite-prerender-plugin'

// vite-prerender-plugin emits the prerender entry as a client chunk that
// browsers download (via modulepreload) but never execute. Strip the
// modulepreload link and delete the unused chunk file after build.
function stripPrerenderChunk(): Plugin {
  return {
    name: 'strip-prerender-chunk',
    apply: 'build',
    enforce: 'post',
    writeBundle(options, bundle) {
      const outDir = options.dir ?? 'dist'
      for (const [fileName, chunk] of Object.entries(bundle)) {
        if (chunk.type === 'chunk' && fileName.includes('prerender')) {
          // Remove the chunk file
          const chunkPath = path.join(outDir, fileName)
          fs.rmSync(chunkPath, { force: true })

          // Strip modulepreload link from all HTML files
          const htmlFiles = Object.keys(bundle).filter(f => f.endsWith('.html'))
          for (const htmlFile of htmlFiles) {
            const htmlPath = path.join(outDir, htmlFile)
            if (fs.existsSync(htmlPath)) {
              const html = fs.readFileSync(htmlPath, 'utf-8')
              const cleaned = html.replace(
                new RegExp(`\\s*<link[^>]*${fileName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[^>]*>`),
                ''
              )
              if (cleaned !== html) fs.writeFileSync(htmlPath, cleaned)
            }
          }
          break
        }
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    vitePrerenderPlugin({
      renderTarget: '#root',
      prerenderScript: path.resolve(__dirname, 'src/prerender.tsx'),
      additionalPrerenderRoutes: ['/privacy'],
    }),
    stripPrerenderChunk(),
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
