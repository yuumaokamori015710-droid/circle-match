# Club Edit Public UI

Approved mobile-first presentation, retaining the original Circle Match mark and
wordmark. Shared presentation lives in `outputs/circlematch_club_ui.py` and
`outputs/club_static/`; the existing event, auth, payment, venue and circle code
continues to own data and permissions.

## Interaction

- The home page shows a compact keyword search, native horizontal sports rail,
  and up to three real open public events. Empty/error states stay explicit.
- The rail has a full category grid, keyboard navigation, desktop arrows, selected
  states and browser-session scroll restoration. It works as ordinary links
  without JavaScript. Venue football/futsal uses the catalog's combined category.
- Search matches event title, location or public organizer name and combines
  with the existing sport, area, date and participation filters.
- Mobile navigation retains events, venues, circles and the real account area.
  No non-functional saved/favorite destination or fictional events are added.
- Detail pages keep the existing admission states and a mobile action above the
  navigation, with enough trailing space for content. Guest/member admission,
  individual/team tariffs, offline payment choices, consent and final submission
  remain owned by the existing server and form scripts.
- The member sign-in keeps its existing Google/email controls and return paths.
  Auth pages omit the bottom navigation. Secure guest-verification responses
  retain their existing isolated HTML/CSP.

## Assets

Photos are sport illustrations, explicitly captioned `競技イメージ`, not actual
event/venue photography. WebP derivatives are generated from the existing sports
PNGs; the original files and logo are unchanged. No external image/font/icon CDN
is required by the new UI. CSS/JS URLs include content hashes.

`scripts/build_club_assets.cjs` mechanically creates the committed WebP files and
selected SVGs from Lucide 1.8.0 (ISC; license in `club_static/LUCIDE-LICENSE.txt`).
The build uses the existing local Node runtime's `sharp` and `lucide` packages;
it is not a production dependency or deploy step.

## Validation

`scripts/test_club_ui.py` covers real HTTP markup, original branding, bounded
asset routes, escaped user content, combined search filters, context-safe rail
links, existing sign-in controls and real dual pricing. Existing sports-navigation
and latest-event tests assert the new rail-first ordering and preserved data
visibility. Other event/payment/auth/venue tests remain in the regression suite.

`scripts/preview_home_layout.py` runs a disposable loopback-only fixture. Its fake
host/participant sessions are defined in the preview handler only, never in the
production handler. It starts no email or payment workers.
