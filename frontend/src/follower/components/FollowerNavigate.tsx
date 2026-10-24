
import { useState } from 'react'

interface Props {
  routeId: string | undefined
}

const demoSteps = [
  {
    direction: '直進',
    landmark: '駅の出口を出て、そのまま歩道を進みます。',
    distance: 120,
    arrow: '↑',
    color: '#176B4D',
    image:
      'https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=1000&q=80',
  },
  {
    direction: '右に曲がる',
    landmark: '横断歩道の先で右に曲がります。',
    distance: 80,
    arrow: '↗',
    color: '#176B4D',
    image:
      'https://images.unsplash.com/photo-1519501025264-65ba15a82390?auto=format&fit=crop&w=1000&q=80',
  },
  {
    direction: '左に曲がる',
    landmark: '大きな通りに出たら左に曲がります。',
    distance: 60,
    arrow: '↖',
    color: '#176B4D',
    image:
      'https://images.unsplash.com/photo-1449824913935-59a10b8d2000?auto=format&fit=crop&w=1000&q=80',
  },
  {
    direction: '直進',
    landmark: '建物が見えたら、入口まで進みます。',
    distance: 30,
    arrow: '↑',
    color: '#176B4D',
    image:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1000&q=80',
  },
  {
    direction: '到着！',
    landmark: '目的地に到着しました。お疲れさまでした！',
    distance: 0,
    arrow: '✓',
    color: '#176B4D',
    image:
      'https://images.unsplash.com/photo-1511818966892-d7d671e672a2?auto=format&fit=crop&w=1000&q=80',
  },
]

export function FollowerNavigate({ routeId }: Props) {
  const [current, setCurrent] = useState(0)
  const step = demoSteps[current]
  const arrived = current === demoSteps.length - 1
  const progress = ((current + 1) / demoSteps.length) * 100

  return (
    <main
      style={{
        minHeight: '100vh',
        background: '#F5F5F0',
        color: '#202820',
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        padding: '20px 16px 32px',
        boxSizing: 'border-box',
      }}
    >
      <div style={{ maxWidth: 480, margin: '0 auto' }}>
        <header style={{ marginBottom: 24 }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 800,
                  letterSpacing: 3,
                  color: '#176B4D',
                }}
              >
                WAYFINDER
              </div>
              <div style={{ fontSize: 12, color: '#73776F', marginTop: 4 }}>
                写真でつなぐ道案内
              </div>
            </div>
            <span
              style={{
                fontSize: 11,
                padding: '6px 10px',
                borderRadius: 20,
                background: '#DDEFE3',
                color: '#176B4D',
                fontWeight: 700,
              }}
            >
              DEMO
            </span>
          </div>

          <h1 style={{ fontSize: 24, margin: '24px 0 6px' }}>
            会場までの道案内
          </h1>
          <p style={{ fontSize: 14, color: '#73776F', margin: 0 }}>
            出発地 → 目的地
          </p>
          <p style={{ fontSize: 11, color: '#73776F', marginTop: 6 }}>
            案内ID：{routeId ?? 'demo'}
          </p>

          <div
            style={{
              height: 5,
              background: '#E0E3DB',
              borderRadius: 10,
              marginTop: 18,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${progress}%`,
                background: '#176B4D',
                transition: 'width 0.2s',
              }}
            />
          </div>
          <p
            style={{
              fontSize: 12,
              color: '#73776F',
              textAlign: 'right',
              margin: '7px 0 0',
            }}
          >
            {arrived
              ? 'すべての案内が完了しました'
              : `${current + 1} / ${demoSteps.length} ステップ`}
          </p>
        </header>

        <section
          style={{
            background: '#FFFFFF',
            borderRadius: 20,
            padding: 12,
            boxShadow: '0 4px 18px #17291A0D',
          }}
        >
          <div
            style={{
              position: 'relative',
              borderRadius: 14,
              overflow: 'hidden',
              background: '#E5E7E0',
            }}
          >
            <img
              src={step.image}
              alt="道の目印の参考写真"
              style={{
                display: 'block',
                width: '100%',
                height: 250,
                objectFit: 'cover',
              }}
            />
            <span
              style={{
                position: 'absolute',
                top: 12,
                left: 12,
                background: '#FFFFFFF0',
                borderRadius: 8,
                padding: '7px 10px',
                fontSize: 12,
                fontWeight: 700,
              }}
            >
              {arrived ? 'GOAL' : `目印 ${current + 1}`}
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              padding: '22px 8px',
            }}
          >
            <div
              style={{
                width: 82,
                height: 82,
                flexShrink: 0,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                borderRadius: 20,
                background: step.color,
                color: '#FFFFFF',
                fontSize: 48,
                fontWeight: 700,
              }}
            >
              {step.arrow}
            </div>
            <div>
              <h2
                style={{
                  fontSize: 25,
                  lineHeight: 1.3,
                  margin: 0,
                  color: step.color,
                }}
              >
                {step.direction}
              </h2>
              <p
                style={{
                  fontSize: 14,
                  lineHeight: 1.8,
                  margin: '8px 0 0',
                  color: '#50564F',
                }}
              >
                {step.landmark}
              </p>
            </div>
          </div>

          <div
            style={{
              borderTop: '1px solid #E9EBE5',
              padding: '16px 8px 10px',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <div style={{ fontSize: 26 }}>🚶</div>
            <div>
              <div style={{ fontSize: 12, color: '#73776F' }}>
                {arrived ? '目的地' : '次の目印まで'}
              </div>
              <div style={{ fontSize: 25, fontWeight: 800, marginTop: 3 }}>
                {arrived ? '到着！' : `約 ${step.distance} m`}
              </div>
            </div>
          </div>
        </section>

        <div
          style={{
            display: 'flex',
            gap: 12,
            marginTop: 18,
          }}
        >
          <button
            onClick={() => setCurrent((n) => Math.max(0, n - 1))}
            disabled={current === 0}
            style={{
              flex: 1,
              padding: '16px 10px',
              borderRadius: 14,
              border: '1px solid #D9DDD4',
              background: '#FFFFFF',
              color: '#176B4D',
              fontSize: 16,
              fontWeight: 700,
              opacity: current === 0 ? 0.4 : 1,
              cursor: current === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            ← 前へ
          </button>
          <button
            onClick={() =>
              setCurrent((n) => Math.min(demoSteps.length - 1, n + 1))
            }
            disabled={arrived}
            style={{
              flex: 1,
              padding: '16px 10px',
              borderRadius: 14,
              border: 'none',
              background: '#176B4D',
              color: '#FFFFFF',
              fontSize: 16,
              fontWeight: 700,
              opacity: arrived ? 0.5 : 1,
              cursor: arrived ? 'not-allowed' : 'pointer',
            }}
          >
            {arrived ? '到着済み ✓' : '次へ →'}
          </button>
        </div>

        <p
          style={{
            fontSize: 11,
            lineHeight: 1.7,
            textAlign: 'center',
            color: '#858980',
            marginTop: 18,
          }}
        >
          ※ 現在は画面確認用のサンプルです。写真・距離・経路は実際の道順ではありません。
        </p>
      </div>
    </main>
  )
}
