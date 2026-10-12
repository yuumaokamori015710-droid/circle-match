# Venue comparison controls and Komazawa

## Changes

- Reduced row padding, text spacing and collapsed detail height. Booking and
  event-creation actions share a line where space permits. Mobile retains
  readable stacked records and touch-sized actions.
- All six column headings expose native details menus, with relevant filters
  and ascending/descending sorting. Mobile displays the same headings as a
  compact two-row toolbar. Region filtering opens the existing map selector.
- Name-only search is independent of the broader facility/place keyword.
  Price filters distinguish published prices, missing amounts and comparable
  per-court hourly prices. Booking/registration controls share the existing
  filter state, rather than creating conflicting duplicate form fields.
- Default ordering is `available`: any published amount or conditional tariff
  comes before missing prices, including zero-cost and non-hourly tariffs.
  Explicit hourly price sorting still compares only like units and places
  unknown/non-comparable amounts last in either direction. Saved explicit
  browser preferences remain supported; new/reset defaults prefer prices.
- All controls preserve query context. Links and GET forms also work without
  JavaScript. The client and server implement identical deterministic sorts.

## Official catalog additions

Four separate Komazawa facilities were checked on 2026-10-12. The existing
gym and tennis records and their identifiers are unchanged. Total inventory
increases from 1,202 to 1,206; sport counts overlap, facilities do not.

- First ballgame field: 29,100 JPY/morning, amateur sports, no admission fee,
  no stand use. CLOSED for construction 2026-09-01 through 2027-03-31 (planned),
  excluded by default and unavailable for event creation.
- Second ballgame field: 19,800 JPY/full-field morning (four hours).
- Auxiliary field: 18,000 JPY/full-field morning (four hours).
- Stadium: 48,400 JPY/full-field morning (four hours); counter application,
  not online booking. Individual running fees are not substituted for rental.

Time slots, half-field practice rates, separate lighting costs and official
booking/group-registration requirements are retained in the tariff details.
All quoted tariffs are inclusive of tax, admission-free and without stand use;
stand/admission/equipment charges are not represented as the same price.
Full-field time-slot fees are not misrepresented as per-court hourly quotes.

Official sources:

- https://www.tef.or.jp/kopgp/ballgame1/index.html
- https://www.tef.or.jp/kopgp/ballgame2/
- https://www.tef.or.jp/kopgp/substadium/index.html
- https://www.tef.or.jp/kopgp/stadium/index.html
- https://www.tef.or.jp/kopgp/general/
- https://www.tef.or.jp/news/post-746.html
- https://sports.tef.or.jp/

## Verification

- 72 Python tests passed across venue columns, existing venues, circle maps,
  sport navigation and SEO, using disposable SQLite and loopback HTTP.
- Existing Playwright suite passed 56 sport/viewport combinations, tariff,
  map, search, settings, no-JavaScript and failure/retry checks.
- New Playwright suite passed at 320, 390, 768, 1440 and 1920 pixels: all six
  menus stay within the viewport; combined filters, reload/back, all 13 sorts
  versus SSR, Komazawa closure handling and no-JavaScript links work.
- No new browser JavaScript errors or horizontal page overflow.
- Browser evidence is generated in `work/venue-columns-verification/`.

## Deployment and rollback

Deploy the latest `main` to the existing Circle Match Render service. No DB
migration, credentials, environment settings or billing changes are required.
Rollback by reverting this release commit onto the latest branch and deploying
that resulting commit, not by replacing the persistent database or old data.
