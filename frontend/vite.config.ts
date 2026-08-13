import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    proxy: {
      // Même origine que l'API en dev : pas de CORS, cookie httpOnly
      // SameSite=Strict envoyé normalement (étape 1). Voir
      // docs/adr/2026-08-13-meme-origine-proxy-vite.md.
      '/api': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
    },
  },
})
