/** 開発用プレビューの入口（/src/creator/annotate/preview.html）。本番ビルドには含まれない */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../../index.css'
import { PreviewApp } from './PreviewApp'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PreviewApp />
  </StrictMode>,
)
