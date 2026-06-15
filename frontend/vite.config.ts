import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Codespaces (and other HTTPS reverse-proxy setups) serve the dev server over
// port 443, so the HMR websocket client must be told to connect there. Locally
// (plain http://localhost:5173, including local Docker) there is no server on
// 443, and forcing clientPort:443 floods the console with endless
// ERR_CONNECTION_REFUSED to ws://localhost:443. Only override HMR when we are
// actually behind such a proxy.
const isCodespaces =
  process.env.CODESPACES === 'true' || !!process.env.CODESPACE_NAME

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
    // Only pin the HMR client to 443 when served through an HTTPS proxy
    // (Codespaces). Locally, leave it as Vite's default so the websocket
    // connects to the actual dev port instead of a dead :443.
    hmr: isCodespaces ? { clientPort: 443 } : true,
  },
})
