# Offline Payment Choices

Date: 2026-10-28. Baseline: `1afdf0c`.

## Behavior

- Hosts can offer on-site payment, bank transfer, or both. With both, each paid applicant must explicitly select a method before reviewing and submitting. This applies to both individual and team admission.
- Existing single-method clients can omit the choice. The server rejects unavailable methods and calculates the fee from the selected admission tariff, not client-supplied amounts. A free tariff requires no payment choice.
- The selected method is retained in the application, confirmation, host management and acceptance notification. Cash applicants do not receive bank account information. Bank information remains private until the existing final attendance confirmation and is not returned in public event JSON.
- Once applications are pending/confirmed, changing the available payment methods is rejected. Existing payment and announcement locks remain in force. No owner permission checks are bypassed.
- An expired bank transfer deadline blocks bank admissions/attendance confirmation but does not close the cash option. Existing attendance/application deadlines still apply to both.
- Capacity remains optional. Mixed admissions count actual people, but team pricing is once per team, not per team member.

## Storage and Recovery

Startup adds only missing columns, in an immediate transaction, after a SQLite sibling backup named `*.pre-payment-choices-<timestamp>.sqlite`:

```text
event_posts.allow_on_site_payment INTEGER NOT NULL DEFAULT 0 CHECK (... IN (0,1))
event_applications.selected_payment_method TEXT CHECK (... IN ('free','on_site','bank_transfer','online'))
```

Mixed offline payment is stored as `payment_method='bank_transfer'` and `allow_on_site_payment=1`. The host form uses the virtual option `on_site_or_bank_transfer`. Existing event enums are not rebuilt. Legacy application selections remain NULL and use the event's original method. Existing IDs, rows, indexes and foreign keys are preserved. No hosting environment, service plan, online payment activation or provider credentials are changed.

Prefer a forward fix. An old binary cannot interpret cash selections in mixed-method events; retain this support in any code rollback. Do not automatically restore the pre-migration backup over newer applications/payments. A coordinated database recovery requires a fresh snapshot and reconciliation of all writes since the backup.

## Requested Operator Correction

The service operator explicitly requested correcting the existing user-created Komazawa listing, rather than signing in as its organizer. `repair_requested_komazawa_admission()` is startup-only and targets exactly `event_user_supabase_fe23d660_0d10_49cc_ae6_f42c6bd8fd`. It is not an HTTP endpoint or an alternate organizer login.

It requires the original published individual JPY 2,500 / on-site / unlimited / unannounced state, no application rows (including cancelled ones), no protected payments, and no prior `komazawa_admission_20261028` audit marker. It backs up the database, rechecks under an immediate write lock, and changes only the participation/pricing/payment settings plus `updated_at`: both admission types, individual JPY 2,500, team JPY 15,000, both offline payment methods. The compatibility `fee_amount` becomes the maximum tariff, JPY 15,000.

The audit records `actor=operator_release`, before/after values and the reason. Organizer ownership, event date/venue/content, unlimited capacity, and minimum formation count five remain unchanged. Any unexpected state or existing application causes a skip, not a forced change. No email is sent by the correction. Startup logs and the public event must be checked after deployment to establish whether it actually applied.

Actual bank details are neither invented nor copied from another account. The real organizer registers them in the existing private announcement flow when the event is ready. There is no real transfer or payment in this release verification.

## Verification

- Full unittest discovery: 506 tests; 31 dependency skips under the default Python and one Windows localhost `WinError 10053` interruption in an existing invitation HTTP test. No assertion failures.
- Recheck with the existing payments venv: all 55 selected tests passed, including the dependency-dependent crawler/Stripe tests, interrupted HTTP test and all 13 new payment-choice tests.
- Standalone `scripts/test_event_flow.py`: passed after the final changes.
- Sharing/group regression module: all nine tests passed (including the JavaScript harness with its required source input); standalone sign-in harness passed.
- New tests cover all four admission/payment combinations, correct tariff totals, unknown-method rejection, legacy clients, a free tariff, private bank details, expired bank deadlines, host form/persistence, ownership, application locks, additive migration/idempotence, and scoped correction guards/audit.
- Isolated browser fixture: host saved both prices and both methods with no capacity; individual/cash, individual/bank, team/cash and team/bank all reached matching receipts. Eleven-person teams remained JPY 15,000. Desktop 1440px and mobile 390px showed no horizontal overflow; no console warnings/errors were observed.
- Private evidence is under `work/komazawa-application-audit-20261028/`. The temporary loopback fixture is not a production endpoint. Real user applications, authentication, mail delivery and transfers were not submitted during testing.

The matching Render Live deploy and read-only production verification are recorded separately in the private release evidence after deployment.
