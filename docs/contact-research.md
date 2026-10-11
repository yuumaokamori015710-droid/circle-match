# サークルの公開連絡先調査

調査結果は管理者専用 `/admin/contact-research` に保存する。公開プロフィール・公開API・公開seedへメールを追加しない。公開情報の取得は、送信、配信同意、本人確認を意味しない。

`scripts/research_circle_contacts.py --directory <private-directory>` は現在の公開サークル一覧を全件スナップショットし、登録出典と団体名で対応するリンクを確認する。同じURLはキャッシュし、robots.txt、ホスト別のアクセス間隔、HTTP失敗を記録する。ログイン必須のSNS、非公開サイト、別団体のプロフィール、大学・掲載サイトの共通窓口は自動採用しない。メールは団体名を含む限定的な文脈で確認し、同じメールが複数団体に出現した場合は要確認へ戻す。

出力ディレクトリはGit管理外に置く。`results.jsonl` は再開用、`pages.sqlite` は取得キャッシュ、`results.json` は管理者専用取り込み用、`contacts.csv` は全件の状態、`progress.json` は集計を保持する。実行中のPCを終了すると処理は止まるが、同じコマンドで保存済みから再開できる。

状態はメール確認、確認範囲で未発見、問い合わせ先候補、取得できず、参照先なし、要確認に分ける。「未発見」はウェブ全体や非公開情報にも存在しないという意味ではない。出典が古い、画像だけに記載されている、別名称で運営されている場合などは追加調査を要する。アドレスの推測や非公開窓口への侵入は行わない。

取り込み例：

```
python scripts/import_contact_research.py --file <private-directory>/results.json --validate-only
python scripts/import_contact_research.py --file <private-directory>/results.json --credentials-file <temporary-admin-connection.json>
```

認証情報は既存Render環境の管理者資格情報を使い、一時ファイルは取り込み後に削除する。新しい資格情報や権限は作成しない。250件ずつ原子的に取り込み、再試行しても重複しない。管理画面・JSON・CSVには既存の管理者認証が必要で、認証設定がなければ503で拒否する。公開検索は従来どおり代表者の明示同意がある連絡先だけを返す。
