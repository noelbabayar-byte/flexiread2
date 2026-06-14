import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  // Relative base so assets load correctly behind Codespaces proxies.
  base: './',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    strictPort: true,
    // ===================================================================
    // FIX #1: API Proxy - Vite dev server'a API proxy eklendi
    // ===================================================================
    // ESKI: Frontend API'ye doğrudan erişiyordu, CORS sorunları olabiliyordu
    // YENI: /api yolu API'ye proxy ediliyor
    //       Bu sayede aynı origin üzerinden API'ye erişilir
    //       CORS sorunları ortadan kalkar
    // NOT: VITE_API_URL ayarlıysa proxy kullanılmayabilir ama
    //      yedek olarak burada da mevcut
    // ===================================================================
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://api:8000',
        changeOrigin: true,
        // rewrite kaldirdik çünkü backend /api/v1 prefixini bekliyor
      },
    },
    hmr: {
      clientPort: 443,
    },
  },
})
