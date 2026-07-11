import csv
import base64
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sqlite3
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("CIRCLEMATCH_DB_PATH", ROOT / "circlematch.sqlite"))
PUBLIC_SEED_PATH = Path(os.environ.get("CIRCLEMATCH_PUBLIC_SEED_PATH", ROOT / "public_circles_seed.csv"))
LOG_PATH = ROOT.parent / "work" / "circlematch_db_app.log"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8787"))
SITE_NAME = os.environ.get("CIRCLEMATCH_SITE_NAME", "Circle Match")
SITE_OPERATOR = os.environ.get("CIRCLEMATCH_OPERATOR", "Circle Match 運営")
CONTACT_EMAIL = os.environ.get("CIRCLEMATCH_CONTACT_EMAIL", "contact@example.com")
SITE_BASE_URL = os.environ.get("CIRCLEMATCH_SITE_BASE_URL", "")
ADMIN_USERNAME = os.environ.get("CIRCLEMATCH_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("CIRCLEMATCH_ADMIN_PASSWORD", "")
GOOGLE_CLIENT_ID = os.environ.get("CIRCLEMATCH_GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("CIRCLEMATCH_GOOGLE_CLIENT_SECRET", "")
SUPABASE_URL = os.environ.get("CIRCLEMATCH_SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("CIRCLEMATCH_SUPABASE_ANON_KEY", "")
SESSION_SECRET = os.environ.get("CIRCLEMATCH_SESSION_SECRET", ADMIN_PASSWORD or "local-dev-session-secret")
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

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
POPULAR_SPORTS = [
    ("野球", "Baseball", "BS", "#1f6f8b", "baseball.png"),
    ("サッカー", "Football", "SC", "#0f7a62", "soccer.png"),
    ("テニス", "Tennis", "TN", "#b2601d", "tennis.png"),
    ("バスケットボール", "Basketball", "BK", "#9a3b24", "basketball.png"),
    ("バレーボール", "Volleyball", "VB", "#315b9a", "volleyball.png"),
    ("バドミントン", "Badminton", "BD", "#6d4aa2", "badminton.png"),
    ("フットサル", "Futsal", "FS", "#2d806b", "futsal.png"),
    ("ラグビー", "Rugby", "RG", "#7a4b2b", "rugby.png"),
    ("その他", "Other Sports", "OT", "#42526b", "other.png"),
]
KANTO_PREFECTURES = ["東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県"]
REGION_GROUPS = {
    "hokkaido": {"label": "北海道", "prefectures": ["北海道"]},
    "tohoku": {"label": "東北", "prefectures": ["青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県"]},
    "kanto": {"label": "関東", "prefectures": KANTO_PREFECTURES},
    "chubu": {"label": "中部", "prefectures": ["新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県"]},
    "kansai": {"label": "関西", "prefectures": ["三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県"]},
    "chugoku_shikoku": {"label": "中国・四国", "prefectures": ["鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県"]},
    "kyushu": {"label": "九州", "prefectures": ["福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]},
}
SOURCE_TYPES = ["university_official", "self_registered", "public_sns", "other"]
VERIFICATION_STATUSES = ["unverified", "claimed", "university_verified", "admin_verified"]
ORGANIZATION_TYPES = ["体育会", "部活", "公認サークル", "同好会", "非公認サークル", "学生団体", "不明"]
ADSENSE_HEAD = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5276152865683531" crossorigin="anonymous"></script>'


def with_adsense(html):
    if ADSENSE_HEAD in html:
        return html
    return html.replace("</head>", f"  {ADSENSE_HEAD}\n</head>", 1)

MATCH_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__SITE_NAME__ | 大学サークルの練習試合・交流募集</title>
  <style>
    :root{--ink:#17212f;--muted:#64748b;--line:#dbe4ed;--paper:#fff;--soft:#f3f7fb;--brand:#0f7a62;--accent:#e15b31;--blue:#2767a5}
    *{box-sizing:border-box}body{margin:0;background:#f4f7fa;color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    a{color:inherit}.topbar{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}
    .top{max-width:1180px;margin:auto;padding:12px 18px;display:flex;align-items:center;justify-content:space-between;gap:14px}.brand{display:flex;align-items:center;gap:10px;font-weight:900;text-decoration:none}.mark{display:grid;place-items:center;width:34px;height:34px;border-radius:8px;background:#0f7a62;color:#fff}
    .nav{display:flex;align-items:center;gap:9px;flex-wrap:wrap}.nav a{font-size:14px;font-weight:900;color:#31506b;text-decoration:none}.nav a.login-user,.nav a.signup-user{display:inline-flex;align-items:center;min-height:40px;border-radius:8px;padding:9px 15px}.nav a.login-user{border:1px solid var(--accent);background:#fff;color:var(--accent)}.nav a.signup-user{border:1px solid var(--accent);background:var(--accent);color:#fff}
    .hero{position:relative;min-height:560px;display:grid;align-items:end;overflow:hidden;background:#102034}.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(8,18,31,.86),rgba(8,18,31,.54) 48%,rgba(8,18,31,.18))}
    .hero-inner{position:relative;max-width:1180px;margin:0 auto;width:100%;padding:84px 18px 54px;color:#fff}.eyebrow{margin:0 0 12px;font-size:13px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#bde8dc}.hero h1{max-width:780px;margin:0;font-size:clamp(34px,6vw,68px);line-height:1.05;letter-spacing:0}.lead{max-width:720px;margin:18px 0 0;color:#e9f3f1;font-size:17px;line-height:1.8}
    .actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}.button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;border-radius:8px;padding:11px 16px;font-weight:900;text-decoration:none;border:1px solid transparent}.button.primary{background:var(--accent);color:#fff}.button.secondary{background:#fff;border-color:var(--accent);color:var(--accent)}.button.light{background:#fff;color:var(--ink);border-color:var(--line)}.hero-cta{min-height:56px;font-size:18px;padding:14px 22px}.db-bridge{background:#14344d!important;color:#fff!important;border-color:#14344d!important}
    main{max-width:1180px;margin:auto;padding:22px 18px 48px}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:-42px;position:relative;z-index:2}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:850}.metric strong{display:block;margin-top:6px;font-size:26px}
    .section{margin-top:24px}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.panel-head{padding:18px;border-bottom:1px solid var(--line);display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap}.panel-head h2{margin:0;font-size:24px}.panel-head p{margin:8px 0 0;color:var(--muted);line-height:1.7;max-width:760px}.section-link{padding:0 14px 16px}.section-link a{color:#31506b;font-weight:900}
    .filters{display:grid;grid-template-columns:minmax(220px,1fr) repeat(5,150px);gap:9px;padding:14px;background:#f9fbfd;border-bottom:1px solid var(--line)}input,select,textarea{width:100%;border:1px solid #cbd7e2;border-radius:8px;min-height:42px;padding:10px 11px;font:inherit;background:#fff;color:var(--ink)}
    .match-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:14px}.match-card{border:1px solid var(--line);border-radius:8px;padding:15px;background:#fff;display:flex;flex-direction:column;gap:12px;min-height:230px}.match-card h3{margin:0;font-size:18px}.meta{display:grid;gap:6px;color:var(--muted);font-size:13px;line-height:1.5}.tagline{color:#405164;line-height:1.7;margin:0}.badges{display:flex;gap:6px;flex-wrap:wrap}.badge{display:inline-flex;align-items:center;min-height:23px;padding:3px 8px;border-radius:999px;background:#eef4f8;color:#405164;font-size:12px;font-weight:900}.badge.open{background:#e2f5ed;color:#0d674f}.badge.type{background:#e8eef8;color:#24558a}
    .empty{padding:28px;color:var(--muted);line-height:1.8}.sport-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.sport-card{position:relative;overflow:hidden;min-height:176px;border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:0;background:#132238;text-decoration:none;color:#fff;box-shadow:0 14px 30px rgba(20,36,56,.18)}.sport-card:hover{box-shadow:0 18px 38px rgba(20,36,56,.25);transform:translateY(-2px)}.sport-visual{position:absolute;inset:0;overflow:hidden}.sport-visual img{width:100%;height:100%;object-fit:cover;filter:saturate(1.12) contrast(1.05)}.sport-card::before{content:"";position:absolute;inset:0;z-index:1;background:linear-gradient(90deg,rgba(9,18,31,.9),rgba(9,18,31,.52) 54%,rgba(9,18,31,.08))}.sport-card::after{content:"";position:absolute;z-index:1;right:-44px;bottom:-56px;width:170px;height:170px;border-radius:50%;background:rgba(255,255,255,.12)}.sport-copy{position:relative;z-index:2;display:grid;gap:7px;max-width:68%;padding:18px}.sport-copy strong{font-size:25px;line-height:1.08;text-shadow:0 2px 12px rgba(0,0,0,.35)}.sport-copy em{font-style:normal;color:rgba(255,255,255,.8);font-size:12px;font-weight:850}.sport-card b{position:absolute;z-index:2;left:18px;bottom:16px;width:max-content;min-height:34px;border-radius:999px;display:inline-flex;align-items:center;padding:7px 12px;background:rgba(255,255,255,.18);color:#fff;font-size:12px;backdrop-filter:blur(8px)}
    .map-board{padding:18px;background:linear-gradient(180deg,#fff,#f7fbf1)}.map-headline{margin:0 0 16px;font-size:25px;font-weight:950;line-height:1.25}.map-headline strong{color:var(--accent);font-size:38px}.map-stage{position:relative;min-height:560px;border:1px solid #d7e4cc;border-radius:8px;overflow:hidden;background:radial-gradient(circle at 38% 48%,rgba(157,207,79,.14),transparent 34%),linear-gradient(135deg,#fbfdf8,#eef7e6)}.japan-silhouette{position:absolute;left:8%;top:8%;width:54%;height:84%;filter:drop-shadow(0 9px 13px rgba(49,111,31,.22))}.japan-silhouette .country{fill:#83c945;stroke:#fff;stroke-width:1.2;stroke-linejoin:round}.japan-silhouette .outline{fill:none;stroke:rgba(49,111,31,.22);stroke-width:1.8}.map-region-buttons{position:absolute;right:22px;top:22px;z-index:2;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;width:360px}.map-region{display:grid;gap:5px;min-height:82px;padding:12px 14px;border:1px solid #cbd7e2;border-radius:8px;background:linear-gradient(rgba(255,255,255,.96),rgba(242,245,248,.94));box-shadow:0 8px 18px rgba(27,45,69,.13);color:var(--ink);text-align:center;text-decoration:none;font-weight:900;backdrop-filter:blur(3px)}.map-region strong{font-size:19px;line-height:1.2}.map-region:hover{border-color:var(--accent);box-shadow:0 12px 24px rgba(225,91,49,.18);transform:translateY(-2px)}.map-region span{color:#516680;font-size:13px;font-weight:850}
    footer{max-width:1180px;margin:0 auto;padding:0 18px 34px;color:var(--muted);font-size:13px;display:flex;gap:12px;flex-wrap:wrap}.admin-link{color:#65758a}
    @media(max-width:900px){.stats{grid-template-columns:repeat(2,minmax(0,1fr));margin-top:12px}.filters{grid-template-columns:1fr 1fr}.match-grid{grid-template-columns:1fr}.sport-grid{grid-template-columns:1fr}.hero{min-height:520px}.map-stage{min-height:520px}.japan-silhouette{left:6%;width:52%}.map-region-buttons{right:14px;width:330px;gap:10px}.map-region{min-height:78px;padding:11px 12px}.map-region strong{font-size:18px}}
    @media(max-width:760px){.map-headline{font-size:20px}.map-headline strong{font-size:30px}.map-stage{min-height:auto;padding:14px;display:grid;gap:12px}.japan-silhouette{position:relative;left:auto;top:auto;width:100%;height:auto;max-height:320px}.map-region-buttons{position:relative;right:auto;top:auto;width:auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.map-region{min-width:0}.map-region:hover{transform:translateY(-2px)}}
    @media(max-width:620px){.top{align-items:flex-start}.nav{gap:9px}.filters{grid-template-columns:1fr}.hero-inner{padding-top:70px}.metric strong{font-size:22px}}
  </style>
</head>
<body>
  <header class="topbar"><div class="top"><a class="brand" href="/"><span class="mark">CM</span><span>__SITE_NAME__</span></a><nav class="nav"><a class="login-user" href="/signin">ログイン</a><a class="signup-user" href="/representative">新規登録</a></nav></div></header>
  <section class="hero"><img src="/assets/hero-court.png" alt="屋外コートで交流する大学生グループ"><div class="shade"></div><div class="hero-inner"><p class="eyebrow">Practice Match / Circle Meetup</p><h1>練習相手も、仲間も、ここで見つかる。</h1><p class="lead">Circle Matchは、大学サークル・部活動の練習試合、合同練習、助っ人募集、交流イベントをつなぐマッチングサービスです。</p><div class="actions"><a class="button secondary hero-cta" href="#matches">募集中はこちら</a><a class="button primary hero-cta" href="/post-match">募集する</a></div></div></section>
  <main>
    <section class="stats"><div class="metric"><span>対象大学</span><strong id="uniCount">0</strong></div><div class="metric"><span>候補サークル</span><strong id="circleCount">0</strong></div><div class="metric"><span>検証済み/申請済み</span><strong id="verifiedCount">0</strong></div><div class="metric"><span>募集中</span><strong id="matchCount">0</strong></div></section>
    <section id="matches" class="section panel"><div class="panel-head"><div><h2>募集掲示板</h2><p>地域、都道府県、競技、大学名、団体名で絞り込めます。募集中が少ない時は、その条件のDB候補へ広げられます。</p></div></div><div class="filters"><input id="q" placeholder="大学名・団体名・場所で検索"><select id="regionFilter"><option value="">全地域</option></select><select id="prefFilter"><option value="">全都道府県</option></select><select id="sportFilter"><option value="">全競技</option></select><select id="typeFilter"><option value="">全募集</option><option>練習試合</option><option>合同練習</option><option>助っ人募集</option><option>大会参加者募集</option></select><select id="sortFilter"><option value="date">日時が近い順</option><option value="new">新着順</option><option value="university">大学名順</option><option value="sport">競技順</option></select></div><div id="matchList" class="match-grid" aria-live="polite"></div><div class="section-link"><a id="dbBridge" href="/circles">同じ条件でサークルDBを見る</a></div></section>
    <section class="section panel"><div class="panel-head"><div><h2>スポーツから探す</h2><p>競技を押すと、サークルDBと交流募集を同時に確認できます。</p></div></div><div class="sport-grid" id="sportGrid"></div><div class="section-link"><a href="/circles">サークルDBで候補を広げる</a></div></section>
    <section class="section panel"><div class="panel-head"><div><h2>地域から探す</h2><p>地図上の地域を押すと、募集掲示板とDB候補をその地域で絞り込めます。</p></div></div><div class="map-board"><p class="map-headline"><strong id="mapCircleCount">0</strong>件の大学サークル候補から地域で探す</p><div class="map-stage"><svg class="japan-silhouette" id="japanMap" viewBox="0 0 520 560" role="img" aria-label="日本地図"></svg><div class="map-region-buttons" id="regionGrid"></div></div></div></section>
  </main>
  <footer><span>掲載情報の訂正・削除は問い合わせページから連絡してください。</span><a class="admin-link" href="/circles">サークルDB</a><a class="admin-link" href="/terms">利用規約</a><a class="admin-link" href="/admin">管理画面</a></footer>
  <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
  <script>
    const prefs = __PREFS__;
    const regions = __REGIONS__;
    const sports = __SPORTS__;
    const popularSports = __POPULAR_SPORTS__;
    const params = new URLSearchParams(location.search);
    let allCircleCache = null;
    let allMatchCache = null;
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function fillSelect(el, values, first){el.innerHTML=`<option value="">${first}</option>`+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("")}
    function fillRegions(){ $("regionFilter").innerHTML='<option value="">全地域</option>'+regions.map(r=>`<option value="${esc(r.value)}">${esc(r.label)}</option>`).join("") }
    async function drawJapanMap(){if(!window.d3||!window.topojson)return; const svg=d3.select("#japanMap"); if(svg.select(".country").size())return; const world=await d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"); const countries=topojson.feature(world, world.objects.countries); const japan=countries.features.find(d=>String(d.id)==="392"); if(!japan)return; const projection=d3.geoMercator().fitSize([520,560],japan); const path=d3.geoPath(projection); svg.append("path").datum(japan).attr("class","country").attr("d",path); svg.append("path").datum(topojson.mesh(world, world.objects.countries, (a,b)=>String(a.id)==="392"||String(b.id)==="392")).attr("class","outline").attr("d",path)}
    function renderSports(){ $("sportGrid").innerHTML=popularSports.map(s=>`<a class="sport-card" style="--tone:${esc(s.color)}" data-code="${esc(s.code)}" href="/sports?sport=${encodeURIComponent(s.name)}"><span class="sport-visual"><img src="/assets/sports/${esc(s.image)}?v=20260706v1" alt=""></span><span class="sport-copy"><strong>${esc(s.name)}</strong><em>${esc(s.label)}</em></span><b>相手を探す</b></a>`).join("") }
    function renderRegions(circles,matches){const pos={hokkaido:"pos-hokkaido",tohoku:"pos-tohoku",kanto:"pos-kanto",chubu:"pos-chubu",kansai:"pos-kansai",chugoku_shikoku:"pos-chugoku_shikoku",kyushu:"pos-kyushu"}; $("mapCircleCount").textContent=circles.length; $("regionGrid").innerHTML=regions.map(r=>{const db=circles.filter(c=>r.prefectures.includes(c.prefecture)).length; const open=matches.filter(m=>r.prefectures.includes(m.prefecture)).length; return `<a class="map-region ${esc(pos[r.value]||"")}" href="/regions?region=${encodeURIComponent(r.value)}"><strong>${esc(r.label)}</strong><span>募集 ${open}件</span><span>DB ${db}件</span></a>`}).join("")}
    function selectedRegion(){return regions.find(r=>r.value===$("regionFilter").value)}
    function prefValues(){return selectedRegion()?.prefectures || prefs}
    function syncPrefOptions(){const current=$("prefFilter").value; fillSelect($("prefFilter"),prefValues(),selectedRegion()?`${selectedRegion().label}すべて`:"全都道府県"); if(prefValues().includes(current)) $("prefFilter").value=current}
    function currentQuery(){const qs=new URLSearchParams({q:$("q").value,prefecture:$("prefFilter").value,sport:$("sportFilter").value}); if($("regionFilter").value) qs.set("region",$("regionFilter").value); return qs}
    async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
    function updateStats(circles,matches){$("uniCount").textContent=new Set(circles.map(c=>c.university_id)).size; $("circleCount").textContent=circles.length; $("verifiedCount").textContent=circles.filter(c=>["claimed","university_verified","admin_verified"].includes(c.verification_status)).length; $("matchCount").textContent=matches.length}
    function matchesFilter(m){const q=$("q").value.trim().toLowerCase(); const blob=[m.university_name,m.circle_name,m.sport_category,m.prefecture,m.place,m.conditions,m.level_label].join(" ").toLowerCase(); if(q && !blob.includes(q))return false; if($("typeFilter").value && m.match_type!==$("typeFilter").value)return false; if($("sportFilter").value && m.sport_category!==$("sportFilter").value)return false; if($("prefFilter").value && m.prefecture!==$("prefFilter").value)return false; return true}
    function sortMatches(rows){const v=$("sortFilter").value; return rows.slice().sort((a,b)=>{if(v==="new")return String(b.created_at||"").localeCompare(String(a.created_at||"")); if(v==="university")return String(a.university_name||"").localeCompare(String(b.university_name||""),"ja"); if(v==="sport")return String(a.sport_category||"").localeCompare(String(b.sport_category||""),"ja"); return String(a.scheduled_at||"9999").localeCompare(String(b.scheduled_at||"9999"))})}
    function card(m){return `<article class="match-card"><div class="badges"><span class="badge open">${esc(m.status||"open")}</span><span class="badge type">${esc(m.match_type)}</span><span class="badge">${esc(m.sport_category||"競技未設定")}</span></div><h3>${esc(m.circle_name)}</h3><div class="meta"><span>${esc(m.university_name)} / ${esc(m.prefecture||"地域未設定")}</span><span>${esc(m.scheduled_at||"日時未定")} / ${esc(m.place||"場所未定")}</span><span>${esc(m.level_label||"レベル未設定")}</span></div><p class="tagline">${esc(m.conditions||"条件は登録後に調整します。")}</p></article>`}
    function badge(v,cls=""){return `<span class="badge ${cls}">${esc(v)}</span>`}
    async function refresh(){const qs=currentQuery(); $("dbBridge").href="/circles?"+qs; const all=await api("/api/matches?"+qs); const circles=await api("/api/circles?"+qs); if(!allCircleCache) allCircleCache=await api("/api/circles"); if(!allMatchCache) allMatchCache=await api("/api/matches"); const data=sortMatches(all.filter(matchesFilter)); renderRegions(allCircleCache,allMatchCache); updateStats(circles,data); $("matchList").innerHTML=data.map(card).join("") || `<div class="empty">現在公開中の募集はありません。同じ条件のDB候補は ${circles.length} 件あります。下のDBリンクから候補団体を確認できます。</div>`}
    async function boot(){renderSports(); drawJapanMap().catch(()=>{}); fillRegions(); fillSelect($("sportFilter"),sports,"全競技"); $("regionFilter").value=params.get("region")||""; syncPrefOptions(); $("q").value=params.get("q")||""; $("prefFilter").value=params.get("prefecture")||""; $("sportFilter").value=params.get("sport")||""; await refresh()}
    ["q","typeFilter","sportFilter","prefFilter","sortFilter"].forEach(id=>$(id).addEventListener("input",refresh));
    $("regionFilter").addEventListener("input",()=>{syncPrefOptions(); refresh()});
    boot().catch(e=>alert(e.message));
  </script>
</body>
</html>"""

SIGNIN_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ログイン | __SITE_NAME__</title>
  <style>
    :root{--ink:#17212f;--muted:#64748b;--line:#dbe4ed;--brand:#0f7a62;--accent:#e15b31}
    *{box-sizing:border-box}body{margin:0;background:#f4f7fa;color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1040px;margin:auto;padding:16px 18px;display:flex;justify-content:space-between;align-items:center;gap:12px}.brand{font-weight:900;text-decoration:none}.nav{display:flex;gap:12px;flex-wrap:wrap}.nav a{color:#31506b;text-decoration:none;font-weight:850}
    main{max-width:1040px;margin:auto;padding:38px 18px 60px;display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;padding:24px}.hero h1{font-size:36px;line-height:1.15;margin:0}.hero p,.panel p{color:var(--muted);line-height:1.8}.button{display:flex;align-items:center;justify-content:center;gap:10px;min-height:48px;border-radius:8px;padding:12px 16px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:900;text-decoration:none;cursor:pointer}.button.primary{background:var(--brand);border-color:var(--brand);color:#fff}.button.accent{background:var(--accent);border-color:var(--accent);color:#fff}.google-dot{width:20px;height:20px;border-radius:50%;background:conic-gradient(#4285f4 0 25%,#34a853 0 50%,#fbbc05 0 75%,#ea4335 0)}
    .note{margin-top:14px;border-top:1px solid var(--line);padding-top:14px;color:var(--muted);font-size:14px;line-height:1.7}.choice{display:none;gap:10px}.choice.active{display:grid}.status{margin-top:12px;padding:12px;border-radius:8px;background:#f9fbfd;color:var(--muted);line-height:1.7;font-size:14px}.status.error{background:#fff1f1;color:#a33}
    @media(max-width:760px){main{grid-template-columns:1fr}.hero h1{font-size:30px}.top{align-items:flex-start;flex-direction:column}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a href="/">募集を探す</a></nav></div></header>
  <main>
    <section class="hero"><h1>ログインして、練習試合探しを始める。</h1><p>ログイン後に、一般ユーザーとして使うか、サークル代表として登録へ進むかを選べます。閲覧だけならログイン不要です。</p></section>
    <section class="panel">
      <button id="googleButton" class="button" type="button"><span class="google-dot"></span><span>Googleでログイン</span></button>
      <div id="choice" class="choice">
        <a class="button primary" href="/">一般ユーザーとして続ける</a>
        <a class="button accent" href="/representative">サークル代表として登録する</a>
      </div>
      <p id="oauthNote" class="note">Supabase AuthでGoogle認証し、メールアドレス、ユーザーID、ログイン日時など必要最小限の情報だけを保存します。</p>
      <div id="status" class="status">ログイン状態を確認しています。</div>
    </section>
  </main>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
  <script>
    const supabaseUrl = __SUPABASE_URL__;
    const supabaseAnonKey = __SUPABASE_ANON_KEY__;
    const authReady = __AUTH_READY__;
    const statusEl = document.getElementById("status");
    const choiceEl = document.getElementById("choice");
    const loginButton = document.getElementById("googleButton");
    function setStatus(text, error=false){statusEl.textContent=text; statusEl.className=error?"status error":"status"}
    async function syncSession(client, session){
      if(!session?.access_token) return null;
      const res = await fetch("/api/auth/supabase", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({access_token:session.access_token})});
      const data = await res.json();
      if(!res.ok) throw new Error(data.error || "ログイン同期に失敗しました");
      return data.user;
    }
    async function boot(){
      if(!authReady){
        loginButton.disabled = true;
        setStatus("SupabaseのURL/Anon Keyが未設定です。Renderの環境変数を入れると、このボタンから実ログインできます。", true);
        return;
      }
      const client = window.supabase.createClient(supabaseUrl, supabaseAnonKey);
      const { data } = await client.auth.getSession();
      if(data.session){
        const user = await syncSession(client, data.session);
        loginButton.style.display = "none";
        choiceEl.classList.add("active");
        setStatus(`${user?.email || "ログイン済み"} でログインしています。利用方法を選んでください。`);
      }else{
        setStatus("Googleアカウントでログインしてください。");
      }
      loginButton.onclick = async () => {
        setStatus("Googleログインへ移動します。");
        const redirectTo = `${location.origin}/signin`;
        const { error } = await client.auth.signInWithOAuth({provider:"google", options:{redirectTo, queryParams:{prompt:"select_account"}}});
        if(error) setStatus(error.message, true);
      };
    }
    boot().catch(err=>setStatus(err.message, true));
  </script>
</body>
</html>"""

SPORT_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__SPORT__ | __SITE_NAME__</title>
  <style>
    :root{--ink:#17212f;--muted:#64748b;--line:#dbe4ed;--paper:#fff;--soft:#f4f7fa;--brand:#0f7a62;--accent:#e15b31;--blue:#2767a5}
    *{box-sizing:border-box}body{margin:0;background:var(--soft);color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1180px;margin:auto;padding:16px 18px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.brand{font-weight:900;text-decoration:none}.nav{display:flex;align-items:center;gap:14px;flex-wrap:wrap}.nav a{display:inline-flex;align-items:center;justify-content:center;min-height:42px;color:#31506b;text-decoration:none;font-weight:850;line-height:1}.nav a.find-link{border-radius:8px;padding:10px 14px;background:var(--accent);color:#fff}
    main{max-width:1180px;margin:auto;padding:24px 18px 54px}.hero{display:grid;grid-template-columns:1fr auto;gap:16px;align-items:end;margin-bottom:14px}.hero h1{font-size:38px;margin:0 0 8px}.hero p{margin:0;color:var(--muted);line-height:1.75}.button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;border-radius:8px;padding:10px 14px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:900;text-decoration:none}.button.primary{background:var(--accent);color:#fff;border-color:transparent}
    .stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:900}.metric strong{display:block;margin-top:6px;font-size:27px}
    .grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:14px}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.db-panel{position:relative}.panel h2{margin:0;padding:16px;border-bottom:1px solid var(--line);font-size:21px}.region-list,.area-list{display:grid;gap:8px;padding:14px}.region-list{grid-template-columns:repeat(2,minmax(0,1fr));border-bottom:1px solid var(--line);background:#f9fbfd}.region-button,.area{border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink);font:inherit;cursor:pointer}.region-button{padding:10px;text-align:left}.region-button.active,.area.active{border-color:var(--accent);box-shadow:0 0 0 2px rgba(225,91,49,.14)}.region-button b{display:block}.region-button span{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.area{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px;background:#fafcff;text-align:left}.area b{font-size:16px}.badge{display:inline-flex;border-radius:999px;background:#edf2f7;color:#405164;min-height:23px;padding:3px 8px;font-size:12px;font-weight:900}.badge.ok{background:#e2f5ed;color:#0d674f}.table-tools{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border-bottom:1px solid var(--line);color:var(--muted);font-size:13px;font-weight:850}.filter-menu{position:absolute;z-index:5;right:12px;top:100px;width:min(360px,calc(100% - 24px));background:#fff;border:1px solid #cbd7e2;border-radius:8px;box-shadow:0 18px 42px rgba(23,33,47,.18);padding:12px;display:grid;gap:10px}.filter-menu.hidden{display:none}.filter-menu strong{font-size:14px}.filter-actions,.choice-grid{display:flex;gap:7px;flex-wrap:wrap}.filter-menu button,.th-filter{font:inherit;cursor:pointer}.filter-menu button{border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--ink);min-height:31px;padding:5px 10px;font-size:12px;font-weight:900}.filter-menu button.active,.filter-menu button:hover{border-color:var(--accent);color:#b8421e;background:#fff6f2}.tablewrap{overflow:auto;max-height:680px}input,select{width:100%;border:1px solid #c8d4df;border-radius:8px;min-height:38px;padding:8px 10px;font:inherit;background:#fff;color:var(--ink)}table{width:100%;border-collapse:collapse;font-size:14px;min-width:720px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{position:sticky;top:0;background:#f8fbfd;color:var(--muted);font-size:12px}.th-filter{display:inline-flex;align-items:center;gap:6px;border:0;background:transparent;color:inherit;padding:0;font-weight:900}.th-filter svg{width:13px;height:13px;stroke:currentColor;stroke-width:2;fill:none}.th-filter.active{color:var(--accent)}.name{font-weight:900}.sub{display:block;color:var(--muted);font-size:12px;margin-top:3px}.empty{padding:18px;color:var(--muted);line-height:1.7}footer{max-width:1180px;margin:0 auto;padding:0 18px 38px;color:var(--muted);font-size:13px;display:flex;gap:12px;flex-wrap:wrap}.admin-link{color:#65758a}
    @media(max-width:860px){.hero,.grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr}.hero h1{font-size:31px}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a class="find-link" href="/">トップへ戻る</a><a href="/post-match">募集する</a><a href="/representative">DBへの登録依頼はこちら</a><a href="/signin">ログイン</a></nav></div></header>
  <main>
    <section class="hero"><div><h1>__SPORT__の相手を探す</h1><p>__SPORT__サークルDBと練習試合・交流募集をまとめて確認できます。</p></div><a class="button primary" href="/post-match">募集する</a></section>
    <section class="stats"><div class="metric"><span>サークル</span><strong id="circleCount">0</strong></div><div class="metric"><span>交流募集</span><strong id="matchCount">0</strong></div><div class="metric"><span>対象都道府県</span><strong id="prefCount">0</strong></div></section>
    <section class="grid"><aside class="panel"><h2>地域別の交流募集</h2><div id="regionList" class="region-list"></div><div id="areaList" class="area-list"></div></aside><section class="panel db-panel"><h2>__SPORT__サークルDB</h2><div class="table-tools"><span><strong id="visibleCircleCount">0</strong> 件を表示</span><span id="activeFilterText"></span></div><div id="filterMenu" class="filter-menu hidden"></div><div class="tablewrap"><table><thead><tr><th><button class="th-filter" data-filter="university">大学 <svg viewBox="0 0 24 24"><path d="M4 5h16l-6 7v5l-4 2v-7z"/></svg></button></th><th><button class="th-filter" data-filter="circle">団体名 <svg viewBox="0 0 24 24"><path d="M4 5h16l-6 7v5l-4 2v-7z"/></svg></button></th><th>登録済み</th><th><button class="th-filter" data-filter="type">種別 <svg viewBox="0 0 24 24"><path d="M4 5h16l-6 7v5l-4 2v-7z"/></svg></button></th><th><button class="th-filter" data-filter="source">出典 <svg viewBox="0 0 24 24"><path d="M4 5h16l-6 7v5l-4 2v-7z"/></svg></button></th></tr></thead><tbody id="circleRows"></tbody></table></div></section></section>
  </main>
  <footer><span>候補を広げたい場合は</span><a class="admin-link" href="/circles">サークルDBを見る</a><a class="admin-link" href="/contact">問い合わせ</a></footer>
  <script>
    const sport = __SPORT_JSON__;
    const params = new URLSearchParams(location.search);
    let selectedRegion = params.get("region") || "";
    let selectedPrefecture = params.get("prefecture") || "";
    let currentCircles = [];
    let columnFilters = {university:"", circle:"", type:"", source:"", sort:"university"};
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function statusLabel(v){return ({university_verified:"公式確認済み",admin_verified:"運営確認済み",claimed:"申請済み",unverified:"未確認"}[v] || v)}
    function sourceLabel(v){return ({university_official:"大学公式",self_registered:"本人登録",public_sns:"SNS等",other:"その他"}[v] || v)}
    function badge(v,cls=""){return `<span class="badge ${cls}">${esc(v)}</span>`}
    async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
    function rowValue(c,key){return key==="university"?`${c.university_name||""} ${c.prefecture||""} ${c.city||""}`:key==="circle"?c.circle_name||"":key==="type"?c.organization_type||"不明":key==="source"?c.source_type||"":""}
    function displayValue(key,value){if(!value)return "すべて"; if(key==="source")return sourceLabel(value); return value}
    function sortCircles(rows){const v=columnFilters.sort; return rows.slice().sort((a,b)=>{if(v==="circle")return String(a.circle_name||"").localeCompare(String(b.circle_name||""),"ja"); if(v==="type")return String(a.organization_type||"").localeCompare(String(b.organization_type||""),"ja"); if(v==="source")return String(a.source_type||"").localeCompare(String(b.source_type||""),"ja"); return String(a.university_name||"").localeCompare(String(b.university_name||""),"ja")})}
    function updateFilterButtons(){document.querySelectorAll("[data-filter]").forEach(b=>{const key=b.dataset.filter; b.classList.toggle("active",!!columnFilters[key]||columnFilters.sort===key)}); const labels={university:"大学",circle:"団体名",type:"種別",source:"出典"}; const active=Object.keys(labels).filter(k=>columnFilters[k]).map(k=>`${labels[k]}: ${displayValue(k,columnFilters[k])}`); $("activeFilterText").textContent=active.length?active.join(" / "):""}
    function renderCircleRows(){const filtered=sortCircles(currentCircles.filter(c=>{if(columnFilters.university&&!rowValue(c,"university").toLowerCase().includes(columnFilters.university.toLowerCase()))return false; if(columnFilters.circle&&!rowValue(c,"circle").toLowerCase().includes(columnFilters.circle.toLowerCase()))return false; if(columnFilters.type&&rowValue(c,"type")!==columnFilters.type)return false; if(columnFilters.source&&rowValue(c,"source")!==columnFilters.source)return false; return true})); $("visibleCircleCount").textContent=filtered.length; $("circleRows").innerHTML=filtered.map(c=>`<tr><td><span class="name">${esc(c.university_name)}</span><span class="sub">${esc(c.prefecture)} ${esc(c.city||"")}</span></td><td><span class="name">${esc(c.circle_name)}</span></td><td>${c.profile_url?`<a href="${esc(c.profile_url)}">URL</a>`:""}</td><td>${badge(c.organization_type||"不明")}</td><td>${badge(sourceLabel(c.source_type))}${c.source_url?`<span class="sub"><a href="${esc(c.source_url)}" target="_blank">出典URL</a></span>`:""}</td></tr>`).join("") || `<tr><td colspan="5" class="empty">データなし</td></tr>`; updateFilterButtons()}
    function uniqueValues(key){return [...new Set(currentCircles.map(c=>rowValue(c,key)).filter(Boolean))].sort((a,b)=>String(displayValue(key,a)).localeCompare(String(displayValue(key,b)),"ja"))}
    function openFilterMenu(key){const labels={university:"大学",circle:"団体名",type:"種別",source:"出典"}; const textFilter=["university","circle"].includes(key); const choices=textFilter?`<input id="columnFilterInput" value="${esc(columnFilters[key])}" placeholder="${esc(labels[key])}で絞り込み">`:`<div class="choice-grid"><button data-choice="" class="${!columnFilters[key]?"active":""}">すべて</button>${uniqueValues(key).map(v=>`<button data-choice="${esc(v)}" class="${columnFilters[key]===v?"active":""}">${esc(displayValue(key,v))}</button>`).join("")}</div>`; $("filterMenu").innerHTML=`<strong>${esc(labels[key])}</strong>${choices}<div class="filter-actions"><button data-sort="${esc(key)}" class="${columnFilters.sort===key?"active":""}">昇順に並べる</button><button data-clear="${esc(key)}">クリア</button></div>`; $("filterMenu").classList.remove("hidden"); if(textFilter){$("columnFilterInput").addEventListener("input",e=>{columnFilters[key]=e.target.value.trim(); renderCircleRows()})} document.querySelectorAll("[data-choice]").forEach(b=>b.onclick=()=>{columnFilters[key]=b.dataset.choice; renderCircleRows(); openFilterMenu(key)}); document.querySelector("[data-sort]").onclick=()=>{columnFilters.sort=key; renderCircleRows(); openFilterMenu(key)}; document.querySelector("[data-clear]").onclick=()=>{columnFilters[key]=""; renderCircleRows(); openFilterMenu(key)}}
    function regionButton(r){return `<button class="region-button ${r.value===selectedRegion?"active":""}" data-region="${esc(r.value)}"><b>${esc(r.label)}</b><span>${badge(`${r.match_count}件`,r.match_count>0?"ok":"")}${badge(`DB ${r.circle_count}件`)}</span></button>`}
    function areaButton(a){return `<button class="area ${a.prefecture===selectedPrefecture?"active":""}" data-prefecture="${esc(a.prefecture)}"><b>${esc(a.prefecture)}</b><span>${badge(`${a.match_count}件`,a.match_count>0?"ok":"")}${badge(`DB ${a.circle_count}件`)}</span></button>`}
    async function boot(){const regionQs=selectedRegion?`&region=${encodeURIComponent(selectedRegion)}`:""; const prefQs=selectedPrefecture?`&prefecture=${encodeURIComponent(selectedPrefecture)}`:""; const data=await api(`/api/sport_overview?sport=${encodeURIComponent(sport)}${regionQs}${prefQs}`); selectedPrefecture=data.prefecture||""; currentCircles=data.circles; $("circleCount").textContent=data.circle_count; $("matchCount").textContent=data.match_count; $("prefCount").textContent=data.areas.filter(a=>a.circle_count||a.match_count).length; $("regionList").innerHTML=data.regions.map(regionButton).join(""); $("areaList").innerHTML=data.areas.map(areaButton).join("") || `<div class="empty">この地域の募集・DB候補はまだありません。</div>`; renderCircleRows(); document.querySelectorAll("[data-region]").forEach(b=>b.onclick=()=>{selectedRegion=b.dataset.region; selectedPrefecture=""; const next=new URL(location.href); if(selectedRegion) next.searchParams.set("region",selectedRegion); else next.searchParams.delete("region"); next.searchParams.delete("prefecture"); history.replaceState(null,"",next); boot().catch(e=>alert(e.message));}); document.querySelectorAll("[data-prefecture]").forEach(b=>b.onclick=()=>{selectedPrefecture=b.dataset.prefecture; const next=new URL(location.href); next.searchParams.set("prefecture",selectedPrefecture); history.replaceState(null,"",next); boot().catch(e=>alert(e.message));});}
    document.querySelectorAll("[data-filter]").forEach(b=>b.addEventListener("click",e=>{e.stopPropagation(); openFilterMenu(b.dataset.filter)}));
    document.addEventListener("click",e=>{if(!$("filterMenu").contains(e.target)&&!e.target.closest("[data-filter]"))$("filterMenu").classList.add("hidden")});
    boot().catch(e=>alert(e.message));
  </script>
</body>
</html>"""

REGION_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__REGION_LABEL__ | __SITE_NAME__</title>
  <style>
    :root{--ink:#17212f;--muted:#64748b;--line:#dbe4ed;--soft:#f4f7fa;--accent:#e15b31;--brand:#0f7a62}
    *{box-sizing:border-box}body{margin:0;background:var(--soft);color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1180px;margin:auto;padding:16px 18px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.brand{font-weight:900;text-decoration:none}.nav{display:flex;align-items:center;gap:14px;flex-wrap:wrap}.nav a{display:inline-flex;align-items:center;justify-content:center;min-height:42px;color:#31506b;text-decoration:none;font-weight:850;line-height:1}.nav a.find-link{border-radius:8px;padding:10px 14px;background:var(--accent);color:#fff}
    main{max-width:1180px;margin:auto;padding:24px 18px 54px}.hero{display:grid;grid-template-columns:1fr auto;gap:16px;align-items:end;margin-bottom:14px}.hero h1{font-size:38px;margin:0 0 8px}.hero p{margin:0;color:var(--muted);line-height:1.75}.button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;border-radius:8px;padding:10px 14px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:900;text-decoration:none}.button.primary{background:var(--accent);color:#fff;border-color:transparent}
    .stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:900}.metric strong{display:block;margin-top:6px;font-size:27px}
    .grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:14px}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.panel h2{margin:0;padding:16px;border-bottom:1px solid var(--line);font-size:21px}.sport-list,.area-list{display:grid;gap:8px;padding:14px}.sport-list{grid-template-columns:repeat(2,minmax(0,1fr));border-bottom:1px solid var(--line);background:#f9fbfd}.sport-button,.area{border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink);font:inherit;cursor:pointer}.sport-button{padding:10px;text-align:left}.sport-button.active,.area.active{border-color:var(--accent);box-shadow:0 0 0 2px rgba(225,91,49,.14)}.sport-button b{display:block}.sport-button span{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.area{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px;background:#fafcff;text-align:left}.area b{font-size:16px}.badge{display:inline-flex;border-radius:999px;background:#edf2f7;color:#405164;min-height:23px;padding:3px 8px;font-size:12px;font-weight:900}.badge.ok{background:#e2f5ed;color:#0d674f}.match-list{display:grid;gap:10px;padding:14px}.match-card{border:1px solid var(--line);border-radius:8px;padding:13px;background:#fff}.match-card h3{margin:6px 0 8px;font-size:17px}.meta{display:grid;gap:4px;color:var(--muted);font-size:13px}.empty{padding:18px;color:var(--muted);line-height:1.7}.table-tools{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border-bottom:1px solid var(--line);color:var(--muted);font-size:13px;font-weight:850}.tablewrap{overflow:auto;max-height:520px}table{width:100%;border-collapse:collapse;font-size:14px;min-width:680px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{position:sticky;top:0;background:#f8fbfd;color:var(--muted);font-size:12px}.name{font-weight:900}.sub{display:block;color:var(--muted);font-size:12px;margin-top:3px}.right-stack{display:grid;gap:14px}footer{max-width:1180px;margin:0 auto;padding:0 18px 38px;color:var(--muted);font-size:13px;display:flex;gap:12px;flex-wrap:wrap}.admin-link{color:#65758a}
    @media(max-width:860px){.hero,.grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr}.hero h1{font-size:31px}.sport-list{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a class="find-link" href="/">トップへ戻る</a><a href="/post-match">募集する</a><a href="/representative">DBへの登録依頼はこちら</a><a href="/signin">ログイン</a></nav></div></header>
  <main>
    <section class="hero"><div><h1>__REGION_LABEL__の相手を探す</h1><p>__REGION_LABEL__の練習試合・交流募集を、スポーツ別・都道府県別に確認できます。</p></div><a class="button primary" href="/post-match">募集する</a></section>
    <section class="stats"><div class="metric"><span>サークル</span><strong id="circleCount">0</strong></div><div class="metric"><span>交流募集</span><strong id="matchCount">0</strong></div><div class="metric"><span>対象競技</span><strong id="sportCount">0</strong></div></section>
    <section class="grid"><aside class="panel"><h2>スポーツ別の交流募集</h2><div id="sportList" class="sport-list"></div><div id="areaList" class="area-list"></div></aside><section class="right-stack"><div class="panel"><h2>交流募集</h2><div id="matchList" class="match-list"></div></div><div class="panel"><h2>__REGION_LABEL__サークルDB</h2><div class="table-tools"><span><strong id="visibleCircleCount">0</strong> 件を表示</span><a id="dbLink" class="admin-link" href="/circles">DBで詳しく見る</a></div><div class="tablewrap"><table><thead><tr><th>大学</th><th>団体名</th><th>登録済み</th><th>種別</th><th>競技</th></tr></thead><tbody id="circleRows"></tbody></table></div></div></section></section>
  </main>
  <footer><span>他の条件で探す場合は</span><a class="admin-link" href="/">トップへ戻る</a><a class="admin-link" href="/circles">サークルDBを見る</a></footer>
  <script>
    const region = __REGION_JSON__;
    const params = new URLSearchParams(location.search);
    let selectedSport = params.get("sport") || "";
    let selectedPrefecture = params.get("prefecture") || "";
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function badge(v,cls=""){return `<span class="badge ${cls}">${esc(v)}</span>`}
    async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
    function sportButton(s){return `<button class="sport-button ${s.name===selectedSport?"active":""}" data-sport="${esc(s.name)}"><b>${esc(s.name || "すべて")}</b><span>${badge(`${s.match_count}件`,s.match_count>0?"ok":"")}${badge(`DB ${s.circle_count}件`)}</span></button>`}
    function areaButton(a){return `<button class="area ${a.prefecture===selectedPrefecture?"active":""}" data-prefecture="${esc(a.prefecture)}"><b>${esc(a.prefecture)}</b><span>${badge(`${a.match_count}件`,a.match_count>0?"ok":"")}${badge(`DB ${a.circle_count}件`)}</span></button>`}
    function matchCard(m){return `<article class="match-card"><div>${badge(m.status||"open","ok")} ${badge(m.match_type)} ${badge(m.sport_category||"競技未設定")}</div><h3>${esc(m.circle_name)}</h3><div class="meta"><span>${esc(m.university_name)} / ${esc(m.prefecture||"地域未設定")}</span><span>${esc(m.scheduled_at||"日時未定")} / ${esc(m.place||"場所未定")}</span><span>${esc(m.level_label||"レベル未設定")}</span></div></article>`}
    function circleRow(c){return `<tr><td><span class="name">${esc(c.university_name)}</span><span class="sub">${esc(c.prefecture)} ${esc(c.city||"")}</span></td><td><span class="name">${esc(c.circle_name)}</span></td><td>${c.profile_url?`<a href="${esc(c.profile_url)}">URL</a>`:""}</td><td>${badge(c.organization_type||"不明")}</td><td>${esc(c.sport_category||"その他")}</td></tr>`}
    function updateUrl(){const next=new URL(location.href); next.searchParams.set("region",region); if(selectedSport)next.searchParams.set("sport",selectedSport); else next.searchParams.delete("sport"); if(selectedPrefecture)next.searchParams.set("prefecture",selectedPrefecture); else next.searchParams.delete("prefecture"); history.replaceState(null,"",next)}
    async function boot(){updateUrl(); const qs=new URLSearchParams({region}); if(selectedSport)qs.set("sport",selectedSport); if(selectedPrefecture)qs.set("prefecture",selectedPrefecture); const data=await api(`/api/region_overview?${qs}`); selectedPrefecture=data.prefecture||""; $("circleCount").textContent=data.circle_count; $("matchCount").textContent=data.match_count; $("sportCount").textContent=data.sports.filter(s=>s.circle_count||s.match_count).length; $("sportList").innerHTML=[{name:"",circle_count:data.region_circle_count,match_count:data.region_match_count},...data.sports].map(sportButton).join(""); $("areaList").innerHTML=data.areas.map(areaButton).join("") || `<div class="empty">この地域の候補はまだありません。</div>`; $("matchList").innerHTML=data.matches.map(matchCard).join("") || `<div class="empty">現在公開中の募集はありません。同じ条件のDB候補は ${data.circle_count} 件あります。</div>`; $("visibleCircleCount").textContent=data.circles.length; $("circleRows").innerHTML=data.circles.map(circleRow).join("") || `<tr><td colspan="5" class="empty">データなし</td></tr>`; const dbQs=new URLSearchParams({region}); if(selectedSport)dbQs.set("sport",selectedSport); if(selectedPrefecture)dbQs.set("prefecture",selectedPrefecture); $("dbLink").href="/circles?"+dbQs; document.querySelectorAll("[data-sport]").forEach(b=>b.onclick=()=>{selectedSport=b.dataset.sport; selectedPrefecture=""; boot().catch(e=>alert(e.message))}); document.querySelectorAll("[data-prefecture]").forEach(b=>b.onclick=()=>{selectedPrefecture=b.dataset.prefecture; boot().catch(e=>alert(e.message))})}
    boot().catch(e=>alert(e.message));
  </script>
</body>
</html>"""

POST_MATCH_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>募集する | __SITE_NAME__</title>
  <style>
    :root{--ink:#17212f;--muted:#64748b;--line:#dbe4ed;--soft:#f4f7fa;--accent:#e15b31;--brand:#0f7a62}
    *{box-sizing:border-box}body{margin:0;background:var(--soft);color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1120px;margin:auto;padding:16px 18px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.brand{font-weight:900;text-decoration:none}.nav{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.nav a{color:#31506b;text-decoration:none;font-weight:850}.nav a.db-request{margin-left:auto;border:1px solid var(--line);border-radius:8px;padding:9px 12px;background:#fff}
    main{max-width:1120px;margin:auto;padding:28px 18px 60px}.hero{display:grid;grid-template-columns:1fr auto;gap:16px;align-items:end;margin-bottom:14px}.hero h1{font-size:36px;line-height:1.15;margin:0 0 10px}.hero p{margin:0;color:var(--muted);line-height:1.8;max-width:760px}.button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;border-radius:8px;padding:10px 14px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:900;text-decoration:none;cursor:pointer}.button.primary{background:var(--accent);border-color:var(--accent);color:#fff}.button.ghost{background:#fff;color:var(--accent);border-color:var(--accent)}
    .layout{display:grid;grid-template-columns:.92fr 1.08fr;gap:14px}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.panel h2{margin:0;padding:16px;border-bottom:1px solid var(--line);font-size:21px}.panel-body{padding:16px}.search-row{display:grid;gap:8px}.circle-list{display:grid;gap:8px;margin-top:12px;max-height:520px;overflow:auto}.circle-option{border:1px solid var(--line);border-radius:8px;background:#fff;text-align:left;padding:12px;cursor:pointer;color:var(--ink)}.circle-option:hover,.circle-option.active{border-color:var(--accent);box-shadow:0 0 0 2px rgba(225,91,49,.14)}.circle-option b{display:block;font-size:16px}.sub{display:block;margin-top:4px;color:var(--muted);font-size:13px;line-height:1.45}.badge{display:inline-flex;border-radius:999px;background:#edf2f7;color:#405164;min-height:23px;padding:3px 8px;font-size:12px;font-weight:900;margin-top:8px}.selected{margin-top:12px;border-radius:8px;background:#f9fbfd;border:1px solid var(--line);padding:12px;color:#405164;line-height:1.7}
    form{display:grid;gap:13px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}label{display:grid;gap:6px;font-weight:850}small{color:var(--muted);font-weight:500;line-height:1.5}input,select,textarea{width:100%;border:1px solid #cbd7e2;border-radius:8px;min-height:42px;padding:10px 11px;font:inherit;background:#fff;color:var(--ink)}textarea{min-height:98px;resize:vertical}.result{display:none;border-radius:8px;padding:12px 14px;background:#e2f5ed;color:#0d674f;font-weight:850;line-height:1.7}.result.error{background:#fde8e4;color:#9b2f1a}.notice{border:1px solid #f2d0bd;background:#fff8f4;color:#7c3a20;border-radius:8px;padding:12px;line-height:1.7;font-size:14px}.login-needed{display:none}
    @media(max-width:860px){.layout,.hero,.form-grid{grid-template-columns:1fr}.hero h1{font-size:30px}.top{align-items:flex-start}.nav a.db-request{margin-left:0}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a href="/">募集中を見る</a><a href="/circles">サークルDB</a><a class="db-request" href="/representative">DBへの登録依頼はこちら</a><a href="/signin">ログイン</a></nav></div></header>
  <main>
    <section class="hero"><div><h1>練習試合・交流募集を出す</h1><p>まず自分のサークルをDBから検索して選び、募集したい期間・練習内容・場所・条件を登録します。DBにない場合は右上の登録依頼から申請してください。</p></div><a class="button ghost" href="/representative">DBへの登録依頼はこちら</a></section>
    <section id="loginNeeded" class="notice login-needed">募集を投稿するにはログインが必要です。<a href="/signin">ログイン / 新規登録</a> してから投稿してください。</section>
    <section class="layout">
      <aside class="panel"><h2>自分のサークルを検索</h2><div class="panel-body"><div class="search-row"><input id="circleSearch" placeholder="大学名・団体名・競技で検索"><select id="sportFilter"><option value="">全競技</option></select></div><div id="circleList" class="circle-list"></div><div id="selectedCircle" class="selected">サークルを選択してください。</div></div></aside>
      <section class="panel"><h2>募集内容</h2><div class="panel-body">
        <form id="matchForm">
          <div class="form-grid"><label>募集種別<select id="matchType" required><option>練習試合</option><option>合同練習</option><option>助っ人募集</option><option>交流イベント</option><option>大会参加者募集</option></select></label><label>レベル感<select id="levelLabel"><option value="">選択してください</option><option>初心者歓迎</option><option>ゆるめ</option><option>中級</option><option>経験者中心</option><option>競技志向</option></select></label></div>
          <div class="form-grid"><label>募集開始日<small>この日以降で相手を探す</small><input id="periodStart" type="date" required></label><label>募集終了日<small>この日までに実施したい</small><input id="periodEnd" type="date" required></label></div>
          <div class="form-grid"><label>場所<small>キャンパス、体育館、グラウンド、地域など</small><input id="place" required placeholder="例: 東京都内体育館、大学グラウンド"></label><label>希望人数・形式<small>任意</small><input id="capacity" placeholder="例: 5対5、10人程度、1チーム"></label></div>
          <label>何の練習をしたいか<small>例: 練習試合、基礎練、ゲーム形式、合同練習、助っ人募集など</small><textarea id="practiceDetail" required placeholder="例: 週末にフットサルの練習試合をしたいです。経験者多めですが、楽しく交流できる相手を探しています。"></textarea></label>
          <label>相手への条件・補足<small>費用、持ち物、雨天時、連絡方法、希望する相手のレベルなど</small><textarea id="conditions" placeholder="例: コート代折半、男女ミックス可、日程はDMで調整したいです。"></textarea></label>
          <div id="result" class="result"></div>
          <button class="button primary" type="submit">募集を投稿する</button>
        </form>
      </div></section>
    </section>
  </main>
  <script>
    const sports = __SPORTS__;
    const $ = id => document.getElementById(id);
    let circles = [];
    let selectedCircle = null;
    let authenticated = false;
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    async function api(path, options){const r=await fetch(path, options); const data=await r.json(); if(!r.ok)throw new Error(data.error||"通信に失敗しました"); return data}
    function fillSports(){ $("sportFilter").innerHTML='<option value="">全競技</option>'+sports.map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join("") }
    function renderCircles(){const q=$("circleSearch").value.trim().toLowerCase(); const sport=$("sportFilter").value; const rows=circles.filter(c=>{const blob=[c.university_name,c.circle_name,c.sport_category,c.prefecture,c.city].join(" ").toLowerCase(); if(q && !blob.includes(q))return false; if(sport && c.sport_category!==sport)return false; return true}).slice(0,80); $("circleList").innerHTML=rows.map(c=>`<button type="button" class="circle-option ${selectedCircle?.circle_id===c.circle_id?"active":""}" data-circle="${esc(c.circle_id)}"><b>${esc(c.circle_name)}</b><span class="sub">${esc(c.university_name)} / ${esc(c.prefecture)} ${esc(c.city||"")} / ${esc(c.sport_category||"競技未設定")}</span><span class="badge">${esc(c.organization_type||"不明")}</span></button>`).join("") || `<div class="selected">候補が見つかりません。DBへの登録依頼をしてください。</div>`; document.querySelectorAll("[data-circle]").forEach(b=>b.onclick=()=>selectCircle(b.dataset.circle))}
    function selectCircle(id){selectedCircle=circles.find(c=>c.circle_id===id); if(!selectedCircle)return; $("selectedCircle").innerHTML=`<b>${esc(selectedCircle.circle_name)}</b><span class="sub">${esc(selectedCircle.university_name)} / ${esc(selectedCircle.prefecture)} / ${esc(selectedCircle.sport_category||"")}</span>`; if(selectedCircle.sport_category) $("sportFilter").value=selectedCircle.sport_category; renderCircles()}
    async function boot(){fillSports(); const me=await api("/api/me"); authenticated=!!me.authenticated; $("loginNeeded").style.display=authenticated?"none":"block"; circles=await api("/api/circles"); renderCircles()}
    ["circleSearch","sportFilter"].forEach(id=>$(id).addEventListener("input",renderCircles));
    $("matchForm").addEventListener("submit",async e=>{e.preventDefault(); const result=$("result"); result.style.display="block"; result.className="result"; try{if(!authenticated)throw new Error("募集投稿にはログインが必要です。"); if(!selectedCircle)throw new Error("自分のサークルを選択してください。"); const payload={circle_id:selectedCircle.circle_id,match_type:$("matchType").value,level_label:$("levelLabel").value,period_start:$("periodStart").value,period_end:$("periodEnd").value,place:$("place").value,capacity:$("capacity").value,practice_detail:$("practiceDetail").value,conditions:$("conditions").value}; result.textContent="投稿中です"; const data=await api("/api/matches/public",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); result.innerHTML=`募集を投稿しました。投稿ID: ${esc(data.match_post_id)}<br><a href="/?q=${encodeURIComponent(selectedCircle.circle_name)}#matches">募集掲示板で確認する</a>`; e.target.reset()}catch(err){result.className="result error"; result.textContent=err.message}})
    boot().catch(e=>{const r=$("result"); r.style.display="block"; r.className="result error"; r.textContent=e.message});
  </script>
</body>
</html>"""

REPRESENTATIVE_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>サークル代表登録 | __SITE_NAME__</title>
  <style>
    :root{--ink:#17212f;--muted:#64748b;--line:#dbe4ed;--brand:#0f7a62;--accent:#e15b31;--soft:#f4f7fa}
    *{box-sizing:border-box}body{margin:0;background:var(--soft);color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1120px;margin:auto;padding:16px 18px;display:flex;justify-content:space-between;align-items:center;gap:12px}.brand{font-weight:900;text-decoration:none}.nav{display:flex;gap:12px;flex-wrap:wrap}.nav a{color:#31506b;text-decoration:none;font-weight:850}
    main{max-width:1120px;margin:auto;padding:26px 18px 60px}.intro{display:grid;grid-template-columns:1.05fr .95fr;gap:14px;margin-bottom:14px}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;padding:22px}.intro h1{font-size:34px;line-height:1.18;margin:0 0 10px}.intro p,.help p{color:var(--muted);line-height:1.8;margin:0}.steps{display:grid;gap:9px}.step{border:1px solid var(--line);border-radius:8px;padding:12px;background:#f9fbfd}.step b{display:block;margin-bottom:4px}
    form{display:grid;gap:14px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}label{display:grid;gap:6px;font-weight:850}small{color:var(--muted);font-weight:500}input,select,textarea{width:100%;border:1px solid #cbd7e2;border-radius:8px;min-height:42px;padding:10px 11px;font:inherit;background:#fff;color:var(--ink)}textarea{min-height:96px;resize:vertical}.button{display:inline-flex;align-items:center;justify-content:center;min-height:46px;border-radius:8px;padding:11px 16px;border:1px solid transparent;background:var(--accent);color:#fff;font-weight:900;text-decoration:none;cursor:pointer}.ghost{background:#fff;color:var(--ink);border-color:var(--line)}.actions{display:flex;gap:10px;flex-wrap:wrap}.result{display:none;border-radius:8px;padding:12px 14px;background:#e2f5ed;color:#0d674f;font-weight:850}.result.error{background:#fde8e4;color:#9b2f1a}
    @media(max-width:820px){.intro,.form-grid{grid-template-columns:1fr}.top{align-items:flex-start;flex-direction:column}.intro h1{font-size:29px}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a href="/">募集を探す</a><a href="/signin">ログイン</a><a href="/contact">問い合わせ</a></nav></div></header>
  <main>
    <section class="intro"><article class="panel"><h1>自分が所属するサークルを登録しよう！</h1><p>代表者が簡単なアンケートに答えるだけで、サークル紹介ページを自動作成します。大学メールは本人確認のためだけに使い、公開ページには表示しません。</p></article><aside class="steps"><div class="step"><b>1. 団体情報を入力</b>大学、団体名、競技、公式ページやSNSなどの出典を登録します。</div><div class="step"><b>2. 紹介アンケートに回答</b>人数、雰囲気、経験者割合、練習頻度などを入力します。</div><div class="step"><b>3. サークルページを公開</b>登録済みDBから紹介ページへ遷移できるようにします。</div></aside></section>
    <section class="panel">
      <form id="claimForm">
        <div class="form-grid"><label>大学<select id="universityId" required></select></label><label>団体名<input id="circleName" required placeholder="例: フットサル同好会"></label></div>
        <div class="form-grid"><label>競技<select id="sportCategory"></select></label><label>団体種別<select id="organizationType"></select></label></div>
        <div class="form-grid"><label>代表者名<small>公開されません</small><input id="claimantName" required></label><label>大学メール<small>公開されません</small><input id="claimantEmail" type="email" required placeholder="name@university.ac.jp"></label></div>
        <label>出典URL<small>大学公式ページ、団体公式SNS、サークル紹介ページなど</small><input id="evidenceUrl" type="url" placeholder="https://"></label>
        <div class="form-grid"><label>人数<small>例: 20人、50人以上など</small><input id="memberCount" placeholder="例: 35人"></label><label>練習頻度<small>例: 週2回、月2回など</small><input id="practiceFrequency" placeholder="例: 週2回"></label></div>
        <div class="form-grid"><label>雰囲気<select id="atmosphere"><option value="">選択してください</option><option>初心者歓迎</option><option>ゆるめ</option><option>ほどよく真剣</option><option>競技志向</option><option>交流重視</option></select></label><label>経験者割合<select id="experienceRatio"><option value="">選択してください</option><option>初心者中心</option><option>初心者と経験者が半々</option><option>経験者多め</option><option>経験者中心</option><option>未定</option></select></label></div>
        <label>主な活動場所<small>キャンパス、体育館、グラウンド、外部施設など</small><input id="activityPlace" placeholder="例: 早稲田キャンパス周辺、都内体育館"></label>
        <label>紹介文<small>公開ページに表示されます</small><textarea id="introduction" placeholder="どんなサークルか、どんな相手と交流したいかを書いてください"></textarea></label>
        <label>補足<small>運営への連絡、確認してほしいことなど。公開ページにも代表コメントとして使えます。</small><textarea id="message"></textarea></label>
        <div id="result" class="result"></div>
        <div class="actions"><button class="button" type="submit">代表申請を送信</button><a class="button ghost" href="/signin">一般ユーザーとしてログイン</a></div>
      </form>
    </section>
  </main>
  <script>
    const sports = __SPORTS__;
    const orgTypes = __ORG_TYPES__;
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function fill(el, rows, label){el.innerHTML=`<option value="">${label}</option>`+rows.map(r=>`<option value="${esc(r.value)}">${esc(r.label)}</option>`).join("")}
    async function api(path, options){const r=await fetch(path, options); const data=await r.json(); if(!r.ok)throw new Error(data.error||"送信に失敗しました"); return data}
    async function boot(){const universities=await api("/api/universities"); fill($("universityId"),universities.map(u=>({value:u.university_id,label:`${u.university_name} / ${u.prefecture}`})),"大学を選択"); fill($("sportCategory"),sports.map(v=>({value:v,label:v})),"競技を選択"); fill($("organizationType"),orgTypes.map(v=>({value:v,label:v})),"団体種別を選択")}
    $("claimForm").addEventListener("submit",async e=>{e.preventDefault(); const result=$("result"); result.style.display="block"; result.className="result"; result.textContent="送信中です"; try{const payload={university_id:$("universityId").value,circle_name:$("circleName").value,sport_category:$("sportCategory").value,organization_type:$("organizationType").value,claimant_name:$("claimantName").value,claimant_email:$("claimantEmail").value,evidence_url:$("evidenceUrl").value,member_count:$("memberCount").value,practice_frequency:$("practiceFrequency").value,atmosphere:$("atmosphere").value,experience_ratio:$("experienceRatio").value,activity_place:$("activityPlace").value,introduction:$("introduction").value,message:$("message").value}; const data=await api("/api/claims",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); result.innerHTML=`代表申請を受け付けました。申請ID: ${esc(data.claim_id)}<br><a href="${esc(data.profile_url)}">作成されたサークルページを見る</a>`; e.target.reset()}catch(err){result.className="result error"; result.textContent=err.message}})
    boot().catch(e=>{const r=$("result"); r.style.display="block"; r.className="result error"; r.textContent=e.message});
  </script>
</body>
</html>"""

CIRCLE_PROFILE_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__CIRCLE_NAME__ | __SITE_NAME__</title>
  <style>
    :root{--ink:#17212f;--muted:#64748b;--line:#dbe4ed;--soft:#f4f7fa;--accent:#e15b31;--brand:#0f7a62}
    *{box-sizing:border-box}body{margin:0;background:var(--soft);color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1040px;margin:auto;padding:16px 18px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.brand{font-weight:900;text-decoration:none}.nav{display:flex;gap:12px;flex-wrap:wrap}.nav a{color:#31506b;text-decoration:none;font-weight:850}
    main{max-width:1040px;margin:auto;padding:28px 18px 60px}.hero{background:#fff;border:1px solid var(--line);border-radius:8px;padding:26px}.eyebrow{margin:0 0 8px;color:var(--brand);font-size:13px;font-weight:900}.hero h1{margin:0;font-size:38px;line-height:1.16}.lead{margin:14px 0 0;color:#405164;line-height:1.8;font-size:16px}.meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}.badge{display:inline-flex;align-items:center;border-radius:999px;background:#edf2f7;color:#405164;min-height:25px;padding:4px 10px;font-size:12px;font-weight:900}.badge.ok{background:#e2f5ed;color:#0d674f}
    .grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:900}.metric strong{display:block;margin-top:5px;font-size:18px;line-height:1.35}.panel{margin-top:14px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:20px}.panel h2{margin:0 0 10px;font-size:22px}.panel p{margin:0;color:#405164;line-height:1.8}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;border-radius:8px;padding:10px 14px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:900;text-decoration:none}.button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
    footer{max-width:1040px;margin:auto;padding:0 18px 34px;color:var(--muted);font-size:13px}
    @media(max-width:760px){.hero h1{font-size:30px}.grid{grid-template-columns:1fr 1fr}.top{align-items:flex-start}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a href="/circles">サークルDB</a><a href="/representative">自分のサークルを登録</a></nav></div></header>
  <main>
    <section class="hero"><p class="eyebrow">__UNIVERSITY_NAME__ / __SPORT__</p><h1>__CIRCLE_NAME__</h1><p class="lead">__CATCH_COPY__</p><div class="meta"><span class="badge ok">登録済み</span><span class="badge">__ORG_TYPE__</span><span class="badge">__PREFECTURE__</span></div><div class="actions"><a class="button primary" href="/?sport=__SPORT_ENC__#matches">募集を探す</a><a class="button" href="/circles?sport=__SPORT_ENC__">同じ競技のDBを見る</a></div></section>
    <section class="grid"><div class="metric"><span>人数</span><strong>__MEMBER_COUNT__</strong></div><div class="metric"><span>雰囲気</span><strong>__ATMOSPHERE__</strong></div><div class="metric"><span>経験者割合</span><strong>__EXPERIENCE_RATIO__</strong></div><div class="metric"><span>練習頻度</span><strong>__PRACTICE_FREQUENCY__</strong></div></section>
    <section class="panel"><h2>サークル紹介</h2><p>__INTRODUCTION__</p></section>
    <section class="panel"><h2>活動場所</h2><p>__ACTIVITY_PLACE__</p></section>
    <section class="panel"><h2>代表コメント</h2><p>__REPRESENTATIVE_COMMENT__</p></section>
  </main>
  <footer>このページはサークル代表の登録内容をもとに自動生成されています。訂正・削除は問い合わせページから連絡してください。</footer>
</body>
</html>"""

PUBLIC_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__SITE_NAME__ | 全国サークルDB</title>
  <style>
    :root{--ink:#17212f;--muted:#65758a;--line:#dbe4ed;--paper:#fff;--soft:#f4f7fa;--brand:#0f7a62;--accent:#e15b31;--blue:#2767a5}
    *{box-sizing:border-box}body{margin:0;background:#eef3f7;color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1120px;margin:auto;padding:18px;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
    h1{margin:0;font-size:23px}.nav{display:flex;gap:10px;flex-wrap:wrap}.nav a{color:var(--blue);font-weight:800;text-decoration:none}.nav a.cta{display:inline-flex;align-items:center;min-height:38px;border-radius:8px;padding:8px 12px;background:var(--accent);color:#fff}
    main{max-width:1120px;margin:auto;padding:18px}.hero{padding:18px 0 16px}.hero p{max-width:740px;color:var(--muted);line-height:1.7;margin:8px 0 0}
    .summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0 14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:13px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:800}.metric strong{display:block;margin-top:6px;font-size:24px}.breadcrumb{display:flex;gap:8px;align-items:center;flex-wrap:wrap;color:var(--muted);font-size:13px;font-weight:800;margin:0 0 10px}.breadcrumb b{color:var(--ink)}
    .panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.filters{display:grid;grid-template-columns:minmax(220px,1fr) repeat(5,150px);gap:8px;padding:14px;border-bottom:1px solid var(--line)}
    input,select{width:100%;border:1px solid #c8d4df;border-radius:8px;min-height:40px;padding:9px 10px;font:inherit;background:#fff;color:var(--ink)}
    .tablewrap{overflow:auto;max-height:680px}table{width:100%;border-collapse:collapse;font-size:14px;min-width:840px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{position:sticky;top:0;background:#f7fafc;color:var(--muted);font-size:12px}.name{font-weight:850}.sub{display:block;color:var(--muted);font-size:12px;margin-top:3px}.badge{display:inline-flex;border-radius:999px;background:#edf2f7;color:#405164;min-height:22px;padding:3px 8px;font-size:12px;font-weight:850}.ok{background:#e1f4eb;color:#0b624d}.blue{background:#e2edf8;color:#20598f}
    footer{max-width:1120px;margin:0 auto;padding:20px 18px 38px;color:var(--muted);font-size:13px}.admin-link{color:#65758a}
    @media(max-width:760px){.summary{grid-template-columns:repeat(2,minmax(0,1fr))}.filters{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <header><div class="top"><h1>サークルDB</h1><nav class="nav"><a class="cta" id="matchBridge" href="/">募集を探す</a><a href="/privacy">プライバシー</a><a href="/terms">利用規約</a><a href="/about-data">掲載情報</a><a href="/contact">問い合わせ</a></nav></div></header>
  <main>
    <section class="hero"><h2>大学サークル検索</h2><p>公開出典をもとにサークル・部活動の名称、競技、検証状態を整理しています。代表者の個人情報や内部メモは公開しません。</p></section>
    <section class="summary"><div class="metric"><span>対象地域</span><strong id="prefCount">0</strong></div><div class="metric"><span>対象大学</span><strong id="uniCount">0</strong></div><div class="metric"><span>検索結果</span><strong id="circleCount">0</strong></div><div class="metric"><span>検証済み/申請済み</span><strong id="verifiedCount">0</strong></div></section>
    <div class="breadcrumb"><span>検索範囲</span><b id="regionCrumb">関東</b><span>›</span><b id="prefCrumb">すべて</b></div>
    <section class="panel"><div class="filters"><input id="q" placeholder="大学名・団体名・競技で検索"><select id="regionFilter"><option value="">全地域</option></select><select id="prefFilter"><option value="">全都道府県</option></select><select id="sportFilter"><option value="">全競技</option></select><select id="statusFilter"><option value="">全検証</option><option value="university_verified">公式確認済み</option><option value="admin_verified">運営確認済み</option><option value="claimed">申請済み</option><option value="unverified">未確認</option></select><select id="sortFilter"><option value="university">大学名順</option><option value="circle">団体名順</option><option value="prefecture">都道府県順</option><option value="sport">競技順</option><option value="status">検証順</option><option value="updated">更新日順</option></select></div><div class="tablewrap"><table><thead><tr><th>大学</th><th>団体名</th><th>登録済み</th><th>種別</th><th>競技</th><th>検証</th><th>出典</th></tr></thead><tbody id="rows"></tbody></table></div></section>
  </main>
  <footer>掲載情報の訂正・削除は問い合わせページから連絡してください。<a class="admin-link" href="/admin">管理画面</a></footer>
  <script>
    const prefs = __PREFS__;
    const regions = __REGIONS__;
    const sports = __SPORTS__;
    const params = new URLSearchParams(location.search);
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function statusLabel(v){return ({university_verified:"公式確認済み",admin_verified:"運営確認済み",claimed:"申請済み",unverified:"未確認"}[v] || v)}
    function sourceLabel(v){return ({university_official:"大学公式",self_registered:"本人登録",public_sns:"SNS等",other:"その他"}[v] || v)}
    function badge(v,cls=""){return `<span class="badge ${cls}">${esc(v)}</span>`}
    function fillSelect(el, values, first){el.innerHTML=`<option value="">${first}</option>`+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("")}
    function fillRegions(){ $("regionFilter").innerHTML='<option value="">全地域</option>'+regions.map(r=>`<option value="${esc(r.value)}">${esc(r.label)}</option>`).join("") }
    function selectedRegion(){return regions.find(r=>r.value===$("regionFilter").value)}
    function prefValues(){return selectedRegion()?.prefectures || prefs}
    function syncPrefOptions(){const current=$("prefFilter").value; fillSelect($("prefFilter"),prefValues(),selectedRegion()?`${selectedRegion().label}すべて`:"全都道府県"); if(prefValues().includes(current)) $("prefFilter").value=current}
    function currentQuery(){const qs=new URLSearchParams({q:$("q").value,prefecture:$("prefFilter").value,sport:$("sportFilter").value,status:$("statusFilter").value,sort:$("sortFilter").value}); if($("regionFilter").value) qs.set("region",$("regionFilter").value); return qs}
    async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
    function updateSummary(data){$("prefCount").textContent=new Set(data.map(c=>c.prefecture)).size; $("uniCount").textContent=new Set(data.map(c=>c.university_id)).size; $("circleCount").textContent=data.length; $("verifiedCount").textContent=data.filter(c=>["claimed","university_verified","admin_verified"].includes(c.verification_status)).length; $("regionCrumb").textContent=selectedRegion()?.label||"全地域"; $("prefCrumb").textContent=$("prefFilter").value||"すべて"}
    async function refresh(){const qs=currentQuery(); $("matchBridge").href="/?"+qs+"#matches"; const data=await api("/api/circles?"+qs); updateSummary(data); $("rows").innerHTML=data.map(c=>`<tr><td><span class="name">${esc(c.university_name)}</span><span class="sub">${esc(c.prefecture)}${c.city?` / ${esc(c.city)}`:""}</span></td><td><span class="name">${esc(c.circle_name)}</span></td><td>${c.profile_url?`<a href="${esc(c.profile_url)}">URL</a>`:""}</td><td>${badge(c.organization_type||"不明","blue")}</td><td>${esc(c.sport_category||"その他")}</td><td>${badge(statusLabel(c.verification_status),["admin_verified","university_verified"].includes(c.verification_status)?"ok":"")}</td><td>${badge(sourceLabel(c.source_type))}${c.source_url?`<span class="sub"><a href="${esc(c.source_url)}" target="_blank">出典URL</a></span>`:""}</td></tr>`).join("") || `<tr><td colspan="7">データなし</td></tr>`}
    async function boot(){fillRegions(); fillSelect($("sportFilter"),sports,"全競技"); $("regionFilter").value=params.get("region")||""; syncPrefOptions(); $("q").value=params.get("q")||""; $("prefFilter").value=params.get("prefecture")||""; $("sportFilter").value=params.get("sport")||""; $("statusFilter").value=params.get("status")||""; $("sortFilter").value=params.get("sort")||"university"; await refresh()}
    ["q","prefFilter","sportFilter","statusFilter","sortFilter"].forEach(id=>$(id).addEventListener("input",refresh));
    $("regionFilter").addEventListener("input",()=>{syncPrefOptions(); refresh()});
    boot().catch(e=>alert(e.message));
  </script>
</body>
</html>"""

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
    .filters{display:grid;grid-template-columns:minmax(220px,1fr) 140px 150px 150px 150px 150px;gap:8px;padding:15px;border-bottom:1px solid var(--line)}.tablewrap{overflow:auto;max-height:650px}table{width:100%;border-collapse:collapse;font-size:13px;table-layout:auto}th,td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{position:sticky;top:0;background:#f7fafc;color:var(--muted);font-size:12px}.circle-table{min-width:1080px}.circle-table th:nth-child(1){width:20%}.circle-table th:nth-child(2){width:30%}.circle-table th:nth-child(3){width:13%}.circle-table th:nth-child(4){width:12%}.circle-table th:nth-child(5){width:10%}.circle-table th:nth-child(6){width:9%}.circle-table th:nth-child(7){width:6%}.primary-cell{min-width:300px}.circle-name{display:block;font-size:15px;font-weight:850;line-height:1.35}.subline{display:block;margin-top:4px;color:var(--muted);font-size:12px;line-height:1.35}.uni-name{font-weight:850;white-space:nowrap}.actions{white-space:nowrap}.badge{display:inline-flex;align-items:center;border-radius:999px;background:#edf2f7;color:#405164;min-height:22px;padding:3px 8px;font-size:12px;font-weight:850;white-space:nowrap}.ok{background:#e1f4eb;color:#0b624d}.warn{background:#fff0cf;color:#775000}.blue{background:#e2edf8;color:#20598f}.muted{color:var(--muted)}.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px}.notice{padding:12px 14px;border:1px solid #f0d9ad;background:#fff8ec;color:#6d4b06;border-radius:8px;margin-bottom:14px;line-height:1.6}
    @media(max-width:980px){.summary{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.filters{grid-template-columns:1fr}.row{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <header><div class="top"><h1>Circle Match DB Admin</h1><nav class="tabs"><button class="tab active" data-view="circles">サークル検索</button><button class="tab" data-view="circle-register">サークル登録</button><button class="tab" data-view="collection">収集状況</button><button class="tab" data-view="candidates">候補レビュー</button><button class="tab" data-view="metrics">管理指標</button><button class="tab" data-view="privacy">非公開情報</button><button class="tab" data-view="universities">大学DB</button><button class="tab" data-view="matches">募集DB</button><button class="tab" data-view="imports">CSV取込</button><button class="tab" data-view="logs">更新履歴</button></nav></div></header>
  <main>
    <div class="notice">これはブラウザ保存ではなく、SQLiteファイル <span class="mono">outputs/circlematch.sqlite</span> に保存される実DBです。公開DBと個人情報・内部メモDBを分離し、公開検索APIには個人情報を返しません。</div>
    <nav class="site-links"><a href="/privacy" target="_blank">プライバシーポリシー</a><a href="/terms" target="_blank">利用規約</a><a href="/about-data" target="_blank">掲載情報・削除訂正</a><a href="/contact" target="_blank">問い合わせ</a></nav>
    <section class="summary"><div class="metric"><span>都道府県</span><strong id="prefCount">0</strong></div><div class="metric"><span>大学</span><strong id="uniCount">0</strong></div><div class="metric"><span>サークル</span><strong id="circleCount">0</strong></div><div class="metric"><span>検証済み/申請済み</span><strong id="verifiedCount">0</strong></div><div class="metric"><span>候補</span><strong id="candidateCount">0</strong></div><div class="metric"><span>募集中</span><strong id="matchCount">0</strong></div></section>
    <section id="circles" class="view active"><div class="panel"><div class="head"><div><h2>全国サークル台帳</h2><p>検索・絞り込み・編集対象の確認</p></div><button id="reloadCircles">再読込</button></div><div class="filters"><input id="q" placeholder="大学名・団体名・競技・地域"><select id="prefFilter"><option value="">全都道府県</option></select><select id="orgTypeFilter"><option value="">全種別</option></select><select id="sportFilter"><option value="">全競技</option></select><select id="statusFilter"><option value="">全ステータス</option></select><select id="adminSortFilter"><option value="university">大学名順</option><option value="circle">団体名順</option><option value="prefecture">都道府県順</option><option value="sport">競技順</option><option value="type">種別順</option><option value="status">検証順</option><option value="updated">更新日順</option></select></div><div class="tablewrap"><table class="circle-table"><thead><tr><th>大学</th><th>団体名</th><th>種別</th><th>競技</th><th>ソース</th><th>検証</th><th>操作</th></tr></thead><tbody id="circleRows"></tbody></table></div></div></section>
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
    async function refreshCircles(){const qs=new URLSearchParams({q:$("q").value,prefecture:$("prefFilter").value,organization_type:$("orgTypeFilter").value,sport:$("sportFilter").value,status:$("statusFilter").value,sort:$("adminSortFilter").value}); const rows=await api("/api/circles?"+qs); $("matchCircle").innerHTML=rows.map(c=>`<option value="${c.circle_id}">${esc(c.university_name)} - ${esc(c.circle_name)}</option>`).join(""); $("circleRows").innerHTML=rows.map(c=>`<tr><td><span class="uni-name">${esc(c.university_name)}</span><span class="subline">${esc(c.prefecture)}${c.city?` / ${esc(c.city)}`:""}</span></td><td class="primary-cell"><span class="circle-name">${esc(c.circle_name)}</span></td><td>${badgeOrgType(c.organization_type)}</td><td>${esc(c.sport_category)}${c.activity_area?`<span class="subline">${esc(c.activity_area)}</span>`:""}</td><td>${badgeSource(c.source_type)}<br>${c.source_url?`<a href="${esc(c.source_url)}" target="_blank">URL</a>`:"<span class='muted'>URLなし</span>"}</td><td>${badgeStatus(c.verification_status)}</td><td class="actions"><button data-edit="${c.circle_id}">編集</button></td></tr>`).join("") || `<tr><td colspan="7" class="muted">データなし</td></tr>`; document.querySelectorAll("[data-edit]").forEach(b=>b.onclick=()=>loadCircle(b.dataset.edit, rows));}
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
    ["q","prefFilter","orgTypeFilter","sportFilter","statusFilter","adminSortFilter"].forEach(id=>$(id).addEventListener("input",refreshCircles)); $("reloadCircles").onclick=refreshCircles; $("reloadCollection").onclick=refreshCollection; $("reloadCandidates").onclick=refreshCandidates; $("reloadMetrics").onclick=refreshMetrics; $("reloadPrivacy").onclick=refreshPrivacy; $("reloadLogs").onclick=refreshLogs;
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


def is_local_host():
    return HOST in LOCAL_HOSTS


def admin_auth_enabled():
    return bool(ADMIN_PASSWORD)


def google_oauth_enabled():
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and SESSION_SECRET)


def supabase_auth_enabled():
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY and SESSION_SECRET)


def oauth_redirect_uri():
    root = base_url() or f"http://{HOST}:{PORT}"
    return f"{root}/auth/google/callback"


def secure_cookie_suffix():
    root = base_url() or f"http://{HOST}:{PORT}"
    return "; Secure" if root.startswith("https://") else ""


def sign_value(value):
    return hmac.new(SESSION_SECRET.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def make_oauth_state():
    payload = f"{secrets.token_urlsafe(18)}.{int(datetime.now().timestamp())}"
    return f"{payload}.{sign_value(payload)}"


def verify_oauth_state(state):
    parts = (state or "").split(".")
    if len(parts) != 3:
        return False
    payload = ".".join(parts[:2])
    return hmac.compare_digest(sign_value(payload), parts[2])


def google_authorize_url(state):
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": oauth_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def post_form(url, data):
    body = urlencode(data).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_json(url, access_token):
    request = Request(url, headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_supabase_user(access_token):
    if not supabase_auth_enabled():
        raise ValueError("Supabase Auth is not configured")
    request = Request(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "apikey": SUPABASE_ANON_KEY,
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def upsert_oauth_user(conn, profile):
    subject = profile.get("sub", "")
    email = profile.get("email", "")
    if not subject or not email:
        raise ValueError("Google profile missing subject or email")
    timestamp = now()
    user_id = slug("user", "google_" + subject)
    conn.execute(
        """
        insert into user_accounts(user_id, provider, provider_subject, email, display_name, picture_url, created_at, updated_at)
        values(?,?,?,?,?,?,?,?)
        on conflict(provider, provider_subject) do update set
          email=excluded.email,
          display_name=excluded.display_name,
          picture_url=excluded.picture_url,
          updated_at=excluded.updated_at
        """,
        (user_id, "google", subject, email, profile.get("name", ""), profile.get("picture", ""), timestamp, timestamp),
    )
    row = conn.execute("select user_id from user_accounts where provider='google' and provider_subject=?", (subject,)).fetchone()
    return row["user_id"]


def upsert_supabase_user(conn, profile):
    subject = profile.get("id", "")
    email = profile.get("email", "")
    if not subject or not email:
        raise ValueError("Supabase profile missing id or email")
    metadata = profile.get("user_metadata") or {}
    timestamp = now()
    user_id = slug("user", "supabase_" + subject)
    conn.execute(
        """
        insert into user_accounts(user_id, provider, provider_subject, email, display_name, picture_url, created_at, updated_at)
        values(?,?,?,?,?,?,?,?)
        on conflict(provider, provider_subject) do update set
          email=excluded.email,
          display_name=excluded.display_name,
          picture_url=excluded.picture_url,
          updated_at=excluded.updated_at
        """,
        (
            user_id,
            "supabase",
            subject,
            email,
            metadata.get("full_name") or metadata.get("name") or "",
            metadata.get("avatar_url") or metadata.get("picture") or "",
            timestamp,
            timestamp,
        ),
    )
    row = conn.execute("select user_id from user_accounts where provider='supabase' and provider_subject=?", (subject,)).fetchone()
    return row["user_id"]


def create_user_session(conn, user_id):
    session_id = secrets.token_urlsafe(32)
    timestamp = now()
    conn.execute(
        "insert into user_sessions(session_id, user_id, created_at, expires_at) values(?,?,?,datetime('now','+30 days'))",
        (session_id, user_id, timestamp),
    )
    return session_id


def render_public_html():
    return (
        with_adsense(MATCH_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__SPORTS__", json.dumps(sport_options(), ensure_ascii=False))
        .replace("__REGIONS__", json.dumps(region_options(), ensure_ascii=False))
        .replace("__POPULAR_SPORTS__", json.dumps([
            {"name": name, "label": label, "code": code, "color": color, "image": image}
            for name, label, code, color, image in POPULAR_SPORTS
        ], ensure_ascii=False))
        .replace("__PREFS__", json.dumps(PREFECTURES, ensure_ascii=False))
        .encode("utf-8")
    )


def render_circles_html():
    return (
        with_adsense(PUBLIC_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__SPORTS__", json.dumps(sport_options(), ensure_ascii=False))
        .replace("__REGIONS__", json.dumps(region_options(), ensure_ascii=False))
        .replace("__PREFS__", json.dumps(PREFECTURES, ensure_ascii=False))
        .encode("utf-8")
    )


def render_signin_html():
    return (
        with_adsense(SIGNIN_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__SUPABASE_URL__", json.dumps(SUPABASE_URL))
        .replace("__SUPABASE_ANON_KEY__", json.dumps(SUPABASE_ANON_KEY))
        .replace("__AUTH_READY__", "true" if supabase_auth_enabled() else "false")
        .encode("utf-8")
    )


def render_sport_html(sport):
    sport = sport if sport in sport_options() else "野球"
    return (
        with_adsense(SPORT_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__SPORT__", sport)
        .replace("__SPORT_JSON__", json.dumps(sport, ensure_ascii=False))
        .encode("utf-8")
    )


def render_region_html(region):
    region = region if region in REGION_GROUPS else "kanto"
    return (
        with_adsense(REGION_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__REGION_LABEL__", REGION_GROUPS[region]["label"])
        .replace("__REGION_JSON__", json.dumps(region, ensure_ascii=False))
        .encode("utf-8")
    )


def render_post_match_html():
    return (
        with_adsense(POST_MATCH_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__SPORTS__", json.dumps(sport_options(), ensure_ascii=False))
        .encode("utf-8")
    )


def render_representative_html():
    return (
        with_adsense(REPRESENTATIVE_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__SPORTS__", json.dumps(sport_options(), ensure_ascii=False))
        .replace("__ORG_TYPES__", json.dumps(ORGANIZATION_TYPES, ensure_ascii=False))
        .encode("utf-8")
    )


def render_circle_profile_html(profile_slug):
    with connect() as conn:
        row = conn.execute(
            """
            select p.*, c.circle_id, c.circle_name, c.organization_type, c.sport_category,
              u.university_name, u.prefecture, u.city
            from circle_public_profiles p
            join circles c on c.circle_id=p.circle_id
            join universities u on u.university_id=c.university_id
            where p.profile_slug=? and p.is_published=1
            """,
            (profile_slug,),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    def clean(value, fallback="未入力"):
        value = (value or "").strip()
        return html.escape(value if value else fallback)
    sport = data.get("sport_category") or "その他"
    page = (
        with_adsense(CIRCLE_PROFILE_HTML)
        .replace("__SITE_NAME__", html.escape(SITE_NAME))
        .replace("__UNIVERSITY_NAME__", clean(data.get("university_name")))
        .replace("__SPORT__", clean(sport))
        .replace("__SPORT_ENC__", quote(sport))
        .replace("__CIRCLE_NAME__", clean(data.get("circle_name")))
        .replace("__CATCH_COPY__", clean(data.get("catch_copy"), f"{data.get('circle_name', 'サークル')}の活動紹介ページです。"))
        .replace("__ORG_TYPE__", clean(data.get("organization_type")))
        .replace("__PREFECTURE__", clean(data.get("prefecture")))
        .replace("__MEMBER_COUNT__", clean(data.get("member_count")))
        .replace("__ATMOSPHERE__", clean(data.get("atmosphere")))
        .replace("__EXPERIENCE_RATIO__", clean(data.get("experience_ratio")))
        .replace("__PRACTICE_FREQUENCY__", clean(data.get("practice_frequency")))
        .replace("__INTRODUCTION__", clean(data.get("introduction"), "代表者からの紹介文はまだ登録されていません。"))
        .replace("__ACTIVITY_PLACE__", clean(data.get("activity_place")))
        .replace("__REPRESENTATIVE_COMMENT__", clean(data.get("representative_comment"), "代表者コメントはまだ登録されていません。"))
    )
    return page.encode("utf-8")


def render_admin_html():
    return (
        with_adsense(HTML)
        .replace("__SPORTS__", json.dumps(sport_options(), ensure_ascii=False))
        .replace("__SOURCE_TYPES__", json.dumps(SOURCE_TYPES, ensure_ascii=False))
        .replace("__STATUSES__", json.dumps(VERIFICATION_STATUSES, ensure_ascii=False))
        .replace("__ORG_TYPES__", json.dumps(ORGANIZATION_TYPES, ensure_ascii=False))
        .replace("__PREFS__", json.dumps(PREFECTURES, ensure_ascii=False))
        .encode("utf-8")
    )


def base_url():
    return SITE_BASE_URL.rstrip("/")


def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /api/",
    ]
    if base_url():
        lines.append(f"Sitemap: {base_url()}/sitemap.xml")
    return ("\n".join(lines) + "\n").encode("utf-8")


def sitemap_xml():
    root = base_url() or "http://127.0.0.1:8787"
    paths = ["/", "/signin", "/post-match", "/representative", "/circles", "/privacy", "/terms", "/about-data", "/contact"]
    paths.extend(["/sports?" + urlencode({"sport": name}) for name, _, _, _, _ in POPULAR_SPORTS])
    paths.extend(["/regions?" + urlencode({"region": key}) for key in REGION_GROUPS.keys()])
    urls = "\n".join(
        f"  <url><loc>{root}{path}</loc></url>"
        for path in paths
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
""".encode("utf-8")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    return conn


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    if not base:
        return f"{prefix}_{int(datetime.now().timestamp())}"
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{base[:36]}_{digest}"


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


SPORT_KEYWORDS = [
    ("アメリカンフットボール", ["アメリカンフットボール", "アメフト", "フットボールクラブ", "タッチフットボール"]),
    ("ソフトテニス", ["ソフトテニス"]),
    ("テニス", ["テニス"]),
    ("サッカー", ["サッカー", "蹴球"]),
    ("フットサル", ["フットサル"]),
    ("バスケットボール", ["バスケットボール", "バスケ", "籠球", "3×3"]),
    ("バレーボール", ["バレーボール", "バレー", "排球"]),
    ("バドミントン", ["バドミントン"]),
    ("野球", ["野球", "ベースボール"]),
    ("ラグビー", ["ラグビー"]),
    ("ラクロス", ["ラクロス"]),
    ("卓球", ["卓球"]),
    ("水泳", ["水泳", "水球"]),
    ("陸上競技", ["陸上", "駅伝"]),
    ("ハンドボール", ["ハンドボール"]),
    ("ホッケー", ["ホッケー"]),
    ("ゴルフ", ["ゴルフ"]),
    ("スキー", ["スキー"]),
    ("スケート", ["スケート", "アイススケート", "フィギュア"]),
    ("ソフトボール", ["ソフトボール"]),
    ("アーチェリー", ["アーチェリー", "洋弓"]),
    ("フェンシング", ["フェンシング"]),
    ("自動車", ["自動車"]),
    ("自転車", ["自転車", "サイクリング"]),
    ("トライアスロン", ["トライアスロン"]),
    ("ボウリング", ["ボウリング"]),
    ("ボルダリング", ["ボルダリング"]),
    ("ウィンドサーフィン", ["ウィンドサーフィン", "ウインドサーフィン"]),
    ("スノーボード", ["スノーボード"]),
    ("セパタクロー", ["セパタクロー"]),
    ("ダブルダッチ", ["ダブルダッチ"]),
    ("フライングディスク", ["フライングディスク"]),
    ("ボディビル", ["ボディビル", "バーベル"]),
    ("釣り", ["釣り"]),
    ("アウトドア", ["アウトドア", "ワンダーフォーゲル", "探検", "山岳", "ハイキング", "野外活動", "ユースホステル"]),
    ("ボクシング", ["ボクシング", "キックボクシング"]),
    ("ボート", ["ボート", "漕艇"]),
    ("ヨット", ["ヨット"]),
    ("レスリング", ["レスリング"]),
    ("射撃", ["射撃"]),
    ("航空", ["航空"]),
    ("重量挙", ["重量挙", "ウエイトリフティング"]),
    ("馬術", ["馬術"]),
    ("アルティメット", ["アルティメット"]),
    ("カヌー", ["カヌー"]),
    ("スカッシュ", ["スカッシュ"]),
    ("チアリーディング", ["チア", "リーダー部", "応援団"]),
    ("ライフセービング", ["ライフセービング"]),
    ("武道", ["武道", "剣道", "柔道", "空手", "合気道", "合氣道", "拳法", "少林寺", "テコンドー", "躰道", "弓道", "相撲", "なぎなた"]),
    ("体操", ["体操", "器械体操"]),
    ("ダンス", ["ダンス", "舞踊"]),
    ("音楽", ["音楽", "グリー", "交響楽", "管弦楽", "吹奏楽", "軽音", "フォークソング", "ロック", "マンドリン", "邦楽", "合唱", "オーケストラ", "ギター", "ピアノ", "ブラスバンド", "箏曲"]),
    ("写真", ["写真"]),
    ("美術", ["美術", "陶芸"]),
    ("茶道", ["茶道"]),
    ("書道", ["書道"]),
    ("将棋", ["将棋"]),
    ("囲碁", ["囲碁"]),
    ("漫画", ["漫画", "アニメ"]),
    ("映画", ["映画"]),
    ("演劇", ["演劇"]),
    ("文芸", ["文芸"]),
    ("放送", ["放送", "アナウンス"]),
    ("鉄道", ["鉄道"]),
    ("天文", ["天文"]),
    ("歴史", ["歴史", "戦史"]),
    ("考古学", ["考古"]),
    ("電子計算機", ["電子計算機", "コンピュー", "プログラミング"]),
    ("ボードゲーム", ["ボードゲーム"]),
    ("TRPG", ["TRPG"]),
    ("サバイバルゲーム", ["サバイバルゲーム"]),
    ("ゲーム", ["スプラトゥーン"]),
    ("落語", ["落語"]),
    ("華道", ["華道"]),
    ("能楽", ["能楽"]),
    ("競技かるた", ["競技かるた", "百人一首"]),
    ("料理", ["料理"]),
    ("法律", ["法律", "法学"]),
    ("会計", ["会計"]),
    ("ボランティア", ["ボランティア"]),
]

INVALID_CIRCLE_EXACT_NAMES = {
    "本部", "体育会本部", "クラブ活動", "クラブ＆サークル", "サークル・同好会", "その他の団体",
    "学生団体", "学術団体", "上部団体", "中央執行委員会", "強化クラブ", "関連団体",
    "文化団体連合会", "文化系クラブ", "文化系団体",
}
INVALID_CIRCLE_PHRASES = [
    "本学学生が",
    "による総長への戦績報告会",
    "春の最強王決定戦",
    "場所 ",
    "現在、",
    "練習しています",
    "活動しています",
    "過去には",
    "達成。",
    "全員が",
    "誓約書",
    "WORD／",
    "PDF",
    "文部科学省定義",
    "学生表彰",
    "団体合同ライブ",
    "団体合同ハロウィンライブ",
    "新設団体活動予定書",
]
INVALID_CIRCLE_ALWAYS_PHRASES = [
    "合同ライブ",
    "合同ハロウィンライブ",
    "合同演奏会",
    "活動予定書",
    "参加しました",
    "戦績報告会",
    "活動報告会",
    "定期演奏会",
    "運動会",
    "インタビュー",
]
INVALID_CIRCLE_EVENT_WORDS = [
    "大会", "選手権", "リーグ戦", "トーナメント", "決定戦", "試合結果", "試合予定",
    "戦績", "順位", "結果", "速報", "場所", "活動場所：", "活動日：", "活動時間：",
]
INVALID_SOURCE_PATH_PARTS = [
    "/sports/result", "/result", "/results", "/news", "/event", "/events", "/schedule", "/calendar",
]
INVALID_CIRCLE_TITLE_PATTERNS = [
    r"(TOP|一覧|こちら|を見る|について|もっと知る|ご確認ください)",
    r"(届|補助金|住所変更|研究データ|研究インテグリティ|倫理委員会|認定証|指針|セレクション|再開|レベル\d)",
    r"(紹介動画|活動場所[:：]|活動日[:：]|団体旅行|学部・大学院|付属校|練習しています|活動しています)",
    r"サークル・部会活動",
]


def infer_sport_category(name, current="その他"):
    text = name or ""
    if current and current != "その他":
        return current
    for category, keywords in SPORT_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return category
    return current or "その他"


def is_invalid_circle_name(name, source_url=""):
    text = (name or "").strip()
    url = (source_url or "").lower()
    if not text:
        return True
    if text.startswith("#"):
        return True
    if text in INVALID_CIRCLE_EXACT_NAMES:
        return True
    if any(part in url for part in INVALID_SOURCE_PATH_PARTS) and any(word in text for word in INVALID_CIRCLE_EVENT_WORDS + ["優勝", "準優勝", "位"]):
        return True
    if any(re.search(pattern, text) for pattern in INVALID_CIRCLE_TITLE_PATTERNS):
        return True
    if re.search(r"^\d{1,2}\.\d{1,2}\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun|月|火|水|木|金|土|日|\()", text, re.I):
        return True
    if re.search(r"^\d{4}年", text) and any(word in text for word in INVALID_CIRCLE_EVENT_WORDS):
        return True
    if any(word in text for word in ["優勝", "準優勝", "ベスト", "ブロック…", "…"]) and any(word in text for word in INVALID_CIRCLE_EVENT_WORDS + ["リーグ", "位"]):
        return True
    if any(word in text for word in INVALID_CIRCLE_EVENT_WORDS) and not any(marker in text for marker in ["部", "会", "サークル", "クラブ", "団体", "委員会", "同好会"]):
        return True
    if len(text) > 14 and re.search(r"。$", text) and not any(marker in text for marker in ["部", "会", "サークル", "クラブ", "団体", "委員会", "同好会"]):
        return True
    if any(phrase in text for phrase in ["誓約書", "WORD／", "PDF", "文部科学省定義", "学生表彰", "新設団体活動予定書"]):
        return True
    if any(phrase in text for phrase in INVALID_CIRCLE_ALWAYS_PHRASES):
        return True
    if len(text) > 42 and any(phrase in text for phrase in INVALID_CIRCLE_PHRASES):
        return True
    if text.startswith("【") and any(word in text for word in ["優勝", "準優勝", "位", "リーグ", "大会"]):
        return True
    if any(ch.isdigit() for ch in text) and any(phrase in text for phrase in ["名・", "%", "合同ライブ", "活動予定書"]):
        return True
    if "第" in text and any(word in text for word in ["大会", "選手権", "リーグ戦", "トーナメント"]):
        return True
    if "第" in text and any(word in text for word in ["演奏会", "運動会", "外語祭"]):
        return True
    if len(text) > 36 and any(word in text for word in ["インタビュー", "振り返る", "を前に"]):
        return True
    if any(phrase in text for phrase in ["本学学生が", "号 歴史を変えた"]):
        return True
    return False


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
<body><main><a class="back" href="/">トップへ戻る</a><div class="panel">{body}</div></main></body></html>"""
    return with_adsense(html).encode("utf-8")


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
        create table if not exists circle_public_profiles (
          profile_id text primary key,
          circle_id text not null references circles(circle_id) on delete cascade,
          profile_slug text not null unique,
          catch_copy text,
          introduction text,
          member_count text,
          atmosphere text,
          experience_ratio text,
          practice_frequency text,
          activity_place text,
          representative_comment text,
          is_published integer not null default 1,
          created_at text not null,
          updated_at text not null,
          unique(circle_id)
        );
        create table if not exists user_accounts (
          user_id text primary key,
          provider text not null,
          provider_subject text not null,
          email text not null,
          display_name text,
          picture_url text,
          created_at text not null,
          updated_at text not null,
          unique(provider, provider_subject)
        );
        create table if not exists user_sessions (
          session_id text primary key,
          user_id text not null references user_accounts(user_id) on delete cascade,
          created_at text not null,
          expires_at text not null
        );
        create table if not exists match_posts (
          match_post_id text primary key,
          circle_id text not null references circles(circle_id),
          match_type text not null,
          level_label text,
          scheduled_at text,
          period_start text,
          period_end text,
          place text,
          practice_detail text,
          capacity text,
          conditions text,
          status text not null default 'open',
          created_by text,
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
        create index if not exists idx_circle_public_profiles_circle on circle_public_profiles(circle_id);
        create index if not exists idx_circle_public_profiles_slug on circle_public_profiles(profile_slug);
        create index if not exists idx_user_sessions_user on user_sessions(user_id);
        create index if not exists idx_circle_candidates_university on circle_candidates(university_id);
        create index if not exists idx_circle_candidates_status on circle_candidates(review_status);
        """)
        ensure_column(conn, "circles", "organization_type", "text not null default '不明'")
        ensure_column(conn, "match_posts", "period_start", "text")
        ensure_column(conn, "match_posts", "period_end", "text")
        ensure_column(conn, "match_posts", "practice_detail", "text")
        ensure_column(conn, "match_posts", "capacity", "text")
        ensure_column(conn, "match_posts", "created_by", "text")
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
        imported_seed = seed_public_circles_from_csv(conn)
        if conn.execute("select count(*) from circles").fetchone()[0] == 0 and not imported_seed:
            seed_circles(conn)
        normalize_circle_records(conn)
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


def seed_public_circles_from_csv(conn):
    if not PUBLIC_SEED_PATH.exists():
        return 0
    with PUBLIC_SEED_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        imported = 0
        for item in reader:
            uni_name = (item.get("university_name") or "").strip()
            circle_name = (item.get("circle_name") or "").strip()
            if not uni_name or not circle_name:
                continue
            if is_invalid_circle_name(circle_name, item.get("source_url", "")):
                continue
            uni = conn.execute(
                "select university_id from universities where university_name=? order by campus_name limit 1",
                (uni_name,),
            ).fetchone()
            if uni:
                university_id = uni["university_id"]
            else:
                university_id = upsert_university(conn, {
                    "university_name": uni_name,
                    "prefecture": item.get("prefecture") or "東京都",
                    "city": item.get("city", ""),
                    "campus_name": item.get("campus_name", ""),
                    "official_url": item.get("official_url", ""),
                    "source_url": item.get("official_url", ""),
                }, audit=False)
            upsert_circle(conn, {
                "university_id": university_id,
                "circle_name": circle_name,
                "organization_type": item.get("organization_type") or infer_organization_type(circle_name, item.get("source_type") or "other"),
                "sport_category": infer_sport_category(circle_name, item.get("sport_category") or "その他"),
                "activity_area": item.get("activity_area", ""),
                "source_type": item.get("source_type") or "other",
                "source_url": item.get("source_url", ""),
                "verification_status": item.get("verification_status") or "unverified",
                "public_status": item.get("public_status") or "published",
                "last_checked_at": item.get("last_checked_at", ""),
            }, audit_entry=False)
            imported += 1
        if imported:
            audit(conn, "public_seed_import", "circle", None, {"imported": imported, "source": str(PUBLIC_SEED_PATH)})
        return imported


def normalize_circle_records(conn):
    removed = 0
    updated = 0
    for row in conn.execute("select circle_id, circle_name, sport_category, source_url from circles").fetchall():
        name = row["circle_name"]
        if is_invalid_circle_name(name, row["source_url"] or ""):
            conn.execute("delete from data_sources where entity_type='circle' and entity_id=?", (row["circle_id"],))
            conn.execute("delete from circle_private_profiles where circle_id=?", (row["circle_id"],))
            conn.execute("delete from circle_claims where circle_id=?", (row["circle_id"],))
            conn.execute("delete from match_posts where circle_id=?", (row["circle_id"],))
            conn.execute("delete from circles where circle_id=?", (row["circle_id"],))
            removed += 1
            continue
        sport = infer_sport_category(name, row["sport_category"])
        if sport != row["sport_category"]:
            conn.execute(
                "update circles set sport_category=?, updated_at=? where circle_id=?",
                (sport, now(), row["circle_id"]),
            )
            updated += 1
    if removed or updated:
        audit(conn, "normalize_circle_records", "circle", None, {"removed": removed, "updated": updated})


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


def upsert_circle_public_profile(conn, circle_id, data):
    timestamp = now()
    profile_slug = data.get("profile_slug") or circle_id
    conn.execute(
        """
        insert into circle_public_profiles(profile_id, circle_id, profile_slug, catch_copy, introduction, member_count,
          atmosphere, experience_ratio, practice_frequency, activity_place, representative_comment, is_published, created_at, updated_at)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        on conflict(circle_id) do update set
          catch_copy=excluded.catch_copy,
          introduction=excluded.introduction,
          member_count=excluded.member_count,
          atmosphere=excluded.atmosphere,
          experience_ratio=excluded.experience_ratio,
          practice_frequency=excluded.practice_frequency,
          activity_place=excluded.activity_place,
          representative_comment=excluded.representative_comment,
          is_published=excluded.is_published,
          updated_at=excluded.updated_at
        """,
        (
            slug("pub", circle_id),
            circle_id,
            profile_slug,
            (data.get("catch_copy") or "").strip(),
            (data.get("introduction") or "").strip(),
            (data.get("member_count") or "").strip(),
            (data.get("atmosphere") or "").strip(),
            (data.get("experience_ratio") or "").strip(),
            (data.get("practice_frequency") or "").strip(),
            (data.get("activity_place") or "").strip(),
            (data.get("representative_comment") or data.get("message") or "").strip(),
            1,
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


def upsert_circle(conn, data, audit_entry=True):
    name = data.get("circle_name", "").strip()
    university_id = data.get("university_id", "").strip()
    if not name or not university_id:
        raise ValueError("university_id and circle_name are required")
    if is_invalid_circle_name(name, data.get("source_url", "")):
        raise ValueError("circle_name looks like an event result or non-circle record")
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
            infer_sport_category(name, data.get("sport_category") or "その他"),
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
    if audit_entry:
        audit(conn, "upsert", "circle", saved_id, data)
    return saved_id


def create_circle_claim(conn, data):
    university_id = (data.get("university_id") or "").strip()
    circle_name = (data.get("circle_name") or "").strip()
    claimant_email = (data.get("claimant_email") or "").strip()
    claimant_name = (data.get("claimant_name") or "").strip()
    if not university_id or not circle_name or not claimant_email:
        raise ValueError("university_id, circle_name and claimant_email are required")
    if "@" not in claimant_email:
        raise ValueError("valid claimant_email is required")
    if not conn.execute("select 1 from universities where university_id=?", (university_id,)).fetchone():
        raise ValueError("university not found")
    circle_id = upsert_circle(conn, {
        "university_id": university_id,
        "circle_name": circle_name,
        "organization_type": data.get("organization_type") if data.get("organization_type") in ORGANIZATION_TYPES else "不明",
        "sport_category": data.get("sport_category") if data.get("sport_category") in SPORTS else "その他",
        "activity_area": "",
        "source_type": "self_registered",
        "source_url": data.get("evidence_url", ""),
        "verification_status": "claimed",
        "public_status": "published",
        "owner_notes": data.get("message", ""),
        "consent_status": "representative_claim",
    })
    timestamp = now()
    claim_id = slug("claim", circle_id + claimant_email + timestamp)
    conn.execute(
        """
        insert into circle_claims(claim_id, circle_id, claimant_name, claimant_email, university_email_verified, status, evidence_url, reviewed_at, created_at, updated_at)
        values(?,?,?,?,?,?,?,?,?,?)
        """,
        (claim_id, circle_id, claimant_name, claimant_email, 0, "pending", data.get("evidence_url", ""), "", timestamp, timestamp),
    )
    upsert_circle_public_profile(conn, circle_id, {
        "catch_copy": data.get("catch_copy") or f"{circle_name}の活動紹介",
        "introduction": data.get("introduction") or data.get("message", ""),
        "member_count": data.get("member_count", ""),
        "atmosphere": data.get("atmosphere", ""),
        "experience_ratio": data.get("experience_ratio", ""),
        "practice_frequency": data.get("practice_frequency", ""),
        "activity_place": data.get("activity_place", ""),
        "representative_comment": data.get("message", ""),
    })
    audit(conn, "representative_claim", "circle_claim", claim_id, {
        "circle_id": circle_id,
        "claimant_name": claimant_name,
        "claimant_email": claimant_email,
        "evidence_url": data.get("evidence_url", ""),
        "message": data.get("message", ""),
    })
    return claim_id, circle_id


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
    universities = conn.execute("select university_id, university_name, prefecture from universities").fetchall()
    for university in universities:
        count = conn.execute("select count(*) from circles where university_id=?", (university["university_id"],)).fetchone()[0]
        in_focus = university["prefecture"] in KANTO_PREFECTURES
        status = "partial" if count else ("not_started" if in_focus else "out_of_scope")
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
              priority=excluded.priority,
              source_search_query=coalesce(collection_targets.source_search_query, excluded.source_search_query),
              notes=excluded.notes,
              updated_at=excluded.updated_at
            """,
            (
                university["university_id"],
                status,
                1 if in_focus else 5,
                query,
                "",
                "重点収集対象" if in_focus else "通常収集対象",
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

    def require_admin(self):
        if not admin_auth_enabled():
            return True
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            self.send_auth_required()
            return False
        try:
            raw = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        except Exception:
            self.send_auth_required()
            return False
        username, separator, password = raw.partition(":")
        if not separator:
            self.send_auth_required()
            return False
        valid_user = hmac.compare_digest(username, ADMIN_USERNAME)
        valid_pass = hmac.compare_digest(password, ADMIN_PASSWORD)
        if not (valid_user and valid_pass):
            self.send_auth_required()
            return False
        return True

    def send_auth_required(self):
        body = json.dumps({"error": "admin authentication required"}, ensure_ascii=False).encode("utf-8")
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Circle Match Admin"')
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, status=200, cookies=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for cookie in cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, body, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, body, content_type="text/plain; charset=utf-8", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location, cookies=None):
        self.send_response(302)
        self.send_header("Location", location)
        for cookie in cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def cookie_value(self, name):
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return ""

    def send_file(self, path, content_type):
        if not path.exists():
            self.send_text(b"Not found\n", "text/plain; charset=utf-8", 404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def handle_google_callback(self, query):
        if not google_oauth_enabled():
            self.send_html(render_signin_html(), 503)
            return
        code = (query.get("code", [""])[0] or "").strip()
        state = (query.get("state", [""])[0] or "").strip()
        if not code or not state or not verify_oauth_state(state) or state != self.cookie_value("cm_oauth_state"):
            self.send_json({"error": "invalid oauth state"}, 400)
            return
        token = post_form("https://oauth2.googleapis.com/token", {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": oauth_redirect_uri(),
        })
        profile = fetch_json("https://openidconnect.googleapis.com/v1/userinfo", token["access_token"])
        with connect() as conn:
            user_id = upsert_oauth_user(conn, profile)
            session_id = create_user_session(conn, user_id)
            conn.commit()
        self.redirect("/", [
            "cm_oauth_state=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax",
            f"cm_session={session_id}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax{secure_cookie_suffix()}",
        ])

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self.send_html(render_public_html())
            elif parsed.path == "/auth/google":
                if not google_oauth_enabled():
                    self.send_html(render_signin_html(), 503)
                    return
                state = make_oauth_state()
                self.redirect(google_authorize_url(state), [f"cm_oauth_state={state}; Path=/; Max-Age=600; HttpOnly; SameSite=Lax{secure_cookie_suffix()}"])
            elif parsed.path == "/auth/google/callback":
                self.handle_google_callback(parse_qs(parsed.query))
            elif parsed.path == "/signin":
                self.send_html(render_signin_html())
            elif parsed.path == "/logout":
                self.redirect("/", ["cm_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"])
            elif parsed.path == "/post-match":
                self.send_html(render_post_match_html())
            elif parsed.path == "/representative":
                self.send_html(render_representative_html())
            elif parsed.path == "/sports":
                sport = (parse_qs(parsed.query).get("sport", ["野球"])[0] or "野球").strip()
                self.send_html(render_sport_html(sport))
            elif parsed.path == "/regions":
                region = (parse_qs(parsed.query).get("region", ["kanto"])[0] or "kanto").strip()
                self.send_html(render_region_html(region))
            elif parsed.path == "/circles":
                self.send_html(render_circles_html())
            elif parsed.path.startswith("/circles/"):
                profile_slug = unquote(parsed.path.removeprefix("/circles/").strip("/"))
                page = render_circle_profile_html(profile_slug)
                if page:
                    self.send_html(page)
                else:
                    self.send_html("<h1>サークルページが見つかりません</h1>".encode("utf-8"), 404)
            elif parsed.path == "/assets/hero-court.png":
                self.send_file(ROOT / "hero-court.png", "image/png")
            elif parsed.path.startswith("/assets/sports/"):
                self.send_file(ROOT / "sports" / Path(parsed.path).name, "image/png")
            elif parsed.path == "/admin":
                if not self.require_admin():
                    return
                self.send_html(render_admin_html())
            elif parsed.path == "/privacy":
                self.send_html(privacy_page())
            elif parsed.path == "/terms":
                self.send_html(terms_page())
            elif parsed.path == "/about-data":
                self.send_html(about_data_page())
            elif parsed.path == "/contact":
                self.send_html(contact_page())
            elif parsed.path == "/healthz":
                self.send_json({"ok": True, **summary()})
            elif parsed.path == "/robots.txt":
                self.send_text(robots_txt())
            elif parsed.path == "/sitemap.xml":
                self.send_text(sitemap_xml(), "application/xml; charset=utf-8")
            elif parsed.path == "/api/summary":
                self.send_json(summary())
            elif parsed.path == "/api/universities":
                self.send_json(rows("select * from universities order by prefecture, university_name"))
            elif parsed.path == "/api/sports":
                self.send_json(sport_options())
            elif parsed.path == "/api/regions":
                self.send_json(region_options())
            elif parsed.path == "/api/circles":
                self.send_json(search_circles(parse_qs(parsed.query)))
            elif parsed.path == "/api/matches":
                self.send_json(search_matches(parse_qs(parsed.query)))
            elif parsed.path == "/api/sport_overview":
                self.send_json(sport_overview(parse_qs(parsed.query)))
            elif parsed.path == "/api/region_overview":
                self.send_json(region_overview(parse_qs(parsed.query)))
            elif parsed.path == "/api/me":
                self.send_json(current_user(self.cookie_value("cm_session")))
            elif parsed.path == "/api/collection_status":
                if not self.require_admin():
                    return
                self.send_json(collection_status())
            elif parsed.path == "/api/candidates":
                if not self.require_admin():
                    return
                self.send_json(candidate_rows())
            elif parsed.path == "/api/admin_metrics":
                if not self.require_admin():
                    return
                self.send_json(admin_metrics())
            elif parsed.path == "/api/privacy_metrics":
                if not self.require_admin():
                    return
                self.send_json(privacy_metrics())
            elif parsed.path == "/api/audit_logs":
                if not self.require_admin():
                    return
                self.send_json(rows("select * from audit_logs order by audit_id desc limit 200"))
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/auth/supabase":
                if not supabase_auth_enabled():
                    self.send_json({"error": "Supabase Auth is not configured"}, 503)
                    return
                data = self.read_json()
                access_token = (data.get("access_token") or "").strip()
                if not access_token:
                    self.send_json({"error": "access_token is required"}, 400)
                    return
                profile = fetch_supabase_user(access_token)
                with connect() as conn:
                    user_id = upsert_supabase_user(conn, profile)
                    session_id = create_user_session(conn, user_id)
                    conn.commit()
                self.send_json({"ok": True, "user": current_user(session_id)}, 200, [
                    f"cm_session={session_id}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax{secure_cookie_suffix()}"
                ])
                return
            if parsed.path == "/api/claims":
                data = self.read_json()
                with connect() as conn:
                    claim_id, circle_id = create_circle_claim(conn, data)
                    conn.commit()
                    self.send_json({"ok": True, "claim_id": claim_id, "circle_id": circle_id, "profile_url": f"/circles/{quote(circle_id)}"})
                return
            if parsed.path == "/api/matches/public":
                data = self.read_json()
                user = current_user(self.cookie_value("cm_session"))
                if not user.get("authenticated"):
                    self.send_json({"error": "login required"}, 401)
                    return
                with connect() as conn:
                    match_post_id = create_public_match_post(conn, data, user)
                    conn.commit()
                    self.send_json({"ok": True, "match_post_id": match_post_id})
                return
            if not self.require_admin():
                return
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


def sport_options():
    with connect() as conn:
        db_sports = [
            row["sport_category"]
            for row in conn.execute(
                "select sport_category from circles where sport_category is not null and sport_category<>'' group by sport_category order by count(*) desc, sport_category"
            ).fetchall()
        ]
    return list(dict.fromkeys([*SPORTS, *db_sports]))


def region_options():
    return [{"value": key, "label": data["label"], "prefectures": data["prefectures"]} for key, data in REGION_GROUPS.items()]


def region_prefectures(region):
    return REGION_GROUPS.get(region, {}).get("prefectures", [])


def search_circles(params):
    query = (params.get("q", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    region = (params.get("region", [""])[0] or "").strip()
    organization_type = (params.get("organization_type", [""])[0] or "").strip()
    sport = (params.get("sport", [""])[0] or "").strip()
    status = (params.get("status", [""])[0] or "").strip()
    sort = (params.get("sort", ["university"])[0] or "university").strip()
    where = []
    args = []
    if query:
        where.append("(c.circle_name like ? or c.sport_category like ? or c.activity_area like ? or u.university_name like ?)")
        args.extend([f"%{query}%"] * 4)
    if prefecture:
        where.append("u.prefecture=?")
        args.append(prefecture)
    elif region:
        prefs = region_prefectures(region)
        if prefs:
            where.append("u.prefecture in (%s)" % ",".join(["?"] * len(prefs)))
            args.extend(prefs)
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
          p.profile_slug,
          u.university_name,
          u.prefecture,
          u.city
        from circles c
        join universities u on u.university_id=c.university_id
        left join circle_public_profiles p on p.circle_id=c.circle_id and p.is_published=1
    """
    if where:
        sql += " where " + " and ".join(where)
    order_by = {
        "university": "u.university_name, c.sport_category, c.circle_name",
        "circle": "c.circle_name, u.university_name",
        "prefecture": "u.prefecture, u.university_name, c.circle_name",
        "sport": "c.sport_category, u.university_name, c.circle_name",
        "type": "c.organization_type, u.university_name, c.circle_name",
        "status": "c.verification_status, u.university_name, c.circle_name",
        "updated": "c.updated_at desc, u.university_name, c.circle_name",
    }.get(sort, "u.university_name, c.sport_category, c.circle_name")
    sql += " order by " + order_by
    result = rows(sql, args)
    for row in result:
        row["profile_url"] = f"/circles/{quote(row['profile_slug'])}" if row.get("profile_slug") else ""
    return result


def search_matches(params):
    sport = (params.get("sport", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    region = (params.get("region", [""])[0] or "").strip()
    where = []
    args = []
    if sport:
        where.append("c.sport_category=?")
        args.append(sport)
    if prefecture:
        where.append("u.prefecture=?")
        args.append(prefecture)
    elif region:
        prefs = region_prefectures(region)
        if prefs:
            where.append("u.prefecture in (%s)" % ",".join(["?"] * len(prefs)))
            args.extend(prefs)
    sql = """
        select m.*, c.circle_name, c.sport_category, u.university_name, u.prefecture
        from match_posts m join circles c on c.circle_id=m.circle_id join universities u on u.university_id=c.university_id
    """
    if where:
        sql += " where " + " and ".join(where)
    sql += " order by coalesce(m.scheduled_at, ''), m.created_at desc"
    return rows(sql, args)


def sport_overview(params):
    sport = (params.get("sport", ["野球"])[0] or "野球").strip()
    region = (params.get("region", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    if prefecture:
        matching_region = next((key for key, data in REGION_GROUPS.items() if prefecture in data["prefectures"]), "")
        if region and prefecture not in region_prefectures(region):
            prefecture = ""
        elif not region:
            region = matching_region
    all_circles = search_circles({"sport": [sport]})
    all_matches = search_matches({"sport": [sport]})
    region_circles = search_circles({"sport": [sport], "region": [region]})
    region_matches = search_matches({"sport": [sport], "region": [region]})
    circles = search_circles({"sport": [sport], "region": [region], "prefecture": [prefecture]})
    matches = search_matches({"sport": [sport], "region": [region], "prefecture": [prefecture]})
    region_summaries = []
    for key, data in REGION_GROUPS.items():
        prefs = set(data["prefectures"])
        circle_count = sum(1 for c in all_circles if c["prefecture"] in prefs)
        match_count = sum(1 for m in all_matches if m["prefecture"] in prefs)
        region_summaries.append({
            "value": key,
            "label": data["label"],
            "circle_count": circle_count,
            "match_count": match_count,
        })
    areas = []
    region_prefs = region_prefectures(region)
    for pref in region_prefs if region_prefs else PREFECTURES:
        circle_count = sum(1 for c in region_circles if c["prefecture"] == pref)
        match_count = sum(1 for m in region_matches if m["prefecture"] == pref)
        if circle_count or match_count or region:
            areas.append({"prefecture": pref, "circle_count": circle_count, "match_count": match_count})
    return {
        "sport": sport,
        "region": region,
        "prefecture": prefecture,
        "circle_count": len(circles),
        "match_count": len(matches),
        "regions": region_summaries,
        "areas": areas,
        "matches": matches,
        "circles": circles[:250],
    }


def region_overview(params):
    region = (params.get("region", ["kanto"])[0] or "kanto").strip()
    if region not in REGION_GROUPS:
        region = "kanto"
    sport = (params.get("sport", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    if prefecture and prefecture not in region_prefectures(region):
        prefecture = ""
    region_label = REGION_GROUPS[region]["label"]
    region_circles_all = search_circles({"region": [region]})
    region_matches_all = search_matches({"region": [region]})
    circles = search_circles({"region": [region], "sport": [sport], "prefecture": [prefecture]})
    matches = search_matches({"region": [region], "sport": [sport], "prefecture": [prefecture]})
    sports = []
    for name in sport_options():
        circle_count = sum(1 for c in region_circles_all if c["sport_category"] == name)
        match_count = sum(1 for m in region_matches_all if m["sport_category"] == name)
        if circle_count or match_count or name in SPORTS:
            sports.append({
                "name": name,
                "circle_count": circle_count,
                "match_count": match_count,
            })
    sports.sort(key=lambda item: (-item["match_count"], -item["circle_count"], item["name"]))
    scoped_circles = search_circles({"region": [region], "sport": [sport]})
    scoped_matches = search_matches({"region": [region], "sport": [sport]})
    areas = []
    for pref in region_prefectures(region):
        circle_count = sum(1 for c in scoped_circles if c["prefecture"] == pref)
        match_count = sum(1 for m in scoped_matches if m["prefecture"] == pref)
        if circle_count or match_count or sport:
            areas.append({
                "prefecture": pref,
                "circle_count": circle_count,
                "match_count": match_count,
            })
    return {
        "region": region,
        "region_label": region_label,
        "sport": sport,
        "prefecture": prefecture,
        "region_circle_count": len(region_circles_all),
        "region_match_count": len(region_matches_all),
        "circle_count": len(circles),
        "match_count": len(matches),
        "sports": sports,
        "areas": areas,
        "matches": matches[:50],
        "circles": circles[:250],
    }


def current_user(session_id):
    if not session_id:
        return {"authenticated": False}
    with connect() as conn:
        row = conn.execute(
            """
            select u.user_id, u.email, u.display_name, u.picture_url
            from user_sessions s join user_accounts u on u.user_id=s.user_id
            where s.session_id=? and datetime(s.expires_at) > datetime('now')
            """,
            (session_id,),
        ).fetchone()
        if not row:
            return {"authenticated": False}
        return {"authenticated": True, **dict(row)}


def create_public_match_post(conn, data, user):
    if not user.get("authenticated"):
        raise ValueError("login required")
    circle_id = (data.get("circle_id") or "").strip()
    if not circle_id:
        raise ValueError("circle_id is required")
    circle = conn.execute("select circle_id from circles where circle_id=?", (circle_id,)).fetchone()
    if not circle:
        raise ValueError("circle not found")
    match_type = (data.get("match_type") or "練習試合").strip()
    period_start = (data.get("period_start") or "").strip()
    period_end = (data.get("period_end") or "").strip()
    place = (data.get("place") or "").strip()
    practice_detail = (data.get("practice_detail") or "").strip()
    if not period_start or not period_end or not place or not practice_detail:
        raise ValueError("period_start, period_end, place and practice_detail are required")
    timestamp = now()
    scheduled_at = f"{period_start}〜{period_end}" if period_start != period_end else period_start
    capacity = (data.get("capacity") or "").strip()
    conditions = (data.get("conditions") or "").strip()
    if capacity:
        conditions = f"希望人数・形式: {capacity}\n{conditions}".strip()
    if practice_detail:
        conditions = f"{practice_detail}\n{conditions}".strip()
    entity_id = slug("m", circle_id + match_type + period_start + period_end + timestamp)
    conn.execute(
        """
        insert into match_posts(match_post_id, circle_id, match_type, level_label, scheduled_at,
          period_start, period_end, place, practice_detail, capacity, conditions, status, created_by, created_at, updated_at)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            entity_id,
            circle_id,
            match_type,
            (data.get("level_label") or "").strip(),
            scheduled_at,
            period_start,
            period_end,
            place,
            practice_detail,
            capacity,
            conditions,
            "open",
            user.get("user_id", ""),
            timestamp,
            timestamp,
        ),
    )
    audit(conn, "public_insert", "match_post", entity_id, {
        "circle_id": circle_id,
        "match_type": match_type,
        "period_start": period_start,
        "period_end": period_end,
        "created_by": user.get("user_id", ""),
    })
    return entity_id


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
        if is_invalid_circle_name(circle_name, item.get("source_url", "")):
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
        if is_invalid_circle_name(candidate_name, item.get("source_url", "")):
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
        if not is_local_host() and not admin_auth_enabled():
            raise RuntimeError("CIRCLEMATCH_ADMIN_PASSWORD is required when HOST is not local")
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
