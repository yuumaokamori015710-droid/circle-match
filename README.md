# Circle Match

全国の大学サークル・部活動情報を、出典付きで管理するためのWebアプリです。

現在はDB整備と管理画面を優先したローカル/初期本番向け構成です。公開DBと個人情報・内部メモDBを分離し、公開APIには代表者情報や内部メモを返さない設計にしています。

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

## Google OAuth

Set these values in Render environment variables. Do not commit the actual values.

```text
CIRCLEMATCH_GOOGLE_CLIENT_ID=<Google OAuth client ID>
CIRCLEMATCH_GOOGLE_CLIENT_SECRET=<Google OAuth client secret>
CIRCLEMATCH_SESSION_SECRET=<random long secret>
```

Google Cloud Console OAuth redirect URI:

```text
https://circle-match.onrender.com/auth/google/callback
```

After the custom domain HTTPS is ready, also add:

```text
https://circle-match.jp/auth/google/callback
```
