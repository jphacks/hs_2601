/**
 * 5 本の API（+ 参加者向け詳細取得）への入口。creator / follower はここだけを import する。
 *
 * VITE_API_MODE=server でバックエンドを呼ぶ。未指定・fixture のときは
 * shared/fixtures のサンプルを返す fixtureApi で動く（バックエンド未接続の間の既定）。
 */
import { createFixtureApi } from './fixtureApi'
import { serverApi } from './serverApi'
import type { RouteApi } from './types'

export type ApiMode = 'fixture' | 'server'

export const API_MODE: ApiMode = import.meta.env.VITE_API_MODE === 'server' ? 'server' : 'fixture'

export const routeApi: RouteApi = API_MODE === 'server' ? serverApi : createFixtureApi()

export type { RouteApi } from './types'
