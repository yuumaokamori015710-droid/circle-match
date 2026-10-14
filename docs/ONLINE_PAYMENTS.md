# Circle Match オンライン決済

更新: 2026-10-15。コードは決済機能フラグ既定OFFで展開する。本番の実決済は未有効。
Stripeアカウントはテスト用サンドボックスまで作成済み。事業者確認、Connect設定、
Webhookと実際のテスト決済・返金の確認が済むまで本番決済フラグを有効にしない。

## 1. 実装範囲と構成

既存の Python HTTPServer / SQLite / Supabase 認証 / 通知Outboxを維持。
決済は `outputs/circlematch_payments.py`、SSR画面は `outputs/circlematch_payment_ui.py` に分離した。
`outputs/circlematch_db_app.py` の申込・開催案内・最終参加確認・マイページへ接続する。
既存イベントの参加費、無料・現地払い・口座振込、団体DB、画像、公開URLは一括変更しない。

- Stripe Python SDK: `stripe==16.0.0` (安定版)
- API: `2026-09-30.endive` を全SDKリクエストで指定
- Checkout hosted / Connect destination charge / JPプラットフォーム・JP主催者 / JPY / 単発カード
- 1注文1主催者。個人申込の友人分は代表者がまとめて支払う。チーム申込は1チーム分。
- オンラインの「個人・チーム両方」募集は料金単位が曖昧になるため保存時に拒否。既存の非オンライン募集は維持。
- カード、CVC、本人確認書類、銀行口座をCircle Matchで収集しない。
- SDKは遅延ロード。Stripe未設定・フラグOFFでも既存サイトは起動する。

## 2. 料金と資金の流れ

掲載料・月額料を新設しない。オンラインの参加費に利用料10%を含める。
決済処理費と当サイト利用料に係る消費税も10%内で負担する設計。
参加費へ別途の決済手数料・税を上乗せする処理はない。

すべて整数円。Python整数 / ブラウザBigIntで計算する。

```python
gross_unit_price = (desired_net * 10000 + 8999) // 9000
gross = gross_unit_price * quantity
service_fee = (gross * 1000 + 9999) // 10000
organizer_net = gross - service_fee
```

| 入力 | 支払総額 | サイト利用料 | 主催者分配 |
|---|---:|---:|---:|
| 受取希望1,800円、1人 | 2,000円 | 200円 | 1,800円 |
| 受取希望2,000円、1人 | 2,223円 | 223円 | 2,000円 |
| 単価2,000円、3人 | 6,000円 | 600円 | 5,400円 |
| 単価2,223円、3人 | 6,669円 | 667円 | 6,002円 |
| 単価2,000円、12人編成の1チーム | 2,000円 | 200円 | 1,800円 |

注文総額に対して丸めるので、1人分の丸め済み手数料の人数倍ではない。
0円は無料扱いとしてCheckoutを作成しない。オンライン有料総額は50〜99,999,999円。
未確定の数量で巨大な単価を設定しても、決済直前に注文総額の上限を再検証する。

Checkoutには `payment_intent_data.application_fee_amount` と `transfer_data.destination` を一度だけ指定。
Stripeでの総額分配とapplication feeの回収を照合し、注文の `net` を主催者受取見込額とする。
残高への分配と銀行入金は別。即時入金・開催後入金は約束しない。

### 費用・決済事業者

Connectアカウント作成では `controller.fees.payer=application`、
`controller.losses.payments=application`、Express dashboard、card_payments/transfersを指定。
これらが一致しない既存口座は利用可能としない。主催者へ費用を自動転嫁する処理はない。

`on_behalf_of` は指定しない。日本同士のdestination chargeでプラットフォーム側を
決済上の事業者とする構成を採用した。イベント提供者は画面上の主催者。
この役割分担、カード明細名、Stripe審査で認められる業務・契約を本番前に承認する必要がある。
主催者を決済上の事業者にする契約が必要なら、OBO・明細・費用・返金の再設計が必要。
[Destination charges](https://docs.stripe.com/connect/destination-charges?platform=web&ui=stripe-hosted)

2026-10-04の日本向け公開料金表では、プラットフォームが料金を管理するConnectに
有効アカウント月額200円と入金ごと0.25%+250円が掲載されている。
実契約・別途費用は未確認。少額・低頻度利用では10%を超える費用が生じ得る。
利用者への後出し請求で補填せず、運営負担・入金頻度・採算を本番前に判断する。
[Connect料金](https://stripe.com/jp/connect/pricing)

運営画面はChargeのbalance transactionから取得できた処理費のみ実績表示する。
未取得は「未確定」。利用料200円を利益200円とみなさない。
Connect月額・銀行入金・紛争の費用、税務上の売上・消費税内訳・適格請求書は未自動化。
Stripe請求明細との照合と税務確認が必要。

## 3. 状態と導線

```text
申込(pending / confirmed)
  -> 承認制なら主催者が受付確定
  -> 最低開催数がある場合は開催案内を待つ
  -> 案内がある場合は最新versionへ最終参加確認
  -> マイページ / 申込管理 / 開催案内から参加費確認
  -> 確認チェック -> Stripeの支払確定画面
  -> Stripeで「支払う」 -> 署名Webhook + API照合
  -> 支払確認済み -> Stripe残高分配 -> Stripe設定に従って銀行入金
```

最低開催数も開催案内もない従来型の先着募集では、受付確定後に支払える。
開催案内を更新しても、支払履歴がある申込に新たなCheckoutを作らない。
支払済みの人数・料金・返金条件変更を禁止。日時変更は既存の再案内を使用する。
既存の手動 `event_applications.payment_status` はオンライン成功判定に使わない。

注文: `creating -> open -> paid`、未払いでStripeの終了を確認した場合のみ `expired`。
照合不一致は `review`。`paid_at` は以後消さない。
返金: `none -> requested -> processing -> succeeded`、例外は `failed / partial / review`。
「全額返金処理済み」はRefundのsucceededと、APIの参加者返金・利用料返金・分配取消を確認した状態。
Chargeの返金合計だけでは完了としない。pendingは処理中、requires_actionは要確認とする。
カード明細への反映完了ではない。紛争は `dispute_state` で別管理。

受取設定: `incomplete / reviewing / ready / action_required / restricted`。
GETで登録完了にしない。「利用状態を確認する」のPOSTか口座WebhookでAPI照合する。
サークルDBの掲載・代表申請とは別に、ログイン主催者のuser_idへ口座を固定する。

## 4. 二重処理と復旧

- 注文をSQLiteの `BEGIN IMMEDIATE` 内で確保し、有効注文の部分UNIQUE制約で競合を防ぐ。
- 注文総額・数量・単価・受取人・開催案内・キャンセル条件をスナップショット化。更新禁止トリガーを置く。
- Session/Intent/Charge/返金ID、冪等キーを永続化。決済・返金・口座作成前に保存する。
- ネットワークI/OはSQLite書込トランザクションの外。処理権限は期限付きleaseで確保する。
- 同じ決済の再試行は同じパラメーター・同じキーを使う。作成結果不明のまま23時間を超えた場合は作り直さず運営照合へ。
- 有効Checkoutがある間は人数・料金・取消・枠解放を禁止。「決済画面を終了する」でStripeの実状態を再取得する。
- 成功と失効が競合したら実際の支払状態を優先。Webhook遅延だけで正常支払を無効にしない。
- 取消後の入金は要確認と返金申請を記録。中止イベントなら返金ジョブを予約する。
- 受取口座の制限通知では未払いCheckoutを失効させる。再開ボタンでも口座を再確認する。
- Webhookはraw body署名検証後、IDと処理用IDだけを永続化して応答。保存失敗は5xx。
- ワーカーはAPI再取得で確認するため、Webhookの順序やmetadataだけに依存しない。
- 支払・返金のアプリ通知とメールOutboxは同一DBトランザクションで1回だけ作成する。
- メール送信基盤が未設定なら `not_configured`。送信成功とは表示しない。

## 5. ローカルで確認する

```powershell
python -m venv .venv-payments
.\.venv-payments\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-payments\Scripts\python.exe -X utf8 -m unittest discover -s scripts -p 'test_online_payments.py'
.\.venv-payments\Scripts\python.exe -X utf8 -m unittest discover -s scripts -p 'test_payment_sdk.py'
.\.venv-payments\Scripts\python.exe -X utf8 -m unittest discover -s scripts -p 'test_event*.py'
.\.venv-payments\Scripts\python.exe -X utf8 scripts/test_event_flow.py
.\.venv-payments\Scripts\python.exe -X utf8 scripts/preview_online_payments.py --port 8896
```

プレビュー: `http://127.0.0.1:8896/preview`。仮ユーザー・仮イベント・FakeStripeだけを使用する。
loopback以外へ公開しない。`participant / host / receipt / cancel / payments / connect` の確認入口がある。
本番サイトには存在しない検証専用のユーザー切替。通常アプリからはインポートしない。
通知ワーカーは起動しない。終了時に一時DBを破棄する。

## 6. Stripeテスト接続の設定（今回未実施）

テスト用Stripe認証情報がないため、Stripe Dashboardでの作成・接続は未実施。
本番鍵を代用しない。以下は担当者が安全な環境変数設定画面で設定する。チャット・Gitへ貼らない。
`.env.example` は項目一覧であり、アプリは `.env` を自動ロードしない。

| 環境変数 | 内容 |
|---|---|
| CIRCLEMATCH_ONLINE_PAYMENTS_ENABLED | デフォルトfalse。新規受付だけ制御 |
| CIRCLEMATCH_STRIPE_MODE | test / live、デフォルトtest |
| CIRCLEMATCH_STRIPE_SECRET_KEY | 対応モードのサーバー秘密鍵 |
| CIRCLEMATCH_STRIPE_PLATFORM_ACCOUNT | 接続すべき日本のacct_ ID |
| CIRCLEMATCH_STRIPE_WEBHOOK_SECRET | プラットフォーム用Webhook署名鍵 |
| CIRCLEMATCH_STRIPE_CONNECT_WEBHOOK_SECRET | Connect用Webhook署名鍵（別エンドポイント） |
| CIRCLEMATCH_STRIPE_LIVE_APPROVED | デフォルトfalse。本番は別途承認後のみtrue |
| CIRCLEMATCH_SITE_BASE_URL | テストサイトの正規URL、本番はhttps必須 |
| CIRCLEMATCH_SESSION_SECRET | 既存の推測不可能なサーバー秘密値を維持 |
| CIRCLEMATCH_ADMIN_PASSWORD | 既存の運営管理用認証。空なら決済管理拒否 |

1. 専用テスト環境・独立DB・テストユーザーを作成。StripeのテストモードでConnect設定を確認。
2. APIキーとプラットフォームIDが同じテスト環境であることを確認。
3. 下記2種類のWebhookを設定。APIバージョンはコードと合わせる。
4. 主催者の「売上の受取設定」からテスト用hosted onboardingへ進む。
5. 本物の個人情報ではなくStripe公式のテスト情報で完了し、APIの能力・状態を確認。
6. 先着・承認・開催案内ありなし・グループ・チームでテストカード決済。3D Secure、拒否、期限切れも確認。
7. ブラウザを閉じてもWebhookで反映、全額返金と費用・分配取消、再起動・送信失敗を照合する。
8. 実際のカード・実イベント・本番宛先では試さない。

## 7. Webhook、監視、再処理

プラットフォーム側: `POST /api/payments/webhook`

```text
checkout.session.completed
checkout.session.expired
payment_intent.succeeded
payment_intent.payment_failed
charge.refunded
refund.created
refund.updated
refund.failed
application_fee.refunded
charge.dispute.created
charge.dispute.updated
charge.dispute.closed
```

連結アカウント側: `POST /api/payments/connect-webhook`

```text
account.updated
payout.failed
```

署名鍵は別々。プラットフォーム決済にconnected accountの通知を混ぜない。
未知の連結口座、test/liveの混同、改変bodyは拒否する。最大body 256KiB、署名許容300秒。
Webhook以外のAPIはログイン・所有関係・Origin・セッションHMAC CSRF・1ユーザー毎分15操作制限を維持。

通常起動の既存Outboxワーカーが決済処理も実行する。1回にWebhook1件・返金1件・定期照合最大3件。
API障害時は処理が遅れる。SQLite1インスタンス向けで、外部キューや高負荷時の横展開は未対応。
Webhook失敗はバックオフして最大10回、以後はfailed。運営画面 `/admin/payments` に表示。
Stripe側の配信成功(200)とアプリ側処理完了(done)の両方を監視する。
未処理の滞留、needs_review、返金失敗、Outbox未送信、残高不足を毎日確認し、通知監視を本番前に構築する。

運営画面から失敗Webhookを再処理できる。CLIは既存DBを明示し、通常はテストモードのみ許可する。

```powershell
python scripts/payment_operations.py --database C:\test\circlematch.sqlite --actor operator status
python scripts/payment_operations.py --database C:\test\circlematch.sqlite --actor operator reconcile po_ORDER
python scripts/payment_operations.py --database C:\test\circlematch.sqlite --actor operator replay evt_EVENT
python scripts/payment_operations.py --database C:\test\circlematch.sqlite --actor operator tick
python scripts/payment_operations.py --database C:\test\circlematch.sqlite --actor operator recover-order po_ORDER cs_test_SESSION
python scripts/payment_operations.py --database C:\test\circlematch.sqlite --actor operator recover-account USER_ID acct_ACCOUNT
```

`tick` は予約済み返金を実行し得る。コマンド実行前にモード・DB・対象を確認する。
CLIはメール送信を開始しない。本番での操作には別途明示承認、live設定、`--allow-live`が必要。
復旧コマンドは既存のStripeオブジェクトを照合して紐付けるだけで、新しい決済・口座を作らない。
口座復旧は作成冪等キーmetadataとJP設定を照合。注文復旧は注文ID・金額・modeを照合し、
支払済みならさらにIntent・Charge・手数料・受取人を確認する。証跡はpayment_auditに残す。
作成結果不明時に冪等キーを消したり、新規注文を手作業で作らない。

## 8. 返金・紛争・銀行入金の運用

主催者都合の中止は確認画面に未返金総額・対象件数を表示し、中止保存と同時に全額返金ジョブを作成。
API呼出をHTTP中止リクエスト内で大量実行しない。
参加者都合は本人が理由を添えて申請し、注文の主催者または運営が条件を確認して承認する。
既存のキャンセル条件を上書きしない。採用する本番規約の承認は未完了。

返金APIは `reverse_transfer=true` と `refund_application_fee=true`。
同一注文は同じ返金キーを使い、参加者返金と手数料取消と分配取消が揃うまで完了にしない。
処理中・失敗・要確認を区別し、返金時に戻らない決済費用は運営費用として残す。
不足分を参加者や主催者へ自動請求しない。

- failed: Stripe RefundとCharge、Transfer、ApplicationFeeの実績を確認。残高移動済みでも返金完了にはしない。
- retry: 一時障害。永続キーで再試行。同じ注文を別キーで返金しない。
- review / 部分返金: 自動全額返金を停止。Stripe Dashboardと注文履歴を運営が照合。
- 展開された返金一覧に続きがある場合も全額完了とは判定せず要確認とする。多件数の外部部分返金は運営で全履歴を照合する。
- 作成不明が23時間超: 新しい返金を作らずStripeの返金履歴を調査。既存結果はCharge照合で復旧可能。
- dispute: 通常返金を停止。Stripe Dashboardから証拠・期限・争議費用を確認。アプリで証拠提出はしない。
- payout.failed: 主催者に通知。銀行入金の失敗であり、参加者未払いへ戻さない。主催者のStripe受取設定を修正する。

返金却下UI・部分返金UI・グループ内個別精算・銀行振込実行・入金スケジュール制御は対象外。
返金失敗・紛争の手動復旧は運営対応。争議終了後の追加返金も自動再開せず判断する。
二重課金を防ぐため、支払履歴がある同じ申込の人数変更・再申込は全額返金後も自動では許可しない。
再参加や注文の組み直しは運営へ相談する運用とする。

## 9. DB、停止、ロールバック

追加テーブル: payment_accounts / payment_orders / payment_attempts / payment_refunds /
payment_webhooks / payment_audit / payment_rate_limits。
event_postsへonline_pricing_mode、online_price_inputとonline支払方法を追加する。

既存init_dbの後段に再実行可能な移行を追加。SQLite backup APIで
`*.pre-online-payments-<timestamp>.sqlite` を先に作成し、CHECK制約変更を単一トランザクションで行う。
既存ID、列、インデックス、トリガーをコピーし、foreign_key_checkとintegrity_checkを実行。
失敗時はロールバック。バックアップは個人情報を含むため非公開・アクセス制限・保管期限を設定する。
移行テストは一時DBのみ。本番DBは触っていない。

安全な導入順:
1. 本番とは独立したテスト環境で本移行・実Stripeテスト・既存機能の確認を完了。
2. 最新コードと未コミット変更を保全し、担当者が本番反映を別途承認する。
3. 本番の整合バックアップと復旧訓練を行う。必要な空きディスク容量を確認。
4. 最初はフラグOFFで移行する。旧アプリでonlineデータを編集しない。
5. 契約・費用・表示・監視・Webhookを確認後、限定した主催者で有効化。

停止は `CIRCLEMATCH_ONLINE_PAYMENTS_ENABLED=false`。Webhook鍵やワーカーは残す。
既存の照合・返金は継続する。OFF直前に発行済みのCheckout URLはStripeが失効するまで有効になり得るため、
緊急停止時は注文画面の終了操作とStripe上で全未払いSessionの終了を確認する。
サーバー停止だけで予約枠を解放しない。再起動後はlease期限経過後に処理再開。

コードを戻す必要がある場合も、決済テーブルや履歴を削除しない。稼働中DBへ古いバックアップを上書きしない。
決済対応版の照合・Webhook・返金処理を残した修正版へ切り替える。
バックアップからの復元は別ファイル・停止した隔離環境で検証し、決済会社の履歴との差分を精算してから判断する。

## 10. 本番前チェック（すべて未承認）

- [ ] Stripeプラットフォームの利用承認、業務内容、JP/JPY、Connect controller設定
- [ ] 主催者の本人確認・card_payments/transfers・入金能力・制限通知
- [ ] イベント提供者、決済上の事業者、カード明細・サポート連絡先の整合
- [ ] 利用規約、総額10%内包の説明、キャンセル・中止・返金条件
- [ ] 必要な事業者表示。住所・登録番号を架空値で埋めない
- [ ] 利用料の税務、消費税・適格請求書・主催者売上との区分
- [ ] 決済費、Connect月額・入金費、返金費、紛争費用を運営が負担する採算
- [ ] Stripeの銀行入金スケジュール、主催者へ通知する説明
- [ ] 返金原資、マイナス残高・失敗時の担当者、緊急連絡体制
- [ ] 本番用の独立DB・キー・2種類のWebhook・監視・秘密値保管
- [ ] アプリ処理滞留とメール未送信を検知する外部監視
- [ ] 本物の情報を使わないStripeテスト、3D Secure、拒否、口座制限、返金・争議の試験
- [ ] バックアップと復旧訓練、明示的なデプロイ・本番有効化承認

## 11. 参照した公式資料

確認日: 2026-10-04。契約・法務・税務の確認完了を意味しない。

- [Stripe Python v16.0.0](https://github.com/stripe/stripe-python/releases/tag/v16.0.0)
- [固定APIバージョン](https://github.com/stripe/stripe-python/blob/v16.0.0/stripe/_api_version.py)
- [Destination charges](https://docs.stripe.com/connect/destination-charges?platform=web&ui=stripe-hosted)
- [Hosted onboarding](https://docs.stripe.com/connect/hosted-onboarding)
- [Checkout fulfillment](https://docs.stripe.com/checkout/fulfillment)
- [Webhooks](https://docs.stripe.com/webhooks)
- [Refunds](https://docs.stripe.com/refunds)
- [Refund objectの状態](https://docs.stripe.com/api/refunds/object)
- [Charge objectの返金一覧](https://docs.stripe.com/api/charges/object)
- [通貨・最小最大金額](https://docs.stripe.com/currencies)
- [Checkout Session作成・有効期限](https://docs.stripe.com/api/checkout/sessions/create)
- [Connect日本料金](https://stripe.com/jp/connect/pricing)
