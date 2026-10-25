/**
 * 作成受付で送る manifest（interface.md 4 章 PlanInput）を組み立てる。
 * キーは snake_case、seq は配列順、画像パスは `photos/<id>.jpg`。
 */
import type { CreateRouteInput, PhotoInput, PlanInput, PlanInputPhoto } from '../types/creator'

/** 写真 ID に使える文字（4 章）。バックエンドのファイル名にもなる */
export const PHOTO_ID_PATTERN = /^[A-Za-z0-9_-]{1,64}$/

/** multipart で送るときのファイル名。manifest の `image` と突き合わされる */
export function photoFileName(id: string): string {
  return `${id}.jpg`
}

function toManifestPhoto(photo: PhotoInput, seq: number): PlanInputPhoto {
  if (!PHOTO_ID_PATTERN.test(photo.id)) throw new Error(`写真 ID に使えない文字があります: ${photo.id}`)
  return {
    id: photo.id,
    seq,
    image: `photos/${photoFileName(photo.id)}`,
    lat: photo.lat,
    lng: photo.lng,
    accuracy_m: photo.accuracyM ?? null,
    taken_at: photo.takenAt ?? null,
    location_source: 'gps',
    caption: photo.caption ?? null,
  }
}

/** CreateRouteInput → PlanInput。createdAt が無ければ fallbackCreatedAt を使う */
export function buildPlanManifest(input: CreateRouteInput, fallbackCreatedAt: string): PlanInput {
  return {
    version: 1,
    name: input.name.trim(),
    origin: input.origin.trim(),
    destination: input.destination.trim(),
    creator_id: input.creatorId,
    created_at: input.createdAt ?? fallbackCreatedAt,
    photos: input.photos.map(toManifestPhoto),
    options: { use_vlm_on_photos: false },
  }
}
