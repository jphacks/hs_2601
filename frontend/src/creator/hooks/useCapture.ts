import { useCallback, useEffect, useRef, useState } from 'react'
import type { CapturedPhoto } from '../types'

const GEOLOCATION_OPTIONS: PositionOptions = { enableHighAccuracy: true, timeout: 10000 }

function updatePhoto(
  photos: CapturedPhoto[],
  id: string,
  patch: Partial<CapturedPhoto>,
): CapturedPhoto[] {
  return photos.map((p) => (p.id === id ? { ...p, ...patch } : p))
}

/** File を受け取った瞬間に Geolocation で座標を取り、写真と座標をペアで保持する */
export function useCapture() {
  const [photos, setPhotos] = useState<CapturedPhoto[]>([])
  const photosRef = useRef<CapturedPhoto[]>([])

  useEffect(() => {
    photosRef.current = photos
  }, [photos])

  // ページを離れたらサムネイル用 Object URL を解放する
  useEffect(() => {
    return () => {
      photosRef.current.forEach((p) => URL.revokeObjectURL(p.preview))
    }
  }, [])

  const attachLocation = useCallback((photoId: string) => {
    if (!navigator.geolocation) {
      setPhotos((old) => updatePhoto(old, photoId, { locationError: 'この端末では位置情報を使えません' }))
      return
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) =>
        setPhotos((old) =>
          updatePhoto(old, photoId, { lat: coords.latitude, lng: coords.longitude }),
        ),
      (err) => setPhotos((old) => updatePhoto(old, photoId, { locationError: err.message })),
      GEOLOCATION_OPTIONS,
    )
  }, [])

  const addPhotos = useCallback(
    (files: FileList | null) => {
      if (!files) return
      const added = Array.from(files)
        .filter((file) => file.type.startsWith('image/'))
        .map<CapturedPhoto>((file) => ({
          id: crypto.randomUUID(),
          file,
          preview: URL.createObjectURL(file),
        }))
      if (added.length === 0) return
      setPhotos((old) => [...old, ...added])
      added.forEach((p) => attachLocation(p.id))
    },
    [attachLocation],
  )

  const removePhoto = useCallback((photo: CapturedPhoto) => {
    URL.revokeObjectURL(photo.preview)
    setPhotos((old) => old.filter((p) => p.id !== photo.id))
  }, [])

  const clearPhotos = useCallback(() => {
    setPhotos((old) => {
      old.forEach((p) => URL.revokeObjectURL(p.preview))
      return []
    })
  }, [])

  return { photos, addPhotos, removePhoto, clearPhotos }
}
