# Account navigation and event workflow verification

## Automated checks

- `node scripts/test_signin.cjs`: email/Google start, callback, return URL,
  resend cooldown, expired/error states; non-persistent Supabase client.
- `python scripts/test_account_navigation.py`: initial HTML headers on home,
  DB tab, event list/editor/detail, both DBs and mypage; anonymous/invalid
  sessions; POST logout, CSRF rejection, revoked session, other device preserved.
- `python scripts/test_event_flow.py`: actual HTTP create/apply/close,
  authentication gate, approval, message, cancellation, migration preservation.
- `python scripts/test_event_capacity_email.py`: 10 tests for individual/team
  capacity, simultaneous last-slot requests, ownership, private contact,
  transactional outbox, retry/permanent failure and verified-email login.

All use temporary SQLite and test accounts. Provider HTTP is mocked in outbox
tests; no test sends real email or changes the production directory.

## Browser checks on the local fixture

Entry point: `python scripts/preview_event_flow.py` (127.0.0.1:8894 only).
The fixture must never be the production entry point. Its role-switch URLs
exist only in the disposable test handler, not in the application.

Confirmed with separate host/participant accounts:

1. Create a pickleball event, save draft, resume persisted contents.
2. Set team participation, two team slots, approval and bank transfer.
3. Preview and publish. Detail shows 2,000 yen per team and no required end time.
4. Apply as a ten-person team. Participant mypage shows pending approval.
5. Approve as host. Both mypages show confirmed; host counts one team, not ten.
6. Send host message, receive and reply as participant. Check private message pane.
7. Read application, approval and message notifications.
8. Cancel as participant. Mypage shows cancelled, further contact disabled;
   host notification shows the cancellation.
9. Inspect 390x844 and 320x740 mobile layouts: no horizontal overflow or
   overlapping header controls; header height about 55px.

The browser's native confirmation dialog briefly interrupted automation; the
dialog was resolved and the cancelled state was then visibly confirmed.

## Provider settings and limits

Japanese Magic Link and Confirm Sign Up templates were saved in the dedicated
Supabase project and verified in its preview. ConfirmationURL remains unchanged.
This pass does not create another real Supabase account or send another email.
Production email login and one transactional notification were previously
received/delivered using the configured SMTP/API provider in this task.

No real production event or application was created for this verification.
Real organizer onboarding and inbox testing on new devices remain operational
follow-ups; the draft plan is in `first-organizers.md`.
