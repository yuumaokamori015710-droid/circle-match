# Event Operations

## Scope

Existing public recruitment content is unchanged. Apple sign-in is not enabled.

- Owners can record unpaid, payment received, settlement/refund review, or refunded. These are manual records, not a payment processor. A private owner memo is never returned to other users. Paid cancellations and event cancellations enter settlement review without promising a refund.
- Applicants can change group headcount without cancelling their reservation. Approved increases on approval-based events need another organizer approval; existing headcount remains reserved until then. Capacity is rechecked under a SQLite write transaction. Paid/settled applications require consultation with the organizer before changing headcount. Changing count resets final attendance confirmation.
- Announcements include a final attendance deadline, no later than the payment deadline/event date. One reminder is generated within 24 hours before it; after expiry both parties are notified. A persisted per-application/version key prevents duplicate reminders on restart. No automatic cancellation occurs. Organizers can individually release expired, unconfirmed, unpaid reservations with a reason sent to the applicant.
- Logged-in visitors may privately ask questions without applying. Only that visitor and the organizer can read or reply; cancelled/past events retain existing conversations but disallow new visitor conversations. Messages use the existing email outbox and are limited to 10/minute and 60/hour per account.

## Navigation

- Event detail -> Ask organizer -> sign-in when needed -> private conversation.
- My page -> pre-application questions, or host Questions/contact -> conversation.
- My page -> applicant Details/headcount -> change headcount.
- My page -> host Admission/payment management -> application -> approvals, settlement and expired reservation release.
- Notifications link directly to conversations, attendance confirmation or management.

## Operational Limits

- Existing announcements with no attendance deadline are not changed automatically; organizers set a deadline from the announcement editor.
- Payment reconciliation and actual transfers/refunds remain outside Circle Match. Recording a status does not move money. Bank account details remain on the authenticated attendance page only.
- Reminders run every 60 seconds in the existing service worker, up to 100 eligible applications per pass. They continue as in-app notifications when mail configuration is unavailable; email retries use the existing persisted outbox. During service downtime reminders wait until restart. Missed pre-deadline reminders become expiry notices.
- A public event fee cannot change once payment/settlement records exist. Automatic detection of bank transfers is not included.

## Data and Recovery

Startup performs an additive, idempotent migration with a SQLite backup named `circlematch.sqlite.pre-operations-<timestamp>.sqlite` on the same disk. No circles, recruitment descriptions, applications or messages are replaced. Application revisions reject stale updates. Headcount snapshots and payment status audits are retained.

For code rollback, leave added columns/tables intact. To recover database content, stop writes, preserve the current database and journal files, validate a consistent backup with `PRAGMA integrity_check`, and restore only with operator approval after reconciling new applications. Do not copy an old database over a running service.

## Verification

Run `python -m unittest discover -s scripts -p "test_event*.py"`, `python scripts/test_event_flow.py`, `python scripts/test_account_navigation.py`, and `node scripts/test_signin.cjs`. `scripts/preview_event_operations.py` supplies disposable localhost-only accounts and data; it disables outbound email and must never be used as the production entry point.

Verified on 2026-10-01:

- 62 event tests passed, including 13 new operations tests. Coverage includes concurrent capacity updates, owner/applicant isolation, private memos, revision conflicts, cross-origin/invalid content-type rejection, reminder deduplication, and migration backup integrity.
- Event flow integration passed; three account navigation tests and the JavaScript sign-in flow passed.
- Browser walkthrough with disposable accounts: reduce 3 people to 2, reconfirm attendance, show the updated 2,000-yen total, record payment, ask before applying, receive an organizer reply, reopen the conversation from My Page.
- Desktop (1440px) and mobile (390px) screenshots checked. The mobile message page had 390px document/scroll width; the payment page had 375px content/scroll width plus its scrollbar. No horizontal overflow.
- Production recruitment content and the unrelated circle seed collection are excluded from this change. No production applications, payments or test emails were created.
