import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // 同一ネットワークのスマホから接続できるようにする
    port: 5173,
  },
})
