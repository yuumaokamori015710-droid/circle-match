# デプロイ方針

## 現段階の推奨

最初の本番検証は、以下のどちらかが扱いやすい。

- Render / Railway / Fly.io などのPaaS
- 小さなVPS

ただし、現在のSQLite構成はプロトタイプ向け。公開サービスとして運用する段階では、PostgreSQLなどの管理DBへ移行する。

## 必須の本番環境変数

```text
HOST=0.0.0.0
PORT=<hosting provider assigned port>
CIRCLEMATCH_SITE_NAME=Circle Match
CIRCLEMATCH_OPERATOR=<real operator name>
CIRCLEMATCH_CONTACT_EMAIL=<real contact email>
CIRCLEMATCH_DB_PATH=<path outside repository or mounted volume>
```

## 初期デプロイ時の注意

- 管理画面を一般公開しない
- `/privacy`, `/terms`, `/about-data`, `/contact` は公開する
- AdSense申請前に独自ドメインとHTTPSを有効にする
- DBファイルをコンテナイメージに含めない
- 本番DBはバックアップ対象にする

## 次に必要な実装

1. 管理画面ログイン
2. 公開ページと管理ページの分離
3. PostgreSQL対応
4. 代表者申請フォーム
5. 問い合わせフォーム、またはメールリンクの本番連絡先化
6. robots.txt と sitemap.xml

