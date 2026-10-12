# Venue Map and Conditional Tariffs

## Scope

- Keep all 1,202 venue records, identifiers, booking URLs and legacy catalogs intact.
- Tokyo-first administrative map: Japan > Kanto > Tokyo > 23 wards / Tama / islands > municipality.
- Areas without matching sport facilities are disabled. This is geographic selection, not facility pins or live availability.
- Four visible filters: name/address, booking channel, registration requirement, comparable court price ceiling. Two rows on phones, one row on desktop.
- Facility type, ownership and strict hours are removed from the visible filter UI. Older URLs still work and can be reset.
- Desktop comparison table; compact mobile rows. Sorting stays on the results header, outside the filters.
- Native GET forms, SVG links and server-rendered first 50 results work without JavaScript. Client search and saved settings remain supported.

## Map Provenance

Source: [SmartNews Japan Topography](https://github.com/smartnews-smri/japan-topography), using MLIT National Land Numerical Information administrative boundaries (2021). Source credit is displayed beside the map. Source URLs and input SHA-256 are stored in `region_maps.json`.

`scripts/build_venue_maps.cjs` uses D3 and TopoJSON at build time. Production serves precomputed SVG paths and does not contact a map provider or download these libraries.

## Price Review

Before this change: 533 facilities with a listed amount, 669 without one.

After this change: **565 facilities with an amount**, including **316 with 5,540 explicit conditional tariffs**. Newly priced: 32 facilities. **637 facilities still lack a verified amount**. Their absence is displayed honestly; it is not converted into zero or removed by relabeling.

Examples of reviewed primary sources:

- [Kita community-room tariffs](https://www.city.kita.lg.jp/_res/projects/default_project/_page_/001/002/372/20180423shimokaisetsugo.pdf): resident/nonresident, room and morning/afternoon/evening.
- [Takinogawa Gym](https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010416/1010420/1010421.html), [Kirigaoka Gym](https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010416/1010420/1010422.html), [Akabane Gym](https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010416/1010420/1010423.html): revised group rental fees, whole/partial arena and time slots. Individual admission fees are not substituted for exclusive rental.
- [FC Tokyo Park Fuchu](https://www.fctokyoparkfuchu.jp/rental/): member/visitor, weekday/weekend and separate 45-minute late slot.
- [JSC Nishigaoka](https://www.jpnsport.go.jp/hpsc/Default.aspx?TabId=1440): ordinary court rental, not tournament entry fees.
- Meguro official community-center tables: registered resident / general resident / other groups, rooms and time slots.
- 69 Manekineko operator PDFs: four matching member/visitor/day columns and two time bands. Per-room and per-person charges are distinguished. Seven ambiguous PDFs were not converted.

Each tariff has an integer yen amount, unit, exact usage label, conditions, primary-source URL and review date. Legacy `price_from`, `price_to` and hourly comparisons are not rewritten. Conditional minimums are not treated as universally comparable hourly rates. Lower/upper ranges without a verified conditional breakdown remain ranges rather than invented fixed prices.

Largest remaining sources: third-party gym listings (144), Tokyo school-opening facilities (110), operator pages without a usable price PDF (59). School eligibility, lighting and air-conditioning charges are not assumed free. Remaining facilities need further primary-source research or an operator quote.

## Reproduction

```powershell
node scripts/build_venue_maps.cjs
python scripts/build_venue_fee_plans.py --collect --collect-sports --pdf-python <python-with-pdfplumber>
<python-with-pdfplumber> scripts/collect_karaoke_tariffs.py
```

The fee builder uses the existing dated review evidence in `docs/venue-fee-review-2026-10-12.json`. Network collection only reads public operator/municipal sources; no bookings or contact requests are sent. The karaoke collector checks extracted amounts against that evidence and rejects ambiguous mappings.

## Verification and Recovery

- Python integration and regression suites cover venues, sport navigation, SEO, event/account flows, pricing/notifications and latest-event homepage.
- Browser checks: 14 sports at 390/768/1440/1920px; table/fee units; map drill-down and browser back/forward; booking/registration/price filters; old hours URLs; reload/shared conditions; saved preferences; forced mobile/desktop views; settings at 320/390/768/1440/1920px; JavaScript-disabled map/forms/tariffs; API-failure retention of SSR results.
- Existing circle/event/auth data are unchanged. No SQLite or Supabase migration, no environment or plan changes.
- Recovery: revert this release commit and deploy its successor normally. No database restoration is needed. Do not reset unrelated changes or deploy an old pinned commit.
