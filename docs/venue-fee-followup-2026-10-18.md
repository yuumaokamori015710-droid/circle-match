# Official Venue Fee Follow-Up: 2026-10-18

## Scope and Preservation

Reviewed 25 existing catalog records, prioritizing Shinjuku tennis followed by
Katsushika soccer/futsal and indoor basketball/volleyball facilities. Added ten
previously unknown tariff records and 24 cancellation policies. One currently
closed baseball/soccer field remains unpriced and is now hidden by default.
These are existing catalog records, not 25 distinct newly discovered buildings:
the combined Nishiochiai park entry and its legacy tennis entry are retained.

Research started at GitHub main `bc800fdb0d466ae58dfeadd3b83e67c5bf26fb42`,
including the latest individual/team pricing implementation. The dirty original
workspace was not reset or copied over this release. All previous fee/policy
entries, the entire 404-record legacy tennis JSON, facility IDs, booking URLs,
contacts, images and public URLs are retained. No external inquiries, login,
reservations, payments, schema, environment or plan changes were made.

## Ten New Tariffs

JPY, normal private hire only. Units, room size and included/excluded charges
are explicit; no hourly estimates, unrelated rooms or youth exemptions are
substituted for a sports-field price.

| Existing ID | Facility | Verified price and scope | Official source |
| --- | --- | --- | --- |
| shinjuku-okubo | 大久保スポーツプラザ 庭球場 | 1,500/2h; 1,800/2h30, separate units; lighting extra 500/30min | [Current-linked tariff PDF](https://www.regasu-shinjuku.or.jp/regasu/wp-content/uploads/2013/05/ookubo-tennis-price.pdf), [facility](https://www.regasu-shinjuku.or.jp/?p=159827) |
| tokyo-venue-144440cef349 | 西落合公園少年野球場・庭球場 | Tennis only 1,500/2h; youth baseball's free category is not adult tennis | [Operator](https://www.regasu-shinjuku.or.jp/?p=653) |
| tokyo-venue-8a1449acfd44 | 西戸山公園野球場 | 5,100/2h; lighting extra 3,150/30min; no full-size soccer goal | [Operator](https://www.regasu-shinjuku.or.jp/?p=652) |
| tokyo-venue-be0319cd8fbd | 小菅西公園 | Futsal pitch 2,600/up to 2h; lighting extra 1,100/2h, not skateboard admission | [Operator](https://spo.katsushika-web.net/facility/others/#anc-kosugenishi) |
| tokyo-venue-6e8063869f46 | 柴又球技場 | Pitch 1,200/up to 2h; youth exemption excluded | [Operator](https://spo.katsushika-web.net/facility/others/#anc-edogawa-sibamata) |
| tokyo-venue-f22c36060e5d | 荒川小菅球技場 | Pitch 1,200/up to 2h; youth exemption excluded | [Operator](https://spo.katsushika-web.net/facility/others/#anc-arakawa-kosuge) |
| tokyo-venue-6b66e7410823 | 江戸川河川敷（柴又付近） | Baseball field only 1,200/up to 2h; not free youth softball | [Operator](https://spo.katsushika-web.net/facility/others/#anc-edogawa-sibamata) |
| tokyo-venue-e6f34cc5ab8e | 荒川河川敷（小菅・堀切橋付近） | Baseball field only 1,200/up to 2h; early/late winter closures explicit | [Operator](https://spo.katsushika-web.net/facility/others/#anc-arakawa-kosuge) |
| tokyo-gym-8661317f0c40 | 奥戸総合スポーツセンター温水プール館・エイトホール | Eight Hall 6,300-9,700/2h30; 29,200/day12h separately; no pool admission substituted | [Tariff](https://spo.katsushika-web.net/group_guide/), [facility/volleyball and badminton](https://spo.katsushika-web.net/facility/okudo-pool/) |
| tokyo-gym-8107c9095a7c | 水元総合スポーツセンター体育館 | Main full 10,200-15,500/2h, half 5,100-7,750/2h, sub 5,000-7,200/2h; day rates separate | [Tariff](https://spo.katsushika-web.net/group_guide/), [room/sport mapping](https://spo.katsushika-web.net/facility/mizumoto/arena/) |

The Nishiochiai current facility page says no lights; the conflicting old
outdoor-list PDF lighting statement is not adopted. Shinjuku registration is
free, with payment onsite on the day, not payment at reservation. Category
eligibility and registration renewal still apply. Katsushika online booking
requires user/account registration, with ordinary usage paid by later bank
debit; being able to pay later does not establish permission for unattended
automated booking. No automation-permission or live-vacancy claim is made.

## Reconfirmed Prices and Added Cancellation Terms

The following previously priced records retain all original prices. Their
applicable cancellation terms now have a source and check date:

| Existing ID | Facility | Rechecked tariff source |
| --- | --- | --- |
| shinjuku-kansenen | 甘泉園公園 庭球場 | [1,500/2h](https://www.regasu-shinjuku.or.jp/?p=656) |
| shinjuku-ochiai-chuo | 落合中央公園 庭球場 | [1,500/2h, lighting separate](https://www.regasu-shinjuku.or.jp/?p=657) |
| shinjuku-nishiochiai | 西落合公園 庭球場 | [1,500/2h](https://www.regasu-shinjuku.or.jp/?p=653) |
| katsushika-kamichiba | 上千葉公園運動場テニスコート | [Day 1,200/up to 2h](https://spo.katsushika-web.net/facility/others/#anc-kamichiba) |
| katsushika-okudo | 奥戸総合スポーツセンターテニスコート | [Day 1,200/up to 2h](https://spo.katsushika-web.net/group_guide/) |
| katsushika-kosuge | 小菅東スポーツ公園テニスコート | [Day 1,200/up to 2h](https://spo.katsushika-web.net/facility/others/#anc-kosugehigashi) |
| katsushika-higashishinkoiwa | 東新小岩運動場テニスコート | [1,200/2h; night lights +275/30min](https://www.city.katsushika.lg.jp/tourism/1002753/1030217/1032636.html) |
| katsushika-higashikanamachi | 東金町運動場テニスコート | [1,200/up to 2h](https://spo.katsushika-web.net/facility/others/#anc-higashikanamachi-ground) |
| katsushika-mizumoto | 水元総合スポーツセンターテニスコート | [Day 1,200/2h; seasonal night rates separate](https://spo.katsushika-web.net/group_guide/) |
| katsushika-shibue | 渋江公園テニスコート | [Day 1,200/up to 2h](https://spo.katsushika-web.net/facility/others/#anc-shibue) |
| katsushika-niijuku | 葛飾にいじゅくみらい公園運動場テニスコート | [Day 1,200/up to 2h; final night slot is 3h, not 2h](https://spo.katsushika-web.net/facility/others/#anc-nijukumirai) |
| tokyo-venue-acf6eedff95e | 四つ木橋球技場 | [1,200/up to 2h](https://spo.katsushika-web.net/facility/others/#anc-arakawa-yotsugibashi) |
| tokyo-venue-c4c0a999cf17 | 木根川橋球技場 | [1,200/up to 2h](https://spo.katsushika-web.net/facility/others/#anc-arakawa-yotsugibashi) |
| tokyo-venue-48461c620190 | 奥戸総合スポーツセンター体育館・陸上競技場 | [Existing main/small gym tariffs confirmed](https://spo.katsushika-web.net/group_guide/) |

Six Shinjuku entries (the four tennis records, the combined Nishiochiai entry,
and Nishitoyama) use the [official outdoor guide](https://www.regasu-shinjuku.or.jp/?p=139217):
online/counter cancellation; no reservation restriction by five days before;
four days before through the use day causes one month of reservation/lottery
suspension from next month's 25th through the following month's 24th; no-show
up to three months. Rain/ground closure is decided onsite, requires a phone
check, and must not be entered as ordinary self-cancellation online.

Eighteen Katsushika entries use the
[operator guide](https://spo.katsushika-web.net/group_guide/) and
[municipal payment/cancellation rules](https://www.city.katsushika.lg.jp/tourism/1002753/1030217/1003235.html):
free by seven days before, 50% from six days through the previous day, 100%
on the day/no-show. Counter-processed reservations are not cancellable online.
Outdoor bad-weather closure is an onsite decision; unusable usage is not bank
debited, but previously paid money requires a refund procedure. This weather
exception is not applied to the three indoor hall/gym records. East Shinkoiwa's
current facility page explicitly links to the municipal rules, so those rules
are used as its policy source rather than assuming another operator's scope.

## Closed Field, Not Closed Tennis

`tokyo-venue-ecb55dd79d92` (落合中央公園野球場) is closed for artificial-turf
and lighting works until the end of March 2027, subject to change, per the
[current facility notice](https://www.regasu-shinjuku.or.jp/?p=657).
The original ID and booking URL are retained. Only its availability status,
availability note, check date and added source are changed. No currently
bookable tariff is attached. The adjacent tennis entry is not marked closed.

## Verification and Release

Importer: `scripts/record_venue_fee_review_20261018.py`. It appends only, refuses
to overwrite a different prior review or already priced venue, and is
idempotent. Focused regression: `scripts/test_venue_fee_followup_20261018.py`.
Browser verification: `scripts/verify_venue_fee_followup_20261018_browser.cjs`.
The existing expansion test explicitly permits this additional source-verified
closure, while retaining checks for all other records.

Catalog after this batch: 1,206 records, 690 priced, 516 unpriced including
suspended entries, 512 active unpriced. No unconfirmed price is changed to zero.

Local suites: 80 venue tests and 39 sport-navigation, SEO, event-flow and
individual/team-pricing regressions passed (119 total). Four viewport widths (390, 768, 1440,
1920) checked all ten new tariffs, 24 API policy mappings, initial HTML source,
price/unit/source/booking links, details, overflow and closed-field hiding.
Two additional no-JavaScript checks passed. Mobile/desktop screenshots were
visually inspected. Tests use a disposable local database and do not start
notification workers. Public API, initial HTML and browser checks are repeated
after the latest-main automatic Render deployment becomes live.

Structural comparison against the starting main verified all 404 tennis,
51 sports and 751 expansion records retain their IDs and booking URLs. All
431 previous tariff entries and 56 previous policy entries are identical.
Only the one documented closure changes a base record. A second importer run
left both overlay files' SHA256 checksums unchanged. Initial local test attempts
hit sandbox loopback restrictions/missing bundled BeautifulSoup; rerunning with
the existing system Python and permitted local HTTP resolved those environment
failures without changing dependencies or production code.

Rollback: revert this batch's commit on latest main, rerun the venue tests and
deploy the resulting branch. No private database restoration is required.
