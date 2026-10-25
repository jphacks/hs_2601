# creator/pages（接続層）

URL ごとの画面。hooks の戻り値を components に渡すだけで、ロジック・見た目はここに書かない。

| パス | ページ | 表示する component |
|---|---|---|
| `/c` | `HomePage` | CreatorHome |
| `/c/new` | `RouteCreatePage` | RouteCreateForm（入力と撮影を 1 画面に） |
| `/c/new/creating/:jobId` | `CreatingPage` | RouteLoading |
| `/c/routes` | `RouteListPage` | RoutePublishList |
| `/c/routes/:routeId` | `ResultPage` | RouteDetail（作成結果の確認と道の詳細を共通化） |
| `/c/published` | `PublishedPage` | RoutePublished |

- `CreatorRoot.tsx` は `/c` 配下のレイアウト。作成中の入力（draft）をここで持ち、Outlet context で配下に渡す。
- docs では入力と撮影を別ページにしているが、現状の UI を保つため 1 画面にしている。
