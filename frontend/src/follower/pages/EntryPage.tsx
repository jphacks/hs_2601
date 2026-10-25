import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_MODE } from '../../shared/api/endpoints'
import { SAMPLE_ROUTE_ID } from '../../shared/api/fixtureApi'
import { EntryForm } from '../components/EntryForm'

/** /r の入口。ID を入力して /r/:id へ遷移するだけ */
export function EntryPage() {
  const navigate = useNavigate()
  const [routeId, setRouteId] = useState('')
  const open = (id: string) => navigate(`/r/${encodeURIComponent(id.trim())}`)

  return (
    <main className="box-border min-h-screen bg-canvas px-4 pt-5 pb-8 text-ink">
      <div className="mx-auto max-w-[480px]">
        <EntryForm
          routeId={routeId}
          sampleRouteId={API_MODE === 'fixture' ? SAMPLE_ROUTE_ID : null}
          onRouteIdChange={setRouteId}
          onOpen={() => open(routeId)}
          onOpenSample={() => open(SAMPLE_ROUTE_ID)}
        />
      </div>
    </main>
  )
}
