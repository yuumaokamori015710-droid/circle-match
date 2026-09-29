# Event Sharing and Group Applications

## Changes

- Open a share dialog after the owner publishes an event. It is also available
  from event details and beside application review/submit controls.
- Share only the public event title and detail URL. Application answers, contact
  addresses, organizer targets and authentication query parameters are excluded.
- LINE and X open their share composer. Instagram and TikTok use the device's
  native share menu, with clipboard fallback. Availability depends on the device
  and installed apps; this is not automatic social-media posting.
- Add karaoke and event photo categories, plus a custom-category creation entry.
  Existing "other" data, filtering and image URLs remain compatible.
- Support direct fee input, including full-width digits and thousands separators.
  Zero-fee events disable payment selection and omit payment method from public
  details, the preview and application recap.
- Allow individual applications to include friends. Their total headcount is
  reserved atomically; the representative handles contact and whole-group
  cancellation. Partial cancellation and separate companion accounts are not
  implemented.
- Center the 480px desktop publishing button. Add a home icon and place the
  notification bell immediately after the account/logout controls.

## Verification (2026-09-30 JST)

- `python -m unittest discover -s scripts -p "test_event*.py"`: 40 passed.
- `python scripts/test_event_flow.py`: passed HTTP creation and application flow.
- `python scripts/test_account_navigation.py`: 3 passed.
- `node scripts/test_signin.cjs`: passed.
- Local browser: create and publish a custom board-game event; automatic share
  dialog; link copying; free-fee disabled payment; full-width `1,500` fee input;
  three-person application charged 4,500 yen and consuming 3 of 4 places.
- Browser layouts inspected at desktop, 390px and 320px widths. Share dialog and
  header remain within the viewport; both new images loaded.
- Concurrent group requests, approval, cancellation, privacy boundaries,
  clipboard failure, native-share cancellation and public custom-category
  discovery are covered by isolated tests.

## Release Safety

No database schema or seed-data changes are required. Existing event and circle
records are preserved. All test event creation and application actions used an
isolated local database with outgoing notifications disabled. No posts were sent
to social networks. The existing Render service and main branch are used; no
environment variables or paid-service settings are changed.

Rollback is a revert of this release's application, tests and new image assets
followed by a deployment of the resulting latest main commit. Existing grouped
applications keep their stored headcounts; reverting the UI does not remove them.
