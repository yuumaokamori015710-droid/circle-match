# 運営操作とアクセス確認

## 徴収設定はRender専用

2026-11-04の本人指示により、サイト上の主催者利用料の徴収スイッチを撤去した。
旧画面 `/admin/payments/host-fees` と旧更新API `/api/payments/admin/host-fees/campaign` は、
一般会員・匿名・管理者のいずれでもGET/POSTが404になる。管理一覧へのリンクもない。
他の運営画面は従来のBasic認証で保護し、一般会員のログインだけでは入れない。
ブラウザに保持されたBasic認証は会員アカウントとは別のため、会員を切り替えるだけの確認はしない。

切替は既存Renderサービス `circle-match` のShellから行う。Renderへのアクセス権限が必要。
サービス・プラン・環境変数・Stripeキー・DBスキーマの変更は不要。
コマンドは既存のDBだけを開き、初期化・テーブル作成・マイグレーションを実行しない。

```sh
python scripts/manage_host_fee_campaign.py status
```

通常は `enabled: false` (OFF)。`revision` を確認してから変更する。
以下の `N` は現在の改訂番号に置き換える。古い番号のままでは変更できない。

```sh
python scripts/manage_host_fee_campaign.py off --expected-revision N --actor operator-label
```

ONにするのは本人が徴収開始を明示的に決めたときだけ。
次のコマンドは新規公開分への徴収を開始するので、確認用途では実行しない。

```sh
python scripts/manage_host_fee_campaign.py on --expected-revision N --confirm-new-events-only --actor operator-label
```

- ON対象は切替後に初回公開し、主催者が条件に同意した大会だけ。既存大会・OFF中の公開分・今回の駒沢大会の永続免除を維持する。
- 入金確認済み売上の10%と開催確定条件は変えない。参加者の振込・現地払い・料金・受付やConnect受付を変更しない。
- ON前に既存Stripe設定とアカウントを読み取り照合する。ON操作だけでは注文・請求・送金を作らず、主催者の同意を代理登録しない。
- OFFは未完了Checkoutを終了・照合する。`stopping: true` なら終了・照合待ちであり、ONには戻せない。バックグラウンドとWebhookの照合は続ける。
- 終了コード0は確認/操作完了、2は入力・設定・接続エラー、3は停止・照合待ちまたは不正な保存状態。結果不明を新しい請求で置き換えない。
- 設定変更は既存 `audit_logs` に `host_fee_campaign_change` / `source: render_shell` として記録する。`actor` は操作メモであり認証の代わりではない。操作権限はRenderで管理する。
- `status` は読み取り専用。APIキー・パスワード・Cookieを表示しない。

## 反映ごとの自動検証

GitHub Actionsの `Admin Access Verification` はmainへのpushごとと手動実行に対応する。
Renderのデプロイや料金設定を変更する処理、管理者/Stripeの秘密情報は持たせない。

1. 一時DBと実際のHTTPハンドラを使い、匿名・有効な一般会員2アカウントそれぞれで運営画面/APIが拒否されることを確認する。
2. 管理者認証が有効なこと、会員セッションがあってもBasic認証を代替できないこと、既存決済管理のCSRF保護を検証する。
3. 廃止した徴収画面/APIが管理者にも404を返し、状態が変わらないことを確認する。
4. `/healthz` の公開コミット番号が対象コミットになるまで最大15分待つ。旧バージョンに対する確認を本番反映済みと扱わない。
5. Cookie・Basic認証を持たない新しいHTTP接続で、本番の運営12ルートが401、旧徴収画面/APIのGET/POSTが404になることを確認する。申込・請求・データ更新は送らない。

一般会員の有効セッションでの検証は一時DBで行い、本番の実利用者を借用・代理ログインしない。
本番チェックの結果と一般会員の統合テスト結果は混同せず、Actionsのステップに分けて表示する。
本番のHTTP結果はSummaryと `admin-access-<commit>` のJSON成果物に30日保存する。
成果物にレスポンス本文・メール・Cookie・Authorization・パスワードを含めない。
テスト失敗や対象コミット未反映は失敗として残し、自動で徴収ON・再デプロイ・ロールバックはしない。
短時間に新しいmainが来た場合は古い確認をキャンセルし、最新mainの確認を優先する。

ローカルの確認:

```sh
python -m unittest discover -s scripts -p test_admin_access.py -v
python -m unittest discover -s scripts -p test_fee_campaign.py -v
python scripts/check_admin_access.py --expected-commit COMMIT --report work/admin-access-report.json
```

Renderから手動再デプロイした場合も、同じコミットを対象にActionsの手動実行または最後のコマンドで再確認する。
環境変数だけを変えた再デプロイはGitHub pushでは検知しないため、この手動確認を省略しない。
