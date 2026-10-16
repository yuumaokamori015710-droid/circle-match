# Venue Fee Follow-Up: 2026-10-16

Reviewed 24 existing Tokyo records after fast-forwarding to GitHub main `28cd882`, including the latest payment safeguards. Added official tariffs to 22 previously unpriced records and cancellation information to 15. One officially closed gym is now suspended, without deleting its record. IDs, original booking/official URLs, other catalog data, SQLite, schema, environment settings and plans were preserved. No reservations, inquiries, logins or payments were performed.

## Reviewed Records

| Existing ID | Facility | Official price evidence / result |
| --- | --- | --- |
| tokyo-venue-9b93d81ca10e | 伊興地域学習センター | [Ward tariff](https://www.city.adachi.tokyo.jp/sg-shien/iko.html): gym full/half; 3-hour morning and 2.5-hour later slots separate. |
| tokyo-venue-8a96774363e5 | 東和地域学習センター | [Ward tariff](https://www.city.adachi.tokyo.jp/sg-shien/touwa.html): gym only, not learning-room or individual admission. |
| tokyo-venue-84dbc0345777 | 江北地域学習センター | [Ward tariff](https://www.city.adachi.tokyo.jp/sg-shien/shisetsu/kouhoku.html): full/half and same-duration ranges. |
| tokyo-gym-bc16a86706e5 | 中央本町地域体育館 | [Ward tariff](https://www.city.adachi.tokyo.jp/sg-shien/chuouhonchou.html): full 2,700 yen/3 hours or 3,500–4,100 yen/2.5 hours. |
| tokyo-gym-dc5097408efb | 佐野地域体育館 | [Ward tariff](https://www.city.adachi.tokyo.jp/sg-shien/sano.html): full 2,200 yen/3 hours or 2,700–3,300 yen/2.5 hours. |
| tokyo-gym-6a6bb1ea794a | 梅田地域体育館 | [Ward tariff](https://www.city.adachi.tokyo.jp/sg-shien/umeda2.html): gym, not separately priced stage hall. |
| tokyo-gym-145a2b1e2fa3 | 興本地域体育館 | [Ward tariff](https://www.city.adachi.tokyo.jp/sg-shien/okimoto.html): full/half, 3-hour/2.5-hour separately. |
| tokyo-gym-9df21a804b72 | 鹿浜地域体育館 | [Ward tariff](https://www.city.adachi.tokyo.jp/sg-shien/shikahama.html): full/half, 3-hour/2.5-hour separately. |
| tokyo-gym-573105da20a9 | スイムスポーツセンター | [Ward tariff](https://www.city.adachi.tokyo.jp/sports/shisetsu/swim.html): gym full/half, short slots/full day; pool and dance room excluded. |
| tokyo-gym-46bb4a7e287c | 総合スポーツセンター【足立区】 | [Ward tariff](https://www.city.adachi.tokyo.jp/sports/shisetsu/sousupo-in.html): large full/half/quarter gym and small gym use distinct units. |
| tokyo-gym-e4c214671936 | 花畑地域体育館 | [Ward closure](https://www.city.adachi.tokyo.jp/sg-shien/hanahata.html): closed 2026-09-01 to about 2028-03. SUSPENDED, retained links, no historical price promoted as current bookability. |
| tokyo-gym-0cb647825898 | 大蔵第二運動場 | [Operator gym tariff](https://www.se-sports.or.jp/facilityinfo/okura-gym/): full/half, weekday/weekend, 2-hour/3-hour/full-day separate. |
| tokyo-gym-4eb031276843 | 総合運動場【世田谷区】 | [Operator gym tariff](https://www.se-sports.or.jp/facilityinfo/sougou-gym/): full 17,160–20,550 yen/3 hours, half/full-day separately. |
| tokyo-gym-e9661f9d4b0f | 希望丘地域体育館 | [Third-floor gym](https://www.se-sports.or.jp/facilityinfo/kibougaoka-gym-3rd-floor/): weekday/Saturday versus Sunday/holiday; 3-hour/2.5-hour separate; 15:00–16:00 is not group-rentable. |
| tokyo-gym-815e7ebed1c0 | 尾山台地域体育館 | [Operator gym tariff](https://www.se-sports.or.jp/facilityinfo/oyamadai-gym/): Wednesday 2.5-hour, eligible Sunday/holiday 4-hour/full-day. [Planned 2026-12 to 2027-02-mid closure](https://www.se-sports.or.jp/news/22467/) is in conditions; not yet suspended on this date. |
| tokyo-gym-f4ecc307371e | 駒沢オリンピック公園総合運動場 | [Indoor ball-game hall](https://www.tef.or.jp/kopgp/ballgame-indoor/): amateur/no spectator admission/stand unused, 37,800–65,000 yen/4 hours; 8-hour/full-day separately. Not every facility or admission category in the park. |
| tokyo-gym-125683b2ea6c | 四谷スポーツスクエア | [Current linked PDF](https://yotsuya-sports-square.jp/yotsuyawp/wp-content/themes/twentytwentyone-child/pdf/price.pdf), visually checked: multipurpose hall, 3-hour/full-day; registered ward-resident discount eligibility explicit. |
| tokyo-gym-5074f6b079ec | 新宿コズミックスポーツセンター | [Current guide](https://www.regasu-shinjuku.or.jp/?p=668) links [tariff PDF](https://www.regasu-shinjuku.or.jp/regasu/wp-content/uploads/2018/07/shisetsu-price.pdf), visually checked. Large gym full/half, 3-hour/full-day. URL path year is not the effective date; current guide links it. Ward/non-ward groups have identical rates. |
| tokyo-venue-555e53ea3e30 | 新砂運動場 | [Operator revised tariff PDF](https://www.di-ksp.jp/wp/wp-content/uploads/R6%E5%88%A9%E7%94%A8%E6%96%99%E9%87%91%E6%94%B9%E8%A8%82%EF%BC%88%E6%96%B0%E7%A0%82%E9%81%8B%E5%8B%95%E5%A0%B4%EF%BC%89_202402HP%E5%91%A8%E7%9F%A5.pdf), visually checked, new column for approvals from 2025-04-01. Soccer, first/second grounds full/half, multipurpose ground separate. Lighting is additional 5,150 yen/hour, not a 2-hour surface price. |
| tokyo-gym-01345ff23a1e | 江東区亀戸スポーツセンター | [Official operator](https://www.koto-hsc.or.jp/centerlist/sports_center3/): large gym full area; 3-hour/4-hour/3.5-hour/combined/full-day separate. Admission-charging use is 150%, excluded from normal range and stated in conditions. |
| tokyo-gym-598414cefd93 | 東京体育館 | [Subarena page](https://www.tef.or.jp/tmg/subarena/) links [PDF](https://www.tef.or.jp/tmg/subarena/subarena_fee02.pdf), visually checked: amateur/no spectator admission; full/half and 4-hour/8-hour/full-day separate; half-area normally practice only. |
| tokyo-gym-ece12bfc054b | サンライフ練馬 | [Designated operator](https://sunlifenerima.sakura.ne.jp/riyoujikan.html), linked by [ward](https://www.city.nerima.tokyo.jp/shisetsu/community/shohi/sunlife.html): effective 2026-07, 5,400 yen/3-hour morning, 7,200 yen/4-hour afternoon/evening, not hourly. |
| tokyo-gym-24073ef2f004 | 旭町南地区区民館 | [Ward special-facility guide](https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/asahityouminami.html): gym full 1,600 yen/hour, half 800 yen/hour; eligible registered groups pay half. No pool fee substituted. |
| tokyo-sports-038 | 江戸川区スポーツランド（フットサルコート） | Hold: [operator](https://www.edogawa-sportsland.com/tennis-footsul/) says 670 yen/hour plus 320 yen lighting, while [ward 2026-04 schedule](https://www.city.edogawa.tokyo.jp/documents/67566/ichiranv2.pdf) p.16 says 460 yen/hour. The inclusion/eligibility difference was not established. Conflicting prices are not a legitimate 460–670 yen range. |

## Cancellation Scope

- Eight Adachi regional gyms/centers: [ward guide](https://www.city.adachi.tokyo.jp/sg-shien/chiikibunka/shogaigakushu/riyohouhou02.html), refund windows/responsibility exceptions. Not automatically copied to separately managed Swim/General Sports Centers.
- Four Setagaya gyms: [Keyaki guide](https://www.se-sports.or.jp/keyaki/), graded self-cancellation charges. Outdoor bad-weather free cancellation explicitly excluded for indoor gyms.
- Yotsuya: [operator](https://yotsuya-sports-square.jp/userguide1/), full refund by one calendar month before, half by 14 days before, then none.
- Cosmic: unpaid online/counter cancellation and paid counter-refund procedure verified. Precise paid-refund percentages remain unverified because the guide's refund table was not reliably extracted.
- Kameido: ward-declared disaster-related closure gives full refund. Self-cancellation deadline/percentage is unknown, not advertised as free.

All new tariffs/policies carry `2026-10-16`, original charging units, eligibility and source URLs. Discount ranges describe specifically eligible groups, not a guaranteed price for everyone. Snapshot importer `scripts/record_venue_fee_review_20261016.py` refuses to overwrite a different review for an existing ID.

Before: 1,206 records, 642 with prices, 564 unpriced. After: 664 with prices, 542 unpriced, including preserved suspended records. Unknown amounts were not zeroed or guessed.

## Verification

- 83 unit/integration checks passed: venues, columns, fee ranges, this snapshot, sport navigation, SEO and event flow. The catalog-error log in the failure-state test is deliberately injected.
- Existing browser suite passed 56 sport/viewport combinations (390/768/1440/1920 px), 16 fee cases, map selection, URL history, filters, sorting, settings, no-JS and offline fallback. Local Windows browser navigations produced client-disconnect log noise; browser assertions passed.
- New browser suite passed all 22 added venue tariffs at 390 and 1440 px, two no-JS initial-HTML cases, source-link/amount/units checks and closed-gym default exclusion; no page errors or horizontal overflow.
- Visually reviewed new soccer/mobile and gym/desktop screenshots. Snapshot importer rerun left both catalog hashes unchanged. Original prior tariff objects and all original facility IDs/booking URLs were retained.
- Remaining unknown: 542 catalog records in total, 540 excluding suspended facilities. No user action is needed for this data update; conflicting Edogawa tariffs remain queued for public-source research.
