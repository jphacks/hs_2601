import { useParams } from 'react-router-dom'

export function FollowerNavigatePage() {
  const { id } = useParams<{ id: string }>()
  return (
    <main>
      <h1>参加者</h1>
      <p>道案内 ID: {id}</p>
      <p>道案内を表示する画面（準備中）</p>
    </main>
  )
}
