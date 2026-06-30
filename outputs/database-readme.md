# Circle Match 実DB版

## 起動

```powershell
python outputs\circlematch_db_app.py
```

起動後、ブラウザで以下を開く。

```text
http://127.0.0.1:8787
```

## DBファイル

```text
outputs/circlematch.sqlite
```

ブラウザの `localStorage` ではなく、SQLiteファイルに保存される。

## 入っている主なテーブル

- `prefectures`: 47都道府県
- `universities`: 大学マスタ
- `circles`: 公開サークルマスタ。団体名、競技、出典、検証状態など公開可能な事実だけ
- `circle_private_profiles`: 非公開サークル補足。SNS管理URL、内部メモ、同意状態など公開APIに返さない情報
- `circle_claims`: 非公開代表者申請。氏名、大学メール、認証状態など公開APIに返さない情報
- `match_posts`: 募集投稿
- `data_sources`: 出典管理
- `audit_logs`: 更新履歴
- `collection_targets`: 大学ごとの収集ステータス
- `circle_candidates`: 自動収集・手動調査で見つけた未公開候補
- `collection_runs`: 収集実行ログ

## 初期データ

- 都道府県: 47件
- 大学: 主要大学123件から拡張中
- サークル: 1,116件。大学公式ページ、競技連盟ページなどの実出典つきデータを投入中
- 検証済み/申請済みサークル: 1,115件
- 候補: 競技連盟・公開情報から見つけた未確認候補をレビュー前提で投入中

サークルデータは、他サイトの丸コピーを避ける。実データは大学公式ページ、競技連盟ページ、団体本人の自己登録、公開SNS、手動確認済み出典からCSVまたは管理画面で追加する。

## CSV取込

テンプレート:

```text
outputs/circle_import_template.csv
```

列:

```text
university_name,circle_name,sport_category,activity_area,source_type,source_url,verification_status
```

`source_type` は以下のいずれか。

```text
university_official
self_registered
public_sns
other
```

`verification_status` は以下のいずれか。

```text
unverified
claimed
university_verified
admin_verified
```

## API

```text
GET  /api/summary
GET  /api/universities
POST /api/universities
GET  /api/circles
POST /api/circles
GET  /api/candidates
GET  /api/admin_metrics
GET  /api/privacy_metrics
GET  /api/matches
POST /api/matches
GET  /api/audit_logs
POST /api/import/circles_csv
POST /api/import/candidates_csv
POST /api/candidates/promote
POST /api/candidates/reject
```

## 方針

全国サークルDBとして拡張できる構造にしている。既存サイトの紹介文、画像、レビュー、ランキング等は保存しない。出典URL・検証ステータス・更新履歴を必ず残す。

## プライバシー分離

公開検索API `GET /api/circles` は、`circles` の公開列だけを返す。代表者氏名、大学メール、内部メモ、個別連絡先、非公開SNS管理情報は返さない。

個人情報・内部情報は以下に分離する。

- `circle_private_profiles`: 団体に紐づく非公開補足。内部メモ、同意状態、管理用SNS URL
- `circle_claims`: 代表者申請。 claimant_name、claimant_email、大学メール認証状態、審査状態

監査ログは、メール、氏名、内部メモ、SNS URL、認証トークン等のセンシティブ項目を伏せ字化して保存する。

## プロダクト設計メモ

### ユーザーと権限

- 閲覧者: ログイン不要でサークル一覧、公開募集一覧を閲覧できる
- 通常ログインユーザー: 応募、メッセージ、修正提案ができる
- 大学メール認証済みユーザー: 大学所属の信頼度を中として扱う
- サークル代表者: 大学メール認証と運営手動承認を通過したユーザーだけに付与する

Googleログインだけでは、大学所属やサークル代表者であることを確認できないため、代表者権限には使わない。

### 公開範囲

- サークルページ: 正式確認済みサークルだけGoogle検索対象にする
- 候補データ: 管理画面だけに表示する
- 募集一覧: 公開する
- 募集詳細、応募、メッセージ: ログイン後に表示する

### DB更新

- 代表者は自分のサークル情報を更新できる
- 通常ログインユーザーは修正提案を送れる
- 運営は修正提案の承認、怪しい更新の監査、掲載停止を行う
- 重要項目の変更は履歴を保存し、必要に応じて再承認する

### DB収集ゴール

- Phase 1: 主要100大学 x 主要競技
- Phase 2: 全国大学 x 公認団体中心
- Phase 3: 全国大学 x 公認/非公認候補まで

当面の実装優先度はDB作りを最優先にする。マッチング機能は、DBが使われ始めてからブラッシュアップしてリリースする。

### 管理画面の段階

現在の優先は `DB作業特化`。

- 収集状況
- 候補レビュー
- 出典確認
- 修正提案
- CSV取込
- 大学別、競技別、検証ステータス別、出典タイプ別の管理指標

DB作業特化が終わったら、次に `サービス運営全体` へ広げる。

- ユーザー承認
- 代表者承認
- 募集承認
- 通報
- メッセージ監査

### マッチング機能の将来方針

- 募集投稿は代表者認証済みサークルだけ可能にする
- 初回投稿だけ運営承認、2回目以降は即公開にする
- マッチ成立条件は、募集主が応募を承認した時点にする
- 応募フォームは、人数、レベル、希望時間帯、場所対応、ユニフォーム色、審判/施設対応など試合調整に必要な情報まで入力する
- マッチ成立後の評価は公開レビューにせず、運営への非公開フィードバックだけにする
