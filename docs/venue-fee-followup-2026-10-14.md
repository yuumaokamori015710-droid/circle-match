# Venue fee follow-up: 2026-10-14

20 Tokyo soccer/futsal and gym venues were reviewed against operator or municipal primary sources. Eleven previously unpriced venues gained conditional tariffs; five already-priced Meguro gyms were checked without changing their rates; four remain unpriced. Amounts are never inferred from other facilities, older fiscal-year tables, or booking deposits. The catalog, venue IDs, booking URLs and existing tariffs are preserved.

## Newly priced (11)

| Venue ID | Facility | Reviewed tariff scope | Official source |
| --- | --- | --- | --- |
| `tokyo-venue-34caff76d086` | 二子玉川緑地運動場 | 球技場 and youth soccer field, each 2 hours; weekday/weekend kept separate | https://www.se-sports.or.jp/facilityinfo/futako-ball-game-field/ ; https://www.se-sports.or.jp/facilityinfo/futako-youth-soccer-field/ |
| `tokyo-venue-c8eeb7f64931` | 渋谷区二子玉川区民運動施設 | 運動場 2 hours; ward/extra-ward groups | https://www.city.shibuya.tokyo.jp/shisetsu/sports-shisetsu/sports-center/sp1_2ko.html |
| `tokyo-venue-8af7723f06fb` | 井口グラウンド | 2 hours and May-August final 90 minutes separately; only registered Mitaka groups, junior-group discount | https://mitaka-sportsandculture.or.jp/zaidan/other/ground/iguchi.html |
| `tokyo-venue-76009f87c8f4` | 浜町運動場 | 1 field / 2 hours; daytime and floodlit night | https://www.city.chuo.lg.jp/a0015/bunkakankou/sports/mosikomihoho/undouzyou.html |
| `tokyo-venue-fb1731b080c2` | 戸吹スポーツ公園サッカー兼ラグビー場 | Half/full field each 2 hours; lighting additional | https://www.tobuki-sp.jp/price.html |
| `tokyo-venue-0ed440fdd641` | 北ノ台スポーツ多目的広場 | Gym 3-hour/day and futsal ground 2-hour units separately; registration required | https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010388.html |
| `tokyo-venue-c00e2b6906bf` | エスフォルタアリーナ八王子 | Main/sub arena full-area 2.5-hour sessions; commercial use excluded | https://www.hachioji.esforta.jp/usage-fee/ |
| `tokyo-venue-712511e56aa8` | 中野区立総合体育館 | Main/sub arena full-area 2-hour sessions; early/long sessions excluded | https://information.konamisportsclub.jp/trust/nakano/pricing/ |
| `tokyo-venue-a6e3e9da0d77` | 砧サッカー場 | Adult A/B field 2-hour sessions, ward category and time; youth tariffs linked, not mixed | https://www.city.meguro.tokyo.jp/sports/bunkasports/sports/ryokinhenko.html |
| `tokyo-venue-340b25d181f0` | 滝ガ原運動場サッカー場 | Soccer field 2-hour use | https://www.city.hachioji.tokyo.jp/shisetsu/104/p012070.html |
| `tokyo-venue-6ab610a2569c` | SUBARU総合スポーツセンター | Full main/sub arena 3-hour group hire only; 1-hour and individual use excluded | https://www.mitakagenki-plaza.jp/sports/guide.html ; https://www.mitakagenki-plaza.jp/_files/00008723/dantaiprice.pdf |

Each row's exact amounts, matched unit, applicability notes, source URL and check date are in `outputs/venues/catalogs/fee_plans.json`. Cancellation terms found on primary pages were added separately for 二子玉川緑地運動場, 井口グラウンド, SUBARU総合スポーツセンター and 平和の森公園多目的運動広場; absence of a cancellation record still means unknown, not free.

## Rechecked, no value change (5)

`tokyo-venue-ec8de0668a02` 八雲体育館, `tokyo-venue-19bdbd66ba0c` 目黒区民センター体育館, `tokyo-venue-14082e508e16` 碑文谷体育館, `tokyo-venue-e34356792fd2` 駒場体育館 and `tokyo-gym-e4e044521f5b` 中央体育館【目黒区】 match the municipality's current 3-hour gym tariff table: https://www.city.meguro.tokyo.jp/sports/bunkasports/sports/ryokinhenko.html . No existing tariff was overwritten.

## Still unpriced after review (4)

| Venue ID | Facility | Reason and official source |
| --- | --- | --- |
| `tokyo-venue-8d267086196e` | 平和の森公園多目的運動広場 | Operator PDF has overlapping field/lighting and eligibility tables; reviewed cancellation rules only. https://information.konamisportsclub.jp/file.jsp?id=33348 |
| `tokyo-venue-7f5f8dbd18bb` | 妙正寺川公園運動広場 | Municipal facility page gives registration/reservation guidance, not a confidently matched current tariff. https://www.city.tokyo-nakano.lg.jp/shisetsu/bunka/sports/myousyoujigawa.html |
| `tokyo-venue-8e6c0f81a52c` | 新川暫定広場 | Municipal page gives ball-field booking and time information but no matched current fee. https://www.city.mitaka.lg.jp/c_service/079/079233.html |
| `tokyo-venue-5b81852866ce` | 富士森公園内運動施設 | City outdoor-facility index links multiple areas and old fee PDFs. A current fee for this catalog record's exact facility/usage is not confirmed. https://www.city.hachioji.tokyo.jp/shisetsu/004/p012078.html |

No site inquiries, reservations or payments were performed. Fee changes are additive and can be reverted independently without touching the venue inventory.
