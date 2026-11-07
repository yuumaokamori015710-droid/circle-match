# 2026-11-07 公式料金・取消条件の継続調査

確認日: 2026-11-07 (JST)。基準main: `b2bd02898598d47b2e9476e120f1f834d40646c9`。開始時の`78eb410`から追加された連絡先変更を保全して取り込んだ。

24施設を調査し、17施設に料金、6施設に取消・天候条件を追加。7施設は金額保留。既存料金と既存の取消条件は上書きしていない。
総数1,206施設、料金掲載958、未掲載248（通常検索対象237）。前回941掲載・265未掲載から17件増加。

残る未掲載サッカー・体育館系4施設を先に確認したが、団体のコート貸切料金を特定できず保留を継続。その後、東京都の未掲載テニス施設を優先した。

## 新たに確認した料金

金額は公式記載額。最低・最高は同じ施設・課金単位・登録/年齢区分でのみ計算。市内外、限定枠と通常枠、照明を混ぜない。時給への換算はしない。

| 施設ID | 施設 | 今回確認した範囲と一次情報 |
| --- | --- | --- |
| `tokyo-venue-e2d803873b82` | 戸倉第一 | [市の施設案内](https://www.city.kokubunji.tokyo.jp/shisetsu/sport/tennis/1004190.html)。登録対象者の1面2時間1,600円。市内在住在勤在学の個人又は登録サークル団体のみ |
| `shibuya-sportscenter` | 渋谷区スポーツセンター庭球場 | [市の貸切料金](https://www.city.shibuya.tokyo.jp/shisetsu/sports-shisetsu/sports-center/sp0_spcenter2.html)。1面2時間1,400円、照明30分250円別。個人開放400円と区別。A/B面利用可能、C/D面は令和23年度まで休止 |
| `shibuya-nishihara` | 代々木西原公園庭球場 | [区の施設案内](https://www.city.shibuya.tokyo.jp/shisetsu/sports-shisetsu/sports-center/sp2_nishihara.html)。1面2時間1,400円、照明30分250円別 |
| `shibuya-honmachi` | 本町コミュニティセンター庭球場 | [区の施設案内](https://www.city.shibuya.tokyo.jp/shisetsu/sports-shisetsu/sports-center/honmachicc_sports.html)。平日9～15時の1面2時間2,000円。団体登録必須・ゲスト利用不可。土日等のグラウンド利用をテニスと表示しない |
| `koto-shinsuna` | 新砂庭球場 | [指定管理者の現行適用料金PDF](https://www.di-ksp.jp/wp/wp-content/uploads/R6%E5%88%A9%E7%94%A8%E6%96%99%E9%87%91%E6%94%B9%E8%A8%82%EF%BC%88%E6%96%B0%E7%A0%82%E9%81%8B%E5%8B%95%E5%A0%B4%EF%BC%89_202402HP%E5%91%A8%E7%9F%A5.pdf)。2025年4月承認分から、1時間平日1,100円・土日祝1,800円。撮影用1,400円を貸切料金にしない |
| `meguro-kumin` | 目黒区民センター庭球場 | [2026年4月利用ガイド26頁](https://www.city.meguro.tokyo.jp/documents/5809/sportsguidebook.pdf)。2時間の区民大人2,400円・小人1,200円、区外大人4,800円・小人2,400円。8/16～31・11/15～1/31の最終回だけ1時間・各半額、通常枠とは分離 |
| `akiruno-yamada` | 山田グラウンドテニスコート | [2026年10月更新市施設案内](https://www.city.akiruno.tokyo.jp/0000007644.html)。2時間、市内1,300円・市外3,900円。17時以降又は照明利用は市内1,500円・市外4,300円の夜間使用料。別途加算とは解釈しない |
| `akiruno-sogo` | 総合グラウンドテニスコート | [市施設案内](https://www.city.akiruno.tokyo.jp/0000007648.html)。1面2時間、市内1,300円・市外3,900円。12/20～3/20季節休場を注記 |
| `akiruno-tamamikazaki` | 玉見ケ崎テニスコート | [同市料金表](https://www.city.akiruno.tokyo.jp/0000007648.html)。1面2時間、市内500円・市外1,500円。無料の周辺広場と区別。12/20～3/20季節休場を注記 |
| `fuchu-koyanagi` | 小柳庭球場 | [市施設案内](https://www.city.fuchu.tokyo.jp/shisetu/supotu/tekyujo/koyanagi.html)。1時間の基本使用料、市内400円・市外800円。照明加算は市内650円・市外1,300円、E面は昼間のみ |
| `higashiyamato-kaminakahara` | S&D上仲原テニスコート | [指定管理者案内](https://www.higashiyamato-taiikukan.com/s-d%E4%B8%8A%E4%BB%B2%E5%8E%9F%E3%83%86%E3%83%8B%E3%82%B9%E3%82%B3%E3%83%BC%E3%83%88)。1面2時間、大人800円・中学生以下400円、照明1,000円別。中学生以下のみ不可・保護者同伴。市内外登録可。営利・譲渡・転貸不可 |
| `musashino-tennis` | 武蔵野庭球場 | [指定管理者料金表](https://www.musashino.or.jp/_res/projects/default_project/_page_/001/001/569/1001569-02.pdf)。1面2時間、市民1,000円・市民以外2,000円。参加料徴収時3倍の条件は通常範囲に混ぜず、別規約の確認を案内 |
| `komae-motoizumi` | 元和泉市民テニスコート | [指定管理者案内](https://www.komae-sponavi.net/other/motoizumi_tennis/)。2時間一般1,400円・高校生以下800円。9月16～17時の1時間枠700円・400円は別単位。市内在住在勤在学・個人登録限定 |
| `komae-higashinogawa` | 東野川市民テニスコート | [指定管理者案内](https://www.komae-sponavi.net/other/higashinogawa/)。2時間一般1,400円・高校生以下800円。同じ個人登録条件。高校生以下価格は本人申込かつ対象者のみでの利用 |
| `chofu-midori` | 市民緑ケ丘テニスコート | [市の現行案内](https://www.city.chofu.lg.jp/040070/p026083.html)。1面2時間、市内2,400円・市外4,800円、照明30分300円別。営利目的利用不可の具体条件も保存 |
| `hamura-fujimi` | S&Dスポーツパーク富士見テニスコート | [市公園有料施設料金表](https://www.city.hamura.tokyo.jp/0000000768.html)。6～18時2時間600円、18～21時3時間900円。照明1時間510円別。市外加算を推測しない |
| `machida-tsuruma` | 鶴間公園テニスコート | [指定管理者案内](https://tsuruma-park.com/playfield/sports-ground/)。2時間、市内平日1,800円・土日祝2,500円、市外平日3,700円・土日祝5,000円。照明30分400円別。他の町田市営コートの1,040円を流用しない |

あきる野の市内料金は当日構成員の半数以上が市内在住在勤在学の場合。[渋谷スポーツセンター休止告知](https://www.city.shibuya.tokyo.jp/shisetsu/sports-shisetsu/sports-center/sportscenterkasetukousyakennsetunitomonauitibusisetunoriyoukyuusinituite.html)のPDF表をレンダリングし、A/BとC/Dの対応を確認した。施設全体を休止扱いにはしない。

## 取消・天候の追記6施設

- 狛江2施設: 各指定管理者ページで3日前までシステム取消、期限後は電話。未払い不使用6回で1か月停止は金銭の取消料ではない。天候判断は開始30分前。開始30分未満は支払不要、2時間枠の30分以上1時間30分未満は半額。その他の割合を推測しない。
- 武蔵野: [現行庭球場案内](https://www.musashino.or.jp/sports/1001550/1001569.html)。朝一は8:30、他は2時間前に可否判断。施設中止は取消連絡不要。利用者判断の不使用は開始60分以内の連絡が必要。半分超過後中止は返金対象外。通常自己都合の期限・割合は保留。
- 目黒: 利用ガイド14頁の庭球場欄。4日前まではペナルティなし、3日前から直前取消。直前3回又は無断1回で3か月後まで予約制限。15頁の屋内施設専用返金率を庭球場に流用しない。
- 小柳: 市施設案内で雨天不使用を連絡し、使用料は次回予約に振替。現金返金とは記載しない。自己都合条件は未確認。
- 緑ケ丘: 市施設案内で前日までシステム取消。当日連絡は1か月、無断は3か月の新規予約停止。半分到達前の現地降雨で使用不可なら制裁免除だが連絡は必要。金銭の還付率は未確認。

鶴間の既存2026-11-05取消記録はそのまま保全。他施設の取消・天候条件で今回確認できなかった部分は、料金注記に未確認と記録した。

## 保留7施設

| 施設ID | 調査先・金額を採用しない理由 |
| --- | --- |
| `tokyo-venue-2b0bbd7157ff` | 秋留台。[都立公園案内PDF](https://www.tokyo-park.or.jp/park/akirudai/assets/akirudai-field.pdf)は団体料金問い合わせ。個人陸上開放無料をサッカー貸切0円にしない |
| `tokyo-venue-c282bded258a` | 川町少年野球場。[市施設案内](https://www.city.hachioji.tokyo.jp/shisetsu/104/p012073.html)に金額なし。中学生以下限定を確認 |
| `tokyo-venue-205d87234dd3` | 府中朝日。[市施設案内](https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/asahi.html)はグラウンド一般利用不可。会議室代をピッチに転用しない |
| `tokyo-gym-a231878afdcf` | 小金井総合体育館。[団体ページ](https://www.koganei-sponavi.net/gymnasium/group/)の貸切PDFが取得/解析失敗。個人利用や他室料金を流用せず保留 |
| `higashimurayama-maekawa` | 前川公園。[都施設情報](https://www.tokyo-parasports-navi.metro.tokyo.lg.jp/facilities/1811)で施設を照合。市本文と条例本文が取得拒否。検索抜粋だけから数値採用しない |
| `higashimurayama-undo` | 愛の泉みんなの運動公園。[都施設情報](https://www.tokyo-parasports-navi.metro.tokyo.lg.jp/facilities/1520)と市の公開案内を確認対象としたが料金表本文を取得できず保留 |
| `chofu-jindaiji` | 市民深大寺。[登録済み市公式ページ](https://www.city.chofu.lg.jp/040070/p026085.html)が取得拒否。緑ケ丘など他施設の料金を転用しない |

## 保全と検証

元の3カタログ、施設ID、予約URL、既存料金・出典・取消記録を保全し、料金・取消サイドカーへの追記のみ。環境変数、料金プラン、DBスキーマ、ログイン・応募・決済・配信量制御は変更しない。

`scripts/record_venue_fee_review_20261107.py`は既存価格・既存レビューとの競合を書込み前に拒否し、同じ入力で再実行しても不変。`scripts/test_venue_fee_followup_20261107.py`は8項目で保存内容・同単位の範囲・年齢/市内外/季節条件・未知の価格・全既存データ保全・API/初期HTMLを検証する。カタログのバイト比較はGitのWindowsチェックアウト改行だけ正規化する。

過去の調査テストは、従来と同じ日付別集計・追記前方一致方式を11月6日分にも適用。過去に保留だった鶴間が今回の正確な料金レコードに一致することを検証し、単に保留アサートを削除しない。

PDF料金表は一次情報をダウンロードし、表の行・列をレンダリングして目視確認した。画像・一時DB・検証ログ・デプロイ確認は非公開の作業記録に保存する。予約・問合せ送信・支払いは行っていない。

会場系241テストを通過。ChromeのPC幅と390×844で鶴間の市内外の料金範囲、詳細展開、目黒の8料金区分、出典と取消確認日、横はみ出しなしを確認。スポーツ画像の読込みも確認した。ブラウザ画像のファイル保存は実行環境の書込み制限によりできなかったため、画面の目視とDOM検査結果を作業記録に残し、保存済み画像があるとは扱わない。表示サイズは復元済み。
