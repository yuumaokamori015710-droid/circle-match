# 2026-11-06 公式料金・取消条件の継続調査

確認日：2026-11-06（日本時間）。基準 main：`9ef2bbeee940bac1418379dbb776fdffa7347c27`。

26施設を確認。料金未掲載19施設に条件付き料金を追加、既掲載2施設を再確認、5施設は金額保留。取消・返還条件を18施設に追加。
総数1,206施設は不変。料金掲載941、未掲載265（通常検索対象254、既存休止11）。今回確認した大沢野川は料金掲載済みの休止施設となり、全休止施設数は12。
前回の922掲載・284未掲載からの差分は19施設。サッカー・体育館系の残り4施設を先に再確認し、金額を安全に特定できなかったため、残る東京のテニス施設へ進んだ。

## 追加料金

各金額は税込等の明記がない場合、公式掲載額のまま。課金単位、登録区分、照明、施行日を分離し、時給換算や他室・他競技の料金転用をしない。
市外加算を算出した清瀬の900円は公式の600円×150%。福生の市外額は施設ページに明記された額。減免・用途別加算は通常料金に含めない。

| 施設ID | 対象 | 今回の採用範囲 |
| --- | --- | --- |
| `tokyo-venue-8a29b57a2a95` | 自治大学校庭球場 | 市内登録団体1面2時間800円、土曜のみ。市内在住在勤在学5人以上・専用登録 |
| `tachikawa-izumi` | 泉町庭球場 | 1面2時間、市内800円／市外1,600円、照明別 |
| `tachikawa-nishiki` | 錦町庭球場 | 同上。兼用フットサル料金とは別 |
| `tachikawa-sunagawa` | 砂川中央地区庭球場 | 市内登録個人1面2時間100円、市外額なし |
| `tachikawa-nishisuna` | 西砂庭球場 | 同上 |
| `musashimurayama-ominami` | 大南公園庭球場 | 2026年7月から2時間、市内1,020円／市外2,040円。春秋17～18時だけの1時間枠510円／1,020円は別単位 |
| `musashimurayama-kaminarizuka` | 雷塚公園庭球場 | 同上。営利利用不可 |
| `fussa-sdfield` | S&Dフィールド福生テニスコート | 1面1時間、市内500円／市外1,500円、照明別 |
| `fussa-minami` | 南公園テニスコート | 1面1時間、市内500円／市外1,500円 |
| `fussa-musashinodai` | 武蔵野台テニスコート | 1面1時間、市内800円／市外2,400円。2面分フットサルは別料金・窓口予約のみ |
| `fussa-fukuto` | 福東総合グランドテニスコート | 1面1時間、市内800円／市外2,400円 |
| `hino-tamadaira` | 多摩平第一公園テニスコート | 通常1面2時間以内700円、照明別。2027年4月からの980円を現行範囲へ混ぜない |
| `hino-asahigaoka` | 旭が丘中央公園テニスコート | 同上、照明なし |
| `hino-nanao` | 七生自然学園テニスコート | 1面2時間2,100円、一部3時間3,150円は別単位 |
| `kiyose-uchiyama` | 清瀬内山運動公園テニスコート | 1面2時間、市内600円／市外900円 |
| `kiyose-himawari` | コミュニティプラザテニスコート | 同上。中学生以上、サブコートの奥行き注意 |
| `mitaka-osawa` | 大沢総合グラウンドテニスコート | 市内登録団体1面2時間1,500円、照明別。共用個人開放500円とは分離 |
| `mitaka-shinkawa` | 新川テニスコート | 市内登録団体1面2時間700円。共用個人開放250円とは分離 |
| `mitaka-nogawa` | 大沢野川グラウンドテニスコート | 同700円。ただし冠水復旧中で全4面休止、通常検索から除外。再開・予約可を保証しない |

## 再確認・保留

`kiyose-chuo`（中央公園）・`kiyose-shimokiyoto`（下清戸運動公園）は既掲載600円と公式表を再照合し、元の料金・ID・予約URLを保持。取消条件のみ追加。

| 施設ID | 保留理由・確認先 |
| --- | --- |
| `tokyo-venue-2b0bbd7157ff` 秋留台公園 | [都立公園案内PDF](https://www.tokyo-park.or.jp/park/akirudai/assets/akirudai-field.pdf)は団体有料・金額問い合わせ。個人無料を貸切0円にしない |
| `tokyo-venue-c282bded258a` 川町運動場少年野球場 | [八王子市施設案内](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012073.html)に対象貸切の金額なし。中学生以下等の条件を確認 |
| `tokyo-venue-205d87234dd3` 府中朝日フットボールパーク | [府中市施設案内](https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/asahi.html)は一般グラウンド使用不可。クラブハウス会議室の料金をピッチ料金にしない |
| `tokyo-gym-a231878afdcf` 小金井市総合体育館 | [指定管理者団体案内](https://www.koganei-sponavi.net/gymnasium/group/)の貸切PDFは今回も取得・表の読取ができず保留 |
| `musashimurayama-mitsugi` 三ツ木庭球場 | [共通ページ](https://musashimurayama-gym.jp/sports-facilities/tennis)に数値表があるが市内外対応が不明瞭。7月料金改定告知は大南・雷塚のみを明示するため、三ツ木へ流用せず保留。共通返還条件は記録 |

## 取消・天候・登録の一次情報

- 立川5施設：[2026年8月版料金表](https://www.city.tachikawa.lg.jp/_res/projects/default_project/_page_/001/008/085/tebiki_20260801.pdf)18頁。[現行ペナルティ](https://www.city.tachikawa.lg.jp/kanko/sports/1002923/1002944/1025596.html)で現地払い施設の前日取消・当日開始前連絡例外と、自治大学校の14日前基準を区別。制裁期間は取消料ではない。不特定多数向け参加費付き募集も営利のおそれとして対象。既払還付・雨天免除率は未確認。
- 武蔵村山3施設：[改定告知](https://musashimurayama-gym.jp/news/info/5717)、[共通利用・返還条件](https://musashimurayama-gym.jp/sports-facilities/tennis)。事前窓口取消や天候等は返還対象、雨天申出は前日又は当日開始後1時間以内、申出後1か月・許可書兼領収書等の条件あり。返還割合は明記を確認できず、無料取消とは断定しない。
- 福生4施設：市の各施設ページ [S&D](https://www.city.fussa.tokyo.jp/map/sports/1001680.html)、[南公園](https://www.city.fussa.tokyo.jp/map/sports/1001670.html)、[武蔵野台](https://www.city.fussa.tokyo.jp/map/sports/1001677.html)、[福東](https://www.city.fussa.tokyo.jp/map/sports/1001666.html)。[現行登録案内](https://www.city.fussa.tokyo.jp/1021105/index.html)を確認。検索に残る旧手引きPDFは404で、取消・雨天条件は未確認と明記し、推測の規定を追加しない。
- 日野3施設：[指定管理者料金・登録案内](https://hino-playground.com/facility/tennis)、[2027年改定](https://www.city.hino.lg.jp/shisetsu/sports/1032278.html)、[取消案内](https://www.city.hino.lg.jp/bunka/yoyaku/1007380.html)。取消料なしと既払不還付は別。前日・当日は電話、無断3回で3か月停止。雨天例外は未確認。
- 清瀬4施設：[中央・下清戸・内山料金表](https://www.city.kiyose.lg.jp/shisetsu/riyouyoyaku/1005433.html)、[ひまわり料金表](https://www.city.kiyose.lg.jp/shisetsu/riyouyoyaku/1005439.html)。30日前80%・20日前60%・前日30%は「還付率」。各窓口手続き、雨天時の割合未確認等を分けて記録。
- 三鷹3施設：[大沢総合](https://mitaka-sportsandculture.or.jp/zaidan/other/ground/)、[新川](https://mitaka-sportsandculture.or.jp/zaidan/other/tennis/)、[大沢野川](https://mitaka-sportsandculture.or.jp/zaidan/other/ground/nogawa.html)。市内団体の通常貸切のみ採用。7日前を過ぎると料金発生、事前納付後・期限後は施設連絡。旧案内の全員市民要件ではなく、[2026年10月以降の登録条件](https://www.mitakagenki-plaza.jp/sports/dantai_20260223101459.html)を使用。団体4人以上、市民半数以上、全員登録・責任者本人確認等。新規個人貸切と従来の共用個人開放は混同しない。

大沢野川の休止は[市の現行施設案内](https://www.city.mitaka.lg.jp/c_service/001/001667.html)と指定管理者の両方で確認。運営者が休止予約を取消処理する旨があり、通常の自己都合取消と分離。

## 保全・検証

料金・取消サイドカーへの追記のみ。元カタログの例外は大沢野川1件の休止状態・注記・確認日・出典追加だけ。元ID・予約URL・その他の施設情報、従来レビュー、個人情報・認証・決済・環境変数・DBスキーマ・料金プランは変更しない。
生成スクリプトは同一内容で再実行しても不変、既存料金や相違する既存レビューは書込み前に拒否。履歴テストは日付別スナップショットと今回の明示的な休止差分だけを許容する。
新テスト：`scripts/test_venue_fee_followup_20261106.py`。会場系233件と配信量制御12件を通過。最後の照明単位明記後も新規10件を再実行し通過。
一時DB・localhost限定でPCと390×844のスマホ表示を確認。清瀬の市内外料金・還付率、大南の通常枠と季節限定枠、詳細展開・絞り込み、画像の読込みと横はみ出しなしを確認した。表示サイズは復元。本番Live・公開URLの確認結果は非公開の作業記録へ保存する。
