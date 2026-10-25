import { useNavigate } from 'react-router-dom'
import { CreatorHome } from '../components/CreatorHome'

/** ホーム。「道を作る」「作った道を公開する」の 2 ボタン */
export function HomePage() {
  const navigate = useNavigate()
  return <CreatorHome onCreate={() => navigate('/c/new')} onRoutes={() => navigate('/c/routes')} />
}
