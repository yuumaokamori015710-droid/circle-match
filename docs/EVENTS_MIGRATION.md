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

## メール通知

現時点のRender設定にはメール送信プロバイダがありません。そのため通知はアプリ内へ保存され、`email_status` は `not_configured` です。画面上でメールを「送信済み」とは表示しません。メール基盤を追加する場合は、送信成功時だけ `sent`、失敗時は `failed` とエラー内容を記録する実装を追加してください。
