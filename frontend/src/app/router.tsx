import { createBrowserRouter, Navigate } from 'react-router-dom'
import { CreatorHomePage } from '../creator/pages/CreatorHomePage'
import { FollowerNavigatePage } from '../follower/pages/FollowerNavigatePage'

/**
 * ルーティング。
 * - /c/*     作る人（creator）
 * - /r/:id   参加者（follower）
 */
export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/c" replace /> },
  { path: '/c', element: <CreatorHomePage /> },
  { path: '/r/:id', element: <FollowerNavigatePage /> },
])
