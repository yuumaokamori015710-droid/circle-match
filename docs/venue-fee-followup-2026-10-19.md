# Official Venue Fee Follow-Up: 2026-10-19

## Scope and Preservation

Reviewed 21 existing records: 20 newly priced and one officially closed.
These are catalog records, not 21 distinct newly discovered buildings:
the retained Suwa-minami and Sumida field entries overlap physical facilities.
Seventeen cancellation policies were added; Saginomiya's consistent existing
policy was retained, and one Heiwa no Mori policy was corrected to disclose
conflicting official documents rather than promise free cancellation.

Started from and re-fetched GitHub main `e573efe0e686fa8b0707b4ff167b35fa25b34561`.
The latest mobile homepage changes are preserved. Structural comparison
confirmed all 404 tennis, 51 sports and 751 expansion IDs and booking URLs
remain intact. The original tennis file has no Git diff; all 441 prior fee
reviews and 79 of 80 prior cancellation reviews are identical. Only the
documented closure changes a base venue. No schema, environment, plan,
reservation, payment, inquiry, authenticated-source or email changes occur.

## Added Tariffs

JPY, normal adult/group hire unless explicitly restricted. Each amount has
its own source, unit, applicability and 2026-10-19 check date in `fee_plans.json`.
Different durations and room sizes are not merged; concessions are excluded.

| Existing ID | Facility | Confirmed scope and fees | Official source |
| --- | --- | --- | --- |
| tokyo-venue-121d6c8174f3 | 一ノ宮公園球技場 | One field/2h: city 730, noncity 1,460 | [Current operator guide](https://tama-sports.com/wp/images/スポーツ施設の利用手引き20260525.pdf), [field page](https://tama-sports.com/facility/ballfield) |
| tokyo-venue-2eee55f51c74 | 和田公園球技場 | One field/2h: city 2,080, noncity 4,160 | [Operator](https://tama-sports.com/facility/ballfield) |
| tokyo-venue-0e8ff3149e98 | 宝野公園球技場 | One field/2h: city 2,080, noncity 4,160 | [Operator](https://tama-sports.com/facility/ballfield) |
| tokyo-venue-5b984fb3a2d9 | 諏訪南公園野球場兼球技場 | Ballfield/2h: city 2,080, noncity 4,160; baseball cannot run simultaneously | [Operator](https://tama-sports.com/facility/ballfield) |
| tokyo-venue-e394b1e32142 | 諏訪南公園野球場（球技場） | Same existing field identity and ballfield tariff; retained duplicate ID | [Operator](https://tama-sports.com/facility/baseball) |
| tokyo-venue-58dddea55c17 | 貝取南公園野球場 | Baseball/2h: city 2,080 only; noncity groups prohibited | [Specific facility restrictions](https://tama-sports.com/facility/baseball) |
| tokyo-venue-ddccb6a7186f | 大沼グラウンド | 2h: city 1,500, noncity 2,250; winter final 1h: 750/1,125 separately | [City](https://www.city.kodaira.tokyo.jp/kurashi/001/001348.html), [ordinance](https://www.city.kodaira.tokyo.jp/reiki/reiki_honbun/g135RG00000373.html) |
| tokyo-venue-47487bc65669 | 天神グラウンド | Same 2h and winter final-1h tariffs; published permitted sports still apply | [City](https://www.city.kodaira.tokyo.jp/kurashi/001/001348.html) |
| tokyo-venue-4b48ca660485 | 小川西グラウンド | 2h: city 1,700, noncity 2,550; lights extra 4,200/6,300 per hour | [City](https://www.city.kodaira.tokyo.jp/kurashi/001/001348.html) |
| tokyo-venue-d6ae544d3049 | 萩山公園グラウンド | 2h: city 1,500, noncity 2,250; winter final 1h: 750/1,125 | [City](https://www.city.kodaira.tokyo.jp/kurashi/001/001348.html) |
| tokyo-venue-147fe0995885 | フクシ・エンタープライズ墨田フィールド | Futsal court/2h: 10,000-18,000; junior-size soccer pitch/general category: 9,000-16,200/2h; track/infield separate | [Operator fees](https://sumidacity-ground.com/fee) |
| tokyo-venue-c4a96df3f8b8 | 墨田区総合運動場 | Same existing complex; exact city/noncity, weekday/weekend categories retained | [Operator fees](https://sumidacity-ground.com/fee) |
| tokyo-gym-de4248a7e59c | 墨田区総合体育館 | Main 1/3: 6,600-17,600/3h; sub full: 9,900-26,400/3h; half: 4,950-13,200/3h. Final 1h30 separate | [Operator room tariffs](https://www.sumidacity-gym.com/facility/3f.php) |
| tokyo-gym-e29afd238620 | スポーツプラザ梅若 | Full gym: 4,840-8,740/3h; 5,830-15,670/4h; day12h: 17,270-34,650 | [Operator](https://information.konamisportsclub.jp/trust/umewaka/pricing/) |
| tokyo-venue-7f5f8dbd18bb | 妙正寺川公園運動広場 | Explicitly free/2h, but requires eligible Nakano group; not unrestricted hire | [Manager guide](https://www.tetsugakudo.jp/wp-content/uploads/2024/07/2024_07232.pdf) |
| tokyo-venue-8d267086196e | 平和の森公園多目的運動広場 | 2,900/2h, required seasonal lighting extra 700/30min | [2026 guide](https://information.konamisportsclub.jp/file.jsp?id=34282) |
| tokyo-gym-07d760f3b816 | 鷺宮スポーツ・コミュニティプラザ | Free-registration whole-open category: full 18,400-22,200/3h, 25,600-30,900/4h; other durations and half-hall separate | [Current-linked image PDF](https://www.nakano-sports-comm.net/?mode=n&s=1&type=021), [current page](https://www.nakano-sports-comm.net/saginomiya/group/) |
| tokyo-venue-bde3fe735327 | 東品川文化センター | Sports room city/noncity: 3,500/4,200 per3h; 4,600/5,500 per3h30; 5,800/7,000 per4h | [City PDF](https://www.city.shinagawa.tokyo.jp/ct/pdf/hpg000000314_17.pdf) |
| tokyo-gym-4cc7151e3584 | 南大井文化センター | Sports room city/noncity: 4,600/5,500 per3h; 6,000/7,200 per3h30; 7,600/9,100 per4h | [City PDF](https://www.city.shinagawa.tokyo.jp/ct/pdf/hpg000000314_18.pdf) |
| tokyo-gym-62c8903535b7 | 旗の台文化センター | Sports room city/noncity: 5,300/6,400 per3h; 6,900/8,300 per3h30; 8,800/10,600 per4h | [City PDF](https://www.city.shinagawa.tokyo.jp/ct/pdf/hpg000000314_16.pdf) |

Important exclusions: Sumida's cheaper non-futsal use of a futsal court is not
priced as futsal. Its field lighting and commercial/admission surcharge remain
separate. The current [gym reservation notice](https://sumidacity-gym.com/)
says basketball is unavailable in the sub-arena, overriding the older room
table: basketball uses the main-arena tariff, not the sub rate. Published
rounding (e.g. 18,970, not an invented 18,975) is preserved. Saginomiya's
paid general-group registration discounts are excluded from the free-registration
category. Shinagawa's light-sports room, meeting rooms and pool prices are not
substituted for gym hire; no Sunday/holiday evening hire is advertised.

## Cancellation, Restrictions and Holds

- Tama six records: [May 2026 guide](https://tama-sports.com/wp/images/スポーツ施設の利用手引き20260525.pdf). Paid voluntary cancellation gives 80% in the prior month's first half, then 50% through three days before, none from two days before. Paper approval and counter cash-refund procedures apply even after online payment. Ordinary refund rules explicitly exclude tournament-hire charges; weather-unusable hire has its own conditions.
- Kodaira four: [city application guide](https://www.city.kodaira.tokyo.jp/kurashi/002/002684.html) confirms refunds through 14 days before. Exact late/weather exceptions are not established by that page and are not invented.
- Sumida field two: [current guide](https://sumidacity-ground.com/guide) has full refunds through14 days, half13-7, none6 or fewer days. Ordinary rain is not closure; manager-declared severe-weather closure is different. Late unpaid cancellations also cause booking-restriction points.
- Sumida gym: [group guide](https://www.sumidacity-gym.com/sp/guide/dantai/introduction.php) confirms the14/13-7/6-day refund bands; paid cancellation requires representative counter procedures, with later bank refund. Unpaid late-cancellation points are recorded separately.
- Myoshojigawa: [manager guide](https://www.tetsugakudo.jp/wp-content/uploads/2024/07/2024_07232.pdf) confirms free hire but late cancellations/no-shows still restrict bookings. Nakano eligibility and the1st-15th usage period remain explicit.
- Shinagawa three: [current cultural-center rules, article8](https://www.city.shinagawa.tokyo.jp/reiki/H421902100022/print.html) use the sports-room7-day deadline (next opening day if closed), qualifying reasons and refund application. Hall/pool deadlines are not reused.
- Saginomiya: consistent earlier policy retained unchanged. Umewaka: fees verified, but no definitive official cancellation schedule found; policy remains unknown, not free.

### Heiwa no Mori Official-Source Conflict

The earlier published statement is archived here and in Git history, not silently
discarded:

```json
{"id":"tokyo-venue-8d267086196e","status":"conditional","summary":"利用3日前までは無料取消。当日・前日・前々日は取消不可で利用料金が発生します。荒天による途中中止で残り1時間以上の場合は後半1時間分の還付対象。照明料の扱いは公式案内を確認してください。","source_url":"https://information.konamisportsclub.jp/file.jsp?id=33348","checked_at":"2026-10-14"}
```

The [older operator PDF](https://information.konamisportsclub.jp/file.jsp?id=33348)
still says three days/free. The [dated 2026-01-30 operator guide](https://information.konamisportsclub.jp/file.jsp?id=34282)
says paid cancellation by seven days gives50%, six days or later none.
The operator and municipal copies also differ on the online cancellation cutoff.
The live policy now states this conflict and requires confirmation before
booking; it does not choose a convenient free-cancellation promise. No inquiry
was sent. Both guides agree on ordinary hire2,900/2h and lighting700/30min.

### Closed, Not Deleted

`tokyo-venue-d7b168f67c73`, 中央公園グラウンド【小平市】, is closed for
renovation from2026-04-01 through2027-03-end (planned), per the
[current city page](https://www.city.kodaira.tokyo.jp/kurashi/001/001348.html).
Only availability, check date and the added source change; ID/booking URL remain.
No currently bookable tariff is attached; default search hides it.

## Verification and Release

Catalog:1,206 retained records; priced690 ->710; unpriced516 ->496,
including five suspended unpriced records; active unpriced512 ->491.
Tariff overlays441 ->461; cancellation overlays80 ->97 (17 added, one corrected).

Importer: `scripts/record_venue_fee_review_20261019.py`. It rejects unrelated
overwrites and accepts only the explicitly archived old Heiwa policy for its
guarded correction. A second run leaves all five catalog SHA256 hashes unchanged.
Ten focused new tests cover exact bounds, eligibility, room mapping, durations,
published rounding, zero/free evidence, source conflict, closure and idempotence.

Local verification passed:90 venue tests,15 sport-navigation tests and31
SEO/event/dual-pricing/latest-homepage tests (136 total). Browser checks passed
all20 tariffs at390/768/1440/1920px,18 current policy mappings, source and
booking links, details, SSR evidence, closed-field hiding, price clipping and
horizontal overflow. Three additional JavaScript-disabled cases passed.
Mobile/PC screenshots were visually inspected. Tests use disposable local data
without notification workers. The first browser attempt caught a test-only URL
encoding mismatch; comparing normalized URLs resolved it without UI changes.

Latest-main auto-deploy and public browser checks must complete before reporting
production success. Rollback is a revert of this batch on latest main followed
by tests and deploy; no private database restore is needed.
