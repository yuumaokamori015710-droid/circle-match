# Official Venue Fee Follow-Up: 2026-11-04

## Scope and Result

Checked 20 existing records against public official sources, starting with all six active unpriced soccer/futsal or gym records. Added 15 scoped tariff sets and 14 cancellation records; five tariffs remain unknown. The unchanged 1,206-record inventory now has 906 priced and 300 unpriced records (289 active, 11 suspended). These are records with at least one verified tariff, not claims that every room, customer type or activity is priced.

No registration, inquiry, booking, login, payment, environment variable, billing-plan or DB-schema change was made. Main at the research baseline was `0aea1414be40f63eafad046d62d2461e4d5b1f77`. IDs, booking URLs, earlier tariff/policy records and all original catalog fields are retained except the specifically sourced Honshuku availability correction. Latest AdSense/UI/payment changes remain intact; no AdSense reapplication.

## Priority Sports: Six Records

| Existing ID | Facility | Decision and official evidence |
| --- | --- | --- |
| `tokyo-venue-2b0bbd7157ff` | 秋留台公園 | Hold: [official field guide](https://www.tokyo-park.or.jp/park/akirudai/assets/akirudai-field.pdf) says group use is paid but the amount requires inquiry. Free individual track access is not free soccer hire. Grass competitive use is unavailable December 1 to March 31. No guessed price. |
| `tokyo-venue-8e6c0f81a52c` | 新川暫定広場 | [Facility guide](https://www.city.mitaka.lg.jp/c_service/079/079233.html) explicitly describes free use and registered ball-court reservations; [current October-onward rules](https://www.city.mitaka.lg.jp/c_service/079/079234.html) confirm eligibility and bookings. Record 0 yen for approved group use, separately per 2 hours and winter final 1.5-hour slot. Futsal groups need six competitive members, soccer nine, at least half local resident/worker/student; no commercial use. No day-of reservations or group reservations on second Saturday/fourth Sunday. Earlier cancellation record (system through seven days before, later contact) remains unchanged. |
| `tokyo-venue-c282bded258a` | 川町運動場少年野球場 | Hold: [city facility guide](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012073.html) confirms youth-only use, seasonal closure and restricted opening, but not a numerical hire tariff. No inference from unstaffed opening. |
| `tokyo-venue-205d87234dd3` | 府中朝日フットボールパーク | Hold: [city guide](https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/asahi.html) prices clubhouse rooms, not the association/event-use pitch. Those room amounts are not football hire prices. |
| `tokyo-gym-a231878afdcf` | 小金井市総合体育館 | Hold: [official group-hire page](https://www.koganei-sponavi.net/gymnasium/group/) links a group guide that could not be parsed reliably. No stale/truncated PDF amounts or individual entry fees used. |
| `tokyo-gym-aa77f48e78d0` | 本宿体育館 | [City notice updated October 25](https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/honshuku.html) confirms full closure November 2026 through end-February 2027, subject to change, and no private hire in October/March. Set SUSPENDED and preserve the record; hide from normal search. Old hire rates stay unknown. Earlier cancellation review is retained. |

## Other Tariff Additions: Fourteen Records

All amounts below are yen per specified room and time period, not hourly conversions or facility-wide minima. Equipment, other rooms, discounts and surcharges are excluded. Each fee option carries its own source URL, conditions and November 4 check date. Same-room/same-duration min/max ranges are derived from the recorded periods; different durations and eligibility categories are not combined.

| Existing ID | Exact scope | Verified periods and amounts | Official tariff |
| --- | --- | --- | --- |
| `tokyo-venue-d40445daf945` | ライフコミュニティ西馬込・会議室、区内通常 | Weekday 09–12: 860 / 13–17: 1,700 / 18–22: 2,500; weekend/holiday 980 / 2,100 / 3,100. 3h and 4h separate. | [Meeting room](https://www.city.ota.tokyo.jp/shisetsu/hall/community/life_kaigi0930.html) |
| `tokyo-venue-9f1e6da622bb` | 六郷集会室・第一集会室、区内通常 | Weekday 09–12: 1,700 / 13–16:30: 2,900 / 17:30–21:30: 4,700; weekend/holiday 1,700 / 3,500 / 5,600. 3h, 3.5h and 4h separate. | [First room](https://www.city.ota.tokyo.jp/shisetsu/hall/rokugosyuukaishitsu/daiichishukaishitsu.html) |
| `tokyo-venue-a01a8272f849` | 区立山王会館・集会室、区内通常 | Weekday 09–12: 1,500 / 13–17: 2,900 / 18–22: 4,300; weekend/holiday 1,800 / 3,500 / 5,100. | [Room](https://www.city.ota.tokyo.jp/shisetsu/hall/sannou_k/sannokaikan_shukaishitsu.html) |
| `tokyo-venue-acafbf43b734` | 多摩川集会室・第一集会室、区内通常 | Weekday 09–12: 740 / 13–17: 1,500 / 18–22: 2,200; weekend/holiday 860 / 1,700 / 2,600. Apply directly to facility, not assumed online. | [First room](https://www.city.ota.tokyo.jp/shisetsu/hall/tamagawasyuukai/tamagawa1.html) |
| `tokyo-venue-3dad1de4b1e7` | 嶺町文化センター・体育室 | 09–12 and 19–22 (3h): 1,700; 13–15:30 and 16–18:30 (2.5h): 1,400. Low-ceiling sport restrictions apply. | [City rooms and fees](https://www.city.ota.tokyo.jp/shisetsu/bunkacenter/minemachibunkacenter.html) |
| `tokyo-venue-f756c371fa95` | 新井宿会館・集会室、区内通常 | Weekday 09–12: 3,000 / 13–16:30: 4,500 / 17:30–21:30: 7,500; weekend/holiday 3,000 / 5,400 / 9,000. 3h, 3.5h and 4h separate. | [Room](https://www.city.ota.tokyo.jp/shisetsu/hall/araijuku_k/araijukukaikan_shukaishitsu.html) |
| `tokyo-venue-7f86d45f6b38` | カムカム新蒲田・第一集会室、区内通常 | 09–12 (3h): 1,600 / 13–17 and 18–22 (4h): 2,100. Not music-studio or main-hall rates. | [City-linked tariff PDF](https://www.city.ota.tokyo.jp/shisetsu/hall/shisetu_kamkamshinkamata.files/sisetusiyouryou3.pdf), [operator eligibility](https://shinkamata.jp/guide/) |
| `tokyo-venue-52d36d518953` | 羽田文化センター・第一集会室 | 09–12 (3h): 1,300 / 13–17 and 18–22 (4h): 1,800. This matches the listed 羽田1-18-13 address; gym at 羽田4-11-1 is a different building and not priced here. | [City guide](https://www.city.ota.tokyo.jp/shisetsu/bunkacenter/hanedabunkacenter.html) |
| `tokyo-venue-8d8fb7de1c48` | 萩中文化センター・体育室 | 09–12 and 19–22 (3h): 1,500; 13–15:30 and 16–18:30 (2.5h): 1,200. Not a regulation basketball court. | [City guide](https://www.city.ota.tokyo.jp/shisetsu/bunkacenter/haginakabunkacenter.html) |
| `tokyo-venue-17c00cfd90cb` | 中央町社会教育館・B102、その他団体 | 09–12 (3h): 2,800; each afternoon/evening 2.5h slot: 2,900. | [City tariff](https://www.city.meguro.tokyo.jp/shougaigakushuu/shisetsu/bunkakouryuu/chuocho.html) |
| `tokyo-venue-51e711229a72` | 区民センター社会教育館・701、その他団体 | 09–12 (3h): 3,600; each other 2.5h slot: 3,700. | [City tariff](https://www.city.meguro.tokyo.jp/shougaigakushuu/shisetsu/bunkakouryuu/kyoiku_kumin_center.html) |
| `tokyo-venue-d8e3b629e732` | 東山社会教育館・201、その他団体 | 09–12 (3h): 3,400; each other 2.5h slot: 3,500. | [City tariff](https://www.city.meguro.tokyo.jp/shougaigakushuu/shisetsu/bunkakouryuu/higashiyama.html) |
| `tokyo-venue-cf9e1adb9414` | 目黒本町社会教育館・303、その他団体 | 09–12 (3h): 2,800; each other 2.5h slot: 2,900. | [City tariff](https://www.city.meguro.tokyo.jp/shougaigakushuu/shisetsu/bunkakouryuu/kyoiku_megurohonmachi.html) |
| `tokyo-venue-13e7f69454a5` | 緑が丘文化会館・本館201、その他団体 | 09–12 (3h): 4,800; each other 2.5h slot: 5,000. | [City tariff](https://www.city.meguro.tokyo.jp/shougaigakushuu/shisetsu/bunkakouryuu/kyoiku_midorigaoka.html) |

Ota meeting-room tables describe roughly 20% nonresident surcharges: exact charged/rounded amounts are not synthesized. Cultural-center eligibility/possible surcharges are left for confirmation, not inferred. Meguro prices deliberately use the unrestricted-registration その他団体 tier, not the cheaper resident-certified tiers. [Registration](https://www.city.meguro.tokyo.jp/toubu/kusei/onlineservice/touroku.html) permits nonresident-only groups/individuals; [booking schedule](https://www.city.meguro.tokyo.jp/toubu/kusei/onlineservice/communityroom.html) starts their vacancy bookings one month ahead.

## Cancellation Evidence

- Eight Ota room/gym records: [official Uguisu guide](https://www.city.ota.tokyo.jp/shisetsu/uguisunet_annai/ugu.html) distinguishes unpaid system cancellation from paid counter procedures; user cancellation is generally nonrefundable with facility-specific exceptions. Exact rates/deadlines are not inferred from generic guidance. Park-only rain refunds and penalties are not extended to indoor rooms.
- Kamkam: the current [operator guide](https://shinkamata.jp/guide/) links the [cancellation example](https://shinkamata.jp/wp/wp-content/themes/actio/img/pdf/%E5%88%A9%E7%94%A8%E5%8F%96%E6%B6%88%E7%94%B3%E8%AB%8B%E6%9B%B8%E3%80%90%E8%A8%98%E5%85%A5%E4%BE%8B%E3%80%91.pdf). Thirty-plus days before: full refund; day-before/day-of: none; equipment cancellation before use: full. Intermediate percentage-to-row mapping was unclear in extraction and is explicitly not guessed. Original first-use date applies after changes. No ordinary-rain waiver confirmed.
- Five Meguro records: [current refund guide](https://www.city.meguro.tokyo.jp/toubu/kusei/onlineservice/shiyouryou.html), updated October 7, requires **20 / 10 / 5 intervening days** for 100% / 75% / 50%; both endpoint dates are excluded, and closing days can bring the deadline forward. Cash and card refund routes differ. Community-room disaster conditions require pre-use notification in principle; do not self-cancel card-paid disaster refunds or assume ordinary rain qualifies.

## Verification and Release

`scripts/test_venue_fee_followup_20261104.py` checks actual zero versus unknown, exact units/rooms/tiers, address matching, cancellation bounds, closure visibility, ID/booking preservation, append-only history, idempotence and conflict refusal before writes. Historical checks allow only the exact sourced Honshuku correction and the exact Shinkawa tariff resolution; other changes still fail. Test, browser and production release evidence is recorded privately with the final release commit/deploy ID.
