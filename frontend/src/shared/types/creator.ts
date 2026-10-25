/**
 * 作る人向け API の入出力。backend/app/schemas/creator_api.py と 1:1 にする。
 * 契約は docs/interface.md 4 章（PlanInput、snake_case）と 5 章（HTTP API、camelCase）。
 */
import type { PlanStatus } from './routePlan'

/** 座標の出どころ。既定は gps */
export type LocationSource = 'gps' | 'manual' | 'exif'

/** 送信する写真 1 枚。座標が取れた写真だけを送る（4 章） */
export interface PhotoInput {
  /** 英数字・`-`・`_` のみ。ファイル名 `<id>.jpg` と manifest の突き合わせに使う */
  id: string
  /** JPEG（長辺 1280px 以下）に変換済みの画像 */
  file: Blob
  lat: number
  lng: number
  /** Geolocation の accuracy（m） */
  accuracyM?: number
  /** 撮影時刻（ISO 8601） */
  takenAt?: string
  /** 作成者のメッセージ（目印文に使われる）。無ければ null */
  caption?: string | null
}

export interface CreateRouteInput {
  /** 命名。ID はこのハッシュ（3 章） */
  name: string
  origin: string
  destination: string
  photos: PhotoInput[]
  creatorId: string
  /** 作成日時（ISO 8601）。省略時は送信時刻 */
  createdAt?: string
}

/** POST /api/routes の 202 */
export interface CreateRouteResult {
  jobId: string
  routeId: string
}

export type JobState = 'running' | 'done' | 'failed'

/** 作成ジョブの処理段階（画面の「◯◯中…」表示用） */
export type JobStep = 'geocode' | 'route' | 'streetview' | 'landmark' | 'arrow' | 'save'

/** GET /api/jobs/{jobId} */
export interface JobStatus {
  jobId: string
  state: JobState
  /** 今の処理段階。任意 */
  step?: JobStep | null
  /** 完了時にだけ入る */
  routeId?: string | null
  /** 失敗時にだけ入る（利用者向けの日本語） */
  message?: string | null
}

/** GET /api/routes?creator_id= の 1 件（新しい順） */
export interface RouteSummary {
  id: string
  name: string
  origin: string
  destination: string
  status: PlanStatus
  /** 保存日時（ISO 8601） */
  createdAt: string
}

/** POST /api/routes/{id}/publish */
export interface PublishResult {
  routeId: string
  /** 参加者に渡す URL */
  url: string
  /** QR 画像のパス（`/api/routes/{id}/qr.png`）。API の base URL を前に付けて使う。fixture では無い */
  qrPath?: string | null
}

/** manifest の写真 1 枚（4 章 `photos[]`、snake_case） */
export interface PlanInputPhoto {
  id: string
  seq: number
  image: string
  lat: number
  lng: number
  accuracy_m: number | null
  taken_at: string | null
  location_source: LocationSource
  caption: string | null
}

/** 作成入力の中間データ（4 章 `PlanInput`）。POST /api/routes の `manifest` に JSON 文字列で入れる */
export interface PlanInput {
  version: 1
  name: string
  origin: string
  destination: string
  creator_id: string
  created_at: string
  photos: PlanInputPhoto[]
  options: { use_vlm_on_photos: boolean }
}
