import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const backendTarget = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'
const proxy = {
  '/api': {
    target: backendTarget,
    changeOrigin: true,
    ws: true
  }
}

export default defineConfig({
  plugins: [vue()],
  build: {
    chunkSizeWarningLimit: 600
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    host: '127.0.0.1',
    port: 3000,
    // Fail loudly instead of silently moving to :3001, which would break the
    // backend origin allow-list (refresh and the log stream would 403).
    strictPort: true,
    proxy
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
    strictPort: true,
    proxy
  }
})
