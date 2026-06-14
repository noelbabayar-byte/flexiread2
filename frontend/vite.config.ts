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
    // ESKI: Frontend API'ye dogrudan erisiyordu, CORS sorunlari olabiliyordu
    // YENI: /api yolu API'ye proxy ediliyor
    //       Bu sayede ayni origin uzerinden API'ye erisilir
    //       CORS sorunlari ortadan kalkar
    // NOT: VITE_API_URL ayarliysa proxy kullanilmayabilir ama
    //      yedek olarak burada da mevcut
    // ===================================================================
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://api:8000',
        changeOrigin: true,
        // rewrite kaldirdik cunku backend /api/v1 prefixini bekliyor
      },
    },
    hmr: {
      clientPort: 443,
    },
  },
})
