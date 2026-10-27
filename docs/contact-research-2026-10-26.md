# 公開連絡先調査 2026-10-26

## 対象と結果

2026-10-27再開時、直前の会場更新を含む最新main `d6339092c034faffadfe88cffeb5fbf5cb304b01` と未反映の26件の証拠・採否を再確認した。公開ページの実取得日は以下のとおり10月26日のままとし、再開や再検証を新規取得として数えない。公開連絡先JSONの正規化ハッシュは前回と一致し、本番統計も全9,350・社会人2,990掲載を維持。連絡先関連108・招待31テストを最新mainで再実行して全139件成功。既存の非公開調査結果を上書きせず、本番検証・反映の記録を別に保存する。

最新main `55a7ff321a43d845c15ebd9fc075aa745393745f`、本チャットの進捗、公開連絡先JSON、過去10回の非公開個別レビュー、公開DB9,350掲載を先に確認。直前の会場料金更新と過去の連絡先更新を保全した。東京3・神奈川20・埼玉3の社会人DB掲載26件について、元のID・名称・掲載元URLを現在の公開一覧と照合し、掲載元から直接リンクする公式ページ等を公開GETで調べた。

今回採用できる団体共有メールは0件。既存の公開JSON481掲載（メール420・フォーム53・LINE8）は値・順序とも変更せず、社会人メール累計167掲載、全窓口228掲載を保持。メール未取得は8,930掲載（社会人2,823）、窓口未確認は8,869掲載。確認範囲での未取得であり、全件取得済みやウェブ上にメールが存在しないという意味ではない。

社会人DB分類が対象年齢を保証するものではないため、ジュニア・小学生対象団体も個別に区別した。フォーム・LINEをメールへ変換せず、今回は新規窓口を追加しない。Firecrawl検索は利用枠不足で実行されず、条件変更での再試行・課金を行わず通常の公開ページ取得を使用した。

## 個別確認

各行の確認日は2026-10-26。元のcircle_id、掲載元、実際の取得URL・日時・本文、画像確認根拠、保留理由は非公開個別記録に対応付けて保存。以下のURLは出典であり、団体メールの取得済みを意味しない。

| 掲載元 | 確認した公式ページ等 | 保留理由 |
| --- | --- | --- |
| [B-Freaks・東京](https://www.net-menber.com/look/data/94256.html) | [公式](https://b-freaks.crayonsite.com/) | 30歳以上の社会人バスケ。体験問い合わせフォーム案内、団体メール未確認。別掲載の以前の確認を新規メールとして数えない。 |
| [南葛西スリーファイヤーズ](https://www.net-menber.com/look/data/150956.html) | [公式](http://mtf-jvc.sakura.ne.jp/)、フレームのメニュー・トップ | 現行更新を確認。画像のホバー表示は監督個人宛で、団体共有メールとして公開しない。小学生ジュニア対象。 |
| [ゴルフサークルK's・7月ラウンド会](https://www.net-menber.com/look/data/230939.html) | [公式](https://sites.google.com/view/ks-golf-circle/) | 成人向け平日ゴルフのLINE・入会フォーム案内。団体メール未確認、カレンダー所有者等は除外。 |
| [TEREA](https://www.net-menber.com/look/data/196625.html) | [掲載先Notion](https://playful-booklet-d8d.notion.site/TEREA-f48fc82f2f794e56af86547a15fa3175?pvs=4) | 取得本文は読み込みに必要な内容が不足。認証や隠れたAPIを使わず保留。 |
| [レクリエイターズ・根岸駅](https://www.net-menber.com/look/data/91276.html) | 掲載元からリンクしたGoogleフォーム | つばさシャトル’s参加申込フォームであり、一般の団体メールではない。回答・ログインなし。 |
| [セピア](https://www.net-menber.com/look/data/11408.html) | [公式ブログ](https://sepiagogo.exblog.jp/)、[プロフィール](https://sepiagogo.exblog.jp/profile/) | 戸塚区のママさんバレーの同一性を確認。個人コメントと運営会社窓口を採用しない。 |
| [ラオウ杯](https://www.net-menber.com/look/data/198379.html) | [公式ブログ](https://ameblo.jp/tennis39-entry/) | テニス開催・雨天中止案内、団体メール未確認。Ameba共通窓口は除外。 |
| [南小ドリームズ](https://www.net-menber.com/look/data/216070.html) | [公式](https://nanshodreams.wixsite.com/dreams) | 少年野球の公式LINE案内、団体メール未確認。成人チームとは扱わない。 |
| [女子6人制Legend](https://www.net-menber.com/look/data/152347.html) | [掲載先](http://www2.hp-ez.com/hp/volleyteam-legend) | 取得本文が不足。同名別チームや混合チームのメールを転用しない。 |
| [横浜優和クラブJr.](https://www.net-menber.com/look/data/197132.html) | [公式](https://yokohamayuwajr.wixsite.com/yuwa)、[問い合わせ](https://yokohamayuwajr.wixsite.com/yuwa/contact) | ジュニア向け問い合わせフォーム、団体メール未確認。 |
| [ミドル＆シニア海倶楽部](https://www.net-menber.com/look/data/114720.html) | [主催者管理のプロフィール](https://commu-chika.jp/organizations/416) | マリントーク倶楽部の活動を照合。運営会社の問い合わせフォームとLINE共有リンクを団体窓口にしない。 |
| [狛江市周辺バスケットボール](https://www.net-menber.com/look/data/192150.html) | [公式](https://sites.google.com/view/basketball-komae) | 参加はLINE、練習試合は掲載元メッセージという用途を区別。メール未確認。 |
| [登山・アウトドア社会人サークル](https://www.net-menber.com/look/data/60022.html) | [掲載先](http://lifeofmountain.net/about) | robots制限で停止。別経路へ切り替えて回避しない。 |
| [相鉄沿線バド好き練習会](https://www.net-menber.com/look/data/214127.html) | [掲載先](https://www4.hp-ez.com/hp/audo/page2/1) | 有効な本文情報が不足、連絡先未確認。 |
| [ダンスサークル・クローバー](https://www.net-menber.com/look/data/83662.html) | [掲載先](https://trump.who-dance.com/)、問い合わせ | 現在のリンク先は渋谷のTrumPを名乗る。名称継承の明示的根拠なしに別名の団体窓口へ結び付けない。 |
| [座間市空手道連盟所属・鳳友会](https://www.net-menber.com/look/data/143567.html) | [公式](https://houyuukai.wixsite.com/houyuukai-karate) | LINE・無料体験案内。団体メール未確認。 |
| [羽の輪](https://www.net-menber.com/look/data/230012.html) | [公式リンク先note](https://note.com/note_riruru)、クリエイターへの問い合わせ | 公開プロフィール・メッセージページを確認。noteの共通窓口やメッセージをメールに転用しない。 |
| [ゴルフサークルpgc](https://www.net-menber.com/look/data/170451.html) | [公式](http://home.g02.itscom.net/pgc/)、[公開の団体案内](http://home.g02.itscom.net/pgc/pgc2.htm) | 正式メールは会員承認後だけ通知。伏字のYahoo例示から推測しない。会員認証パスは取得せず、入会・問い合わせフォームを区別。 |
| [都岡ミニバスケットボールクラブ](https://www.net-menber.com/look/data/191852.html) | [公式](https://tuokaminibasu.crayonsite.net/) | 体験・各種問い合わせフォーム案内。団体メール未確認、児童対象。 |
| [闘塾](https://www.net-menber.com/look/data/215512.html) | [公式](https://www.karatetojuku.com/)、問い合わせ | 見学・体験・質問フォーム、LINE、稽古予約を区別。加盟連盟の窓口を転用しない。 |
| [インプレッシブ](https://www.net-menber.com/look/data/21821.html) | [公式](https://imprehike.com/)、直接リンクの問い合わせ先 | 問い合わせフォーム先はrobots制限。イベント取消・緊急連絡シートを一般メールに転用しない。 |
| [そある](https://www.net-menber.com/look/data/209423.html) | [主催者のサークルプロフィール](https://www.tennisbear.net/circle/45272/info/) | テニスベアの一般サポートは団体の窓口ではない。メール未確認。 |
| [エンジョイバスケ](https://www.net-menber.com/look/data/170418.html) | [掲載先](https://honmokunomirai.com/) | 現在は英語スポーツニュースの内容で、掲載バスケ団体との同一性を確認できない。窓口を採用しない。 |
| [Jadeバドミントンクラブ](https://www.net-menber.com/look/data/175347.html) | [公開mixiコミュニティ](https://mixi.jp/view_community_detail.pl?id=6150557) | 桶川支部の公開説明を確認。参加にはログインが必要。mixi共通窓口は除外し、認証領域には入らない。 |
| [平日昼間にバスケ](https://www.net-menber.com/look/data/220551.html) | [主催者の団体情報](https://www.c-sqr.net/c/cs140508/about) | 川口市の月曜昼間活動、男性39歳以上などの申込条件とフォームを確認。団体メール未確認。 |
| [バレーボールサークルSGP](https://www.net-menber.com/look/data/222881.html) | 掲載元からリンクする公開Googleドキュメント | 理念・方針の団体管理文書を確認。本文にメール未掲載。文書所有者を連絡先と推定しない。 |

## 保全と検証

取得本文、公開画像、取得日時、採否、ID対応は新しい非公開調査フォルダへ保存し、既存の非公開結果を変更しない。非公開画像に含まれる個人メールや候補一覧は公開リポジトリへ追加しない。公開JSONは前mainの内容と改行を正規化して完全一致を確認。既存の公開設定・抑止指定、団体情報、DBスキーマ、環境変数、料金プランを変更しない。今回の公開変更は調査記録のみ。

既存テストで公開メールと実DBシードのID・名称・掲載元URL照合、`enabled=0`維持、プロフィールの公開同意・掲載フラグを再取り込みで解除しないことを検証する。公開APIと初期HTMLをスマホ・PCで確認し、main反映後は指定された既存Renderサービスの対象コミットLive化と本番 `https://circle-match.jp/?tab=db` を確認する。検証・反映結果は非公開のpublication記録へ保存し、ビルド中を完了としない。

ローカルでは連絡先関連108テスト、招待関連31テストの139件が成功。隔離した実アプリDBの26掲載でID・名称・掲載元URLと連絡先未追加を照合し、390/1440px・JavaScript無効を含む10表示ケース、公開DBトップのHTTP 200、横はみ出し・ブラウザエラーなしを確認。既存のYSTCメールと、同一性を確認できない2掲載及びPGCの未追加を表示検証した。テスト専用DB・証拠画像を本番DBや公開シードへ取り込まない。

送信、問い合わせ、ログイン、会員登録、友だち追加、支払い、有料契約は行っていない。新規メール0件のため公開JSONへの追加を捏造せず、既存481件を保全する。
