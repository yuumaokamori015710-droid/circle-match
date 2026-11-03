# 公開連絡先調査 2026-11-03

## 対象と結果

最新GitHub main `7dcf22c8f0efbd4d0e923b1c4832967fffd5a4f7`、本チャット、手順、
公開JSON482掲載と過去の非公開個別レビュー37ファイルを確認した。
公開DBの9,350掲載（社会人2,990掲載）を再取得し、既存窓口・既調査IDを除外した
東京の社会人スポーツ26掲載を調査した。件数はDB掲載数で、実在団体の重複除外数ではない。

**今回追加した公開団体メールは2件、いずれも参加応募用**。
公開窓口は484掲載（メール423・フォーム53・LINE8）、社会人メール累計170掲載、
社会人の全窓口231掲載。メール未取得8,927掲載（社会人2,820）、全窓口未確認8,866掲載。
残りは確認範囲で未取得の件数であり、メール不在や全件調査済みを意味しない。

## 採用した出典と用途

- [enjoy_tennisの主催者募集](https://circle-book.com/circles/8437): 木場公園の社会人テニス。
  「応募方法」で氏名・連絡先メール・年齢・性別・テニス経歴を添えて送るメールを公開。
  初心者・経験者を募集し、キャンセルは前日まで、勧誘・迷惑行為は禁止。
  通常Chromeの未ログイン表示で宛先と団体名を照合した。
- [Full Forceの主催者募集](https://circle-book.com/circles/58585): 港区・品川区・大田区のバスケ。
  「メールの場合」の宛先、件名「東京バスケ(お名前)」、名前・年齢・部活動歴・バスケ歴・
  希望レベルの指定を確認。通常・ゆるめ・わいわいで経験条件が異なり、わいわいは経験者の
  参加を制限する。勧誘・迷惑行為は禁止。通常Chromeの未ログイン表示で照合した。

元circle_id・DB掲載名・元掲載URLと実際のメール掲載URL・確認日・用途をJSONに保持。
どちらも一般の大会営業・交流招待への受信同意、返信、到達を確認したものではない。
HTML取得器では両メールが `[email protected]` と表示され自動判定が未発見だったため、
通常ブラウザでサイトが公開表示する実際の宛先を確認した。アドレスの推測はしていない。

## 個別確認

実取得日は2026-11-03。元ID・名称・掲載URL・取得日時・本文・直接リンク・
用途・保留理由はGit管理外の `private-circle-contacts-20261103/` に保存した。

| 掲載元 | 確認範囲と判断 |
| --- | --- |
| [enjoy badminton](https://circle-book.com/circles/4561) | 杉並の成人バドミントン。本文の「お問い合わせメール」だけでは受信アドレスを確認できず保留。 |
| [enjoy_tennis](https://circle-book.com/circles/8437) | 上記参加応募用メールを採用。木場公園・募集条件と同一性を照合。 |
| [EPOCH](https://circle-book.com/circles/4201) | バスケメンバー・練習相手募集。メールで返信する記載を受信先の公開と取り違えない。 |
| [EVOLVE](https://circle-book.com/circles/18666) | 北区の混合バレー。継続所属向け・単発不可。Instagram本文は未取得でメール未確認。 |
| [Full Force](https://circle-book.com/circles/58585) | 上記バスケ参加連絡用メールを採用。件名・希望レベル指定を保持。 |
| [futbal](https://circle-book.com/circles/72986) | 初心者向け混合フットサル。主催者募集欄の範囲でメール未確認。 |
| [gente](https://circle-book.com/circles/11442) | 荒川のバスケ。コメント・Instagram・ThreadsのDM案内。SNS本文は未取得。 |
| [IROHA](https://circle-book.com/circles/3668) | 直接リンクの公式女子6人制ページまで取得。入部・大会紹介・練習試合はフォーム案内でメール未確認。男子SABUROKUと混同しない。 |
| [Lien](https://circle-book.com/circles/72401) | 大田区の混合バレー。メッセージ・DM案内。YouTube動画をメール根拠にせず、SNS本文は未取得。 |
| [LIONSと summers](https://circle-book.com/circles/5902) | 府中のバスケ。学校アクセスリンクは会場案内で、学校メールは団体窓口にしない。 |
| [Momongaバスケットボールクラブ](https://circle-book.com/circles/3224) | 公式サイトとお問い合わせを取得。フォーム・公式LINEのみ、公開受信メールは未確認。広告メールお断りを保持。 |
| [neccot](https://circle-book.com/circles/16362) | 東京のバスケ。主催者募集欄を確認、Instagram本文は未取得でメール未確認。 |
| [Newbies](https://circle-book.com/circles/20634) | 東京23区の初心者バスケ。漢字フルネーム・希望枠を添える継続参加用メッセージ案内。 |
| [No name ballerZ](https://circle-book.com/circles/7770) | 立川のバスケ。応募事項不足は返信しない条件とInstagram DM案内。返信メールの言及から宛先を推測しない。 |
| [Pisutatio](https://www.net-menber.com/look/data/100497.html) | 北区西が丘のフットサル。公開募集欄でメール未確認。検索結果の奈良の同名チームは別団体として除外。 |
| [Purple Wizards](https://www.net-menber.com/look/data/71845.html) | 西東京きらっとで活動するバスケ。公開募集本文でメール未確認。 |
| [Pバス](https://circle-book.com/circles/16967) | 目黒のバスケ。名前・年齢を添えた掲載元メッセージ案内のみ。 |
| [Queen Bees](https://www.net-menber.com/look/data/215958.html) | 女子バスケの見学・加入募集。主催者公開本文でメール未確認。 |
| [Rad Perillas](https://www.net-menber.com/look/data/162177.html) | 西東京のバスケ。Instagramリンクは記録、本文未取得でメール未確認。 |
| [Raging Spirits2](https://circle-book.com/circles/6871) | 東京の男女混合バスケ。掲載元メッセージの案内でメール未確認。 |
| [Re'F](https://www.net-menber.com/look/data/128715.html) | 板橋・北区のバレー。新規参加制限・応相談を保持、Instagram本文は未取得。 |
| [RHD](https://www.net-menber.com/look/data/231858.html) | 新宿のバスケ。戸山サンライズは会場であり団体連絡先ではない。 |
| [RISE](https://www.net-menber.com/look/data/104449.html) | 葛飾の女子9人制バレー。本文でメール未確認。2023年更新の古さを保持し、閲覧者の質問を根拠にしない。 |
| [Rockets](https://www.net-menber.com/look/data/142739.html) | 東京北区・大宮の野球。Instagram本文は未取得。スポンサーの窓口はチームメールにしない。 |
| [Rockies](https://www.net-menber.com/look/data/191427.html) | バスケの掲載元は募集停止。Instagram本文は未取得、募集停止を迂回する応募は行わない。 |
| [ROMANCE KING](https://www.net-menber.com/look/data/134294.html) | 荒川などの野球。2021年更新を保持。関連チーム・プラットフォーム窓口は除外。 |

## 直接リンク先と取得状況

- [IROHA女子公式](https://saburoku-iroha.crayonsite.net/p/3/)は2026年9月時点の募集・
  女性経験3年以上・大会紹介や練習試合相談を案内。問い合わせフォームへの直接リンクは
  記録したが、今回はメールのみの追加としフォームの送信・会員登録はしていない。
- [Momonga公式サイト](https://momongabba.jimdofree.com/)と
  [お問い合わせ](https://momongabba.jimdofree.com/お問合せ/)を取得し、練馬の初心者向け
  社会人バスケという同一性を照合。フォームのメール欄は送信者用で、公開受信メールと
  扱わない。企業の広告メールは一切お断りと明記されており、公式LINEの友だち追加なし。
- 掲載元26件は間隔を空け直列取得し、26件とも取得成功。追加の公式3ページも取得した。
  enjoy_tennisの外部取得サービスはエンジン取得失敗を返したが、拒否や認証必須と
  断定せず、通常Chromeで公開ページとメールを確認。CAPTCHAやログインの回避はない。
  未取得SNSを調査済みと扱わず、他人の投稿・カレンダー所有者・同名別団体は採用しない。

## 保全と検証

既存482掲載はレコード・順序・出典とも基準mainから維持し、2件だけ追記。
利用者プロフィールや非公開指定・`enabled=0` は再取り込み時も保全するテストを追加した。
元ID・掲載URLを26掲載とも実シード検索APIで照合し、新規2件のメール・用途・確認日と
HTMLの公開メール表示、招待作成画面への出典表示まで検証した。未確認24件は空欄を維持し、
後日の根拠ある窓口追加は許容する。連絡先・候補審査・招待の148テストが成功。
追加のHTML検証を含む今回のHTTP回帰テストも再実行で成功した。

隔離一時DBのスマホ390px・PC1440pxで、新規2団体と保留IROHAの6表示を確認。
横はみ出しなし。画面内の読み込み済み画像に欠落なしで、横スクロール外の未読み込み
lazy画像は破損と扱わない。コンソール警告・エラーなし。全ページ画像は取得タイムアウトと
なったためviewport画像を保存し、検証後に一時サーバーを終了した。
本番APIと同じ表示ケース・Render Liveは反映時に照合し、コミット・デプロイIDと実行結果を
非公開の公開記録へ保存する。

ログイン・応募・メール送信・フォーム送信・フォロー・決済なし。
直前のStripe接続と保留中テスト、既存の会場データ・UI・環境変数・料金プラン・
DBスキーマは変更していない。
