# オンライン決済の検証結果

初回検証日: 2026-10-04。以下の画面操作・FakeStripe試験はこの日に実施。
追加検証日: 2026-10-15。最新mainへ統合したコードで全305テスト成功（31件スキップ）。
既存SQLiteのコピーで移行・再起動・integrity_checkを確認し、移行前からの外部キー違反4件を増やしていない。
実Stripeのカード決済・送金・返金は未実施。本番決済フラグは有効にしていない。

## 環境と範囲

- 既存Python HTTPServer / SQLite構成を維持。
- `TemporaryDirectory`内の隔離SQLiteに仮ユーザー・仮イベントを作成。
- 実DBをテスト用データで置換しない。既存のseed CSVの未コミット変更も保持。
- 決済業務テストはFakeStripe。SDK検証は公式stripe==16.0.0とインメモリHTTP transport。
- 実Stripeへの通信、実カード、本番通知先への送信は行っていない。
- 起動時の既存DB変更、CHECK制約変更、外部キー、バックアップ、失敗時rollbackは隔離DBで確認。

## 自動テスト

| 実行内容 | 結果 |
|---|---|
| `python -m unittest discover -s scripts -p test_online_payments.py` | 40件成功 |
| `python -m unittest discover -s scripts -p test_payment_sdk.py` | 3件成功 |
| `python -m unittest discover -s scripts -p 'test_event*.py'` | 62件成功 |
| `python -m unittest discover -s scripts -p test_account_navigation.py` | 3件成功 |
| `python scripts/test_event_flow.py` | `event flow: ok` |
| `node scripts/test_signin.cjs` | `signin flow: ok` |
| 決済本体・SSR UI・既存アプリ・検証/運用スクリプトの`py_compile` | 成功 |
| `python scripts/payment_operations.py --help` | 成功 |
| `git diff --check` | エラーなし。既存の改行設定によるCRLF警告のみ |

上表は10月4日の個別試験結果。10月15日の統合後は全305テスト成功（31件スキップ）。
既存メール試験のHTTPErrorモックのcleanup警告は残るが失敗はない。

### 確認した重要ケース

- 2,000円から手数料200円・主催者1,800円。受取希望1,800円から2,000円。
- 受取希望2,000円から2,223円・手数料223円。3人合計と注文総額での端数計算。
- チーム内人数を料金に乗算しない。無料はSessionなし。負数・小数・最低額未満・上限超過を拒否。
- 金額・通貨・手数料・送金先・modeの改変、古い確認画面、他人の注文を拒否。
- 先着・承認待ち・開催案内・最終参加確認・定員競合・支払期限。
- 決済中の人数変更・取消・枠解放を停止し、Stripe終了確認後に許可。
- 連打・複数スレッド・タイムアウト・再起動・保存失敗から同じ注文を復旧。
- 作成結果不明が23時間を超えた場合の新規作成禁止と、既存Session/口座の運営復旧。
- 成功URLのGETでは支払済みにしない。支払後にブラウザが戻らなくてもWebhookで反映。
- Webhook重複・順序逆転・署名不正・別mode・Connect通知混入・DB保存失敗。
- 全額返金、利用料返金、分配取消、重複防止、タイムアウト再開、失敗、外部部分返金、紛争。
- Chargeの合計が全額でもRefundがpendingなら返金完了にしない。
- Refundがrequires_action、または返金一覧に続きがある場合は運営要確認。
- 銀行入金失敗を主催者へ通知し、参加者の支払確認済み状態は維持。
- フラグOFF後も既存決済照合・Webhook・返金を継続。
- 無料・現地払い・口座振込の既存イベントと、ログイン・参加・主催導線。

## 画面操作

`scripts/preview_online_payments.py`をloopbackで起動し、実際のSSR画面とAPIをブラウザ操作した。
このプレビューは検証専用の仮ログインであり、Supabaseの実ログイン試験ではない。

1. 参加者: 2,000円×3人、支払総額6,000円、主催者・日時・会場・条件を確認。
2. 主催者: 受取希望2,000円を入力し、参加費2,223円・手数料223円への即時更新を確認。
3. 主催者: 参加者支払額からの入力方式でも2,000円・200円・1,800円を確認。
4. 公開前プレビューから隔離DBへ保存。詳細ページに参加費2,223円と利用料込みの補足が表示。
5. 参加者: 支払確認済みのモック注文で返金を申請。「返金申請中・確認した返金額0円」を確認。
6. 主催者: 未払い1件・支払済み1件、取扱高2,000円・利用料200円・分配見込1,800円を確認。
7. 受取設定: モックAPIで利用状態を再確認。銀行への入金と残高分配を区別した説明を確認。
8. 主催者: 中止前に1件・2,000円を確認して処理を予約。「返金処理中」で止まり、完了を誤表示しない。
9. 処理中の注文で重複申請ボタンが表示されないことを確認。

幅1440pxのPC、390px・320pxのスマホで確認。
横方向のdocument overflowはなく、総額・数量・条件・48px以上の支払ボタンが収まっている。
最新のブラウザコンソールにerror/warnなし。画像は既存ロゴ等をそのまま使用。
Stripe hosted Checkout・hosted onboarding自体の実画面は未確認。

画像証跡はローカルの`work/online-payments-verification/`に保存:

- [参加者PC](../work/online-payments-verification/participant-desktop.jpg)
- [参加者390px](../work/online-payments-verification/participant-390.jpg)
- [参加者390px・総額と支払ボタン](../work/online-payments-verification/participant-390-payment.jpg)
- [参加者320px](../work/online-payments-verification/participant-320.jpg)
- [主催者料金PC](../work/online-payments-verification/host-pricing-desktop.jpg)
- [主催者料金390px](../work/online-payments-verification/host-pricing-390.jpg)
- [保存後のイベント](../work/online-payments-verification/event-saved-390.jpg)
- [主催者集計](../work/online-payments-verification/organizer-totals-desktop.jpg)
- [受取設定](../work/online-payments-verification/connect-desktop.jpg)
- [開催中止確認](../work/online-payments-verification/cancel-390.jpg)
- [返金処理中](../work/online-payments-verification/refund-processing-390.jpg)

## 未実施・残る制約

- テスト用Stripeキー・Webhook署名鍵・プラットフォーム設定がないため、実Stripeテストは未実施。
- 実Connect本人確認、実テストカード、3D Secure/拒否、実Webhook配信、Stripe残高照合は未実施。
- 実メール配送、本番移行、本番インフラの高負荷・フェイルオーバー試験は未実施。
- 法務・税務・Stripe利用承認、Connect/入金費用、実銀行入金日程は未確認。10%内での採算も別途確認が必要。
- 1チームの申込を1注文として扱う。1申込で複数チームを同時に買う機能はない。
- 部分返金UI、返金却下UI、争議証拠提出、返金失敗の自動再実行は対象外。運営対応が必要。
- 支払履歴がある同じ申込の人数変更・再申込は、全額返金後も自動では許可しない。
- 注文一覧は最新200件、未処理Webhook一覧は100件。ページ送りや高度な会計帳票は未実装。
- SQLite単一インスタンスと既存Outboxワーカーの処理量が前提。滞留監視と実負荷評価が必要。

手順・必要な環境変数・再処理・停止・復旧・承認チェックリストは
[ONLINE_PAYMENTS.md](ONLINE_PAYMENTS.md)を参照。
