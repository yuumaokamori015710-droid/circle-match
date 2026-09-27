# 大会・イベント機能のデータ移行と復旧

## 変更内容

この変更は既存の `circles`、`match_posts`、団体紹介、CSVシードを削除・置換しません。起動時にSQLiteへ次のテーブルとインデックスを**追加**します。

- `event_posts`: 大会・イベントの下書き、公開、締切、中止状態
- `event_applications`: 個人・チームの参加申込と受付状態
- `event_notifications`: アプリ内通知とメール通知状態
- `event_messages`: 主催者と参加者の連絡

既存の `match_posts` は旧来のサークル交流募集としてそのまま残ります。新機能では利用しません。

## 本番反映前のバックアップ

Renderの永続ディスク上のSQLiteは `CIRCLEMATCH_DB_PATH`（本番では `/var/data/circlematch.sqlite`）です。デプロイ前にRenderのディスクスナップショット機能を利用するか、Render Shellで次を実行してダンプを保管します。

```sh
python -c "import sqlite3; c=sqlite3.connect('/var/data/circlematch.sqlite'); open('/var/data/circlematch-pre-events.sql','w',encoding='utf-8').write('\\n'.join(c.iterdump()))"
```

アプリは不足テーブルを `create table if not exists` で作成するため、通常の起動では既存データを書き換えません。

## 復旧

イベント機能の追加後に問題があった場合は、まず前の正常なGitコミットをRenderで再デプロイします。データをデプロイ前の状態へ戻す必要がある場合だけ、保存済みダンプを別ファイルへ復元してから、`CIRCLEMATCH_DB_PATH` を切り替えます。稼働中の `/var/data/circlematch.sqlite` を削除・上書きして復元しないでください。

## 口座振込への対応（2026-09-27）

旧 `event_posts.payment_method` のCHECK制約を、`free` / `on_site` / `bank_transfer` へ拡張します。既存DBでは起動時に一度だけ、SQLiteのバックアップAPIでDBと同じディレクトリに `circlematch.sqlite.pre-bank-transfer-日時.sqlite` を作成し、その後トランザクション内でテーブルを再構築します。募集ID・全列・インデックス・トリガーを保持し、募集・申込・通知・メッセージの外部キーを検査します。失敗時はロールバックし、起動ログへ例外を出します。

復旧が必要な場合は上記バックアップを別の作業用DBへ複製し、`CIRCLEMATCH_DB_PATH` を切り替えてください。バックアップ以降の申込等を失わないよう、現行DBも必ず保管します。

振込はアプリ内決済ではありません。参加確定後、主催者がアプリ内メッセージで振込先・期限を案内し、入金を確認します。口座番号を公開一覧へ追加したり、入金済みと自動判定したりはしません。

終了日時は新規フォームには表示しません。既存の終了日時データは保持し、既存募集の編集でも消去しません。

## メール通知

メールログインはSupabaseのMagic Linkを利用します。専用プロジェクトのカスタムSMTPと許可リダイレクトURLを設定し、実送信を確認した後で `CIRCLEMATCH_EMAIL_AUTH_ENABLED=true` を設定します。未設定時は送信フォームを無効化します。Supabaseの標準メール送信はプロジェクトメンバー宛てのテスト用途であり、一般利用者向けに有効化しないでください。

Googleログインは同じ専用SupabaseのGoogleプロバイダーを使用します。RenderにはプロジェクトURL、公開用キー、独立したセッション秘密鍵を設定します。Service Role KeyやGoogleのクライアント秘密鍵はブラウザへ渡しません。認証後は許可した自サイト内の `return_to` へ戻し、応募画面・応募APIの両方でログインを要求します。

現時点のRender設定にはメール送信プロバイダがありません。そのため通知はアプリ内へ保存され、`email_status` は `not_configured` です。画面上でメールを「送信済み」とは表示しません。メール基盤を追加する場合は、送信成功時だけ `sent`、失敗時は `failed` とエラー内容を記録する実装を追加してください。
