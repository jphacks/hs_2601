import { useState } from 'react'
import type { CreatorScreen, Photo, Route } from '../types'

const GEOLOCATION_OPTIONS: PositionOptions = { enableHighAccuracy: true, timeout: 10000 }
/** 画面動作確認用の疑似待ち時間。バックエンドの作成 API 接続時に置き換える */
const MOCK_CREATE_DELAY_MS = 1000

/** 作る人の画面遷移と状態をまとめて管理する */
export function useCreatorFlow() {
  const [screen, setScreen] = useState<CreatorScreen>('home')
  const [start, setStart] = useState('')
  const [goal, setGoal] = useState('')
  const [photos, setPhotos] = useState<Photo[]>([])
  const [routes, setRoutes] = useState<Route[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [activeRoute, setActiveRoute] = useState<Route | null>(null)

  function attachLocation(photoId: string) {
    navigator.geolocation?.getCurrentPosition(
      (position) => {
        setPhotos((old) =>
          old.map((p) =>
            p.id === photoId
              ? { ...p, lat: position.coords.latitude, lng: position.coords.longitude }
              : p,
          ),
        )
      },
      () => {
        console.log('位置情報を取得できませんでした')
      },
      GEOLOCATION_OPTIONS,
    )
  }

  function addPhotos(files: FileList | null) {
    if (!files) return

    Array.from(files).forEach((file) => {
      if (!file.type.startsWith('image/')) return

      const photo: Photo = {
        id: crypto.randomUUID(),
        file,
        preview: URL.createObjectURL(file),
      }
      setPhotos((old) => [...old, photo])
      attachLocation(photo.id)
    })
  }

  function removePhoto(photo: Photo) {
    URL.revokeObjectURL(photo.preview)
    setPhotos((old) => old.filter((p) => p.id !== photo.id))
  }

  function createRoute() {
    if (!start.trim() || !goal.trim()) {
      alert('出発地と目的地を入力してください')
      return
    }
    if (photos.length === 0) {
      alert('目印となる写真を撮影してください')
      return
    }

    setScreen('loading')

    // 現段階では画面の動作確認用。
    // 後からバックエンドの作成 API に置き換えます。
    setTimeout(() => {
      const route: Route = {
        id: crypto.randomUUID(),
        start,
        goal,
        published: false,
      }
      setRoutes((old) => [...old, route])
      setActiveRoute(route)
      setScreen('detail')
    }, MOCK_CREATE_DELAY_MS)
  }

  function toggleSelected(routeId: string, checked: boolean) {
    setSelected((old) =>
      checked ? [...old, routeId] : old.filter((id) => id !== routeId),
    )
  }

  function openDetail(route: Route) {
    setActiveRoute(route)
    setScreen('detail')
  }

  function publishRoutes() {
    setRoutes((old) =>
      old.map((r) => (selected.includes(r.id) ? { ...r, published: true } : r)),
    )
    setScreen('published')
  }

  return {
    screen,
    setScreen,
    start,
    setStart,
    goal,
    setGoal,
    photos,
    routes,
    selected,
    activeRoute,
    addPhotos,
    removePhoto,
    createRoute,
    toggleSelected,
    openDetail,
    publishRoutes,
  }
}
