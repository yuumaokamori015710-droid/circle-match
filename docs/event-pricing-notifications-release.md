# Event Pricing and Notifications

## Data Change

- `event_posts.target_total_amount` is nullable, integer yen, restricted to 0 through 1,000,000,000.
- Startup adds the column only if it is missing. Existing records and IDs are unchanged.
- Before the first alteration, SQLite's backup API creates `<database>.pre-target-total-<timestamp>.sqlite` alongside the persistent database. Startup logs the exact path. Repeated starts do not create extra backups.
- Only owner edit/copy and hosted-event responses include the value. Public event queries and participant responses exclude it. A target-only edit does not notify participants.

## Rollback

- The previous app revision can run with the extra nullable column; a code rollback does not require deleting it or restoring old data.
- Preserve the live database and the backup before any recovery operation. Restoring the snapshot would discard changes made after its timestamp, so stop writes and reconcile newer rows first. Do not automatically replace the live database with the snapshot.
- New events derive capacity and price units from participation type. Existing event units are preserved on edits when participation type is unchanged.
- `payment_method='free'` is retained internally for schema compatibility and displayed as `-`. A positive public fee must have an on-site or bank-transfer method; paid draft amounts are not silently erased.

## Notifications

- `/notifications` is the authenticated inbox; the old `/mypage?tab=notifications` URL redirects there.
- The fixed header bell shows the recipient's exact unread count. Visible pages check every 30 seconds and on focus.
- Reading an inbox page marks only its displayed notifications as read, through the recipient-scoped POST endpoint. Pagination preserves access to older notices.
- JSON responses are not cached. No auth-provider or email-sending configuration changes are needed.
- Tests use temporary SQLite databases and mocked email delivery. No test emails or public sample events are created.
