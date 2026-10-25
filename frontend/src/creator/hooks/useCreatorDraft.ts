import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { useCapture } from './useCapture'

/** 作成中の入力（命名・出発地・目的地・写真）。/c 配下のページ間で共有する */
export type CreatorDraft = ReturnType<typeof useCreatorDraft>

/** ルートのレイアウト（CreatorRoot）で 1 回だけ呼び、Outlet context で配下に渡す */
export function useCreatorDraft() {
  const [name, setName] = useState('')
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const capture = useCapture()

  function reset() {
    setName('')
    setOrigin('')
    setDestination('')
    capture.clearPhotos()
  }

  return { name, setName, origin, setOrigin, destination, setDestination, ...capture, reset }
}

/** 配下のページから draft を受け取る */
export function useDraft(): CreatorDraft {
  return useOutletContext<CreatorDraft>()
}
