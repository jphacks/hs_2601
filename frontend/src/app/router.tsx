import { createBrowserRouter, Navigate } from 'react-router-dom'
import { CreatingPage } from '../creator/pages/CreatingPage'
import { CreatorRoot } from '../creator/pages/CreatorRoot'
import { HomePage } from '../creator/pages/HomePage'
import { PublishedPage } from '../creator/pages/PublishedPage'
import { ResultPage } from '../creator/pages/ResultPage'
import { RouteCreatePage } from '../creator/pages/RouteCreatePage'
import { RouteListPage } from '../creator/pages/RouteListPage'
import { NavigatePage } from '../follower/pages/NavigatePage'

/**
 * ルーティング。
 * - /c/*     作る人（creator）
 * - /r/:id   参加者（follower）
 */
export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/c" replace /> },
  {
    path: '/c',
    element: <CreatorRoot />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'new', element: <RouteCreatePage /> },
      { path: 'new/creating/:jobId', element: <CreatingPage /> },
      { path: 'routes', element: <RouteListPage /> },
      { path: 'routes/:routeId', element: <ResultPage /> },
      { path: 'published', element: <PublishedPage /> },
    ],
  },
  { path: '/r/:id', element: <NavigatePage /> },
])
