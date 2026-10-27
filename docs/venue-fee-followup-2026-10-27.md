# Tokyo Venue Fee Follow-Up, 2026-10-27

## Scope And Result

- Latest fetched GitHub main baseline: `55a7ff321a43d845c15ebd9fc075aa745393745f`.
- 26 existing records reviewed: 14 newly priced, 15 cancellation/weather records added, 12 tariff holds retained. Soccer/futsal and indoor-sport holds were checked first, followed by unpriced baseball/athletics facilities.
- Catalog remains 1,206 records: 830 priced, 376 unpriced including nine suspended, 367 active unpriced.
- Kameido baseball/tennis is newly marked suspended in the combined catalog. Its existing booking note already mentioned closure; the structured status now agrees. The legacy tennis record was already suspended and is unchanged. Three other closures below were already recorded and are not counted as new.
- IDs, names, addresses, sports, reservation URLs, legacy tennis data and every previous fee/policy record are preserved. Only Kameido's availability status/note, source append and check date change in the original expansion catalog. Staged Oct26 contact-research documents are preserved separately, not included in this venue commit.
- Official public pages were retrieved October27 JST with timestamps and hashes in untracked `work/venue-fee-review-20261027/sources`. No inquiry, reservation, payment, login, environment, service plan or database schema changes.

Prices below cover the exact named space, billing unit and conditions, not all commercial, equipment, discount or full-day tariffs. Unknown fees remain unknown, not zero. Free use is adopted only when explicitly confirmed for the applicable registered junior group.

## Added Tariffs

| Existing ID | Scope And Confirmed Yen | Official Source |
| --- | --- | --- |
| `tokyo-venue-048bb49572f3` | ThreeBond Stadium Hachioji: 8,000/one baseball field/2h. Lighting separately 18,000/2h; no spectator parking. | [City facility](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012122.html) |
| `tokyo-venue-16bb2c8850d1` | Kamiyugi baseball: 8,000/one field/2h. Do not borrow another park's lighting fee. | [City facility](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012126.html) |
| `tokyo-venue-4a8e4a8753a7` | Kamiyugi softball: 2,000/one field/2h. Adult baseball prohibited; junior rubber-ball baseball permitted. | [City facility](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012128.html) |
| `tokyo-venue-3cfb27df8e7a` | Kamiyugi track group hire: 20,000/4h, lighting separately 15,000/4h. Individual 50–200 entry and passes excluded. | [City facility](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012069.html) |
| `tokyo-venue-1c7e242fd790` | Kitano: 4,000/one baseball field/2h; lighting separately 6,000/2h. | [City facility](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012123.html) |
| `tokyo-venue-5e7a80249c77` | Otsuka: 2,000/one baseball field/2h, rubber-ball baseball/softball. | [City facility](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012125.html) |
| `tokyo-venue-606b9074a6ba` | Fujimori track's existing athletics record: personal entry adult200, high-school100, elementary/middle-school50, per person per entry. Not group hire, nor free community opening. Existing football-field alias and its prior restricted group tariff retained. | [City facility](https://www.city.hachioji.tokyo.jp/life/010/002/003/004/p012068.html) |
| `tokyo-venue-649d27923ae4` | Takigahara: baseball2,000/one field/2h; softball1,000/one field/2h, separate units. Hardball prohibited. | [City facility](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012130.html) |
| `tokyo-venue-e2bb272043d2` | Nishiterakata: 1,000/one baseball field/2h. The separate softball field is not an additional included field. | [City facility](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012127.html) |
| `tokyo-sports-032` | Kita Chuo Park baseball: general2,920/one field/2h; qualified registered juniors exempt. Lighting separately6,160/2h, general total9,080; exemption does not establish free lighting. | [City facility](https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010393/1010396/1010397.html) |
| `tokyo-venue-58eea0a2f035` | Iwabuchi: junior-only field, explicitly free/one field/normal2h slot. Not an adult group offer. | [City facility](https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010393/1010396/1010400.html) |
| `tokyo-venue-49f6c14142ff` | Shin-Arakawa Ohashi baseball: general1,200/one field/2h; qualified registered juniors exempt. Winter one-hour slots not guessed from the two-hour price. | [City facility](https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010393/1010396/1010398.html) |
| `tokyo-venue-3766e52a081e` | Yumenoshima: rubber-ball baseball2,700–3,700/one field/2h; junior field650–800/one field/2h, only Koto elementary/middle-school registered groups. Other groups pay normal baseball rates. Lighting4,600/hour separately; no junior lighting. | [Operator table](https://www.di-ksp.jp/facility/yumenoshima_u) |
| `tokyo-venue-f8e9ad9cee63` | Shiomi: baseball/softball2,700–3,700/one field/2h; tennis1,100–1,800/one court/hour, different units. Lighting separately4,600/hour for field,1,800/hour for tennis. Free practice wall is not court hire. | [Operator table](https://www.di-ksp.jp/facility/shiomi) |

Kita junior registration requires ten or more elementary/middle-school members, seven of ten residing/working/studying in Kita, with adult representative/deputy. Outside-ward junior registration is unavailable. Exemption requires the counter procedure, not online payment. See the [October27 registration guide](https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010393/1010394.html) and [current sports guide](https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010441.html). Ordinary slot, seasonal opening, approval and registration restrictions remain in each fee note.

## Holds And Closures

| Existing ID | Evidence And Decision |
| --- | --- |
| `tokyo-gym-a231878afdcf` | [Koganei operator group guide](https://www.koganei-sponavi.net/gymnasium/group/) links a PDF that again returned exactly1,048,576 bytes with invalid EOF. No tariff read from partial PDF, no rapid repeat fetch. Personal prices not substituted. |
| `tokyo-gym-c9fd2d3160d0` | [Arakawa official guide](https://www.city.arakawa.tokyo.jp/a017/sport/shisetsuriyou/s-houseriyou.html): closed March31,2025–lateMarch2027 planned. Posted rates explicitly pre-renovation. Existing suspended status preserved; no current tariff adopted. |
| `tokyo-venue-ec7d0ac023ca` | [City April1 bulletin index](https://www.city.higashikurume.lg.jp/shisei/koho/kouhoushi/1028321/1028861.html), page7 closure notice: Seibu abolished March31,2026 on land return. Existing closure retained, not free bookable hire. |
| `tokyo-venue-6b06aed3958d` | [Fussa October13 guide](https://www.city.fussa.tokyo.jp/education/sports/1002683.html): baseball field closed July2026–May2027 planned. Existing suspended status retained. Other futsal/field rates not copied here. |
| `tokyo-venue-205d87234dd3` | [Fuchu Asahi](https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/asahi.html): association/federation events, not ordinary general-group ground hire. Meeting-room fees not soccer charges. |
| `tokyo-venue-2b0bbd7157ff` | [Akirudai field guide](https://www.tokyo-park.or.jp/park/akirudai/assets/akirudai-field.pdf): paid group hire, amount requires inquiry. Free personal athletics not soccer hire. No inquiry sent. |
| `tokyo-venue-8e6c0f81a52c` | [Shinkawa group-use guide](https://www.city.mitaka.lg.jp/c_service/079/079234.html): exact group fee absent. No inference of free group hire; prior cancellation record retained. |
| `tokyo-venue-c282bded258a` | [Kawamachi](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012073.html): junior-only, seasonal/weekday constraints; exact fee absent. Prior cancellation policy retained. |
| `tokyo-venue-456ad6cd0311` | [Kunugida](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012075.html): no exact fee in current facility guide. Unknown retained, not zero. |
| `tokyo-venue-40fd2672b512` | [Takakura](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012124.html): no exact fee. Unstaffed facility requires application at Fujimori gym one week before; omission causes cancellation/penalty. |
| `tokyo-venue-3df7eec0d53c` | [Koto current guide](https://www.city.koto.lg.jp/104010/bunkasports/sports/torikumi/6384.html): baseball and tennis closed since April1,2025 for demolition/removal, reopening undecided. Structured suspended status added, record and booking URL retained. |
| `tokyo-venue-74f8af5c1bc3` | [Yumenoshima East city page](https://www.city.koto.lg.jp/104010/shisetsuannai/kokyo/sportsshisetsu/yakyu/16166.html): Koto junior registered groups only, exact tariff absent. Distinct from the junior sections inside Yumenoshima baseball park;650–800 not copied. |

## Cancellation And Weather

- Eleven Hachioji records without an existing policy receive the [city-wide outdoor cancellation rules](https://www.city.hachioji.tokyo.jp/shisetsu/104/p005417.html): cancel promptly, system through previous day, facility telephone on day. On-day/no-show prevents new lottery/vacancy bookings for three months starting the first of the second following month. Existing bookings survive. This is a booking restriction, not a monetary cancellation fee. Rain exceptions/refund percentages unverified. Takakura's one-week application requirement is explicit. Kawamachi's prior record is untouched.
- Kita Chuo and Shin-Arakawa use the [current city sports rules](https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010441.html):14days or earlier full refund/transfer,13–7days half,6days through use day none. Unpaid late cancellations also require payment before the specified refund. Paid cancellations only at sports counters, not phone; registered-member identification required. Junior exemptions are not a demand for adult fees. No unsupported rain refund inferred.
- Yumenoshima and Shiomi operator pages require checking weather usability with management before use. Self-convenience deadlines, fees and rain-refund percentages are not stated there; unknown remains explicit rather than treating unusable weather as automatic cash refund.

## Verification And Publication

Importer preflights every existing tariff/policy conflict, refuses overwriting prior reviews and is idempotent. Ten new regression tests cover exact units, three restricted junior exemptions, current closure/default filtering, policies and baseline preservation. Historical preservation tests permit only the named Kameido metadata correction; earlier source prefixes, IDs, booking links and tariffs still compare exactly.

Verification:165venue tests,15sport-navigation tests,8SEO tests and standalone event flow; mobile/desktop browser matrix covers all26records at390/768/1440/1920px, four default-closure-hiding checks and four JavaScript-disabled checks (112cases). Expected source and reservation links, exact published tariffs, full tariff rows, policy text, SSR, clipping and overflow are checked. Screenshots and isolated test databases stay untracked.

Publication requires latest main push, matching-commit Render Live on service `srv-d9378v67r5hc73bmv3cg` in workspace `tea-d92j9m6rnols7398l8vg`, and the same production browser/API checks at `https://circle-match.jp/venues`. Final commit/deploy/verification evidence is recorded in untracked `work/venue-fee-review-20261027/publication.json`; queued/building is not success. No user action is needed for verified additions. Held fees require future complete official evidence, not credentials, paid subscriptions or outreach in this run.
