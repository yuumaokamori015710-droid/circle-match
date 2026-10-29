# Official Venue Fee Follow-Up: 2026-10-29

## Scope And Preservation

Reviewed 25 existing facilities: seven remaining Tokyo soccer/indoor-sports
records first, followed by 12 Taito and six Chiyoda community venues. Added 19
scoped tariff sets and 19 cancellation records; six tariffs remain on hold.
The inventory is unchanged at 1,206 records: 861 priced, 345 unpriced, including
336 active and nine suspended unpriced records. A priced record means at least
one explicitly scoped tariff is known, not that every room or eligibility is
covered. No records, booking destinations or original catalog fields changed.

Base: `37bf2b3bab5eb6b225f843cdc69b7add65ab0d1f` (latest GitHub main).
Research is isolated in `codex/venue-fees-20261029`; the separate, unapproved UI
preview and its dirty checkout are not part of this release. Prior fees,
policies, contacts, privacy choices and event/payment work are preserved.
No environment, paid plan, schema, reservation, payment or inquiry changes.

## Confirmed Tariffs

- [Tokyo Para Sports Training Center](https://tokyo-ptc.jp/guide/): the public
  page is available again. Its linked [operator tariff](https://tokyo-ptc.jp/wp-content/themes/tokyo-ptc/files/%E6%96%99%E9%87%91%E8%A1%A8.pdf)
  confirms the gym's four-hour group blocks: weekdays 7,000–8,800 yen;
  weekends/holidays 8,800–11,000 yen, in separate eligibility units. The temporary
  exemption for sports groups with at least half disabled participants is
  recorded as a condition, not unconditional free use. Other rooms and personal
  training admission are outside this set. Advance cancellation contact is
  required; no-show cancellation is chargeable, but no fee rate/deadline or
  ordinary weather exemption is published in the reviewed guide/rules.
- [Taito's current official guide](https://www.city.taito.lg.jp/kusei/shisetsu/hall/kuminkan/kuminkanriyouannai1.html)
  links separate [resident](https://www.city.taito.lg.jp/kusei/shisetsu/hall/kuminkan/kuminkanriyouannai1.files/kunai0712.pdf)
  and [nonresident](https://www.city.taito.lg.jp/kusei/shisetsu/hall/kuminkan/kuminkanriyouannai1.files/kugai0712.pdf)
  tables. One named room per existing venue is transcribed for admission-fee-free
  use only: Ueno 101, Higashi-Ueno 201, first meeting room at Kanasugi,
  Kaminarimon, Umamichi and Kiyokawa, and multipurpose halls at Iriya,
  Taito-itchome, Kotobuki, Asakusabashi, Yanaka and Kanasugi-Shitaya. This is
  explicitly not the minimum across all rooms. Each resident category and exact
  3/4/12/13-hour duration stays separate. Paid-admission use, equipment and
  remaining rooms are not covered. Registration/member and use restrictions
  remain explicit. The [January 2026 guide](https://www.city.taito.lg.jp/kusei/shisetsu/hall/kuminkan/kuminkanriyouannai1.files/kuminkanriyoannai202601.pdf)
  confirms paid-use refunds of 100% by two months, 80% by 15 days and 50% by seven
  days, with distinct counter/online procedures. Disaster/closure cases require
  contacting the facility first, not normal online cancellation.
- [Chiyoda's official guide](https://www.city.chiyoda.lg.jp/shisetsu/kuyakusho/riyoannai.html)
  and [current tariff PDF](https://www.city.chiyoda.lg.jp/documents/6859/ryokinichiran.pdf)
  confirm single western room A at Manseibashi, Izumibashi, Fujimi, Jimbocho,
  Kanda-koen and Kojimachi. General-group eligibility only; other rooms, combined
  rooms and exemptions are outside the scope. Morning three-hour and
  afternoon/night four-hour prices are not combined. The guide allows prior-day
  cancellation; paid reservations need counter refund handling. Same-day
  bookings cannot be cancelled. Unspecified refund percentages/weather waivers
  are not inferred.

## Six Holds

| Existing facility | Official evidence and reason |
| --- | --- |
| 小金井市総合体育館 | [Group guide](https://www.koganei-sponavi.net/gymnasium/group/) links a PDF whose saved response is again exactly 1,048,576 bytes without PDF EOF. No partial table adopted and no rapid refetch. |
| 本宿体育館 | [City facility page](https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/honshuku.html) still stops gym group booking in October/March around renovation planned November 2–February 28. Prior qualified closure policy retained; listed pre/post-work or meeting-room fees are not current gym bookability. |
| 秋留台公園 | [Operator guide](https://www.tokyo-park.or.jp/park/akirudai/assets/akirudai-field.pdf) directs group-price inquiries to the service center; free personal track sessions do not establish free soccer hire. Turf use stops December–March. No inquiry sent. |
| 新川暫定広場 | [Current city guide](https://www.city.mitaka.lg.jp/c_service/079/079234.html) confirms registration and seven-day online cancellation cutoff, but no exact group tariff; prior policy retained, not inferred free. |
| 府中朝日フットボールパーク | [City facility page](https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/asahi.html) restricts the field to qualifying associations' official events. Clubhouse room prices are not soccer prices. |
| 川町運動場少年野球場 | [City page](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012073.html) confirms junior-high-or-younger use, seasonal closures and limited unattended opening; no exact tariff in the facility or linked public reservation guide. Existing policy preserved. |

## Evidence And Verification

`scripts/record_venue_fee_review_20261029.py` is conflict-checked and idempotent.
`scripts/test_venue_fee_followup_20261029.py` checks units, eligibility, scope,
unknown values, policy qualifications, previous JSON prefixes and all three
original catalogs. Historical October 26/28 holds now accept separately dated
later verification; their prior fee/policy data is unchanged.

Private evidence: `work/venue-fee-review-20261029/`, containing URL/status/date,
byte counts, SHA-256 hashes, complete source responses, PDF text and rendered
pages. No login-only sources or contact submissions. Local and production
browser/test/release evidence is recorded there after verification.

Local verification passed: 181 venue tests, 15 sport-navigation tests, eight SEO
tests and the standalone event-application HTTP flow. Browser checks cover all
25 reviewed records at 390px and 1440px (50 cases), including expanded tariffs,
eligibility/duration text, official booking and cancellation links, and unknown
prices. No document overflow or browser console errors. The public local API
matches all 1,206 catalog identities/booking URLs and the reviewed tariff and
policy records. Screenshots and machine-readable comparisons stay private.
