# Guest Entry Follow-up, 2026-11-11

## Observed Issue

The applicant's screenshot and URL showed the member sign-in page with a return
destination of the Komazawa event's `/apply` route. Before this change, anonymous
GETs to the event's `/guest` endpoint already returned the email form with HTTP
200. The preceding click cannot be reconstructed from the screenshot alone.

Two confirmed navigation problems made this confusing: anonymous `/apply` links
returned to the detail-page choices rather than the guest form, and the member
sign-in page mentioned guest admission without linking to the same event's
guest entry. A regression test failed on that missing exit before the fix.

## Changes

- Anonymous eligible `/apply` requests redirect directly to that event's guest
  entry. The explicitly labeled member sign-in link remains available.
- A member sign-in page for an open, offline-paid/free event includes a prominent
  same-event guest link, independently of the member authentication SDK.
- The guest entry requests the representative's name and email. The bounded name
  is stored with the expiring proof and prefilled only after email verification.
- Old email-only proofs remain redeemable. Event-scoped cookies, one-use proofs,
  expiry, origin checks, duplicate protection, capacity, payments and conditions
  acceptance are unchanged. Hosting and online-payment gates remain member-only.
- No database schema, environment setting, pricing, event record, or external
  notification destination is changed.

## Local Verification

- `python -X utf8 -B -m unittest discover -s scripts -p test_event_guests.py`:
  14 passed, including regression, name escaping, no premature application,
  no member session, legacy proofs and ineligible-event checks.
- `python -X utf8 -B -m unittest discover -s scripts -p 'test_event*.py'`:
  130 passed, including the 14 guest tests.
- `python -X utf8 -B -m unittest discover -s scripts -p 'test_account*.py'`:
  3 passed.
- Regular Chrome, disposable loopback fixture with mocked mail: sign-in guest
  exit, name/email entry, mail verification, bank-transfer choice, review and
  submission reached the guest receipt without signing into a member account.
- 390 x 844 mobile and 1440 x 1000 desktop views checked. Desktop document width
  equals viewport width; name/email fields are visible. Temporary viewport and
  preview server were restored/stopped after verification.
- No production application, test email, charge, transfer, or real agreement was
  submitted during testing.

## Production Acceptance

After the existing service auto-deploys this commit, confirm its Live SHA and
read-only GETs for the real event, its anonymous `/apply` redirect, its `/guest`
form and its member sign-in guest exit. Do not submit a real test application or
send a real verification email as part of this release check.
