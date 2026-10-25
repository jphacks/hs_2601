# Cloudflare Tunnel で開発 PC をスマホから開く

カメラ・位置情報・QR の動作確認は HTTPS と実機が要る。Cloudflare Tunnel（quick tunnel）を使うと、
アカウント登録なしで開発 PC のポートに一時的な `https://xxxx.trycloudflare.com` が付く。

- 無料。アカウント不要。
- WSL の中で動かすので、Windows 側のポート転送やファイアウォール設定は不要。
- 同じ Wi-Fi でなくても開ける（外出先で実際に歩きながら確認できる）。
- URL は `cloudflared` を起動し直すたびに変わる。QR や `.env` に書いた URL はそのたびに更新する。

## 1. インストール（初回のみ、WSL 内）

```bash
mkdir -p ~/.local/bin
curl -L -o ~/.local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x ~/.local/bin/cloudflared
cloudflared --version        # 出なければ: export PATH="$HOME/.local/bin:$PATH" を ~/.bashrc に追加
```

## 2. 使い方の基本

公開したいサーバーを起動した状態で、別の端末で次を実行する。

```bash
cloudflared tunnel --url http://localhost:<ポート>
```

数秒後にログに次のような行が出る。この URL をスマホで開く。

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://holds-llp-restoration-newly.trycloudflare.com                                     |
+--------------------------------------------------------------------------------------------+
```

- 止めるときは Ctrl+C。止めると URL は無効になる。
- 2 つのポート（フロント 5173 とバックエンド 8000）を同時に公開するなら、端末を 2 つ開いてそれぞれ実行する。URL は別々になる。

## 3. バックエンドだけで QR → 写真列を確認する

API サーバーが `/r/<id>` で写真列の HTML を返すので、フロント無しで一連の流れを試せる。

```bash
# 端末 A: API サーバー
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 端末 B: 公開 URL を発行
cloudflared tunnel --url http://localhost:8000

# 端末 C: 発行された URL を backend/.env の PUBLIC_BASE_URL に書き、QR を作り直す
#   PUBLIC_BASE_URL=https://xxxx.trycloudflare.com
cd backend && source .venv/bin/activate
python -m scripts.publish --from-route ./out/cases/5 --name "四天王寺→てんしば"
explorer.exe out/cases/5/qr.png
```

スマホの標準カメラで `qr.png` を読むと `https://xxxx.trycloudflare.com/r/<id>` が開き、写真列が表示される。
PC 側の確認は `curl -s http://localhost:8000/r/<id> | grep -c "<img"` が地点数と一致すれば OK。

## 4. フロントエンド（Vite）をスマホで開く

```bash
# 端末 A: フロント
cd frontend && npm run dev          # 5173 で起動

# 端末 B: 公開 URL を発行
cloudflared tunnel --url http://localhost:5173
```

Vite は知らないホスト名からのアクセスを拒否する（`Blocked request. This host ("xxxx.trycloudflare.com") is not allowed.`）。
`frontend/vite.config.ts` の `server` に次を足す。

```ts
server: {
  host: true,
  port: 5173,
  allowedHosts: ['.trycloudflare.com'],
},
```

フロントからバックエンドも呼ぶなら、バックエンドにも別のトンネルを張り、その URL を `frontend/.env.local` に書く。

```bash
# 端末 C: バックエンド公開
cloudflared tunnel --url http://localhost:8000
```

```
# frontend/.env.local
VITE_API_MODE=server
VITE_API_BASE_URL=https://yyyy.trycloudflare.com
```

`.env.local` を変えたら `npm run dev` を起動し直す。バックエンドの CORS は全オリジン許可なので追加設定は不要。

## 5. よくあるつまずき

| 症状 | 原因と対処 |
|---|---|
| スマホで開くと `Blocked request` | Vite の `allowedHosts` 未設定（4 を参照） |
| QR を読んでも開かない、古い写真列が出る | `cloudflared` を再起動して URL が変わった。`.env` の `PUBLIC_BASE_URL` を直し、QR を作り直す |
| `502 Bad Gateway` | 公開先のサーバーが起動していない、またはポート番号違い |
| 位置情報・カメラが使えない | `http://192.168.x.x:5173` など HTTPS でない URL で開いている。トンネルの `https://` URL を使う |
| しばらくして繋がらなくなる | quick tunnel は長時間放置すると切れることがある。`cloudflared` を起動し直す（URL は変わる） |

## 6. 固定 URL が欲しくなったら

quick tunnel は URL が毎回変わる。デモ当日に同じ URL を使い続けたい場合は、Cloudflare アカウントを作り
`cloudflared tunnel login` → `cloudflared tunnel create <name>` で名前付きトンネルを作ると、自分のドメインに固定できる。
ハッカソン中は quick tunnel で十分なので、必要になったときに検討する。
