import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { CreatorLayout } from '../components/CreatorLayout'
import { useCreatorDraft } from '../hooks/useCreatorDraft'

export const CREATOR_HOME = '/c'

/** /c 配下の共通レイアウト。作成中の入力（draft）をここで持ち、Outlet context で配下に渡す */
export function CreatorRoot() {
  const draft = useCreatorDraft()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <CreatorLayout showHomeLink={pathname !== CREATOR_HOME} onHome={() => navigate(CREATOR_HOME)}>
      <Outlet context={draft} />
    </CreatorLayout>
  )
}
