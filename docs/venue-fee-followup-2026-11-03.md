# Official Venue Fee Follow-Up: 2026-11-03

## Scope And Preservation

Reviewed **29 distinct existing records**: the 13 remaining priority soccer/gym
records, two more Hachioji grounds, four Tama sports facilities, seven Koto
cultural centers and three Sumida community centers. Added **13 scoped tariff
sets and 14 policy records**; 16 tariffs remain on hold. The 1,206-record
inventory now has **891 priced and 315 unpriced (305 active / 10 suspended)**.
Priced means one verified scope, not every room, user category or bookable date.

Base main: `8ecf2edb4f75c62026079d52b1621b863390120b`.
Previous fees and policies remain exact prefixes. IDs, names, booking URLs,
sports and all other source fields are preserved. The only source-record
correction is the confirmed Higashikomagata closure: status, closure note,
checked date and one appended official source. Historical tests explicitly
validate that correction before comparing their original snapshots; they do
not broadly exempt future changes. No UI redesign, environment, plan, schema,
contact privacy, account, event, payment or user database changes. One scoped
Club Edit tariff-header contrast correction is included, not a redesign. No inquiries,
reservations, payments or authenticated source access.

## New Tariffs

Koto: one named room per existing center, **not building-wide minima**. Morning
9-12 is 3h; afternoon 13-17 and evening 18-22 are 4h. Those durations remain
separate. General groups require at least two members and an adult representative
(not a high-school student); district groups have lottery priority. Nonresidents
may use the facilities, but commercial use, sales and unspecified-public room
gatherings are prohibited. Internet/lottery registration is a counter procedure.
Room-specific activity prohibitions still apply; these are not gym tariffs.

| Existing facility / ID suffix | Room | Morning / afternoon / evening, yen | Official tariff |
| --- | --- | --- | --- |
| 亀戸文化センター / 13c10707fc3b | 第1会議室 | 2,000 / 4,100 / 5,150 | [Fees](https://www.kcf.or.jp/kameido/shisetsu-bunka/fee/) |
| 古石場文化センター / 92c99e38e33e | 第1会議室 | 1,800 / 3,700 / 4,550 | [Fees](https://www.kcf.or.jp/furuishiba/shisetsu/fee/) |
| 東大島文化センター / 22803d6ec704 | 第1会議室 | 1,800 / 3,700 / 4,550 | [Fees](https://www.kcf.or.jp/higashiojima/shisetsu/fee/) |
| 森下文化センター / 1cb442e20203 | 第1会議室 | 1,800 / 3,700 / 4,550 | [Fees](https://www.kcf.or.jp/morishita/shisetsu/fee/) |
| 江東区文化センター / 0d428ad0eed9 | 第1会議室 | 1,800 / 3,700 / 4,550 | [Fees](https://www.kcf.or.jp/koto/shisetsu/fee/) |
| 砂町文化センター / 8cc9f3611320 | 第1会議室 | 1,800 / 3,700 / 4,550 | [Fees](https://www.kcf.or.jp/sunamachi/shisetsu/fee/) |
| 豊洲文化センター / f4279ddf1eb4 | 第1研修室 | 1,300 / 2,700 / 3,700 | [Fees](https://www.kcf.or.jp/toyosu/shisetsu/fee/) |

Each center's linked use page was checked separately and saved in its policy
record. General-room paid cancellations by 14 days at 21:00 refund all, by
seven days at 21:00 half, later none. Approval paper and representative seal
are required at that facility's counter; a closed-day deadline moves to the
preceding open day. Refunds over 20,000 yen use bank transfer at the user's
transfer-fee expense. Large-hall six/four-month rules do not replace these
room rules. Fees over 1,500 yen per attendance/course may attract a 50% surcharge
for the performance period, subject to facility determination; not inferred
into ordinary tariffs. Normal rain relief is unconfirmed. See
[registration/application](https://www.kcf.or.jp/koto/shisetsu/apply/) and
[general use](https://www.kcf.or.jp/koto/shisetsu/use/).

Sumida:

- [梅若橋 community room](https://www.city.sumida.lg.jp/sisetu_info/tamokuteki/communitykaikan/umewakabashi/syuukaijyo.html),
  ID `tokyo-venue-39dcf27aa5d1`: multipurpose room only, 2,200 yen / 3h morning,
  2,900 / 4h afternoon or night. The [operator](https://sumida-umecomi.net/meeting_room/)
  confirms the same rates and limits Web provisional booking to registered
  previous users. Other rooms, children's gym and extensions are excluded.
- [横川 community room](https://www.city.sumida.lg.jp/sisetu_info/tamokuteki/communitykaikan/yokokawa/syuukaijyo.html),
  ID `tokyo-venue-5cc27fca9da0`: 25-tatami room 2,600 / 3h, 3,400 / 4h,
  1,700 / 2h night B. Childcare restricts weekdays to morning/night B and school
  holidays to night B; Saturday counts as weekday in the
  [municipal guide](https://www.city.sumida.lg.jp/sisetu_info/tamokuteki/tiikisyuukaizyo.html).
  Residents reserve three months ahead, others two, both by five days before use.
  Room eligibility, reductions and paid extension are not mixed with base rates.

The [current official implementing rules, articles 3/6](https://www.city.sumida.lg.jp/wkg/reiki_int/reiki_honbun/g108RG00000288.html)
cover these community rooms: cancellation by five days refunds all; disaster,
accident or non-user-caused inability refunds all or the unusable portion.
Mid-use interruption is the manager-determined amount. Paper or supported
online procedures depend on the original booking/payment. No ordinary-rain
waiver or unspecified late refund is inferred.

Tama:

- [陸上競技場 linked official PDF](https://tama-sports.com/wp/images/%E9%99%B8%E4%B8%8A%E7%AB%B6%E6%8A%80%E5%A0%B4.docx-1.pdf),
  ID `tokyo-venue-689b7f628626`: competition-ground hire 8,370 / morning 3h,
  12,560 / afternoon 4h, 20,930 / full-day 8h. Equipment and other rooms excluded.
  Paid admission adds maximum admission charge x100. The PDF is dated April
  2020 but is still linked by the [current operator](https://tama-sports.com/facility/tamahigashi).
  Hire eligibility requires facility confirmation; personal track access is
  not unrestricted grass-field hire. No lighting. Specific hire refund terms
  remain unconfirmed rather than copying unrelated personal/baseball rules.
- The [2026 operator guide](https://tama-sports.com/wp/images/%E3%82%B9%E3%83%9D%E3%83%BC%E3%83%84%E6%96%BD%E8%A8%AD%E3%81%AE%E5%88%A9%E7%94%A8%E6%89%8B%E5%BC%95%E3%81%8D20260525.pdf)
  PDF page 10 (printed 8) and [baseball page](https://tama-sports.com/facility/baseball)
  confirm adult general group rates per field / 2h: 一本杉
  (`tokyo-venue-5623e0c1f690`) 8,370 resident / 16,740 nonresident; 諏訪北
  (`tokyo-venue-1dcd0e1458df`) and 関戸 (`tokyo-venue-f36637b84638`) each
  2,080 / 4,160. Eligibility units stay distinct. Ten-member registration,
  half resident/work/student qualification and no off-roster use are explicit.
  Child/disability rates, short sunset slots and equipment are excluded.
  The [municipal page](https://www.city.tama.lg.jp/kenkofukushi/1008238/sports/riyou/index.html)
  links a later night-lighting termination notice for 一本杉; its details returned
  403, so old night-inclusive amounts were not published.

Guide PDF page 6 (printed 4): after payment, self-cancellation refunds 80% by
the preceding month's 1st-15th, 50% by three days before, none later. One change
by seven days, same user/conditions, to an existing provisional booking. Paper
approval/statement and a counter visit are required; online/card payments also
refund as cash. Weather-caused unusability can refund 100%, but not after 30+
minutes used; claim within five years. Tournament-related fees, program entry
and same-day tickets are outside these ordinary rules. Heat refunds are a
separate program requiring contact before start; not treated as unconditional.
Local complete PDFs and rendered table images were visually checked.

## Sixteen Tariff Holds

| Existing facility | Current official result / reason retained unknown |
| --- | --- |
| 小金井市総合体育館 | [Group PDF](https://www.koganei-sponavi.net/gymnasium/group/) still fails web parsing; previously truncated PDF not reused. |
| 本宿体育館 | [Current page](https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/honshuku.html) confirms Nov-Feb full closure and no Oct/Mar group hire; no old-rate substitution. |
| 秋留台公園 | [Official guide](https://www.tokyo-park.or.jp/park/akirudai/assets/akirudai-field.pdf) requires inquiry for group price; free individual track is not free soccer hire. |
| 新川暫定広場 | [New registration rules](https://www.city.mitaka.lg.jp/c_service/079/079234.html) do not establish a group hire fee. |
| 府中朝日フットボールパーク | [Facility page](https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/asahi.html): association events; clubhouse rates are not field rates. |
| 川町運動場少年野球場 | [Youth-only page](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012073.html) and common guide lack current explicit fee; do not infer free. |
| 椚田運動場少年野球場 | [Youth-only page](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012075.html): current fee unconfirmed, winter closure. |
| 高倉公園野球場 | [Current instructions](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012124.html) require counter approval by one week; historic free-use material is not current confirmation. Existing cancellation record retained. |
| 多摩：南豊ヶ丘フィールド | [Old operator URL](https://www.futsal-tokyo.co.jp/nantoyo/) redirects to generic booking home; suspended record kept. |
| 中央公園グラウンド【小平市】 | [Old official URL](https://www.city.kodaira.tokyo.jp/kurashi/001/001348.html) 404; suspended record kept. |
| 落合中央公園野球場 | [Official URL](https://www.regasu-shinjuku.or.jp/?p=657) times out; suspended record kept. |
| 西部運動広場 | [Official April newsletter](https://www.city.higashikurume.lg.jp/_res/projects/default_project/_page_/001/028/861/080401n.pdf) retained as closure evidence, not current tariff. |
| 福生野球場 | [Official page](https://www.city.fussa.tokyo.jp/education/sports/1002683.html): closure July 2026-May 2027 planned; no replacement fee. |
| あらかわ遊園スポーツハウス | [Official page](https://www.city.arakawa.tokyo.jp/a017/sport/shisetsuriyou/s-houseriyou.html): closed through March 2027 planned. |
| 花畑地域体育館 | [Official page](https://www.city.adachi.tokyo.jp/sg-shien/hanahata.html): closed September 2026-March 2028 planned. |
| 東駒形コミュニティ会館 | [Current closure notice](https://www.city.sumida.lg.jp/sisetu_info/tamokuteki/communitykaikan/index.html): whole building Oct 10-Dec 20; meeting rooms through Feb 16, 2027, gym through Feb 28. Status corrected to suspended, record and original booking URL retained. |

## Verification And Release

Passed 202 existing/detailed venue tests (including the nine new dated tests),
plus 27 Club Edit, sports-navigation and public-event-URL tests. The initial
restricted HTTP attempt could not access localhost; the same suite passed with
local network permission. The fixture's intentionally raised source-read error
is expected fallback coverage, not a production error.

Local public API comparison matched all 1,206 IDs, booking URLs, fees, policies
and availability fields exactly. All 29 reviewed server-rendered pages returned
200 with matching fee notes; the closed record appears only when suspended
records are included. Browser QA at 320px, 390px and 1440px confirmed expanded
room/field details, separate unit labels, source links, stable navigation and no
page-level horizontal overflow. The production desktop screenshot exposed a
white inherited tariff-header background with near-white text in Club Edit.
One scoped CSS rule gives that header the existing dark table-header background
and explicit light text. A contrast regression test and computed-color browser
check cover the correction; no layout, navigation or broader UI redesign.

Private complete source PDFs, rendered table images, browser screenshots, HTTP
comparisons and final deployment evidence stay in
`work/venue-fee-review-20261103/`, outside published data. The release workflow
requires latest-main preservation, the existing service's automatic deployment
to become Live, and a second API/SSR and mobile/desktop check on production.

No user action is needed for this research batch. Unpriced remaining records
are not a claim that all rooms or unpublished tariffs have been researched.
