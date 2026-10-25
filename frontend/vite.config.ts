import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true, // 同一ネットワークのスマホから接続できるようにする
    port: 5173,
    allowedHosts: ['.trycloudflare.com'], // Cloudflare Tunnel 経由のスマホからのアクセスを許可
  },
})
