import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const backend = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    target: 'es2020'
  },
  server: {
    host: '127.0.0.1',
    port: 3000,
    strictPort: true,
    // 只适合开发：生产由 FastAPI 直接托管 dist，同源，不需要代理。
    proxy: {
      '/api': { target: backend, changeOrigin: true, ws: true },
      '/img': { target: backend, changeOrigin: true }
    }
  }
})
