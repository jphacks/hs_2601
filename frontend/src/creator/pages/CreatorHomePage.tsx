import { CreatorHome } from '../components/CreatorHome'
import { CreatorLayout } from '../components/CreatorLayout'
import { RouteCreateForm } from '../components/RouteCreateForm'
import { RouteDetail } from '../components/RouteDetail'
import { RouteLoading } from '../components/RouteLoading'
import { RoutePublishList } from '../components/RoutePublishList'
import { RoutePublished } from '../components/RoutePublished'
import { useCreatorFlow } from '../hooks/useCreatorFlow'

/** hooks と components を繋ぐだけ。ロジック・見た目はここに書かない */
export function CreatorHomePage() {
  const flow = useCreatorFlow()
  const goHome = () => flow.setScreen('home')

  return (
    <CreatorLayout showHomeLink={flow.screen !== 'home'} onHome={goHome}>
      {flow.screen === 'home' && (
        <CreatorHome
          onCreate={() => flow.setScreen('create')}
          onRoutes={() => flow.setScreen('routes')}
        />
      )}
      {flow.screen === 'create' && (
        <RouteCreateForm
          start={flow.start}
          goal={flow.goal}
          photos={flow.photos}
          onStartChange={flow.setStart}
          onGoalChange={flow.setGoal}
          onAddPhotos={flow.addPhotos}
          onRemovePhoto={flow.removePhoto}
          onSubmit={flow.createRoute}
          onCancel={goHome}
        />
      )}
      {flow.screen === 'loading' && <RouteLoading />}
      {flow.screen === 'detail' && flow.activeRoute && (
        <RouteDetail
          route={flow.activeRoute}
          photos={flow.photos}
          onPublish={() => flow.setScreen('routes')}
          onEdit={() => flow.setScreen('create')}
        />
      )}
      {flow.screen === 'routes' && (
        <RoutePublishList
          routes={flow.routes}
          selected={flow.selected}
          onToggle={flow.toggleSelected}
          onDetail={flow.openDetail}
          onPublish={flow.publishRoutes}
        />
      )}
      {flow.screen === 'published' && (
        <RoutePublished
          routes={flow.routes.filter((r) => flow.selected.includes(r.id))}
          onHome={goHome}
        />
      )}
    </CreatorLayout>
  )
}
