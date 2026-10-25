import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_MODE } from '../../shared/api/endpoints'
import { SAMPLE_ROUTE_ID } from '../../shared/api/fixtureApi'
import { EntryForm } from '../components/EntryForm'
import { QrScanner } from '../components/QrScanner'
import { useQrScanner } from '../hooks/useQrScanner'
import { routeIdFromQr } from '../logic/qrPayload'

/** /r の入口。QR 読み取りか ID 入力で /r/:id へ遷移するだけ */
export function EntryPage() {
  const navigate = useNavigate()
  const [routeId, setRouteId] = useState('')
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)

  const open = useCallback(
    (id: string) => navigate(`/r/${encodeURIComponent(id.trim())}`),
    [navigate],
  )

  const onDetected = useCallback(
    (text: string) => {
      const id = routeIdFromQr(text)
      setScanning(false)
      if (id) {
        open(id)
      } else {
        setScanError('この QR コードは道案内のものではありません')
      }
    },
    [open],
  )

  const scanner = useQrScanner(scanning, onDetected)

  return (
    <main className="box-border min-h-screen bg-canvas px-4 pt-5 pb-8 text-ink">
      <div className="mx-auto max-w-[480px]">
        {scanning ? (
          <QrScanner videoRef={scanner.videoRef} error={scanner.error} onCancel={() => setScanning(false)} />
        ) : (
          <EntryForm
            routeId={routeId}
            sampleRouteId={API_MODE === 'fixture' ? SAMPLE_ROUTE_ID : null}
            error={scanError}
            onRouteIdChange={setRouteId}
            onOpen={() => open(routeId)}
            onOpenSample={() => open(SAMPLE_ROUTE_ID)}
            onScanQr={() => {
              setScanError(null)
              setScanning(true)
            }}
          />
        )}
      </div>
    </main>
  )
}
