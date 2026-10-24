import { useParams } from 'react-router-dom'
import { FollowerNavigate } from '../components/FollowerNavigate'

/** URL から ID を取り出して components に渡すだけ */
export function FollowerNavigatePage() {
  const { id } = useParams<{ id: string }>()
  return <FollowerNavigate routeId={id} />
}
