# 会場予約タブ

`/venues` is a native public Circle Match page alongside the events and circle
directory tabs. It lists Tokyo facilities for all 14 main sports/activity
categories. The first 50 matching facilities, booking links, counts and GET
filters are server-rendered and usable without JavaScript. Client-side search,
filtering, sorting and incremental pagination enhance the same list after one
read-only catalog request. API failure leaves the initial records readable.
Reservation links lead to the facility's official reservation instructions or
booking site; this page does not submit reservations or process payments.

## Files and data

- `outputs/circlematch_venues.py`: native body, asset declarations and public
  catalog interface; no acquisition admin or database dependency.
- `outputs/venues/`: scoped CSS, JavaScript and the curated public catalog.
- `outputs/circlematch_db_app.py`: shared tabs and explicit public GET routes.
- `scripts/test_venues.py`: isolated HTTP and navigation integration checks.
- `scripts/verify_venues_browser.cjs`: Playwright checks at 390, 768, 1440 and
  1920 pixels, including no-JavaScript and failed-API scenarios. Requires
  Playwright and Chrome; set `VENUE_PYTHON` for a non-default Python runtime.
  Set `VENUE_TEST_URL` to verify a deployed site without starting a local server.

The initial catalog and directory UI were copied from the existing
`circlematch-acquisition` project at commit
`f6b3b14f21a3c729e2e70f7f3f14f8ce51e94b3a`. The catalog contains 404 facilities
across 58 Tokyo municipalities, with source checks dated 2026-10-10. Each record
retains its official source URLs, original price unit, conditions, check date
and unknown values. Known suspended facilities are hidden by default.
Coverage is described in the catalog; the list is not a claim of completeness
or live availability.

`tokyo_sports.json` adds 47 official-source records checked on 2026-10-12,
including 28 soccer/futsal facilities, indoor sports centers, a pickleball
venue, running tracks, rugby grounds, golf, karaoke, meeting rooms and board
game cafes. Ground golf and youth-only activity centers are not misclassified
as general golf/karaoke venues. Unknown prices, lighting and equipment stay
unknown. Booking eligibility and municipal registration requirements are
included. Direct booking systems may require login or reject automated access;
the facility's official information link is also available.

`tokyo_expansion.json` adds 662 distinct facilities checked on 2026-10-12,
bringing the combined inventory to 1,113 (including retained suspended records).
The additions include sports grounds and gyms, 135 operator-listed karaoke
stores with store-specific Web booking links, and 312 event/meeting facilities.
Multi-purpose venues appear in several sport filters but count once in the
total. Soccer/futsal now has 157 facilities. Existing IDs, prices and source
records in both original files are unchanged.

The source audit retrieved 1,213 distinct official information/reservation URLs
with bounded concurrency. Candidate records were checked against retrieved
facility names, street addresses, supported sport terms and reservation routes.
Duplicate names/aliases and complex-wide records were consolidated; numbered
court/room listings were not used to inflate the inventory. Unverified addresses,
unsupported sport tags, failed URLs, expired session links and current known
closures were excluded. For example, the Gotanda Cultural Center music hall
is omitted during its published 2026-09-24 to 2026-12-08 construction closure.
Current unknown prices and availability remain unknown, not zero or available.

Some official metropolitan sports records describe telephone/counter booking
or link to legacy session-based systems. Their stable official "reservation
method" page is used instead of storing a session URL. Municipal meeting rooms
remain event-only, with group-registration and permitted-use restrictions.
The catalog is loaded locally with a one-entry mtime-invalidated cache across
all three files; public requests do not crawl external sites or read private DBs.

To roll back this inventory release, revert its commit and deploy the resulting
latest branch. No private database migration or replacement is involved. Do not
remove the expansion file alone while its loader references it. Run the venue,
sport-navigation, SEO and event-flow tests and the browser verifier after updates.

`GET /api/venues?sport=...` serves the combined catalog, scoped to the selected
category. The original `/api/tennis-courts` and 404-record tennis file are
unchanged. `/venues?sport=...&prefecture=東京都` retains the shared sports,
region and tab navigation. Venue filters use `v_*` URL parameters in JavaScript;
native GET forms also accept plain filter names. No-JavaScript pagination uses
`v_page`. Other regions and custom categories explicitly say coverage is pending.

After securing a booking externally, `/events/new?venue=<catalog-id>&sport=...`
prefills the trusted venue name/address, Tokyo prefecture and a supported sport.
It preserves the existing authentication and draft workflow. This does not
claim the venue has been reserved. No external booking, payment, account or
private database mutation is performed by the venue directory.

Update the checked-in catalog from verified official information and run the
catalog validation and `scripts/test_venues.py` before publishing. The catalog
is intentionally independent of either application's private user database.
Do not copy private acquisition settings, credentials or management routes
into this public page.
