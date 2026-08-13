import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Séparé de vite.config.ts : Vitest ignore la clé `server.proxy` (elle ne
// concerne que le serveur de dev), et un fichier dédié évite toute ambiguïté
// sur quelle config s'applique à `vitest run` vs `vite dev`/`vite build`.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
  },
})
