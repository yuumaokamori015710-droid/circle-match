# Tokyo Venue Fee Follow-Up, 2026-10-25

## Scope And Result

- Baseline: latest GitHub main `3cac8975957073fb4d7bee6730e17398fa295e01`, including Oct24 venue and contact releases.
- 21 physical facilities, represented by 22 existing records, reviewed. Sakuragaoka has two existing alias IDs, not two physical facilities.
- 16 tariff records and 13 cancellation records added; six tariff holds remain unknown, not zero.
- Catalog: 1,206 records, 801 priced, 405 unpriced including eight suspended; 397 active records remain unpriced.
- Original three catalogs, IDs, names, sports, booking URLs and previous tariff/policy records unchanged. No environment, plan, schema, booking or payment changes.
- Official pages and currently linked operator PDFs checked on 2026-10-25 JST. Local evidence retains response metadata/hashes, original documents and visual PDF review. Failed connections were not rapidly retried or replaced with guesses.

Ranges cover the stated space, duration and reviewed conditions only, not every possible equipment, commercial or discounted tariff.

## Added Tariffs

| Existing ID | Facility And Same-Unit Tariffs (Yen) | Official Evidence |
| --- | --- | --- |
| `tokyo-gym-bc35a0a1e3c2` | Fujimori gym: main full 9,000/2h50m, 10,500/3h; half 4,500/2h50m, 5,200/3h. Annex full 4,200/2h50m, 4,800/3h; half 2,100/2h50m, 2,400/3h. | [City tariff](https://www.city.hachioji.tokyo.jp/shisetsu/104/p025060.html), [defects/future closure](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012106.html) |
| `tokyo-gym-132a18a63ed5` | Kounohara: room1 full 3,600/2h50m, 4,200/3h; half 1,800/2h50m, 2,100/3h. Room2 1,600/2h50m, 1,700/3h; room3 1,000/2h50m, 1,200/3h. | [Designated operator](https://information.konamisportsclub.jp/trust/kounohara/pricing/) |
| `tokyo-venue-a2d6191898f8` | Hikari: available second room only, citizen/nonresident 1,000–2,000/2h30m, light exercise. First room stopped; no basketball/volleyball court tariff added. | [Current city tariff/room uses](https://www.city.kokubunji.tokyo.jp/shisetsu/sport/hikari/1004200.html), [operator closure](https://www.kokubunji-sports.net/new/7175/) |
| `tokyo-gym-bd292e78d64f` | Fuchu Lifelong Learning Center: full 2,500–3,700/2h30m, 3,000–6,000/3h; half 1,200–1,800/2h30m, 1,500–3,000/3h. Morning/night labels retained. | [Exact city table](https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/syougaigakusyuu.html), [operator corroboration](https://fuchu.shogaigakushu.jp/guide) |
| `tokyo-venue-d0be017dbb50` | Yatozawa ground full: Tokyo youth/general/admission-charging 500/1,000/2,000 per hour. | [Town facility page](https://www.town.hinode.tokyo.jp/0000000154.html) |
| `tokyo-venue-455b065cd3a8` | Yatozawa soccer full: Tokyo youth/general/admission-charging 3,000/6,000/12,000 per hour. May–October only. | [Town facility page](https://www.town.hinode.tokyo.jp/0000000155.html) |
| `tokyo-venue-9b83c8d54781`, `tokyo-venue-f03ca8d7146e` | Same S&D Field Sakuragaoka: full 450–1,800, A 250–1,000, B 200–800 per booking unit. Normal 2h and March–October 16–19h (3h) are separate units, same posted amount. | [Operator PDF](https://www.higashiyamato-taiikukan.com/_files/ugd/b5659a_5d9395de9937446eb7d46894b621a412.pdf), [city identity](https://www.city.higashiyamato.lg.jp/shisei/shiyakusho/shisetsu/sports/1006850.html) |
| `tokyo-venue-f8ec50340ea7` | Kiyohara full: youth/general 3,900–7,800 per unit, separately recorded for normal 2h and March–October 16–19h (3h). | [Operator PDF](https://www.higashiyamato-taiikukan.com/_files/ugd/b5659a_8777533f47564dc59e0f9aff5c6b1d62.pdf), [time-slot note](https://www.higashiyamato-taiikukan.com/清原中央公園運動広場) |
| `tokyo-gym-9387fcd334e9` | Higashiyamato S&D gym /2h30m: room1 full/half 9,600/4,800; room2 4,600/2,300; room3 2,600/1,300. Different room uses retained. | [Operator PDF](https://www.higashiyamato-taiikukan.com/_files/ugd/21c974_2146814578aa4dd183435800952630c8.pdf) |
| `tokyo-venue-1a933984b689` | Higashihara full 2,400/2h, half 1,200/2h. Separate lighting full 3,000/hour, half one-half. | [Operator](https://www.omesports.net/facility/higashihara) |
| `tokyo-gym-3fc84a0cf785` | Ome: hall1 full 9,000/3h, 12,000/4h; half 4,500/3h, 6,000/4h; quarter 2,250/3h, 3,000/4h. Martial-arts hall2 full 1,500/3h, 2,000/4h; half 750/3h, 1,000/4h. | [Operator](https://www.omesports.net/facility/gymnasium) |
| `tokyo-gym-efd5e350238b` | Kumagawa: personal-use room1 70–150/person/90min, not group hire. Ordinary hire unavailable. | [Operator room1](https://fussa-kumagawa.com/gym-1/), [room2 also personal only](https://fussa-kumagawa.com/gym-2/) |
| `tokyo-gym-e6782f27b40b` | Fussa area gym: second room hire citizen child/adult/nonresident 400/800/2,400/hour. Every user must meet citizen conditions. Room1 ordinarily personal only. | [Operator second room](https://fussa-fussa.com/facility/?facility=facility_arena-2), [first room](https://fussa-fussa.com/facility/?facility=facility_arena-1) |
| `tokyo-venue-71237581c393` | Ikebukuro Sports Center: white-wood or tatami martial-arts room, each 3,600/3h; not ball-court hire. | [City page](https://www.city.toshima.lg.jp/501/bunka/sports/sports/003418/003496.html) |
| `tokyo-venue-2e14b39dc02c` | Nishisugamo tennis 1,000/court/hour posted unit, actual booking blocks 2h or 3h; not futsal hire. | [City page](https://www.city.toshima.lg.jp/501/bunka/sports/sports/003418/003476.html) |

Hachioji's future April2027 rates are excluded. Fujimori main hall closure is planned Dec14,2026–Jan15,2027; third room Dec14–28,2026. Higashiyamato's operator PDFs were visually compared with the municipal ordinance; ordinance ceilings alone were not treated as operator tariffs. Nonresident multipliers were not invented. Admission-charging rates are included only where expressly listed for Yatozawa; the other listed ordinary ranges exclude those surcharges.

## Holds

| Existing ID | Official Review And Reason No Tariff Was Added |
| --- | --- |
| `tokyo-venue-f403faf4f42f` | [Nakahara Sports Children's Park](https://www.city.mitaka.lg.jp/c_service/053/053763.html): group practice-area registration and unreserved personal use confirmed; exact current group fee not found on inspected page. Missing fee is not free hire evidence. |
| `tokyo-venue-8e6c0f81a52c` | [Shinkawa, rules effective Oct1](https://www.city.mitaka.lg.jp/c_service/079/079234.html): group eligibility/public opening/cancellation confirmed, group fee unstated. Free public opening is not zero-price group hire. |
| `tokyo-venue-5b81852866ce` | [Fujimori outdoor/athletics field](https://www.city.hachioji.tokyo.jp/life/010/002/003/004/p012068.html): linked detailed tariff PDF connection reset. Individual entry/free community opening do not establish soccer hire rates. No immediate retry. |
| `tokyo-venue-c282bded258a` | [Kawamachi youth baseball](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012073.html): middle-school-age-or-younger restriction confirmed, current exact charge unstated. Historic free-use tables not substituted. |
| `tokyo-venue-205d87234dd3` | [Fuchu Asahi Football Park](https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/asahi.html): ground/clublounge limited to official federation/association competitions, no ordinary public group hire. Ordinance ground and meeting-room prices not published as publicly bookable soccer hire. |
| `tokyo-gym-aa77f48e78d0` | [Honshuku gym](https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/honshuku.html): no gym hire acceptance in October or March; full closure planned November2026–February2027. Posted hire table not published as current bookable hire. |

Sport/space mismatches are qualified in fee notes rather than deleting, merging or renaming existing identities. Kumagawa personal use remains distinct from hire. Hikari's available second room and Ikebukuro's martial-arts rooms do not imply basketball/volleyball availability.

## Cancellation Evidence

- Shinkawa: [Oct1 procedure](https://www.city.mitaka.lg.jp/c_service/079/079234.html), online through seven days before, later contact department. No invented refund rate.
- Four Hachioji IDs: [city guide](https://www.city.hachioji.tokyo.jp/shisetsu/104/p005417.html), online by previous day, phone on day. Outdoor day-of/no-show restricts future booking for three months from the second subsequent month, not cash penalties. Fujimori/Kounohara payments nonrefundable. No unsupported weather exemption.
- Asahi: [ordinance Article10](https://www1.g-reiki.net/city.fuchu.tokyo/reiki_honbun/g130RG00000266.html), normally nonrefundable; qualifying reasons may permit part/full return. No invented deadline.
- Honshuku: [city cancellation procedure](https://www.city.fuchu.tokyo.jp/shisetu/supotu/yoyaku/torikesi.html), one calendar month before 100%, ten days before 50%, nine days onward 0%; documents and published rounding retained. Not automatically applied to separately administered Lifelong Learning Center.
- Two Yatozawa facilities: respective current pages expressly disallow personal-convenience cancellation, allow rain etc. Exact refund percentages, deadlines and weather determination unstated.
- Four Higashiyamato IDs: corresponding operator PDFs above, seven-day counter deadline (previous day if closed), return to reservation-ID credit and later counter offset. Not automatically cash reimbursement. Late unavoidable-reason exceptions require facility judgment. Sakuragaoka weather/heat calls are from 30min before start; this ground-specific condition is not applied to the gym.
- Other cancellation policies remain unknown, not assumed free or prohibited.

## Verification And Publication

Importer preflights IDs/current prices/conflicts in both files before append and is idempotent. Tests preserve original catalog fields and historical review prefixes, distinguish person/hire/space/time units, stopped rooms and exact rounding. Historical tests now assert the narrow Oct25 verified spaces rather than indefinitely requiring previously unknown prices.

Local verification passed: 144 venue tests, 15 sport-navigation tests, eight SEO tests and the standalone event-flow runner (`event flow: ok`). The Oct25 browser matrix passed all 22 records at 390/768/1440/1920px plus four no-JavaScript cases (92 total), checking SSR, every tariff, cancellation text, source/booking links and overflow. Mobile/desktop screenshots were visually reviewed. Local screenshots/evidence stay outside version control.

Publish reviewed tracked files on latest main, then verify matching commit Live on existing Render service `srv-d9378v67r5hc73bmv3cg` in workspace `tea-d92j9m6rnols7398l8vg` and production `/venues` and `/api/venues`. Do not treat a queued deploy as Live.

No user login, paid subscription, inquiry, reservation or payment performed. No user action required for verified additions. Six holds need future usable official fee evidence or clarified public eligibility.
