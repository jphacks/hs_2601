import { useNavigate } from 'react-router-dom'
import { RouteCreateForm } from '../components/RouteCreateForm'
import { useCreateRoute } from '../hooks/useCreateRoute'
import { useDraft } from '../hooks/useCreatorDraft'

/** 命名・出発地・目的地の入力と撮影。作成受付が通ったら作成中画面へ */
export function RouteCreatePage() {
  const navigate = useNavigate()
  const draft = useDraft()
  const create = useCreateRoute(({ jobId }) => navigate(`/c/new/creating/${jobId}`))

  return (
    <RouteCreateForm
      name={draft.name}
      origin={draft.origin}
      destination={draft.destination}
      photos={draft.photos}
      error={create.error}
      phase={create.phase}
      onNameChange={draft.setName}
      onOriginChange={draft.setOrigin}
      onDestinationChange={draft.setDestination}
      onAddPhotos={draft.addPhotos}
      onRemovePhoto={draft.removePhoto}
      onRetryLocation={draft.retryLocation}
      onSubmit={() => create.submit(draft)}
      onCancel={() => navigate('/c')}
    />
  )
}
