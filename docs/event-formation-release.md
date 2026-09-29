# Event Formation Release

## States

- A new form asks for minimum people/teams. Approval-pending applications do not count.
- Confirmed admission reserves capacity; it is not final attendance in this workflow.
- Reaching the minimum sends an organizer notification, once per threshold crossing.
- The organizer announces the date, venue and details. Confirmed applicants receive an in-app notification and the existing email outbox job.
- Each applicant confirms the latest announcement version for their whole application/group. Only then can that applicant see the transfer account and deadline.
- Updates require re-confirmation. Existing payment instructions remain fixed. Never pay twice after an update; settlement and refunds are manual.
- Bank-transfer applications/approvals stop at the payment deadline. Cancellation frees capacity and hides payment instructions.
- The system does not automatically cancel unconfirmed/unpaid applications or automatically refund money.

## Compatibility and Privacy

- Existing events retain their admission rules (`minimum_participants=0`); organizers can explicitly configure a minimum in edit. No event/application records are replaced.
- Existing internal `target_total_amount` is retained; UI calls it the break-even amount. Forecast is capacity times unit fee minus this amount, owner-only, not collected funds.
- Bank account fields are excluded from public APIs, sharing, notifications and other users' mypages. Detail and attendance responses are no-store.
- Copies retain ordinary event settings but not bank accounts, announcements or participant confirmations.
- Instagram/TikTok open their services and copy the full recruitment text; they do not automatically publish or prefill a post. Plus opens native sharing where supported. X gets a length-limited summary; copy retains all details.

## Deployment and Recovery

Startup adds columns to `event_posts` and `event_applications`, within one transaction after creating a consistent SQLite backup at:

`/var/data/circlematch.sqlite.pre-formation-<timestamp>.sqlite`

No schema columns are removed. Migration is idempotent. An application rollback can leave these additive columns in place; do not restore an older database over newer applications.

For database recovery only: stop writes to the service, preserve the current database and its WAL/SHM alongside a current SQLite backup, verify the pre-formation backup using `PRAGMA integrity_check`, and restore only with explicit operator approval. This loses records created since that backup unless reconciled first. Do not perform a file copy over a running SQLite database.

## Verification

Run `python -m unittest discover -s scripts -p "test_event*.py"`, `python scripts/test_event_flow.py`, `python scripts/test_account_navigation.py`, and `node scripts/test_signin.cjs`.
Use disposable local accounts for publishing/announcing/applying; no production test invitations, bank accounts or outgoing test emails are required.
