# Circle Match

全国の大学サークル・部活動情報を、出典付きで管理するためのWebアプリです。

現在はDB整備と管理画面を優先したローカル/初期本番向け構成です。公開DBと個人情報・内部メモDBを分離し、公開APIには代表者情報や内部メモを返さない設計にしています。

## Public Navigation

`/` はスポーツカードを入口にした共通ホームです。競技を選んだ先で「大会・イベント」「サークルDB」「会場予約」を切り替え、競技・地方・都道府県だけをタブ間で引き継ぎます。日付、団体名検索、会場の料金上限などは各画面の条件として扱います。

- `/events`: 大会・イベント一覧。競技未指定でも直接検索できます。
- `/?tab=db&audience=university`: 大学サークルDB。`audience=social` で社会人へ切り替えます。
- `/venues`: 会場一覧。現在の掲載範囲は東京都のテニスコートです。未掲載の競技・地域は「掲載準備中」と表示し、施設一覧を取得しません。

共通条件は `sport` / `region` / `prefecture`、会場専用条件は `v_*` のURLパラメーターに保存します。ホームは全競技・全地域から受付中の公開募集を新着順に最大6件表示します。会場ページはSQLiteへ接続せず、会場のCSS/JSは内容ハッシュでキャッシュを更新します。空き照会・自動予約はこの会場一覧には接続していません。

## Circle Invitations

サークルDB・団体紹介の「交流に招待」から、本人が主催する受付中の公開イベントへの招待、または練習試合・合同練習などの相談を作成できます。作成にはログインが必要です。

招待リンクは30日間有効です。リンクを持つ人は最初の招待内容を閲覧でき、ログインして関係者本人であることを確認した最初の1人が返信できます。その後の会話は作成者と返信者の2アカウントに限定されます。リンクはコピー・LINEで本人が渡す方式で、自動メール送信はありません。返信で団体代表権限やイベント参加枠は付与されません。

`/invitations` とマイページから自分の招待を確認できます。返信・メッセージはアプリ内で通知し、作成者は招待を取り下げられます。招待ページは検索対象外・広告なし・参照元URLを送信しない設定です。起動時に既存DBへ招待用の2テーブルを追加し、既存データは変更しません。

## Run Locally

```powershell
python outputs\circlematch_db_app.py
```

Open:

```text
http://127.0.0.1:8787/
```

Admin:

```text
http://127.0.0.1:8787/admin
```

Initialize only:

```powershell
python outputs\circlematch_db_app.py --init-only
```

## Environment Variables

Copy `.env.example` and set equivalent values in your hosting provider.

```text
HOST=127.0.0.1
PORT=8787
CIRCLEMATCH_SITE_NAME=Circle Match
CIRCLEMATCH_OPERATOR=Circle Match 運営
CIRCLEMATCH_CONTACT_EMAIL=contact@example.com
CIRCLEMATCH_SITE_BASE_URL=http://127.0.0.1:8787
CIRCLEMATCH_ADMIN_USERNAME=admin
CIRCLEMATCH_ADMIN_PASSWORD=
CIRCLEMATCH_DB_PATH=outputs/circlematch.sqlite
CIRCLEMATCH_PUBLIC_SEED_PATH=outputs/public_circles_seed.csv
```

For production, set:

```text
HOST=0.0.0.0
PORT=<provider assigned port>
CIRCLEMATCH_CONTACT_EMAIL=<real contact address>
CIRCLEMATCH_SITE_BASE_URL=<https production URL>
CIRCLEMATCH_ADMIN_USERNAME=<admin user>
CIRCLEMATCH_ADMIN_PASSWORD=<strong password>
CIRCLEMATCH_DB_PATH=<path outside the repository>
CIRCLEMATCH_PUBLIC_SEED_PATH=outputs/public_circles_seed.csv
```

When `HOST` is not local, `CIRCLEMATCH_ADMIN_PASSWORD` is required. This prevents accidentally exposing the admin UI in production.

## Do Not Commit

The following must not be committed to GitHub:

- SQLite DB files such as `outputs/circlematch.sqlite`
- `.env`
- API keys, DB credentials, mail service keys
- representative names, university emails, inquiry bodies
- logs
- scraped PDFs or reviewed source files that may contain third-party content

`.gitignore` is configured for these files, but check `git status` before every commit.

## Legal Pages

The app exposes these pages:

- `/privacy`
- `/terms`
- `/about-data`
- `/contact`

Before AdSense application or public launch, replace `contact@example.com` and `Circle Match 運営` with real operator/contact information.

## Privacy Architecture

Public API:

- `GET /api/circles` returns public facts only.
- It does not return `owner_notes`, `sns_url`, `claimant_email`, representative names, or internal notes.
- `/admin` and admin APIs require Basic authentication when `CIRCLEMATCH_ADMIN_PASSWORD` is set.

Database separation:

- `circles`: public circle facts
- `circle_private_profiles`: internal notes and non-public supplemental info
- `circle_claims`: representative claim and university email verification info
- `audit_logs`: sensitive fields are redacted

## Production Readiness

See:

```text
outputs/production-privacy-security-checklist.md
```

Recommended next production steps:

1. Deploy with `render.yaml` or equivalent PaaS settings.
2. Set real contact/admin environment variables.
3. Configure HTTPS and a custom domain.
4. Move from SQLite to managed PostgreSQL before heavier usage.
5. Add backups, monitoring, and incident response procedures.

## Supabase Auth

Set these values in Render environment variables. Do not commit the actual values.

```text
CIRCLEMATCH_SUPABASE_URL=<Supabase project URL>
CIRCLEMATCH_SUPABASE_ANON_KEY=<Supabase anon public key>
CIRCLEMATCH_SESSION_SECRET=<random long secret>
```

Enable Google as an Auth provider in Supabase, then add these redirect URLs in Supabase Auth settings:

```text
https://circle-match.onrender.com/signin
```

After the custom domain HTTPS is ready, also add:

```text
https://circle-match.jp/signin
```
