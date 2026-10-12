# Venue Search and Browser Settings

## Scope

- All 1,202 original venue records, identifiers, prices, booking links and event-prefill links are preserved.
- `/venues` now scopes municipality choices by area and the selected sport. An incompatible municipality is cleared on area change, including the initial server render.
- Booking channel (Web, phone, counter) and facility-user registration are separate filters. Unknown is not treated as registration-free. Channel tags come only from the curated booking-method text, not from arbitrary contact telephone numbers. A system used only for vacancy lookup is not tagged as Web booking.
- Venue-purpose categories are separate from public/private operation. A mixed-purpose venue can match multiple categories. Legacy `facility_kind` URLs and the tennis API remain compatible.
- Sort belongs to the results header, associated with the GET search form. All conditions are URL-backed; server HTML and browser filtering are tested.
- The price ceiling is typed, accepts comma separators/full-width digits, and retains the explicit per-court/hour comparison basis. Variable and incomparable prices are excluded from hourly comparisons.
- Confirmed time windows are not live opening status, calendar availability or a guarantee of continuous reservation slots. Unknown hours are excluded only when a time condition is set. Closure and room-specific conditions must be checked with the operator.

## Verified Common Utilization Hours

Checked on 2026-10-12 against official sources. Times below concern facility use, not reception desks. Closures and exceptions are retained on each venue card. No hours were guessed for other venues.

| Venue | Common Time Window | Official Source |
| --- | --- | --- |
| フットサルクラブ東京 八幡山コート | 10:00–23:00 | https://www.futsal-tokyo.co.jp/hachimanyama/ |
| FC東京パーク府中 | 11:00–21:45 | https://www.fctokyoparkfuchu.jp/facility/ |
| ジェクサー・フットサルクラブ アトレ大井町店 | 10:00–20:00 | https://www.jexer.jp/futsal/oi/ |
| 伊興地域学習センター | 09:00–21:30 | https://www.city.adachi.tokyo.jp/sg-shien/shisetsu/shogaigakushu/001.html |
| 保塚地域学習センター | 09:00–21:30 | https://www.city.adachi.tokyo.jp/sg-shien/shisetsu/shogaigakushu/014.html |
| 新田地域学習センター | 09:00–21:30 | https://www.city.adachi.tokyo.jp/sg-shien/shisetsu/shogaigakushu/008.html |
| 東和地域学習センター | 09:00–21:30 | https://www.city.adachi.tokyo.jp/sg-shien/shisetsu/shogaigakushu/011.html |
| 江北地域学習センター | 09:00–21:30 | https://www.city.adachi.tokyo.jp/sg-shien/shisetsu/shogaigakushu/004.html |
| 竹の塚地域学習センター | 09:00–21:30 | https://www.city.adachi.tokyo.jp/sg-shien/shisetsu/shogaigakushu/009.html |
| 中野区立総合体育館 | 07:00–22:15 | https://information.konamisportsclub.jp/trust/nakano/ |
| 武蔵村山市総合体育館 | 09:00–21:30 | https://musashimurayama-gym.jp/gym/facilities |
| JELLY JELLY CAFE 池袋1号店 | 13:00–23:00 | https://jellyjellycafe.com/ikebukuro |
| JELLY JELLY CAFE 渋谷本店 | 13:00–23:00 | https://jellyjellycafe.com/shibuya |

Ikebukuro opens earlier on weekends; only the common range is used in filtering. Both cafes have a 22:00 last-admission cutoff, indicated in their notes. Search compares utilization windows, not arrival admissibility.

## Settings

- `/settings` is public and noindex. The gear appears beside the notification bell.
- Auto/mobile/desktop display, default venue area/sort, and optional last-search persistence are local to this browser (`circlematch.preferences.v1`, `circlematch.venue-search.v1.*`). Nothing is written to accounts, cookies or the database.
- Forced mobile uses a 390px presentation and browser-parsed media rules; desktop uses a 1280px viewport on phones. Other media features such as reduced motion remain intact. Auto restores the original rules and viewport.
- Settings themselves always use auto display so the phone user can easily restore auto mode after choosing desktop.
- Explicit URL conditions override saved conditions. Applied defaults also enter the URL for sharing. Storage failures show an error rather than a false saved message. Reset clears only Circle Match preferences and saved venue conditions.
- No dependencies, secrets, environment variables, paid plans or DB migrations are added. Rollback is redeployment of the previous application commit. Existing event and venue data are unaffected.
