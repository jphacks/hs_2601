/** 作成者 ID。ログインは作らず、初回アクセス時に生成して localStorage に保存する */

const STORAGE_KEY = 'wayfinder.creatorId'

export function getOrCreateCreatorId(storage: Storage = localStorage): string {
  const existing = storage.getItem(STORAGE_KEY)
  if (existing) return existing
  const created = crypto.randomUUID()
  storage.setItem(STORAGE_KEY, created)
  return created
}
