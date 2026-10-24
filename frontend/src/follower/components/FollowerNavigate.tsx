
import { useState } from 'react'

interface Props {
  routeId: string | undefined
}

interface Step {
  image: string
  direction: 'straight' | 'left' | 'right' | 'arrive'
  title: string
  landmark: string
  distance: number
}

const demoSteps: Step[] = [
  {
    image:
      'https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=1000',
    direction: 'straight',
    title: 'このまま直進',
    landmark: '前方の大きな交差点を目指してください。',
    distance: 150,
  },
  {
    image:
      'https://images.unsplash.com/photo-1519608487953-e999c86e7455?w=1000',
    direction: 'right',
    title: '右に曲がる',
    landmark: '交差点まで来たら、右に曲がってください。',
    distance: 80,
  },
  {
    image:
      'https://images.unsplash.com/photo-1511818966892-d7d671e672a2?w=1000',
    direction: 'left',
    title: '左に曲がる',
    landmark: '建物の入口を目印に、左に曲がってください。',
    distance: 40,
  },
  {
    image:
      'https://images.unsplash.com/photo-1497366754035-f200968a6e72?w=1000',
    direction: 'arrive',
    title: '会場に到着！',
    landmark: '目的地に到着しました。お疲れさまでした！',
    distance: 0,
  },
]

const arrows: Record<Step['direction'], string> = {
  straight: '↑',
  left: '←',
  right: '→',
  arrive: '✓',
}

export function FollowerNavigate({ routeId }: Props) {
  const [current, setCurrent] = useState(0)
  const step = demoSteps[current]

  const isLast = current === demoSteps.length - 1

  return (
    <main
      style={{
        minHeight: '100vh',
        background: '#f7f7f4',
        color: '#292923',
        padding: '24px 16px',
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      <div style={{ maxWidth: 480, margin: '0 auto' }}>
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 20,
          }}
        >
          <div>
            <p
              style={{
                color: '#047857',
                fontWeight: 800,
                letterSpacing: 2,
                fontSize: 12,
                margin: '0 0 6px',
              }}
            >
              WAYFINDER
            </p>
            <h1 style={{ fontSize: 23, margin: 0 }}>
              会場までの道案内
            </h1>
          </div>

          <span
            style={{
              background: '#fff',
              borderRadius: 20,
              padding: '8px 12px',
              fontSize: 14,
              whiteSpace: 'nowrap',
            }}
          >
            {current + 1} / {demoSteps.length}
          </span>
        </header>

        <div
          style={{
            height: 6,
            background: '#e5e5df',
            borderRadius: 10,
            overflow: 'hidden',
            marginBottom: 16,
          }}
        >
          <div
            style={{
              width: `${((current + 1) / demoSteps.length) * 100}%`,
              height: '100%',
              background: '#047857',
              transition: 'width 0.2s',
            }}
          />
        </div>

        <section
          style={{
            background: '#fff',
            border: '1px solid #e7e5e4',
            borderRadius: 20,
            overflow: 'hidden',
          }}
        >
          <img
            src={step.image}
            alt={`目印の写真 ${current + 1}`}
            style={{
              display: 'block',
              width: '100%',
              height: 260,
              objectFit: 'cover',
              background: '#e7e5e4',
            }}
          />

          <div style={{ padding: 20 }}>
            <div
              style={{
                display: 'flex',
                gap: 16,
                alignItems: 'center',
                marginBottom: 24,
              }}
            >
              <div
                aria-label={step.title}
                style={{
                  flexShrink: 0,
                  width: 76,
                  height: 76,
                  borderRadius: 18,
                  background: '#047857',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 48,
                  fontWeight: 700,
                }}
              >
                {arrows[step.direction]}
              </div>

              <div>
                <p
                  style={{
                    margin: '0 0 6px',
                    fontSize: 13,
                    color: '#78786f',
                  }}
                >
                  {step.direction === 'arrive' ? 'ゴール' : '次の行動'}
                </p>

                <h2 style={{ margin: 0, fontSize: 24 }}>
                  {step.title}
                </h2>

                <p
                  style={{
                    margin: '8px 0 0',
                    fontSize: 14,
                    color: '#57574f',
                  }}
                >
                  {step.distance > 0
                    ? `次の目印まで約 ${step.distance} m`
                    : '目的地です'}
                </p>
              </div>
            </div>

            <div
              style={{
                padding: 16,
                background: '#f7f7f4',
                borderRadius: 12,
                marginBottom: 20,
              }}
            >
              <p
                style={{
                  margin: '0 0 8px',
                  color: '#047857',
                  fontSize: 14,
                  fontWeight: 700,
                }}
              >
                目印
              </p>

              <p style={{ margin: 0, lineHeight: 1.8 }}>
                {step.landmark}
              </p>
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={() =>
                  setCurrent((n) => Math.max(0, n - 1))
                }
                disabled={current === 0}
                style={{
                  flex: 1,
                  padding: '15px 8px',
                  borderRadius: 12,
                  border: '1px solid #d6d3d1',
                  background: '#fff',
                  fontSize: 16,
                  fontWeight: 600,
                  cursor: current === 0 ? 'default' : 'pointer',
                  opacity: current === 0 ? 0.4 : 1,
                }}
              >
                ← 前へ
              </button>

              <button
                onClick={() =>
                  setCurrent((n) =>
                    Math.min(demoSteps.length - 1, n + 1)
                  )
                }
                disabled={isLast}
                style={{
                  flex: 2,
                  padding: '15px 8px',
                  borderRadius: 12,
                  border: 'none',
                  background: '#047857',
                  color: '#fff',
                  fontSize: 16,
                  fontWeight: 700,
                  cursor: isLast ? 'default' : 'pointer',
                  opacity: isLast ? 0.4 : 1,
                }}
              >
                次へ →
              </button>
            </div>
          </div>
        </section>

        <p
          style={{
            marginTop: 16,
            color: '#78786f',
            fontSize: 12,
            textAlign: 'center',
            lineHeight: 1.8,
          }}
        >
          案内 ID：{routeId ?? '未指定'}
          <br />
          写真と目印を確認し、安全に移動してください。
        </p>
      </div>
    </main>
  )
}
