# Tokyo Venue Fee Follow-Up, 2026-10-28

## Scope And Result

- Latest fetched GitHub main baseline: `83d63902d840ddfd5b866e7e5575357d2995c030`. The Komazawa admission/payment release and all earlier venue/contact work are preserved.
- 21 existing facilities reviewed. The six unresolved soccer/futsal/indoor facilities were checked first, followed by eight Nerima community/hall facilities, four outdoor sports facilities and three private tennis holds.
- 12 previously unpriced records receive tariffs, 12 cancellation/weather records are added, and nine tariff holds remain unknown. Inventory remains 1,206: 842 priced, 364 unpriced, including nine suspended (355 active unpriced).
- Only `fee_plans.json` and `cancellation_policies.json` receive appended records. Original catalogs, every facility ID/name/address/sport/booking URL, all previous fee/policy entries, private settings and the legacy tennis catalog remain unchanged. No database schema, event settings, environment variables, hosting plans or other automations change.
- Public official sources were retrieved on October 28 JST. Response bytes, SHA-256 hashes and source URLs are archived privately in `work/venue-fee-review-20261028/sources/`. Complete PDF pages were visually checked for Seki and Musashino. No inquiries, reservations, payments or login-required content were submitted/accessed.

## Added Tariffs

All amounts are JPY, for the explicitly named room/field and unit only. Different room, duration, resident or registration conditions have separate range units. Rates are not converted to an hourly equivalent. Equipment, lighting and other omitted special uses are not silently included.

| Existing ID | Confirmed Scope | Primary Source |
| --- | --- | --- |
| `tokyo-venue-fb993a9bd6f1` | Kitamachi: six rooms, general 100–400/hour; eligible registered community groups pay half. Each room and registration category are separate units. | [Ward room table](https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/kitamachi.html) |
| `tokyo-venue-f9757579e50e` | Hayamiya: six rooms, general 100–400/hour; eligible community groups half. | [Ward room table](https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/hayamiya.html) |
| `tokyo-venue-88a2836410aa` | Sakuradai: six rooms, general 100–300/hour; eligible community groups half. | [Ward room table](https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/sakuradai.html) |
| `tokyo-venue-18ca308ccdfb` | Hikawadai: six rooms, general 100–600/hour; eligible community groups half. | [Ward room table](https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/hikawadai.html) |
| `tokyo-venue-e50943c53e95` | Toyotama Kita: seven rooms, general 100–300/hour; eligible community groups half. Child/library rooms are rentable only outside their public-opening programs. | [Ward room table](https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/toyotama.html) |
| `tokyo-venue-4d2338f59594` | Takamatsu: four rooms, general 100–300/hour; eligible community groups half. School-club rooms are not rentable free rooms. | [Ward room table](https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/takamatsu.html) |
| `tokyo-venue-caef0b487244` | Hikarigaoka hall: multipurpose hall 5,400/3h or 7,200/4h; meeting rooms 1/2 each 1,800/3h or 2,400/4h, combined 3,300/3h or 4,400/4h; conference room 1 is 2,100/3h or 2,800/4h, conference room 2 is 1,800/3h or 2,400/4h. | [Ward room guide](https://www.city.nerima.tokyo.jp/shisetsu/bunka/kuminhall/hikarigaokakuminnhor.html) |
| `tokyo-venue-b87866a9fdd9` | Seki hall: multipurpose 5,400/3h or 7,200/4h; rehearsal 400/hour. New-system rehearsal hourly units are not the old multi-hour period fee. Other center rooms/equipment excluded. | [Operator August 7 guide, page 10](https://www.nerima-swf.jp/datas/seki_hol/pdf/020260815111033_SJE3r.pdf) |
| `tokyo-sports-031` | Shingashi athletics group hire 3,600/hour. Not personal entry or Arakawa Todabashi's multipurpose field. | [Designated operator](https://www.shisetsu-tds.jp/tokyo-itabashi-shingashi-rikujou/fee/) |
| `tokyo-venue-c698a2f4c1f9` | Musashino baseball, one field/2h: resident 2,000, nonresident 4,000, with no participant/admission charge. Fee-charging use has a separate 3x rule; combined nonresident/charged-use multiplier is not guessed. | [Current operator-linked tariff](https://www.musashino.or.jp/_res/projects/default_project/_page_/001/001/568/1001568-02.pdf), [charge rule](https://www.musashino.or.jp/_res/projects/default_project/_page_/001/001/568/202603s.pdf) |
| `tokyo-venue-294da8909003` | Chofu Nishimachi baseball 3,000/one field/2h; no inferred nonresident rate. Separate from its junior field or metropolitan park field. | [City guide](https://www.city.chofu.lg.jp/040070/p026093.html) |
| `tokyo-venue-6832b2db0714` | Chofu municipal baseball: resident 1,200/2h or 1,800/3h evening, nonresident 2,400/2h or 3,600/3h. Lighting separately 2,000/30min. | [City guide](https://www.city.chofu.lg.jp/040070/p026082.html) |

The six Nerima district-room discounts require the separate community-group registration: at least five members, at least half residing/working/studying in Nerima, and other registration conditions. General system registration alone is not the discount. See the [current ward guide](https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/1119.html). July 2026 system transition requires re-registration. Senior/other individual exemptions are outside these ordinary tariff ranges; they do not make general group hire free. Commercial activity and open recruitment to unspecified attendees are prohibited. Room-specific child/senior openings, permitted activities, capacity and sound restrictions remain applicable. No basketball/volleyball support is inferred for these existing event-only records.

Hikarigaoka's ordinary six-room tariffs retain separate room/time units; childcare-only, music, art, Japanese room and welfare-center rooms are outside this review's scope. Its conference room 1 reopened August 1. Published general reservation dates should be checked against the new-system guide, not treated as live availability. Seki requires the two-week advance meeting for multipurpose hall use.

## Holds

| Existing ID | Review Decision |
| --- | --- |
| `tokyo-gym-a231878afdcf` | [Koganei operator group guide](https://www.koganei-sponavi.net/gymnasium/group/) still links a PDF returned as exactly 1,048,576 bytes without an EOF. No repeated fast fetch or tariff adoption from the partial document. |
| `tokyo-gym-aa77f48e78d0` | [Honshuku city guide](https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/honshuku.html), updated October 25: October and March group-hire reservations stopped, November–February full renovation closure planned. October 26 reservation notice specifies November 2–February 28 planned. Listed ordinary pre-/post-work tariffs are not adopted as currently bookable hire. Existing October 25 cancellation/closure warning remains unchanged. Individual opening versus future complete closure is not collapsed into a new all-use closure status today. |
| `tokyo-gym-d56f81f38406` | [Tokyo Para Training Center guide](https://tokyo-ptc.jp/guide/) returned 503. No inquiry, login or substitution of ordinance ceilings/personal prices for the current exact room tariff. |
| `tokyo-venue-2b0bbd7157ff` | [Akirudai operator PDF](https://www.tokyo-park.or.jp/park/akirudai/assets/akirudai-field.pdf) explicitly says paid group price requires inquiry. Free personal athletics is not soccer hire; December–March turf use is unavailable. |
| `tokyo-venue-8e6c0f81a52c` | [Shinkawa October-use city guide](https://www.city.mitaka.lg.jp/c_service/079/079234.html) gives group/booking requirements but no exact group tariff. No inference of free group hire; previous cancellation evidence is retained. |
| `tokyo-venue-205d87234dd3` | [Fuchu Asahi city guide](https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/asahi.html) restricts field use to associations/tournaments. Meeting/multipurpose-room charges are not football-ground tariffs. |
| `private-chitose` | [Chitose operator rental page](https://tennis.chitose.jp/rentalcoat/) confirms cancellation/weather rules but not an adopted, fully mapped court tariff in the inspected rental guide. Fee remains unknown, policy added. |
| `private-nanbu` | [Nanbu rental guide](https://nanbu-tc.sunnyday.jp/rentalcourt.html) is image-led; a complete current surface/time/member tariff was not verified in this review. No OCR guess or school price substituted. |
| `private-santopia` | [Santopia operator FAQ](https://www.santo-tc.co.jp/faq/) confirms restricted rental windows but no rental amount. School tuition and school cancellation terms are not rental rates/policies. |

## Cancellation And Weather

- Six Nerima district facilities: the [ward payment guide](https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/kaisuukenn.html) says paid fees are not refundable except special reasons. Cancellation deadlines, booking penalties and weather exemptions are not inferred from this payment page. This policy is not copied to the two halls.
- Seki's current operator guide, page 8: cancellation less than a week before use restricts Web lottery/bookings 30 days from the following day; no-show 90 days. The facility's documented payment/report-before-end exception and same-day consolidation are qualified. These are booking restrictions, not monetary cancellation charges. Refund percentages remain unconfirmed.
- Shingashi: check weather/ground status before use; the facility does not call applicants. Weather/ground-condition closure is refundable under the operator's counter procedure (direct-debit groups need no application). Ordinary self-convenience deadlines/refund percentages remain unknown.
- Musashino: [operator rules](https://www.musashino.or.jp/sports/1001550/1001568.html) distinguish facility closure from an operator-declared user-decision day. Closure after more than one hour of the two-hour slot is not refundable. On user-decision days, non-use requires notice within 60 minutes of the slot start to qualify for refund. Ordinary cancellation rates are not asserted.
- Two Chofu fields: preceding-day system cancellation, on-day notice before start, one-month late-cancel versus three-month no-show new-booking restrictions. Nishimachi's rain-before-half-slot exception and required contact are explicit. Booking penalties are not assumed monetary fees/refunds.
- Chitose: 30% three days before, 50% two days/before, 70% same day, 100% no-show; weather decision one hour before with telephone confirmation. No unstated four-day free window or automatic weather refund is invented. Public bank details are not copied into the catalog.

## Verification And Publication

The importer rejects previously priced facilities and conflicting prior reviews before writing, and is idempotent. Eight new tests cover exact entries/counts, hold preservation, room/eligibility units, 3h/4h/hourly distinctions, field/lighting/nonresident restrictions, qualified cancellation rules and exact structural preservation of the three original catalogs plus all prior fee/policy prefixes. JSON comparison accommodates Git LF versus Windows checkout CRLF without allowing any data change. The October 27 inventory test now accounts for later explicitly dated additions, as existing historical tests already do.

Verification passed: all 173 venue regression cases, 15 sports-navigation cases, eight SEO cases and the standalone event flow. The first new preservation assertion compared Git LF bytes with checkout CRLF bytes; it was corrected to compare the complete JSON structure, then the full 173-case suite passed. All 21 reviewed records were checked in the isolated browser at 390px and 1440px (42 cases): published tariff counts/source links, original booking destinations, policy text, held unknown fees and no horizontal overflow. A leftover local-only QA cookie initially required initializing the disposable preview schema; no production session or private database was used or changed. No console warnings/errors remained in the completed preview.

Publish only after latest main is preserved, with a matching-commit Render Live deployment and production `/venues`/API verification. Final verification evidence is kept privately alongside source captures. No held facility requires user credentials, subscription or outreach in this run.
