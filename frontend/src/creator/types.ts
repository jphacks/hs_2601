/** 作る人（creator）画面で扱うデータ型 */

export interface Photo {
  id: string
  file: File
  preview: string
  lat?: number
  lng?: number
}

export interface Route {
  id: string
  start: string
  goal: string
  published: boolean
}

export type CreatorScreen =
  | 'home'
  | 'create'
  | 'loading'
  | 'detail'
  | 'routes'
  | 'published'
