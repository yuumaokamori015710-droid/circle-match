# 関東の社会人サークル連絡窓口調査（2026-10-16）

東京14団体、神奈川11団体、埼玉1団体の計26団体について、登録出典とそこから案内された公式サイトを確認。公開メール2件、一般問い合わせフォーム5件、公式LINE1件を追加した。問い合わせ・メール送信、友だち追加、ログインは行っていない。

## 採用した窓口

| 団体 | 登録出典 | 実際の窓口掲載元 | 種別・用途 |
| --- | --- | --- | --- |
| FC.サルミナート | [117668](https://www.net-menber.com/look/data/117668.html) | [公式お問い合わせ](https://kazyusya.wixsite.com/salminart/contact) | 代表者宛て公開メール |
| paradox横浜 | [116582](https://www.net-menber.com/look/data/116582.html) | [公式メンバー募集](https://paradoxyokohama.iinaa.net/recruit.html) | 入団・練習参加の公開メール。イベント勧誘への同意ではない |
| YOU.FO体験会 in 台東区 | [228470](https://www.net-menber.com/look/data/228470.html) | [日本YOU.FO協会](https://youfo.or.jp/contact/) | 体験会・イベント・パートナーシップ相談フォーム |
| Internationl Basketball Club | [73444](https://www.net-menber.com/look/data/73444.html) | [公式お問合わせ](https://internationalbasketballclub.jimdofree.com/お問合わせ/) | 参加・見学・質問フォーム。DBの元の名称表記を保持 |
| SITクラブ | [120131](https://www.net-menber.com/look/data/120131.html) | [公式お問い合わせ](https://sit-rugby.club/お問い合わせ/) | 一般問い合わせフォーム |
| MakeSmileフットサルクラブ | [231798](https://www.net-menber.com/look/data/231798.html) | [NPO法人ONE](https://npo-one.jp/info/) | 派遣事業・イベント企画等の相談フォーム |
| RED Bein（レッドバイン） | [137339](https://www.net-menber.com/look/data/137339.html) | [公式問い合わせ](http://redbein.net/page-401/) | 一般問い合わせフォーム。公式はHTTP、HTTPS接続未確認を用途欄にも明記 |
| ラビサル神奈川 | [213054](https://www.net-menber.com/look/data/213054.html) | [公式お問い合せ](https://kanagawa.rabisal.com/contact/) | ページ内の実際のリンク先を採用した公式LINE。本文のID文字列から推測しない |

全件の元の `circle_id`、団体名、`circle_source_url` を保持し、窓口の掲載URL・用途・確認日を公開JSONへ保存。公式サイトの窓口が存在することと、交流招待への同意・本人確認・返信保証は区別する。

## 今回追加しなかった18団体

| 団体 | 今回確認した範囲での結果 |
| --- | --- |
| FCチャレンジ | 掲載元・公式サイトを再確認。既知の体験入部専用窓口は一般の交流相談用として採用しない |
| S2フットサル | 掲載元・公式スケジュールの確認範囲では公開メール未発見 |
| divertir大田 | 登録先の旧公式サイトは404。別の現行サイトに他チーム・イベントへの勧誘を断る表示があり、招待窓口に採用しない |
| ★NO NAME FC★ | 公式サイトはジモティー・スポーツやろうよ・LaBOLAでの問い合わせを案内。今回公開メール未発見 |
| お水の会 | 掲載元・公式ブログを確認。ブログの文字コード・解析に問題があり、連絡先は保留 |
| スポの輪 | 掲載元・主催者のCAMPFIRE公開ページでメール未発見。ログイン必須の連絡機能は取得しない |
| ブランディングス | 公式はアメリカンフットボール団体。入部・体験フォームを一般交流用に流用しない |
| 浦安フリーダム | 掲載元が案内するLaBOLA募集URLは404。別団体の窓口で補完しない |
| Hi-Clear | 公式サイトにフォームへのリンクはあるが、今回メール未発見・一般交流用途は未確認 |
| THB | 案内された公式サイトを取得できず保留 |
| Team Mishmash | 公式はLINEでの加入・試走案内。一般交流用途を確認できず、メールも今回未発見 |
| Desfrute | 掲載元・公式トップの確認範囲では公開メール未発見 |
| FC COLORREAL78 | 公式に小中高校生向け体験練習フォームがあり、成人団体への一般招待先として流用しない |
| Mata-mata | 掲載元を確認。案内先はrobotsで取得不可、回避しない |
| STKフットサル | 掲載元・案内されたイベントページでメール未発見。ページの初期HTMLが空で、存在しないとは断定しない |
| Vitality 〜体育〜 | 登録先の旧公式URLは404で保留 |
| in.harmonyFC | 登録先は取得制限あり。ジュニア団体向けの別用途窓口を採用しない |
| 完熟とまとFC | 公式の問い合わせページは本文・フォームなし。実際に連絡できる窓口とは扱わない |

非公開の取得記録・キャッシュ・確認した全文はGit管理外の `private-circle-contacts-20261016` に保管し、既存の2026-10-14調査を上書きしない。自動調査の結果と、追加の公式ページ確認を反映した `manual-review.json` は別ファイルで保存した。「未発見」は今回確認した範囲の結果であり、全サイト・SNSを調べ尽くした意味ではない。

## 集計

- 追加後の確認済み窓口: 408団体（メール399、フォーム8、LINE1）。
- 社会人: メール146団体、フォーム・LINE込み155団体。大学メール253団体は変更なし。
- 9,350団体のスナップショット基準で、確認済み窓口のない団体8,942、メール未取得8,951。
- 既存の非公開設定・`enabled=0`、利用者の連絡先・代表申請情報は変更しない。件数は確認済みJSONの累計であり、個別の非公開設定によって公開表示件数は減る場合がある。

## 検証

- 既存400件のJSONがすべて未変更であることを前コミットと構造比較した。
- `test_public_contacts`、`test_contact_research`、`test_contact_research_http`、`test_contact_candidate_review`、`test_circle_contact_crawler`、`test_circle_invitations` の114テストが成功。初回はWindowsのローカル接続切断が1件発生し、単独・全体の再実行は成功した。
- 実際の全件シードDBで408件のID・名称・出典対応を検証。新規メール・フォーム・LINEの全件について、非公開プロフィールと無効化の維持を検証した。
- `verify_public_contacts_20261016_browser.cjs` で390px・1440px各8団体とJavaScript無効8団体を検証。初期HTML、絞り込み後の正確な団体ID、連絡窓口リンク、公開用途、横スクロールなしを確認。外部窓口はクリック・送信しない。
- 本番確認には同じスクリプトを `CONTACT_TEST_URL=https://circle-match.jp` で実行できる。公開APIだけを読み、募集・申請・個人情報を作成しない。
