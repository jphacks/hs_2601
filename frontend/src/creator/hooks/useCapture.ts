import { useCallback, useEffect, useRef, useState } from 'react'
import { toIsoWithOffset } from '../../shared/lib/datetime'
import { geolocationErrorMessage } from '../photoLocation'
import type { CapturedPhoto } from '../types'

/** 撮影した瞬間の位置が欲しいので、古いキャッシュ（maximumAge）は使わない */
const GEOLOCATION_OPTIONS: PositionOptions = { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }

function updatePhoto(
  photos: CapturedPhoto[],
  id: string,
  patch: Partial<CapturedPhoto>,
): CapturedPhoto[] {
  return photos.map((p) => (p.id === id ? { ...p, ...patch } : p))
}

/**
 * File を受け取った瞬間に Geolocation で座標（と精度）を取り、写真と座標をペアで保持する。
 * 取れなかった写真は retryLocation で取り直すか removePhoto で外す。
 */
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
          updatePhoto(old, photoId, {
            lat: coords.latitude,
            lng: coords.longitude,
            accuracyM: coords.accuracy,
            locationError: undefined,
          }),
        ),
      (err) =>
        setPhotos((old) =>
          updatePhoto(old, photoId, { locationError: geolocationErrorMessage(err.code) }),
        ),
      GEOLOCATION_OPTIONS,
    )
  }, [])

  /** 位置情報が取れなかった写真の取り直し。今いる場所の座標になるので、撮った場所で押してもらう */
  const retryLocation = useCallback(
    (photo: CapturedPhoto) => {
      setPhotos((old) => updatePhoto(old, photo.id, { locationError: undefined }))
      attachLocation(photo.id)
    },
    [attachLocation],
  )

  const addPhotos = useCallback(
    (files: FileList | null) => {
      if (!files) return
      const added = Array.from(files)
        .filter((file) => file.type.startsWith('image/'))
        .map<CapturedPhoto>((file) => ({
          id: crypto.randomUUID(),
          file,
          preview: URL.createObjectURL(file),
          takenAt: toIsoWithOffset(new Date()),
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

  return { photos, addPhotos, removePhoto, retryLocation, clearPhotos }
}
