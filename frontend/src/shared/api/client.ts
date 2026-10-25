/**
 * バックエンド通信の共通ラッパー。
 * 各 API 関数（endpoints.ts）はこれを経由して呼ぶ。
 */

const DEFAULT_BASE_URL = 'http://localhost:8000'

/** 末尾の / を落として、path 側の先頭 / と二重にならないようにする */
const BASE_URL: string = (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL).replace(/\/+$/, '')

/** API のパス（`/api/...`）を完全な URL にする。`<img src>` 用。すでに完全な URL ならそのまま */
export function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path
  return `${BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(status: number, body: unknown) {
    super(`API error ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

type Method = 'GET' | 'POST' | 'PUT' | 'DELETE'

interface RequestOptions {
  method?: Method
  /** JSON として送るボディ。FormData を渡す場合はそのまま送る */
  body?: unknown
  signal?: AbortSignal
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text()
  if (text.length === 0) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export async function request<T>(
  path: string,
  { method = 'GET', body, signal }: RequestOptions = {},
): Promise<T> {
  const isForm = body instanceof FormData
  const res = await fetch(apiUrl(path), {
    method,
    headers: isForm || body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: isForm ? body : body === undefined ? undefined : JSON.stringify(body),
    signal,
  })
  const data = await parseBody(res)
  if (!res.ok) throw new ApiError(res.status, data)
  return data as T
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: 'POST', body, signal }),
}
