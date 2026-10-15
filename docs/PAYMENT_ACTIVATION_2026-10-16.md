# Online payment activation

## Confirmed production state

- Inspected the Circle Match Stripe account and existing Render service on 2026-10-16 JST.
- Render was live at `ba48cca` on `main`; the gated Checkout/Connect implementation was already deployed.
- Render Environment did not contain any `CIRCLEMATCH_STRIPE_*` variables or `CIRCLEMATCH_ONLINE_PAYMENTS_ENABLED` (including expanded rows). No linked environment groups were present.
- Stripe showed payments paused: the Japan security checklist was overdue. A representative identity-document task was also pending. Do not infer approval from the earlier account-registration completion.
- Opened the security checklist for the account owner. No assertions, identity documents, agreements, charges, transfers, refunds or credentials were submitted.

## This change

- Require both separate webhook signing secrets, a matching API key/mode and a valid site origin before new payment operations.
- Check the platform's `charges_enabled` before creating Checkout or returning an open payment URL. Account identity/country/currency checks remain in place.
- Preserve reconciliation, webhook handling and refund operations while new payments are disabled or platform charges are paused.
- Add a protected connection-check action to `/admin/payments`, using existing admin authentication, Origin, CSRF and rate limits. It retrieves only the platform account and returns whitelisted booleans, never keys, personal data or raw provider exceptions.
- Add `scripts/check_payment_connection.py`: no DB access or migration, no Stripe mutation. `--stripe` opts into the same read-only account check. Exit 2 means incomplete checks, not payment success.
- These checks do not prove Connect availability, webhook delivery or successful Checkout/3DS/refunds. Those require actual isolated Stripe tests.

## Remaining activation order

1. Account owner completes truthful security-checklist answers and the identity-document task in Stripe. Do not select security controls that have not been verified.
2. Confirm Stripe's payments are enabled and Connect platform activation/business model is accepted.
3. Securely connect test credentials and two webhook endpoints to an isolated test environment. Follow `ONLINE_PAYMENTS.md` for event subscriptions and pinned API version.
4. Verify hosted onboarding, card success/3DS/decline, application-fee/destination reconciliation, duplicate/late webhooks and full refund with transfer reversal. Mock test success does not replace these tests.
5. Confirm disclosures/terms, organizer identity, refund resources and monitoring. Store live credentials and signing secrets only in Render's secret settings, with explicit approval for credential provisioning. Keep the new-payment switch off until this is done.
6. Enable live mode only after the checks pass. Each paid organizer must finish their own Stripe hosted onboarding. Existing on-site/bank-transfer events are not silently converted to online payment.
7. The user performs the first authorized real Checkout; verify its signed webhook and ledger allocation afterwards. Do not self-charge with a fake purchase to claim success.

No real payment can currently be claimed as verified, and no live-payment switch was enabled by this change.

## Automated verification

- Payment flow: 45 tests passed (FakeStripe and disposable SQLite).
- Existing event regression: 62 tests passed.
- Official Stripe SDK contract: 3 tests passed (in-memory transport, no Stripe API requests).
- Python compilation and `git diff --check` passed.
- Connection CLI with no credentials reported missing settings and did not contact Stripe or create a DB.
- Operated the protected connection-check button in the loopback simulator; the mocked API result updated in place. At widths 1440 and 390, document scroll widths were 1425 and 375 respectively: no horizontal overflow. Inspected screenshots at both sizes.
- The first sandbox run could not access local sockets; the successful rerun explicitly allowed local HTTP testing. Existing mocked mail-error cleanup warnings remain in the event suite.

These 110 passing tests are not live card processing, real webhook delivery or bank-payout verification.

## Official references

- [Stripe Account: charges_enabled / payouts_enabled](https://docs.stripe.com/api/accounts/object)
- [Japan security checklist](https://support.stripe.com/questions/japan-security-checklist)
- [Destination charges](https://docs.stripe.com/connect/destination-charges)
- [Japan Connect pricing](https://stripe.com/jp/connect/pricing)
