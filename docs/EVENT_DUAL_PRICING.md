# Individual and Team Prices in One Event

Date: 2026-10-17. Baseline: `04e7c70`.

## Behavior

- Organizers select individual, team or both. Both exposes two plain-text JPY inputs, with comma/full-width digit normalization.
- Individual admission charges its per-person rate times the submitted headcount. Team admission charges one team rate, independently of its headcount.
- Both rates are required to publish a new mixed event. Drafts can be incomplete. Zero is a real free rate, not an unknown value. If both rates are zero the payment method becomes free; otherwise the selected on-site/bank/online method remains applicable to paid admissions.
- Participants select their admission type before confirmation. Unit price, confirmation total, result, host management, bank guidance and acceptance notifications use the selected tariff.
- Detail/list HTML and client-rendered cards expose both rates. Sharing uses the same rates; X uses a shorter price description to retain both within its post budget.
- For mixed admission, capacity and minimum formation threshold count actual people, including all team members. A team of 11 and an individual booking for two consume 13 people, not three units. Existing team-only events retain team-count semantics.
- Rate changes are rejected once pending/confirmed admissions exist, after an announcement, or where payment guards prohibit a financial change. Other users cannot edit event settings or read private admission details.
- Break-even forecasts for mixed admission sum confirmed individual and team fees. Capacity times a single unit price is not a valid full-capacity forecast for mixed tariffs; the UI does not invent one.

## Storage and Compatibility

Four nullable columns are added to `event_posts`:

```text
individual_fee_amount
team_fee_amount
individual_online_price_input
team_online_price_input
```

Published mixed tariffs have both amount columns set. The online input columns retain the organizer's net/gross basis while amount columns store the actual published gross unit amounts. The existing online pricing mode is shared by both tariffs.

`circlematch_event_pricing.py` owns tariff selection and total calculation across views, notifications and Checkout. For separate-price events, the legacy `fee_amount` compatibility field is the maximum tariff; it is not a participant's unit price. Billing must select the application tariff, never multiply that compatibility field by headcount.

Existing rows remain null in the new columns. Their original `fee_amount` and `fee_unit` are not reinterpreted or backfilled. Existing shared-price mixed events can retain their old pricing while editing; an explicit checkbox switches to separate rates, subject to the application/payment locks. New events, copies and transitions from single-type to mixed admission require explicit separate rates.

The 2026-10-17 release did not automatically rewrite the existing Komazawa listing from its free-text description. The explicitly requested, guarded operator correction in the 2026-10-28 release is documented in [EVENT_PAYMENT_CHOICES.md](EVENT_PAYMENT_CHOICES.md). Normal organizer ownership checks remain unchanged; protected admissions are never retroactively repriced.

## Migration and Recovery

- Startup checks the schema; migration is idempotent and adds only missing columns.
- Before any ALTER, SQLite writes a sibling `*.pre-dual-pricing-<timestamp>.sqlite` backup and closes its handle.
- All ALTERs run in one immediate transaction; an exception rolls them back and propagates. Existing IDs, foreign keys, indexes, event/application rows and circle/venue catalogs are retained.
- No environment variables, instance type, payment activation, external provider credentials or service plans are changed.
- Prefer a forward fix if new separate-price events have been created. Do not redeploy the old single-price binary against new mixed events: it cannot interpret their tariffs correctly. Preserve the shared tariff/Checkout support in any emergency code rollback.
- Restore a full database backup only during a coordinated maintenance/recovery window, after taking a fresh backup and reconciling writes/payments since the snapshot. Never restore the pre-migration snapshot automatically over new applications or payment records. Extra nullable columns alone do not require database restoration.

## Verification

Full regression run: 375 cases, 374 passed and one existing HTTP test interrupted by Windows `WinError 10053`. Recheck: all 23 selected cases passed (16 dual-pricing cases, five payment cases, the JavaScript unit test and the interrupted HTTP test), 16.728 seconds. No unresolved assertion failures remain. Logs: `release-tests.log` and `release-recheck.log` in the private evidence folder. The final two-field desktop alignment is also checked in the production browser; it does not change billing rules.

Automated coverage includes separate persistence and required inputs, individual group/team totals, matching public/share/notification text, one-free/both-free cases, untrusted client amounts, capacity on approval, duplicate prevention across modes, headcount changes, private bank information after final confirmation, financial forecasts, legacy editing and migration preservation. Fake-Stripe cases cover gross/net tariffs, quantities, source preservation on edit, zero-charge handling, blocked-payment preview and full team-order refund.

Isolated browser walkthrough at 1440px desktop and 390px mobile:

1. Edit a draft, enter individual JPY 2,500 and team JPY 15,000, preview, acknowledge and publish.
2. Individual books two people: confirmation/result JPY 5,000, pending approval.
3. A different account books an 11-person team in the same event: confirmation/result JPY 15,000, pending approval.
4. Organizer approves both; confirmed capacity is 13 people and formation is ready.
5. Organizer announces; team representative confirms attendance; bank instructions appear only afterward, with JPY 15,000.
6. No horizontal overflow or console errors observed in that walkthrough. External email/authentication/payment calls were disabled, and the fixture is not production code.

Private screenshots/logs are under `work/dual-pricing-20261017/`. The final release evidence records the test result, matching Render Live commit, schema startup and read-only production checks. Successful fake-Stripe tests do not certify real card charges, transfers or mail delivery.
