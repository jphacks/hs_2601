import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PhotoAnnotator } from '../annotate'
import { RouteCreateForm } from '../components/RouteCreateForm'
import { useCreateRoute } from '../hooks/useCreateRoute'
import { useDraft } from '../hooks/useCreatorDraft'

/** 命名・出発地・目的地の入力と撮影。写真には描画とメッセージを付けられる。作成受付が通ったら作成中画面へ */
export function RouteCreatePage() {
  const navigate = useNavigate()
  const draft = useDraft()
  const create = useCreateRoute(({ jobId }) => navigate(`/c/new/creating/${jobId}`))
  const [editingId, setEditingId] = useState<string | null>(null)
  const editing = draft.photos.find((p) => p.id === editingId) ?? null

  return (
    <>
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
        onAnnotatePhoto={(photo) => setEditingId(photo.id)}
        onSubmit={() => create.submit(draft)}
        onCancel={() => navigate('/c')}
      />
      {editing && (
        // 元の写真（file）から描き直す。描画済みの画像を元にすると線が二重に焼き込まれるため
        <PhotoAnnotator
          key={editing.id}
          source={editing.file}
          initialCaption={editing.caption}
          onDone={(result) => {
            draft.annotatePhoto(editing.id, result)
            setEditingId(null)
          }}
          onCancel={() => setEditingId(null)}
        />
      )}
    </>
  )
}
