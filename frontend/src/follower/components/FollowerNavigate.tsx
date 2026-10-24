interface Props {
  routeId: string | undefined
}

export function FollowerNavigate({ routeId }: Props) {
  return (
    <main>
      <h1>参加者</h1>
      <p>道案内 ID: {routeId ?? '(なし)'}</p>
      <p>道案内を表示する画面（準備中）</p>
    </main>
  )
}
