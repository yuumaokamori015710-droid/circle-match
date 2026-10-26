# Tokyo Venue Fee Follow-Up, 2026-10-26

## Scope And Result

- Baseline latest GitHub main: `657654c373c803a1a8d46bf9ea0cb1c01e471f26`, retaining the Oct25 venue and contact releases.
- 22 existing facilities reviewed; 15 tariff records and six cancellation/interruption records added; seven tariff holds remain unknown.
- Catalog: 1,206 records, 816 priced, 390 unpriced including eight suspended; 382 active records remain unpriced.
- Original three catalogs, IDs, names, sports, booking URLs and historical fee/policy prefixes unchanged. No environment, plan, schema, inquiry, reservation or payment changes.
- Official sources retrieved on 2026-10-26 JST. Cached HTML/PDF, response metadata and hashes stay in untracked local evidence. Complete fee tables were visually reviewed where PDF layout matters. Failed or truncated sources were not replaced by guessed rates.

Ranges apply to the named space, duration and conditions only, not every commercial, discounted, equipment or full-day tariff. Existing sport tags are preserved, with restricted uses explicitly qualified in fee notes.

## Added Tariffs

| Existing ID | Facility And Same-Unit Tariffs (Yen) | Official Evidence |
| --- | --- | --- |
| `tokyo-gym-77213713f20f` | Kawai gym: general registered 500/2h, specific registered 3,000/2h. General requires town residence/work etc; specific requires five or more out-of-town users and lodging in town. Free field is not gym hire. | [Town facility](https://www.town.okutama.tokyo.jp/1/kyoikuka/bunka_sports/1/1/1048.html) |
| `tokyo-gym-3d46bb173da3` | Nippara gym: general 500/2h, specific 2,000/2h, same registration/lodging conditions; Nippara Hoshokai manages use. | [Town facility](https://www.town.okutama.tokyo.jp/1/kyoikuka/bunka_sports/1/1/647.html) |
| `tokyo-venue-15fb9fbe4c57` | Nakanogo: outdoor 250/hour, indoor 500/hour, separate spaces. | [Current town table](https://www.town.hachijo.tokyo.jp/kurashi/shisetsu/taiikukan/), [facility identity](https://www.town.hachijo.tokyo.jp/kanko-bunka/kanko-sports/sports/) |
| `tokyo-venue-fbb6eed2f3b0` | Kashitate: outdoor 250/hour, indoor 500/hour, separate spaces. | [Town table](https://www.town.hachijo.tokyo.jp/kurashi/shisetsu/taiikukan/) |
| `tokyo-venue-9cf3b539f28b` | Sueyoshi: outdoor 250/hour, indoor 500/hour. Outdoor lighting separately 250/hour, not mixed into indoor fee. | [Town table](https://www.town.hachijo.tokyo.jp/kurashi/shisetsu/taiikukan/) |
| `tokyo-venue-d53efa57a050` | Nambara: soccer one court 500/hour. Registration/application/permission required, ordinarily no individual use. Admission-charging rates excluded. | [Town table](https://www.town.hachijo.tokyo.jp/kurashi/shisetsu/taiikukan/) |
| `tokyo-venue-aac633c1f3fe` | Nishi-Chofu: one 260sqm room, citizen/nonresident 1,200–2,400/3h. Low ceiling prohibits basketball, volleyball and badminton; this is table-tennis/martial-arts/exercise hire, not a badminton-court offer. | [City facility](https://www.city.chofu.lg.jp/040070/p026079.html) |
| `tokyo-venue-a047783f25fd` | Arakawa-Todabashi track/field group hire 3,600/hour. Free personal track use expressly excludes field and group occupation. | [Operator fee/conditions](https://www.shisetsu-tds.jp/tokyo-itabashi-arakawatodabashi-rikujou/fee/) |
| `tokyo-venue-4422731f5921` | Musashino Chuo sports field A/B each free per use, residents/nonresidents alike. No invented fixed-duration hourly unit. Counter booking only, four weeks ahead; separate tournament/construction closures apply. | [Foundation facility](https://www.musashino.or.jp/sports/1001550/1001573.html), [Oct/Nov closure notice](https://www.musashino.or.jp/sports/1001575/1003373.html) |
| `tokyo-venue-3a4d82e5e208` | Shonen: existing multi-use-field record 1,000/2h. Address is Adachi but operator is Arakawa; other baseball/soccer sections' 300/750 tariffs excluded. Arakawa registration eligibility applies. | [Arakawa city guide](https://www.city.arakawa.tokyo.jp/a017/sport/shisetsuriyou/shounenriyou.html) |
| `tokyo-venue-299cd43c6cce` | Arakawa riverside soccer: weekday Taito registered 1,100, outside 1,650; weekend/holiday 1,300/1,950, all one court/2h. Address in Adachi is not the tariff municipality. Parking excluded. | [Taito city guide](https://www.city.taito.lg.jp/gakushu/sports/sportssisetsuichiran/arakawa/arakawakasenjiki.html) |
| `tokyo-gym-3ca2e0f9828f` | TAC Higashimurayama existing room2 only: summer early 3,100–6,200/1h50m; ordinary 4,300–8,600/2h30m; late 4,300–8,600/2h40m. Seven-person registration; majority town residence/work/study for base rate, outside double. Nov5 gym closure retained. | [Operator current guide](https://www.higashimurayama-sportscenter.jp/?s=1&mode=h&type=group), [closure](https://www.higashimurayama-sportscenter.jp/info/8449/) |
| `tokyo-gym-f3e1aaf426e5` | Keio Arena existing subarena only, admission-free sports A/B and morning/afternoon/night 4h slots: half 7,000–22,000, full 14,000–44,000. A is internal participant use; B includes multi-team tournaments, not student discount. Half hire from two months ahead with full priority; equipment extra. | [Current operator PDF](https://keio-arena.tokyo/information/pdf/pricelist.pdf), [current linked index](https://keio-arena.tokyo/information/) |
| `tokyo-venue-f403faf4f42f` | Nakahara: registered practice-area group use explicitly free, 1 area/2h. 2025 city guide printed p3 corroborated with Oct20,2026 facility registration/use guide. Three small practice areas, not match-sized. Futsal six-person registration exception is explicit. | [City fee guide](https://www.city.mitaka.lg.jp/c_service/103/attached/attach_103305_4.pdf), [current facility](https://www.city.mitaka.lg.jp/c_service/053/053763.html) |
| `tokyo-venue-5b81852866ce` | Fujimori outdoor competition field: permitted group hire full 15,000/3h or less, half 7,500/3h or less. Youth/association, city-group sports-day and approved event restrictions retained; personal applicants cannot book as groups. Lighting 3,000 and soccer equipment 2,000 per 3h extra. Individual entry 50–200/free opening not mixed. | [Current linked city PDF](https://www.city.hachioji.tokyo.jp/life/010/002/003/004/p012068_d/fil/syuti.pdf), [current facility](https://www.city.hachioji.tokyo.jp/life/010/002/003/004/p012068.html) |

## Holds

| Existing ID | Official Evidence And Reason |
| --- | --- |
| `tokyo-venue-2b0bbd7157ff` | [Akirudai official PDF](https://www.tokyo-park.or.jp/park/akirudai/assets/akirudai-field.pdf): group hire paid, amount requires inquiry. Free personal athletics is not free soccer hire; winter grass restriction remains. No inquiry sent. |
| `tokyo-venue-8e6c0f81a52c` | [Shinkawa Oct1 procedure](https://www.city.mitaka.lg.jp/c_service/079/079234.html) and city sports guide: group fee unstated. Public personal opening does not prove free group hire. Prior cancellation record preserved. |
| `tokyo-venue-c282bded258a` | [Kawamachi youth field](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012073.html): middle-school-age-or-younger and seasonal/day restrictions; exact current price absent. Historic free assumptions not substituted. |
| `tokyo-venue-205d87234dd3` | [Fuchu Asahi](https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/asahi.html): federation/association events, ordinary general groups cannot hire ground. Meeting-room fees not soccer hire. |
| `tokyo-gym-aa77f48e78d0` | [Honshuku updated Oct25](https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/honshuku.html): no hire acceptance October/March; full closure November2026–February2027. Posted hire tariff not presented as current public hire. |
| `tokyo-gym-a231878afdcf` | [Koganei operator group index](https://www.koganei-sponavi.net/gymnasium/group/): linked PDF response truncated at 1MiB and failed EOF validation; existing hold maintained. Personal-use prices are not large-gym group hire. No rapid repeat fetch. |
| `tokyo-gym-d56f81f38406` | [Para training operator guide](https://tokyo-ptc.jp/guide/): robots retrieval unavailable, stopped without bypass. Partial search information on disability eligibility does not establish unrestricted group charges; no tariff adopted. |

## Cancellation Evidence

- Kawai: weekday education-department notice, normally no refund, education-committee cancellation exceptions. No invented generic rain waiver or deadline.
- Nishi-Chofu: on-day notice to local manager before start. No unsupported refund percentage or indoor weather exemption.
- Arakawa-Todabashi: weather/condition cancellation refund, caller checks Azusawa gym on day; no outbound cancellation notice. Approval paper and counter refund, direct-debit groups need no procedure.
- Shonen: heatstroke special-alert closure only; ordinary heat, weather refunds and personal-convenience deadlines unverified.
- Taito riverside: two calendar months before 100%, 15 days before 80%, seven days before 50%, six days to day zero refund. Management-declared unusable ground refunded with documents; page's obsolete heat-information name is flagged, not generalized to modern alerts.
- Keio: cancellation form by fax/mail/counter; normally nonrefundable. Unavoidable reason by remaining-payment deadline permits refund minus 10% deposit. Deposit due within one week of application; balance within one month of application, not one month before use. Within-one-month bookings pay together.
- All six records use the corresponding official sources above, checked Oct26. No policy copied to another venue by analogy. Previously published policies remain unchanged.

## Verification And Publication

Importer preflights both append files and priced-record conflicts and is idempotent. Regression tests compare every original catalog and the exact pre-review historical prefixes. Two historical test files now assert only the newly verified Nakahara/Fujimori entries instead of indefinitely requiring unknown values.

Local verification passed: 155 venue tests, 15 sport-navigation tests and eight SEO tests (178 total), plus the standalone event-flow runner (`event flow: ok`). The browser matrix passed all 22 records at 390/768/1440/1920 pixels plus four no-JavaScript mobile/desktop cases (92 total): SSR, exact tariffs, source/booking links, cancellation text, price clipping and page overflow. Mobile and desktop screenshots were visually reviewed. Test databases and screenshots remain isolated in untracked work files.

Publication is through latest main and the existing commit-triggered Render auto-deploy, without changing service settings. Final evidence must confirm the matching commit is Live on `srv-d9378v67r5hc73bmv3cg`, workspace `tea-d92j9m6rnols7398l8vg`, and that the same browser matrix and `/venues`/`/api/venues` pass on `https://circle-match.jp`. The deploy ID, commit and production verification results are retained in local `work/venue-fee-review-20261026/publication.json`; queued/building is not treated as completion.

No user action is needed for the verified additions. Seven held fees require future usable official evidence or clarified eligibility, not credentials, paid access or outreach in this run.
