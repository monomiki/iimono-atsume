# いいものあつめ AIデイリー収集

Raindrop.ioに保存済みのブックマークを分析し、X、Instagram、Web/RSSなどから新しい候補を集め、推薦スコアと理由を付けてRaindropへ保存するためのパイプラインです。

APIキーがない状態でも`DRY_RUN=true`でモック候補を使って日次処理が最後まで動きます。

## 設計

- `src/raindrop/`: Raindrop.io REST APIクライアント。コレクションIDは固定せず、root/child collection一覧からタイトルで解決します。
- `src/preference/`: 既存ブックマークからカテゴリ別の嗜好プロファイルを生成します。保存件数は平方根で正規化し、大カテゴリの過剰優先を抑えます。
- `src/collectors/`: X、Instagram、Web/RSSを独立アダプターとして扱います。未設定APIはモック/公開フィードへフォールバックします。
- `src/recommendation/`: URL正規化、投稿IDベース重複判定、分類、スコアリング、作者・カテゴリ偏り抑制を行います。
- `src/storage/`: SQLiteにフィードバック、保存済み候補、日次実行結果を保存します。
- `src/reporting/`: 日本語Markdownレポートを`reports/YYYY-MM-DD.md`へ出力します。

## セットアップ

Python 3.12以上を推奨します。この環境では標準ライブラリだけでもDRY_RUNが動くように実装しています。

```bash
cp .env.example .env
python -m src.cli daily-run --dry-run
```

推奨依存を入れる場合:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## 環境変数

`.env`に設定します。秘密情報はGitへコミットしないでください。

```env
RAINDROP_ACCESS_TOKEN=
X_BEARER_TOKEN=
INSTAGRAM_ACCESS_TOKEN=
OPENAI_API_KEY=
DATABASE_URL=sqlite:///data/recommendations.db
TIMEZONE=Asia/Tokyo
DAILY_RUN_TIME=07:00
MAX_DAILY_ITEMS=100
DRY_RUN=true
```

`DRY_RUN=true`ではRaindrop.ioへ保存せず、保存予定候補とレポートのみ生成します。

## CLI

```bash
python -m src.cli analyze-library
python -m src.cli build-profile
python -m src.cli collect --source x
python -m src.cli collect --source instagram
python -m src.cli collect --source web
python -m src.cli recommend
python -m src.cli daily-run
python -m src.cli daily-run --dry-run
python -m src.cli daily-run --date 2026-07-22
python -m src.cli feedback-sync
python -m src.cli show-profile
```

## Raindrop保存先

認証情報がある場合、次のコレクションを作成または再利用します。

- `🤖 AIデイリー収集`
- `📥 未確認`
- `⭐ 高精度`
- `🧭 新規発見`
- `🚫 興味なし`

初期運用では原則`📥 未確認`へ保存します。高スコアかつ信頼性がある候補は`⭐ 高精度`、探索枠は`🧭 新規発見`です。

## テスト

外部APIは使わず、モックデータで実行します。

```bash
python -m unittest discover -s tests
```

`pytest`をインストールしている場合:

```bash
pytest
```

## 現時点の情報源

- X: APIトークン未設定時はモック候補。`X_BEARER_TOKEN`設定後に公式API実装を拡張する入口があります。
- Instagram: API権限がない場合は手動指定/モック候補で継続します。
- Web/RSS: `config/sources.yaml`にRSS URLを追加できます。取得失敗しても全体処理は継続します。

## 静的まとめサイト

日次処理はMarkdownレポートに加えて、`public/`に静的サイトを生成します。

```text
public/
├── index.html
├── daily/
│   ├── index.html
│   └── YYYY-MM-DD/index.html
├── favorites/index.html
├── assets/css/main.css
├── assets/js/favorites.js
├── data/daily/YYYY-MM-DD.json
├── data/items/*.json
├── feed.xml
├── sitemap.xml
└── robots.txt
```

独自ドメインは`.env`またはGitHub Actions variablesで設定します。国際化ドメインを使う場合は、Unicode表記とPunycode表記のどちらでもホスティング側が求める値を設定してください。

```env
PUBLIC_SITE_DOMAIN=イキモノ.コム
PUBLIC_SITE_BASE_URL=https://イキモノ.コム
PUBLIC_SITE_PATH_PREFIX=/daily
```

既存サイトを壊したくない場合は、`https://イキモノ.コム/daily/`のようなサブディレクトリ、または`https://daily.イキモノ.コム/`のようなサブドメインを使います。

ローカルプレビュー:

```bash
python -m src.cli daily-run --dry-run
python -m http.server 8000 -d public
```

## GitHub Pages

既存リポジトリがある場合はそのリポジトリを使い、ない場合はGitHubで新規作成します。GitHub PagesはActionsから公開する設定にしてください。

1. GitHubのリポジトリ設定でPagesを開く
2. Sourceを`GitHub Actions`にする
3. 独自ドメインを使う場合はPages画面でCustom domainを設定する
4. DNSはGitHub Pagesまたは利用中DNSサービスが提示する値を確認して設定する
5. `イキモノ.コム`直下で既存サイトがある場合はサブドメインかサブディレクトリを選ぶ

日次GitHub Actionsは[.github/workflows/daily-collection.yml](.github/workflows/daily-collection.yml)にあります。日本時間7:00はUTC 22:00なので、cronは`0 22 * * *`です。日付判定は`Asia/Tokyo`で行います。

GitHub Actions Secrets / Variablesに設定する主な値:

```text
Secrets:
RAINDROP_ACCESS_TOKEN
X_BEARER_TOKEN
INSTAGRAM_ACCESS_TOKEN
DISCORD_DAILY_WEBHOOK_URL

Variables:
PUBLIC_SITE_DOMAIN
PUBLIC_SITE_BASE_URL
FAVORITE_API_BASE_URL
FAVORITE_ALLOWED_ORIGIN
```

## Discord連携

日次まとめは`日々のまとめtest`チャンネルへ投稿します。本番ではチャンネル名ではなくIDかWebhook URLを使います。FavoriteはDiscordへ転送せず、サイト内の絞り込み・並び替え用タグとして使います。

チャンネルIDの取得:

1. Discordで開発者モードを有効化する
2. 対象チャンネルを右クリックする
3. `IDをコピー`を選ぶ
4. `DISCORD_DAILY_CHANNEL_ID`に設定する

Botを使う場合はDiscord Developer PortalでBotを作成し、最小権限として`View Channel`、`Send Messages`、`Embed Links`、必要に応じて`Read Message History`を付けます。Webhookを使う場合は、日次まとめ用Webhook URLをSecretsに保存します。

同じ日付の日次通知はSQLiteの`discord_notifications`テーブルで重複防止します。標準では既存通知があれば再投稿しません。

## Favorite API

公開サイトは完全な静的HTMLです。Favoriteはブラウザの`localStorage`へタグとして保存され、FavoriteフィルターとFavorite優先ソートに使われます。必要に応じて、`favorite-api/`のCloudflare Workers雛形でサーバー側保存もできます。

```text
GET /api/favorites
GET /api/favorites/:itemId
POST /api/favorites
DELETE /api/favorites/:itemId
```

Favorite APIはブラウザから送られたタイトルや本文を信用せず、`item_id`から公開済み`data/items/*.json`を取得して検証します。認証は本番必須で、初期実装は共有パスコードを`Authorization: Bearer ...`または認証Cookieで確認します。

Cloudflare Workersの設定例:

```bash
cd favorite-api
npm install
npm test
npx wrangler kv namespace create FAVORITES
npx wrangler secret put FAVORITE_API_SECRET
npx wrangler deploy
```

`wrangler.toml`の`PUBLIC_DATA_BASE_URL`、`FAVORITE_ALLOWED_ORIGIN`、KV namespace IDは実際の環境に合わせて設定します。FavoriteのDiscord転送は行いません。

```bash
python -m src.cli sync-web-favorites
```

Favoriteの重複防止には、正規化URLまたはSNS投稿ID由来のキーを使います。Favoriteは`web_favorite`としてフィードバックに記録され、次回推薦の加点に使われます。

## 追加CLI

```bash
python -m src.cli build-site
python -m src.cli build-site --date 2026-07-22
python -m src.cli deploy-site
python -m src.cli notify-discord --date 2026-07-22
python -m src.cli sync-web-favorites
```

## 初回実行

```bash
cp .env.example .env
python -m src.cli daily-run --dry-run
python -m src.cli show-profile
```

Raindropへ実保存する場合は`.env`に`RAINDROP_ACCESS_TOKEN`を設定し、`DRY_RUN=false`にします。

初回デプロイは、GitHub PagesとSecretsを設定したあとGitHub Actionsの`Daily Collection`を手動実行するのが安全です。ローカルから実行する場合は、`DRY_RUN=false`、GitHub remote、Discord webhook、公開URLを設定してから`python -m src.cli daily-run`を実行します。
