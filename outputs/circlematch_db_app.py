import csv
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("CIRCLEMATCH_DB_PATH", ROOT / "circlematch.sqlite"))
LOG_PATH = ROOT.parent / "work" / "circlematch_db_app.log"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8787"))
SITE_NAME = os.environ.get("CIRCLEMATCH_SITE_NAME", "Circle Match")
SITE_OPERATOR = os.environ.get("CIRCLEMATCH_OPERATOR", "Circle Match 運営")
CONTACT_EMAIL = os.environ.get("CIRCLEMATCH_CONTACT_EMAIL", "contact@example.com")

PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
    "岐阜県", "静岡県", "愛知県", "三重県",
    "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
    "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県",
    "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
]

UNIVERSITY_SEED = [
    ("北海道大学", "北海道", "札幌市", "札幌キャンパス", "https://www.hokudai.ac.jp/"),
    ("弘前大学", "青森県", "弘前市", "", "https://www.hirosaki-u.ac.jp/"),
    ("岩手大学", "岩手県", "盛岡市", "", "https://www.iwate-u.ac.jp/"),
    ("東北大学", "宮城県", "仙台市", "", "https://www.tohoku.ac.jp/"),
    ("秋田大学", "秋田県", "秋田市", "", "https://www.akita-u.ac.jp/"),
    ("山形大学", "山形県", "山形市", "", "https://www.yamagata-u.ac.jp/"),
    ("福島大学", "福島県", "福島市", "", "https://www.fukushima-u.ac.jp/"),
    ("筑波大学", "茨城県", "つくば市", "", "https://www.tsukuba.ac.jp/"),
    ("宇都宮大学", "栃木県", "宇都宮市", "", "https://www.utsunomiya-u.ac.jp/"),
    ("群馬大学", "群馬県", "前橋市", "", "https://www.gunma-u.ac.jp/"),
    ("埼玉大学", "埼玉県", "さいたま市", "", "https://www.saitama-u.ac.jp/"),
    ("千葉大学", "千葉県", "千葉市", "", "https://www.chiba-u.ac.jp/"),
    ("東京大学", "東京都", "文京区", "本郷キャンパス", "https://www.u-tokyo.ac.jp/"),
    ("早稲田大学", "東京都", "新宿区", "早稲田キャンパス", "https://www.waseda.jp/"),
    ("慶應義塾大学", "東京都", "港区", "三田キャンパス", "https://www.keio.ac.jp/"),
    ("明治大学", "東京都", "千代田区", "駿河台キャンパス", "https://www.meiji.ac.jp/"),
    ("横浜国立大学", "神奈川県", "横浜市", "", "https://www.ynu.ac.jp/"),
    ("新潟大学", "新潟県", "新潟市", "", "https://www.niigata-u.ac.jp/"),
    ("富山大学", "富山県", "富山市", "", "https://www.u-toyama.ac.jp/"),
    ("金沢大学", "石川県", "金沢市", "", "https://www.kanazawa-u.ac.jp/"),
    ("福井大学", "福井県", "福井市", "", "https://www.u-fukui.ac.jp/"),
    ("山梨大学", "山梨県", "甲府市", "", "https://www.yamanashi.ac.jp/"),
    ("信州大学", "長野県", "松本市", "", "https://www.shinshu-u.ac.jp/"),
    ("岐阜大学", "岐阜県", "岐阜市", "", "https://www.gifu-u.ac.jp/"),
    ("静岡大学", "静岡県", "静岡市", "", "https://www.shizuoka.ac.jp/"),
    ("名古屋大学", "愛知県", "名古屋市", "", "https://www.nagoya-u.ac.jp/"),
    ("三重大学", "三重県", "津市", "", "https://www.mie-u.ac.jp/"),
    ("滋賀大学", "滋賀県", "彦根市", "", "https://www.shiga-u.ac.jp/"),
    ("京都大学", "京都府", "京都市", "吉田キャンパス", "https://www.kyoto-u.ac.jp/"),
    ("大阪大学", "大阪府", "吹田市", "", "https://www.osaka-u.ac.jp/"),
    ("神戸大学", "兵庫県", "神戸市", "", "https://www.kobe-u.ac.jp/"),
    ("奈良女子大学", "奈良県", "奈良市", "", "https://www.nara-wu.ac.jp/"),
    ("和歌山大学", "和歌山県", "和歌山市", "", "https://www.wakayama-u.ac.jp/"),
    ("鳥取大学", "鳥取県", "鳥取市", "", "https://www.tottori-u.ac.jp/"),
    ("島根大学", "島根県", "松江市", "", "https://www.shimane-u.ac.jp/"),
    ("岡山大学", "岡山県", "岡山市", "", "https://www.okayama-u.ac.jp/"),
    ("広島大学", "広島県", "東広島市", "", "https://www.hiroshima-u.ac.jp/"),
    ("山口大学", "山口県", "山口市", "", "https://www.yamaguchi-u.ac.jp/"),
    ("徳島大学", "徳島県", "徳島市", "", "https://www.tokushima-u.ac.jp/"),
    ("香川大学", "香川県", "高松市", "", "https://www.kagawa-u.ac.jp/"),
    ("愛媛大学", "愛媛県", "松山市", "", "https://www.ehime-u.ac.jp/"),
    ("高知大学", "高知県", "高知市", "", "https://www.kochi-u.ac.jp/"),
    ("九州大学", "福岡県", "福岡市", "伊都キャンパス", "https://www.kyushu-u.ac.jp/"),
    ("佐賀大学", "佐賀県", "佐賀市", "", "https://www.saga-u.ac.jp/"),
    ("長崎大学", "長崎県", "長崎市", "", "https://www.nagasaki-u.ac.jp/"),
    ("熊本大学", "熊本県", "熊本市", "", "https://www.kumamoto-u.ac.jp/"),
    ("大分大学", "大分県", "大分市", "", "https://www.oita-u.ac.jp/"),
    ("宮崎大学", "宮崎県", "宮崎市", "", "https://www.miyazaki-u.ac.jp/"),
    ("鹿児島大学", "鹿児島県", "鹿児島市", "", "https://www.kagoshima-u.ac.jp/"),
    ("琉球大学", "沖縄県", "中頭郡西原町", "", "https://www.u-ryukyu.ac.jp/")
]

SPORTS = ["サッカー", "フットサル", "バスケットボール", "テニス", "バレーボール", "野球", "バドミントン", "ラグビー", "その他"]
SOURCE_TYPES = ["university_official", "self_registered", "public_sns", "other"]
VERIFICATION_STATUSES = ["unverified", "claimed", "university_verified", "admin_verified"]
ORGANIZATION_TYPES = ["体育会", "部活", "公認サークル", "同好会", "非公認サークル", "学生団体", "不明"]

HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Circle Match DB Admin</title>
  <style>
    :root{--ink:#17212f;--muted:#65758a;--line:#dbe4ed;--paper:#fff;--soft:#f4f7fa;--brand:#0f7a62;--red:#a73520;--blue:#2767a5}
    *{box-sizing:border-box}body{margin:0;background:#eef3f7;color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{position:sticky;top:0;z-index:3;background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1280px;margin:auto;padding:13px 18px;display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap}
    h1{font-size:18px;margin:0}.tabs{display:flex;gap:6px;flex-wrap:wrap}button,input,select,textarea{font:inherit}button{border:1px solid var(--line);border-radius:8px;background:#fff;min-height:38px;padding:8px 11px;font-weight:750;cursor:pointer}
    button.primary{background:var(--brand);border-color:var(--brand);color:#fff}button.danger{color:var(--red);background:#fff5f2;border-color:#efc2b7}.tab.active{background:#e4f3ee;color:#0a5949;border-color:#b8dccf}
    main{max-width:1280px;margin:auto;padding:18px}.site-links{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px}.site-links a{color:var(--blue);font-weight:800;text-decoration:none}.summary{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin-bottom:14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:13px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:800}.metric strong{display:block;margin-top:7px;font-size:25px}
    .view{display:none}.view.active{display:block}.grid{display:grid;grid-template-columns:360px minmax(0,1fr);gap:14px;align-items:start}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.head{padding:14px 15px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}.head h2{font-size:17px;margin:0}.head p{margin:4px 0 0;color:var(--muted);font-size:13px}
    form{padding:15px;display:grid;gap:11px}label{display:grid;gap:6px;color:var(--muted);font-size:12px;font-weight:800}input,select,textarea{width:100%;border:1px solid #c8d4df;border-radius:8px;min-height:39px;padding:9px 10px;background:#fff;color:var(--ink)}textarea{min-height:78px;resize:vertical}.row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
    .filters{display:grid;grid-template-columns:minmax(220px,1fr) 140px 150px 150px 150px;gap:8px;padding:15px;border-bottom:1px solid var(--line)}.tablewrap{overflow:auto;max-height:650px}table{width:100%;border-collapse:collapse;font-size:13px;table-layout:auto}th,td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{position:sticky;top:0;background:#f7fafc;color:var(--muted);font-size:12px}.circle-table{min-width:1080px}.circle-table th:nth-child(1){width:20%}.circle-table th:nth-child(2){width:30%}.circle-table th:nth-child(3){width:13%}.circle-table th:nth-child(4){width:12%}.circle-table th:nth-child(5){width:10%}.circle-table th:nth-child(6){width:9%}.circle-table th:nth-child(7){width:6%}.primary-cell{min-width:300px}.circle-name{display:block;font-size:15px;font-weight:850;line-height:1.35}.subline{display:block;margin-top:4px;color:var(--muted);font-size:12px;line-height:1.35}.uni-name{font-weight:850;white-space:nowrap}.actions{white-space:nowrap}.badge{display:inline-flex;align-items:center;border-radius:999px;background:#edf2f7;color:#405164;min-height:22px;padding:3px 8px;font-size:12px;font-weight:850;white-space:nowrap}.ok{background:#e1f4eb;color:#0b624d}.warn{background:#fff0cf;color:#775000}.blue{background:#e2edf8;color:#20598f}.muted{color:var(--muted)}.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px}.notice{padding:12px 14px;border:1px solid #f0d9ad;background:#fff8ec;color:#6d4b06;border-radius:8px;margin-bottom:14px;line-height:1.6}
    @media(max-width:980px){.summary{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.filters{grid-template-columns:1fr}.row{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <header><div class="top"><h1>Circle Match DB Admin</h1><nav class="tabs"><button class="tab active" data-view="circles">サークル検索</button><button class="tab" data-view="circle-register">サークル登録</button><button class="tab" data-view="collection">収集状況</button><button class="tab" data-view="candidates">候補レビュー</button><button class="tab" data-view="metrics">管理指標</button><button class="tab" data-view="privacy">非公開情報</button><button class="tab" data-view="universities">大学DB</button><button class="tab" data-view="matches">募集DB</button><button class="tab" data-view="imports">CSV取込</button><button class="tab" data-view="logs">更新履歴</button></nav></div></header>
  <main>
    <div class="notice">これはブラウザ保存ではなく、SQLiteファイル <span class="mono">outputs/circlematch.sqlite</span> に保存される実DBです。公開DBと個人情報・内部メモDBを分離し、公開検索APIには個人情報を返しません。</div>
    <nav class="site-links"><a href="/privacy" target="_blank">プライバシーポリシー</a><a href="/terms" target="_blank">利用規約</a><a href="/about-data" target="_blank">掲載情報・削除訂正</a><a href="/contact" target="_blank">問い合わせ</a></nav>
    <section class="summary"><div class="metric"><span>都道府県</span><strong id="prefCount">0</strong></div><div class="metric"><span>大学</span><strong id="uniCount">0</strong></div><div class="metric"><span>サークル</span><strong id="circleCount">0</strong></div><div class="metric"><span>検証済み/申請済み</span><strong id="verifiedCount">0</strong></div><div class="metric"><span>候補</span><strong id="candidateCount">0</strong></div><div class="metric"><span>募集中</span><strong id="matchCount">0</strong></div></section>
    <section id="circles" class="view active"><div class="panel"><div class="head"><div><h2>全国サークル台帳</h2><p>検索・絞り込み・編集対象の確認</p></div><button id="reloadCircles">再読込</button></div><div class="filters"><input id="q" placeholder="大学名・団体名・競技・地域"><select id="prefFilter"><option value="">全都道府県</option></select><select id="orgTypeFilter"><option value="">全種別</option></select><select id="sportFilter"><option value="">全競技</option></select><select id="statusFilter"><option value="">全ステータス</option></select></div><div class="tablewrap"><table class="circle-table"><thead><tr><th>大学</th><th>団体名</th><th>種別</th><th>競技</th><th>ソース</th><th>検証</th><th>操作</th></tr></thead><tbody id="circleRows"></tbody></table></div></div></section>
    <section id="circle-register" class="view"><div class="panel"><div class="head"><div><h2>サークル登録/更新</h2><p>公開DBに載せる事実情報だけを登録します。代表者連絡先や内部メモは非公開DBで扱います。</p></div><button id="clearCircleForm" type="button">新規入力</button></div><form id="circleForm"><label>大学<select id="circleUniversity" required></select></label><label>団体名<input id="circleName" required></label><div class="row"><label>団体種別<select id="organizationType"></select></label><label>競技<select id="sport"></select></label></div><label>活動地域<input id="activityArea"></label><div class="row"><label>出典種別<select id="sourceType"></select></label><label>検証<select id="verificationStatus"></select></label></div><label>出典URL<input id="sourceUrl" type="url"></label><button class="primary">保存</button></form></div></section>
    <section id="collection" class="view"><div class="panel"><div class="head"><div><h2>大学別の収集状況</h2><p>未収集・一部収集済み・公式確認済みを追跡します。</p></div><button id="reloadCollection">再読込</button></div><div class="tablewrap"><table><thead><tr><th>大学</th><th>地域</th><th>登録サークル数</th><th>収集状態</th><th>検索クエリ/出典</th><th>最終確認</th></tr></thead><tbody id="collectionRows"></tbody></table></div></div></section>
    <section id="candidates" class="view"><div class="panel"><div class="head"><div><h2>候補レビュー</h2><p>自動収集・手動調査で見つけた未公開候補。正式DBへの昇格前に出典を確認します。</p></div><button id="reloadCandidates">再読込</button></div><div class="tablewrap"><table><thead><tr><th>ID</th><th>大学</th><th>候補サークル</th><th>競技/状態</th><th>出典</th><th>メモ</th><th>操作</th></tr></thead><tbody id="candidateRows"></tbody></table></div></div></section>
    <section id="metrics" class="view"><div class="grid"><div class="panel"><div class="head"><div><h2>大学別収集率</h2><p>スカスカな大学を優先的に潰します。</p></div></div><div class="tablewrap"><table><thead><tr><th>大学</th><th>地域</th><th>正式</th><th>候補</th></tr></thead><tbody id="metricUniversityRows"></tbody></table></div></div><div class="panel"><div class="head"><div><h2>競技・検証・出典</h2><p>DBの厚みと公開可能性を見ます。</p></div><button id="reloadMetrics">再読込</button></div><div class="tablewrap"><table><thead><tr><th>区分</th><th>項目</th><th>件数</th></tr></thead><tbody id="metricRows"></tbody></table></div></div></div></section>
    <section id="privacy" class="view"><div class="grid"><div class="panel"><div class="head"><div><h2>公開/非公開の分離</h2><p>公開APIに返さない情報の保管状況だけを確認します。</p></div><button id="reloadPrivacy">再読込</button></div><div class="tablewrap"><table><thead><tr><th>区分</th><th>件数</th><th>公開API</th></tr></thead><tbody id="privacyRows"></tbody></table></div></div><div class="panel"><div class="head"><div><h2>個人情報の扱い</h2><p>代表者メール・氏名・内部メモは公開検索と分離します。</p></div></div><div style="padding:15px;line-height:1.7;color:var(--muted)">公開DBは大学名、団体名、競技、出典、検証状態だけを保持します。代表者申請、大学メール認証、内部メモ、連絡先は非公開テーブルに保存し、公開一覧・検索APIには含めません。</div></div></div></section>
    <section id="universities" class="view"><div class="grid"><div class="panel"><div class="head"><div><h2>大学登録</h2><p>全国の大学マスタを拡張</p></div></div><form id="universityForm"><label>大学名<input id="universityName" required></label><div class="row"><label>都道府県<select id="universityPrefecture"></select></label><label>市区町村<input id="city"></label></div><label>キャンパス<input id="campusName"></label><label>公式URL<input id="officialUrl" type="url"></label><button class="primary">保存</button></form></div><div class="panel"><div class="head"><div><h2>大学一覧</h2><p>初期データは47都道府県をカバーする主要大学</p></div></div><div class="tablewrap"><table><thead><tr><th>ID</th><th>大学</th><th>地域</th><th>公式URL</th></tr></thead><tbody id="universityRows"></tbody></table></div></div></div></section>
    <section id="matches" class="view"><div class="grid"><div class="panel"><div class="head"><div><h2>募集登録</h2><p>DB上のサークルに紐づけ</p></div></div><form id="matchForm"><label>サークル<select id="matchCircle" required></select></label><div class="row"><label>種別<select id="matchType"><option>練習試合</option><option>合同練習</option><option>助っ人募集</option><option>大会参加者募集</option></select></label><label>レベル<input id="levelLabel" placeholder="中級、初心者歓迎など"></label></div><label>日時<input id="scheduledAt" type="datetime-local"></label><label>場所<input id="place"></label><label>条件<textarea id="conditions"></textarea></label><button class="primary">保存</button></form></div><div class="panel"><div class="head"><div><h2>募集一覧</h2><p>公開予定の募集データ</p></div></div><div class="tablewrap"><table><thead><tr><th>ID</th><th>サークル</th><th>種別/レベル</th><th>日時/場所</th><th>条件</th></tr></thead><tbody id="matchRows"></tbody></table></div></div></div></section>
    <section id="imports" class="view"><div class="grid"><div class="panel"><div class="head"><div><h2>正式サークルCSV取込</h2><p>公開列: university_name,circle_name,sport_category,activity_area,source_type,source_url,verification_status</p></div></div><form id="importForm"><label>サークルCSV<textarea id="csvText" placeholder="university_name,circle_name,sport_category,activity_area,source_type,source_url,verification_status"></textarea></label><button class="primary">正式DBに取込</button></form></div><div class="panel"><div class="head"><div><h2>候補CSV取込</h2><p>列: university_name,candidate_name,sport_category,source_type,source_url,evidence_text,review_status,notes</p></div></div><form id="candidateImportForm"><label>候補CSV<textarea id="candidateCsvText" placeholder="university_name,candidate_name,sport_category,source_type,source_url,evidence_text,review_status,notes"></textarea></label><button class="primary">候補DBに取込</button></form></div></div></section>
    <section id="logs" class="view"><div class="panel"><div class="head"><div><h2>更新履歴</h2><p>登録・更新・取込の監査ログ</p></div><button id="reloadLogs">再読込</button></div><div class="tablewrap"><table><thead><tr><th>日時</th><th>操作</th><th>対象</th><th>内容</th></tr></thead><tbody id="logRows"></tbody></table></div></div></section>
  </main>
  <script>
    const sports = __SPORTS__;
    const sourceTypes = __SOURCE_TYPES__;
    const statuses = __STATUSES__;
    const organizationTypes = __ORG_TYPES__;
    const prefs = __PREFS__;
    const $ = id => document.getElementById(id);
    async function api(path, options={}) {
      const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    }
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function sourceLabel(v){return ({university_official:"大学公式",self_registered:"本人登録",public_sns:"SNS等",other:"その他"}[v] || v)}
    function statusLabel(v){return ({university_verified:"公式確認済み",admin_verified:"運営確認済み",claimed:"申請済み",unverified:"未確認"}[v] || v)}
    function orgTypeLabel(v){return v || "不明"}
    function badgeSource(v){const cls = v === "university_official" ? "ok" : v === "self_registered" ? "warn" : v === "public_sns" ? "blue" : ""; return `<span class="badge ${cls}">${esc(sourceLabel(v))}</span>`}
    function badgeStatus(v){const cls = ["admin_verified","university_verified"].includes(v) ? "ok" : v === "claimed" ? "warn" : ""; return `<span class="badge ${cls}">${esc(statusLabel(v))}</span>`}
    function badgeOrgType(v){const cls = ["体育会","部活"].includes(v) ? "blue" : ["公認サークル","同好会"].includes(v) ? "ok" : v === "非公認サークル" ? "warn" : ""; return `<span class="badge ${cls}">${esc(orgTypeLabel(v))}</span>`}
    function fillSelect(el, values, first){el.innerHTML=(first?`<option value="">${first}</option>`:"")+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("")}
    async function refreshSummary(){const s=await api("/api/summary"); $("prefCount").textContent=s.prefectures; $("uniCount").textContent=s.universities; $("circleCount").textContent=s.circles; $("verifiedCount").textContent=s.verified_circles; $("candidateCount").textContent=s.circle_candidates; $("matchCount").textContent=s.match_posts}
    async function refreshUniversities(){const rows=await api("/api/universities"); $("circleUniversity").innerHTML=rows.map(u=>`<option value="${u.university_id}">${esc(u.university_name)} / ${esc(u.prefecture)}</option>`).join(""); $("universityRows").innerHTML=rows.map(u=>`<tr><td class="mono">${u.university_id}</td><td><b>${esc(u.university_name)}</b><br><span class="muted">${esc(u.campus_name||"")}</span></td><td>${esc(u.prefecture)} ${esc(u.city||"")}</td><td>${u.official_url?`<a href="${esc(u.official_url)}" target="_blank">公式</a>`:""}</td></tr>`).join("");}
    async function refreshCircles(){const qs=new URLSearchParams({q:$("q").value,prefecture:$("prefFilter").value,organization_type:$("orgTypeFilter").value,sport:$("sportFilter").value,status:$("statusFilter").value}); const rows=await api("/api/circles?"+qs); $("matchCircle").innerHTML=rows.map(c=>`<option value="${c.circle_id}">${esc(c.university_name)} - ${esc(c.circle_name)}</option>`).join(""); $("circleRows").innerHTML=rows.map(c=>`<tr><td><span class="uni-name">${esc(c.university_name)}</span><span class="subline">${esc(c.prefecture)}${c.city?` / ${esc(c.city)}`:""}</span></td><td class="primary-cell"><span class="circle-name">${esc(c.circle_name)}</span></td><td>${badgeOrgType(c.organization_type)}</td><td>${esc(c.sport_category)}${c.activity_area?`<span class="subline">${esc(c.activity_area)}</span>`:""}</td><td>${badgeSource(c.source_type)}<br>${c.source_url?`<a href="${esc(c.source_url)}" target="_blank">URL</a>`:"<span class='muted'>URLなし</span>"}</td><td>${badgeStatus(c.verification_status)}</td><td class="actions"><button data-edit="${c.circle_id}">編集</button></td></tr>`).join("") || `<tr><td colspan="7" class="muted">データなし</td></tr>`; document.querySelectorAll("[data-edit]").forEach(b=>b.onclick=()=>loadCircle(b.dataset.edit, rows));}
    async function refreshMatches(){const rows=await api("/api/matches"); $("matchRows").innerHTML=rows.map(m=>`<tr><td class="mono">${m.match_post_id}</td><td>${esc(m.university_name)}<br><b>${esc(m.circle_name)}</b></td><td>${esc(m.match_type)}<br><span class="badge">${esc(m.level_label||"")}</span></td><td>${esc(m.scheduled_at||"")}<br><span class="muted">${esc(m.place||"")}</span></td><td>${esc(m.conditions||"")}</td></tr>`).join("") || `<tr><td colspan="5" class="muted">データなし</td></tr>`}
    async function refreshCollection(){const rows=await api("/api/collection_status"); $("collectionRows").innerHTML=rows.map(r=>`<tr><td><b>${esc(r.university_name)}</b><br><span class="mono">${esc(r.university_id)}</span></td><td>${esc(r.prefecture)} ${esc(r.city||"")}</td><td><span class="badge ${r.circle_count>0?"ok":"warn"}">${r.circle_count}件</span></td><td><span class="badge">${esc(r.collection_status)}</span></td><td>${r.source_url?`<a href="${esc(r.source_url)}" target="_blank">出典</a><br>`:""}<span class="muted">${esc(r.source_search_query)}</span></td><td>${esc(r.last_checked_at||"未確認")}</td></tr>`).join("")}
    async function refreshCandidates(){const rows=await api("/api/candidates"); $("candidateRows").innerHTML=rows.map(c=>`<tr><td class="mono">${esc(c.candidate_id)}</td><td><b>${esc(c.university_name)}</b><br><span class="muted">${esc(c.prefecture)} ${esc(c.city||"")}</span></td><td><b>${esc(c.candidate_name)}</b></td><td>${esc(c.sport_category)}<br><span class="badge ${c.review_status==="approved"?"ok":c.review_status==="rejected"?"danger":"warn"}">${esc(c.review_status)}</span></td><td><span class="badge blue">${esc(c.source_type)}</span><br>${c.source_url?`<a href="${esc(c.source_url)}" target="_blank">出典URL</a>`:"<span class='muted'>出典未登録</span>"}<br><span class="muted">${esc(c.evidence_text||"")}</span></td><td>${esc(c.notes||"")}</td><td>${c.review_status==="approved"?"<span class='muted'>昇格済み</span>":`<button data-promote="${esc(c.candidate_id)}">昇格</button> <button class="danger" data-reject="${esc(c.candidate_id)}">却下</button>`}</td></tr>`).join("") || `<tr><td colspan="7" class="muted">候補なし</td></tr>`; document.querySelectorAll("[data-promote]").forEach(b=>b.onclick=()=>promoteCandidate(b.dataset.promote)); document.querySelectorAll("[data-reject]").forEach(b=>b.onclick=()=>rejectCandidate(b.dataset.reject));}
    async function refreshMetrics(){const data=await api("/api/admin_metrics"); $("metricUniversityRows").innerHTML=data.by_university.map(r=>`<tr><td><b>${esc(r.university_name)}</b></td><td>${esc(r.prefecture)}</td><td><span class="badge ${r.circle_count>0?"ok":"warn"}">${r.circle_count}</span></td><td><span class="badge">${r.candidate_count}</span></td></tr>`).join(""); const sections=[["種別",data.by_organization_type],["競技",data.by_sport],["検証",data.by_verification],["出典",data.by_source]]; $("metricRows").innerHTML=sections.flatMap(([label,rows])=>rows.map(r=>`<tr><td>${label}</td><td>${esc(r.name)}</td><td><span class="badge">${r.count}</span></td></tr>`)).join("")}
    async function refreshPrivacy(){const data=await api("/api/privacy_metrics"); $("privacyRows").innerHTML=data.map(r=>`<tr><td><b>${esc(r.label)}</b><br><span class="muted">${esc(r.description)}</span></td><td><span class="badge">${r.count}</span></td><td>${r.public_api?`<span class="badge warn">返す</span>`:`<span class="badge ok">返さない</span>`}</td></tr>`).join("")}
    async function promoteCandidate(id){if(!confirm("この候補を正式サークルDBへ昇格しますか？"))return; await api("/api/candidates/promote",{method:"POST",body:JSON.stringify({candidate_id:id})}); await refreshAll();}
    async function rejectCandidate(id){if(!confirm("この候補を却下しますか？"))return; await api("/api/candidates/reject",{method:"POST",body:JSON.stringify({candidate_id:id})}); await refreshAll();}
    async function refreshLogs(){const rows=await api("/api/audit_logs"); $("logRows").innerHTML=rows.map(l=>`<tr><td>${esc(l.created_at)}</td><td><span class="badge">${esc(l.action)}</span></td><td>${esc(l.entity_type)}<br><span class="mono">${esc(l.entity_id)}</span></td><td><span class="mono">${esc(l.payload)}</span></td></tr>`).join("")}
    function switchView(viewId){document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x.dataset.view===viewId));document.querySelectorAll(".view").forEach(x=>x.classList.toggle("active",x.id===viewId));window.scrollTo({top:0,behavior:"smooth"});}
    function loadCircle(id, rows){const c=rows.find(x=>x.circle_id===id); if(!c)return; $("circleUniversity").value=c.university_id; $("circleName").value=c.circle_name; $("organizationType").value=c.organization_type||"不明"; $("sport").value=c.sport_category; $("activityArea").value=c.activity_area||""; $("sourceType").value=c.source_type; $("verificationStatus").value=c.verification_status; $("sourceUrl").value=c.source_url||""; switchView("circle-register");}
    async function boot(){fillSelect($("sport"),sports); fillSelect($("organizationType"),organizationTypes); fillSelect($("sourceType"),sourceTypes); fillSelect($("verificationStatus"),statuses); fillSelect($("prefFilter"),prefs,"全都道府県"); fillSelect($("orgTypeFilter"),organizationTypes,"全種別"); fillSelect($("sportFilter"),sports,"全競技"); fillSelect($("statusFilter"),statuses,"全ステータス"); fillSelect($("universityPrefecture"),prefs); await refreshAll();}
    async function refreshAll(){await refreshSummary(); await refreshUniversities(); await refreshCircles(); await refreshMatches(); await refreshCollection(); await refreshCandidates(); await refreshMetrics(); await refreshPrivacy(); await refreshLogs();}
    document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>switchView(t.dataset.view));
    ["q","prefFilter","orgTypeFilter","sportFilter","statusFilter"].forEach(id=>$(id).addEventListener("input",refreshCircles)); $("reloadCircles").onclick=refreshCircles; $("reloadCollection").onclick=refreshCollection; $("reloadCandidates").onclick=refreshCandidates; $("reloadMetrics").onclick=refreshMetrics; $("reloadPrivacy").onclick=refreshPrivacy; $("reloadLogs").onclick=refreshLogs;
    $("clearCircleForm").onclick=()=>{$("circleForm").reset();};
    $("universityForm").onsubmit=async e=>{e.preventDefault(); await api("/api/universities",{method:"POST",body:JSON.stringify({university_name:$("universityName").value,prefecture:$("universityPrefecture").value,city:$("city").value,campus_name:$("campusName").value,official_url:$("officialUrl").value})}); e.target.reset(); await refreshAll();};
    $("circleForm").onsubmit=async e=>{e.preventDefault(); await api("/api/circles",{method:"POST",body:JSON.stringify({university_id:$("circleUniversity").value,circle_name:$("circleName").value,organization_type:$("organizationType").value,sport_category:$("sport").value,activity_area:$("activityArea").value,source_type:$("sourceType").value,source_url:$("sourceUrl").value,verification_status:$("verificationStatus").value})}); e.target.reset(); await refreshAll(); switchView("circles");};
    $("matchForm").onsubmit=async e=>{e.preventDefault(); await api("/api/matches",{method:"POST",body:JSON.stringify({circle_id:$("matchCircle").value,match_type:$("matchType").value,level_label:$("levelLabel").value,scheduled_at:$("scheduledAt").value,place:$("place").value,conditions:$("conditions").value})}); e.target.reset(); await refreshAll();};
    $("importForm").onsubmit=async e=>{e.preventDefault(); const r=await api("/api/import/circles_csv",{method:"POST",body:JSON.stringify({csv_text:$("csvText").value})}); alert(`${r.imported}件取り込みました`); $("csvText").value=""; await refreshAll();};
    $("candidateImportForm").onsubmit=async e=>{e.preventDefault(); const r=await api("/api/import/candidates_csv",{method:"POST",body:JSON.stringify({csv_text:$("candidateCsvText").value})}); alert(`${r.imported}件の候補を取り込みました`); $("candidateCsvText").value=""; await refreshAll();};
    boot().catch(err=>alert(err.message));
  </script>
</body>
</html>"""


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log(message):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{now()} {message}\n")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    return conn


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:40]}" if base else f"{prefix}_{int(datetime.now().timestamp())}"


def infer_organization_type(name, source_type=""):
    text = name or ""
    if "体育会" in text:
        return "体育会"
    if text.endswith("部") or "部 " in text or "部　" in text or "部・" in text or "部/" in text:
        return "部活"
    if "同好会" in text:
        return "同好会"
    if "サークル" in text:
        return "公認サークル" if source_type == "university_official" else "非公認サークル"
    if "学生団体" in text or "委員会" in text or "団体" in text:
        return "学生団体"
    return "公認サークル" if source_type == "university_official" else "不明"


def ensure_column(conn, table, column, definition):
    cols = [row["name"] for row in conn.execute(f"pragma table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"alter table {table} add column {column} {definition}")


SENSITIVE_AUDIT_KEYS = {
    "claimant_name", "claimant_email", "email", "mail", "phone", "tel", "line_id",
    "owner_notes", "internal_notes", "sns_url", "public_sns_url", "verification_token",
}


def redacted_payload(payload):
    if isinstance(payload, dict):
        return {
            key: "[redacted]" if key in SENSITIVE_AUDIT_KEYS else redacted_payload(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redacted_payload(value) for value in payload]
    return payload


LEGAL_CSS = """
body{margin:0;background:#f4f7fa;color:#17212f;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.8}
main{max-width:880px;margin:0 auto;padding:32px 18px 56px}
a{color:#2767a5;font-weight:700}h1{font-size:28px;margin:0 0 8px}h2{font-size:19px;margin:28px 0 8px}
p,li{font-size:15px}.meta{color:#65758a;margin-bottom:24px}.panel{background:#fff;border:1px solid #dbe4ed;border-radius:8px;padding:24px}
ul{padding-left:1.3em}.back{display:inline-block;margin-bottom:18px}
"""


def legal_layout(title, body):
    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | {SITE_NAME}</title>
  <style>{LEGAL_CSS}</style>
</head>
<body><main><a class="back" href="/">管理画面へ戻る</a><div class="panel">{body}</div></main></body></html>"""
    return html.encode("utf-8")


def privacy_page():
    body = f"""
<h1>プライバシーポリシー</h1>
<p class="meta">制定日: 2026年7月1日 / 運営者: {SITE_OPERATOR}</p>
<p>{SITE_NAME}は、全国の大学サークル・部活動情報の検索、掲載、代表者確認、練習試合等の募集支援を目的としてサービスを運営します。</p>
<h2>取得する情報</h2>
<ul>
  <li>公開情報: 大学名、団体名、競技カテゴリ、活動地域、出典URL、検証ステータス</li>
  <li>代表者確認情報: 氏名、大学メールアドレス、所属団体、申請内容、審査履歴</li>
  <li>問い合わせ情報: 氏名または担当者名、メールアドレス、問い合わせ本文</li>
  <li>技術情報: IPアドレス、User-Agent、Cookie、アクセスログ、不正利用防止に必要な情報</li>
</ul>
<h2>利用目的</h2>
<ul>
  <li>サークル・部活動情報の掲載、更新、出典確認、削除訂正対応</li>
  <li>大学メール認証、代表者確認、なりすまし防止、権限管理</li>
  <li>問い合わせ対応、重要なお知らせ、不正利用・障害対応</li>
  <li>サービス改善、利用状況分析、広告配信、法令遵守</li>
</ul>
<h2>公開範囲</h2>
<p>公開検索ページには、公開情報のみを表示します。代表者氏名、大学メールアドレス、問い合わせ本文、内部メモ、認証情報は公開しません。</p>
<h2>第三者配信広告とCookie</h2>
<p>本サービスではGoogle AdSense等の第三者配信広告を利用する場合があります。Googleなどの第三者配信事業者は、Cookieを使用して、ユーザーの過去のアクセス情報に基づく広告を配信することがあります。パーソナライズ広告は、Googleの広告設定ページ等から無効にできます。</p>
<h2>第三者提供・委託</h2>
<p>法令に基づく場合を除き、本人の同意なく個人情報を第三者に提供しません。サーバー、メール配信、アクセス解析、広告配信等に必要な範囲で外部サービスに取り扱いを委託する場合があります。</p>
<h2>安全管理措置</h2>
<ul>
  <li>公開DBと個人情報DBの分離</li>
  <li>公開APIから個人情報・内部メモを返さない設計</li>
  <li>認証情報、APIキー、DB接続情報をGitHubに保存しない運用</li>
  <li>監査ログの保存とセンシティブ項目の伏せ字化</li>
  <li>本番環境でのHTTPS、アクセス制御、バックアップ、権限分離</li>
</ul>
<h2>保存期間</h2>
<p>公開情報は掲載目的に必要な期間保存します。代表者確認情報、問い合わせ情報、ログは、対応完了、不正利用防止、法令対応に必要な期間保存し、不要になった情報は削除または識別できない形にします。</p>
<h2>開示・訂正・削除</h2>
<p>本人または団体関係者から、個人情報や掲載情報の開示、訂正、削除、利用停止の請求があった場合、本人確認のうえ合理的な範囲で対応します。</p>
<h2>漏えい等が発生した場合</h2>
<p>個人情報の漏えい、滅失、毀損等が発生した場合、被害拡大防止、原因調査、本人通知、個人情報保護委員会への報告等、法令に従って対応します。</p>
<h2>問い合わせ窓口</h2>
<p>個人情報、掲載情報、削除訂正に関する問い合わせ: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
"""
    return legal_layout("プライバシーポリシー", body)


def terms_page():
    body = f"""
<h1>利用規約</h1>
<p class="meta">制定日: 2026年7月1日 / 運営者: {SITE_OPERATOR}</p>
<h2>目的</h2>
<p>本規約は、{SITE_NAME}の利用条件を定めるものです。本サービスは、大学サークル・部活動情報の検索、掲載、練習試合等の募集支援を目的とします。</p>
<h2>掲載情報</h2>
<p>掲載情報は、大学公式ページ、団体本人の登録、公開SNS、その他公開情報をもとに作成します。正確性の維持に努めますが、内容の完全性、最新性、有用性を保証するものではありません。</p>
<h2>禁止事項</h2>
<ul>
  <li>なりすまし、虚偽登録、第三者の権利侵害</li>
  <li>個人情報、連絡先、非公開情報の無断投稿</li>
  <li>迷惑行為、差別的表現、違法行為、公序良俗に反する行為</li>
  <li>サービス運営、サーバー、DBに過度な負荷をかける行為</li>
</ul>
<h2>代表者申請</h2>
<p>代表者権限は、大学メール認証、公式情報、運営確認等をもとに付与します。虚偽申請や権限の不正利用が判明した場合、掲載停止または権限取消を行います。</p>
<h2>掲載停止・削除</h2>
<p>権利侵害、個人情報、虚偽情報、不適切情報、出典不明情報を確認した場合、運営判断で修正、非公開化、削除を行うことがあります。</p>
<h2>免責</h2>
<p>本サービスの利用、掲載情報、ユーザー間の連絡・試合調整により生じた損害について、運営者の故意または重過失がある場合を除き、運営者は責任を負いません。</p>
<h2>問い合わせ</h2>
<p><a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
"""
    return legal_layout("利用規約", body)


def about_data_page():
    body = f"""
<h1>掲載情報・削除訂正について</h1>
<p class="meta">最終更新日: 2026年7月1日</p>
<h2>情報源</h2>
<p>本サービスは、大学公式ページ、団体本人による登録、公開SNS、その他公開情報を出典として、サークル・部活動の名称、競技、大学、出典URL、検証状態を掲載します。</p>
<h2>掲載しない情報</h2>
<ul>
  <li>代表者の個人メールアドレス、電話番号、LINE ID</li>
  <li>本人同意のない個人名、個人写真、非公開グループの情報</li>
  <li>他サイトの紹介文、画像、口コミ、ランキングのコピー</li>
</ul>
<h2>検証ステータス</h2>
<ul>
  <li>公式確認済み: 大学公式ページで存在確認済み</li>
  <li>運営確認済み: 運営が出典や申請内容を確認済み</li>
  <li>申請済み: 団体関係者から申請があった状態</li>
  <li>未確認: 公開情報から候補として登録した状態</li>
</ul>
<h2>削除・訂正依頼</h2>
<p>掲載情報の削除、訂正、非公開化を希望する場合は、団体名、大学名、対象URL、依頼内容、申請者の立場を記載して <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> まで連絡してください。</p>
"""
    return legal_layout("掲載情報・削除訂正について", body)


def contact_page():
    body = f"""
<h1>問い合わせ</h1>
<p class="meta">運営者: {SITE_OPERATOR}</p>
<p>掲載情報の訂正、削除、代表者申請、個人情報に関する問い合わせは、以下のメールアドレスまで連絡してください。</p>
<p><a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
<h2>記載してほしい内容</h2>
<ul>
  <li>大学名、団体名</li>
  <li>対象ページまたは出典URL</li>
  <li>訂正・削除・問い合わせの内容</li>
  <li>申請者の立場</li>
</ul>
"""
    return legal_layout("問い合わせ", body)


def init_db():
    with connect() as conn:
        conn.executescript("""
        create table if not exists prefectures (
          prefecture text primary key,
          region text
        );
        create table if not exists universities (
          university_id text primary key,
          university_name text not null,
          prefecture text not null references prefectures(prefecture),
          city text,
          campus_name text,
          official_url text,
          source_url text,
          created_at text not null,
          updated_at text not null,
          unique(university_name, campus_name)
        );
        create table if not exists circles (
          circle_id text primary key,
          university_id text not null references universities(university_id),
          circle_name text not null,
          organization_type text not null default '不明',
          sport_category text not null,
          activity_area text,
          source_type text not null check(source_type in ('university_official','self_registered','public_sns','other')),
          source_url text,
          verification_status text not null check(verification_status in ('unverified','claimed','university_verified','admin_verified')),
          public_status text not null default 'draft',
          last_checked_at text,
          sns_url text,
          owner_notes text,
          created_at text not null,
          updated_at text not null,
          unique(university_id, circle_name)
        );
        create table if not exists circle_private_profiles (
          profile_id text primary key,
          circle_id text not null references circles(circle_id) on delete cascade,
          public_sns_url text,
          internal_notes text,
          consent_status text not null default 'not_applicable',
          created_at text not null,
          updated_at text not null,
          unique(circle_id)
        );
        create table if not exists circle_claims (
          claim_id text primary key,
          circle_id text not null references circles(circle_id) on delete cascade,
          claimant_name text,
          claimant_email text not null,
          university_email_verified integer not null default 0,
          status text not null default 'pending',
          evidence_url text,
          reviewed_at text,
          created_at text not null,
          updated_at text not null
        );
        create table if not exists match_posts (
          match_post_id text primary key,
          circle_id text not null references circles(circle_id),
          match_type text not null,
          level_label text,
          scheduled_at text,
          place text,
          conditions text,
          status text not null default 'open',
          created_at text not null,
          updated_at text not null
        );
        create table if not exists data_sources (
          source_id text primary key,
          entity_type text not null,
          entity_id text not null,
          source_type text not null,
          source_url text,
          memo text,
          checked_at text,
          created_at text not null
        );
        create table if not exists audit_logs (
          audit_id integer primary key autoincrement,
          action text not null,
          entity_type text not null,
          entity_id text,
          payload text,
          created_at text not null
        );
        create table if not exists collection_targets (
          university_id text primary key references universities(university_id),
          collection_status text not null default 'not_started',
          priority integer not null default 3,
          source_search_query text,
          source_url text,
          notes text,
          last_checked_at text,
          updated_at text not null
        );
        create table if not exists circle_candidates (
          candidate_id text primary key,
          university_id text not null references universities(university_id),
          candidate_name text not null,
          sport_category text not null default 'その他',
          source_type text not null default 'other',
          source_url text,
          evidence_text text,
          review_status text not null default 'pending',
          notes text,
          created_at text not null,
          updated_at text not null,
          unique(university_id, candidate_name, source_url)
        );
        create table if not exists collection_runs (
          run_id text primary key,
          target_scope text not null,
          status text not null,
          collected_count integer not null default 0,
          candidate_count integer not null default 0,
          memo text,
          started_at text not null,
          finished_at text
        );
        create index if not exists idx_universities_prefecture on universities(prefecture);
        create index if not exists idx_circles_university on circles(university_id);
        create index if not exists idx_circles_sport on circles(sport_category);
        create index if not exists idx_circles_status on circles(verification_status);
        create index if not exists idx_circle_private_profiles_circle on circle_private_profiles(circle_id);
        create index if not exists idx_circle_claims_circle on circle_claims(circle_id);
        create index if not exists idx_circle_claims_status on circle_claims(status);
        create index if not exists idx_circle_candidates_university on circle_candidates(university_id);
        create index if not exists idx_circle_candidates_status on circle_candidates(review_status);
        """)
        ensure_column(conn, "circles", "organization_type", "text not null default '不明'")
        conn.execute("create index if not exists idx_circles_organization_type on circles(organization_type)")
        conn.execute("""
            update circles
            set organization_type = case
              when circle_name like '%体育会%' then '体育会'
              when circle_name like '%同好会%' then '同好会'
              when circle_name like '%サークル%' and source_type='university_official' then '公認サークル'
              when circle_name like '%サークル%' then '非公認サークル'
              when circle_name like '%学生団体%' or circle_name like '%委員会%' or circle_name like '%団体%' then '学生団体'
              when circle_name like '%部' or circle_name like '%部 %' or circle_name like '%部　%' then '部活'
              when source_type='university_official' then '公認サークル'
              else '不明'
            end
            where organization_type is null or organization_type='' or organization_type='不明'
        """)
        for pref in PREFECTURES:
            conn.execute("insert or ignore into prefectures(prefecture, region) values(?, '')", (pref,))
        for name, pref, city, campus, url in UNIVERSITY_SEED:
            upsert_university(conn, {
                "university_name": name,
                "prefecture": pref,
                "city": city,
                "campus_name": campus,
                "official_url": url,
                "source_url": url,
            }, audit=False)
        if conn.execute("select count(*) from circles").fetchone()[0] == 0:
            seed_circles(conn)
        migrate_circle_private_data(conn)
        redact_existing_audit_logs(conn)
        seed_collection_targets(conn)
        conn.commit()


def audit(conn, action, entity_type, entity_id, payload):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(redacted_payload(payload), ensure_ascii=False), now()),
    )


def upsert_university(conn, data, audit=True):
    required = data.get("university_name", "").strip()
    if not required:
        raise ValueError("university_name is required")
    uni_id = data.get("university_id") or slug("u", required + "_" + data.get("campus_name", ""))
    timestamp = now()
    conn.execute(
        """
        insert into universities(university_id, university_name, prefecture, city, campus_name, official_url, source_url, created_at, updated_at)
        values(?,?,?,?,?,?,?,?,?)
        on conflict(university_name, campus_name) do update set
          prefecture=excluded.prefecture,
          city=excluded.city,
          official_url=excluded.official_url,
          source_url=excluded.source_url,
          updated_at=excluded.updated_at
        """,
        (
            uni_id,
            required,
            data.get("prefecture") or "東京都",
            data.get("city", ""),
            data.get("campus_name", ""),
            data.get("official_url", ""),
            data.get("source_url", data.get("official_url", "")),
            timestamp,
            timestamp,
        ),
    )
    if audit:
        audit_log_id = conn.execute(
            "select university_id from universities where university_name=? and campus_name=?",
            (required, data.get("campus_name", "")),
        ).fetchone()["university_id"]
        globals()["audit"](conn, "upsert", "university", audit_log_id, data)
        return audit_log_id
    return uni_id


def upsert_circle_private_profile(conn, circle_id, data):
    public_sns_url = (data.get("public_sns_url") or data.get("sns_url") or "").strip()
    internal_notes = (data.get("internal_notes") or data.get("owner_notes") or "").strip()
    if not public_sns_url and not internal_notes:
        return
    timestamp = now()
    conn.execute(
        """
        insert into circle_private_profiles(profile_id, circle_id, public_sns_url, internal_notes, consent_status, created_at, updated_at)
        values(?,?,?,?,?,?,?)
        on conflict(circle_id) do update set
          public_sns_url=case when excluded.public_sns_url='' then circle_private_profiles.public_sns_url else excluded.public_sns_url end,
          internal_notes=case when excluded.internal_notes='' then circle_private_profiles.internal_notes else excluded.internal_notes end,
          consent_status=excluded.consent_status,
          updated_at=excluded.updated_at
        """,
        (
            slug("priv", circle_id),
            circle_id,
            public_sns_url,
            internal_notes,
            data.get("consent_status", "not_applicable"),
            timestamp,
            timestamp,
        ),
    )


def migrate_circle_private_data(conn):
    rows_to_migrate = conn.execute(
        """
        select circle_id, coalesce(sns_url, '') as sns_url, coalesce(owner_notes, '') as owner_notes
        from circles
        where coalesce(sns_url, '') <> '' or coalesce(owner_notes, '') <> ''
        """
    ).fetchall()
    for row in rows_to_migrate:
        upsert_circle_private_profile(conn, row["circle_id"], {
            "sns_url": row["sns_url"],
            "owner_notes": row["owner_notes"],
            "consent_status": "legacy_private_migrated",
        })
    if rows_to_migrate:
        conn.execute("update circles set sns_url='', owner_notes='' where coalesce(sns_url, '') <> '' or coalesce(owner_notes, '') <> ''")
        audit(conn, "privacy_migrate", "circle_private_profiles", None, {"migrated": len(rows_to_migrate)})


def redact_existing_audit_logs(conn):
    changed = 0
    for row in conn.execute("select audit_id, payload from audit_logs where payload is not null and payload <> ''").fetchall():
        try:
            payload = json.loads(row["payload"])
        except json.JSONDecodeError:
            continue
        redacted = redacted_payload(payload)
        if redacted != payload:
            conn.execute(
                "update audit_logs set payload=? where audit_id=?",
                (json.dumps(redacted, ensure_ascii=False), row["audit_id"]),
            )
            changed += 1
    if changed:
        conn.execute(
            "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
            ("privacy_redact_existing_logs", "audit_logs", None, json.dumps({"redacted": changed}, ensure_ascii=False), now()),
        )


def upsert_circle(conn, data):
    name = data.get("circle_name", "").strip()
    university_id = data.get("university_id", "").strip()
    if not name or not university_id:
        raise ValueError("university_id and circle_name are required")
    circle_id = data.get("circle_id") or slug("c", university_id + "_" + name)
    timestamp = now()
    conn.execute(
        """
        insert into circles(circle_id, university_id, circle_name, organization_type, sport_category, activity_area, source_type, source_url,
          verification_status, public_status, last_checked_at, sns_url, owner_notes, created_at, updated_at)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        on conflict(university_id, circle_name) do update set
          organization_type=excluded.organization_type,
          sport_category=excluded.sport_category,
          activity_area=excluded.activity_area,
          source_type=excluded.source_type,
          source_url=excluded.source_url,
          verification_status=excluded.verification_status,
          public_status=excluded.public_status,
          last_checked_at=excluded.last_checked_at,
          updated_at=excluded.updated_at
        """,
        (
            circle_id,
            university_id,
            name,
            data.get("organization_type") if data.get("organization_type") in ORGANIZATION_TYPES else infer_organization_type(name, data.get("source_type", "")),
            data.get("sport_category") or "その他",
            data.get("activity_area", ""),
            data.get("source_type") if data.get("source_type") in SOURCE_TYPES else "other",
            data.get("source_url", ""),
            data.get("verification_status") if data.get("verification_status") in VERIFICATION_STATUSES else "unverified",
            data.get("public_status", "published"),
            data.get("last_checked_at") or now()[:10],
            "",
            "",
            timestamp,
            timestamp,
        ),
    )
    row = conn.execute(
        "select circle_id from circles where university_id=? and circle_name=?",
        (university_id, name),
    ).fetchone()
    saved_id = row["circle_id"]
    upsert_circle_private_profile(conn, saved_id, data)
    if data.get("source_url"):
        conn.execute(
            "insert or replace into data_sources(source_id, entity_type, entity_id, source_type, source_url, memo, checked_at, created_at) values(?,?,?,?,?,?,?,?)",
            (slug("src", saved_id + data.get("source_url", "")), "circle", saved_id, data.get("source_type", "other"), data.get("source_url", ""), "circle source", now()[:10], timestamp),
        )
    audit(conn, "upsert", "circle", saved_id, data)
    return saved_id


def seed_circles(conn):
    samples = [
        ("早稲田大学", "サンプル フットサル同好会", "フットサル", "東京都新宿区", "self_registered", "claimed", "経験者と初心者が混在。平日夜に練習試合希望。"),
        ("慶應義塾大学", "サンプル バスケットボールサークル", "バスケットボール", "東京都港区", "university_official", "university_verified", "中級中心。体育館確保済みの日に相手募集。"),
        ("九州大学", "サンプル サッカーサークル", "サッカー", "福岡県福岡市", "public_sns", "unverified", "九州エリアの練習試合候補。出典確認待ち。"),
    ]
    for uni_name, circle, sport, area, source_type, status, notes in samples:
        uni = conn.execute("select university_id from universities where university_name=?", (uni_name,)).fetchone()
        if uni:
            upsert_circle(conn, {
                "university_id": uni["university_id"],
                "circle_name": circle,
                "sport_category": sport,
                "activity_area": area,
                "organization_type": infer_organization_type(circle, source_type),
                "source_type": source_type,
                "verification_status": status,
                "owner_notes": notes,
            })


def seed_collection_targets(conn):
    timestamp = now()
    universities = conn.execute("select university_id, university_name from universities").fetchall()
    for university in universities:
        count = conn.execute("select count(*) from circles where university_id=?", (university["university_id"],)).fetchone()[0]
        status = "partial" if count else "not_started"
        query = f"{university['university_name']} 公認団体 サークル 一覧"
        conn.execute(
            """
            insert into collection_targets(university_id, collection_status, priority, source_search_query, source_url, notes, last_checked_at, updated_at)
            values(?,?,?,?,?,?,?,?)
            on conflict(university_id) do update set
              collection_status=case
                when collection_targets.collection_status in ('official_confirmed','self_registered') then collection_targets.collection_status
                when ? > 0 then 'partial'
                else collection_targets.collection_status
              end,
              source_search_query=coalesce(collection_targets.source_search_query, excluded.source_search_query),
              updated_at=excluded.updated_at
            """,
            (
                university["university_id"],
                status,
                3,
                query,
                "",
                "大学公式・競技連盟・団体公式SNSから収集予定",
                now()[:10] if count else "",
                timestamp,
                count,
            ),
        )


def rows(query, params=()):
    with connect() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, body, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                body = HTML.replace("__SPORTS__", json.dumps(SPORTS, ensure_ascii=False)).replace("__SOURCE_TYPES__", json.dumps(SOURCE_TYPES, ensure_ascii=False)).replace("__STATUSES__", json.dumps(VERIFICATION_STATUSES, ensure_ascii=False)).replace("__ORG_TYPES__", json.dumps(ORGANIZATION_TYPES, ensure_ascii=False)).replace("__PREFS__", json.dumps(PREFECTURES, ensure_ascii=False)).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif parsed.path == "/privacy":
                self.send_html(privacy_page())
            elif parsed.path == "/terms":
                self.send_html(terms_page())
            elif parsed.path == "/about-data":
                self.send_html(about_data_page())
            elif parsed.path == "/contact":
                self.send_html(contact_page())
            elif parsed.path == "/api/summary":
                self.send_json(summary())
            elif parsed.path == "/api/universities":
                self.send_json(rows("select * from universities order by prefecture, university_name"))
            elif parsed.path == "/api/circles":
                self.send_json(search_circles(parse_qs(parsed.query)))
            elif parsed.path == "/api/matches":
                self.send_json(rows("""
                    select m.*, c.circle_name, u.university_name
                    from match_posts m join circles c on c.circle_id=m.circle_id join universities u on u.university_id=c.university_id
                    order by coalesce(m.scheduled_at, ''), m.created_at desc
                """))
            elif parsed.path == "/api/collection_status":
                self.send_json(collection_status())
            elif parsed.path == "/api/candidates":
                self.send_json(candidate_rows())
            elif parsed.path == "/api/admin_metrics":
                self.send_json(admin_metrics())
            elif parsed.path == "/api/privacy_metrics":
                self.send_json(privacy_metrics())
            elif parsed.path == "/api/audit_logs":
                self.send_json(rows("select * from audit_logs order by audit_id desc limit 200"))
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self.read_json()
            with connect() as conn:
                if parsed.path == "/api/universities":
                    entity_id = upsert_university(conn, data)
                    conn.commit()
                    self.send_json({"ok": True, "university_id": entity_id})
                elif parsed.path == "/api/circles":
                    entity_id = upsert_circle(conn, data)
                    conn.commit()
                    self.send_json({"ok": True, "circle_id": entity_id})
                elif parsed.path == "/api/matches":
                    entity_id = slug("m", data.get("circle_id", "") + data.get("scheduled_at", ""))
                    timestamp = now()
                    conn.execute(
                        "insert into match_posts(match_post_id, circle_id, match_type, level_label, scheduled_at, place, conditions, status, created_at, updated_at) values(?,?,?,?,?,?,?,?,?,?)",
                        (entity_id, data["circle_id"], data.get("match_type", "練習試合"), data.get("level_label", ""), data.get("scheduled_at", ""), data.get("place", ""), data.get("conditions", ""), "open", timestamp, timestamp),
                    )
                    audit(conn, "insert", "match_post", entity_id, data)
                    conn.commit()
                    self.send_json({"ok": True, "match_post_id": entity_id})
                elif parsed.path == "/api/import/circles_csv":
                    imported = import_circles_csv(conn, data.get("csv_text", ""))
                    conn.commit()
                    self.send_json({"ok": True, "imported": imported})
                elif parsed.path == "/api/import/candidates_csv":
                    imported = import_candidates_csv(conn, data.get("csv_text", ""))
                    conn.commit()
                    self.send_json({"ok": True, "imported": imported})
                elif parsed.path == "/api/candidates/promote":
                    entity_id = promote_candidate(conn, data.get("candidate_id", ""))
                    conn.commit()
                    self.send_json({"ok": True, "circle_id": entity_id})
                elif parsed.path == "/api/candidates/reject":
                    reject_candidate(conn, data.get("candidate_id", ""))
                    conn.commit()
                    self.send_json({"ok": True})
                else:
                    self.send_json({"error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)


def summary():
    with connect() as conn:
        return {
            "prefectures": conn.execute("select count(*) from prefectures").fetchone()[0],
            "universities": conn.execute("select count(*) from universities").fetchone()[0],
            "circles": conn.execute("select count(*) from circles").fetchone()[0],
            "verified_circles": conn.execute("select count(*) from circles where verification_status in ('claimed','university_verified','admin_verified')").fetchone()[0],
            "circle_candidates": conn.execute("select count(*) from circle_candidates").fetchone()[0],
            "match_posts": conn.execute("select count(*) from match_posts").fetchone()[0],
        }


def search_circles(params):
    query = (params.get("q", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    organization_type = (params.get("organization_type", [""])[0] or "").strip()
    sport = (params.get("sport", [""])[0] or "").strip()
    status = (params.get("status", [""])[0] or "").strip()
    where = []
    args = []
    if query:
        where.append("(c.circle_name like ? or c.sport_category like ? or c.activity_area like ? or u.university_name like ?)")
        args.extend([f"%{query}%"] * 4)
    if prefecture:
        where.append("u.prefecture=?")
        args.append(prefecture)
    if organization_type:
        where.append("c.organization_type=?")
        args.append(organization_type)
    if sport:
        where.append("c.sport_category=?")
        args.append(sport)
    if status:
        where.append("c.verification_status=?")
        args.append(status)
    sql = """
        select
          c.circle_id,
          c.university_id,
          c.circle_name,
          c.organization_type,
          c.sport_category,
          c.activity_area,
          c.source_type,
          c.source_url,
          c.verification_status,
          c.public_status,
          c.last_checked_at,
          c.created_at,
          c.updated_at,
          u.university_name,
          u.prefecture,
          u.city
        from circles c join universities u on u.university_id=c.university_id
    """
    if where:
        sql += " where " + " and ".join(where)
    sql += " order by u.prefecture, u.university_name, c.sport_category, c.circle_name"
    return rows(sql, args)


def collection_status():
    return rows("""
        select
          u.university_id,
          u.university_name,
          u.prefecture,
          u.city,
          coalesce(ct.collection_status, 'not_started') as collection_status,
          coalesce(ct.priority, 3) as priority,
          coalesce(ct.source_search_query, u.university_name || ' 公認団体 サークル 一覧') as source_search_query,
          coalesce(ct.source_url, '') as source_url,
          coalesce(ct.notes, '') as notes,
          coalesce(ct.last_checked_at, '') as last_checked_at,
          coalesce(circle_counts.circle_count, 0) as circle_count
        from universities u
        left join collection_targets ct on ct.university_id = u.university_id
        left join (
          select university_id, count(*) as circle_count
          from circles
          group by university_id
        ) circle_counts on circle_counts.university_id = u.university_id
        order by circle_count asc, u.prefecture, u.university_name
    """)


def candidate_rows():
    return rows("""
        select cc.*, u.university_name, u.prefecture, u.city
        from circle_candidates cc
        join universities u on u.university_id = cc.university_id
        order by
          case cc.review_status when 'pending' then 0 when 'needs_check' then 1 when 'approved' then 2 else 3 end,
          u.prefecture,
          u.university_name,
          cc.candidate_name
    """)


def admin_metrics():
    return {
        "by_university": rows("""
            select
              u.university_name,
              u.prefecture,
              coalesce(c.circle_count, 0) as circle_count,
              coalesce(cc.candidate_count, 0) as candidate_count
            from universities u
            left join (
              select university_id, count(*) as circle_count
              from circles
              group by university_id
            ) c on c.university_id = u.university_id
            left join (
              select university_id, count(*) as candidate_count
              from circle_candidates
              group by university_id
            ) cc on cc.university_id = u.university_id
            order by circle_count asc, candidate_count desc, u.prefecture, u.university_name
            limit 120
        """),
        "by_sport": rows("""
            select sport_category as name, count(*) as count
            from circles
            group by sport_category
            order by count desc, sport_category
        """),
        "by_organization_type": rows("""
            select organization_type as name, count(*) as count
            from circles
            group by organization_type
            order by count desc, organization_type
        """),
        "by_verification": rows("""
            select verification_status as name, count(*) as count
            from circles
            group by verification_status
            order by count desc, verification_status
        """),
        "by_source": rows("""
            select source_type as name, count(*) as count
            from circles
            group by source_type
            order by count desc, source_type
        """),
    }


def privacy_metrics():
    with connect() as conn:
        return [
            {
                "label": "公開サークルDB",
                "description": "大学名、団体名、種別、競技、出典、検証状態",
                "count": conn.execute("select count(*) from circles").fetchone()[0],
                "public_api": True,
            },
            {
                "label": "非公開サークル補足",
                "description": "SNS管理URL、内部メモ、同意状態。公開検索APIには返さない",
                "count": conn.execute("select count(*) from circle_private_profiles").fetchone()[0],
                "public_api": False,
            },
            {
                "label": "代表者申請",
                "description": "氏名、大学メール、申請状態。公開検索APIには返さない",
                "count": conn.execute("select count(*) from circle_claims").fetchone()[0],
                "public_api": False,
            },
            {
                "label": "候補DB",
                "description": "未公開候補。管理画面だけでレビューする",
                "count": conn.execute("select count(*) from circle_candidates").fetchone()[0],
                "public_api": False,
            },
        ]


def import_circles_csv(conn, text):
    reader = csv.DictReader(text.splitlines())
    imported = 0
    for item in reader:
        uni_name = (item.get("university_name") or "").strip()
        circle_name = (item.get("circle_name") or "").strip()
        if not uni_name or not circle_name:
            continue
        uni = conn.execute("select university_id from universities where university_name=? order by campus_name limit 1", (uni_name,)).fetchone()
        if not uni:
            university_id = upsert_university(conn, {
                "university_name": uni_name,
                "prefecture": item.get("prefecture") or "東京都",
                "city": item.get("city", ""),
                "campus_name": item.get("campus_name", ""),
                "official_url": item.get("official_url", ""),
            })
        else:
            university_id = uni["university_id"]
        upsert_circle(conn, {
            "university_id": university_id,
            "circle_name": circle_name,
            "organization_type": item.get("organization_type") or infer_organization_type(circle_name, item.get("source_type") or "other"),
            "sport_category": item.get("sport_category") or "その他",
            "activity_area": item.get("activity_area", ""),
            "source_type": item.get("source_type") or "other",
            "source_url": item.get("source_url", ""),
            "verification_status": item.get("verification_status") or "unverified",
            "sns_url": item.get("sns_url", ""),
            "owner_notes": item.get("owner_notes", ""),
        })
        imported += 1
    audit(conn, "csv_import", "circle", None, {"imported": imported})
    return imported


def import_candidates_csv(conn, text):
    reader = csv.DictReader(text.splitlines())
    imported = 0
    for item in reader:
        uni_name = (item.get("university_name") or "").strip()
        candidate_name = (item.get("candidate_name") or item.get("circle_name") or "").strip()
        if not uni_name or not candidate_name:
            continue
        uni = conn.execute(
            "select university_id from universities where university_name=? order by campus_name limit 1",
            (uni_name,),
        ).fetchone()
        if not uni:
            university_id = upsert_university(conn, {
                "university_name": uni_name,
                "prefecture": item.get("prefecture") or "東京都",
                "city": item.get("city", ""),
                "campus_name": item.get("campus_name", ""),
                "official_url": item.get("official_url", ""),
            })
        else:
            university_id = uni["university_id"]
        source_url = (item.get("source_url") or "").strip()
        candidate_id = slug("cand", university_id + "_" + candidate_name + "_" + source_url)
        timestamp = now()
        conn.execute(
            """
            insert into circle_candidates(candidate_id, university_id, candidate_name, sport_category, source_type,
              source_url, evidence_text, review_status, notes, created_at, updated_at)
            values(?,?,?,?,?,?,?,?,?,?,?)
            on conflict(university_id, candidate_name, source_url) do update set
              sport_category=excluded.sport_category,
              source_type=excluded.source_type,
              evidence_text=excluded.evidence_text,
              review_status=excluded.review_status,
              notes=excluded.notes,
              updated_at=excluded.updated_at
            """,
            (
                candidate_id,
                university_id,
                candidate_name,
                item.get("sport_category") or "その他",
                item.get("source_type") or "other",
                source_url,
                item.get("evidence_text", ""),
                item.get("review_status") or "pending",
                item.get("notes", ""),
                timestamp,
                timestamp,
            ),
        )
        imported += 1
    audit(conn, "csv_import", "circle_candidate", None, {"imported": imported})
    return imported


def promote_candidate(conn, candidate_id):
    candidate = conn.execute(
        "select * from circle_candidates where candidate_id=?",
        (candidate_id,),
    ).fetchone()
    if not candidate:
        raise ValueError("candidate not found")
    circle_id = upsert_circle(conn, {
        "university_id": candidate["university_id"],
        "circle_name": candidate["candidate_name"],
        "organization_type": infer_organization_type(candidate["candidate_name"], candidate["source_type"]),
        "sport_category": candidate["sport_category"],
        "activity_area": "",
        "source_type": candidate["source_type"] if candidate["source_type"] in SOURCE_TYPES else "other",
        "source_url": candidate["source_url"] or "",
        "verification_status": "admin_verified",
        "public_status": "published",
        "owner_notes": candidate["notes"] or candidate["evidence_text"] or "",
    })
    conn.execute(
        "update circle_candidates set review_status='approved', updated_at=? where candidate_id=?",
        (now(), candidate_id),
    )
    audit(conn, "promote", "circle_candidate", candidate_id, {"circle_id": circle_id})
    return circle_id


def reject_candidate(conn, candidate_id):
    candidate = conn.execute(
        "select candidate_id from circle_candidates where candidate_id=?",
        (candidate_id,),
    ).fetchone()
    if not candidate:
        raise ValueError("candidate not found")
    conn.execute(
        "update circle_candidates set review_status='rejected', updated_at=? where candidate_id=?",
        (now(), candidate_id),
    )
    audit(conn, "reject", "circle_candidate", candidate_id, {})


def main():
    try:
        log("starting")
        init_db()
        if len(sys.argv) > 1 and sys.argv[1] == "--init-only":
            print(json.dumps({"db": str(DB_PATH), **summary()}, ensure_ascii=False, indent=2))
            return
        server = ThreadingHTTPServer((HOST, PORT), Handler)
        log(f"listening http://{HOST}:{PORT}")
        try:
            print(f"Circle Match DB Admin: http://{HOST}:{PORT}")
            print(f"SQLite DB: {DB_PATH}")
        except Exception:
            pass
        server.serve_forever()
    except Exception as exc:
        log(f"failed {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
