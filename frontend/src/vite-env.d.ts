/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_MODE?: 'fixture' | 'server'
  readonly VITE_API_BASE_URL?: string
}
