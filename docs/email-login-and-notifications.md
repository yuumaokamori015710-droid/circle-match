# Email login and event notifications

## Authentication

Email sign-in uses Supabase magic links, not locally stored passwords. The same
account can host and participate. A successful link returns to the original
application or event editor. Supabase validates the access token through its
user endpoint; the app requires email_confirmed_at before creating a session.
Google login remains enabled. Service-role and mail keys must stay server-only.

The Supabase browser client uses persistSession=false and autoRefreshToken=false:
only the HttpOnly application cookie persists after token exchange. A local
Supabase session must not silently sign a user back in after logout. Public
headers are personalized at response time (Cache-Control: no-store), including
legacy DB pages. POST /logout validates a session-bound HMAC token, expires that
server session, and clears the cookie. GET /logout only shows confirmation;
other devices remain signed in. Restoring a page from bfcache reloads its header.

Japanese authentication templates are in outputs/email-templates/. In the
dedicated project pxlcrikgkluzmdhuwgds, set Magic link or OTP subject to
"Circle Matchへのログイン" and Confirm sign up to "Circle Matchへの登録確認".
Keep {{ .ConfirmationURL }} unchanged. Both were saved and preview-verified on
2026-09-27. These files are the versioned source; Git deployment does not update
Supabase templates automatically. Do not change another project's templates.

Keep CIRCLEMATCH_EMAIL_AUTH_ENABLED=false until custom SMTP is configured and a
real login email has been received and redeemed.

### Provider setup

1. Create a Resend account and verify the sending domain in its Domains screen.
   Add only the displayed sending DNS records. Preserve website records and
   existing inbound-mail MX records. No paid upgrade without owner approval.
2. Create a domain-restricted, sending-only API key. Enter it directly into the
   hosting dashboards; never commit it or paste it into a task.
3. In the Circle Match dedicated Supabase project, open Authentication > Email >
   SMTP Settings. Set the verified sender, display name Circle Match, host
   smtp.resend.com, port 465, username resend, and the key as password. Keep email
   confirmations enabled.
4. Preserve Google redirect settings. Allow the app's /signin callback with its
   return_to query for supported origins. First-time signup and magic-link email
   templates must use {{ .ConfirmationURL }}. Disable authentication link tracking.
5. Test new/existing email accounts, expired/used links, and returning to an
   application and the event editor. Enable email login only after real delivery
   and link redemption. Provider acceptance does not prove inbox delivery.

## Event email outbox

Render variables, never public browser configuration:

```text
CIRCLEMATCH_SITE_BASE_URL=https://circle-match.jp
CIRCLEMATCH_EMAIL_FROM=Circle Match <notifications@circle-match.jp>
CIRCLEMATCH_RESEND_API_KEY=<sending-only key>
CIRCLEMATCH_EMAIL_NOTIFICATIONS_ENABLED=true
```

Enable only after sender verification. Login mail uses Supabase SMTP; event mail
uses the Resend HTTPS API with the same verified sending domain. No new package
is required. Only transactional notifications are sent, not advertising.

Applications, decisions, cancellations, event changes and messages create an
in-app notification. If email is configured, an immutable payload snapshot is
stored in event_email_outbox in the same transaction. Rolled-back operations
never send. Old unconfigured notifications are NOT bulk mailed on activation.

A single bounded worker processes one job at a time outside the SQLite write
transaction. Jobs survive restarts. A SHA-256-derived idempotency key and fixed
payload prevent duplicate retries in Resend's 24-hour window. There are at most
five attempts. Uncertain jobs older than 23 hours fail for manual inspection
instead of risking duplication. Network/408/409/429/5xx failures retry; other
4xx errors fail immediately. No provider error body or credential is logged.

The UI distinguishes unconfigured, queued, sending, retry, failed and
provider-accepted states. Sent means accepted by Resend, NOT inbox delivery.
No delivery webhook is implemented; inspect bounce/delivery events in Resend.
Supabase and provider quotas apply to authentication emails.

Mail goes only to the stored authenticated account email, not an arbitrary
organizer-contact input. Each email has one recipient. Private message text and
participant rosters are excluded; the notification links to authenticated
my-page. Public notification responses exclude outbox payloads and mail errors.

## Capacity and messages

- Individual/mixed events use people; team events can use teams or people.
- A team application uses one team slot, independently of roster size.
- Application/approval capacity checks run inside a SQLite write transaction.
- Cancellation releases confirmed capacity. Capacity cannot fall below confirmed
  occupancy. Active applications prevent changing participation type, capacity
  unit, acceptance mode, or returning the event to draft.
- Host contact opens a private per-applicant message pane. Cancelled/declined
  applications cannot write messages under the existing permission model.

## Migration and recovery

Startup adds event_email_outbox and its index with IF NOT EXISTS. Existing event,
account, application and notification rows are not rewritten. No destructive
migration is introduced. Before deployment, take a SQLite online backup or a
Render disk snapshot using the existing operational backup procedure.

To stop sending, set CIRCLEMATCH_EMAIL_NOTIFICATIONS_ENABLED=false and redeploy.
In-app notifications continue to work. Keep the outbox table for audit. Do not
mark failures sent or blindly retry uncertain old jobs. Disable email login
separately via its feature flag if SMTP is unavailable. A rollback may leave
the additive table in place; do not overwrite newer data with an old snapshot.

## Verification

```text
node scripts/test_signin.cjs
python scripts/test_account_navigation.py
python scripts/test_event_flow.py
python scripts/test_event_capacity_email.py
```

Tests use temporary SQLite databases and mocked mail requests, not real users.
DNS, credentials and inbox delivery require the separate production test above.

Official references:
- https://supabase.com/docs/guides/auth/auth-email-passwordless
- https://supabase.com/docs/guides/auth/auth-smtp
- https://resend.com/docs/send-with-supabase-smtp
- https://resend.com/docs/dashboard/emails/idempotency-keys
