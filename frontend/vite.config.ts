import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '..', '')
  const proxy = {
    '/api': { target: `http://127.0.0.1:${env.API_PORT || '8000'}`, changeOrigin: false },
  }
  return {
    plugins: [react(), tailwindcss()],
    cacheDir: env.API_PORT === '18000' ? 'node_modules/.vite-e2e' : 'node_modules/.vite',
    envDir: '..',
    server: { proxy },
    preview: { proxy },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}'],
      restoreMocks: true,
    },
  }
})
