# GitHub公開手順

## 公開前に確認すること

1. `python scripts/check_publish_safety.py` が成功すること
2. `.env` が存在してもGitHub対象外であること
3. `outputs/circlematch.sqlite` がGitHub対象外であること
4. `work/*.log` と `work/*.pdf` がGitHub対象外であること
5. `CIRCLEMATCH_CONTACT_EMAIL` を本番環境変数で実連絡先にすること

## 初回Git化

```powershell
git init
git status --short
git add .gitignore .env.example README.md Procfile requirements.txt outputs scripts docs work
git status --short
```

`git status --short` に以下が出ていないことを確認する。

```text
outputs/circlematch.sqlite
work/*.log
work/*.pdf
.env
```

問題なければコミットする。

```powershell
git commit -m "Prepare Circle Match for safe GitHub publishing"
```

## GitHubリポジトリ作成後

```powershell
git remote add origin <GitHub repository URL>
git branch -M main
git push -u origin main
```

## GitHubに置くもの

- アプリコード
- スキーマ
- 収集スクリプト
- 公開用CSVテンプレート
- 法務・プライバシー関連ドキュメント
- 本番公開前チェックリスト

## GitHubに置かないもの

- SQLite DB本体
- `.env`
- APIキー
- 代表者氏名、大学メール、問い合わせ本文
- ログ
- PDFなどの収集元ファイル

