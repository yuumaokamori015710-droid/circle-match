# 会場予約タブ

Latest official-price review: [2026-10-24](venue-fee-followup-2026-10-24.md). It reviewed 20 existing records and added 18 tariff sets and 17 cancellation-condition records. The catalog remains 1,206 records: 785 priced, 421 unpriced (413 active). Nonstandard time units, resident eligibility, restricted sports and partial closures stay explicit. Akirudai and Koganei remain unpriced without guessing. Existing IDs, booking URLs, original catalog fields and previous reviews are retained. [Previous review: 2026-10-23](venue-fee-followup-2026-10-23.md).

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

An indoor-sports follow-up checked 238 official SPOPITA basketball/volleyball
detail pages on 2026-10-12. It adds 89 gyms and enriches the sport/source fields
of 55 retained facilities, bringing the combined inventory to 1,202. Current
category counts are basketball 139, volleyball 145, badminton 149 and table
tennis 148. These category counts overlap; each facility counts once in the
combined inventory. Main/small gymnasium rooms are consolidated, and reviewed
aliases such as Hikari Sports Center and San Machida Asahi Gymnasium retain
their existing IDs instead of becoming duplicate listings.

New indoor records require a documented indoor facility type, exact sport
buttons, Tokyo street address and reservation instructions on the facility's
official detail page. School/restricted training facilities, outdoor courts,
records without reservation information and the closed Ryuhoku Sports Plaza
are not added. Registration, municipal/nonresident eligibility and reservation
conditions are retained in booking notes. Unknown prices remain null and
availability remains UNKNOWN. Booking links use stable official instructions,
not expired session URLs. Existing names, prices, booking URLs and the entire
legacy tennis file/API remain unchanged. Enrichment adds sports, sources,
the check date and evidence-supported indoor flags; cultural/community-center
labels and booking notes clarify which gym rooms support sports. The existing
toggle means "indoor facility exists", including mixed indoor/outdoor complexes.

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

The 2026-10-14 official fee and cancellation follow-up is recorded in
`docs/venue-fee-followup-2026-10-14.md`. It adds 11 previously unknown venue
tariffs without changing venue IDs, original booking URLs or existing tariffs.

The 2026-10-15 Ota and Adachi follow-up is in
`docs/venue-fee-followup-2026-10-15.md`. It adds seven source-matched tariffs
and cancellation conditions while retaining unknown prices where the exact
bookable facility tariff is unconfirmed.

The second and third Tokyo batches are recorded in
`docs/venue-fee-followup-2026-10-15-b.md` and
`docs/venue-fee-followup-2026-10-15-c.md`. The third batch adds ten
source-matched tariffs and four cancellation-policy records; it leaves
sport-mismatched or currently closed facilities unpriced.

The 2026-10-16 review is recorded in `docs/venue-fee-followup-2026-10-16.md`:
24 existing facilities reviewed, 22 newly priced, 15 cancellation checks,
and Hanahata's official long-term closure recorded. The catalog has 1,206
records, 664 with prices and 542 unpriced (including suspended records).
Charging units, eligibility and conflicting-source holds remain explicit.

The 2026-10-17 review adds 16 tariffs and 14 cancellation policies across
Fuchu, Komae, Fussa, Chuo, Shinagawa and Taito. Five research holds include
restricted group hire and an officially closed field. The catalog remains
1,206 records: 680 priced, 526 unpriced including suspended entries, and
523 active unpriced. See `docs/venue-fee-followup-2026-10-17.md` for sources,
same-unit ranges and closure dates.

The [2026-10-18 review](venue-fee-followup-2026-10-18.md) prioritizes Shinjuku
tennis and adds Katsushika soccer/futsal and indoor hall tariffs. Ten new
tariffs and 24 cancellation policies bring the unchanged 1,206-record catalog
to 690 priced and 516 unpriced (512 active unpriced). The original tennis file
and earlier fee/policy records are unchanged. Ochiai Chuo's baseball/soccer
field closure is recorded without marking its adjacent tennis court closed.

The [2026-10-19 review](venue-fee-followup-2026-10-19.md) covers Tama and
Kodaira outdoor fields plus Sumida, Nakano and Shinagawa sports halls.
Twenty newly priced existing records bring the catalog to 710 priced and
496 unpriced (491 active unpriced), still 1,206 records total. Seventeen
cancellation policies are added; one earlier Heiwa no Mori policy now
explicitly flags conflicting official guides, with the previous statement
archived in the dated report. Kodaira Central Park is closed until March
2027 (planned). Earlier tariffs, IDs, booking URLs and the legacy tennis
file are preserved. Free Myoshojigawa hire is source-confirmed and retains
Nakano group eligibility; it is not a placeholder zero.
