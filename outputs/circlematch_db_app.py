import csv
import base64
from contextlib import contextmanager
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("CIRCLEMATCH_DB_PATH", ROOT / "circlematch.sqlite"))
PUBLIC_SEED_PATH = Path(os.environ.get("CIRCLEMATCH_PUBLIC_SEED_PATH", ROOT / "public_circles_seed.csv"))
SOCIAL_SEED_PATH = Path(os.environ.get("CIRCLEMATCH_SOCIAL_SEED_PATH", ROOT / "social_circles_seed.csv"))
LOG_PATH = ROOT.parent / "work" / "circlematch_db_app.log"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8787"))
SITE_NAME = os.environ.get("CIRCLEMATCH_SITE_NAME", "Circle Match")
SITE_OPERATOR = os.environ.get("CIRCLEMATCH_OPERATOR", "Circle Match 運営")
CONTACT_EMAIL = os.environ.get("CIRCLEMATCH_CONTACT_EMAIL", "contact@circle-match.jp")
POLICY_UPDATED_AT = "2026年8月31日"
SITE_BASE_URL = os.environ.get("CIRCLEMATCH_SITE_BASE_URL", "")
ADMIN_USERNAME = os.environ.get("CIRCLEMATCH_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("CIRCLEMATCH_ADMIN_PASSWORD", "")
GOOGLE_CLIENT_ID = os.environ.get("CIRCLEMATCH_GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("CIRCLEMATCH_GOOGLE_CLIENT_SECRET", "")
SUPABASE_URL = os.environ.get("CIRCLEMATCH_SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("CIRCLEMATCH_SUPABASE_ANON_KEY", "")
SESSION_SECRET = os.environ.get("CIRCLEMATCH_SESSION_SECRET", ADMIN_PASSWORD or "local-dev-session-secret")
EMAIL_AUTH_ENABLED = os.environ.get("CIRCLEMATCH_EMAIL_AUTH_ENABLED", "").lower() == "true"
RESEND_API_KEY = os.environ.get("CIRCLEMATCH_RESEND_API_KEY", "")
EMAIL_FROM = os.environ.get("CIRCLEMATCH_EMAIL_FROM", "")
EMAIL_NOTIFICATIONS_ENABLED = os.environ.get("CIRCLEMATCH_EMAIL_NOTIFICATIONS_ENABLED", "").lower() == "true"
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

SPORTS = ["サッカー・フットサル", "バスケットボール", "テニス", "ピックルボール", "バレーボール", "野球", "バドミントン", "ラグビー", "ランニング", "その他"]
POPULAR_SPORTS = [
    ("野球", "Baseball", "BS", "#1f6f8b", "baseball.png"),
    ("サッカー・フットサル", "Football & Futsal", "SF", "#0f7a62", "soccer.png"),
    ("テニス", "Tennis", "TN", "#b2601d", "tennis.png"),
    ("ピックルボール", "Pickleball", "PB", "#356c64", "pickleball.png"),
    ("卓球", "Table Tennis", "TT", "#a4432d", "table-tennis.png"),
    ("ゴルフ", "Golf", "GF", "#3c764c", "golf.png"),
    ("バスケットボール", "Basketball", "BK", "#9a3b24", "basketball.png"),
    ("バレーボール", "Volleyball", "VB", "#315b9a", "volleyball.png"),
    ("バドミントン", "Badminton", "BD", "#6d4aa2", "badminton.png"),
    ("ランニング", "Running", "RN", "#cc5c2c", "running.png"),
    ("ラグビー", "Rugby", "RG", "#7a4b2b", "rugby.png"),
    ("カラオケ", "Karaoke", "KA", "#42526b", "karaoke.png"),
    ("イベント", "Events", "EV", "#356c64", "events.png"),
    ("ボードゲーム", "Board Games", "BG", "#356c64", "board-games.png"),
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
ORGANIZATION_TYPES = ["体育会", "部活", "公認サークル", "同好会", "非公認サークル", "学生団体", "社会人サークル", "不明"]
EVENT_TYPES = ["大会", "交流イベント", "練習試合", "合同練習"]
EVENT_ACCEPTANCE_MODES = {"first_come", "approval"}
EVENT_PARTICIPATION_TYPES = {"individual", "team", "both"}
EVENT_STATUSES = {"draft", "published", "closed", "cancelled"}
APPLICATION_STATUSES = {"pending", "confirmed", "declined", "cancelled"}
ADSENSE_HEAD = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5276152865683531" crossorigin="anonymous"></script>'
ADSENSE_ADS_TXT = b"google.com, pub-5276152865683531, DIRECT, f08c47fec0942fa0\n"
BRAND_WORDMARK = '<span class="brand-wordmark"><span class="brand-word-circle">Circle</span><span class="brand-word-match">Match</span></span>'
BRAND_LOGO_STYLE = """
  <link rel="icon" type="image/png" sizes="256x256" href="/assets/circle-match-mark.png?v=20260809">
  <link rel="apple-touch-icon" sizes="256x256" href="/assets/circle-match-mark.png?v=20260809">
  <style id="circle-match-brand-logo">
    a.brand{display:inline-flex;align-items:center;gap:9px;color:#102A43;font-size:20px;line-height:1;font-weight:900;letter-spacing:0;text-decoration:none}
    a.brand::before{content:"";display:block;flex:0 0 38px;width:38px;height:38px;background:url("/assets/circle-match-mark.png?v=20260809") center/contain no-repeat}
    a.brand .mark{display:none}
    a.brand .brand-wordmark{display:inline-flex;align-items:baseline;gap:.23em;white-space:nowrap}
    a.brand .brand-word-circle{color:#102A43}
    a.brand .brand-word-match{color:#F15A2A}
    @media(max-width:620px){a.brand{font-size:18px}a.brand::before{flex-basis:34px;width:34px;height:34px}}
    .account-logout{display:inline-flex;margin:0}.account-logout button{min-height:38px;border:0;background:transparent;color:#405164;padding:8px;font:inherit;font-size:13px;cursor:pointer;white-space:nowrap}
    nav a.cm-account{display:inline-flex;align-items:center;min-height:38px;padding:8px 10px;border:1px solid #e15b31;border-radius:8px;color:#e15b31;background:#fff;text-decoration:none;white-space:nowrap;font-size:14px;font-weight:800}
    header .top>.nav{align-items:center}header .top>.nav>a{display:inline-flex;align-items:center;justify-content:center;min-height:44px;line-height:1.4}
    @media(max-width:620px){.site-nav a.brand .brand-wordmark{display:none}.site-nav .main-nav a,.site-nav .account-logout button{padding:7px;font-size:12px}.site-nav a.brand{gap:0}.site-nav .main-nav{flex-wrap:wrap;justify-content:flex-end}}
  </style>
"""


def with_adsense(html):
    html = html.replace('><span class="mark">CM</span><span>__SITE_NAME__</span></a>', f'>{BRAND_WORDMARK}</a>')
    html = html.replace('>__SITE_NAME__</a>', f'>{BRAND_WORDMARK}</a>')
    if "circle-match-brand-logo" not in html:
        html = html.replace("</head>", f"{BRAND_LOGO_STYLE}</head>", 1)
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
    .section{margin-top:24px}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.panel-head{padding:18px;border-bottom:1px solid var(--line);display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap}.panel-head h2{margin:0;font-size:24px}.panel-head p{margin:8px 0 0;color:var(--muted);line-height:1.7;max-width:760px}.section-link{padding:0 14px 16px}.section-link a{color:#31506b;font-weight:900}.ssr-error{font-size:13px;line-height:1.45;color:#a54822}
    .database-value{padding:22px}.database-value h2{margin:0;font-size:24px}.database-value>p{margin:10px 0 0;color:#405164;line-height:1.8;max-width:860px}.database-points{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:18px}.database-point{border:1px solid var(--line);border-radius:8px;padding:15px;background:#f9fbfd}.database-point strong{display:block;font-size:16px}.database-point p{margin:7px 0 0;color:var(--muted);font-size:14px;line-height:1.65}.database-links{display:flex;gap:10px;flex-wrap:wrap;margin-top:17px}.database-links a{font-weight:900;color:#31506b}
    .filters{display:grid;grid-template-columns:minmax(220px,1fr) repeat(5,150px);gap:9px;padding:14px;background:#f9fbfd;border-bottom:1px solid var(--line)}input,select,textarea{width:100%;border:1px solid #cbd7e2;border-radius:8px;min-height:42px;padding:10px 11px;font:inherit;background:#fff;color:var(--ink)}
    .match-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:14px}.match-card{border:1px solid var(--line);border-radius:8px;padding:15px;background:#fff;display:flex;flex-direction:column;gap:12px;min-height:230px}.match-card h3{margin:0;font-size:18px}.meta{display:grid;gap:6px;color:var(--muted);font-size:13px;line-height:1.5}.tagline{color:#405164;line-height:1.7;margin:0}.badges{display:flex;gap:6px;flex-wrap:wrap}.badge{display:inline-flex;align-items:center;min-height:23px;padding:3px 8px;border-radius:999px;background:#eef4f8;color:#405164;font-size:12px;font-weight:900}.badge.open{background:#e2f5ed;color:#0d674f}.badge.type{background:#e8eef8;color:#24558a}
    .empty{padding:28px;color:var(--muted);line-height:1.8}.sport-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.sport-card{position:relative;overflow:hidden;min-height:176px;border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:0;background:#132238;text-decoration:none;color:#fff;box-shadow:0 14px 30px rgba(20,36,56,.18)}.sport-card:hover{box-shadow:0 18px 38px rgba(20,36,56,.25);transform:translateY(-2px)}.sport-visual{position:absolute;inset:0;overflow:hidden}.sport-visual img{width:100%;height:100%;object-fit:cover;filter:saturate(1.12) contrast(1.05)}.sport-card::before{content:"";position:absolute;inset:0;z-index:1;background:linear-gradient(90deg,rgba(9,18,31,.9),rgba(9,18,31,.52) 54%,rgba(9,18,31,.08))}.sport-card::after{content:"";position:absolute;z-index:1;right:-44px;bottom:-56px;width:170px;height:170px;border-radius:50%;background:rgba(255,255,255,.12)}.sport-copy{position:relative;z-index:2;display:grid;gap:7px;max-width:68%;padding:18px}.sport-copy strong{font-size:25px;line-height:1.08;text-shadow:0 2px 12px rgba(0,0,0,.35)}.sport-copy em{font-style:normal;color:rgba(255,255,255,.8);font-size:12px;font-weight:850}.sport-card b{position:absolute;z-index:2;left:18px;bottom:16px;width:max-content;min-height:34px;border-radius:999px;display:inline-flex;align-items:center;padding:7px 12px;background:rgba(255,255,255,.18);color:#fff;font-size:12px;backdrop-filter:blur(8px)}
    .map-board{padding:18px;background:linear-gradient(180deg,#fff,#f7fbf1)}.map-headline{margin:0 0 16px;font-size:25px;font-weight:950;line-height:1.25}.map-headline strong{color:var(--accent);font-size:38px}.map-stage{position:relative;min-height:560px;border:1px solid #d7e4cc;border-radius:8px;overflow:hidden;background:radial-gradient(circle at 38% 48%,rgba(157,207,79,.14),transparent 34%),linear-gradient(135deg,#fbfdf8,#eef7e6)}.japan-silhouette{position:absolute;left:8%;top:8%;width:54%;height:84%;filter:drop-shadow(0 9px 13px rgba(49,111,31,.22))}.japan-silhouette .country{fill:#83c945;stroke:#fff;stroke-width:1.2;stroke-linejoin:round}.japan-silhouette .outline{fill:none;stroke:rgba(49,111,31,.22);stroke-width:1.8}.map-region-buttons{position:absolute;right:22px;top:22px;z-index:2;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;width:360px}.map-region{display:grid;gap:5px;min-height:98px;padding:12px 14px;border:1px solid #cbd7e2;border-radius:8px;background:linear-gradient(rgba(255,255,255,.96),rgba(242,245,248,.94));box-shadow:0 8px 18px rgba(27,45,69,.13);color:var(--ink);text-align:center;text-decoration:none;font-weight:900;backdrop-filter:blur(3px)}.map-region strong{font-size:19px;line-height:1.2}.map-region:hover{border-color:var(--accent);box-shadow:0 12px 24px rgba(225,91,49,.18);transform:translateY(-2px)}.map-region span{color:#516680;font-size:13px;font-weight:850}.map-region .region-note{display:inline-flex;justify-content:center;justify-self:center;width:max-content;max-width:100%;padding:2px 8px;border-radius:999px;background:#fff3e8;color:#a54822;font-size:11px;font-weight:950;line-height:1.5}
    .coverage-notice{display:none;margin-top:14px;border:1px solid #f1d2be;background:#fff8f4;color:#7b3b22;border-radius:8px;padding:12px 14px;font-weight:850;line-height:1.7}
    footer{max-width:1180px;margin:0 auto;padding:0 18px 34px;color:var(--muted);font-size:13px;display:flex;gap:12px;flex-wrap:wrap}.admin-link{color:#65758a}
    @media(max-width:900px){.stats{grid-template-columns:repeat(2,minmax(0,1fr));margin-top:12px}.filters{grid-template-columns:1fr 1fr}.match-grid{grid-template-columns:1fr}.sport-grid{grid-template-columns:1fr}.database-points{grid-template-columns:1fr}.hero{min-height:520px}.map-stage{min-height:520px}.japan-silhouette{left:6%;width:52%}.map-region-buttons{right:14px;width:330px;gap:10px}.map-region{min-height:94px;padding:11px 12px}.map-region strong{font-size:18px}}
    @media(max-width:760px){.map-headline{font-size:20px}.map-headline strong{font-size:30px}.map-stage{min-height:auto;padding:14px;display:grid;gap:12px}.japan-silhouette{position:relative;left:auto;top:auto;width:100%;height:auto;max-height:320px}.map-region-buttons{position:relative;right:auto;top:auto;width:auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.map-region{min-width:0}.map-region:hover{transform:translateY(-2px)}}
    @media(max-width:620px){.top{align-items:flex-start}.nav{gap:9px}.filters{grid-template-columns:1fr}.hero-inner{padding-top:70px}.metric strong{font-size:22px}}
  </style>
</head>
<body>
  <header class="topbar"><div class="top"><a class="brand" href="/"><span class="mark">CM</span><span>__SITE_NAME__</span></a><nav class="nav"><a href="/social">社会人はこちら</a><a class="signup-user" href="/representative">団体代表者の方へ</a></nav></div></header>
  <section class="hero"><img src="/assets/hero-court.png" alt="屋外コートで交流する大学生グループ"><div class="shade"></div><div class="hero-inner"><p class="eyebrow">Sports Circle Database / Practice Match</p><h1>練習相手も、仲間も、ここで見つかる。</h1><p class="lead">Circle Matchは、大学・社会人のスポーツ団体情報を、競技・地域・出典ごとに整理して探せるサークルDBです。練習試合、合同練習、助っ人募集、交流イベントにも活用できます。</p><div class="actions"><a class="button secondary hero-cta" href="#matches">募集中はこちら</a><a class="button primary hero-cta" href="/representative?intent=post-match">募集を出す</a></div></div></section>
  <main>
    <section class="stats"><div class="metric"><span>対象大学</span><strong id="uniCount">__SSR_UNIVERSITY_COUNT__</strong></div><div class="metric"><span>候補サークル</span><strong id="circleCount">__SSR_CIRCLE_COUNT__</strong></div><div class="metric"><span>検証済み/申請済み</span><strong id="verifiedCount">__SSR_VERIFIED_COUNT__</strong></div><div class="metric"><span>募集中</span><strong id="matchCount">__SSR_MATCH_COUNT__</strong></div></section>
    <section class="section panel"><div class="panel-head"><div><h2>スポーツから探す</h2><p>競技を押すと、サークルDBと交流募集を同時に確認できます。</p></div></div><div class="sport-grid" id="sportGrid"></div><div class="section-link"><a href="/circles">サークルDBで候補を広げる</a></div></section>
    <div id="coverageNotice" class="coverage-notice">関東以外の地域は現在DB拡充中です。掲載漏れや訂正は問い合わせから連絡してください。</div>
    <section id="matches" class="section panel"><div class="panel-head"><div><h2>募集掲示板</h2><p>地域、都道府県、競技、大学名、団体名で絞り込めます。募集中が少ない時は、その条件のDB候補へ広げられます。</p></div><a class="button light" href="/social">社会人サークルを見る</a></div><div class="filters"><input id="q" placeholder="大学名・団体名・場所で検索"><select id="regionFilter"><option value="">全地域</option></select><select id="prefFilter"><option value="">全都道府県</option></select><input id="sportFilter" list="sportOptions" placeholder="競技名を入力" aria-label="競技名で絞り込み" autocomplete="off"><datalist id="sportOptions"></datalist><select id="typeFilter"><option value="">全募集</option><option>練習試合</option><option>合同練習</option><option>助っ人募集</option><option>大会参加者募集</option></select><select id="sortFilter"><option value="date">日時が近い順</option><option value="new">新着順</option><option value="university">大学名順</option><option value="sport">競技順</option></select></div><div id="matchList" class="match-grid" aria-live="polite"></div><div class="section-link"><a id="dbBridge" href="/circles">同じ条件でサークルDBを見る</a></div></section>
    <section class="section panel"><div class="panel-head"><div><h2>地域から探す</h2><p>地図上の地域を押すと、募集掲示板とDB候補をその地域で絞り込めます。</p></div></div><div class="map-board"><p class="map-headline"><strong id="mapCircleCount">__SSR_CIRCLE_COUNT__</strong>件の大学サークル候補から地域で探す</p><div class="map-stage"><svg class="japan-silhouette" id="japanMap" viewBox="0 0 520 560" role="img" aria-label="日本地図"></svg><div class="map-region-buttons" id="regionGrid"></div></div></div></section>
    <section class="section panel database-value"><h2>Circle Match DBとは</h2><p>大学・社会人のスポーツ団体や交流相手を、競技・地域から探せるサービスです。</p><div class="database-links"><a href="/circles">大学サークルDBを見る</a><a href="/social/circles">社会人サークルDBを見る</a><a href="/about-data">データの掲載・更新方針</a></div></section>
  </main>
  <footer><span>サイトへのご意見・ご要望はこちら: <a class="admin-link" href="mailto:__CONTACT_EMAIL__">__CONTACT_EMAIL__</a></span><a class="admin-link" href="/circles">サークルDB</a><a class="admin-link" href="/about-data">データ方針</a><a class="admin-link" href="/guides">サークル運営ガイド</a><a class="admin-link" href="/operator">運営者情報</a><a class="admin-link" href="/terms">利用規約</a><a class="admin-link" href="/contact">問い合わせ</a></footer>
  <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
  <script>
    const prefs = __PREFS__;
    const regions = __REGIONS__;
    const sports = __SPORTS__;
    const popularSports = __POPULAR_SPORTS__;
    const initialSummary = __INITIAL_SUMMARY__;
    const params = new URLSearchParams(location.search);
    let allCircleCache = null;
    let allMatchCache = null;
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function fillSelect(el, values, first){el.innerHTML=`<option value="">${first}</option>`+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("")}
    function fillSportOptions(){ $("sportOptions").innerHTML=sports.map(v=>`<option value="${esc(v)}"></option>`).join("") }
    function fillRegions(){ $("regionFilter").innerHTML='<option value="">全地域</option>'+regions.map(r=>`<option value="${esc(r.value)}">${esc(r.label)}</option>`).join("") }
    async function drawJapanMap(){if(!window.d3||!window.topojson)return; const svg=d3.select("#japanMap"); if(svg.select(".country").size())return; const world=await d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json"); const countries=topojson.feature(world, world.objects.countries); const japan=countries.features.find(d=>String(d.id)==="392"); if(!japan)return; const projection=d3.geoMercator().fitSize([520,560],japan); const path=d3.geoPath(projection); svg.append("path").datum(japan).attr("class","country").attr("d",path); svg.append("path").datum(topojson.mesh(world, world.objects.countries, (a,b)=>String(a.id)==="392"||String(b.id)==="392")).attr("class","outline").attr("d",path)}
    function renderSports(){ $("sportGrid").innerHTML=popularSports.map(s=>`<a class="sport-card" style="--tone:${esc(s.color)}" data-code="${esc(s.code)}" href="/sports?sport=${encodeURIComponent(s.name)}"><span class="sport-visual"><img src="/assets/sports/${esc(s.image)}?v=20260706v1" alt=""></span><span class="sport-copy"><strong>${esc(s.name)}</strong><em>${esc(s.label)}</em></span><b>相手を探す</b></a>`).join("") }
    function renderRegions(regionData){const pos={hokkaido:"pos-hokkaido",tohoku:"pos-tohoku",kanto:"pos-kanto",chubu:"pos-chubu",kansai:"pos-kansai",chugoku_shikoku:"pos-chugoku_shikoku",kyushu:"pos-kyushu"}; const total=regionData.reduce((sum,r)=>sum+(r.circle_count||0),0); $("mapCircleCount").textContent=total; $("regionGrid").innerHTML=regions.map(r=>{const stat=regionData.find(item=>item.value===r.value)||{}; const note=r.value==="kanto"?"":`<span class="region-note">DB拡充中</span>`; return `<a class="map-region ${esc(pos[r.value]||"")}" href="/regions?region=${encodeURIComponent(r.value)}"><strong>${esc(r.label)}</strong><span>募集 ${stat.match_count||0}件</span><span>DB ${stat.circle_count||0}件</span>${note}</a>`}).join("")}
    function selectedRegion(){return regions.find(r=>r.value===$("regionFilter").value)}
    function prefValues(){return selectedRegion()?.prefectures || prefs}
    function syncPrefOptions(){const current=$("prefFilter").value; fillSelect($("prefFilter"),prefValues(),selectedRegion()?`${selectedRegion().label}すべて`:"全都道府県"); if(prefValues().includes(current)) $("prefFilter").value=current}
    function currentQuery(){const qs=new URLSearchParams({audience:"university",q:$("q").value,prefecture:$("prefFilter").value,sport:$("sportFilter").value}); if($("regionFilter").value) qs.set("region",$("regionFilter").value); return qs}
    async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
    function updateStats(stats,matches){$("uniCount").textContent=stats.universities; $("circleCount").textContent=stats.circles; $("verifiedCount").textContent=stats.verified_circles; $("matchCount").textContent=matches.length}
    function applyInitialSummary(){if(!initialSummary)return; $("uniCount").textContent=initialSummary.universities; $("circleCount").textContent=initialSummary.circles; $("verifiedCount").textContent=initialSummary.verified_circles; $("matchCount").textContent=initialSummary.match_posts; $("mapCircleCount").textContent=initialSummary.circles}
    function matchesFilter(m){const q=$("q").value.trim().toLowerCase(); const sport=$("sportFilter").value.trim().toLowerCase(); const blob=[m.university_name,m.circle_name,m.sport_category,m.prefecture,m.place,m.conditions,m.level_label].join(" ").toLowerCase(); if(q && !blob.includes(q))return false; if($("typeFilter").value && m.match_type!==$("typeFilter").value)return false; if(sport && !String(m.sport_category||"").toLowerCase().includes(sport))return false; if($("prefFilter").value && m.prefecture!==$("prefFilter").value)return false; return true}
    function sortMatches(rows){const v=$("sortFilter").value; return rows.slice().sort((a,b)=>{if(v==="new")return String(b.created_at||"").localeCompare(String(a.created_at||"")); if(v==="university")return String(a.university_name||"").localeCompare(String(b.university_name||""),"ja"); if(v==="sport")return String(a.sport_category||"").localeCompare(String(b.sport_category||""),"ja"); return String(a.scheduled_at||"9999").localeCompare(String(b.scheduled_at||"9999"))})}
    function card(m){return `<article class="match-card"><div class="badges"><span class="badge open">${esc(m.status||"open")}</span><span class="badge type">${esc(m.match_type)}</span><span class="badge">${esc(m.sport_category||"競技未設定")}</span></div><h3>${esc(m.circle_name)}</h3><div class="meta"><span>${esc(m.university_name)} / ${esc(m.prefecture||"地域未設定")}</span><span>${esc(m.scheduled_at||"日時未定")} / ${esc(m.place||"場所未定")}</span><span>${esc(m.level_label||"レベル未設定")}</span></div><p class="tagline">${esc(m.conditions||"条件は登録後に調整します。")}</p></article>`}
    function badge(v,cls=""){return `<span class="badge ${cls}">${esc(v)}</span>`}
    async function refresh(){const qs=currentQuery(); $("dbBridge").href="/circles?"+qs; const [all,stats,regionData]=await Promise.all([api("/api/matches?"+qs),api("/api/circle-stats?"+qs),api("/api/region-counts?audience=university")]); const data=sortMatches(all.filter(matchesFilter)); renderRegions(regionData); updateStats(stats,data); $("matchList").innerHTML=data.map(card).join("") || `<div class="empty">現在公開中の募集はありません。同じ条件のDB候補は ${stats.circles} 件あります。下のDBリンクから候補団体を確認できます。</div>`}
    function updateCoverageNotice(){const region=$("regionFilter").value; $("coverageNotice").style.display=region && region!=="kanto" ? "block" : "none"}
    async function boot(){renderSports(); drawJapanMap().catch(()=>{}); fillRegions(); fillSportOptions(); $("regionFilter").value=params.get("region")||""; syncPrefOptions(); updateCoverageNotice(); $("q").value=params.get("q")||""; $("prefFilter").value=params.get("prefecture")||""; $("sportFilter").value=params.get("sport")||""; applyInitialSummary(); await refresh()}
    ["q","typeFilter","sportFilter","prefFilter","sortFilter"].forEach(id=>$(id).addEventListener("input",refresh));
    $("regionFilter").addEventListener("input",()=>{syncPrefOptions(); updateCoverageNotice(); refresh()});
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
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap">
  <style>
    :root{--ink:#17212f;--muted:#64748b;--line:#dbe4ed;--brand:#0f7a62;--accent:#e15b31}
    *{box-sizing:border-box}body{margin:0;background:#f4f7fa;color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1040px;margin:auto;padding:12px 18px;display:flex;justify-content:space-between;align-items:center;gap:12px}.header-start{display:flex;align-items:center;gap:12px;min-width:0}.brand{font-weight:900;text-decoration:none}.nav{display:flex;align-items:center;gap:12px;flex:0 0 auto}.nav a{padding:10px 12px;border-radius:8px;color:#31506b;text-decoration:none;font-size:14px;font-weight:850;white-space:nowrap}.back-link{display:inline-flex;align-items:center;justify-content:center;flex:0 0 44px;width:44px;height:44px;border:1px solid var(--line);border-radius:8px;color:var(--ink);background:#fff;text-decoration:none;font-size:24px;line-height:1}.back-link:hover,.nav a:hover{background:#f4f7fa}.back-link:focus-visible,.nav a:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
    .signin-main{width:100%;max-width:640px;margin:0 auto;padding:32px 18px 60px;display:grid;grid-template-columns:minmax(0,1fr);gap:22px;align-items:start}
    .signin-main>section{min-width:0}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;padding:24px}.hero{text-align:center}.hero h1{font-size:30px;line-height:1.45;margin:0;text-wrap:balance}.hero p,.panel p{color:var(--muted);line-height:1.8}.hero p:last-child{margin-bottom:0}.button{display:flex;align-items:center;justify-content:center;gap:10px;min-height:52px;border-radius:8px;padding:12px 16px;border:1px solid var(--line);background:#fff;color:var(--ink);font:inherit;font-weight:900;text-decoration:none;cursor:pointer}.button.primary{background:var(--brand);border-color:var(--brand);color:#fff}.button.accent{background:var(--accent);border-color:var(--accent);color:#fff}
    /* Google's official HTML button: https://developers.google.com/identity/branding-guidelines */
    .gsi-material-button{user-select:none;-webkit-appearance:none;appearance:none;background-color:#fff;background-image:none;border:1px solid #747775;border-radius:4px;box-sizing:border-box;color:#1f1f1f;cursor:pointer;font-family:Roboto,Arial,sans-serif;font-size:14px;height:52px;letter-spacing:0;outline:none;overflow:hidden;padding:0 12px;position:relative;text-align:center;transition:background-color .218s,border-color .218s,box-shadow .218s;vertical-align:middle;white-space:nowrap;width:100%;min-width:0;display:block;margin-inline:auto}
    .gsi-material-button .gsi-material-button-icon{height:20px;margin-right:10px;min-width:20px;width:20px}
    .gsi-material-button .gsi-material-button-content-wrapper{align-items:center;display:flex;flex-direction:row;flex-wrap:nowrap;height:100%;justify-content:space-between;position:relative;width:100%}
    .gsi-material-button .gsi-material-button-contents{flex-grow:1;font-family:Roboto,Arial,sans-serif;font-weight:500;overflow:hidden;text-overflow:ellipsis;vertical-align:top}
    .gsi-material-button .gsi-material-button-state{transition:opacity .218s;bottom:0;left:0;opacity:0;position:absolute;right:0;top:0}
    .gsi-material-button:disabled{cursor:default;background-color:#ffffff61;border-color:#1f1f1f1f}
    .gsi-material-button:disabled .gsi-material-button-contents,.gsi-material-button:disabled .gsi-material-button-icon{opacity:.38}
    .gsi-material-button:not(:disabled):active .gsi-material-button-state,.gsi-material-button:not(:disabled):focus .gsi-material-button-state{background-color:#303030;opacity:.12}
    .gsi-material-button:not(:disabled):hover{box-shadow:0 1px 2px 0 rgba(60,64,67,.30),0 1px 3px 1px rgba(60,64,67,.15)}
    .gsi-material-button:not(:disabled):hover .gsi-material-button-state{background-color:#303030;opacity:.08}
    .gsi-material-button:focus-visible{outline:2px solid #1a73e8;outline-offset:2px}
    .note{margin-top:14px;border-top:1px solid var(--line);padding-top:14px;color:var(--muted);font-size:14px;line-height:1.7}.choice{display:none;gap:10px}.choice.active{display:grid}.status{margin-top:12px;padding:12px;border-radius:8px;background:#f9fbfd;color:var(--muted);line-height:1.7;font-size:14px}.status.error{background:#fff1f1;color:#a33}
    .email-login{display:grid;gap:10px;margin-top:20px;padding-top:20px;border-top:1px solid var(--line)}.email-login label{font-size:14px;font-weight:800}.email-login input{width:100%;min-width:0;min-height:52px;border:1px solid var(--line);border-radius:8px;padding:12px;font:inherit;font-size:16px}.email-login p{margin:0;font-size:13px}.button{width:100%}.button:disabled{opacity:.55;cursor:not-allowed}[hidden]{display:none!important}
    @media(max-width:760px){.signin-main{padding:24px 16px 40px;gap:20px}.panel{padding:20px}.hero h1{font-size:26px}.top{padding:10px 12px;gap:8px}.header-start{gap:8px}}
    @media(max-width:400px){.header-start{flex-shrink:0}.header-start a.brand .brand-wordmark{display:none}.header-start a.brand{gap:0}.nav{gap:4px}.nav a{padding-inline:8px}}
    .hero.hosting-intro h1{font-size:24px;line-height:1.5}
    .hero.hosting-intro .signin-lead{font-size:20px;font-weight:800;color:var(--ink);line-height:1.6;margin:12px 0;text-wrap:balance}
    .hero.hosting-intro .signin-detail{font-size:14px}
    @media(max-width:760px){.hero.hosting-intro h1{font-size:22px}.hero.hosting-intro .signin-lead{font-size:18px}}
  </style>
</head>
<body>
  <header data-account-navigation="hidden"><div class="top"><div class="header-start"><a class="back-link" href="__SIGNIN_BACK_URL__" aria-label="戻る" title="戻る"><span aria-hidden="true">&larr;</span></a><a class="brand" href="/">__SITE_NAME__</a></div><nav class="nav" aria-label="サイトナビゲーション"><a href="__SIGNIN_FIND_URL__">募集を探す</a></nav></div></header>
  <main class="signin-main">
    <section class="hero __SIGNIN_INTRO_CLASS__"><h1>__SIGNIN_HEADING__</h1>__SIGNIN_LEAD__<p class="signin-detail">__SIGNIN_DESCRIPTION__</p></section>
    <section class="panel" aria-label="ログイン方法">
      <button id="googleButton" class="gsi-material-button" type="button" disabled>
        <span class="gsi-material-button-state" aria-hidden="true"></span>
        <span class="gsi-material-button-content-wrapper">
          <span class="gsi-material-button-icon" aria-hidden="true">
            <svg version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" style="display:block" focusable="false">
              <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"></path>
              <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"></path>
              <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"></path>
              <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"></path>
              <path fill="none" d="M0 0h48v48H0z"></path>
            </svg>
          </span>
          <span class="gsi-material-button-contents">Google でログイン</span>
        </span>
      </button>
      <form id="emailForm" class="email-login">
        <label for="loginEmail">メールアドレスでログイン</label>
        <input id="loginEmail" type="email" autocomplete="email" maxlength="254" placeholder="you@example.com" required disabled>
        <button id="emailButton" class="button accent" type="submit" disabled>ログインリンクを受け取る</button>
        <p id="emailNote">メールログインは現在準備中です。</p>
      </form>
      <div id="choice" class="choice">
        <a class="button primary" href="/mypage">マイページへ進む</a>
        <a class="button accent" href="/events/new">募集を掲載する</a>
      </div>
      <p id="oauthNote" class="note">認証にはSupabase Authを利用します。メールアドレス、ユーザーID、ログイン日時など必要最小限の情報だけを保存します。</p>
      <div id="status" class="status" role="status" aria-live="polite">ログイン状態を確認しています。</div>
    </section>
  </main>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
  <script>
    const supabaseUrl = __SUPABASE_URL__;
    const supabaseAnonKey = __SUPABASE_ANON_KEY__;
    const authReady = __AUTH_READY__;
    const emailReady = __EMAIL_AUTH_READY__;
    const returnTo = __RETURN_TO__;
    const statusEl = document.getElementById("status");
    const choiceEl = document.getElementById("choice");
    const loginButton = document.getElementById("googleButton");
    const emailForm = document.getElementById("emailForm");
    const emailButton = document.getElementById("emailButton");
    const emailInput = document.getElementById("loginEmail");
    const redirectTo = `${location.origin}/signin?return_to=${encodeURIComponent(returnTo || "/")}`;
    function setStatus(text, error=false){statusEl.textContent=text; statusEl.className=error?"status error":"status"}
    function signedIn(user){
      loginButton.hidden=true; emailForm.hidden=true; choiceEl.classList.add("active");
      setStatus(`${user?.email || "ログイン済み"} でログインしています。`);
      if(returnTo && returnTo!=="/") location.replace(returnTo);
    }
    async function syncSession(client, session){
      if(!session?.access_token) return null;
      const res = await fetch("/api/auth/supabase", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({access_token:session.access_token})});
      const data = await res.json();
      if(!res.ok) throw new Error(data.error || "ログイン同期に失敗しました");
      return data.user;
    }
    async function boot(){
      const callbackError = new URLSearchParams(location.hash.slice(1)).get("error")
        || new URLSearchParams(location.search).get("error");
      const meResponse=await fetch("/api/me");
      if(meResponse.ok){const me=await meResponse.json();if(me.authenticated){signedIn(me);return}}
      if(!authReady){
        setStatus("現在ログインをご利用いただけません。時間をおいて再度お試しください。", true);
        return;
      }
      // The HttpOnly application cookie owns the session after this one-time exchange.
      const client = window.supabase.createClient(supabaseUrl, supabaseAnonKey,{auth:{persistSession:false,autoRefreshToken:false}});
      const { data, error: sessionError } = await client.auth.getSession();
      if(sessionError || callbackError) setStatus("ログインリンクが無効か、有効期限を過ぎています。もう一度メールを送信してください。", true);
      if(data.session){
        try{
          const user = await syncSession(client, data.session);
          signedIn(user);
          return;
        }catch(error){setStatus("ログイン状態を確認できませんでした。もう一度ログインしてください。",true)}
      }else if(!sessionError && !callbackError){
        setStatus("ログイン後、元の画面に戻ります。");
      }
      loginButton.disabled=false;
      emailButton.disabled=!emailReady; emailInput.disabled=!emailReady;
      if(emailReady)document.getElementById("emailNote").textContent="パスワードは不要です。届いたリンクからログインしてください。初めての方はアカウントが作成されます。";
      emailForm.onsubmit=async event=>{
        event.preventDefault();if(!emailReady||emailButton.disabled||!emailForm.reportValidity())return;
        emailButton.disabled=true;setStatus("ログインリンクをリクエストしています。");
        try{
          const {error}=await client.auth.signInWithOtp({email:emailInput.value.trim(),options:{emailRedirectTo:redirectTo,shouldCreateUser:true}});
          if(error)throw error;
          setStatus("ログインリンクの送信を受け付けました。メールをご確認ください。");
          setTimeout(()=>{emailButton.disabled=false},60000);
        }catch(error){setStatus("メールを送信できませんでした。時間をおいて再度お試しください。",true);emailButton.disabled=false}
      };
      loginButton.onclick = async () => {
        loginButton.disabled=true;setStatus("Googleログインへ移動します。");
        try{
          const { error } = await client.auth.signInWithOAuth({provider:"google", options:{redirectTo, queryParams:{prompt:"select_account"}}});
          if(error)throw error;
        }catch(error){setStatus("Googleログインを開始できませんでした。時間をおいて再度お試しください。",true);loginButton.disabled=false}
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
    main{max-width:1180px;margin:auto;padding:24px 18px 54px}.hero{position:relative;overflow:hidden;display:grid;grid-template-columns:1fr auto;gap:16px;align-items:end;min-height:310px;margin-bottom:14px;border-radius:8px;padding:34px;background:#152235 url("__SPORT_IMAGE__") center/cover no-repeat;color:#fff}.hero::before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(9,18,31,.86),rgba(9,18,31,.55) 58%,rgba(9,18,31,.2))}.hero>*{position:relative;z-index:1}.hero h1{font-size:42px;margin:0 0 12px;line-height:1.14}.hero p{max-width:650px;margin:0;color:rgba(255,255,255,.86);line-height:1.75}.button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;border-radius:8px;padding:10px 14px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:900;text-decoration:none}.button.primary{background:var(--accent);color:#fff;border-color:transparent}
    .stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:900}.metric strong{display:block;margin-top:6px;font-size:27px}
    .grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:14px}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.db-panel{position:relative}.panel h2{margin:0;padding:16px;border-bottom:1px solid var(--line);font-size:21px}.region-list,.area-list{display:grid;gap:8px;padding:14px}.region-list{grid-template-columns:repeat(2,minmax(0,1fr));border-bottom:1px solid var(--line);background:#f9fbfd}.region-button,.area{border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink);font:inherit;cursor:pointer}.region-button{padding:10px;text-align:left}.region-button.active,.area.active{border-color:var(--accent);box-shadow:0 0 0 2px rgba(225,91,49,.14)}.region-button b{display:block}.region-button span{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.area{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px;background:#fafcff;text-align:left}.area b{font-size:16px}.badge{display:inline-flex;border-radius:999px;background:#edf2f7;color:#405164;min-height:23px;padding:3px 8px;font-size:12px;font-weight:900}.badge.ok{background:#e2f5ed;color:#0d674f}.table-tools{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border-bottom:1px solid var(--line);color:var(--muted);font-size:13px;font-weight:850}.filter-menu{position:absolute;z-index:5;right:12px;top:100px;width:min(360px,calc(100% - 24px));background:#fff;border:1px solid #cbd7e2;border-radius:8px;box-shadow:0 18px 42px rgba(23,33,47,.18);padding:12px;display:grid;gap:10px}.filter-menu.hidden{display:none}.filter-menu strong{font-size:14px}.filter-actions,.choice-grid{display:flex;gap:7px;flex-wrap:wrap}.filter-menu button,.th-filter{font:inherit;cursor:pointer}.filter-menu button{border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--ink);min-height:31px;padding:5px 10px;font-size:12px;font-weight:900}.filter-menu button.active,.filter-menu button:hover{border-color:var(--accent);color:#b8421e;background:#fff6f2}.tablewrap{overflow:auto;max-height:680px}input,select{width:100%;border:1px solid #c8d4df;border-radius:8px;min-height:38px;padding:8px 10px;font:inherit;background:#fff;color:var(--ink)}table{width:100%;border-collapse:collapse;font-size:14px;min-width:720px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{position:sticky;top:0;background:#f8fbfd;color:var(--muted);font-size:12px}.th-filter{display:inline-flex;align-items:center;gap:7px;border:1px solid #c8d4df;border-radius:999px;background:#fff;color:#405164;min-height:30px;padding:5px 9px;font-weight:950;box-shadow:0 1px 0 rgba(23,33,47,.04)}.th-filter::after{content:"絞込";font-size:10px;color:#6b7d90;font-weight:950}.th-filter svg{width:16px;height:16px;stroke:currentColor;stroke-width:2;fill:none}.th-filter:hover,.th-filter.active{border-color:var(--accent);color:var(--accent);background:#fff6f2}.th-filter.active::after{color:var(--accent)}.name{font-weight:900}.sub{display:block;color:var(--muted);font-size:12px;margin-top:3px}.empty{padding:18px;color:var(--muted);line-height:1.7}footer{max-width:1180px;margin:0 auto;padding:0 18px 38px;color:var(--muted);font-size:13px;display:flex;gap:12px;flex-wrap:wrap}.admin-link{color:#65758a}
    @media(max-width:860px){.hero,.grid{grid-template-columns:1fr}.hero{min-height:280px;padding:24px}.stats{grid-template-columns:1fr}.hero h1{font-size:31px}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a class="find-link" href="/">トップへ戻る</a><a href="/representative?intent=post-match">募集を出す</a><a href="/representative">掲載情報を整える</a></nav></div></header>
  <main>
    <section class="hero"><div><h1>__SPORT__の相手を探す</h1><p>__SPORT__サークルDBと練習試合・交流募集をまとめて確認できます。</p></div><a class="button primary" href="/representative?intent=post-match">募集を出す</a></section>
    <section class="stats"><div class="metric"><span>サークル</span><strong id="circleCount">0</strong></div><div class="metric"><span>交流募集</span><strong id="matchCount">0</strong></div><div class="metric"><span>対象都道府県</span><strong id="prefCount">0</strong></div></section>
    <section class="grid"><aside class="panel"><h2>地域別の交流募集</h2><div id="regionList" class="region-list"></div><div id="areaList" class="area-list"></div></aside><section class="panel db-panel"><h2>__SPORT__サークルDB</h2><div class="table-tools"><span><strong id="visibleCircleCount">0</strong> 件を表示</span><span id="activeFilterText"></span></div><div id="filterMenu" class="filter-menu hidden"></div><div class="tablewrap"><table><thead><tr><th><button class="th-filter" data-filter="university">大学 <svg viewBox="0 0 24 24"><path d="M4 5h16l-6 7v5l-4 2v-7z"/></svg></button></th><th><button class="th-filter" data-filter="circle">団体名 <svg viewBox="0 0 24 24"><path d="M4 5h16l-6 7v5l-4 2v-7z"/></svg></button></th><th>登録済み</th><th><button class="th-filter" data-filter="type">種別 <svg viewBox="0 0 24 24"><path d="M4 5h16l-6 7v5l-4 2v-7z"/></svg></button></th><th><button class="th-filter" data-filter="source">出典 <svg viewBox="0 0 24 24"><path d="M4 5h16l-6 7v5l-4 2v-7z"/></svg></button></th></tr></thead><tbody id="circleRows"></tbody></table></div></section></section>
  </main>
  <footer><span>サイトへのご意見・ご要望はこちら: <a class="admin-link" href="mailto:__CONTACT_EMAIL__">__CONTACT_EMAIL__</a></span><a class="admin-link" href="/guides">サークル運営ガイド</a><a class="admin-link" href="/operator">運営者情報</a><a class="admin-link" href="/circles">サークルDBを見る</a><a class="admin-link" href="/contact">問い合わせ</a></footer>
  <script>
    const sport = __SPORT_JSON__;
    const params = new URLSearchParams(location.search);
    let selectedRegion = params.get("region") || "kanto";
    let selectedPrefecture = params.get("prefecture") || "";
    let currentCircles = [];
    let columnFilters = {university:"", circle:"", type:"", source:"", sort:"university"};
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function statusLabel(v){return ({university_verified:"大学公式情報掲載",admin_verified:"公開情報掲載",claimed:"代表申請受付",unverified:"未確認"}[v] || v)}
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
    main{max-width:1180px;margin:auto;padding:24px 18px 54px}.hero{display:grid;grid-template-columns:1fr auto;gap:16px;align-items:end;margin-bottom:14px}.hero h1{font-size:38px;margin:0 0 8px}.hero p{margin:0;color:var(--muted);line-height:1.75}.button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;border-radius:8px;padding:10px 14px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:900;text-decoration:none}.button.primary{background:var(--accent);color:#fff;border-color:transparent}.sport-context-hero{position:relative;min-height:230px;overflow:hidden;margin:0 0 14px;border:1px solid var(--line);border-radius:8px;background:#132238;color:#fff}.sport-context-hero[hidden]{display:none}.sport-context-hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.sport-context-hero::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(8,18,31,.88),rgba(8,18,31,.55) 58%,rgba(8,18,31,.12))}.sport-context-copy{position:relative;z-index:1;display:grid;align-content:end;min-height:230px;gap:7px;padding:24px;color:#fff}.sport-context-copy p{margin:0;color:rgba(255,255,255,.82);font-size:13px;font-weight:850}.sport-context-copy h2{margin:0;font-size:30px;line-height:1.2}
    .stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:900}.metric strong{display:block;margin-top:6px;font-size:27px}
    .grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:14px}.panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.panel h2{margin:0;padding:16px;border-bottom:1px solid var(--line);font-size:21px}.coverage-notice{display:__REGION_NOTICE_DISPLAY__;margin-bottom:14px;border:1px solid #f1d2be;background:#fff8f4;color:#7b3b22;border-radius:8px;padding:12px 14px;font-weight:850;line-height:1.7}.sport-search{padding:12px 14px 0;background:#f9fbfd}.sport-search input{width:100%;min-height:42px;border:1px solid var(--line);border-radius:8px;padding:10px 12px;font:inherit}.sport-list,.area-list{display:grid;gap:8px;padding:14px}.sport-list{grid-template-columns:repeat(2,minmax(0,1fr));border-bottom:1px solid var(--line);background:#f9fbfd}.sport-button,.area{border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink);font:inherit;cursor:pointer}.sport-button{padding:10px;text-align:left}.sport-button.active,.area.active{border-color:var(--accent);box-shadow:0 0 0 2px rgba(225,91,49,.14)}.sport-button b{display:block}.sport-button span{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}.area{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px;background:#fafcff;text-align:left}.area b{font-size:16px}.badge{display:inline-flex;border-radius:999px;background:#edf2f7;color:#405164;min-height:23px;padding:3px 8px;font-size:12px;font-weight:900}.badge.ok{background:#e2f5ed;color:#0d674f}.match-list{display:grid;gap:10px;padding:14px}.match-card{border:1px solid var(--line);border-radius:8px;padding:13px;background:#fff}.match-card h3{margin:6px 0 8px;font-size:17px}.meta{display:grid;gap:4px;color:var(--muted);font-size:13px}.empty{padding:18px;color:var(--muted);line-height:1.7}.table-tools{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border-bottom:1px solid var(--line);color:var(--muted);font-size:13px;font-weight:850}.tablewrap{overflow:auto;max-height:520px}table{width:100%;border-collapse:collapse;font-size:14px;min-width:680px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{position:sticky;top:0;background:#f8fbfd;color:var(--muted);font-size:12px}.name{font-weight:900}.sub{display:block;color:var(--muted);font-size:12px;margin-top:3px}.right-stack{display:grid;gap:14px}footer{max-width:1180px;margin:0 auto;padding:0 18px 38px;color:var(--muted);font-size:13px;display:flex;gap:12px;flex-wrap:wrap}.admin-link{color:#65758a}
    @media(max-width:860px){.hero,.grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr}.hero h1{font-size:31px}.sport-list{grid-template-columns:1fr}.sport-context-copy{min-height:210px;padding:20px}.sport-context-copy h2{font-size:25px}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a class="find-link" href="/">トップへ戻る</a><a href="/representative?intent=post-match">募集を出す</a><a href="/representative">掲載情報を整える</a></nav></div></header>
  <main>
    <section class="hero"><div><h1>__REGION_LABEL__の相手を探す</h1><p>__REGION_LABEL__の練習試合・交流募集を、スポーツ別・都道府県別に確認できます。</p></div><a class="button primary" href="/representative?intent=post-match">募集を出す</a></section>
    <section id="sportContextHero" class="sport-context-hero" hidden><img id="sportContextImage" alt=""><div class="sport-context-copy"><p id="sportContextEyebrow"></p><h2 id="sportContextTitle"></h2><p>サークルDBと交流募集をまとめて確認できます。</p></div></section>
    <section class="stats"><div class="metric"><span>サークル</span><strong id="circleCount">0</strong></div><div class="metric"><span>交流募集</span><strong id="matchCount">0</strong></div><div class="metric"><span>対象競技</span><strong id="sportCount">0</strong></div></section>
    <div class="coverage-notice">関東以外の地域は現在DB拡充中です。掲載漏れや訂正は問い合わせから連絡してください。</div>
    <section class="grid"><aside class="panel"><h2>スポーツ別の交流募集</h2><div class="sport-search"><input id="sportSearch" placeholder="その他の競技を検索"></div><div id="sportList" class="sport-list"></div><div id="areaList" class="area-list"></div></aside><section class="right-stack"><div class="panel"><h2>交流募集</h2><div id="matchList" class="match-list"></div></div><div class="panel"><h2>__REGION_LABEL__サークルDB</h2><div class="table-tools"><span><strong id="visibleCircleCount">0</strong> 件を表示</span><a id="dbLink" class="admin-link" href="/circles">DBで詳しく見る</a></div><div class="tablewrap"><table><thead><tr><th>大学</th><th>団体名</th><th>登録済み</th><th>種別</th><th>競技</th></tr></thead><tbody id="circleRows"></tbody></table></div></div></section></section>
  </main>
  <footer><span>サイトへのご意見・ご要望はこちら: <a class="admin-link" href="mailto:__CONTACT_EMAIL__">__CONTACT_EMAIL__</a></span><a class="admin-link" href="/guides">サークル運営ガイド</a><a class="admin-link" href="/operator">運営者情報</a><a class="admin-link" href="/">トップへ戻る</a><a class="admin-link" href="/circles">サークルDBを見る</a><a class="admin-link" href="/contact">問い合わせ</a></footer>
  <script>
    const region = __REGION_JSON__;
    const regionLabel = __REGION_LABEL_JSON__;
    const sportImages = __SPORT_IMAGES__;
    const params = new URLSearchParams(location.search);
    let selectedSport = params.get("sport") || "";
    let selectedPrefecture = params.get("prefecture") || "";
    let allSports = [];
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function badge(v,cls=""){return `<span class="badge ${cls}">${esc(v)}</span>`}
    async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
    function sportButton(s){return `<button class="sport-button ${s.name===selectedSport?"active":""}" data-sport="${esc(s.name)}"><b>${esc(s.name || "すべて")}</b><span>${badge(`${s.match_count}件`,s.match_count>0?"ok":"")}${badge(`DB ${s.circle_count}件`)}</span></button>`}
    function renderSportContext(){const box=$("sportContextHero"); if(!selectedSport){box.hidden=true; return} const image=sportImages[selectedSport]||sportImages["その他"]; $("sportContextImage").src=`/assets/sports/${encodeURIComponent(image)}?v=20260713v1`; $("sportContextImage").alt=`${selectedSport}のスポーツ用具`; $("sportContextEyebrow").textContent=`${regionLabel} / ${selectedSport}`; $("sportContextTitle").textContent=`${selectedSport}の相手を${regionLabel}で探す`; box.hidden=false}
    function renderSportList(){const q=($("sportSearch").value||"").trim().toLowerCase(); const primary=allSports.filter(s=>s.name!=="その他"); let rows=q?allSports.filter(s=>s.name.toLowerCase().includes(q)):primary.slice(0,14); if(selectedSport&&!rows.some(s=>s.name===selectedSport)){const selected=allSports.find(s=>s.name===selectedSport); if(selected)rows=[selected,...rows]} $("sportList").innerHTML=[{name:"",circle_count:window.regionCircleCount||0,match_count:window.regionMatchCount||0},...rows].map(sportButton).join("") || `<div class="empty">該当する競技がありません。</div>`; document.querySelectorAll("[data-sport]").forEach(b=>b.onclick=()=>{selectedSport=b.dataset.sport; selectedPrefecture=""; boot().catch(e=>alert(e.message))})}
    function areaButton(a){return `<button class="area ${a.prefecture===selectedPrefecture?"active":""}" data-prefecture="${esc(a.prefecture)}"><b>${esc(a.prefecture)}</b><span>${badge(`${a.match_count}件`,a.match_count>0?"ok":"")}${badge(`DB ${a.circle_count}件`)}</span></button>`}
    function matchCard(m){return `<article class="match-card"><div>${badge(m.status||"open","ok")} ${badge(m.match_type)} ${badge(m.sport_category||"競技未設定")}</div><h3>${esc(m.circle_name)}</h3><div class="meta"><span>${esc(m.university_name)} / ${esc(m.prefecture||"地域未設定")}</span><span>${esc(m.scheduled_at||"日時未定")} / ${esc(m.place||"場所未定")}</span><span>${esc(m.level_label||"レベル未設定")}</span></div></article>`}
    function circleRow(c){return `<tr><td><span class="name">${esc(c.university_name)}</span><span class="sub">${esc(c.prefecture)} ${esc(c.city||"")}</span></td><td><span class="name">${esc(c.circle_name)}</span></td><td>${c.profile_url?`<a href="${esc(c.profile_url)}">URL</a>`:""}</td><td>${badge(c.organization_type||"不明")}</td><td>${esc(c.sport_category||"その他")}</td></tr>`}
    function updateUrl(){const next=new URL(location.href); next.searchParams.set("region",region); if(selectedSport)next.searchParams.set("sport",selectedSport); else next.searchParams.delete("sport"); if(selectedPrefecture)next.searchParams.set("prefecture",selectedPrefecture); else next.searchParams.delete("prefecture"); history.replaceState(null,"",next)}
    async function boot(){updateUrl(); renderSportContext(); const qs=new URLSearchParams({region}); if(selectedSport)qs.set("sport",selectedSport); if(selectedPrefecture)qs.set("prefecture",selectedPrefecture); const data=await api(`/api/region_overview?${qs}`); selectedPrefecture=data.prefecture||""; allSports=data.sports||[]; window.regionCircleCount=data.region_circle_count; window.regionMatchCount=data.region_match_count; $("circleCount").textContent=data.circle_count; $("matchCount").textContent=data.match_count; $("sportCount").textContent=data.sports.filter(s=>s.circle_count||s.match_count).length; renderSportList(); $("areaList").innerHTML=data.areas.map(areaButton).join("") || `<div class="empty">この地域の候補はまだありません。</div>`; $("matchList").innerHTML=data.matches.map(matchCard).join("") || `<div class="empty">現在公開中の募集はありません。同じ条件のDB候補は ${data.circle_count} 件あります。</div>`; $("visibleCircleCount").textContent=data.circles.length; $("circleRows").innerHTML=data.circles.map(circleRow).join("") || `<tr><td colspan="5" class="empty">データなし</td></tr>`; const dbQs=new URLSearchParams({region}); if(selectedSport)dbQs.set("sport",selectedSport); if(selectedPrefecture)dbQs.set("prefecture",selectedPrefecture); $("dbLink").href="/circles?"+dbQs; document.querySelectorAll("[data-prefecture]").forEach(b=>b.onclick=()=>{selectedPrefecture=b.dataset.prefecture; boot().catch(e=>alert(e.message))})}
    $("sportSearch").addEventListener("input",renderSportList);
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
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a href="/">募集中を見る</a><a href="/circles">サークルDB</a><a class="db-request" href="/representative">団体代表者の方へ</a></nav></div></header>
  <main>
    <section class="hero"><div><h1>練習試合・交流募集を出す</h1><p>まず自分のサークルをDBから検索して選び、募集したい期間・練習内容・場所・条件を登録します。DBにない場合は右上の登録依頼から申請してください。</p></div><a class="button ghost" href="/representative">DBへの登録依頼はこちら</a></section>
    <section id="loginNeeded" class="notice login-needed">募集を投稿するには団体代表者の確認が必要です。<a href="/representative?intent=post-match">代表申請</a>から団体情報を登録してください。</section>
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
    async function boot(){fillSports(); const me=await api("/api/me"); authenticated=!!me.authenticated; $("loginNeeded").style.display=authenticated?"none":"block"; circles=[]; renderCircles()}
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
    form{display:grid;gap:14px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}label{display:grid;gap:6px;font-weight:850}small{color:var(--muted);font-weight:500}input,select,textarea{width:100%;border:1px solid #cbd7e2;border-radius:8px;min-height:42px;padding:10px 11px;font:inherit;background:#fff;color:var(--ink)}textarea{min-height:96px;resize:vertical}.consent{display:flex;align-items:flex-start;gap:9px;padding:11px 12px;border:1px solid var(--line);border-radius:8px;background:#f9fbfd;line-height:1.55}.consent input{width:auto;min-height:0;margin:3px 0 0}.button{display:inline-flex;align-items:center;justify-content:center;min-height:46px;border-radius:8px;padding:11px 16px;border:1px solid transparent;background:var(--accent);color:#fff;font-weight:900;text-decoration:none;cursor:pointer}.ghost{background:#fff;color:var(--ink);border-color:var(--line)}.actions{display:flex;gap:10px;flex-wrap:wrap}.result{display:none;border-radius:8px;padding:12px 14px;background:#e2f5ed;color:#0d674f;font-weight:850}.result.error{background:#fde8e4;color:#9b2f1a}.mode-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.mode{border:1px solid #cbd7e2;border-radius:8px;padding:13px;background:#fff;cursor:pointer}.mode:has(input:checked){border-color:var(--accent);box-shadow:0 0 0 2px #fde8e4}.mode input{width:auto;min-height:0;margin-right:7px}.mode small{display:block;margin:7px 0 0 25px;line-height:1.55}.search-box{border:1px solid var(--line);border-radius:8px;padding:14px;background:#f9fbfd}.search-box h2{font-size:17px;margin:0 0 8px}.search-box p{margin:0 0 10px;color:var(--muted);line-height:1.6}.search-results,.university-results{display:grid;gap:7px;margin-top:9px;max-height:250px;overflow:auto}.search-result{display:block;width:100%;text-align:left;border:1px solid var(--line);border-radius:7px;background:#fff;padding:10px;cursor:pointer;color:var(--ink);font:inherit}.search-result:hover,.search-result.active{border-color:var(--accent);background:#fff8f4}.search-result b,.search-result span{display:block}.search-result span{color:var(--muted);font-size:13px;margin-top:3px}.selected{border:1px solid #a9d9c9;border-radius:7px;background:#edf9f4;padding:10px;color:#0d674f;font-weight:750}.selected span{display:block;font-size:13px;margin-top:3px;font-weight:600}.hidden{display:none!important}
    @media(max-width:820px){.intro,.form-grid{grid-template-columns:1fr}.top{align-items:flex-start;flex-direction:column}.intro h1{font-size:29px}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a href="/">募集を探す</a><a href="/contact">問い合わせ</a></nav></div></header>
  <main>
    <section class="intro"><article class="panel"><h1 id="representativeTitle">自分が所属するサークルを登録しよう！</h1><p id="representativeLead">代表者が簡単なアンケートに答えるだけで、サークル紹介ページを自動作成します。大学団体は大学メールで、社会人サークルは代表者メールで確認します。どちらも公開ページに個人用メールは表示しません。</p></article><aside class="steps"><div class="step"><b>1. 団体を探す</b>まずDBを検索して、登録済みの自分の団体を選びます。見つからなければ新規入力へ進めます。</div><div class="step"><b>2. 紹介アンケートに回答</b>人数、雰囲気、経験者割合、練習頻度などを入力します。</div><div class="step" id="representativeStep3"><b>3. 本人確認</b>大学団体は大学メール、社会人サークルは代表者メールで申請内容を確認します。</div></aside></section>
    <section class="panel">
      <form id="claimForm">
        <div><label>団体区分</label><div class="mode-grid"><label class="mode"><span><input name="audience" type="radio" value="university" checked>大学サークル・部活動</span><small>大学を選び、大学公式メールで確認します。</small></label><label class="mode"><span><input name="audience" type="radio" value="social">社会人サークル</span><small>大学メールは不要です。代表者メールで確認します。</small></label></div></div>
        <section class="search-box"><h2>登録済みの団体を検索</h2><p>団体名、大学名、競技、活動地域を入力して候補を選択できます。候補にない場合は、下の入力欄から新規団体として申請してください。</p><input id="existingSearch" autocomplete="off" placeholder="例: 早稲田 フットサル / 渋谷 テニス"><div id="existingResults" class="search-results"><span class="sub">2文字以上入力すると候補を表示します。</span></div><div id="selectedExisting" class="selected hidden"></div><div class="actions"><button id="newCircleButton" class="button ghost" type="button">候補にないため新規で入力する</button></div></section>
        <input id="selectedCircleId" type="hidden">
        <section id="universityFields" class="form-grid"><label>大学を検索・選択<small>候補から必ず選んでください</small><input id="universitySearch" autocomplete="off" placeholder="例: 早稲田大学"><input id="universityId" type="hidden"><div id="universityResults" class="university-results"></div></label><label>団体名<small>新規団体の場合に入力してください</small><input id="circleName" required placeholder="例: フットサル同好会"></label></section>
        <section id="socialFields" class="form-grid hidden"><label>主な活動都道府県<select id="prefecture"></select></label><label>主な活動エリア<small>市区町村・沿線・施設エリアなど</small><input id="socialCity" placeholder="例: 渋谷区、横浜市、都内西部"></label></section>
        <div class="form-grid"><label>競技<select id="sportCategory" required></select></label><label>団体種別<select id="organizationType"></select></label></div>
        <div class="form-grid"><label>代表者名<small>公開されません</small><input id="claimantName" required></label><label id="claimantEmailLabel">大学メール<small id="claimantEmailHelp">選択した大学の公式メールアドレスを入力してください。公開されず、本人確認にだけ使います。</small><input id="claimantEmail" type="email" required placeholder="name@university.ac.jp"></label></div>
        <div class="form-grid"><label>公開連絡用メール<small>団体の問い合わせ窓口として公開するアドレスだけを入力してください</small><input id="publicContactEmail" type="email" placeholder="circle@example.com"></label><label class="consent"><input id="publicContactConsent" type="checkbox">このメールアドレスを団体の公開連絡先として掲載することに同意します</label></div>
        <label>出典URL<small>大学公式ページ、団体公式SNS、サークル紹介ページなど</small><input id="evidenceUrl" type="url" placeholder="https://"></label>
        <div class="form-grid"><label>人数<small>例: 20人、50人以上など</small><input id="memberCount" placeholder="例: 35人"></label><label>練習頻度<small>例: 週2回、月2回など</small><input id="practiceFrequency" placeholder="例: 週2回"></label></div>
        <div class="form-grid"><label>雰囲気<select id="atmosphere"><option value="">選択してください</option><option>初心者歓迎</option><option>ゆるめ</option><option>ほどよく真剣</option><option>競技志向</option><option>交流重視</option></select></label><label>経験者割合<select id="experienceRatio"><option value="">選択してください</option><option>初心者中心</option><option>初心者と経験者が半々</option><option>経験者多め</option><option>経験者中心</option><option>未定</option></select></label></div>
        <label>主な活動場所<small>キャンパス、体育館、グラウンド、外部施設など</small><input id="activityPlace" placeholder="例: 早稲田キャンパス周辺、都内体育館"></label>
        <label>紹介文<small>公開ページに表示されます</small><textarea id="introduction" placeholder="どんなサークルか、どんな相手と交流したいかを書いてください"></textarea></label>
        <label>補足<small>運営への連絡、確認してほしいことなど。公開ページにも代表コメントとして使えます。</small><textarea id="message"></textarea></label>
        <div id="result" class="result"></div>
        <div class="actions"><button class="button" type="submit">代表申請を送信</button><a class="button ghost" href="/">閲覧トップへ戻る</a></div>
      </form>
    </section>
  </main>
  <script>
    const sports = __SPORTS__;
    const orgTypes = __ORG_TYPES__;
    const prefectures = __PREFS__;
    const $ = id => document.getElementById(id);
    let universities = [];
    let selectedExisting = null;
    let searchTimer = null;
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function fill(el, rows, label){el.innerHTML=`<option value="">${label}</option>`+rows.map(r=>`<option value="${esc(r.value)}">${esc(r.label)}</option>`).join("")}
    function audience(){return document.querySelector('input[name="audience"]:checked').value}
    async function api(path, options){const r=await fetch(path, options); const data=await r.json(); if(!r.ok)throw new Error(data.error||"送信に失敗しました"); return data}
    function clearExisting(){selectedExisting=null; $("selectedCircleId").value=""; $("selectedExisting").classList.add("hidden")}
    function renderUniversityCandidates(query){const q=query.trim().toLowerCase(); const rows=universities.filter(u=>[u.university_name,u.prefecture,u.city].join(" ").toLowerCase().includes(q)).slice(0,12); $("universityResults").innerHTML=rows.map(u=>`<button class="search-result" type="button" data-university="${esc(u.university_id)}"><b>${esc(u.university_name)}</b><span>${esc(u.prefecture)}${u.city?` / ${esc(u.city)}`:""}</span></button>`).join("") || (q?'<span class="sub">大学が見つかりません。表記を変えて検索してください。</span>':''); document.querySelectorAll("[data-university]").forEach(button=>button.onclick=()=>{const u=universities.find(item=>item.university_id===button.dataset.university); if(!u)return; $("universityId").value=u.university_id; $("universitySearch").value=`${u.university_name} / ${u.prefecture}`; $("universityResults").innerHTML='<div class="selected">大学を選択しました</div>'})}
    function selectExisting(circle){selectedExisting=circle; $("selectedCircleId").value=circle.circle_id; $("circleName").value=circle.circle_name; $("sportCategory").value=circle.sport_category||""; $("organizationType").value=circle.organization_type||""; if(audience()==="university"){ $("universityId").value=circle.university_id; $("universitySearch").value=`${circle.university_name} / ${circle.prefecture}` }else{$("prefecture").value=circle.prefecture||""; $("socialCity").value=circle.city||circle.activity_area||""} $("selectedExisting").classList.remove("hidden"); $("selectedExisting").innerHTML=`<b>選択中: ${esc(circle.circle_name)}</b><span>${esc(circle.university_name)} / ${esc(circle.prefecture)} / ${esc(circle.sport_category||"その他")}</span>`; $("existingResults").innerHTML=''}
    function renderExisting(rows){$("existingResults").innerHTML=rows.map(c=>`<button class="search-result" type="button" data-circle="${esc(c.circle_id)}"><b>${esc(c.circle_name)}</b><span>${esc(c.university_name)} / ${esc(c.prefecture)} / ${esc(c.sport_category||"その他")}</span></button>`).join("") || '<span class="sub">候補が見つかりません。このまま新規団体として入力してください。</span>'; document.querySelectorAll("[data-circle]").forEach(button=>button.onclick=()=>{const circle=rows.find(item=>item.circle_id===button.dataset.circle); if(circle)selectExisting(circle)})}
    async function searchExisting(){const q=$("existingSearch").value.trim(); if(q.length<2){$("existingResults").innerHTML='<span class="sub">2文字以上入力すると候補を表示します。</span>'; return} const qs=new URLSearchParams({q,audience:audience()}); const rows=await api("/api/circle-search?"+qs); renderExisting(rows)}
    function applyAudience(){const social=audience()==="social"; clearExisting(); $("existingSearch").value=""; $("existingResults").innerHTML='<span class="sub">2文字以上入力すると候補を表示します。</span>'; $("universityFields").classList.toggle("hidden",social); $("socialFields").classList.toggle("hidden",!social); if(social){$("organizationType").innerHTML='<option value="社会人サークル">社会人サークル</option>'}else{fill($("organizationType"),orgTypes.filter(v=>v!=="社会人サークル").map(v=>({value:v,label:v})),"団体種別を選択")} $("organizationType").disabled=social; $("claimantEmailLabel").childNodes[0].textContent=social?"代表者メール":"大学メール"; $("claimantEmailHelp").textContent=social?"団体の代表者として連絡を受け取れるメールアドレスを入力してください。公開されず、本人確認にだけ使います。":"選択した大学の公式メールアドレスを入力してください。公開されず、本人確認にだけ使います。"; $("claimantEmail").placeholder=social?"representative@example.com":"name@university.ac.jp"; $("representativeStep3").innerHTML=social?"<b>3. 代表者メールを確認</b>入力した代表者メールから確認メールを送り、運営確認後に募集を公開できます。":"<b>3. 大学メールを確認</b>大学メールから確認メールを送り、運営確認後に募集を公開できます。"}
    async function boot(){const intent=new URLSearchParams(location.search).get("intent"); if(intent==="post-match"){ $("representativeTitle").textContent="募集を出す前に、団体代表者として申請しよう"; $("representativeLead").textContent="募集投稿は、団体情報と代表者申請を確認した後に開放します。大学団体は大学メール、社会人サークルは代表者メールで確認します。"} universities=await api("/api/universities"); fill($("sportCategory"),sports.map(v=>({value:v,label:v})),"競技を選択"); fill($("prefecture"),prefectures.map(v=>({value:v,label:v})),"都道府県を選択"); $("universitySearch").addEventListener("input",()=>{ $("universityId").value=""; renderUniversityCandidates($("universitySearch").value) }); $("existingSearch").addEventListener("input",()=>{clearTimeout(searchTimer); searchTimer=setTimeout(()=>searchExisting().catch(err=>$("existingResults").innerHTML=`<span class="sub">${esc(err.message)}</span>`),220)}); document.querySelectorAll('input[name="audience"]').forEach(input=>input.addEventListener("change",applyAudience)); $("newCircleButton").addEventListener("click",()=>{clearExisting(); $("circleName").focus()}); applyAudience()}
    $("claimForm").addEventListener("submit",async e=>{e.preventDefault(); const result=$("result"); result.style.display="block"; result.className="result"; result.textContent="送信中です"; try{const social=audience()==="social"; const publicContactEmail=$("publicContactEmail").value.trim(); const publicContactConsent=$("publicContactConsent").checked; if(publicContactEmail&&!publicContactConsent)throw new Error("公開連絡用メールを掲載する場合は、公開への同意が必要です。"); if(publicContactConsent&&!publicContactEmail)throw new Error("公開する団体用メールアドレスを入力してください。"); if(!$("selectedCircleId").value&&!social&&!$("universityId").value)throw new Error("大学を検索して候補から選択してください。"); if(!$("selectedCircleId").value&&social&&!$("prefecture").value)throw new Error("社会人サークルの主な活動都道府県を選択してください。"); const payload={audience:audience(),circle_id:$("selectedCircleId").value,university_id:$("universityId").value,prefecture:$("prefecture").value,social_city:$("socialCity").value,circle_name:$("circleName").value,sport_category:$("sportCategory").value,organization_type:$("organizationType").value,claimant_name:$("claimantName").value,claimant_email:$("claimantEmail").value,public_contact_email:publicContactEmail,public_contact_consent:publicContactConsent,evidence_url:$("evidenceUrl").value,member_count:$("memberCount").value,practice_frequency:$("practiceFrequency").value,atmosphere:$("atmosphere").value,experience_ratio:$("experienceRatio").value,activity_place:$("activityPlace").value,introduction:$("introduction").value,message:$("message").value}; const data=await api("/api/claims",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); result.innerHTML=`代表申請を受け付けました。申請ID: ${esc(data.claim_id)}<br><a href="${esc(data.verification_mailto)}">${esc(data.verification_label)}を作成</a><br><small>${esc(data.verification_note)}</small><br><a href="${esc(data.profile_url)}">作成されたサークルページを見る</a>`; e.target.reset(); clearExisting(); applyAudience()}catch(err){result.className="result error"; result.textContent=err.message}})
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
    .grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:900}.metric strong{display:block;margin-top:5px;font-size:18px;line-height:1.35}.panel{margin-top:14px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:20px}.panel h2{margin:0 0 10px;font-size:22px}.panel p{margin:0;color:#405164;line-height:1.8}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;border-radius:8px;padding:10px 14px;border:1px solid var(--line);background:#fff;color:var(--ink);font-weight:900;text-decoration:none;cursor:pointer}.button.primary{background:var(--accent);border-color:var(--accent);color:#fff}.contact-email{font-weight:900;color:var(--brand)!important;word-break:break-all}.invite-template{width:100%;min-height:220px;margin-top:14px;border:1px solid var(--line);border-radius:8px;padding:12px;background:#f9fbfd;color:#405164;font:inherit;line-height:1.7;resize:vertical}
    footer{max-width:1040px;margin:auto;padding:0 18px 34px;color:var(--muted);font-size:13px}
    @media(max-width:760px){.hero h1{font-size:30px}.grid{grid-template-columns:1fr 1fr}.top{align-items:flex-start}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a href="/circles">サークルDB</a><a href="/representative">自分のサークルを登録</a></nav></div></header>
  <main>
    <section class="hero"><p class="eyebrow">__UNIVERSITY_NAME__ / __SPORT__</p><h1>__CIRCLE_NAME__</h1><p class="lead">__CATCH_COPY__</p><div class="meta">__REPRESENTATIVE_STATUS_BADGE__<span class="badge">__ORG_TYPE__</span><span class="badge">__PREFECTURE__</span></div><div class="actions"><a class="button primary" href="/?sport=__SPORT_ENC__#matches">募集を探す</a><a class="button" href="/circles?sport=__SPORT_ENC__">同じ競技のDBを見る</a></div></section>
    <section class="grid"><div class="metric"><span>人数</span><strong>__MEMBER_COUNT__</strong></div><div class="metric"><span>雰囲気</span><strong>__ATMOSPHERE__</strong></div><div class="metric"><span>経験者割合</span><strong>__EXPERIENCE_RATIO__</strong></div><div class="metric"><span>練習頻度</span><strong>__PRACTICE_FREQUENCY__</strong></div></section>
    <section class="panel"><h2>サークル紹介</h2><p>__INTRODUCTION__</p></section>
    <section class="panel"><h2>活動場所</h2><p>__ACTIVITY_PLACE__</p></section>
    <section class="panel"><h2>代表コメント</h2><p>__REPRESENTATIVE_COMMENT__</p></section>
    __CONTACT_SECTION__
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
    main{max-width:1120px;margin:auto;padding:18px}.hero{padding:18px 0 16px}.hero p{max-width:740px;color:var(--muted);line-height:1.7;margin:8px 0 0}.coverage-notice{display:none;margin:0 0 12px;border:1px solid #f1d2be;background:#fff8f4;color:#7b3b22;border-radius:8px;padding:12px 14px;font-weight:850;line-height:1.7}
    .summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0 14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:13px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:800}.metric strong{display:block;margin-top:6px;font-size:24px}.breadcrumb{display:flex;gap:8px;align-items:center;flex-wrap:wrap;color:var(--muted);font-size:13px;font-weight:800;margin:0 0 10px}.breadcrumb b{color:var(--ink)}
    .panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.filters{display:grid;grid-template-columns:minmax(220px,1fr) repeat(5,150px);gap:8px;padding:14px;border-bottom:1px solid var(--line)}
    input,select{width:100%;border:1px solid #c8d4df;border-radius:8px;min-height:40px;padding:9px 10px;font:inherit;background:#fff;color:var(--ink)}
    .tablewrap{overflow:auto;max-height:680px}table{width:100%;border-collapse:collapse;font-size:14px;min-width:840px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{position:sticky;top:0;background:#f7fafc;color:var(--muted);font-size:12px}.name{font-weight:850}.sub{display:block;color:var(--muted);font-size:12px;margin-top:3px}.badge{display:inline-flex;border-radius:999px;background:#edf2f7;color:#405164;min-height:22px;padding:3px 8px;font-size:12px;font-weight:850}.ok{background:#e1f4eb;color:#0b624d}.blue{background:#e2edf8;color:#20598f}.ssr-error{font-size:13px;line-height:1.45;color:#a54822}
    footer{max-width:1120px;margin:0 auto;padding:20px 18px 38px;color:var(--muted);font-size:13px}.admin-link{color:#65758a}
    @media(max-width:760px){.summary{grid-template-columns:repeat(2,minmax(0,1fr))}.filters{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a class="cta" id="matchBridge" href="/">募集を探す</a><a href="/privacy">プライバシー</a><a href="/terms">利用規約</a><a href="/about-data">掲載情報</a><a href="/contact">問い合わせ</a></nav></div></header>
  <main>
    <section class="hero"><h2>大学サークル検索</h2><p>公開出典をもとにサークル・部活動の名称、競技、検証状態を整理しています。代表者の個人情報や内部メモは公開しません。</p></section>
    <section class="summary"><div class="metric"><span>対象地域</span><strong id="prefCount">__SSR_PREFECTURE_COUNT__</strong></div><div class="metric"><span>対象大学</span><strong id="uniCount">__SSR_UNIVERSITY_COUNT__</strong></div><div class="metric"><span>検索結果</span><strong id="circleCount">__SSR_CIRCLE_COUNT__</strong></div><div class="metric"><span>検証済み/申請済み</span><strong id="verifiedCount">__SSR_VERIFIED_COUNT__</strong></div></section>
    <div id="coverageNotice" class="coverage-notice">関東以外の地域は現在DB拡充中です。掲載漏れや訂正は問い合わせから連絡してください。</div>
    <div class="breadcrumb"><span>検索範囲</span><b id="regionCrumb">関東</b><span>›</span><b id="prefCrumb">すべて</b></div>
    <section class="panel"><div class="filters"><input id="q" placeholder="大学名・団体名・競技で検索"><select id="regionFilter"><option value="">全地域</option></select><select id="prefFilter"><option value="">全都道府県</option></select><input id="sportFilter" list="sportOptions" placeholder="競技名を入力" aria-label="競技名で絞り込み" autocomplete="off"><datalist id="sportOptions"></datalist><select id="statusFilter"><option value="">全検証</option><option value="university_verified">大学公式情報掲載</option><option value="admin_verified">公開情報掲載</option><option value="claimed">申請済み</option><option value="unverified">未確認</option></select><select id="sortFilter"><option value="university">大学名順</option><option value="circle">団体名順</option><option value="prefecture">都道府県順</option><option value="sport">競技順</option><option value="status">検証順</option><option value="updated">更新日順</option></select></div><div class="tablewrap"><table><thead><tr><th>大学</th><th>団体名</th><th>登録済み</th><th>種別</th><th>競技</th><th>検証</th><th>出典</th></tr></thead><tbody id="rows">__INITIAL_CIRCLE_ROWS__</tbody></table></div></section>
  </main>
  <footer>サイトへのご意見・ご要望はこちら: <a class="admin-link" href="mailto:__CONTACT_EMAIL__">__CONTACT_EMAIL__</a> <a class="admin-link" href="/guides">サークル運営ガイド</a> <a class="admin-link" href="/operator">運営者情報</a> <a class="admin-link" href="/contact">問い合わせ</a></footer>
  <script>
    const prefs = __PREFS__;
    const regions = __REGIONS__;
    const sports = __SPORTS__;
    const initialCircles = __INITIAL_CIRCLES__;
    const initialCircleSummary = __INITIAL_CIRCLE_SUMMARY__;
    const params = new URLSearchParams(location.search);
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function statusLabel(v){return ({university_verified:"大学公式情報掲載",admin_verified:"公開情報掲載",claimed:"代表申請受付",unverified:"未確認"}[v] || v)}
    function sourceLabel(v){return ({university_official:"大学公式",self_registered:"本人登録",public_sns:"SNS等",other:"その他"}[v] || v)}
    function badge(v,cls=""){return `<span class="badge ${cls}">${esc(v)}</span>`}
    function fillSelect(el, values, first){el.innerHTML=`<option value="">${first}</option>`+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("")}
    function fillSportOptions(){ $("sportOptions").innerHTML=sports.map(v=>`<option value="${esc(v)}"></option>`).join("") }
    function fillRegions(){ $("regionFilter").innerHTML='<option value="">全地域</option>'+regions.map(r=>`<option value="${esc(r.value)}">${esc(r.label)}</option>`).join("") }
    function selectedRegion(){return regions.find(r=>r.value===$("regionFilter").value)}
    function prefValues(){return selectedRegion()?.prefectures || prefs}
    function syncPrefOptions(){const current=$("prefFilter").value; fillSelect($("prefFilter"),prefValues(),selectedRegion()?`${selectedRegion().label}すべて`:"全都道府県"); if(prefValues().includes(current)) $("prefFilter").value=current}
    function currentQuery(){const qs=new URLSearchParams({audience:"university",q:$("q").value,prefecture:$("prefFilter").value,sport:$("sportFilter").value,status:$("statusFilter").value,sort:$("sortFilter").value}); if($("regionFilter").value) qs.set("region",$("regionFilter").value); return qs}
    async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
    function updateSummary(stats){$("prefCount").textContent=stats.prefectures; $("uniCount").textContent=stats.universities; $("circleCount").textContent=stats.circles; $("verifiedCount").textContent=stats.verified_circles; $("regionCrumb").textContent=selectedRegion()?.label||"全地域"; $("prefCrumb").textContent=$("prefFilter").value||"すべて"; const region=$("regionFilter").value; $("coverageNotice").style.display=region&&region!=="kanto"?"block":"none"}
    function renderRows(data){return data.map(c=>`<tr><td><span class="name">${esc(c.university_name)}</span><span class="sub">${esc(c.prefecture)}${c.city?` / ${esc(c.city)}`:""}</span></td><td><span class="name">${esc(c.circle_name)}</span></td><td>${c.profile_url?`<a href="${esc(c.profile_url)}">URL</a>`:""}</td><td>${badge(c.organization_type||"不明","blue")}</td><td>${esc(c.sport_category||"その他")}</td><td>${badge(statusLabel(c.verification_status),["admin_verified","university_verified"].includes(c.verification_status)?"ok":"")}</td><td>${badge(sourceLabel(c.source_type))}${c.source_url?`<span class="sub"><a href="${esc(c.source_url)}" target="_blank" rel="noopener noreferrer">出典URL</a></span>`:""}</td></tr>`).join("") || `<tr><td colspan="7">データなし</td></tr>`}
    function applyInitialSummary(){if(!initialCircleSummary)return; $("prefCount").textContent=initialCircleSummary.prefectures; $("uniCount").textContent=initialCircleSummary.universities; $("circleCount").textContent=initialCircleSummary.circles; $("verifiedCount").textContent=initialCircleSummary.verified_circles}
    async function refresh(){const qs=currentQuery(); qs.set("limit","120"); $("matchBridge").href="/?"+qs+"#matches"; const [data,stats]=await Promise.all([api("/api/circles?"+qs),api("/api/circle-stats?"+qs)]); updateSummary(stats); $("rows").innerHTML=renderRows(data)}
    async function boot(){fillRegions(); fillSportOptions(); $("regionFilter").value=params.get("region")||""; syncPrefOptions(); $("q").value=params.get("q")||""; $("prefFilter").value=params.get("prefecture")||""; $("sportFilter").value=params.get("sport")||""; $("statusFilter").value=params.get("status")||""; $("sortFilter").value=params.get("sort")||"university"; applyInitialSummary(); if(initialCircles){$("rows").innerHTML=renderRows(initialCircles)} await refresh()}
    ["q","prefFilter","sportFilter","statusFilter","sortFilter"].forEach(id=>$(id).addEventListener("input",refresh));
    $("regionFilter").addEventListener("input",()=>{syncPrefOptions(); refresh()});
    boot().catch(e=>alert(e.message));
  </script>
</body>
</html>"""

SOCIAL_HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>社会人サークル | __SITE_NAME__</title>
  <style>
    :root{--ink:#17212f;--muted:#65758a;--line:#dbe4ed;--paper:#fff;--soft:#f4f7fa;--brand:#0f7a62;--accent:#e15b31;--blue:#2767a5}
    *{box-sizing:border-box}body{margin:0;background:#eef3f7;color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
    header{background:#fff;border-bottom:1px solid var(--line)}.top{max-width:1120px;margin:auto;padding:18px;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
    h1{margin:0;font-size:23px}.nav{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.nav a{color:var(--blue);font-weight:800;text-decoration:none}.nav a.cta{display:inline-flex;align-items:center;min-height:38px;border-radius:8px;padding:8px 12px;background:var(--accent);color:#fff}
    main{max-width:1120px;margin:auto;padding:18px}.hero{padding:18px 0 16px}.hero h2{margin:0;font-size:28px}.hero p{max-width:740px;color:var(--muted);line-height:1.7;margin:8px 0 0}.coverage-notice{display:none;margin:0 0 12px;border:1px solid #f1d2be;background:#fff8f4;color:#7b3b22;border-radius:8px;padding:12px 14px;font-weight:850;line-height:1.7}
    .summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0 14px}.metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:13px}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:800}.metric strong{display:block;margin-top:6px;font-size:24px}.breadcrumb{display:flex;gap:8px;align-items:center;flex-wrap:wrap;color:var(--muted);font-size:13px;font-weight:800;margin:0 0 10px}.breadcrumb b{color:var(--ink)}
    .panel{background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden}.filters{display:grid;grid-template-columns:minmax(220px,1fr) repeat(5,150px);gap:8px;padding:14px;border-bottom:1px solid var(--line)}input,select{width:100%;border:1px solid #c8d4df;border-radius:8px;min-height:40px;padding:9px 10px;font:inherit;background:#fff;color:var(--ink)}
    .tablewrap{overflow:auto;max-height:680px}table{width:100%;border-collapse:collapse;font-size:14px;min-width:980px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{position:sticky;top:0;background:#f7fafc;color:var(--muted);font-size:12px}.name{font-weight:850}.sub{display:block;color:var(--muted);font-size:12px;margin-top:3px}.badge{display:inline-flex;border-radius:999px;background:#edf2f7;color:#405164;min-height:22px;padding:3px 8px;font-size:12px;font-weight:850}.ok{background:#e1f4eb;color:#0b624d}.blue{background:#e2edf8;color:#20598f}.contact-actions{display:flex;gap:7px;flex-wrap:wrap}.contact-link,.copy-invite{display:inline-flex;align-items:center;justify-content:center;min-height:31px;border:1px solid #c8d4df;border-radius:7px;padding:5px 8px;background:#fff;color:#31506b;font:inherit;font-size:12px;font-weight:850;text-decoration:none;cursor:pointer}.contact-link.primary{background:var(--accent);border-color:var(--accent);color:#fff}.copy-invite.copied{background:#e1f4eb;border-color:#b9dfd2;color:#0b624d}.empty{padding:22px;color:var(--muted);line-height:1.8}
    footer{max-width:1120px;margin:0 auto;padding:20px 18px 38px;color:var(--muted);font-size:13px}.admin-link{color:#65758a}@media(max-width:760px){.summary{grid-template-columns:repeat(2,minmax(0,1fr))}.filters{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <header><div class="top"><a class="brand" href="/social">__SITE_NAME__</a><nav class="nav"><a class="cta" id="matchBridge" href="/social#matches">募集を探す</a><a href="/">大学サークルはこちら</a><a href="/privacy">プライバシー</a><a href="/terms">利用規約</a><a href="/about-data">掲載情報</a><a href="/contact">問い合わせ</a></nav></div></header>
  <main>
    <section class="hero"><h2>社会人サークル検索</h2><p>公開出典をもとに、社会人サークルの名称、競技、活動地域を整理しています。サークル員募集や掲載・修正の相談は、代表者登録から行えます。</p><p class="listing-note">公開掲載は公開出典をもとにDBへ掲載した状態です。代表申請・検証とは別に表示しています。</p></section>
    <section class="summary"><div class="metric"><span>対象地域</span><strong id="prefCount">0</strong></div><div class="metric"><span>対象競技</span><strong id="sportCount">0</strong></div><div class="metric"><span>検索結果</span><strong id="circleCount">0</strong></div><div class="metric"><span>公開掲載・代表申請</span><strong id="verifiedCount">0</strong></div></section>
    <div id="coverageNotice" class="coverage-notice">この地域の社会人サークルDBは現在拡充中です。掲載漏れや訂正は問い合わせから連絡してください。</div>
    <div class="breadcrumb"><span>検索範囲</span><b id="regionCrumb">全地域</b><span>›</span><b id="prefCrumb">すべて</b></div>
    <section class="panel"><div class="filters"><input id="q" placeholder="団体名・競技・地域で検索"><select id="regionFilter"><option value="">全地域</option></select><select id="prefFilter"><option value="">全都道府県</option></select><input id="sportFilter" list="sportOptions" placeholder="競技名を入力" aria-label="競技名で絞り込み" autocomplete="off"><datalist id="sportOptions"></datalist><select id="statusFilter"><option value="">全検証</option><option value="university_verified">大学公式情報掲載</option><option value="admin_verified">公開情報掲載</option><option value="claimed">申請済み</option><option value="unverified">未確認</option></select><select id="sortFilter"><option value="prefecture">活動地域順</option><option value="circle">団体名順</option><option value="sport">競技順</option><option value="status">検証順</option><option value="updated">更新日順</option></select></div><div class="tablewrap"><table><thead><tr><th>活動地域</th><th>団体名</th><th>掲載状態</th><th>登録済み</th><th>種別</th><th>競技</th><th>検証</th><th>連絡する</th><th>出典</th></tr></thead><tbody id="rows"></tbody></table></div></section>
  </main>
  <footer><span>サイトへのご意見・ご要望はこちら: <a class="admin-link" href="mailto:__CONTACT_EMAIL__">__CONTACT_EMAIL__</a></span><a class="admin-link" href="/guides">サークル運営ガイド</a><a class="admin-link" href="/operator">運営者情報</a><a class="admin-link" href="/circles">大学サークルDB</a><a class="admin-link" href="/contact">問い合わせ</a></footer>
  <script>
    const prefs = __PREFS__;
    const regions = __REGIONS__;
    const sports = __SPORTS__;
    const params = new URLSearchParams(location.search);
    const $ = id => document.getElementById(id);
    function esc(v){return String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#039;"}[c]))}
    function statusLabel(v){return ({university_verified:"大学公式情報掲載",admin_verified:"公開情報掲載",claimed:"代表申請受付",unverified:"未確認"}[v] || v)}
    function sourceLabel(v){return ({university_official:"公式",self_registered:"本人登録",public_sns:"SNS等",other:"その他"}[v] || v)}
    function badge(v,cls=""){return `<span class="badge ${cls}">${esc(v)}</span>`}
    function listingBadge(c){if(c.verification_status==="claimed")return badge("代表申請受付","ok"); if(c.public_status==="published"&&c.source_url)return badge("公開掲載済み","ok"); return badge("掲載準備中")}
    function fillSelect(el, values, first){el.innerHTML=`<option value="">${first}</option>`+values.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join("")}
    function fillSportOptions(){ $("sportOptions").innerHTML=sports.map(v=>`<option value="${esc(v)}"></option>`).join("") }
    function inviteText(c){return `はじめまして。Circle Matchで${c.circle_name}の活動情報を拝見し、ご連絡しました。\n\n${c.sport_category||""}の活動・交流について、以下の内容でご相談できればと思っています。\n\n・希望内容: [練習試合 / 合同練習 / イベント参加 / メンバー募集について]\n・希望時期: [候補日]\n・活動地域: [地域]\n・こちらの団体: [団体名]\n\n差し支えなければ、ご都合を教えていただけますと幸いです。\n\nCircle Match（https://circle-match.jp/）を通じてご連絡しました。`}
    function contactCell(c){const invite=inviteText(c); const copy=`<button type="button" class="copy-invite" data-invite="${esc(invite)}">文面をコピー</button>`; if(c.public_contact_email){const subject=`【${c.sport_category||"活動"}のご相談】Circle Matchを見てご連絡しました`; const href=`mailto:${encodeURIComponent(c.public_contact_email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(invite)}`; return `<div class="contact-actions"><a class="contact-link primary" href="${esc(href)}">メールを作成</a>${copy}</div><span class="sub">代表者公開の団体共有メール</span>`} if(c.source_url){return `<div class="contact-actions"><a class="contact-link" href="${esc(c.source_url)}" target="_blank" rel="noopener noreferrer">掲載ページへ</a>${copy}</div><span class="sub">掲載ページの連絡方法を利用</span>`} return `<span class="sub">連絡先は代表者登録後に表示</span>`}
    function fillRegions(){ $("regionFilter").innerHTML='<option value="">全地域</option>'+regions.map(r=>`<option value="${esc(r.value)}">${esc(r.label)}</option>`).join("")}
    function selectedRegion(){return regions.find(r=>r.value===$("regionFilter").value)}
    function prefValues(){return selectedRegion()?.prefectures || prefs}
    function syncPrefOptions(){const current=$("prefFilter").value; fillSelect($("prefFilter"),prefValues(),selectedRegion()?`${selectedRegion().label}すべて`:"全都道府県"); if(prefValues().includes(current)) $("prefFilter").value=current}
    function currentQuery(){const qs=new URLSearchParams({audience:"social",q:$("q").value,prefecture:$("prefFilter").value,sport:$("sportFilter").value,status:$("statusFilter").value,sort:$("sortFilter").value}); if($("regionFilter").value) qs.set("region",$("regionFilter").value); return qs}
    async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
    function updateSummary(stats){$("prefCount").textContent=stats.prefectures; $("sportCount").textContent=stats.sports; $("circleCount").textContent=stats.circles; $("verifiedCount").textContent=stats.verified_circles; $("regionCrumb").textContent=selectedRegion()?.label||"全地域"; $("prefCrumb").textContent=$("prefFilter").value||"すべて"; const region=$("regionFilter").value; $("coverageNotice").style.display=region&&region!=="kanto"?"block":"none"}
    async function refresh(){const qs=currentQuery(); qs.set("limit","120"); $("matchBridge").href="/social?"+qs+"#matches"; const [data,stats]=await Promise.all([api("/api/circles?"+qs),api("/api/circle-stats?"+qs)]); updateSummary(stats); $("rows").innerHTML=data.map(c=>`<tr><td><span class="name">${esc(c.prefecture||"地域未設定")}</span><span class="sub">${esc(c.city||c.activity_area||"")}</span></td><td><span class="name">${esc(c.circle_name)}</span></td><td>${listingBadge(c)}</td><td>${c.profile_url?`<a href="${esc(c.profile_url)}">URL</a>`:""}</td><td>${badge(c.organization_type||"社会人サークル","blue")}</td><td>${esc(c.sport_category||"その他")}</td><td>${badge(statusLabel(c.verification_status),["admin_verified","university_verified"].includes(c.verification_status)?"ok":"")}</td><td>${contactCell(c)}</td><td>${badge(sourceLabel(c.source_type))}${c.source_url?`<span class="sub"><a href="${esc(c.source_url)}" target="_blank" rel="noopener noreferrer">出典URL</a></span>`:""}</td></tr>`).join("") || `<tr><td colspan="9" class="empty">社会人サークルDBは現在拡充中です。掲載希望の団体は「サークル員を募集する」または問い合わせから連絡してください。</td></tr>`}
    async function boot(){fillRegions(); fillSportOptions(); $("regionFilter").value=params.get("region")||""; syncPrefOptions(); $("q").value=params.get("q")||""; $("prefFilter").value=params.get("prefecture")||""; $("sportFilter").value=params.get("sport")||""; $("statusFilter").value=params.get("status")||""; $("sortFilter").value=params.get("sort")||"prefecture"; await refresh()}
    $("rows").addEventListener("click",async e=>{const button=e.target.closest("[data-invite]"); if(!button)return; try{await navigator.clipboard.writeText(button.dataset.invite); button.textContent="コピーしました"; button.classList.add("copied"); setTimeout(()=>{button.textContent="文面をコピー";button.classList.remove("copied")},1800)}catch(_){alert("コピーに失敗しました。もう一度お試しください。")}}); ["q","prefFilter","sportFilter","statusFilter","sortFilter"].forEach(id=>$(id).addEventListener("input",refresh)); $("regionFilter").addEventListener("input",()=>{syncPrefOptions(); refresh()}); boot().catch(e=>alert(e.message));
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
  <header><div class="top"><h1>Circle Match DB Admin</h1><nav class="tabs"><button class="tab active" data-view="circles">サークル検索</button><button class="tab" data-view="circle-register">サークル登録</button><button class="tab" data-view="collection">収集状況</button><button class="tab" data-view="candidates">候補レビュー</button><button class="tab" data-view="claims">代表申請</button><button class="tab" data-view="metrics">管理指標</button><button class="tab" data-view="privacy">非公開情報</button><button class="tab" data-view="universities">大学DB</button><button class="tab" data-view="matches">募集DB</button><button class="tab" data-view="imports">CSV取込</button><button class="tab" data-view="logs">更新履歴</button></nav></div></header>
  <main>
    <div class="notice">これはブラウザ保存ではなく、SQLiteファイル <span class="mono">outputs/circlematch.sqlite</span> に保存される実DBです。公開DBと個人情報・内部メモDBを分離し、公開検索APIには個人情報を返しません。</div>
    <nav class="site-links"><a href="/privacy" target="_blank">プライバシーポリシー</a><a href="/terms" target="_blank">利用規約</a><a href="/about-data" target="_blank">掲載情報・削除訂正</a><a href="/contact" target="_blank">問い合わせ</a></nav>
    <section class="summary"><div class="metric"><span>都道府県</span><strong id="prefCount">0</strong></div><div class="metric"><span>大学</span><strong id="uniCount">0</strong></div><div class="metric"><span>サークル</span><strong id="circleCount">0</strong></div><div class="metric"><span>検証済み/申請済み</span><strong id="verifiedCount">0</strong></div><div class="metric"><span>候補</span><strong id="candidateCount">0</strong></div><div class="metric"><span>募集中</span><strong id="matchCount">0</strong></div></section>
    <section id="circles" class="view active"><div class="panel"><div class="head"><div><h2>全国サークル台帳</h2><p>検索・絞り込み・編集対象の確認</p></div><button id="reloadCircles">再読込</button></div><div class="filters"><input id="q" placeholder="大学名・団体名・競技・地域"><select id="prefFilter"><option value="">全都道府県</option></select><select id="orgTypeFilter"><option value="">全種別</option></select><select id="sportFilter"><option value="">全競技</option></select><select id="statusFilter"><option value="">全ステータス</option></select><select id="adminSortFilter"><option value="university">大学名順</option><option value="circle">団体名順</option><option value="prefecture">都道府県順</option><option value="sport">競技順</option><option value="type">種別順</option><option value="status">検証順</option><option value="updated">更新日順</option></select></div><div class="tablewrap"><table class="circle-table"><thead><tr><th>大学</th><th>団体名</th><th>種別</th><th>競技</th><th>ソース</th><th>検証</th><th>操作</th></tr></thead><tbody id="circleRows"></tbody></table></div></div></section>
    <section id="circle-register" class="view"><div class="panel"><div class="head"><div><h2>サークル登録/更新</h2><p>公開DBに載せる事実情報だけを登録します。代表者連絡先や内部メモは非公開DBで扱います。</p></div><button id="clearCircleForm" type="button">新規入力</button></div><form id="circleForm"><label>大学<select id="circleUniversity" required></select></label><label>団体名<input id="circleName" required></label><div class="row"><label>団体種別<select id="organizationType"></select></label><label>競技<select id="sport"></select></label></div><label>活動地域<input id="activityArea"></label><div class="row"><label>出典種別<select id="sourceType"></select></label><label>検証<select id="verificationStatus"></select></label></div><label>出典URL<input id="sourceUrl" type="url"></label><button class="primary">保存</button></form></div></section>
    <section id="collection" class="view"><div class="panel"><div class="head"><div><h2>大学別の収集状況</h2><p>未収集・一部収集済み・大学公式情報掲載を追跡します。</p></div><button id="reloadCollection">再読込</button></div><div class="tablewrap"><table><thead><tr><th>大学</th><th>地域</th><th>登録サークル数</th><th>収集状態</th><th>検索クエリ/出典</th><th>最終確認</th></tr></thead><tbody id="collectionRows"></tbody></table></div></div></section>
    <section id="candidates" class="view"><div class="panel"><div class="head"><div><h2>候補レビュー</h2><p>自動収集・手動調査で見つけた未公開候補。正式DBへの昇格前に出典を確認します。</p></div><button id="reloadCandidates">再読込</button></div><div class="tablewrap"><table><thead><tr><th>ID</th><th>大学</th><th>候補サークル</th><th>競技/状態</th><th>出典</th><th>メモ</th><th>操作</th></tr></thead><tbody id="candidateRows"></tbody></table></div></div></section>
    <section id="claims" class="view"><div class="panel"><div class="head"><div><h2>代表者申請・大学メール確認</h2><p>大学メールから届いた確認メールの差出人と申請内容を照合してから、確認済みにします。ここに表示される氏名・メールアドレスは公開されません。</p></div><button id="reloadClaims">再読込</button></div><div class="tablewrap"><table><thead><tr><th>申請日時</th><th>大学・団体</th><th>代表者</th><th>確認状況</th><th>出典</th><th>操作</th></tr></thead><tbody id="claimRows"></tbody></table></div></div></section>
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
    function statusLabel(v){return ({university_verified:"大学公式情報掲載",admin_verified:"公開情報掲載",claimed:"代表申請受付",unverified:"未確認"}[v] || v)}
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
    function claimStatusLabel(claim){const label=claim.organization_type==="社会人サークル"?"代表者メール":"大学メール"; return claim.university_email_verified?`${label}確認済み`:claim.status==="pending"?"確認メール待ち":claim.status||"確認待ち"}
    async function refreshClaims(){const rows=await api("/api/claims"); $("claimRows").innerHTML=rows.map(c=>{const social=c.organization_type==="社会人サークル"; const confirmationLabel=social?"代表者メール確認済みにする":"大学メール確認済みにする"; const domainNote=social?"大学ドメイン照合: 対象外":`公式ドメイン照合: ${c.university_email_domain_checked?"済":"未"}`; return `<tr><td>${esc(c.created_at)}<br><span class="mono">${esc(c.claim_id)}</span></td><td><b>${esc(c.university_name)}</b><br>${esc(c.circle_name)}<br><span class="muted">${esc(c.sport_category)}</span></td><td>${esc(c.claimant_name||"")}<br><span class="mono">${esc(c.claimant_email)}</span></td><td><span class="badge ${c.university_email_verified?"ok":"warn"}">${esc(claimStatusLabel(c))}</span><br><span class="muted">${domainNote}</span></td><td>${c.evidence_url?`<a href="${esc(c.evidence_url)}" target="_blank">出典URL</a>`:"<span class='muted'>未登録</span>"}</td><td>${c.university_email_verified?`<span class="muted">${esc(c.university_email_verified_at||"確認済み")}</span>`:`<button class="primary" data-verify-claim="${esc(c.claim_id)}">${confirmationLabel}</button>`}</td></tr>`}).join("") || `<tr><td colspan="6" class="muted">代表申請はまだありません</td></tr>`; document.querySelectorAll("[data-verify-claim]").forEach(b=>b.onclick=()=>verifyClaim(b.dataset.verifyClaim));}
    async function refreshMetrics(){const data=await api("/api/admin_metrics"); $("metricUniversityRows").innerHTML=data.by_university.map(r=>`<tr><td><b>${esc(r.university_name)}</b></td><td>${esc(r.prefecture)}</td><td><span class="badge ${r.circle_count>0?"ok":"warn"}">${r.circle_count}</span></td><td><span class="badge">${r.candidate_count}</span></td></tr>`).join(""); const sections=[["種別",data.by_organization_type],["競技",data.by_sport],["検証",data.by_verification],["出典",data.by_source]]; $("metricRows").innerHTML=sections.flatMap(([label,rows])=>rows.map(r=>`<tr><td>${label}</td><td>${esc(r.name)}</td><td><span class="badge">${r.count}</span></td></tr>`)).join("")}
    async function refreshPrivacy(){const data=await api("/api/privacy_metrics"); $("privacyRows").innerHTML=data.map(r=>`<tr><td><b>${esc(r.label)}</b><br><span class="muted">${esc(r.description)}</span></td><td><span class="badge">${r.count}</span></td><td>${r.public_api?`<span class="badge warn">返す</span>`:`<span class="badge ok">返さない</span>`}</td></tr>`).join("")}
    async function promoteCandidate(id){if(!confirm("この候補を正式サークルDBへ昇格しますか？"))return; await api("/api/candidates/promote",{method:"POST",body:JSON.stringify({candidate_id:id})}); await refreshAll();}
    async function rejectCandidate(id){if(!confirm("この候補を却下しますか？"))return; await api("/api/candidates/reject",{method:"POST",body:JSON.stringify({candidate_id:id})}); await refreshAll();}
    async function verifyClaim(id){if(!confirm("届いた確認メールの差出人と、この申請内容を照合済みですか？"))return; await api("/api/claims/verify",{method:"POST",body:JSON.stringify({claim_id:id})}); await refreshAll();}
    async function refreshLogs(){const rows=await api("/api/audit_logs"); $("logRows").innerHTML=rows.map(l=>`<tr><td>${esc(l.created_at)}</td><td><span class="badge">${esc(l.action)}</span></td><td>${esc(l.entity_type)}<br><span class="mono">${esc(l.entity_id)}</span></td><td><span class="mono">${esc(l.payload)}</span></td></tr>`).join("")}
    function switchView(viewId){document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x.dataset.view===viewId));document.querySelectorAll(".view").forEach(x=>x.classList.toggle("active",x.id===viewId));window.scrollTo({top:0,behavior:"smooth"});}
    function loadCircle(id, rows){const c=rows.find(x=>x.circle_id===id); if(!c)return; $("circleUniversity").value=c.university_id; $("circleName").value=c.circle_name; $("organizationType").value=c.organization_type||"不明"; $("sport").value=c.sport_category; $("activityArea").value=c.activity_area||""; $("sourceType").value=c.source_type; $("verificationStatus").value=c.verification_status; $("sourceUrl").value=c.source_url||""; switchView("circle-register");}
    async function boot(){fillSelect($("sport"),sports); fillSelect($("organizationType"),organizationTypes); fillSelect($("sourceType"),sourceTypes); fillSelect($("verificationStatus"),statuses); fillSelect($("prefFilter"),prefs,"全都道府県"); fillSelect($("orgTypeFilter"),organizationTypes,"全種別"); fillSelect($("sportFilter"),sports,"全競技"); fillSelect($("statusFilter"),statuses,"全ステータス"); fillSelect($("universityPrefecture"),prefs); await refreshAll();}
    async function refreshAll(){await refreshSummary(); await refreshUniversities(); await refreshCircles(); await refreshMatches(); await refreshCollection(); await refreshCandidates(); await refreshClaims(); await refreshMetrics(); await refreshPrivacy(); await refreshLogs();}
    document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>switchView(t.dataset.view));
    ["q","prefFilter","orgTypeFilter","sportFilter","statusFilter","adminSortFilter"].forEach(id=>$(id).addEventListener("input",refreshCircles)); $("reloadCircles").onclick=refreshCircles; $("reloadCollection").onclick=refreshCollection; $("reloadCandidates").onclick=refreshCandidates; $("reloadClaims").onclick=refreshClaims; $("reloadMetrics").onclick=refreshMetrics; $("reloadPrivacy").onclick=refreshPrivacy; $("reloadLogs").onclick=refreshLogs;
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
    entry = f"{now()} {message}"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{entry}\n")
    # Render captures stderr, so failed SSR reads are diagnosable in deploy logs.
    print(entry, file=sys.stderr, flush=True)


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
    if not profile.get("email_confirmed_at"):
        raise ValueError("メールアドレスの確認が完了していません")
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


def logout_token(session_id):
    return hmac.new(SESSION_SECRET.encode(), ("logout:" + session_id).encode(), hashlib.sha256).hexdigest()


def account_navigation(session_id, return_to="/mypage"):
    if not current_user(session_id).get("authenticated"):
        target = safe_return_path(return_to, "/mypage")
        if urlparse(target).path in {"/signin", "/logout"}:
            target = "/mypage"
        href = html.escape("/signin?" + urlencode({"return_to": target}), quote=True)
        return f'<a id="accountLink" class="account cm-account" href="{href}">ログイン</a>'
    return ('<a id="accountLink" class="account cm-account" href="/mypage">マイページ</a>'
            '<form class="account-logout" action="/logout" method="post">'
            f'<input type="hidden" name="csrf_token" value="{logout_token(session_id)}">'
            '<button type="submit">ログアウト</button></form>')


def personalize_navigation(body, session_id, return_to):
    # Work only on the first public header, never on user content or page scripts.
    page = body.decode("utf-8")
    before, separator, after = page.partition("</header>")
    if not separator or 'class="brand"' not in before or "</nav>" not in before:
        return body
    old = '<a id="accountLink" class="account" href="/signin?return_to=/mypage">ログイン</a>'
    if 'data-account-navigation="hidden"' not in before:
        navigation = account_navigation(session_id, return_to)
        before = before.replace(old, navigation, 1) if old in before else before.replace("</nav>", navigation + "</nav>", 1)
    before = before.replace('class="brand"', 'class="brand" aria-label="Circle Match"', 1)
    before = before.replace("<header", '<header data-notification-header="true"', 1)
    user = current_user(session_id)
    count = unread_notification_count(user) if user.get("authenticated") else 0
    label = f"通知（未読{count}件）" if count else "通知"
    bell = (f'<a id="notificationBell" class="cm-bell" href="/notifications" aria-label="{label}" title="{label}">'
            f'{BELL_ICON}<span id="notificationBadge" class="cm-notification-badge" {"" if count else "hidden"}>{count or ""}</span></a>')
    home = f'<a class="cm-home" href="/" aria-label="ホーム" title="ホーム">{HOME_ICON}</a>'
    before = re.sub(r'<a\b[^>]*>\s*(?:大会・イベント|サークルDB)\s*</a>', '', before)
    before = before.replace("</nav>", home + bell + "</nav>", 1)
    before = before.replace("</head>", NOTIFICATION_STYLE + "</head>", 1)
    if user.get("authenticated"):
        after = after.replace("</body>", NOTIFICATION_BADGE_SCRIPT + "</body>", 1)
    after = after.replace('</body>', '<script>window.addEventListener("pageshow",event=>{if(event.persisted)location.reload()});</script></body>', 1)
    return (before + separator + after).encode("utf-8")


# Lucide bell icon, ISC license (see docs/licenses/lucide.txt).
BELL_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.268 21a2 2 0 0 0 3.464 0"/><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"/></svg>'

NOTIFICATION_STYLE = '''<style>
[data-notification-header]{position:sticky;top:0;z-index:30}
header nav a.cm-bell,header nav a.cm-home{position:relative;display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;min-height:44px;flex:0 0 44px;padding:0;border:1px solid #dbe4ed;border-radius:8px;background:#fff;color:#243c50;text-decoration:none;box-sizing:border-box}
header nav a.cm-home{border-color:transparent}.cm-home:hover{background:#edf4f7}.cm-home:focus-visible{outline:3px solid #e15b31;outline-offset:2px}
.cm-bell:hover{background:#edf4f7}.cm-bell:focus-visible{outline:3px solid #e15b31;outline-offset:2px}
.cm-notification-badge{position:absolute;right:-4px;top:-4px;min-width:18px;padding:2px 4px;border-radius:12px;background:#bc3519;color:#fff;font:700 11px/1.3 system-ui;text-align:center}
.cm-notification-badge[hidden]{display:none}.notification-list{padding:0 18px}.notification-heading{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
@media(max-width:620px){header a.brand .brand-wordmark{display:none}.site-nav{gap:6px}.site-nav .main-nav{gap:2px}}
</style>'''

NOTIFICATION_BADGE_SCRIPT = '''<script>
(()=>{
const bell=document.getElementById('notificationBell'),badge=document.getElementById('notificationBadge');let busy=false;
function update(count){badge.textContent=count||'';badge.hidden=!count;const label=count?`通知（未読${count}件）`:'通知';bell.setAttribute('aria-label',label);bell.title=label}
async function refresh(){if(busy||document.hidden)return;busy=true;try{const r=await fetch('/api/notifications/unread',{cache:'no-store'});if(r.status===401){update(0);return}if(!r.ok)throw Error();const data=await r.json();update(data.unread_count)}catch(_){bell.title='通知（新着の確認に失敗しました）'}finally{busy=false}}
window.addEventListener('notifications-read',e=>update(e.detail.unread_count));window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);setInterval(refresh,30000);
})();
</script>'''


def script_json(value):
    """Serialize server data safely for an inline script without exposing secrets."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def ssr_error_value():
    return '<span class="ssr-error">データを取得できませんでした</span>'


def ssr_circle_rows(circles):
    """Render the first public DB records into the initial /circles document."""
    if not circles:
        return '<tr><td colspan="7" class="ssr-error">データを取得できませんでした</td></tr>'

    status_labels = {
        "university_verified": "大学公式情報掲載",
        "admin_verified": "公開情報掲載",
        "claimed": "代表申請受付",
        "unverified": "未確認",
    }
    source_labels = {
        "university_official": "大学公式",
        "self_registered": "本人登録",
        "public_sns": "SNS等",
        "other": "その他",
    }
    rendered = []
    for circle in circles:
        university = html.escape(str(circle.get("university_name") or ""))
        prefecture = html.escape(str(circle.get("prefecture") or ""))
        city = html.escape(str(circle.get("city") or ""))
        circle_name = html.escape(str(circle.get("circle_name") or ""))
        organization_type = html.escape(str(circle.get("organization_type") or "不明"))
        sport = html.escape(str(circle.get("sport_category") or "その他"))
        status = str(circle.get("verification_status") or "unverified")
        status_label = html.escape(status_labels.get(status, status))
        status_class = " ok" if status in {"admin_verified", "university_verified"} else ""
        source = str(circle.get("source_type") or "other")
        source_label = html.escape(source_labels.get(source, source))
        profile_url = str(circle.get("profile_url") or "")
        source_url = str(circle.get("source_url") or "")
        profile_link = f'<a href="{html.escape(profile_url, quote=True)}">URL</a>' if profile_url else ""
        source_link = (
            f'<span class="sub"><a href="{html.escape(source_url, quote=True)}" target="_blank" rel="noopener noreferrer">出典URL</a></span>'
            if source_url else ""
        )
        location = f"{prefecture}{f' / {city}' if city else ''}"
        rendered.append(
            "<tr>"
            f'<td><span class="name">{university}</span><span class="sub">{location}</span></td>'
            f'<td><span class="name">{circle_name}</span></td>'
            f"<td>{profile_link}</td>"
            f'<td><span class="badge blue">{organization_type}</span></td>'
            f"<td>{sport}</td>"
            f'<td><span class="badge{status_class}">{status_label}</span></td>'
            f'<td><span class="badge">{source_label}</span>{source_link}</td>'
            "</tr>"
        )
    return "".join(rendered)


def render_legacy_home_html():
    # The public DB lives on the Render persistent disk. Initial HTML is rendered
    # from that server-side source so crawlers do not depend on browser JavaScript.
    initial_sports = SPORTS
    try:
        initial_summary = summary("university")
        initial_sports = sport_options("university")
        stat_values = {
            "__SSR_UNIVERSITY_COUNT__": str(initial_summary["universities"]),
            "__SSR_CIRCLE_COUNT__": str(initial_summary["circles"]),
            "__SSR_VERIFIED_COUNT__": str(initial_summary["verified_circles"]),
            "__SSR_MATCH_COUNT__": str(initial_summary["match_posts"]),
        }
        initial_summary_json = script_json(initial_summary)
    except Exception as exc:
        log(f"SSR top stats failed: {type(exc).__name__}: {exc}")
        stat_values = {
            "__SSR_UNIVERSITY_COUNT__": ssr_error_value(),
            "__SSR_CIRCLE_COUNT__": ssr_error_value(),
            "__SSR_VERIFIED_COUNT__": ssr_error_value(),
            "__SSR_MATCH_COUNT__": ssr_error_value(),
        }
        initial_summary_json = "null"

    page = (
        with_adsense(MATCH_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__CONTACT_EMAIL__", CONTACT_EMAIL)
        .replace("__SPORTS__", script_json(initial_sports))
        .replace("__REGIONS__", script_json(region_options()))
        .replace("__POPULAR_SPORTS__", script_json([
            {"name": name, "label": label, "code": code, "color": color, "image": image}
            for name, label, code, color, image in POPULAR_SPORTS
        ]))
        .replace("__PREFS__", script_json(PREFECTURES))
        .replace("__INITIAL_SUMMARY__", initial_summary_json)
    )
    for placeholder, value in stat_values.items():
        page = page.replace(placeholder, value)
    return page.encode("utf-8")


EVENT_BASE_CSS = """
  [hidden]{display:none!important}
  .mypage-tabs{flex-wrap:wrap}.my-card,.app-row>span{min-width:0;overflow-wrap:anywhere}
  .message-form{display:grid;gap:8px;margin-top:14px}.message p{white-space:pre-wrap;overflow-wrap:anywhere}
  .app-row .card-actions{flex-shrink:0}
  @media(max-width:600px){.apps .app-row{align-items:flex-start;flex-direction:column}.panel .mypage-tabs button{font-size:13px}.my-card{margin:10px 0}}
  @media(max-width:360px){.site-nav .main-nav a{padding:6px}}
  .event-breadcrumb{margin:0 0 12px;font-size:14px}.event-results-intro{position:relative;min-height:164px;display:flex;align-items:center;padding:24px;overflow:hidden;color:#fff;background:#102a43}.event-results-intro img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:right center}.event-results-intro:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(9,18,31,.88),rgba(9,18,31,.35) 70%,transparent)}.event-results-intro h1{position:relative;z-index:1;margin:0;max-width:75%;font-size:30px;line-height:1.45;overflow-wrap:anywhere}.event-results-intro h1 span{display:block;font-size:18px}.event-grid>.empty,.event-grid>.error-box{grid-column:1/-1}.event-results .filter-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.event-results .panel-head{align-items:center}.event-results #eventResultCount{margin:4px 0 0}.event-results .filter-grid>*{min-width:0}@media(max-width:600px){.event-results-intro{min-height:132px;padding:16px}.event-results-intro h1{font-size:24px;max-width:85%}.event-results-intro h1 span{font-size:16px}.event-results .filter-grid{grid-template-columns:repeat(2,minmax(0,1fr));padding:12px}.event-results .panel-head{padding:12px}.event-results .panel-head h2{font-size:19px}.event-results .empty{padding:12px}.event-results .panel-head>.button{display:none}}
  :root{--ink:#17212f;--muted:#64748b;--line:#dbe4ed;--paper:#fff;--soft:#f4f7fa;--brand:#0f7a62;--accent:#e15b31;--navy:#102a43;--warning:#a54822}
  *{box-sizing:border-box}body{margin:0;background:var(--soft);color:var(--ink);font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}a{color:inherit}.site-header{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}.site-nav{max-width:1180px;margin:auto;padding:10px 16px;display:flex;align-items:center;gap:12px}.brand{flex:0 0 auto;font-weight:900;text-decoration:none}.main-nav{display:flex;align-items:center;gap:5px;min-width:0;margin-left:auto}.main-nav a{min-height:38px;display:inline-flex;align-items:center;justify-content:center;padding:8px 11px;border-radius:8px;color:#405164;font-size:14px;font-weight:900;text-decoration:none;white-space:nowrap}.main-nav a.active{background:#e8f4ef;color:#0d674f}.main-nav a.publish{background:var(--accent);color:#fff}.main-nav a.account{border:1px solid var(--accent);color:var(--accent);background:#fff}.container{max-width:1180px;margin:auto;padding:22px 16px 50px}.intro{display:flex;align-items:end;justify-content:space-between;gap:18px;padding:4px 0 14px}.intro h1{margin:0;font-size:clamp(27px,4vw,42px);line-height:1.15}.intro p{max-width:700px;margin:10px 0 0;color:#50637a;line-height:1.75}.eyebrow{margin:0 0 7px;color:var(--brand);font-weight:950;font-size:12px;letter-spacing:.07em;text-transform:uppercase}.tabs{display:flex;gap:8px;border-bottom:1px solid var(--line);margin-bottom:18px}.tabs a{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:10px 17px;border-bottom:3px solid transparent;color:#61738b;text-decoration:none;font-weight:900}.tabs a.active{border-color:var(--accent);color:var(--ink)}.panel{background:var(--paper);border:1px solid var(--line);border-radius:8px;overflow:hidden}.section{margin-top:18px}.panel-head{padding:16px 18px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:end;gap:12px;flex-wrap:wrap}.panel-head h2{margin:0;font-size:22px}.panel-head p{margin:7px 0 0;color:var(--muted);line-height:1.65}.button{display:inline-flex;align-items:center;justify-content:center;min-height:42px;padding:9px 14px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink);font:inherit;font-size:14px;font-weight:900;text-decoration:none;cursor:pointer}.button.primary{background:var(--accent);border-color:var(--accent);color:#fff}.button.secondary{background:var(--brand);border-color:var(--brand);color:#fff}.button:disabled{opacity:.55;cursor:not-allowed}.sport-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.sport-card{position:relative;overflow:hidden;min-height:154px;border:1px solid rgba(255,255,255,.12);border-radius:8px;background:#132238;text-decoration:none;color:#fff;box-shadow:0 10px 24px rgba(20,36,56,.15)}.sport-card:hover{transform:translateY(-2px);box-shadow:0 16px 30px rgba(20,36,56,.23)}.sport-card img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(1.1) contrast(1.03)}.sport-card:before{content:"";position:absolute;inset:0;z-index:1;background:linear-gradient(90deg,rgba(9,18,31,.92),rgba(9,18,31,.5) 58%,rgba(9,18,31,.1))}.sport-copy{position:relative;z-index:2;display:grid;gap:6px;padding:17px;max-width:76%}.sport-copy strong{font-size:24px;line-height:1.1}.sport-copy span{font-size:12px;font-weight:800;color:rgba(255,255,255,.84)}.sport-copy em{position:absolute;left:17px;top:98px;font-style:normal;font-size:12px;font-weight:900;padding:7px 11px;border-radius:999px;background:rgba(255,255,255,.18);white-space:nowrap}.filter-grid{display:grid;grid-template-columns:1.4fr repeat(4,minmax(120px,1fr));gap:9px;padding:14px;background:#f9fbfd;border-bottom:1px solid var(--line)}input,select,textarea{width:100%;min-height:42px;border:1px solid #cbd7e2;border-radius:8px;padding:9px 10px;background:#fff;color:var(--ink);font:inherit}textarea{min-height:112px;resize:vertical}.event-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:14px}.event-card{display:flex;flex-direction:column;gap:10px;min-height:252px;padding:15px;border:1px solid var(--line);border-radius:8px;background:#fff}.event-card h3{margin:0;font-size:18px;line-height:1.35}.event-card h3 a{text-decoration:none}.event-card p{margin:0;color:#52657a;font-size:13px;line-height:1.65}.card-meta{display:grid;gap:5px;color:#52657a;font-size:13px}.card-footer{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:auto}.badge{display:inline-flex;align-items:center;min-height:24px;padding:3px 8px;border-radius:999px;background:#edf2f7;color:#405164;font-size:12px;font-weight:900}.badge.open{background:#e2f5ed;color:#0d674f}.badge.pending{background:#fff4dd;color:#8a5a00}.badge.closed{background:#f1f3f5;color:#6c7785}.badge.cancelled{background:#fff0f0;color:#a33}.empty,.error-box{padding:24px;color:var(--muted);line-height:1.75}.error-box{color:#9f321e;background:#fff5f2;border:1px solid #f0c6ba;border-radius:8px}.db-toggle{display:flex;gap:7px}.db-toggle a{display:inline-flex;min-height:38px;align-items:center;padding:8px 12px;border:1px solid var(--line);border-radius:8px;text-decoration:none;font-size:14px;font-weight:900}.db-toggle a.active{border-color:var(--brand);background:#e8f4ef;color:#0d674f}.db-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:14px}.metric{padding:13px;border:1px solid var(--line);border-radius:8px;background:#fff}.metric span{display:block;color:var(--muted);font-size:12px;font-weight:850}.metric strong{display:block;margin-top:6px;font-size:24px}.circle-list{display:grid;gap:0}.circle-row{display:grid;grid-template-columns:1.2fr 1.2fr .8fr .9fr;gap:10px;padding:14px 16px;border-top:1px solid var(--line);font-size:14px}.circle-row strong{display:block}.circle-row small{display:block;margin-top:3px;color:var(--muted)}.notice{margin-top:16px;padding:17px;border:1px solid #d7e7dd;background:#f6fbf8;border-radius:8px;color:#365447;line-height:1.75}.about{margin-top:26px;padding:22px;background:#fff;border-top:1px solid var(--line);color:#53667b;line-height:1.8}.about h2{margin:0 0 9px;color:var(--ink);font-size:20px}.detail{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:16px}.detail-main,.detail-side{background:#fff;border:1px solid var(--line);border-radius:8px;padding:20px}.detail-main h1{margin:0;font-size:32px;line-height:1.25}.detail-main p{line-height:1.8;color:#405164}.detail-meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:18px}.detail-meta div{padding:11px;border-radius:8px;background:#f7fafc}.detail-meta span{display:block;color:#64748b;font-size:12px;font-weight:850}.detail-meta strong{display:block;margin-top:4px;line-height:1.55}.detail-side{position:sticky;top:75px;height:max-content}.detail-side h2{margin:0;font-size:18px}.detail-side p{color:#64748b;line-height:1.65}.form-shell{max-width:860px;margin:auto}.stepper{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin-bottom:16px}.stepper span{padding:9px;border-bottom:3px solid #dbe4ed;color:#76879b;font-size:13px;font-weight:900}.stepper span.active{border-color:var(--accent);color:var(--ink)}.form-section{display:none;padding:20px}.form-section.active{display:block}.field-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.field{display:grid;gap:6px}.field.full{grid-column:1/-1}.field label{font-size:13px;font-weight:900;color:#405164}.help{color:#64748b;font-size:12px;line-height:1.55}.form-actions{display:flex;justify-content:space-between;gap:10px;padding:16px 20px;border-top:1px solid var(--line);flex-wrap:wrap}.preview{padding:15px;border-radius:8px;background:#f8fbfd;border:1px solid var(--line);line-height:1.7}.mypage-tabs{display:flex;gap:8px;margin-bottom:12px}.mypage-tabs button{border:1px solid var(--line);border-radius:8px;background:#fff;padding:9px 12px;font:inherit;font-weight:900;cursor:pointer}.mypage-tabs button.active{border-color:var(--brand);background:#e8f4ef;color:#0d674f}.my-section{display:none}.my-section.active{display:block}.my-card{margin-top:10px;padding:15px;border:1px solid var(--line);border-radius:8px;background:#fff}.my-card h3{margin:0 0 6px;font-size:18px}.my-card p{margin:5px 0;color:#607086;font-size:14px;line-height:1.6}.card-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:11px}.apps{display:grid;gap:8px;margin-top:12px}.app-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px;border-radius:8px;background:#f8fbfd}.messages{margin-top:12px;border-top:1px solid var(--line);padding-top:12px}.message-log{display:grid;gap:7px;max-height:220px;overflow:auto}.message{padding:8px 10px;border-radius:8px;background:#f4f7fa;font-size:13px;line-height:1.55}.message.mine{background:#e9f6ef}.notification{padding:11px 0;border-bottom:1px solid var(--line);font-size:14px;line-height:1.6}.notification small{display:block;color:#75869b;margin-top:4px}.mobile-apply{display:none}
  @media(max-width:820px){.site-nav{padding:8px 12px;gap:7px}.main-nav{gap:2px}.main-nav a{min-height:36px;padding:7px;font-size:12px}.main-nav a.db-label{display:none}.container{padding:16px 12px 40px}.intro{align-items:start;flex-direction:column}.sport-grid,.event-grid{grid-template-columns:1fr 1fr}.sport-card{min-height:132px}.sport-copy{padding:13px}.sport-copy strong{font-size:18px}.sport-copy em{left:13px;top:84px}.filter-grid{grid-template-columns:1fr 1fr}.event-grid{padding:12px}.detail{grid-template-columns:1fr}.detail-side{position:static}.detail-meta,.field-grid{grid-template-columns:1fr}.circle-row{grid-template-columns:1fr 1fr}.circle-row>div:nth-child(n+3){display:none}.db-summary{grid-template-columns:1fr 1fr}.mobile-apply{display:flex;position:sticky;bottom:8px;z-index:10;margin-top:12px;box-shadow:0 8px 20px rgba(23,33,47,.18)}}
  @media(max-width:460px){.main-nav a.tab-link{display:none}.main-nav a.publish{margin-left:auto}.sport-grid,.event-grid{grid-template-columns:1fr}.sport-card{min-height:145px}.filter-grid{grid-template-columns:1fr}.detail-main,.detail-side{padding:16px}.detail-main h1{font-size:26px}.db-summary{grid-template-columns:1fr}.stepper span{font-size:11px}.form-actions .button{flex:1}}
"""


def event_shell(title, body, script=""):
    page = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | __SITE_NAME__</title><style>{EVENT_BASE_CSS}{EVENT_UX_CSS}</style></head><body>
<header class="site-header"><div class="site-nav"><a class="brand" href="/">__SITE_NAME__</a><nav class="main-nav"><a class="tab-link __EVENT_TAB__" href="__EVENT_TAB_URL__">大会・イベント</a><a class="tab-link db-label __DB_TAB__" href="__DB_TAB_URL__">サークルDB</a><a id="accountLink" class="account" href="/signin?return_to=/mypage">ログイン</a></nav></div></header>
<main class="container">{body}</main>{script}</body></html>"""
    return with_adsense(page).replace("__SITE_NAME__", SITE_NAME)


EVENT_UX_CSS = """
[hidden]{display:none!important}.intro h1{font-size:32px;letter-spacing:0}.eyebrow{letter-spacing:0}
.field{min-width:0;margin-bottom:12px;align-content:start}.field input,.field select,.field textarea{min-width:0}
.field input:not([type=hidden]),.field select{height:46px}.field label{line-height:1.5}
input[type=radio],input[type=checkbox]{width:20px;height:20px;min-height:20px;padding:0;accent-color:#0f7a62}
#participationChoices label{display:flex;align-items:center;gap:8px;min-height:44px}
fieldset{border:0;padding:0;margin:0 0 16px}legend{font-weight:700}.button{min-height:44px}
.application-recap{padding:12px 0 20px}.application-recap h2{font-size:22px}.application-recap dl,#reviewAnswers{display:grid;grid-template-columns:150px minmax(0,1fr);gap:8px 16px;line-height:1.6}
dt{font-weight:700}dd{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}.preview p,.app-message{white-space:pre-wrap;overflow-wrap:anywhere}
.preview h3{font-size:20px;margin:0 0 12px}.preview dl{display:grid;grid-template-columns:140px minmax(0,1fr);gap:8px}
.error-box{margin-top:12px}.form-section:focus,.error-box:focus{outline:2px solid #e15b31;outline-offset:2px}
.mypage-tabs{flex-wrap:wrap;padding:10px}.app-row{align-items:flex-start;flex-wrap:wrap}.app-row>div:first-child{flex:1;min-width:180px}
.notification.unread{border-left:3px solid #e15b31;padding-left:10px}.notification a{display:inline-flex;min-height:44px;align-items:center}
.ux-dialog{width:min(460px,calc(100% - 32px));border:1px solid #dbe4ed;border-radius:8px;padding:24px;color:#17212f}.ux-dialog::backdrop{background:#17212f88}.ux-dialog h2{font-size:20px;margin-top:0}
.db-pager{display:flex;gap:12px;align-items:center;justify-content:center;flex-wrap:wrap;padding:16px}.circle-row a{display:inline-flex;min-height:44px;align-items:center}
#events,#dbList{scroll-margin-top:85px}
@media(max-width:820px){.circle-row>div:nth-child(n+3){display:block}.circle-row{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.circle-row>*{overflow-wrap:anywhere}}
@media(max-width:460px){.intro h1{font-size:25px}.intro p{font-size:14px}.sport-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.sport-card{min-height:112px}.sport-copy{max-width:100%;padding:10px}.sport-copy strong{font-size:17px;line-height:1.3;overflow-wrap:anywhere}.sport-copy span{display:none}.sport-copy em{position:static;padding:0;margin-top:12px;background:none;font-size:12px}.event-grid{grid-template-columns:1fr}.panel-head h2{font-size:19px}.form-section{padding:14px}.form-actions{padding:12px}.form-actions .card-actions{margin:0;width:100%}.application-recap dl,#reviewAnswers,.preview dl{grid-template-columns:1fr;gap:3px}.application-recap dd,#reviewAnswers dd,.preview dd{margin-bottom:10px}.mypage-tabs{gap:4px}.mypage-tabs button{font-size:13px;min-height:44px;padding:8px}.app-row .card-actions{width:100%}}
.publish-cta{min-height:52px;width:480px;max-width:100%;padding:12px 22px;font-size:16px;line-height:1.4}
.sport-card.custom-card{display:flex;align-items:center;justify-content:center;background:#edf5f1;color:#17604c;border:1px dashed #43836b;box-shadow:none}.sport-card.custom-card:before{display:none}.custom-card .sport-copy{max-width:100%;text-align:center;justify-items:center}.custom-card svg{width:36px;height:36px}.custom-card .sport-copy span{color:#365c4e}.custom-card .sport-copy strong{font-size:20px}
.field input:disabled,.field select:disabled{background:#edf0f3;color:#7a8693;cursor:not-allowed}
.share-actions{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.share-dialog{width:min(520px,calc(100% - 24px));max-height:calc(100dvh - 32px);overflow:auto}.share-dialog .dialog-head{display:flex;align-items:center;justify-content:space-between;gap:12px}.share-dialog .dialog-head h2{margin:0;font-size:20px}.share-dialog .icon-button{width:44px;height:44px;padding:0;flex:0 0 44px}.share-dialog input{font-size:14px}.share-dialog label{display:block;margin-top:12px}.share-dialog #shareStatus{font-size:14px;line-height:1.6;overflow-wrap:anywhere}.share-dialog .share-actions .social-icon{flex:0 0 44px;width:44px;height:44px;min-height:44px;padding:0}.share-dialog .social-icon svg{width:24px;height:24px}.share-dialog textarea{width:100%;box-sizing:border-box;resize:vertical;margin-bottom:12px;font-size:14px}.share-dialog .share-actions{flex-wrap:nowrap;gap:8px}.share-dialog #shareLine{color:#008b3e}.button svg{flex-shrink:0}.share-button{gap:7px}.application-action-buttons{display:flex;gap:8px;flex-wrap:wrap;margin-left:auto}
@media(max-width:620px){.application-action-buttons{margin:0;display:grid;grid-template-columns:auto minmax(0,1fr)}.custom-card .sport-copy strong{font-size:16px}}
.event-publish{display:flex;justify-content:center;margin:16px 0 0}
.event-publish+.event-results{margin-top:16px}
.event-breadcrumb{display:flex;align-items:center;gap:12px;margin:0 0 12px;min-width:0}
.home-link{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;padding:8px 12px;border:1px solid var(--line);border-radius:6px;background:#fff;color:#243c50;font-size:15px;font-weight:800;text-decoration:none;flex-shrink:0}
.home-link:hover{background:#edf4f7}.home-link svg{width:20px;height:20px;flex-shrink:0}
.home-link:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.breadcrumb-current{font-size:14px;color:#526577;overflow-wrap:anywhere;min-width:0}
.event-results .filter-grid{align-items:end}.event-filter{display:grid;gap:6px;min-width:0;font-size:13px;font-weight:700;color:#405164}
.event-filter input,.event-filter select{width:100%;min-width:0;max-width:100%;min-height:46px;font-size:16px;font-weight:400;color:var(--ink)}
.form-shell,.form-shell .panel,.form-section,.field-grid,.field-grid>*{min-width:0;max-width:100%}
.form-shell .panel,.field input,.field select,.field textarea{scroll-margin-top:100px}
.field input,.field select,.field textarea{max-width:100%;font-size:16px;min-height:46px}
input[type=date],input[type=datetime-local]{display:block;min-width:0;max-width:100%;box-sizing:border-box}
input::-webkit-date-and-time-value{min-width:0;text-align:left}
.form-actions .card-actions{margin:0 0 0 auto;min-width:0}.form-actions .button{min-height:48px}
@media(max-width:820px){.field-grid{grid-template-columns:minmax(0,1fr)}}
@media(max-width:620px){
 .event-publish .publish-cta{width:100%;min-width:0;min-height:48px}
 .site-nav .main-nav a.account,.site-nav .account-logout button{min-height:44px}
 .event-results .filter-grid{grid-template-columns:minmax(0,1fr);gap:12px;padding:14px}
 .event-results .panel-head{align-items:flex-start}.event-results .panel-head>div{min-width:0}
 .event-results-intro h1{max-width:100%;font-size:23px}.event-breadcrumb{gap:8px}
 .stepper span{min-width:0;padding:10px 4px;font-size:12px;line-height:1.5}
 .form-actions{display:grid;grid-template-columns:minmax(0,1fr);gap:8px}
 .form-actions #backStep{justify-self:start;min-width:80px;grid-row:2}
 .form-actions .card-actions{width:100%;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
 .form-actions .button{min-width:0;padding:10px 8px;font-size:15px}
 #events,#dbList,.form-shell .panel,.field input,.field select,.field textarea{scroll-margin-top:80px}
}
.container,.site-nav{width:min(1400px,calc(100% - 64px));max-width:1400px;margin-inline:auto;padding-inline:0}
.sport-grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
.sport-card{display:flex;min-width:0;min-height:172px}
.sport-copy{display:flex;flex:1;flex-direction:column;align-items:flex-start;max-width:100%;min-width:0;gap:6px;padding:16px}
.sport-copy strong{font-size:22px;line-height:1.3;overflow-wrap:anywhere}
.sport-copy em{position:static;max-width:100%;margin-top:auto;white-space:normal}
.event-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;padding:16px}
.event-card,.event-card>*{min-width:0;overflow-wrap:anywhere}
.card-footer{flex-wrap:wrap}.card-footer .button{flex-shrink:0}
@media(min-width:1280px){.event-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(min-width:1600px){.sport-grid{grid-template-columns:repeat(5,minmax(0,1fr))}}
@media(max-width:1023px){.sport-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.sport-copy strong{font-size:20px}}
@media(max-width:899px){.container,.site-nav{width:calc(100% - 32px)}.event-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:699px){.sport-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.sport-card{min-height:144px}.sport-copy{padding:12px}.sport-copy strong{font-size:18px}}
@media(max-width:620px){.container,.site-nav{width:calc(100% - 24px)}.container{padding-block:16px 40px}.event-grid{grid-template-columns:minmax(0,1fr);padding:12px;gap:12px}}
@media(max-width:460px){.sport-grid{gap:8px}.sport-card{min-height:120px}.sport-copy{padding:10px}.sport-copy strong{font-size:17px}.sport-copy em{margin-top:auto;padding:0}}
"""


# Lucide house icon, ISC license (see docs/licenses/lucide.txt).
HOME_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>'


def event_home_navigation(current, href="/"):
    return (f'<nav class="event-breadcrumb" aria-label="現在位置"><a class="home-link" '
            f'href="{html.escape(href, quote=True)}">{HOME_ICON}ホーム</a>'
            f'<span aria-hidden="true">/</span><span class="breadcrumb-current" aria-current="page">{html.escape(current)}</span></nav>')


# Additional Lucide icons (ISC; see docs/licenses/lucide.txt).
ICON_START = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
PLUS_ICON = ICON_START + '<path d="M5 12h14"/><path d="M12 5v14"/></svg>'
SHARE_ICON = ICON_START + '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/></svg>'
LINK_ICON = ICON_START + '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>'
CLOSE_ICON = ICON_START + '<path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>'


# Simple Icons v15.0.0, CC0; see docs/licenses/simple-icons.txt.
SOCIAL_ICONS = {
    "instagram": "<svg aria-hidden=\"true\" focusable=\"false\" width=\"24\" height=\"24\" fill=\"currentColor\" viewBox=\"0 0 24 24\" xmlns=\"http://www.w3.org/2000/svg\"><title>Instagram</title><path d=\"M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077\"/></svg>",
    "x": "<svg aria-hidden=\"true\" focusable=\"false\" width=\"24\" height=\"24\" fill=\"currentColor\" viewBox=\"0 0 24 24\" xmlns=\"http://www.w3.org/2000/svg\"><title>X</title><path d=\"M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z\"/></svg>",
    "line": "<svg aria-hidden=\"true\" focusable=\"false\" width=\"24\" height=\"24\" fill=\"currentColor\" viewBox=\"0 0 24 24\" xmlns=\"http://www.w3.org/2000/svg\"><title>LINE</title><path d=\"M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63h2.386c.346 0 .627.285.627.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63.346 0 .628.285.628.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314\"/></svg>",
    "tiktok": "<svg aria-hidden=\"true\" focusable=\"false\" width=\"24\" height=\"24\" fill=\"currentColor\" viewBox=\"0 0 24 24\" xmlns=\"http://www.w3.org/2000/svg\"><title>TikTok</title><path d=\"M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z\"/></svg>",
}


def event_share_button():
    return f'<button class="button share-button" type="button" data-share-event aria-haspopup="dialog">{SHARE_ICON}共有</button>'


def event_share_dialog(event, auto_after_publish=False):
    # Only public metadata is shared. Never include application answers or targets.
    data = {"path": "/events/" + quote(str(event["event_id"])),
            "title": event.get("title") or "大会・イベント", "auto": auto_after_publish}
    fields = [("開催日時", event.get("starts_at") or "未定"),
              ("会場", " / ".join(filter(None, [event.get("prefecture"), event.get("location")])) or "未定"),
              ("定員", str(event["capacity"]) + (event.get("capacity_unit") or "人") if event.get("capacity") else "定員なし"),
              ("締切", event.get("application_deadline") or "開催日時まで"),
              ("内容", event.get("description") or "詳細ページをご確認ください"),
              ("参加条件", event.get("eligibility") or "特に設定されていません")]
    data["text"] = data["title"] + " | Circle Match\n" + "\n".join(label + ": " + str(value) for label, value in fields)
    # X counts most Japanese characters twice. Keep a conservative summary plus URL.
    def short(value, budget):
        result, weight = "", 0
        for char in str(value).replace("\n", " "):
            weight += 1 if ord(char) < 128 else 2
            if weight > budget - 3:
                return result + "..."
            result += char
        return result
    data["xText"] = short(data["title"], 26) + "\n" + "\n".join(label + ":" + short(value, budget) for (label, value), budget in zip(fields, (24, 18, 12, 24, 18, 18))) + "\nCircle Match"
    buttons = ''.join(f'<a id="{identity}" class="button social-icon" aria-label="{label}で共有" title="{label}で共有" target="_blank" rel="noopener noreferrer" {extra}>{SOCIAL_ICONS[name]}</a>'
                      for identity, name, label, extra in (
                          ("shareLine", "line", "LINE", ""), ("shareX", "x", "X", ""),
                          ("shareInstagram", "instagram", "Instagram", 'href="https://www.instagram.com/" data-copy-share="Instagram"'),
                          ("shareTikTok", "tiktok", "TikTok", 'href="https://www.tiktok.com/" data-copy-share="TikTok"')))
    markup = f'''<dialog id="eventShareDialog" class="ux-dialog share-dialog" aria-labelledby="shareHeading"><div class="dialog-head"><h2 id="shareHeading">募集を共有する</h2><button id="closeShare" type="button" class="button icon-button" aria-label="閉じる" title="閉じる">{CLOSE_ICON}</button></div><p>{html.escape(data["title"])}</p><div class="share-actions">{buttons}<button type="button" class="button social-icon" id="shareMore" aria-label="その他の共有先" title="その他の共有先">{PLUS_ICON}</button></div><label for="shareText">共有する募集文</label><textarea id="shareText" rows="6" readonly></textarea><button type="button" class="button share-button" id="copyShareLink">{LINK_ICON}募集文・リンクをコピー</button><label for="shareUrl">募集の公開URL</label><input id="shareUrl" type="url" readonly><p id="shareStatus" role="status" aria-live="polite"></p></dialog>'''
    return markup, EVENT_SHARE_SCRIPT.replace("__SHARE_EVENT__", script_json(data))


EVENT_SHARE_SCRIPT = r'''<script>
(()=>{
const data=__SHARE_EVENT__,dialog=document.getElementById('eventShareDialog'),status=document.getElementById('shareStatus'),input=document.getElementById('shareUrl');
const url=new URL(data.path,location.origin).href,text=data.text;let opener=null;
input.value=url;
const shareText=document.getElementById('shareText');shareText.value=text+'\n'+url;
document.getElementById('shareLine').href='https://social-plugins.line.me/lineit/share?'+new URLSearchParams({url,text});
document.getElementById('shareX').href='https://twitter.com/intent/tweet?'+new URLSearchParams({url,text:data.xText});
function open(source){opener=source;status.textContent='';document.getElementById('shareHeading').textContent='募集を共有する';dialog.showModal()}
document.querySelectorAll('[data-share-event]').forEach(button=>button.addEventListener('click',()=>open(button)));
document.getElementById('closeShare').onclick=()=>dialog.close();
dialog.addEventListener('close',()=>opener?.focus());
async function copy(destination=''){
 try{await navigator.clipboard.writeText(shareText.value);status.textContent=destination?`募集文をコピーしました。${destination}の投稿に貼り付けてください。自動投稿はされません。`:'募集文とリンクをコピーしました。'}
 catch(_){shareText.focus();shareText.select();status.textContent='コピーできませんでした。募集文を選択してコピーしてください。'}
}
document.getElementById('copyShareLink').onclick=()=>copy();
document.querySelectorAll('[data-copy-share]').forEach(link=>link.addEventListener('click',()=>copy(link.dataset.copyShare)));
document.getElementById('shareMore').onclick=async()=>{
 if(!navigator.share){await copy();status.textContent+=' このブラウザは共有先の選択に対応していません。';return}
 status.textContent='共有先を選択してください。';
 try{await navigator.share({title:data.title,text,url})}
 catch(error){if(error.name!=='AbortError')await copy()}
};
const query=new URL(location.href);
if(data.auto&&query.searchParams.get('published')==='1'){
 open(document.querySelector('[data-share-event]'));document.getElementById('shareHeading').textContent='掲載しました。募集を共有しましょう';
 query.searchParams.delete('published');history.replaceState(history.state,'',query.pathname+query.search+query.hash);
}
})();
</script>'''


def selected_home_query(params, tab, *, path="/", **updates):
    values = {}
    for key in ("sport", "region", "prefecture", "date_from", "date_to", "event_type", "participation", "audience", "q"):
        value = (params.get(key, [""])[0] or "").strip()
        if value:
            values[key] = value
    values.update({key: value for key, value in updates.items() if value})
    values["tab"] = tab
    return path + "?" + urlencode(values)


def event_sport_cards(params, tab, audience="university"):
    cards = []
    for name, label, _code, _color, image in POPULAR_SPORTS:
        href = selected_home_query(params, tab, path="/events" if tab == "events" else "/", audience=audience, sport=name)
        cards.append(
            f'<a class="sport-card" href="{html.escape(href, quote=True)}"><img src="/assets/sports/{html.escape(image)}?v=20260713v1" alt="{html.escape(name)}"><span class="sport-copy"><strong>{html.escape(name)}</strong><span>{html.escape(label)}</span><em>{"募集を見る" if tab == "events" else "団体を探す"}</em></span></a>'
        )
    if tab == "events":
        context = {key: params[key][0] for key in ("region", "prefecture") if params.get(key) and params[key][0]}
        href = "/events/new?" + urlencode(dict(context, custom="1"))
        cards.append(f'<a class="sport-card custom-card" href="{html.escape(href, quote=True)}"><span class="sport-copy">{PLUS_ICON}<strong>カスタム募集</strong><span>Custom event</span></span></a>')
    return "".join(cards)


def event_sport_options():
    """Public custom categories remain discoverable without exposing drafts."""
    names = [item[0] for item in POPULAR_SPORTS] + SPORTS
    with connect() as conn:
        names += [row[0] for row in conn.execute("select distinct sport_category from event_posts where status in ('published','closed') and sport_category != '' order by sport_category limit 200")]
    return list(dict.fromkeys(names))


def format_event_datetime(value):
    if not value:
        return "日時未定"
    return html.escape(str(value).replace("-", "/"))


def event_payment_label(value):
    return {"free": "-", "on_site": "現地払い", "bank_transfer": "口座振込"}.get(value, "主催者へ確認")


def event_fee_text(event):
    if event.get("fee_amount") is None:
        return "無料" if event.get("payment_method") == "free" else event_payment_label(event.get("payment_method")) + "（料金は主催者へ確認）"
    unit = event.get("fee_unit") or "1人"
    return f"{int(event['fee_amount']):,}円 / {unit}"


def render_event_cards(events):
    if not events:
        return '<div class="empty">条件に合う募集中の大会・イベントはありません。条件を変えるか、最初の募集を掲載してください。</div>'
    rendered = []
    for event in events:
        event_id = quote(str(event["event_id"]))
        status, available = event_availability(event)
        status_class = "open" if available else ("cancelled" if event.get("status") == "cancelled" else "closed")
        organizer = html.escape(event.get("linked_circle_name") or event.get("organizer_name") or "主催者")
        remaining = "定員なし"
        if event.get("capacity"):
            remaining = f"定員 {event.get('confirmed_count', 0)}/{event['capacity']}{html.escape(event.get('capacity_unit') or '')}"
        rendered.append(
            f'<article class="event-card"><div><span class="badge {status_class}">{html.escape(status)}</span> <span class="badge">{html.escape(event.get("event_type") or "")}</span></div>'
            f'<h3><a href="/events/{event_id}">{html.escape(event.get("title") or "")}</a></h3>'
            f'<p>{html.escape(event.get("sport_category") or "")} / {organizer}</p>'
            f'<div class="card-meta"><span>{format_event_datetime(event.get("starts_at"))}</span><span>{html.escape(event.get("prefecture") or "地域未定")} / {html.escape(event.get("location") or "会場未定")}</span><span>{html.escape(event_fee_text(event))} / {html.escape(event_participation_label(event.get("participation_type") or ""))}</span><span>{remaining}</span></div>'
            f'<div class="card-footer"><span class="badge">{html.escape(event_acceptance_label(event.get("acceptance_mode") or ""))}</span><a class="button" href="/events/{event_id}">詳細・申込</a></div></article>'
        )
    return "".join(rendered)


def render_db_rows(circles):
    if not circles:
        return '<div class="empty">条件に合う団体はありません。検索条件を変えてください。</div>'
    output = []
    for circle in circles:
        link = f'<a href="{html.escape(circle["profile_url"], quote=True)}">紹介ページ</a>' if circle.get("profile_url") else (f'<a href="{html.escape(circle["source_url"], quote=True)}" target="_blank" rel="noopener noreferrer">出典を確認（外部）</a>' if safe_public_source(circle.get("source_url")) else '<a href="/contact">情報を問い合わせる</a>')
        output.append(
            '<div class="circle-row">'
            f'<div><strong>{html.escape(circle.get("university_name") or "活動地域")}</strong><small>{html.escape(circle.get("prefecture") or "")}{(" / " + html.escape(circle.get("city") or "")) if circle.get("city") else ""}</small></div>'
            f'<div><strong>{html.escape(circle.get("circle_name") or "")}</strong><small>{html.escape(circle.get("organization_type") or "不明")}</small></div>'
            f'<div>{html.escape(circle.get("sport_category") or "その他")}</div><div>{link}</div></div>'
        )
    return "".join(output)


def safe_public_source(value):
    try:
        parsed = urlparse(str(value or ""))
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username
    except ValueError:
        return False


def render_db_pager(params, page, total):
    values = {key: value[0] for key, value in params.items() if value and key in {"tab", "audience", "q", "sport", "region", "prefecture", "sort"}}
    values["tab"] = "db"
    links = []
    if page > 1:
        links.append('<a class="button" href="/?' + html.escape(urlencode(dict(values, page=page-1)), quote=True) + '#dbList">前へ</a>')
    links.append(f'<span role="status">{min((page-1)*24+1, total)}〜{min(page*24, total)}件 / 全{total}件</span>')
    if page * 24 < total:
        links.append('<a class="button" href="/?' + html.escape(urlencode(dict(values, page=page+1)), quote=True) + '#dbList">次へ</a>')
    return ''.join(links)


def render_public_html(params=None, event_listing=False):
    """Render the event-first home while keeping all circle data routes intact."""
    params = params or {}
    tab = (params.get("tab", ["events"])[0] or "events").strip()
    if tab not in {"events", "db"}:
        tab = "events"
    audience = audience_scope(params, "university")
    sport = (params.get("sport", [""])[0] or "").strip()
    region = (params.get("region", [""])[0] or "").strip()
    event_listing = tab == "events" and (event_listing or bool(sport))
    event_url = selected_home_query(params, "events", path="/events" if sport or event_listing else "/")
    db_url = selected_home_query(params, "db", audience=audience)
    post_context = {key: params[key][0] for key in ("sport", "region", "prefecture") if params.get(key) and params[key][0]}
    post_url = "/events/new" + ("?" + urlencode(post_context) if post_context else "")
    tabs = f'<div class="tabs"><a class="{"active" if tab == "events" else ""}" href="{html.escape(event_url, quote=True)}">大会・イベント</a><a class="{"active" if tab == "db" else ""}" href="{html.escape(db_url, quote=True)}">サークルDB</a></div>'
    shared_head = '<section class="intro"><div><p class="eyebrow">SPORTS EVENT DIRECTORY</p><h1>スポーツの大会・イベントを、見つけて参加する。</h1><p>大会、交流イベント、練習試合、合同練習を競技・地域から探せます。サークルDBは、主催団体や活動仲間を調べるための情報基盤として残しています。</p></div></section>'
    if tab == "events":
        try:
            initial_events = search_events(params, limit=30)
            event_markup = render_event_cards(initial_events)
            initial_error = ""
        except Exception as exc:
            log(f"event home SSR failed: {type(exc).__name__}: {exc}")
            initial_events = []
            event_markup = '<div class="error-box">募集データを取得できませんでした。時間をおいて再度お試しください。</div>'
            initial_error = "イベントデータを取得できませんでした"
        filter_options = ''.join(f'<option value="{html.escape(value)}"{" selected" if sport == value else ""}>{html.escape(value)}</option>' for value in event_sport_options())
        region_options_html = ''.join(f'<option value="{key}"{" selected" if region == key else ""}>{html.escape(data["label"])}</option>' for key, data in REGION_GROUPS.items())
        type_options = ''.join(f'<option value="{html.escape(value)}">{html.escape(value)}</option>' for value in EVENT_TYPES)
        sport_picker = f'<section class="section panel"><div class="panel-head"><h2>スポーツから探す</h2><a class="button" href="#events">募集一覧へ</a></div><div class="sport-grid">{event_sport_cards(params, "events")}</div></section>'
        if event_listing:
            image_name = next((item[4] for item in POPULAR_SPORTS if item[0] == sport), "other.png")
            listing_title = f'{html.escape(sport)}<span>大会・イベント</span>' if sport else '大会・イベント一覧'
            heading = f'<section class="event-results-intro"><img src="/assets/sports/{image_name}" alt=""><h1>{listing_title}</h1></section>'
            introduction = event_home_navigation(sport or "大会・イベント一覧") + tabs + heading
            if not initial_events and not initial_error:
                event_markup = f'<div class="empty">現在、{html.escape(sport + "の" if sport else "")}募集中の大会・イベントはありません。</div>'
        else:
            introduction = shared_head + tabs + sport_picker
        result_count = "取得できませんでした" if initial_error else f'{len(initial_events)}件を表示'
        body = introduction + f'''<div class="event-publish"><a class="button primary publish-cta" href="{html.escape(post_url, quote=True)}">募集を掲載する</a></div><section class="section panel event-results" id="events"><div class="panel-head"><div><h2>募集中の大会・イベント</h2><p id="eventResultCount" role="status">{result_count}</p></div></div>
<form id="eventFilters" class="filter-grid"><label class="event-filter">競技<select name="sport" aria-label="競技"><option value="">全競技</option>{filter_options}</select></label><label class="event-filter">地域<select name="region" aria-label="地域"><option value="">全地域</option>{region_options_html}</select></label><label class="event-filter">募集種別<select name="event_type" aria-label="募集種別"><option value="">全募集種別</option>{type_options}</select></label><label class="event-filter">開催日以降<input name="date_from" type="date" aria-label="開催日以降"></label><label class="event-filter">参加単位<select name="participation" aria-label="参加単位"><option value="">個人・チームすべて</option><option value="individual">個人参加</option><option value="team">チーム参加</option></select></label></form>
<div id="eventList" class="event-grid">{event_markup}</div></section><section class="about"><h2>Circle Matchとは</h2><p>Circle Matchは、大学・社会人を問わずスポーツ活動の情報を集め、参加できる大会・イベントと、活動団体の情報を見つけやすくするサービスです。団体DBへの掲載と、主催者としての募集管理の権限は分けて扱います。</p></section>'''
        script = EVENT_HOME_SCRIPT.replace("__INITIAL_EVENTS__", script_json(initial_events)).replace("__INITIAL_ERROR__", script_json(initial_error)).replace("__TAB__", script_json(tab)).replace("__AUDIENCE__", script_json(audience))
    else:
        shared_head = '<section class="intro"><div><h1>活動するサークルを探す。</h1><p>大学・社会人の団体情報を、競技や地域から調べられます。出典掲載と、団体の代表権限の確認は別です。</p><a class="button" href="#dbList">団体一覧へ</a></div></section>'
        try:
            scoped = dict(params)
            scoped["audience"] = [audience]
            try:
                db_page = max(1, min(int(params.get("page", ["1"])[0]), 10000))
            except (ValueError, TypeError):
                db_page = 1
            initial_circles = search_circles(scoped, limit=24, offset=(db_page - 1) * 24)
            db_stats = circle_query_stats(scoped)
            db_markup = render_db_rows(initial_circles)
            db_error = ""
        except Exception as exc:
            log(f"db home SSR failed: {type(exc).__name__}: {exc}")
            initial_circles, db_stats = [], {"circles": "取得失敗", "universities": "取得失敗", "prefectures": "取得失敗"}
            db_markup = '<div class="error-box">団体データを取得できませんでした。時間をおいて再度お試しください。</div>'
            db_error = "団体データを取得できませんでした"
        audience_toggle = f'<div class="db-toggle"><a class="{"active" if audience == "university" else ""}" href="{html.escape(selected_home_query(params, "db", audience="university"), quote=True)}">大学</a><a class="{"active" if audience == "social" else ""}" href="{html.escape(selected_home_query(params, "db", audience="social"), quote=True)}">社会人</a></div>'
        filter_options = ''.join(f'<option value="{html.escape(value)}"{" selected" if sport == value else ""}>{html.escape(value)}</option>' for value in sport_options(audience))
        body = shared_head + tabs + f'''<section class="section panel"><div class="panel-head"><div><h2>サークルDB</h2><p>大学と社会人を切り替え、競技・地域から団体情報を確認できます。</p></div>{audience_toggle}</div><div class="db-summary"><div class="metric"><span>対象地域</span><strong id="dbPrefectures">{db_stats.get("prefectures", 0)}</strong></div><div class="metric"><span>{"対象大学" if audience == "university" else "掲載団体"}</span><strong id="dbUniversities">{db_stats.get("universities", 0)}</strong></div><div class="metric"><span>検索結果</span><strong id="dbCircles">{db_stats.get("circles", 0)}</strong></div></div><div class="sport-grid">{event_sport_cards(params, "db", audience)}</div><form id="dbFilters" class="filter-grid"><input name="q" value="{html.escape((params.get("q", [""])[0] or ""), quote=True)}" placeholder="団体名・大学名・地域で検索"><select name="sport"><option value="">全競技</option>{filter_options}</select><select name="region"><option value="">全地域</option>{''.join(f'<option value="{key}"{" selected" if region == key else ""}>{html.escape(data["label"])}</option>' for key, data in REGION_GROUPS.items())}</select><select name="prefecture"><option value="">全都道府県</option>{''.join(f'<option value="{html.escape(p)}">{html.escape(p)}</option>' for p in PREFECTURES)}</select><a class="button" href="{'/circles' if audience == 'university' else '/social/circles'}">詳細検索</a></form><div id="dbList" class="circle-list">{db_markup}</div></section><section class="about"><h2>Circle Matchとは</h2><p>団体データは公開情報・掲載申請情報を基に整理しています。DBに掲載されていることと、募集を主催する権限は別です。公式な団体名で主催する場合は、確認済み代表者だけが紐付けできます。</p></section>'''
        if sport:
            body = event_home_navigation(sport, "/?" + urlencode({"tab": "db", "audience": audience})) + body
        pager = render_db_pager(params, db_page if not db_error else 1, db_stats["circles"] if not db_error else 0)
        body = body.replace('<div id="dbList"', '<div id="dbPagerTop" class="db-pager">' + pager + '</div><div id="dbList"').replace('</section><section class="about">', '<div id="dbPager" class="db-pager">' + pager + '</div></section><section class="about">')
        script = EVENT_HOME_SCRIPT.replace("__INITIAL_EVENTS__", "[]").replace("__INITIAL_ERROR__", script_json(db_error)).replace("__TAB__", script_json(tab)).replace("__AUDIENCE__", script_json(audience)).replace("__INITIAL_CIRCLES__", script_json(initial_circles)).replace("__INITIAL_DB_STATS__", script_json(db_stats))
    page_title = f"{sport}の大会・イベント" if tab == "events" and sport else "大会・イベント"
    page = event_shell(page_title, body, script)
    return (page.replace("__EVENT_TAB__", "active" if tab == "events" else "").replace("__DB_TAB__", "active" if tab == "db" else "").replace("__EVENT_TAB_URL__", html.escape(event_url, quote=True)).replace("__DB_TAB_URL__", html.escape(db_url, quote=True)).replace("__POST_URL__", html.escape(post_url, quote=True))).encode("utf-8")


EVENT_HOME_SCRIPT = r"""
<script>
  const pageTab=__TAB__, pageAudience=__AUDIENCE__, initialEvents=__INITIAL_EVENTS__, initialError=__INITIAL_ERROR__;
  const initialCircles=typeof __INITIAL_CIRCLES__==='undefined'?[]:__INITIAL_CIRCLES__;
  const initialDbStats=typeof __INITIAL_DB_STATS__==='undefined'?{}:__INITIAL_DB_STATS__;
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const qs=()=>new URLSearchParams(location.search);
  const formatDate=v=>v?esc(String(v).replaceAll('-','/')):'日時未定';
  const fee=e=>e.fee_amount===null||e.fee_amount===undefined?(e.payment_method==='free'?'無料':`${e.payment_method==='bank_transfer'?'口座振込':'現地払い'}（料金は主催者へ確認）`):`${Number(e.fee_amount).toLocaleString()}円 / ${esc(e.fee_unit||'1人')}`;
  const status=e=>[e.availability_label||'受付終了',e.can_apply?'open':(e.status==='cancelled'?'cancelled':'closed')];
  function eventCard(e){const st=status(e), org=e.linked_circle_name||e.organizer_name||'主催者'; const cap=e.capacity?`定員 ${e.confirmed_count||0}/${e.capacity}${esc(e.capacity_unit||'')}`:'定員なし'; return `<article class="event-card"><div><span class="badge ${st[1]}">${esc(st[0])}</span> <span class="badge">${esc(e.event_type||'')}</span></div><h3><a href="/events/${encodeURIComponent(e.event_id)}">${esc(e.title||'')}</a></h3><p>${esc(e.sport_category||'')} / ${esc(org)}</p><div class="card-meta"><span>${formatDate(e.starts_at)}</span><span>${esc(e.prefecture||'地域未定')} / ${esc(e.location||'会場未定')}</span><span>${fee(e)} / ${esc(({individual:'個人参加',team:'チーム参加',both:'個人・チーム参加'})[e.participation_type]||'')}</span><span>${cap}</span></div><div class="card-footer"><span class="badge">${esc(({first_come:'先着順',approval:'主催者承認制'})[e.acceptance_mode]||'')}</span><a class="button" href="/events/${encodeURIComponent(e.event_id)}">詳細・申込</a></div></article>`}
  function circleRow(c){let source=false;try{source=['https:','http:'].includes(new URL(c.source_url).protocol)}catch(_){}const profile=c.profile_url?`<a href="${esc(c.profile_url)}">紹介ページ</a>`:(source?`<a href="${esc(c.source_url)}" target="_blank" rel="noopener noreferrer">出典を確認（外部）</a>`:'<a href="/contact">情報を問い合わせる</a>');return `<div class="circle-row"><div><strong>${esc(c.university_name||'活動地域')}</strong><small>${esc(c.prefecture||'')}${c.city?' / '+esc(c.city):''}</small></div><div><strong>${esc(c.circle_name||'')}</strong><small>${esc(c.organization_type||'不明')}</small></div><div>${esc(c.sport_category||'その他')}</div><div>${profile}</div></div>`}
  async function getJson(url){const r=await fetch(url);const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(data.error||'データを取得できませんでした');return data}
  function restoreFilters(form){const current=qs();for(const input of form.elements){if(input.name)input.value=current.get(input.name)||''}}
  function syncLinks(){
    const current=qs(),keys=['sport','region','prefecture','date_from','date_to','event_type','participation','q'];
    document.querySelectorAll('a[href]').forEach(link=>{
      const raw=link.getAttribute('href');
      if(!raw.startsWith('/')||link.classList.contains('home-link')||link.classList.contains('cm-home'))return;
      const target=new URL(raw,location.origin);
      if(['/','/events'].includes(target.pathname)&&target.searchParams.has('tab')){
        for(const key of keys){if(key==='sport'&&link.classList.contains('sport-card'))continue;const value=current.get(key);if(value)target.searchParams.set(key,value);else target.searchParams.delete(key)}
      }else if(target.pathname==='/events/new'){
        for(const key of ['sport','region','prefecture']){if(key==='sport'&&target.searchParams.get('custom')==='1'){target.searchParams.delete(key);continue}const value=current.get(key);if(value)target.searchParams.set(key,value);else target.searchParams.delete(key)}
      }else if(['/circles','/social/circles'].includes(target.pathname)){
        for(const key of ['sport','region','prefecture','q']){const value=current.get(key);if(value)target.searchParams.set(key,value);else target.searchParams.delete(key)}
      }else return;
      link.href=target.pathname+target.search+target.hash;
    });
  }
  function updateUrl(form,resetPage=true){const next=qs();for(const [key,value] of new FormData(form).entries()){if(value)next.set(key,value);else next.delete(key)}next.set('tab',pageTab);if(pageTab==='db'){next.set('audience',pageAudience);if(resetPage)next.delete('page')}const target=location.pathname+'?'+next.toString();if(target!==location.pathname+location.search)history.pushState(null,'',target);syncLinks()}
  async function bootEvents(){
    const form=document.getElementById('eventFilters'),list=document.getElementById('eventList');if(!form)return;
    restoreFilters(form);syncLinks();let request=0;
    const count=document.getElementById('eventResultCount');
    function render(items){const sport=form.elements.sport.value;list.innerHTML=items.length?items.map(eventCard).join(''):`<div class="empty">現在、${sport?esc(sport)+'の':''}募集中の大会・イベントはありません。</div>`;count.textContent=items.length+'件を表示'}
    if(initialError)list.innerHTML=`<div class="error-box">${esc(initialError)}</div>`;else render(initialEvents);
    const sync=async()=>{updateUrl(form);const latest=++request;count.textContent='検索中';list.innerHTML='<div class="empty">募集を検索しています。</div>';try{const data=await getJson('/api/events?'+qs().toString());if(latest===request)render(data)}catch(e){if(latest===request){count.textContent='取得できませんでした';list.innerHTML=`<div class="error-box">${esc(e.message)}</div>`}}};
    form.addEventListener('submit',e=>{e.preventDefault();sync()});form.addEventListener('change',e=>{if(e.target.name==='sport'){updateUrl(form);location.assign('/events?'+qs().toString());return}sync()});
    window.addEventListener('popstate',()=>{restoreFilters(form);sync()});
  }
  async function bootDb(){
    const form=document.getElementById('dbFilters'),list=document.getElementById('dbList');if(!form)return;
    restoreFilters(form);syncLinks();let request=0,timer;
    function render(rows){list.innerHTML=rows.length?rows.map(circleRow).join(''):'<div class="empty">条件に合う団体はありません。検索条件を変えてください。</div>'}
    if(initialError)list.innerHTML=`<div class="error-box">${esc(initialError)}</div>`;else render(initialCircles);
    function pager(total){const page=Math.max(1,Number(qs().get('page'))||1),link=(p,label)=>{const query=qs();query.set('page',p);return `<a class="button" href="/?${esc(query.toString())}#dbList">${label}</a>`};const markup=(page>1?link(page-1,'前へ'):'')+`<span role="status">${Math.min((page-1)*24+1,total)}〜${Math.min(page*24,total)}件 / 全${total}件</span>`+(page*24<total?link(page+1,'次へ'):'');for(const id of ['dbPager','dbPagerTop'])document.getElementById(id).innerHTML=markup}
    const sync=async(resetPage=true)=>{clearTimeout(timer);updateUrl(form,resetPage!==false);const latest=++request;try{const query=new URLSearchParams(new FormData(form));query.set('audience',pageAudience);query.set('offset',String((Math.max(1,Number(qs().get('page'))||1)-1)*24));const [data,stats]=await Promise.all([getJson('/api/circles?limit=24&'+query.toString()),getJson('/api/circle-stats?'+query.toString())]);if(latest!==request)return;render(data);pager(stats.circles);for(const [key,id] of Object.entries({prefectures:'dbPrefectures',universities:'dbUniversities',circles:'dbCircles'})){const node=document.getElementById(id);if(node)node.textContent=stats[key]??0}}catch(e){if(latest===request){list.innerHTML=`<div class="error-box">${esc(e.message)}</div>`;for(const id of ['dbPrefectures','dbUniversities','dbCircles'])document.getElementById(id).textContent='取得失敗'}}};
    form.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(sync,220)});form.addEventListener('change',sync);form.addEventListener('submit',e=>{e.preventDefault();sync()});
    window.addEventListener('popstate',()=>{restoreFilters(form);sync(false)});
  }
  if(pageTab==='events')bootEvents();else bootDb();
</script>
"""


def event_page(title, body, script="", tab="events", post_url="/events/new"):
    return (
        event_shell(title, body, script)
        .replace("__EVENT_TAB__", "active" if tab == "events" else "")
        .replace("__DB_TAB__", "active" if tab == "db" else "")
        .replace("__EVENT_TAB_URL__", "/?tab=events")
        .replace("__DB_TAB_URL__", "/?tab=db&audience=university")
        .replace("__POST_URL__", html.escape(post_url, quote=True))
    )


def render_event_detail_html(event_id, user=None):
    event = get_event(event_id)
    if not event:
        return None
    state, can_apply = event_availability(event)
    state_class = "open" if can_apply else ("cancelled" if event.get("status") == "cancelled" else "closed")
    apply_label = "参加を申請する" if event.get("acceptance_mode") == "approval" else "参加を申し込む"
    application = user_event_application(event_id, user)
    if application and application["status"] != "cancelled":
        can_apply = False
    is_host = False
    if (user or {}).get("authenticated"):
        with connect() as conn:
            is_host = bool(conn.execute("select 1 from event_posts where event_id=? and organizer_user_id=?", (event_id, user["user_id"])).fetchone())
        if is_host:
            can_apply = False
    application_url = f"/events/{quote(str(event_id))}/apply"
    if not (user or {}).get("authenticated"):
        application_url = "/signin?" + urlencode({"return_to": application_url})
        apply_label = "ログインして" + apply_label
    organizer = html.escape(event.get("organizer_name") or "主催者")
    if event.get("linked_circle_profile_slug"):
        organizer = f'<a href="/circles/{quote(str(event["linked_circle_profile_slug"]))}">{html.escape(event.get("linked_circle_name") or event.get("organizer_name") or "主催団体")}</a>'
    fee = html.escape(event_fee_text(event))
    payment_html = ""
    if event.get("fee_amount") != 0:
        payment_html = '<div><span>支払方法</span><strong>' + html.escape(event_payment_label(event.get("payment_method"))) + '</strong>'
        if event.get("payment_method") == "bank_transfer":
            payment_html += '<small>参加確定後、主催者が振込先・期限を案内します。入金確認は主催者が行います。</small>'
        payment_html += '</div>'
    capacity = "定員なし" if not event.get("capacity") else f"{event.get('confirmed_count', 0)} / {event['capacity']}{html.escape(event.get('capacity_unit') or '')}"
    body = f'''<section class="intro"><div><p class="eyebrow">EVENT DETAIL</p><p><a href="/?tab=events&sport={quote(str(event.get("sport_category") or ""))}">大会・イベント一覧</a> / {html.escape(event.get("sport_category") or "")}</p></div></section>
<section class="detail"><article class="detail-main"><div><span class="badge {state_class}">{html.escape(state)}</span> <span class="badge">{html.escape(event.get("event_type") or "")}</span></div><h1>{html.escape(event.get("title") or "")}</h1><p>{html.escape(event.get("sport_category") or "")}</p><div class="detail-meta"><div><span>開催日時</span><strong>{format_event_datetime(event.get("starts_at"))}{(" 〜 " + format_event_datetime(event.get("ends_at"))) if event.get("ends_at") else ""}</strong></div><div><span>会場</span><strong>{html.escape(event.get("prefecture") or "地域未定")} / {html.escape(event.get("location") or "")}</strong></div><div><span>参加費</span><strong>{fee}</strong></div>{payment_html}<div><span>参加単位・定員</span><strong>{html.escape(event_participation_label(event.get("participation_type") or ""))} / {capacity}</strong></div><div><span>受付方式</span><strong>{html.escape(event_acceptance_label(event.get("acceptance_mode") or ""))}</strong></div><div><span>応募締切</span><strong>{format_event_datetime(event.get("application_deadline")) if event.get("application_deadline") else "開催日時まで"}</strong></div></div><h2>内容</h2><p>{html.escape(event.get("description") or "").replace(chr(10), '<br>')}</p><h2>参加条件</h2><p>{html.escape(event.get("eligibility") or "特に設定されていません").replace(chr(10), '<br>')}</p><h2>キャンセル・中止条件</h2><p>{html.escape(event.get("cancellation_policy") or "主催者へご確認ください").replace(chr(10), '<br>')}</p><h2>主催者</h2><p>{organizer}<br><small>連絡先メールアドレスは、参加申込後にアプリ内メッセージで扱います。</small></p></article><aside class="detail-side"><h2>参加受付</h2><p>{"この募集は現在受付中です。" if event_availability(event)[1] else "この募集は現在受け付けていません。"}</p>{f'<a class="button primary" href="{html.escape(application_url, quote=True)}">{apply_label}</a>' if can_apply else f'<span class="badge {state_class}">{html.escape(state)}</span>'}<p class="help">{"先着順は定員内で参加確定します。" if event.get("acceptance_mode") == "first_come" else "主催者承認制です。申請後、主催者の承認で参加確定します。"}</p></aside></section>{f'<a class="button primary mobile-apply" href="{application_url}">{apply_label}</a>' if can_apply else ""}'''
    if application:
        label = event_admission_label(event, application)
        body = body.replace('<h2>参加受付</h2>', '<h2>参加受付</h2><p>あなたの申込: ' + html.escape(label) + '</p><a class="button" href="/mypage?tab=attending">申込状況・主催者への連絡</a>')
    if is_host:
        owner_action = (f'<a class="button primary" href="/events/new?event_id={quote(event_id)}">募集内容を編集</a>'
                        if event["status"] != "cancelled" else '')
        body = body.replace('<h2>参加受付</h2>', '<h2>あなたの募集</h2>' + owner_action + '<p><a href="/mypage?tab=hosted">申込一覧・参加者への連絡</a></p>')
    if event.get("minimum_participants"):
        body = body.replace("先着順は定員内で参加確定します。", "先着順は定員内で受付確定となります。開催決定後に最終参加確認が必要です。")
        body = body.replace("主催者承認制です。申請後、主催者の承認で参加確定します。", "主催者承認後に受付確定となります。開催決定後に最終参加確認が必要です。")
        body += '<section class="application-recap"><h2>開催状況</h2><p>' + html.escape(event_formation_label(event)) + f' / 最低開催数：{event["minimum_participants"]}{html.escape(event["capacity_unit"])}</p></section>'
    contact_url = "/events/" + quote(event_id) + "/contact"
    if not (user or {}).get("authenticated"):
        contact_url = "/signin?" + urlencode({"return_to": contact_url})
    body += f'<div class="card-actions"><a class="button" href="{html.escape(contact_url, quote=True)}">{"質問・連絡を確認" if is_host else "主催者に質問する"}</a></div>'
    body = body.replace("連絡先メールアドレスは、参加申込後にアプリ内メッセージで扱います。", "申込前の質問も、非公開のアプリ内メッセージで受け付けます。")
    share_markup, share_script = event_share_dialog(event, auto_after_publish=is_host and event["status"] == "published")
    body += '<div class="card-actions">' + event_share_button() + '</div>' + share_markup
    return event_page(event.get("title") or "大会・イベント詳細", body, share_script)


def render_event_apply_html(event_id, user):
    event = get_event(event_id)
    if not event:
        return None
    if not user.get("authenticated"):
        return None
    application = user_event_application(event_id, user)
    state, available = event_availability(event)
    detail_url = '/events/' + quote(str(event_id))
    recap = event_application_recap(event)
    if application and application["status"] != "cancelled":
        label = event_admission_label(event, application)
        message = "主催者の承認をお待ちください。まだ参加は確定していません。" if application["status"] == "pending" and event["status"] != "cancelled" else "申込状況や主催者からの連絡はマイページで確認できます。"
        return event_page("申込状況", f'<section class="form-shell"><h1>{html.escape(label)}</h1><p>{message}</p>{recap}<div class="card-actions"><a class="button primary" href="/mypage?tab=attending">マイページへ</a><a class="button" href="{detail_url}">募集詳細へ</a></div></section>')
    with connect() as conn:
        is_host = conn.execute("select 1 from event_posts where event_id=? and organizer_user_id=?", (event_id, user["user_id"])).fetchone()
    if not available or is_host:
        reason = "主催する募集はマイページで管理できます。" if is_host else state + "のため現在申し込めません。"
        return event_page("参加受付", f'<section class="form-shell"><h1>参加受付</h1><p role="status">{html.escape(reason)}</p>{recap}<div class="card-actions"><a class="button" href="{detail_url}">募集詳細へ</a><a class="button" href="/mypage">マイページへ</a></div></section>')
    apply_label = "参加を申請する" if event.get("acceptance_mode") == "approval" else "参加を申し込む"
    modes = ["individual", "team"] if event.get("participation_type") == "both" else [event.get("participation_type")]
    radio = "".join(
        f'<label><input type="radio" name="participation_type" value="{mode}"{" checked" if index == 0 else ""}> {html.escape(event_participation_label(mode))}</label>'
        for index, mode in enumerate(modes)
    )
    with connect() as conn:
        saved = conn.execute("select team_name, representative_name, participant_count from event_applications where applicant_user_id=? and participation_type='team' order by updated_at desc limit 1", (user["user_id"],)).fetchone()
    default_name = html.escape(user.get("display_name") or "", quote=True)
    body = f'''<section class="form-shell"><h1>参加申込</h1>{recap}<section class="panel"><form id="applicationForm" data-event-id="{html.escape(event_id, quote=True)}"><div id="applicationInput" class="form-section active"><fieldset><legend>参加単位</legend><div id="participationChoices" class="card-actions">{radio}</div></fieldset><div id="individualFields" class="field"><label for="applicant_name">申込代表者名（必須）</label><input id="applicant_name" maxlength="80" value="{default_name}" autocomplete="name"></div><div id="teamFields" class="field-grid" hidden><div class="field full"><button class="button" id="reuseTeam" type="button" {"" if saved else "hidden"}>前回のチーム情報を使う</button></div><div class="field"><label for="team_name">チーム名（必須）</label><input id="team_name" maxlength="100"></div><div class="field"><label for="representative_name">代表者名（必須）</label><input id="representative_name" maxlength="80" value="{default_name}"></div></div><div class="field"><label for="participant_count">参加人数（本人・友達を含む合計）</label><input id="participant_count" type="number" min="1" max="100000" value="1" required><span class="help" id="groupHelp">友達の分もまとめて申し込めます。連絡・取り消しは申込代表者が行い、取り消しは申込全員分に適用されます。</span></div><div class="field full"><label for="applicant_message">主催者への連絡（任意）</label><textarea id="applicant_message" maxlength="1200"></textarea></div></div><section id="applicationReview" class="form-section" tabindex="-1"><h2>申込内容の確認</h2><dl id="reviewAnswers"></dl><p id="applicationFeeTotal"></p><p>{"主催者の承認後に参加確定します。" if event.get("acceptance_mode") == "approval" else "定員内であれば、この送信で参加が確定します。"}</p><p>上記の参加費・参加条件・キャンセル条件をご確認ください。</p></section><div class="form-actions"><a class="button" id="detailBack" href="{detail_url}">募集詳細へ戻る</a><button class="button" id="editApplication" type="button" hidden>入力に戻る</button><div class="application-action-buttons">{event_share_button()}<button class="button primary" type="submit" id="applicationSubmit">申込内容を確認する</button></div></div></form></section><div id="applicationStatus" class="error-box" role="alert" tabindex="-1" hidden></div></section>'''
    if event.get("minimum_participants"):
        body = body.replace("主催者の承認後に参加確定します。", "主催者の承認後に受付確定となります。開催決定後、別途最終参加確認が必要です。")
        body = body.replace("定員内であれば、この送信で参加が確定します。", "定員内であれば受付確定となります。開催決定後、別途最終参加確認が必要です。")
    script = APPLICATION_SCRIPT.replace("__SUBMIT_LABEL__", script_json(apply_label)).replace("__SAVED_TEAM__", script_json(dict(saved) if saved else None)).replace("__APPLICATION_FEE__", script_json({"amount": event.get("fee_amount"), "unit": event.get("fee_unit") or "1人"}))
    share_markup, share_script = event_share_dialog(event)
    return event_page("参加申込", body + share_markup, script + share_script)


def event_application_recap(event):
    fields = [("開催日時", format_event_datetime(event.get("starts_at"))), ("会場", (event.get("prefecture") or "") + " / " + (event.get("location") or "")), ("参加費", event_fee_text(event)), ("支払方法", event_payment_label(event.get("payment_method"))), ("受付方式", event_acceptance_label(event.get("acceptance_mode"))), ("参加条件", event.get("eligibility") or "特に設定されていません"), ("キャンセル・中止条件", event.get("cancellation_policy") or "主催者へご確認ください")]
    if event.get("fee_amount") == 0:
        fields = [(label, value) for label, value in fields if label != "支払方法"]
    return '<section class="application-recap"><h2>' + html.escape(event.get("title") or "") + '</h2><dl>' + ''.join('<dt>' + label + '</dt><dd>' + html.escape(str(value)) + '</dd>' for label, value in fields) + '</dl></section>'


APPLICATION_SCRIPT = r'''<script>
const form=document.getElementById('applicationForm'), statusBox=document.getElementById('applicationStatus');
const savedTeam=__SAVED_TEAM__, applicationFee=__APPLICATION_FEE__, submitLabel=__SUBMIT_LABEL__, $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
let reviewing=false,payload;
function sync(){const team=form.querySelector('[name=participation_type]:checked').value==='team';$('teamFields').hidden=!team;$('individualFields').hidden=team;['team_name','representative_name'].forEach(id=>{$(id).disabled=!team;$(id).required=team});$('applicant_name').disabled=team;$('applicant_name').required=!team;$('participant_count').labels[0].textContent=team?'参加予定人数（チーム全体）':'参加人数（本人・友達を含む合計）';$('groupHelp').hidden=team}
function review(value){reviewing=value;$('applicationInput').hidden=value;$('applicationReview').classList.toggle('active',value);$('editApplication').hidden=!value;$('detailBack').hidden=value;$('applicationSubmit').textContent=value?submitLabel:'申込内容を確認する';if(value)$('applicationReview').focus()}
form.addEventListener('change',sync);sync();
$('reuseTeam').onclick=()=>{if(savedTeam)for(const key of ['team_name','representative_name','participant_count'])$(key).value=savedTeam[key]||''};
$('editApplication').onclick=()=>review(false);
form.onsubmit=async e=>{e.preventDefault();statusBox.hidden=true;
 if(!reviewing){if(!form.reportValidity())return;const mode=form.querySelector('[name=participation_type]:checked').value;payload={participation_type:mode};for(const key of ['applicant_name','team_name','representative_name','participant_count','applicant_message'])payload[key]=$(key).value.trim();
 const labels={participation_type:'参加単位',applicant_name:'申込代表者名',team_name:'チーム名',representative_name:'代表者名',participant_count:'参加予定人数',applicant_message:'主催者への連絡'};
 $('reviewAnswers').innerHTML=Object.entries(payload).filter(([k])=>mode==='team'?k!=='applicant_name':!['team_name','representative_name'].includes(k)).map(([k,v])=>`<dt>${labels[k]}</dt><dd>${esc(k==='participation_type'?(v==='team'?'チーム参加':'個人参加'):v)||'なし'}</dd>`).join('');$('applicationFeeTotal').textContent=applicationFee.amount===null?'参加費は主催者へご確認ください。':'参加費合計：'+(applicationFee.amount*(applicationFee.unit==='1チーム'?1:Number(payload.participant_count))).toLocaleString()+'円';review(true);return}
 const button=$('applicationSubmit');button.disabled=true;
 try{const r=await fetch('/api/events/'+encodeURIComponent(form.dataset.eventId)+'/applications',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await r.json();if(!r.ok)throw new Error(data.error||'申込に失敗しました');location.assign('/events/'+encodeURIComponent(form.dataset.eventId)+'/apply')}
 catch(err){statusBox.hidden=false;statusBox.textContent=err.message;statusBox.focus();button.disabled=false}
};
</script>'''


def event_input_datetime(value):
    return str(value or "").replace(" ", "T")[:16]


def render_event_form_html(params, user):
    if not user.get("authenticated"):
        return None
    sport = (params.get("sport", [""])[0] or "").strip()
    event_id = (params.get("event_id", [""])[0] or "").strip()
    copy_id = (params.get("copy", [""])[0] or "").strip()
    initial = {"sport_category": sport, "event_type": "大会", "participation_type": "individual", "capacity_unit": "人", "fee_unit": "1人", "fee_amount": 0, "payment_method": "on_site", "acceptance_mode": "first_come", "minimum_participants": 1}
    initial.update(organizer_form_defaults(user))
    initial["prefecture"] = (params.get("prefecture", [""])[0] or "").strip()
    if event_id or copy_id:
        with connect() as conn:
            initial.update(event_copy_for_owner(conn, event_id or copy_id, user))
            initial["formation_locked"] = bool(event_id and event_owner(conn, event_id, user["user_id"])["announcement_version"])
        if event_id:
            initial["event_id"] = event_id
        else:
            initial.pop("starts_at", None)
            initial.pop("ends_at", None)
            initial.pop("application_deadline", None)
            initial["title"] = f"{initial.get('title', '')}（複製）".strip()
    presets = [item[0] for item in POPULAR_SPORTS]
    if initial.get("payment_method") == "free":
        initial["payment_method"] = "on_site"
    if not initial.get("minimum_participants"):
        initial["minimum_participants"] = ""
    custom = params.get("custom", [""])[0] == "1" or bool(initial.get("sport_category") and initial["sport_category"] not in presets)
    if custom and not event_id and not copy_id:
        initial["event_type"] = "交流イベント"
    sport_choices = ''.join(f'<option value="{html.escape(name)}">{html.escape(name)}</option>' for name in presets)
    category_input = ('<input id="sport_category" type="text" maxlength="100" placeholder="例：ボードゲーム・ハイキング">'
                      if custom else f'<select id="sport_category"><option value="">選択してください</option>{sport_choices}</select>')
    body = f'''<section class="form-shell"><section class="intro"><div><p class="eyebrow">HOST AN EVENT</p><h1>{"募集を編集する" if event_id else "大会・イベントを掲載する"}</h1><p>個人、即席チーム、サークル、大会運営団体のどなたでも掲載できます。団体の詳細紹介や画像は任意です。</p></div></section><section class="panel"><div class="stepper"><span class="active" data-step-label="0">1. 開催内容</span><span data-step-label="1">2. 募集条件</span><span data-step-label="2">3. 公開確認</span></div><form id="eventForm"><section class="form-section active" data-step="0"><div class="field-grid"><div class="field"><label>募集種別</label><select id="event_type">{''.join(f'<option value="{v}">{v}</option>' for v in EVENT_TYPES)}</select></div><div class="field"><label>{"競技・ジャンル" if custom else "競技"}</label>{category_input}</div><div class="field full"><label>タイトル</label><input id="title" maxlength="120" placeholder="例：秋の3x3バスケットボール交流大会"></div><div class="field"><label>開催日時</label><input id="starts_at" type="datetime-local"></div><input id="ends_at" type="hidden"><div class="field"><label>都道府県</label><select id="prefecture"><option value="">選択してください</option>{''.join(f'<option value="{p}">{p}</option>' for p in PREFECTURES)}</select></div><div class="field"><label>会場・地域</label><input id="location" maxlength="250" placeholder="例：代々木公園 バスケットボールコート"></div><div class="field full"><label>説明</label><textarea id="description" maxlength="5000" placeholder="大会・イベントの内容、当日の流れ、持ち物などを記載してください"></textarea></div></div></section><section class="form-section" data-step="1"><div class="field-grid"><div class="field"><label>参加単位</label><select id="participation_type"><option value="individual">個人参加</option><option value="team">チーム参加</option><option value="both">個人・チーム参加</option></select></div><div class="field"><label>定員 [人]（任意）</label><input id="capacity" type="number" min="1" placeholder="例：30"><input id="capacity_unit" type="hidden"></div><div class="field"><label>最低開催人数 [人]</label><input id="minimum_participants" type="number" min="1" max="100000" placeholder="未設定"><span class="help">受付確定数が達すると、主催者へ仮成立を通知します。</span></div><div class="field"><label>1人当たりの参加費 [円]</label><input id="fee_amount" type="text" inputmode="numeric" maxlength="20" placeholder="例：1,500"><input id="fee_unit" type="hidden"><span class="help">参加費なしの場合は0円</span></div><div class="field"><label>損益分岐点 [円]（任意）</label><input id="target_total_amount" type="text" inputmode="numeric" maxlength="20" placeholder="例：30000" aria-describedby="targetTotalHelp"><span class="help" id="targetTotalHelp">主催者にのみ表示されます。</span></div><div class="field"><label>支払方法</label><select id="payment_method"><option value="on_site">現地払い</option><option value="bank_transfer">口座振込</option></select><span class="help" id="paymentHelp">口座は最低開催数に達した後、開催案内で登録します。参加者の最終確認後に振込先を表示します。</span></div><div class="field"><label>受付方式</label><select id="acceptance_mode"><option value="first_come">先着順</option><option value="approval">主催者承認制</option></select></div><div class="field"><label>応募締切（任意）</label><input id="application_deadline" type="datetime-local"></div><div class="field full"><label>参加条件（任意）</label><textarea id="eligibility" maxlength="1200" placeholder="例：大学生・社会人どちらも参加可。初心者歓迎。"></textarea></div></div></section><section class="form-section" data-step="2"><div class="field-grid"><div class="field"><label>主催者の表示名</label><input id="organizer_name" maxlength="80" placeholder="例：Circle Match運営チーム"></div><div class="field"><label>主催者連絡先</label><input id="organizer_contact_email" type="email" maxlength="255" placeholder="メールアドレス"></div><div class="field full"><label>確認済みの主催団体に紐付け（任意）</label><select id="linked_circle_id"><option value="">団体に紐付けない</option></select><span class="help">DBへの掲載だけでは主催権限になりません。確認済みの代表者だけが紐付けできます。</span></div><div class="field full"><label>キャンセル・中止条件</label><textarea id="cancellation_policy" maxlength="1600" placeholder="例：開催3日前までキャンセル可。荒天時は前日18時までに連絡します。"></textarea></div><div class="field full"><label>公開前プレビュー</label><div id="eventPreview" class="preview">入力内容を確認してください。</div></div></div></section><div class="form-actions"><button id="backStep" class="button" type="button">戻る</button><div class="card-actions"><button id="saveDraft" class="button" type="button">下書き保存</button><button id="nextStep" class="button secondary" type="button">次へ</button><button id="publishEvent" class="button primary" type="button" hidden>公開する</button></div></div></form></section><div id="eventFormStatus" class="notice" hidden></div></section>'''
    context = {key: params[key][0] for key in ("sport", "region", "prefecture", "event_id", "copy", "custom") if params.get(key) and params[key][0]}
    return_to = "/events/new" + (("?" + urlencode(context)) if context else "")
    script = EVENT_FORM_SCRIPT.replace("__INITIAL_EVENT__", script_json(initial)).replace("__DEFAULT_EMAIL__", script_json(user.get("email") or "")).replace("__RETURN_TO__", script_json(return_to)).replace("__DRAFT_KEY__", script_json("circle-match:event-draft:" + user["user_id"] + ":" + (event_id or copy_id or ("custom" if custom else "new"))))
    return event_page("募集を掲載する", body, script, post_url=return_to)


def post_url_from_initial(initial):
    sport = (initial.get("sport_category") or "").strip()
    return "/events/new" + (("?" + urlencode({"sport": sport})) if sport else "")


EVENT_FORM_SCRIPT = r"""
<script>
const initialEvent=__INITIAL_EVENT__, defaultEmail=__DEFAULT_EMAIL__, returnTo=__RETURN_TO__, draftKey=__DRAFT_KEY__, form=document.getElementById('eventForm'), statusBox=document.getElementById('eventFormStatus');
const persistedUnits=initialEvent.event_id?{participation:initialEvent.participation_type,capacity:initialEvent.capacity_unit,fee:initialEvent.fee_unit}:null;
let step=0; const ids=['event_type','sport_category','title','starts_at','ends_at','prefecture','location','description','participation_type','capacity','minimum_participants','capacity_unit','eligibility','fee_amount','fee_unit','target_total_amount','payment_method','application_deadline','acceptance_mode','organizer_name','organizer_contact_email','linked_circle_id','cancellation_policy'];
const $=id=>document.getElementById(id);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
function toInput(v){return String(v||'').replace(' ','T').slice(0,16)}
function syncCapacityUnit(){
  const team=$('participation_type').value==='team', legacy=persistedUnits&&$('participation_type').value===persistedUnits.participation;
  $('capacity_unit').value=legacy?persistedUnits.capacity:(team?'チーム':'人');
  $('fee_unit').value=legacy?(persistedUnits.fee||(team?'1チーム':'1人')):(team?'1チーム':'1人');
  $('capacity').labels[0].textContent=`定員 [${$('capacity_unit').value}]（任意）`;
  $('minimum_participants').labels[0].textContent=`最低開催${team?'チーム数':'人数'} [${$('capacity_unit').value}]`;
  $('fee_amount').labels[0].textContent=`${$('fee_unit').value}当たりの参加費 [円]`;
}
function fill(){ids.forEach(id=>{if(!$(id))return;let value=initialEvent[id]??'';if(['starts_at','ends_at','application_deadline'].includes(id))value=toInput(value);$(id).value=value});if(!$('organizer_contact_email').value)$('organizer_contact_email').value=defaultEmail||''}
function showStep(next){step=Math.max(0,Math.min(2,next));document.querySelectorAll('[data-step]').forEach(el=>el.classList.toggle('active',Number(el.dataset.step)===step));document.querySelectorAll('[data-step-label]').forEach(el=>el.classList.toggle('active',Number(el.dataset.stepLabel)===step));$('backStep').hidden=step===0;$('nextStep').hidden=step===2;$('publishEvent').hidden=step!==2;if(step===2)preview()}
function payload(status){const obj={event_id:initialEvent.event_id||'',status};ids.forEach(id=>obj[id]=$(id).value);for(const key of ['fee_amount','target_total_amount'])obj[key]=normalizeFee(obj[key]);if(obj.fee_amount==='0')obj.payment_method='free';return obj}
function preview(){const p=payload('published');const fields=[['募集種別・競技',p.event_type+' / '+p.sport_category],['開催日時',p.starts_at.replace('T',' ')],['会場',p.prefecture+' / '+p.location],['参加単位',({individual:'個人参加',team:'チーム参加',both:'個人・チーム参加'})[p.participation_type]],['定員',p.capacity?p.capacity+p.capacity_unit:'定員なし'],['最低開催数',p.minimum_participants?p.minimum_participants+p.capacity_unit:'未設定（従来の受付）'],['参加費',Number(p.fee_amount)===0?'無料':Number(p.fee_amount).toLocaleString()+'円 / '+p.fee_unit],['支払方法',({free:'-',on_site:'現地払い',bank_transfer:'口座振込'})[p.payment_method]],['受付方式',p.acceptance_mode==='approval'?'主催者承認制':'先着順'],['応募締切',p.application_deadline.replace('T',' ')||'開催日時まで'],['主催者',p.organizer_name],['内容',p.description],['参加条件',p.eligibility||'特に設定されていません'],['キャンセル・中止条件',p.cancellation_policy]];$('eventPreview').innerHTML=`<h3>${esc(p.title||'タイトル未入力')}</h3><dl>${fields.filter(([k])=>k!=='支払方法'||Number(p.fee_amount)!==0).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v||'未入力')}</dd>`).join('')}</dl>`}
async function loadOrganizations(){try{const orgs=await (await fetch('/api/my-organizations')).json();if(!Array.isArray(orgs))return;const select=$('linked_circle_id');const current=initialEvent.linked_circle_id||'';orgs.forEach(o=>{const op=document.createElement('option');op.value=o.circle_id;op.textContent=`${o.circle_name}（${o.university_name||o.prefecture||''}）`;if(o.circle_id===current)op.selected=true;select.append(op)})}catch(_){}}
const required=['sport_category','title','starts_at','prefecture','location','description','organizer_name','organizer_contact_email','cancellation_policy'];
if(initialEvent.minimum_participants)required.push('minimum_participants');
statusBox.className='error-box';statusBox.setAttribute('role','alert');statusBox.tabIndex=-1;
ids.forEach(id=>{const input=$(id);if(input.type==='hidden')return;const label=input.closest('.field')?.querySelector('label');if(label){label.htmlFor=id;if(required.includes(id))label.textContent+='（必須）'}input.required=required.includes(id)});
$('capacity').max=100000;
function error(message,input){statusBox.hidden=false;statusBox.textContent=message;if(input){showStep(Number(input.closest('[data-step]').dataset.step));input.focus()}else statusBox.focus();return false}
function validate(section){statusBox.hidden=true;const controls=section.querySelectorAll('input,select,textarea');for(const input of controls){input.setCustomValidity('');if(input.required&&!input.value.trim())return error((input.labels?.[0]?.textContent||'項目')+'を入力してください',input);if(!input.checkValidity())return error((input.labels?.[0]?.textContent||'項目')+'の入力内容を確認してください',input)}
 if(section.dataset.step==='0'&&new Date($('starts_at').value)<=new Date())return error('開催日時は現在より後にしてください',$('starts_at'));
 if(section.dataset.step==='1'){const deadline=$('application_deadline').value;if(deadline&&(new Date(deadline)<new Date()||deadline>$('starts_at').value))return error('応募締切は現在より後、開催日時以前にしてください',$('application_deadline'));const amount=normalizeFee($('fee_amount').value);if(!/^\d+$/.test(amount)||Number(amount)>10000000)return error('参加費は0〜10,000,000円の整数で入力してください',$('fee_amount'));if(Number(amount)>0&&$('payment_method').value==='free')return error('参加費がある場合は、現地払い・口座振込を選択してください',$('payment_method'));const target=normalizeFee($('target_total_amount').value);if(target&&(!/^\d+$/.test(target)||Number(target)>1000000000))return error('損益分岐点は0〜1,000,000,000円の整数で入力してください',$('target_total_amount'));if($('capacity').value&&Number($('minimum_participants').value)>Number($('capacity').value))return error('最低開催数は定員以下にしてください',$('minimum_participants'))}return true}
function remember(){try{sessionStorage.setItem(draftKey,JSON.stringify(payload('draft')))}catch(_){}}
function normalizeFee(value){return String(value).trim().replace(/[０-９]/g,c=>String.fromCharCode(c.charCodeAt(0)-65248)).replace(/[,，]/g,'')}
function syncPayment(){$('fee_amount').disabled=false;$('fee_amount').required=true;const raw=normalizeFee($('fee_amount').value),free=/^\d+$/.test(raw)&&Number(raw)===0;$('payment_method').disabled=free||(typeof initialEvent!=='undefined'&&initialEvent.formation_locked);if(!['on_site','bank_transfer'].includes($('payment_method').value))$('payment_method').value='on_site';$('paymentHelp').hidden=free||$('payment_method').value!=='bank_transfer'}
async function save(status){if(status==='published'){for(const section of form.querySelectorAll('[data-step]'))if(!validate(section))return}else if(!$('title').value.trim())return error('下書きのタイトルを入力してください',$('title'));const buttons=[$('publishEvent'),$('saveDraft')];buttons.forEach(b=>b.disabled=true);statusBox.hidden=true;remember();try{const r=await fetch('/api/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload(status))});const data=await r.json();if(r.status===401){location.assign('/signin?return_to='+encodeURIComponent(returnTo));return}if(!r.ok)throw new Error(data.error||'保存に失敗しました');try{sessionStorage.removeItem(draftKey)}catch(_){}location.assign(status==='published'?`/events/${encodeURIComponent(data.event_id)}?published=1`:`/events/new?event_id=${encodeURIComponent(data.event_id)}&saved=1`)}catch(err){error(err.message);buttons.forEach(b=>b.disabled=false)}}
fill();try{const saved=JSON.parse(sessionStorage.getItem(draftKey)||'null');if(saved){Object.assign(initialEvent,saved);fill()}}catch(_){}
if(initialEvent.formation_locked){for(const id of ['starts_at','prefecture','location','description','eligibility','fee_amount','payment_method','cancellation_policy','minimum_participants','participation_type']){$(id).readOnly=true;if($(id).tagName==='SELECT')$(id).disabled=true;}const note=document.createElement('p');note.className='notice';note.textContent='開催決定後の料金・参加条件は変更できません。日時・会場の変更は「開催案内」から行ってください。';const link=document.createElement('a');link.href='/events/'+encodeURIComponent(initialEvent.event_id)+'/organize';link.textContent=' 開催案内へ';note.append(link);form.before(note)}
syncCapacityUnit();syncPayment();$('payment_method').addEventListener('change',syncPayment);$('fee_amount').addEventListener('input',syncPayment);$('participation_type').addEventListener('change',()=>{syncCapacityUnit();remember()});loadOrganizations();showStep(0);
if(new URLSearchParams(location.search).get('saved')==='1'){const saved=document.createElement('p');saved.className='notice';saved.textContent='下書きを保存しました。マイページから再開できます。';form.before(saved)}
function moveStep(next){showStep(next);const active=form.querySelector('.form-section.active');active.tabIndex=-1;active.focus({preventScroll:true});form.closest('.panel').scrollIntoView({block:'start'})}
$('nextStep').onclick=()=>{if(validate(form.querySelector('[data-step="'+step+'"]')))moveStep(step+1)};
$('backStep').onclick=()=>moveStep(step-1);$('saveDraft').onclick=()=>save('draft');$('publishEvent').onclick=()=>save('published');form.addEventListener('input',()=>{remember();if(step===2)preview()});form.addEventListener('change',()=>{remember();if(step===2)preview()});form.onsubmit=e=>{e.preventDefault();if(step<2)$('nextStep').click();else save('published')};
</script>
"""


def render_event_organize_html(event_id, user):
    with connect() as conn:
        event = dict(event_owner(conn, event_id, user["user_id"]))
        count = active_confirmed_capacity(conn, event_id)
    event["confirmed_count"] = count
    back = '<a class="button" href="/mypage?tab=hosted">マイページへ戻る</a>'
    if (not event["minimum_participants"] or event["status"] not in {"published", "closed"}
            or event["starts_at"] <= event_local_now()
            or (not event["announcement_version"] and count < event["minimum_participants"])):
        return event_page("開催案内", f'<section class="form-shell"><h1>開催案内</h1><p>開催を決定するには、募集を公開し最低開催人数・チーム数に達している必要があります。現在の受付数：{count}{html.escape(event["capacity_unit"])}</p>{back}</section>')
    def field(key, label, kind="text", maximum=250, readonly=False):
        value = event.get(key) or ""
        if kind == "datetime-local":
            value = event_input_datetime(value)
        attributes = f'id="{key}" name="{key}" required maxlength="{maximum}"' + (' readonly' if readonly else '')
        control = (f'<textarea {attributes}>{html.escape(value)}</textarea>' if kind == "textarea"
                   else f'<input {attributes} type="{kind}" value="{html.escape(value, quote=True)}">')
        return f'<div class="field full"><label for="{key}">{label}</label>{control}</div>'
    fields = field("starts_at", "開催日時", "datetime-local") + field("location", "会場")
    fields += field("announcement_details", "開催案内・集合場所・持ち物など", "textarea", 5000)
    fields += field("attendance_deadline", "最終参加確認の期限", "datetime-local")
    fields += '<p class="help">期限前24時間以内に一度リマインドし、期限切れは主催者と申込者へ通知します。自動取消はしません。</p>'
    if event["payment_method"] == "bank_transfer" and event["fee_amount"]:
        fields += field("bank_transfer_details", "振込先口座（最終参加確認済みの参加者のみ）", "textarea", 1200, bool(event["announcement_version"]))
        fields += field("payment_deadline", "振込期限", "datetime-local")
        fields += '<p class="help">銀行名・支店・口座種別・口座番号・名義をご記入ください。暗証番号やログイン情報は入力しないでください。口座は公開ページ・共有文・メールには掲載しません。入金照合・返金は主催者が行います。</p>'
    label = "開催案内を更新して再確認を依頼する" if event["announcement_version"] else "開催を決定して参加確認を依頼する"
    body = (event_home_navigation("開催案内") + f'<section class="form-shell"><h1>{html.escape(event["title"])}</h1>'
            f'<p>{html.escape(event_formation_label(event))} / 受付数：{count}{html.escape(event["capacity_unit"])}</p>'
            '<p>受付確定済みの参加者に通知します。参加者がアプリで最終確認した後に、振込先・期限を表示します。案内を更新した場合は再確認を依頼します。未確認・未入金の自動取消は行いません。</p>'
            f'<form id="formationForm"><div class="field-grid">{fields}</div><div class="card-actions">{back}<button class="button primary" type="submit">{label}</button></div></form><p id="formationError" class="error-box" role="alert" hidden></p></section>')
    return event_page("開催案内", body, formation_form_script(event, "announce", "/mypage?tab=hosted"))


def render_event_attendance_html(event_id, user):
    with connect() as conn:
        event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
        application = conn.execute("select * from event_applications where event_id=? and applicant_user_id=?",
                                   (event_id, user["user_id"])).fetchone()
    if not event or not application:
        raise PermissionError("この申込を確認する権限がありません")
    event, application = dict(event), dict(application)
    body = event_home_navigation("開催案内・参加確認") + '<section class="form-shell"><h1>開催案内・参加確認</h1>'
    body += '<p>' + html.escape(event_admission_label(event, application)) + '</p>' + event_application_recap(event)
    script = ""
    active = event["status"] in {"published", "closed"} and application["status"] == "confirmed" and bool(event["announcement_version"])
    confirmed = active and application["attendance_version"] == event["announcement_version"]
    if active:
        body += '<h2>主催者からの開催案内</h2><p style="white-space:pre-wrap">' + html.escape(event["announcement_details"]) + '</p>'
        if event["attendance_deadline"]:
            body += '<p>最終参加確認の期限：' + format_event_datetime(event["attendance_deadline"]) + '</p>'
        expired = bool(event["attendance_deadline"] and event["attendance_deadline"] <= event_local_now())
        if not confirmed and event["starts_at"] > event_local_now() and not expired:
            body += f'<form id="formationForm"><p>この確認は申込全員（{application["participant_count"]}名）に適用されます。</p><label><input type="checkbox" required> 最新の開催内容・料金・キャンセル条件を確認し、参加します。</label><p><button type="submit" class="button primary">最終参加を確認する</button></p></form><p id="formationError" class="error-box" role="alert" hidden></p>'
            script = formation_form_script(event, "attendance", "/events/" + quote(event_id) + "/attendance")
        elif not confirmed:
            body += f'<p>確認期限または開催日時を過ぎています。<a href="/events/{quote(event_id)}/contact">主催者へお問い合わせください。</a></p>'
        if confirmed and event["payment_method"] == "bank_transfer" and event["fee_amount"]:
            total = event["fee_amount"] * (1 if event["fee_unit"] == "1チーム" else application["participant_count"])
            body += (f'<section class="application-recap"><h2>振込案内</h2><p>お支払額：{total:,}円</p><p>振込期限：{format_event_datetime(event["payment_deadline"])}</p>'
                     '<p style="white-space:pre-wrap">' + html.escape(event["bank_transfer_details"]) + '</p>'
                     '<p>入金確認・返金は主催者が行います。すでに振込済みの場合は再度振り込まず、マイページから主催者へご連絡ください。期限を過ぎた場合も先に主催者へご確認ください。</p></section>')
        elif confirmed and event["fee_amount"]:
            body += '<p>参加費は当日、現地でお支払いください。</p>'
    else:
        body += '<p>開催決定と受付確定後に、こちらで最終参加確認ができます。</p>'
    body += '<a class="button" href="/mypage?tab=attending">申込管理・主催者への連絡</a></section>'
    return event_page("開催案内・参加確認", body, script)


def formation_form_script(event, action, destination):
    data = {"endpoint": "/api/events/" + quote(event["event_id"]) + "/" + action,
            "version": event["announcement_version"], "destination": destination}
    return r'''<script>(()=>{const data=__DATA__,form=document.getElementById('formationForm'),error=document.getElementById('formationError');
form.onsubmit=async e=>{e.preventDefault();if(!form.reportValidity())return;const button=form.querySelector('button[type=submit]');button.disabled=true;error.hidden=true;
try{const payload=Object.fromEntries(new FormData(form));payload.version=data.version;const r=await fetch(data.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const result=await r.json();if(!r.ok)throw Error(result.error||'保存できませんでした');location.assign(data.destination)}catch(e){error.hidden=false;error.textContent=e.message;button.disabled=false}}})();</script>'''.replace("__DATA__", script_json(data))


def render_notifications_html(user, page=0):
    notes = notifications_for_user(user, page * 50)
    rendered = []
    for note in notes:
        link = f'<a href="/events/{quote(note["event_id"])}">募集詳細を確認する</a>' if note.get("event_id") else ''
        if note.get("event_id") and note.get("notification_type") in {"event_announced", "attendance_recorded", "attendance_reminder", "attendance_expired"}:
            link = f'<a href="/events/{quote(note["event_id"])}/attendance">開催案内・参加確認へ</a>'
        elif note.get("event_id") and note.get("notification_type") == "event_provisional":
            link = f'<a href="/events/{quote(note["event_id"])}/organize">開催を決定する</a>'
        elif note.get("event_id") and note.get("notification_type") in {"attendance_expired_host", "count_requested"}:
            link = f'<a href="/events/{quote(note["event_id"])}/applications">受付・入金管理へ</a>'
        elif note.get("event_id") and note.get("notification_type") == "new_message":
            link = f'<a href="/events/{quote(note["event_id"])}/contact">質問・連絡を開く</a>'
        elif note.get("event_id") and note.get("notification_type") in {"count_changed", "payment_updated", "application_released"}:
            link = '<a href="/mypage">マイページで申込状況を確認する</a>'
        unread = not note.get("read_at")
        rendered.append(f'<article class="notification {"unread" if unread else ""}" data-notification="{html.escape(note["notification_id"], quote=True)}"><strong>{html.escape(note.get("title") or "")}</strong><p>{html.escape(note.get("body") or "")}</p><small>{format_event_datetime(note.get("created_at"))} / メール通知: {html.escape(email_delivery_label(note.get("email_status")))}</small>{link}</article>')
    previous = f'<a class="button" href="/notifications?page={page-1}">前へ</a>' if page else ''
    following = f'<a class="button" href="/notifications?page={page+1}">次へ</a>' if len(notes) == 50 else ''
    body = (event_home_navigation("通知") + '<section class="panel"><div class="panel-head"><h1>通知</h1>'
            '<a class="button" href="/mypage">マイページ</a></div><div class="notification-list">'
            + (''.join(rendered) or '<p class="empty">通知はありません。</p>') + '</div>'
            + (f'<nav class="db-pager" aria-label="通知のページ">{previous}{following}</nav>' if previous or following else '')
            + '</section><div id="notificationError" class="error-box" role="alert" hidden>既読状態を更新できませんでした。'
              '<button id="retryNotificationRead" class="button" type="button">再試行</button></div>')
    script = '''<script>
(()=>{
const error=document.getElementById('notificationError');let busy=false;
async function markRead(){const notes=[...document.querySelectorAll('.notification.unread')];if(busy||!notes.length)return;busy=true;error.hidden=true;
try{const r=await fetch('/api/notifications/read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({notification_ids:notes.map(n=>n.dataset.notification)})});if(!r.ok)throw Error();const result=await r.json();notes.forEach(n=>n.classList.remove('unread'));window.dispatchEvent(new CustomEvent('notifications-read',{detail:result}))}catch(_){error.hidden=false}finally{busy=false}}
document.getElementById('retryNotificationRead').onclick=markRead;document.addEventListener('DOMContentLoaded',markRead);
})();
</script>'''
    return event_page("通知", body, script)


def render_mypage_html(user):
    if not user.get("authenticated"):
        return None
    data = event_my_page(user)
    hosted = []
    for event in data["hosted"]:
        eid, url_id = html.escape(event["event_id"], quote=True), quote(event["event_id"])
        status = event["status"]
        actions = []
        if status != "draft":
            actions.append(f'<a class="button" href="/events/{url_id}">公開ページ</a>')
            actions.append(f'<a class="button" href="/events/{url_id}/applications">受付・入金管理</a>')
            actions.append(f'<a class="button" href="/events/{url_id}/contact">質問・連絡</a>')
        if status != "cancelled":
            actions.append(f'<a class="button" href="/events/new?event_id={url_id}">{"下書きを再開" if status == "draft" else "募集内容を編集"}</a>')
        actions.append(f'<a class="button" href="/events/new?copy={url_id}">複製</a>')
        if status == "published":
            actions.append(f'<button class="button" data-event-status="closed" data-event="{eid}">締切</button>')
        if status in {"published", "closed"}:
            actions.append(f'<button class="button" data-event-status="cancelled" data-event="{eid}">中止</button>')
        label, available = event_availability(event)
        badge = 'cancelled' if status == 'cancelled' else ('open' if available else 'closed')
        target_total = owner_financial_summary(event)
        if event.get("minimum_participants"):
            target_total += f'<p>{html.escape(event_formation_label(event))} / 最低開催数：{event["minimum_participants"]}{html.escape(event["capacity_unit"])} / 最終参加確認済み：{event.get("final_attendance_count", 0)}{html.escape(event["capacity_unit"])}</p>'
            if status in {"published", "closed"} and (event.get("announcement_version") or event.get("confirmed_count", 0) >= event["minimum_participants"]):
                actions.insert(0, f'<a class="button primary" href="/events/{url_id}/organize">{"開催案内を確認・変更" if event.get("announcement_version") else "開催を決定する"}</a>')
        hosted.append(f'<article class="my-card" data-capacity-unit="{html.escape(event.get('capacity_unit') or '人', quote=True)}"><span class="badge {badge}">{html.escape(label)}</span><h3>{html.escape(event.get("title") or "")}</h3><p>{format_event_datetime(event.get("starts_at"))} / 申込 <span data-application-count>{event.get("application_count", 0)}</span>件・確定 <span data-confirmed-count>{event.get("confirmed_count", 0)}</span>{html.escape(event.get("capacity_unit") or "人")}</p>{target_total}<div class="card-actions">{"".join(actions)}</div><div id="apps-{eid}" class="apps" hidden></div><div id="messages-{eid}" class="messages" hidden></div></article>')
    attending = []
    for app in data["attending"]:
        cancelled = app.get("status") == "cancelled"
        label = event_admission_label(app, app)
        badge = "cancelled" if cancelled else ("open" if app.get("application_status") == "confirmed" else "closed")
        eid = html.escape(app["event_id"], quote=True)
        cancel_button = f'<button class="button" data-cancel-app="{html.escape(app["application_id"], quote=True)}" data-event="{eid}">申込を取り消す</button>' if not cancelled and app["application_status"] in {"pending", "confirmed"} else ''
        reapply = f'<a class="button" href="/events/{quote(app["event_id"])}/apply">再度申し込む</a>' if not cancelled and app["application_status"] == "cancelled" and event_availability(app)[1] else ''
        if not cancelled and app["application_status"] == "confirmed" and app.get("announcement_version"):
            reapply += f'<a class="button primary" href="/events/{quote(app["event_id"])}/attendance">開催案内・参加確認</a>'
        reapply += f'<a class="button" href="/events/{quote(app["event_id"])}/applications/{quote(app["application_id"])}">申込内容・人数変更</a>'
        attending.append(f'''<article class="my-card"><span class="badge {badge}">{html.escape(label)}</span><h3>{html.escape(app.get("title") or "")}</h3><p>{format_event_datetime(app.get("starts_at"))} / {html.escape(app.get("location") or "")} / {html.escape(event_participation_label(app.get("participation_type") or ""))}</p><p>{html.escape(app.get("team_name") or app.get("applicant_name") or "")} / {app.get("participant_count", 1)}名</p><div class="card-actions"><a class="button" href="/events/{quote(str(app["event_id"]))}">詳細</a>{cancel_button}{reapply}<button class="button" data-message-event="{eid}">主催者に連絡</button></div><div id="messages-{eid}" class="messages" hidden></div></article>''')
    body = f'''<section class="intro"><div><p class="eyebrow">MY PAGE</p><h1>マイページ</h1><p>{html.escape(user.get("display_name") or user.get("email") or "")}</p></div></section><section class="panel"><div class="panel-head"><div><h2>大会・イベント</h2><p>参加状況と主催する募集を確認できます。</p></div><a class="button primary" href="/events/new">募集を掲載する</a></div><div class="mypage-tabs"><button class="active" data-my-tab="attending">参加するイベント</button><button data-my-tab="hosted">主催するイベント</button></div><div id="my-attending" class="my-section active">{"".join(attending) or '<div class="empty">参加を申し込んだイベントはありません。</div>'}</div><div id="my-hosted" class="my-section">{"".join(hosted) or '<div class="empty">主催している募集はありません。</div>'}</div></section>'''
    with connect() as conn:
        inquiries = conn.execute("""select e.event_id,e.title,max(m.created_at) as latest from event_messages m
                     join event_posts e on e.event_id=m.event_id
                     where e.organizer_user_id!=? and (m.sender_user_id=? or m.recipient_user_id=?)
                     and not exists(select 1 from event_applications a where a.event_id=e.event_id and a.applicant_user_id=?)
                     group by e.event_id order by latest desc limit 100""", (user["user_id"], user["user_id"], user["user_id"], user["user_id"])).fetchall()
    if inquiries:
        inquiry_html = '<h2>申込前の質問・連絡</h2>' + ''.join(f'<article class="app-row"><span>{html.escape(row["title"])}</span><a class="button" href="/events/{quote(row["event_id"])}/contact">連絡を開く</a></article>' for row in inquiries)
        body = body.replace('</div><div id="my-hosted"', inquiry_html + '</div><div id="my-hosted"')
    body += '<div id="myError" class="error-box" role="alert" tabindex="-1" hidden></div><dialog id="actionDialog" class="ux-dialog" aria-labelledby="actionTitle"><h2 id="actionTitle">操作の確認</h2><p id="actionText"></p><form method="dialog" class="card-actions"><button class="button" value="cancel" autofocus>戻る</button><button class="button primary" value="confirm">実行する</button></form></dialog>'
    return event_page("マイページ", body, MYPAGE_SCRIPT)


MYPAGE_SCRIPT = r"""
<script>
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
async function request(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body||{})});const d=await r.json();if(!r.ok)throw new Error(d.error||'操作に失敗しました');return d}
function selectTab(tab){
  if(!['attending','hosted'].includes(tab))tab='attending';
  document.querySelectorAll('[data-my-tab]').forEach(b=>b.classList.toggle('active',b.dataset.myTab===tab));
  document.querySelectorAll('.my-section').forEach(s=>s.classList.toggle('active',s.id==='my-'+tab));
}
document.querySelectorAll('[data-my-tab]').forEach(button=>button.onclick=()=>{
  selectTab(button.dataset.myTab);history.replaceState(null,'','/mypage?tab='+button.dataset.myTab);
});
selectTab(new URLSearchParams(location.search).get('tab'));
function showError(message){const box=document.getElementById('myError');box.hidden=false;box.textContent=message;box.focus()}
function confirmAction(message){const dialog=document.getElementById('actionDialog');document.getElementById('actionText').textContent=message;dialog.returnValue='cancel';return new Promise(resolve=>{dialog.addEventListener('close',()=>resolve(dialog.returnValue==='confirm'),{once:true});dialog.showModal()})}
document.querySelectorAll('[data-event-status]').forEach(button=>button.onclick=async()=>{if(!await confirmAction(button.dataset.eventStatus==='cancelled'?'この募集を中止しますか？参加者へ中止が通知されます。':'新しい申込を締め切りますか？届いている申請の承認は続けられます。'))return;button.disabled=true;try{await request(`/api/events/${encodeURIComponent(button.dataset.event)}/status`,{status:button.dataset.eventStatus});location.reload()}catch(e){showError(e.message);button.disabled=false}});
document.querySelectorAll('[data-cancel-app]').forEach(button=>button.onclick=async()=>{if(!await confirmAction('申込を取り消しますか？キャンセル料・返金は募集の条件をご確認ください。取り消し後も主催者へ連絡できます。'))return;button.disabled=true;try{await request(`/api/events/${encodeURIComponent(button.dataset.event)}/applications/${encodeURIComponent(button.dataset.cancelApp)}/cancel`);location.reload()}catch(e){showError(e.message);button.disabled=false}});
async function loadMessages(eventId,recipient,recipientName='主催者'){
  const pane=document.getElementById('messages-'+eventId), requestId=Symbol();
  if(!pane)return;
  pane.messageRequest=requestId;pane.hidden=false;pane.textContent='連絡を読み込んでいます。';
  const peer=recipient?'?peer_user_id='+encodeURIComponent(recipient):'';
  try{
    const r=await fetch('/api/events/'+encodeURIComponent(eventId)+'/messages'+peer), messages=await r.json();
    if(pane.messageRequest!==requestId)return;
    if(!r.ok)throw new Error(messages.error||'メッセージを取得できません');
    pane.innerHTML='<h4>'+esc(recipientName)+'への連絡</h4><div class="message-log">'+
      (messages.map(m=>'<div class="message"><strong>'+esc(m.sender_name||'利用者')+'</strong><p>'+esc(m.body)+'</p></div>').join('')||'<div class="empty">まだメッセージはありません。</div>')+
      '</div><form class="message-form"><label for="message-input-'+esc(eventId)+'">メッセージ</label><textarea id="message-input-'+esc(eventId)+'" maxlength="2000" required></textarea><div class="card-actions"><button class="button primary" type="submit">送信</button><span role="status" data-message-status></span></div></form>';
    pane.querySelector('form').onsubmit=async e=>{
      e.preventDefault();
      const input=pane.querySelector('textarea'), button=pane.querySelector('button'), status=pane.querySelector('[data-message-status]');
      if(button.disabled||!input.value.trim())return;
      button.disabled=true;status.textContent='送信中…';
      try{
        await request('/api/events/'+encodeURIComponent(eventId)+'/messages',{body:input.value,recipient_user_id:recipient||''});
        if(pane.messageRequest===requestId)await loadMessages(eventId,recipient,recipientName);
      }catch(error){if(pane.messageRequest===requestId){status.textContent=error.message;button.disabled=false}}
    };
  }catch(error){if(pane.messageRequest===requestId)pane.textContent=error.message}
}
document.querySelectorAll('[data-message-event]').forEach(button=>button.onclick=()=>loadMessages(button.dataset.messageEvent,''));
document.querySelectorAll('[data-manage]').forEach(button=>button.onclick=async()=>{const pane=document.getElementById('apps-'+button.dataset.manage);try{const r=await fetch(`/api/events/${encodeURIComponent(button.dataset.manage)}/applications`);const apps=await r.json();if(!r.ok)throw new Error(apps.error||'申込者を取得できません');const card=button.closest('article');card.querySelector('[data-application-count]').textContent=apps.length;card.querySelector('[data-confirmed-count]').textContent=apps.filter(a=>a.status==='confirmed').reduce((n,a)=>n+(card.dataset.capacityUnit==='チーム'?1:Number(a.participant_count)),0);pane.hidden=false;pane.innerHTML=apps.length?apps.map(a=>`<div class="app-row"><div><strong>${esc(a.team_name||a.applicant_name||a.account_name||'参加者')}</strong><p>${a.representative_name?'代表者：'+esc(a.representative_name)+' / ':''}${esc(a.participant_count)}名 / ${esc(a.display_status||({pending:'承認待ち',confirmed:'参加確定',declined:'見送り',cancelled:'取消済み'})[a.status]||a.status)}</p><p class="app-message">申込時の連絡：${esc(a.applicant_message||'なし')}</p></div><div class="card-actions">${a.status==='pending'&&a.can_review?`<button class="button" data-app-action="confirm" data-app="${esc(a.application_id)}">承認</button><button class="button" data-app-action="decline" data-app="${esc(a.application_id)}">見送り</button>`:''}<button class="button" data-recipient-name="${esc(a.team_name||a.applicant_name||a.account_name||'参加者')}" data-app-message="${esc(a.applicant_user_id)}">連絡</button></div></div>`).join(''):'<div class="empty">申込はまだありません。</div>';pane.querySelectorAll('[data-app-action]').forEach(action=>action.onclick=async()=>{if(!await confirmAction(action.dataset.appAction==='confirm'?'この申込を承認して受付を確定しますか？':'この申込を見送りますか？参加者へ通知されます。'))return;action.disabled=true;try{await request(`/api/events/${encodeURIComponent(button.dataset.manage)}/applications/${encodeURIComponent(action.dataset.app)}/status`,{action:action.dataset.appAction});location.reload()}catch(e){showError(e.message);action.disabled=false}});pane.querySelectorAll('[data-app-message]').forEach(action=>action.onclick=()=>loadMessages(button.dataset.manage,action.dataset.appMessage,action.dataset.recipientName))}catch(e){showError(e.message)}});
</script>
"""


EVENT_OPERATIONS_SCRIPT = r'''<script>
document.querySelectorAll('form[data-operation]').forEach(form=>form.onsubmit=async e=>{
  e.preventDefault();if(!form.reportValidity()||form.dataset.busy)return;
  const error=form.querySelector('[role=alert]'),buttons=[...form.querySelectorAll('button')];
  const payload=Object.fromEntries(new FormData(form));
  if(e.submitter?.name)payload[e.submitter.name]=e.submitter.value;
  form.dataset.busy='1';buttons.forEach(b=>b.disabled=true);error.hidden=true;
  try{const r=await fetch(form.dataset.operation,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const result=await r.json();if(!r.ok)throw Error(result.error||'保存できませんでした');location.reload();
  }catch(err){error.textContent=err.message;error.hidden=false;delete form.dataset.busy;buttons.forEach(b=>b.disabled=false)}
});</script>'''


def operation_form(endpoint, contents, revision=None):
    hidden = f'<input type="hidden" name="revision" value="{int(revision)}">' if revision is not None else ''
    return f'<form data-operation="{html.escape(endpoint, quote=True)}">{hidden}{contents}<p class="error-box" role="alert" hidden></p></form>'


def render_event_application_operations(event_id, user, application_id=""):
    with connect() as conn:
        event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
        if not event or not user.get("authenticated"):
            raise PermissionError("この募集を管理する権限がありません")
        event = dict(event)
        owner = event["organizer_user_id"] == user["user_id"]
        if not application_id:
            event_owner(conn, event_id, user["user_id"])
            applications = event_applications_for_owner(event_id, user)
        else:
            app = conn.execute("select * from event_applications where event_id=? and application_id=?", (event_id, application_id)).fetchone()
            if not app or (not owner and app["applicant_user_id"] != user["user_id"]):
                raise PermissionError("この申込を閲覧する権限がありません")
            app = dict(app)
    prefix = "/events/" + quote(event_id)
    back = prefix + "/applications" if owner and application_id else "/mypage?tab=" + ("hosted" if owner else "attending")
    title = "受付・入金管理" if owner else "申込内容・人数変更"
    body = event_home_navigation(title) + f'<section class="form-shell"><h1>{title}</h1><h2>{html.escape(event["title"])}</h2><p><a href="{back}">戻る</a> / <a href="{prefix}/contact">質問・連絡</a></p>'
    if event.get("attendance_deadline"):
        body += '<p>最終参加確認の期限：' + format_event_datetime(event["attendance_deadline"]) + '</p>'
    if not application_id:
        if event["fee_amount"]:
            totals = {key: sum(1 for row in applications if row["payment_status"] == key) for key in PAYMENT_STATUSES}
            body += '<p>' + ' / '.join(f'{label} {totals[key]}件' for key, label in PAYMENT_STATUSES.items()) + '</p>'
        body += '<div class="notification-list">'
        for row in applications:
            label = html.escape(row["team_name"] or row["applicant_name"] or row["account_name"] or "参加者")
            status = html.escape(row["display_status"])
            payment = PAYMENT_STATUSES.get(row["payment_status"], "未入金") if event["fee_amount"] else "無料"
            extra = f'<p>人数変更の申請：{row["requested_participant_count"]}名</p>' if row["requested_participant_count"] else ''
            if row["can_release"]:
                extra += '<p class="error-box">確認期限切れ・最終参加未確認</p>'
            body += f'<article class="app-row"><div><h3>{label}</h3><p>{row["participant_count"]}名 / {status} / {payment}</p>{extra}</div><a class="button" href="{prefix}/applications/{quote(row["application_id"])}">申込を確認・管理</a></article>'
        body += ('' if applications else '<p class="empty">申込はまだありません。</p>') + '</div></section>'
        return event_page(title, body)
    endpoint = "/api" + prefix + "/applications/" + quote(application_id)
    body += f'<h3>{html.escape(app["team_name"] or app["applicant_name"] or "参加者")}</h3><p>{html.escape(event_admission_label(event, app))} / {app["participant_count"]}名</p>'
    if app["applicant_message"]:
        body += '<p>申込時の連絡：' + html.escape(app["applicant_message"]) + '</p>'
    if event["fee_amount"]:
        total = event["fee_amount"] * (1 if event["fee_unit"] == "1チーム" else app["participant_count"])
        body += f'<p>参加費合計：{total:,}円 / {PAYMENT_STATUSES.get(app["payment_status"], "未入金")}</p><p class="help">入金状態は主催者による手動記録です。送金・返金の自動処理はありません。</p>'
    if owner:
        body += f'<p><a class="button" href="{prefix}/contact?{urlencode({"peer_user_id": app["applicant_user_id"]})}">この申込者に連絡</a></p>'
        if app["status"] == "pending" and event["status"] in {"published", "closed"} and event["starts_at"] > event_local_now():
            body += '<h2>参加申請</h2>' + operation_form(endpoint + "/status", '<div class="card-actions"><button class="button primary" name="action" value="confirm">受付を承認する</button><button class="button" name="action" value="decline">見送る</button></div>')
        if app["requested_participant_count"]:
            body += f'<h2>人数変更の申請</h2><p>{app["participant_count"]}名 → {app["requested_participant_count"]}名</p>'
            body += operation_form(endpoint + "/count-review", '<div class="card-actions"><button class="button primary" name="decision" value="approve">人数変更を承認</button><button class="button" name="decision" value="decline">元の人数を維持</button></div>', app["operation_revision"])
        if event["fee_amount"] and app["status"] in {"confirmed", "cancelled"}:
            options = ''.join(f'<option value="{key}"{" selected" if key == app["payment_status"] else ""}>{label}</option>' for key, label in PAYMENT_STATUSES.items())
            fields = '<div class="field"><label for="payment_status">入金・精算状態</label><select id="payment_status" name="payment_status">' + options + '</select></div>'
            fields += '<div class="field"><label for="payment_note">主催者用メモ（任意・非公開）</label><textarea id="payment_note" name="payment_note" maxlength="500">' + html.escape(app["payment_note"]) + '</textarea></div>'
            fields += '<p><label><input type="checkbox" required> 実際の入金・精算状況を確認しました。</label></p><button class="button primary">状態を保存する</button>'
            body += '<h2>入金・返金管理</h2>' + operation_form(endpoint + "/payment", fields, app["operation_revision"])
        if can_release_unconfirmed(event, app):
            fields = '<p>期限を過ぎた未確認の受付を取り消します。先に申込者へ連絡し、状況を確認してください。</p><div class="field"><label for="reason">取消理由</label><textarea id="reason" name="reason" maxlength="500" required></textarea></div><p><label><input type="checkbox" required> 申込者へ取消理由を通知し、受付枠を解放します。</label></p><button class="button">この受付を取り消す</button>'
            body += '<h2>期限切れの受付</h2>' + operation_form(endpoint + "/release", fields, app["operation_revision"])
    elif app["status"] in {"pending", "confirmed"} and event["status"] in {"published", "closed"} and event["starts_at"] > event_local_now():
        body += '<h2>参加人数を変更</h2>'
        if app["payment_status"] != "unpaid":
            body += '<p>入金・精算の記録があるため、主催者へ人数変更をご相談ください。</p>'
        elif event["attendance_deadline"] and event["attendance_deadline"] <= event_local_now():
            body += '<p>確認期限を過ぎています。主催者へご相談ください。</p>'
        else:
            requested = app["requested_participant_count"]
            if requested:
                body += f'<p role="status">{requested}名への変更を申請中です。承認までは{app["participant_count"]}名の枠を維持します。</p>'
            fields = f'<div class="field"><label for="participant_count">本人・友達を含む参加人数 [人]</label><input id="participant_count" name="participant_count" type="number" min="1" max="100000" required value="{requested or app["participant_count"]}"></div>'
            fields += '<p>承認制の受付確定後に人数を増やす場合は、再承認が必要です。変更後は最終参加確認をやり直してください。全員の取消はマイページから行えます。</p><button class="button primary">人数変更を送信する</button>'
            body += operation_form(endpoint + "/count", fields, app["operation_revision"])
    body += '</section>'
    return event_page(title, body, EVENT_OPERATIONS_SCRIPT)


def render_event_contact_html(event_id, user, peer_user_id=""):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    with connect() as conn:
        event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
        if not event:
            raise ValueError("募集が見つかりません")
        owner = event["organizer_user_id"] == user["user_id"]
        prefix = "/events/" + quote(event_id)
        body = event_home_navigation("質問・連絡") + '<section class="form-shell"><h1>質問・連絡</h1><h2>' + html.escape(event["title"]) + f'</h2><p><a href="{prefix}">募集詳細へ戻る</a> / <a href="/mypage">マイページ</a></p>'
        if owner and not peer_user_id:
            peers = conn.execute("""select u.user_id,u.display_name,max(m.created_at) as last_message,
                       sum(case when m.recipient_user_id=? and m.read_at is null then 1 else 0 end) as unread
                  from event_messages m join user_accounts u on u.user_id=case when m.sender_user_id=? then m.recipient_user_id else m.sender_user_id end
                  where m.event_id=? and (m.sender_user_id=? or m.recipient_user_id=?)
                  group by u.user_id order by last_message desc limit 200""", (user["user_id"], user["user_id"], event_id, user["user_id"], user["user_id"])).fetchall()
            body += '<p>質問・連絡は、主催者と送信者本人だけに表示されます。</p>'
            for peer in peers:
                body += f'<article class="app-row"><span>{html.escape(peer["display_name"] or "利用者")} / 未読 {peer["unread"]}件</span><a class="button" href="{prefix}/contact?{urlencode({"peer_user_id": peer["user_id"]})}">連絡を開く</a></article>'
            return event_page("質問・連絡", body + ('' if peers else '<p class="empty">質問・連絡はまだありません。</p>') + '</section>')
    messages = event_messages_for_user(event_id, user, peer_user_id)
    body += '<p>このやり取りは一般公開されません。質問の送信だけでは参加申込にはなりません。</p><div class="message-log">'
    for message in messages:
        body += '<div class="message"><strong>' + html.escape(message["sender_name"] or "利用者") + '</strong><small> ' + format_event_datetime(message["created_at"]) + '</small><p style="white-space:pre-wrap">' + html.escape(message["body"]) + '</p></div>'
    body += ('' if messages else '<p>まだメッセージはありません。</p>') + '</div>'
    fields = f'<input type="hidden" name="recipient_user_id" value="{html.escape(peer_user_id, quote=True) if owner else ""}"><div class="field"><label for="body">メッセージ</label><textarea id="body" name="body" maxlength="2000" required></textarea></div><button class="button primary">送信する</button>'
    body += operation_form('/api' + prefix + '/messages', fields) + '</section>'
    return event_page("質問・連絡", body, EVENT_OPERATIONS_SCRIPT)


def render_circles_html():
    initial_sports = SPORTS
    try:
        initial_summary = summary("university")
        initial_circles = search_circles({"audience": ["university"]}, limit=24)
        initial_sports = sport_options("university")
        stat_values = {
            "__SSR_PREFECTURE_COUNT__": str(initial_summary["prefectures"]),
            "__SSR_UNIVERSITY_COUNT__": str(initial_summary["universities"]),
            "__SSR_CIRCLE_COUNT__": str(initial_summary["circles"]),
            "__SSR_VERIFIED_COUNT__": str(initial_summary["verified_circles"]),
        }
        initial_rows = ssr_circle_rows(initial_circles)
        initial_circles_json = script_json(initial_circles)
        initial_summary_json = script_json(initial_summary)
    except Exception as exc:
        log(f"SSR circle list failed: {type(exc).__name__}: {exc}")
        stat_values = {
            "__SSR_PREFECTURE_COUNT__": ssr_error_value(),
            "__SSR_UNIVERSITY_COUNT__": ssr_error_value(),
            "__SSR_CIRCLE_COUNT__": ssr_error_value(),
            "__SSR_VERIFIED_COUNT__": ssr_error_value(),
        }
        initial_rows = '<tr><td colspan="7" class="ssr-error">データを取得できませんでした</td></tr>'
        initial_circles_json = "null"
        initial_summary_json = "null"

    page = (
        with_adsense(PUBLIC_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__CONTACT_EMAIL__", CONTACT_EMAIL)
        .replace("__SPORTS__", script_json(initial_sports))
        .replace("__REGIONS__", script_json(region_options()))
        .replace("__PREFS__", script_json(PREFECTURES))
        .replace("__INITIAL_CIRCLE_ROWS__", initial_rows)
        .replace("__INITIAL_CIRCLES__", initial_circles_json)
        .replace("__INITIAL_CIRCLE_SUMMARY__", initial_summary_json)
    )
    for placeholder, value in stat_values.items():
        page = page.replace(placeholder, value)
    return page.encode("utf-8")


def render_social_circles_html():
    return (
        with_adsense(SOCIAL_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__CONTACT_EMAIL__", CONTACT_EMAIL)
        .replace("__SPORTS__", json.dumps(sport_options("social"), ensure_ascii=False))
        .replace("__REGIONS__", json.dumps(region_options(), ensure_ascii=False))
        .replace("__PREFS__", json.dumps(PREFECTURES, ensure_ascii=False))
        .encode("utf-8")
    )


def render_social_html():
    # MATCH_HTML has SSR placeholders shared with the university top page. The
    # social page needs its own scoped values before its browser-side filters run.
    initial_sports = SPORTS
    try:
        initial_summary = social_summary()
        initial_sports = sport_options("social")
        stat_values = {
            "__SSR_UNIVERSITY_COUNT__": str(initial_summary["universities"]),
            "__SSR_CIRCLE_COUNT__": str(initial_summary["circles"]),
            "__SSR_VERIFIED_COUNT__": str(initial_summary["verified_circles"]),
            "__SSR_MATCH_COUNT__": str(initial_summary["match_posts"]),
        }
        initial_summary_json = script_json(initial_summary)
    except Exception as exc:
        log(f"SSR social stats failed: {type(exc).__name__}: {exc}")
        stat_values = {
            "__SSR_UNIVERSITY_COUNT__": ssr_error_value(),
            "__SSR_CIRCLE_COUNT__": ssr_error_value(),
            "__SSR_VERIFIED_COUNT__": ssr_error_value(),
            "__SSR_MATCH_COUNT__": ssr_error_value(),
        }
        initial_summary_json = "null"

    social_db_panel = """
    <section id="social-db" class="section panel"><div class="panel-head"><div><h2>社会人サークルDB</h2><p>大学サークルDBと同じ検索・絞り込み画面で、活動地域、競技、掲載状態、出典を確認できます。</p></div><a class="button light" href="/social/circles">社会人サークルDBを見る</a></div></section>
    """
    social_css = """
    """
    social_js = """
    function renderSports(){ $("sportGrid").innerHTML=popularSports.map(s=>`<a class="sport-card" style="--tone:${esc(s.color)}" data-code="${esc(s.code)}" href="/social/sports?sport=${encodeURIComponent(s.name)}"><span class="sport-visual"><img src="/assets/sports/${esc(s.image)}?v=20260706v1" alt=""></span><span class="sport-copy"><strong>${esc(s.name)}</strong><em>${esc(s.label)}</em></span><b>仲間を探す</b></a>`).join("") }
    function renderRegions(regionData){$("mapCircleCount").textContent=regionData.reduce((sum,r)=>sum+(r.circle_count||0),0); $("regionGrid").innerHTML=regions.map(r=>{const stat=regionData.find(item=>item.value===r.value)||{}; return `<a class="map-region" href="/social?region=${encodeURIComponent(r.value)}#matches"><strong>${esc(r.label)}</strong><span>募集 ${stat.match_count||0}件</span><span>DB ${stat.circle_count||0}件</span></a>`}).join("")}
    function selectedRegion(){return regions.find(r=>r.value===$("regionFilter").value)}
    function prefValues(){return selectedRegion()?.prefectures || prefs}
    function syncPrefOptions(){const current=$("prefFilter").value; fillSelect($("prefFilter"),prefValues(),selectedRegion()?`${selectedRegion().label}すべて`:"全都道府県"); if(prefValues().includes(current)) $("prefFilter").value=current}
    function currentQuery(){const qs=new URLSearchParams({audience:"social",q:$("q").value,prefecture:$("prefFilter").value,sport:$("sportFilter").value}); if($("regionFilter").value) qs.set("region",$("regionFilter").value); return qs}
    async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
    function updateStats(stats,matches){$("uniCount").textContent=stats.prefectures; $("circleCount").textContent=stats.circles; $("verifiedCount").textContent=stats.verified_circles; $("matchCount").textContent=matches.length}
    function matchesFilter(m){const q=$("q").value.trim().toLowerCase(); const sport=$("sportFilter").value.trim().toLowerCase(); const blob=[m.circle_name,m.sport_category,m.prefecture,m.place,m.conditions,m.level_label].join(" ").toLowerCase(); if(q && !blob.includes(q))return false; if($("typeFilter").value && m.match_type!==$("typeFilter").value)return false; if(sport && !String(m.sport_category||"").toLowerCase().includes(sport))return false; if($("prefFilter").value && m.prefecture!==$("prefFilter").value)return false; return true}
    function sortMatches(rows){const v=$("sortFilter").value; return rows.slice().sort((a,b)=>{if(v==="new")return String(b.created_at||"").localeCompare(String(a.created_at||"")); if(v==="university")return String(a.circle_name||"").localeCompare(String(b.circle_name||""),"ja"); if(v==="sport")return String(a.sport_category||"").localeCompare(String(b.sport_category||""),"ja"); return String(a.scheduled_at||"9999").localeCompare(String(b.scheduled_at||"9999"))})}
    function card(m){return `<article class="match-card"><div class="badges"><span class="badge open">${esc(m.status||"open")}</span><span class="badge type">${esc(m.match_type)}</span><span class="badge">${esc(m.sport_category||"競技未設定")}</span></div><h3>${esc(m.circle_name)}</h3><div class="meta"><span>${esc(m.prefecture||"地域未設定")} / ${esc(m.place||"場所未定")}</span><span>${esc(m.scheduled_at||"日時未定")}</span><span>${esc(m.level_label||"レベル未設定")}</span></div><p class="tagline">${esc(m.conditions||"条件は登録後に調整します。")}</p></article>`}
    async function refresh(){const qs=currentQuery(); $("dbBridge").href="/social/circles?"+qs; const [all,stats,regionData]=await Promise.all([api("/api/matches?"+qs),api("/api/circle-stats?"+qs),api("/api/region-counts?audience=social")]); const data=sortMatches(all.filter(matchesFilter)); renderRegions(regionData); updateStats(stats,data); $("matchList").innerHTML=data.map(card).join("") || `<div class="empty">現在公開中の募集はありません。同じ条件の社会人サークル候補は ${stats.circles} 件あります。下のDBから候補団体を確認できます。</div>`}
    function updateCoverageNotice(){$("coverageNotice").style.display="none"}
    """
    html = MATCH_HTML
    html = html.replace("<title>__SITE_NAME__ | 大学サークルの練習試合・交流募集</title>", "<title>社会人サークル | __SITE_NAME__</title>")
    html = html.replace('<nav class="nav"><a href="/social">社会人はこちら</a><a class="signup-user" href="/representative">団体代表者の方へ</a></nav>', '<nav class="nav"><a href="/">大学サークルはこちら</a><a class="signup-user" href="/representative?type=social">団体代表者の方へ</a></nav>')
    html = html.replace(
        '<img src="/assets/hero-court.png" alt="屋外コートで交流する大学生グループ">',
        '<img src="/assets/hero-social-adults.png" alt="仕事帰りに交流する社会人スポーツ仲間">',
    )
    html = html.replace("Practice Match / Circle Meetup", "Social Circle / Member Recruiting")
    html = html.replace("練習相手も、仲間も、ここで見つかる。", "社会人のスポーツ仲間も、ここで見つかる。")
    html = html.replace("Circle Matchは、大学サークル・部活動の練習試合、合同練習、助っ人募集、交流イベントをつなぐマッチングサービスです。", "Circle Matchは、社会人スポーツサークルのメンバー募集、練習試合、合同練習、交流イベントをつなぐマッチングサービスです。")
    html = html.replace('href="#matches">募集中はこちら</a><a class="button primary hero-cta" href="/representative?intent=post-match">募集を出す</a>', 'href="#matches">メンバー募集を見る</a><a class="button primary hero-cta" href="/representative?type=social&intent=post-match">サークル員を募集する</a>')
    html = html.replace("<span>対象大学</span>", "<span>対象地域</span>")
    html = html.replace("<span>検証済み/申請済み</span>", "<span>公開掲載・代表申請</span>")
    html = html.replace("<span>募集中</span>", "<span>メンバー・交流募集中</span>")
    html = html.replace('<h2>募集掲示板</h2><p>地域、都道府県、競技、大学名、団体名で絞り込めます。募集中が少ない時は、その条件のDB候補へ広げられます。</p>', '<h2>メンバー募集・交流掲示板</h2><p>地域、都道府県、競技、団体名、活動場所で絞り込めます。募集中が少ない時は、その条件の社会人サークルDB候補へ広げられます。</p>')
    html = html.replace('<a class="button light" href="/social">社会人サークルを見る</a>', '<a class="button light" href="/social/circles">社会人サークルDBを見る</a>')
    html = html.replace('placeholder="大学名・団体名・場所で検索"', 'placeholder="団体名・競技・活動地域で検索"')
    html = html.replace('<a id="dbBridge" href="/circles">同じ条件でサークルDBを見る</a>', '<a id="dbBridge" href="/social/circles">同じ条件で社会人サークルDBを見る</a>')
    html = html.replace("競技を押すと、サークルDBと交流募集を同時に確認できます。", "競技を押すと、社会人サークルDBとメンバー・交流募集を同時に確認できます。")
    html = html.replace("サークルDBで候補を広げる", "社会人サークルDBで候補を広げる")
    html = html.replace('<a href="/circles">社会人サークルDBで候補を広げる</a>', '<a href="/social/circles">社会人サークルDBで候補を広げる</a>')
    html = html.replace("地図上の地域を押すと、募集掲示板とDB候補をその地域で絞り込めます。", "地図上の地域を押すと、社会人の募集掲示板とDB候補をその地域で絞り込めます。")
    html = html.replace('<strong id="mapCircleCount">0</strong>件の大学サークル候補から地域で探す', '<strong id="mapCircleCount">0</strong>件の社会人サークル候補から地域で探す')
    html = html.replace('<a class="admin-link" href="/circles">サークルDB</a>', '<a class="admin-link" href="/social/circles">社会人サークルDB</a>')
    html = html.replace("  </main>\n  <footer>", social_db_panel + "  </main>\n  <footer>")
    html = html.replace("  </style>", social_css + "  </style>", 1)
    start = html.index("    function renderSports(){")
    end = html.index("    function updateCoverageNotice()", start)
    replacement_end = html.index("\n", html.index("}", end)) + 1
    html = html[:start] + social_js + html[replacement_end:]
    page = (
        with_adsense(html)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__CONTACT_EMAIL__", CONTACT_EMAIL)
        .replace("__SPORTS__", script_json(initial_sports))
        .replace("__REGIONS__", json.dumps(region_options(), ensure_ascii=False))
        .replace("__POPULAR_SPORTS__", json.dumps([
            {"name": name, "label": label, "code": code, "color": color, "image": image}
            for name, label, code, color, image in POPULAR_SPORTS
        ], ensure_ascii=False))
        .replace("__PREFS__", json.dumps(PREFECTURES, ensure_ascii=False))
    )
    for placeholder, value in stat_values.items():
        page = page.replace(placeholder, value)
    return page.replace("__INITIAL_SUMMARY__", initial_summary_json).encode("utf-8")


def render_signin_html(return_to="/"):
    return_to = safe_return_path(return_to)
    destination = urlparse(return_to)
    is_hosting = destination.path == "/events/new"
    filters = {key: values[0] for key, values in parse_qs(destination.query).items()
               if key in {"sport", "region", "prefecture", "event_type", "participation", "date_from", "date_to", "q"}}
    find_url = "/events" + ("?" + urlencode(filters) if filters else "")
    # Back must stay on a public page, not repeat the login gate or OAuth flow.
    back_url = "/"
    if is_hosting:
        back_url = find_url
    elif re.fullmatch(r"/events/[^/]+/apply", destination.path):
        back_url = destination.path.removesuffix("/apply")
    elif destination.path in {"/", "/events", "/circles", "/social", "/social/circles", "/sports", "/regions"}:
        back_url = return_to
    heading = "募集掲載の前に" if is_hosting else "ログインして、参加・主催を始める。"
    lead = "ログインすると、基本情報の登録が簡単になります。" if is_hosting else ""
    description = (
        "主催者名・連絡先にはアカウント情報や前回の募集情報を入力済みにします。"
        "ログイン後は募集の作成画面へ進みます。初めての方も、Googleまたはメールアドレスで登録できます。"
        if is_hosting else
        "大会・イベントの閲覧はログイン不要です。申込、募集掲載、受付管理を行う時だけログインしてください。同じアカウントで参加と主催の両方ができます。"
    )
    return (
        with_adsense(SIGNIN_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__SIGNIN_INTRO_CLASS__", "hosting-intro" if is_hosting else "")
        .replace("__SIGNIN_LEAD__", f'<p class="signin-lead">{html.escape(lead)}</p>' if lead else "")
        .replace("__SIGNIN_HEADING__", html.escape(heading))
        .replace("__SIGNIN_DESCRIPTION__", html.escape(description))
        .replace("__SIGNIN_BACK_URL__", html.escape(back_url, quote=True))
        .replace("__SIGNIN_FIND_URL__", html.escape(find_url, quote=True))
        .replace("__SUPABASE_URL__", json.dumps(SUPABASE_URL))
        .replace("__SUPABASE_ANON_KEY__", json.dumps(SUPABASE_ANON_KEY))
        .replace("__AUTH_READY__", "true" if supabase_auth_enabled() else "false")
        .replace("__EMAIL_AUTH_READY__", "true" if supabase_auth_enabled() and EMAIL_AUTH_ENABLED else "false")
        .replace("__RETURN_TO__", script_json(return_to))
        .encode("utf-8")
    )


def render_sport_html(sport):
    sport = sport if sport in sport_options("university") else "野球"
    sport_image = next((image for name, _label, _code, _color, image in POPULAR_SPORTS if name == sport), "other.png")
    return (
        with_adsense(SPORT_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__SPORT__", sport)
        .replace("__SPORT_IMAGE__", f"/assets/sports/{sport_image}?v=20260713v1")
        .replace("__CONTACT_EMAIL__", CONTACT_EMAIL)
        .replace("__SPORT_JSON__", json.dumps(sport, ensure_ascii=False))
        .encode("utf-8")
    )


def render_social_sport_html(sport):
    sport = sport if sport in sport_options("social") else "野球"
    sport_image = next((image for name, _label, _code, _color, image in POPULAR_SPORTS if name == sport), "other.png")
    html = SPORT_HTML
    html = html.replace("<title>__SPORT__ | __SITE_NAME__</title>", "<title>__SPORT__の社会人サークル | __SITE_NAME__</title>")
    html = html.replace(
        '<header><div class="top"><a class="brand" href="/">__SITE_NAME__</a><nav class="nav"><a class="find-link" href="/">トップへ戻る</a><a href="/representative?intent=post-match">募集を出す</a><a href="/representative">掲載情報を整える</a></nav></div></header>',
        '<header><div class="top"><a class="brand" href="/social">__SITE_NAME__</a><nav class="nav"><a class="find-link" href="/social">社会人トップへ戻る</a><a href="/representative?type=social&intent=post-match">サークル員を募集する</a><a href="/representative?type=social">掲載情報を整える</a></nav></div></header>',
    )
    html = html.replace("__SPORT__の相手を探す", "__SPORT__の仲間を探す")
    html = html.replace("__SPORT__サークルDBと練習試合・交流募集をまとめて確認できます。", "__SPORT__の社会人サークルDBとメンバー・交流募集をまとめて確認できます。")
    html = html.replace('href="/representative?intent=post-match">募集を出す</a>', 'href="/representative?type=social&intent=post-match">サークル員を募集する</a>')
    html = html.replace("<span>交流募集</span>", "<span>メンバー・交流募集</span>")
    html = html.replace("<span>対象都道府県</span>", "<span>対象地域</span>")
    html = html.replace('<h2>地域別の交流募集</h2>', '<h2>地域別のメンバー・交流募集</h2>')
    html = html.replace("__SPORT__サークルDB", "__SPORT__ 社会人サークルDB")
    html = html.replace('data-filter="university">大学', 'data-filter="university">活動地域')
    html = html.replace('const labels={university:"大学",circle:"団体名",type:"種別",source:"出典"}', 'const labels={university:"活動地域",circle:"団体名",type:"種別",source:"出典"}')
    html = html.replace('return key==="university"?`${c.university_name||""} ${c.prefecture||""} ${c.city||""}`', 'return key==="university"?`${c.prefecture||""} ${c.city||""} ${c.activity_area||""}`')
    html = html.replace('return String(a.university_name||"").localeCompare(String(b.university_name||""),"ja")', 'return String(rowValue(a,"university")).localeCompare(String(rowValue(b,"university")),"ja")')
    html = html.replace('<tr><td><span class="name">${esc(c.university_name)}</span><span class="sub">${esc(c.prefecture)} ${esc(c.city||"")}</span></td>', '<tr><td><span class="name">${esc(c.prefecture||"地域未設定")}</span><span class="sub">${esc(c.city||c.activity_area||"")}</span></td>')
    html = html.replace('`/api/sport_overview?sport=${encodeURIComponent(sport)}${regionQs}${prefQs}`', '`/api/sport_overview?sport=${encodeURIComponent(sport)}&audience=social${regionQs}${prefQs}`')
    html = html.replace('<a class="admin-link" href="/circles">サークルDBを見る</a>', '<a class="admin-link" href="/social/circles">社会人サークルDBを見る</a>')
    return (
        with_adsense(html)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__SPORT__", sport)
        .replace("__SPORT_IMAGE__", f"/assets/sports/{sport_image}?v=20260713v1")
        .replace("__CONTACT_EMAIL__", CONTACT_EMAIL)
        .replace("__SPORT_JSON__", json.dumps(sport, ensure_ascii=False))
        .encode("utf-8")
    )


def render_region_html(region):
    region = region if region in REGION_GROUPS else "kanto"
    sport_images = {name: image for name, _label, _code, _color, image in POPULAR_SPORTS}
    return (
        with_adsense(REGION_HTML)
        .replace("__SITE_NAME__", SITE_NAME)
        .replace("__REGION_LABEL__", REGION_GROUPS[region]["label"])
        .replace("__REGION_LABEL_JSON__", json.dumps(REGION_GROUPS[region]["label"], ensure_ascii=False))
        .replace("__SPORT_IMAGES__", json.dumps(sport_images, ensure_ascii=False))
        .replace("__CONTACT_EMAIL__", CONTACT_EMAIL)
        .replace("__REGION_NOTICE_DISPLAY__", "none" if region == "kanto" else "block")
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
        .replace("__PREFS__", json.dumps(PREFECTURES, ensure_ascii=False))
        .encode("utf-8")
    )


def render_circle_profile_html(profile_slug):
    with connect() as conn:
        row = conn.execute(
            """
            select p.*, c.circle_id, c.circle_name, c.organization_type, c.sport_category, c.verification_status,
              exists(select 1 from circle_claims cc where cc.circle_id=c.circle_id and cc.university_email_verified=1) as representative_email_verified,
              u.university_name, u.prefecture, u.city
            from circle_public_profiles p
            join circles c on c.circle_id=p.circle_id
            join universities u on u.university_id=c.university_id
            where p.profile_slug=? and p.is_published=1
              and not exists (select 1 from circle_listing_reviews lr where lr.circle_id=c.circle_id and lr.review_status='pending')
            """,
            (profile_slug,),
        ).fetchone()
        hosted_events = []
        if row:
            hosted_sql, hosted_args = event_public_select(
                "e.linked_circle_id=? and e.status in ('published','closed','cancelled')",
                [row["circle_id"]],
            )
            hosted_sql += " order by e.starts_at asc limit 12"
            hosted_events = [dict(item) for item in conn.execute(hosted_sql, hosted_args).fetchall()]
    if not row:
        return None
    data = dict(row)
    def clean(value, fallback="未入力"):
        value = (value or "").strip()
        return html.escape(value if value else fallback)
    sport = data.get("sport_category") or "その他"
    hosted_events_section = (
        '<section class="panel"><h2>この団体が主催する大会・イベント</h2><div class="event-grid">'
        + render_event_cards(hosted_events)
        + "</div></section>"
    )
    contact_email = (data.get("public_contact_email") or "").strip()
    contact_section = ""
    if contact_email and data.get("public_contact_consent"):
        subject = f"【{sport}の交流のご相談】Circle Matchを見てご連絡しました"
        invite_template = "\n".join([
            f"{data.get('circle_name', 'ご担当者')} ご担当者様",
            "",
            "はじめまして。Circle Matchで活動情報を拝見し、ご連絡しました。",
            "",
            "【こちらの団体名】",
            "【希望する内容】練習試合 / 合同練習 / メンバー交流 など",
            "【希望時期・場所】",
            "【補足】",
            "",
            "ご都合が合いましたら、ぜひ詳細をご相談できれば幸いです。",
            "",
            "Circle Match（https://circle-match.jp/）を通じてご連絡しました。",
        ])
        mailto_url = f"mailto:{quote(contact_email, safe='@')}?{urlencode({'subject': subject, 'body': invite_template})}"
        contact_section = f'''<section class="panel contact-panel"><h2>連絡を取るならこちら</h2><p class="contact-email">{html.escape(contact_email)}</p><p>メール作成時は、下の文面をそのまま使うか、必要な箇所を埋めてから送れます。</p><div class="actions"><a class="button primary" href="{html.escape(mailto_url, quote=True)}">メールを作成</a><button class="button" type="button" id="copyInviteTemplate">テンプレートをコピー</button></div><textarea id="inviteTemplate" class="invite-template" readonly>{html.escape(invite_template)}</textarea></section><script>document.getElementById("copyInviteTemplate")?.addEventListener("click",async()=>{{const button=document.getElementById("copyInviteTemplate");try{{await navigator.clipboard.writeText(document.getElementById("inviteTemplate").value);button.textContent="コピーしました"}}catch(_error){{document.getElementById("inviteTemplate").select();document.execCommand("copy");button.textContent="コピーしました"}}}});</script>'''
    verification_status = data.get("verification_status")
    if data.get("representative_email_verified"):
        verified_label = "代表者メール確認済み" if data.get("organization_type") == SOCIAL_AUDIENCE_TYPE else "大学メール確認済み"
        representative_status_badge = f'<span class="badge ok">{verified_label}</span>'
    elif verification_status == "university_verified":
        representative_status_badge = '<span class="badge ok">大学公式情報掲載</span>'
    elif verification_status == "admin_verified":
        representative_status_badge = '<span class="badge ok">公開情報掲載</span>'
    elif verification_status == "claimed":
        representative_status_badge = '<span class="badge">代表申請受付</span>'
    else:
        representative_status_badge = '<span class="badge">未確認</span>'
    contact_section = hosted_events_section + contact_section
    page = (
        with_adsense(CIRCLE_PROFILE_HTML)
        .replace("__SITE_NAME__", html.escape(SITE_NAME))
        .replace("__UNIVERSITY_NAME__", clean(data.get("university_name")))
        .replace("__SPORT__", clean(sport))
        .replace("__SPORT_ENC__", quote(sport))
        .replace("__CIRCLE_NAME__", clean(data.get("circle_name")))
        .replace("__CATCH_COPY__", clean(data.get("catch_copy"), f"{data.get('circle_name', 'サークル')}の活動紹介ページです。"))
        .replace("__REPRESENTATIVE_STATUS_BADGE__", representative_status_badge)
        .replace("__ORG_TYPE__", clean(data.get("organization_type")))
        .replace("__PREFECTURE__", clean(data.get("prefecture")))
        .replace("__MEMBER_COUNT__", clean(data.get("member_count")))
        .replace("__ATMOSPHERE__", clean(data.get("atmosphere")))
        .replace("__EXPERIENCE_RATIO__", clean(data.get("experience_ratio")))
        .replace("__PRACTICE_FREQUENCY__", clean(data.get("practice_frequency")))
        .replace("__INTRODUCTION__", clean(data.get("introduction"), "代表者からの紹介文はまだ登録されていません。"))
        .replace("__ACTIVITY_PLACE__", clean(data.get("activity_place")))
        .replace("__REPRESENTATIVE_COMMENT__", clean(data.get("representative_comment"), "代表者コメントはまだ登録されていません。"))
        .replace("__CONTACT_SECTION__", contact_section)
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
    paths = ["/", "/representative", "/circles", "/social", "/guides", "/operator", "/privacy", "/terms", "/about-data", "/contact"]
    paths.extend([f"/guides/{slug}" for slug in GUIDE_PAGES.keys()])
    paths.extend(["/sports?" + urlencode({"sport": name}) for name, _, _, _, _ in POPULAR_SPORTS])
    paths.extend(["/regions?" + urlencode({"region": key}) for key in REGION_GROUPS.keys()])
    try:
        with connect() as conn:
            event_ids = conn.execute(
                "select event_id from event_posts where status='published' and starts_at>=datetime('now','localtime') order by starts_at limit 5000"
            ).fetchall()
        paths.extend([f"/events/{quote(str(row['event_id']))}" for row in event_ids])
    except Exception as exc:
        log(f"event sitemap query failed: {type(exc).__name__}: {exc}")
    urls = "\n".join(
        f"  <url><loc>{root}{path}</loc></url>"
        for path in paths
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
""".encode("utf-8")


_CIRCLE_SCHEMA_LOCK = threading.Lock()
_CIRCLE_SCHEMA_READY = False
_CIRCLE_RUNTIME_COLUMNS = (
    ("organization_type", "text not null default '不明'"),
    # Older persistent Render volumes predate the fields below.  These are
    # public listing fields, so treating legacy rows as published preserves the
    # existing database instead of making it disappear after a deploy.
    ("public_status", "text not null default 'published'"),
    ("last_checked_at", "text"),
    ("sns_url", "text"),
    ("owner_notes", "text"),
)
STARTUP_MAINTENANCE_REVISION = "2026-08-31.1"
REFERENCE_DATA_REVISION = "2026-08-12.1"


@contextmanager
def connect():
    """Open a SQLite connection that is always closed after each request.

    ``sqlite3.Connection`` supports ``with`` but its native context manager only
    commits or rolls back; it does not close the connection.  The public pages
    open multiple short-lived read connections, so leaving them open made the
    process retain SQLite's native memory until Render killed the instance.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    try:
        ensure_runtime_circle_schema(conn)
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()


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
    ("ピックルボール", ["ピックルボール", "ピックル", "Pickleball", "pickleball", "pickle ball"]),
    ("アメリカンフットボール", ["アメリカンフットボール", "アメフト", "フットボールクラブ", "タッチフットボール"]),
    ("ソフトテニス", ["ソフトテニス"]),
    ("テニス", ["テニス", "Tennis"]),
    ("サッカー・フットサル", ["サッカー", "蹴球", "フットサル", "FC.", "FC "]),
    ("バスケットボール", ["バスケットボール", "バスケ", "籠球", "3×3", "Basketball", "BA"]),
    ("バレーボール", ["バレーボール", "バレー", "排球", "Volleyball", "Volley"]),
    ("バドミントン", ["バドミントン", "Badminton"]),
    ("野球", ["野球", "ベースボール", "Baseball", "キャッチボール", "ホークス", "ヤンキース"]),
    ("ラグビー", ["ラグビー", "Rugby"]),
    ("ラクロス", ["ラクロス", "Lacrosse"]),
    ("卓球", ["卓球"]),
    ("水泳", ["水泳", "水球"]),
    ("ランニング", ["ランニング", "マラソン", "ジョギング", "トレイルラン", "ロードレース"]),
    ("陸上競技", ["陸上", "駅伝"]),
    ("ハンドボール", ["ハンドボール"]),
    ("ホッケー", ["ホッケー"]),
    ("ゴルフ", ["ゴルフ"]),
    ("スキー", ["スキー", "Ski"]),
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
    ("フライングディスク", ["フライングディスク", "フリスビー"]),
    ("ボディビル", ["ボディビル", "バーベル"]),
    ("釣り", ["釣り"]),
    ("アウトドア", ["アウトドア", "ワンダーフォーゲル", "探検", "山岳", "ハイキング", "野外活動", "ユースホステル", "ラフティング", "山友会"]),
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
    ("ダンス", ["ダンス", "舞踊", "フラサークル", "フラメンコ", "バレエ", "パフォーマンス", "舞style"]),
    ("音楽", ["音楽", "グリー", "交響楽", "管弦楽", "吹奏楽", "軽音", "フォークソング", "ロック", "マンドリン", "邦楽", "合唱", "オーケストラ", "ギター", "ピアノ", "ブラスバンド", "箏曲", "JAZZ", "ジャズ", "アカペラ", "アコギ", "エレクトーン", "和太鼓", "Voice", "Song", "MUSIC", "Music", "聖歌隊", "ハンドベル"]),
    ("写真", ["写真"]),
    ("美術", ["美術", "陶芸", "絵画", "Painting", "デザイン", "Design"]),
    ("茶道", ["茶道"]),
    ("書道", ["書道"]),
    ("将棋", ["将棋"]),
    ("囲碁", ["囲碁"]),
    ("漫画", ["漫画", "アニメ", "Comics", "ラブライブ", "Voice&Animation"]),
    ("映画", ["映画"]),
    ("演劇", ["演劇", "劇団", "ミュージカル", "人形劇", "特撮"]),
    ("文芸", ["文芸", "SF研究", "ミステリ", "短歌", "PENクラブ", "創作"]),
    ("放送", ["放送", "アナウンス"]),
    ("鉄道", ["鉄道"]),
    ("天文", ["天文"]),
    ("歴史", ["歴史", "戦史"]),
    ("考古学", ["考古"]),
    ("電子計算機", ["電子計算機", "コンピュー", "プログラミング", "アプリ開発", "AI研究", "Minecraft"]),
    ("ボードゲーム", ["ボードゲーム", "オセロ"]),
    ("TRPG", ["TRPG"]),
    ("サバイバルゲーム", ["サバイバルゲーム"]),
    ("ゲーム", ["スプラトゥーン", "ポケモン", "スマブラ", "デュエルマスターズ", "レゴ", "ゲーム"]),
    ("クイズ", ["クイズ"]),
    ("マジック", ["奇術", "マジック"]),
    ("演芸", ["お笑い", "落研"]),
    ("手芸", ["手芸", "着物", "古着"]),
    ("アイドル研究", ["アイドル研究"]),
    ("マーケティング", ["マーケティング"]),
    ("宗教", ["聖書", "キリスト教"]),
    ("教育", ["こども園", "教育", "てらこや"]),
    ("カメラ", ["カメラ"]),
    ("手話", ["手話"]),
    ("プロレス", ["プロレス"]),
    ("モルック", ["モルック"]),
    ("ボッチャ", ["ボッチャ"]),
    ("競馬", ["競馬"]),
    ("ダーツ", ["ダーツ"]),
    ("バトントワリング", ["バトントワリング", "カラーガード"]),
    ("ディズニー研究", ["ディズニー研究"]),
    ("生物", ["生物", "野生生物"]),
    ("落語", ["落語"]),
    ("華道", ["華道"]),
    ("能楽", ["能楽", "狂言", "観世会"]),
    ("競技かるた", ["競技かるた", "百人一首"]),
    ("料理", ["料理"]),
    ("法律", ["法律", "法学"]),
    ("会計", ["会計"]),
    ("政治", ["政治"]),
    ("経済", ["経済"]),
    ("地理", ["地理"]),
    ("国際交流", ["国際", "模擬国連", "韓国語", "ハングル", "ラテンアメリカ", "E.S.S", "E・S・S", "ESS", "English", "英語", "留学生"]),
    ("ボランティア", ["ボランティア", "IVUSA", "STUDY FOR TWO", "グッドサマリタン", "clown"]),
    ("地域活動", ["地域交流", "ご当地", "銭湯", "珈琲", "猫の会", "みつばち", "プロジェクト"]),
    ("委員会", ["実行委員会", "広報委員会", "懇談会", "総務委員会", "卒業アルバム委員会"]),
    ("自治会", ["自治会", "中央事務局", "常任委員会", "学術本部", "学友会", "学芸総部本部", "学生会執行部"]),
]

INVALID_CIRCLE_EXACT_NAMES = {
    "本部", "体育会本部", "クラブ活動", "クラブ＆サークル", "サークル・同好会", "その他の団体",
    "学生団体", "学術団体", "上部団体", "中央執行委員会", "強化クラブ", "関連団体",
    "文化団体連合会", "文化系クラブ", "文化系団体", "校友会", "学生校友会", "体育施設・サークル共用施設",
    "戸塚グラウンド・ラフォーレ倶楽部", "サークル施設予約システム",
    "委員会・クラブ・サークル・その他学内活動団体",
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
    "団体見学申込用紙",
    "参加団体ポスター",
    "団体見学",
    "学生団体出演依頼書",
    "出演依頼書",
    "委員会挨拶",
    "学生支援センター",
    "相談窓口",
    "特別使用申込書",
    "使用申込書",
    "販売報告書",
    "チケット販売願",
    "助成金",
    "受付に関する方針",
    "外部団体を活用",
    "外部団体による",
    "転部・転科",
    "勝敗表",
    "ダウンロード",
    "団体情報シート",
    "Primary Division",
    "幼稚部",
    "キャンパス見学",
    "認定こども園",
    "課外学習会",
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
    "申込用紙",
    "申込書",
    "販売報告書",
    "助成金",
    "特別講演会",
    "受付に関する方針",
    "参加団体ポスター",
    "団体見学",
    "出演依頼書",
    "委員会挨拶",
    "学生支援センター",
    "相談窓口",
    "外部団体を活用",
    "外部団体による",
    "転部・転科",
    "勝敗表",
    "ダウンロード",
    "団体情報シート",
    "Primary Division",
    "幼稚部",
    "キャンパス見学",
    "認定こども園",
    "課外学習会",
]
INVALID_CIRCLE_EVENT_WORDS = [
    "大会", "選手権", "リーグ戦", "トーナメント", "決定戦", "試合結果", "試合予定",
    "戦績", "順位", "結果", "速報", "場所", "活動場所：", "活動日：", "活動時間：",
]
INVALID_SOURCE_PATH_PARTS = [
    "/sports/result", "/result", "/results", "/news", "/event", "/events", "/schedule", "/calendar",
]
INVALID_SOURCE_ALWAYS_PARTS = [
    "tamagawa.jp/academy/",
]
INVALID_CIRCLE_TITLE_PATTERNS = [
    r"(TOP|一覧|こちら|を見る|について|もっと知る|ご確認ください)",
    r"(届|補助金|住所変更|研究データ|研究インテグリティ|倫理委員会|認定証|指針|セレクション|再開|レベル\d)",
    r"(紹介動画|活動場所[:：]|活動日[:：]|団体旅行|学部・大学院|付属校|練習しています|活動しています|チケット販売報告書|チケット販売願)",
    r"サークル・部会活動",
]

DESCRIPTIVE_PARENTHETICAL_WORDS = [
    "活動", "開催", "運営", "制作", "演奏", "撮影", "講習", "練習", "企画",
    "研究", "発表", "展示", "交流", "支援", "参加", "出場",
]


def infer_sport_category(name, current="その他"):
    text = name or ""
    lower_text = text.lower()
    # Pickleball was historically grouped with tennis or other. Its explicit name
    # takes precedence so existing university and social-circle records are corrected.
    for category, keywords in SPORT_KEYWORDS:
        if category == "ピックルボール" and any(keyword in text or keyword.lower() in lower_text for keyword in keywords):
            return category
    # Soccer and futsal intentionally share one matching pool. Normalize both
    # historic categories before honoring any existing category value.
    if current in {"サッカー", "フットサル"}:
        return "サッカー・フットサル"
    if current and current != "その他":
        return current
    for category, keywords in SPORT_KEYWORDS:
        if any(keyword in text or keyword.lower() in lower_text for keyword in keywords):
            return category
    return current or "その他"


def is_invalid_circle_name(name, source_url=""):
    text = clean_circle_name(name)
    url = (source_url or "").lower()
    if not text:
        return True
    if text.startswith("#"):
        return True
    if text in INVALID_CIRCLE_EXACT_NAMES:
        return True
    if any(part in url for part in INVALID_SOURCE_ALWAYS_PARTS):
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
    if any(phrase in text for phrase in ["誓約書", "WORD／", "PDF", "文部科学省定義", "学生表彰", "新設団体活動予定書", "申込用紙", "申込書", "販売報告書", "助成金"]):
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
    if any(word in text for word in ["講演会", "説明会", "セミナー"]) and (len(text) > 14 or not any(marker in text for marker in ["研究会", "委員会", "同好会", "部"])):
        return True
    if any(phrase in text for phrase in ["本学学生が", "号 歴史を変えた"]):
        return True
    return False


def clean_circle_name(name):
    text = (name or "").strip()
    if not text:
        return ""
    match = re.match(r"^(.+?)[（(]([^（）()]+)[）)]$", text)
    if match:
        base = match.group(1).strip()
        detail = match.group(2).strip()
        has_group_marker = any(marker in base for marker in ["部", "会", "サークル", "クラブ", "団体", "委員会", "同好会", "研究会"])
        looks_descriptive = any(word in detail for word in DESCRIPTIVE_PARENTHETICAL_WORDS)
        if has_group_marker and looks_descriptive:
            return base
    return text


def ensure_column(conn, table, column, definition):
    cols = [row["name"] for row in conn.execute(f"pragma table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"alter table {table} add column {column} {definition}")


def ensure_runtime_circle_schema(conn):
    """Keep long-lived Render SQLite volumes compatible with public queries."""
    global _CIRCLE_SCHEMA_READY
    if _CIRCLE_SCHEMA_READY:
        return
    with _CIRCLE_SCHEMA_LOCK:
        if _CIRCLE_SCHEMA_READY:
            return
        table = conn.execute(
            "select 1 from sqlite_master where type='table' and name='circles'"
        ).fetchone()
        if not table:
            # Fresh databases are created by init_db below.
            return
        try:
            for column, definition in _CIRCLE_RUNTIME_COLUMNS:
                ensure_column(conn, "circles", column, definition)
            columns = {
                row["name"] for row in conn.execute("pragma table_info(circles)").fetchall()
            }
            missing = [column for column, _ in _CIRCLE_RUNTIME_COLUMNS if column not in columns]
            if missing:
                raise RuntimeError(f"circles migration did not complete: {', '.join(missing)}")
            conn.execute(
                "update circles set public_status='published' "
                "where public_status is null or trim(public_status)=''"
            )
            conn.execute(
                "create index if not exists idx_circles_organization_type "
                "on circles(organization_type)"
            )
            conn.execute(
                "create index if not exists idx_circles_public_status "
                "on circles(public_status)"
            )
            conn.commit()
            _CIRCLE_SCHEMA_READY = True
        except Exception as exc:
            print(
                f"circle schema migration failed for {DB_PATH}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            raise


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


GUIDE_PAGES = {
    "practice-match-how-to": {
        "title": "大学サークルの練習試合相手を探す手順",
        "lead": "初めて練習試合を組む代表者向けに、募集条件を整理して相手に伝わりやすくするための基本をまとめます。",
        "sections": [
            ("先に決めること", ["競技、希望日程、場所、レベル感、人数、審判や用具の有無を先に決めます。", "曖昧な募集は返信が来ても調整に時間がかかるため、最低条件と相談可能な条件を分けて書きます。"]),
            ("募集文の型", ["大学名、団体名、競技、希望期間、活動エリア、レベル、連絡方法、補足条件の順に書くと読みやすくなります。", "例: 8月中の土日、東京都内、経験者中心、グラウンド確保済み、同程度の相手を募集。"]),
            ("安全に進めるポイント", ["個人の電話番号やLINE IDをいきなり公開せず、まずはサービス上のフォームや代表メールでやり取りします。", "相手団体の大学名、代表者、活動実態、過去の公開情報を確認してから詳細調整に進みます。"]),
        ],
    },
    "recruiting-template": {
        "title": "サークル代表向け募集文テンプレート",
        "lead": "練習試合、合同練習、助っ人募集、メンバー募集で使える文章の型を用意します。",
        "sections": [
            ("練習試合募集", ["「競技」「希望日」「場所」「レベル」「人数」「費用負担」「連絡期限」を1つずつ埋めると、相手が判断しやすくなります。", "勝敗より交流重視なのか、公式戦に近い強度なのかを必ず書きます。"]),
            ("合同練習募集", ["練習メニュー、参加人数、経験者割合、初心者参加可否、途中参加可否を書きます。", "練習後の交流や食事の有無も、雰囲気を判断する材料になります。"]),
            ("社会人サークルのメンバー募集", ["活動曜日、活動場所、会費、年齢層、初心者歓迎度、体験参加の流れを明記します。", "社会人は時間調整が重要なので、毎週固定か不定期かを先に見せます。"]),
        ],
    },
    "verification-policy": {
        "title": "Circle Matchの掲載情報と検証の考え方",
        "lead": "公開DBを安心して使えるように、情報源、検証ステータス、訂正依頼の考え方を説明します。",
        "sections": [
            ("公開情報を中心に扱う", ["大学公式ページ、団体本人の登録、公開SNSなど、公開されている情報を中心に整理します。", "代表者の個人メールアドレスや電話番号など、本人確認に使う情報は公開DBに出しません。"]),
            ("検証ステータス", ["大学公式情報掲載、公開情報掲載、申請済み、未確認を分けて表示し、出典がわかるものは出典URLを残します。", "未確認情報は、団体本人や大学関係者からの訂正で更新していきます。"]),
            ("削除・訂正", ["掲載内容に誤りがある場合は、問い合わせから対象URL、団体名、訂正内容を送ってください。", "個人情報や誤掲載の疑いがあるものは、確認中に非公開化する場合があります。"]),
        ],
    },
    "circle-database-guide": {
        "title": "Circle Match DBでスポーツ団体を探す方法",
        "lead": "分散しやすい大学・社会人スポーツ団体の情報を、競技、地域、出典、検証状態から比較するための見方を説明します。",
        "sections": [
            ("まず競技と活動地域を決める", ["スポーツ別ページでは、同じ競技の団体と交流募集をまとめて確認できます。地域を選ぶと、都道府県まで候補を絞り込めます。", "大学名や団体名が分かっている場合は、サークルDBの検索欄から直接調べることもできます。候補が少ない競技では、隣接地域まで広げて確認するのが有効です。"]),
            ("出典と検証状態を確認する", ["一覧の出典は、大学公式ページ、団体本人登録、公開SNSなど、情報を確認した入口を示します。出典URLがある場合は、連絡前に活動内容や最新情報を確認できます。", "検証状態は掲載団体の存在や申請状況を示すための補助情報です。活動の安全性、募集の実現、公式な公認を保証するものではありません。"]),
            ("大学団体と社会人サークルを分けて見る", ["大学サークルDBでは大学名・都道府県・競技を軸に、社会人サークルDBでは活動地域・競技を軸に探せます。所属形態が違うため、一覧と検索結果を分けて表示しています。", "練習相手や合同練習の候補を探す場合は、団体の種別、活動場所、競技カテゴリを確認してから連絡条件を調整してください。"]),
            ("情報をより正確にするために", ["掲載漏れ、活動停止、名称変更、誤掲載に気付いた場合は、対象ページまたは出典URLと訂正内容を問い合わせ窓口へ送ってください。", "団体代表者は自分の団体情報を申請でき、確認後は紹介ページや公開連絡先を整備できます。公開DBは、利用者と団体関係者の訂正によって更新していきます。"]),
        ],
    },
    "sports-match-manners": {
        "title": "練習試合・合同練習のマナー",
        "lead": "相手団体とのトラブルを避けるため、事前連絡、当日の進行、終了後の対応を整理します。",
        "sections": [
            ("事前連絡", ["集合時間、場所、服装、用具、雨天時判断、キャンセル期限を明確にします。", "遅刻や人数変更が出た場合は、判明した時点ですぐに共有します。"]),
            ("当日の進行", ["代表者同士で最初に挨拶し、時間配分、ルール、危険行為、撮影可否を確認します。", "初心者や助っ人がいる場合は、怪我を防ぐため強度を合わせます。"]),
            ("終了後", ["お礼、結果、次回候補日、改善点を簡単に共有すると継続的な関係につながります。", "写真や動画をSNSに載せる場合は、相手側の確認を取ります。"]),
        ],
    },
    "kanto-circle-trends": {
        "title": "関東の大学サークル探しで見ておきたいポイント",
        "lead": "関東は大学数とサークル数が多いため、地域、競技、移動時間で絞ると探しやすくなります。",
        "sections": [
            ("地域で絞る", ["東京都、神奈川県、千葉県、埼玉県、茨城県、栃木県、群馬県で分けると候補を整理しやすくなります。", "同じ関東でも移動時間が大きく変わるため、都道府県だけでなく活動場所も確認します。"]),
            ("競技で絞る", ["野球、サッカー、テニス、バスケットボールなどは候補が多く、レベル感の確認が重要です。", "候補が少ない競技は、隣接県や合同練習まで広げると見つかりやすくなります。"]),
            ("DBの使い方", ["まずスポーツ別ページで全体数を見て、次に地域や大学名で絞ると効率的です。", "登録済みURLがある団体は、代表者が紹介ページを整備している可能性が高く、連絡前の確認材料になります。"]),
        ],
    },
    "social-circle-recruiting": {
        "title": "社会人サークルがメンバー募集で書くべき情報",
        "lead": "社会人サークルは、練習相手探しよりもメンバー募集の需要が強いため、参加前の不安を減らす情報が大切です。",
        "sections": [
            ("参加者が知りたいこと", ["活動頻度、曜日、場所、会費、年齢層、初心者歓迎度、体験参加の可否を最初に見せます。", "雰囲気、経験者割合、男女比、競技レベルも判断材料になります。"]),
            ("募集ページの作り方", ["写真よりも、いつ・どこで・どんな人が参加しているかを具体的に書くことが重要です。", "体験参加の流れを3ステップで書くと、問い合わせの心理的ハードルが下がります。"]),
            ("安全性", ["個人情報を公開しすぎず、まずは問い合わせフォームや代表メールを使います。", "未成年参加、保険、怪我、会費徴収の扱いは事前に明確にしておくと安心です。"]),
        ],
    },
    "privacy-for-representatives": {
        "title": "サークル代表者の個人情報を守る考え方",
        "lead": "代表者登録や問い合わせ対応で、どこまで公開し、どこから非公開にするべきかを整理します。",
        "sections": [
            ("公開してよい情報", ["大学名、団体名、競技、活動場所、公開SNS、公式ページなど、団体として公開している情報を中心にします。", "代表者個人の名前を出す場合でも、本人が公開を望む範囲に限定します。"]),
            ("公開しない情報", ["個人メールアドレス、電話番号、LINE ID、住所、学籍番号、内部メモは公開ページに出さない設計にします。", "Circle Matchでも、代表者確認情報は公開検索APIに返さない方針です。"]),
            ("なりすまし対策", ["大学メール確認、公式SNS確認、既存掲載情報との照合を組み合わせます。", "登録済み団体の変更は、申請者の立場を確認してから反映します。"]),
        ],
    },
    "adsense-site-policy": {
        "title": "Circle Matchの広告掲載ポリシー",
        "lead": "広告掲載時に、ユーザーの検索体験と安全性を損なわないための方針です。",
        "sections": [
            ("広告とコンテンツの区別", ["広告は検索結果や募集情報と紛らわしくならない位置に置き、誤クリックを誘導しません。", "広告の近くに「クリックしてください」などの誘導文は置きません。"]),
            ("掲載しないコンテンツ", ["誹謗中傷、差別、暴力、性的内容、著作権侵害、詐欺的な募集、本人同意のない個人情報は扱いません。", "公開DBに不適切な情報が混じった場合は、確認次第修正または非公開化します。"]),
            ("ユーザー価値を優先", ["広告収益よりも、サークル探し、練習試合探し、掲載情報の正確性を優先します。", "検索ページだけでなく、代表者向けのノウハウ記事も継続的に整備します。"]),
        ],
    },
}


def operator_page():
    body = f"""
<h1>運営者情報</h1>
<p class="meta">最終更新日: {POLICY_UPDATED_AT} / 運営者: {SITE_OPERATOR}</p>
<p>{SITE_NAME}は、大学サークル・部活動・社会人スポーツ団体の情報を、競技・活動地域・出典・検証状態ごとに整理する検索データベースです。練習試合、合同練習、助っ人募集、交流イベント、メンバー募集の候補探しにも活用できます。</p>
<h2>運営目的</h2>
<p>サークル活動は、大学公式サイト、SNS、個別の紹介ページに情報が分散しがちです。本サービスでは、公開情報と代表者からの登録情報を団体単位で整理し、活動先や連絡先候補を比較・確認しやすい状態を目指します。マッチング機能は、この情報基盤を活用するための一つの手段です。</p>
<h2>サービスの位置づけ</h2>
<ul>
  <li>本サービスは大学、自治体、競技団体その他の団体から公認・委託を受けたサービスではありません。</li>
  <li>掲載、検証ステータス、代表者申請の受付は、団体の公認、活動の安全性、募集内容の実現を保証するものではありません。</li>
  <li>試合・合同練習・イベントへの参加や連絡は、利用者と団体の責任で条件を確認したうえで行ってください。</li>
</ul>
<h2>編集方針</h2>
<ul>
  <li>公開情報と代表者からの申請情報を分けて管理します。</li>
  <li>団体名、大学名、競技、活動地域、出典URLを照合し、イベント名、試合結果、記事見出しなど団体ではない情報は掲載対象から除外します。</li>
  <li>出典がある情報には出典URLや検証ステータスを残し、掲載後も訂正依頼や更新情報をもとに見直します。</li>
  <li>個人情報や内部メモは公開ページに表示しません。</li>
  <li>誤掲載、削除依頼、権利侵害の疑いがある情報は確認し、必要に応じて修正または非公開化します。</li>
</ul>
<h2>対応方針</h2>
<p>掲載情報の訂正・削除、個人情報、権利侵害のおそれに関する連絡は優先して確認します。受付の目安は5営業日以内ですが、内容確認が必要な場合は追加の確認をお願いすることがあります。</p>
<h2>問い合わせ窓口</h2>
<p>掲載情報の訂正、削除、代表者登録、広告掲載、サービス改善に関する連絡は <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> までお願いします。</p>
"""
    return legal_layout("運営者情報", body)


def guides_page():
    items = "\n".join(
        f"""<li><a href="/guides/{slug}">{data["title"]}</a><br><span class="meta">{data["lead"]}</span></li>"""
        for slug, data in GUIDE_PAGES.items()
    )
    body = f"""
<h1>サークル運営ガイド</h1>
<p class="meta">練習試合、合同練習、助っ人募集、メンバー募集をスムーズに進めるための基礎情報です。</p>
<p>Circle MatchはDB検索だけでなく、代表者が安全に募集し、参加者が安心して比較できるための情報も整備していきます。</p>
<h2>記事一覧</h2>
<ul>{items}</ul>
"""
    return legal_layout("サークル運営ガイド", body)


def guide_page(slug):
    data = GUIDE_PAGES.get(slug)
    if not data:
        return None
    sections = "\n".join(
        f"<h2>{title}</h2><ul>{''.join(f'<li>{item}</li>' for item in items)}</ul>"
        for title, items in data["sections"]
    )
    body = f"""
<h1>{data["title"]}</h1>
<p class="meta">サークル代表者・参加希望者向けガイド</p>
<p>{data["lead"]}</p>
{sections}
<h2>関連ページ</h2>
<ul>
  <li><a href="/guides">サークル運営ガイド一覧</a></li>
  <li><a href="/circles">サークルDBを見る</a></li>
  <li><a href="/contact">掲載情報の訂正・問い合わせ</a></li>
</ul>
"""
    return legal_layout(data["title"], body)


def privacy_page():
    body = f"""
<h1>プライバシーポリシー</h1>
<p class="meta">制定日: 2026年7月1日 / 最終更新日: {POLICY_UPDATED_AT} / 運営者: {SITE_OPERATOR}</p>
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
<p>公開検索ページには、公開情報のみを表示します。代表者氏名、大学メールアドレス、問い合わせ本文、内部メモ、認証情報は公開しません。団体が公開に同意した団体用の連絡先メールアドレスだけは、団体紹介ページに表示する場合があります。</p>
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
<p class="meta">制定日: 2026年7月1日 / 最終更新日: {POLICY_UPDATED_AT} / 運営者: {SITE_OPERATOR}</p>
<h2>目的</h2>
<p>本規約は、{SITE_NAME}の利用条件を定めるものです。本サービスは、大学サークル・部活動情報の検索、掲載、練習試合等の募集支援を目的とします。</p>
<h2>掲載情報</h2>
<p>掲載情報は、大学公式ページ、団体本人の登録、公開SNS、その他公開情報をもとに作成します。正確性の維持に努めますが、内容の完全性、最新性、有用性を保証するものではありません。</p>
<p>掲載、検証ステータス、代表者申請の受付は、大学その他の団体による公認や、団体・募集内容の安全性を保証するものではありません。</p>
<h2>禁止事項</h2>
<ul>
  <li>なりすまし、虚偽登録、第三者の権利侵害</li>
  <li>個人情報、連絡先、非公開情報の無断投稿</li>
  <li>迷惑行為、差別的表現、違法行為、公序良俗に反する行為</li>
  <li>サービス運営、サーバー、DBに過度な負荷をかける行為</li>
</ul>
<h2>代表者申請</h2>
<p>代表者権限は、大学メールから届いた確認メール、公式情報、運営確認等をもとに付与します。虚偽申請や権限の不正利用が判明した場合、掲載停止または権限取消を行います。</p>
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
<h1>Circle Match DBの掲載方針と訂正依頼</h1>
<p class="meta">最終更新日: {POLICY_UPDATED_AT}</p>
<h2>Circle Match DBの目的</h2>
<p>Circle Matchの中心は、大学・社会人スポーツ団体の情報を検索・比較できるデータベースです。大学公式サイト、団体の公式ページ、公開SNSなどに分散した情報を、団体名、所属先、競技、活動地域、出典、検証状態という共通の項目で整理します。</p>
<p>練習試合やメンバー募集の掲載は、DBで候補を見つけた後の行動を助ける機能です。掲載件数だけを目的に自動で情報を増やすのではなく、団体そのものと確認できる情報を対象に、更新・訂正を続けることを重視します。</p>
<h2>情報源</h2>
<p>本サービスは、大学公式ページ、団体本人による登録、公開SNS、その他公開情報を出典として、サークル・部活動の名称、競技、大学、出典URL、検証状態を掲載します。</p>
<p>本サービスは大学、自治体、競技団体その他の団体の公式サービスではありません。掲載や検証ステータスは、団体の公認や活動内容の保証を意味しません。</p>
<h2>DBで確認できる項目</h2>
<ul>
  <li>大学名または主な活動地域、団体名、競技カテゴリ</li>
  <li>活動都道府県・市区町村、団体の種別</li>
  <li>出典種別、出典URL、検証または申請の状態</li>
  <li>代表者が公開に同意して登録した場合のみ、団体紹介ページと団体用連絡先</li>
</ul>
<h2>掲載前の確認</h2>
<ul>
  <li>団体名、所属先、競技、出典URLの組み合わせを確認し、重複を整理します。</li>
  <li>大会名、試合結果、記事見出し、個人名、外部団体名など、団体そのものではない候補は掲載対象から除外します。</li>
  <li>情報が古い、出典が確認できない、または誤掲載の可能性がある場合は、修正または非公開化の対象とします。</li>
</ul>
<h2>掲載しない情報</h2>
<ul>
  <li>代表者の個人メールアドレス、電話番号、LINE ID</li>
  <li>本人同意のない個人名、個人写真、非公開グループの情報</li>
  <li>他サイトの紹介文、画像、口コミ、ランキングのコピー</li>
</ul>
<p>団体の公開連絡先は、代表者が公開に同意して登録した団体用メールアドレスに限ります。</p>
<h2>検証ステータス</h2>
<ul>
  <li>大学公式情報掲載: 大学公式ページで存在確認済み</li>
  <li>公開情報掲載: 運営が出典や申請内容を確認済み</li>
  <li>代表申請受付: 団体関係者から申請を受け付け、大学公式ドメインのメールアドレスを入力済みの状態</li>
  <li>大学メール確認済み: 代表者ページ上で、申請内容と大学メールから届いた確認メールを運営が照合済みの状態</li>
  <li>未確認: 公開情報から候補として登録した状態</li>
</ul>
<h2>削除・訂正依頼</h2>
<p>掲載情報の削除、訂正、非公開化を希望する場合は、団体名、大学名または活動地域、対象URL、依頼内容、申請者の立場を記載して <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> まで連絡してください。個人情報、権利侵害、なりすましのおそれがある内容は優先して確認します。</p>
"""
    return legal_layout("Circle Match DBの掲載方針", body)


def contact_page():
    body = f"""
<h1>問い合わせ</h1>
<p class="meta">運営者: {SITE_OPERATOR} / 最終更新日: {POLICY_UPDATED_AT}</p>
<p>サイトへのご意見・ご要望はこちら。掲載情報の訂正、削除、代表者申請、個人情報に関する問い合わせも、以下のメールアドレスまで連絡してください。</p>
<p><a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
<p>原則として5営業日以内の返信を目安にしています。個人情報、権利侵害、なりすましのおそれがある掲載については、対象ページのURLを添えてください。</p>
<h2>記載してほしい内容</h2>
<ul>
  <li>大学名、団体名</li>
  <li>対象ページまたは出典URL</li>
  <li>訂正・削除・問い合わせの内容</li>
  <li>申請者の立場</li>
</ul>
"""
    return legal_layout("問い合わせ", body)


def state_value(conn, key):
    row = conn.execute(
        "select state_value from app_state where state_key=?",
        (key,),
    ).fetchone()
    return row["state_value"] if row else ""


def set_state_value(conn, key, value):
    conn.execute(
        """
        insert into app_state(state_key, state_value, updated_at)
        values(?,?,?)
        on conflict(state_key) do update set
          state_value=excluded.state_value,
          updated_at=excluded.updated_at
        """,
        (key, value, now()),
    )


def migrate_event_payment_methods(conn):
    """Expand the legacy CHECK without changing event IDs or dependent rows."""
    schema = conn.execute("select sql from sqlite_master where type='table' and name='event_posts'").fetchone()[0]
    old_check = "check(payment_method in ('free','on_site'))"
    if old_check not in schema:
        if "'bank_transfer'" not in schema:
            raise RuntimeError("Unexpected event_posts payment constraint; migration stopped")
        return
    if conn.in_transaction:
        raise RuntimeError("Payment migration must run before startup data changes")
    backup_path = DB_PATH.with_name(DB_PATH.name + ".pre-bank-transfer-" + datetime.now().strftime("%Y%m%d%H%M%S") + ".sqlite")
    backup = sqlite3.connect(backup_path)
    try:
        conn.backup(backup)
    finally:
        backup.close()
    log(f"event payment migration backup: {backup_path}")
    conn.execute("pragma foreign_keys=off")
    try:
        conn.execute("begin immediate")
        objects = conn.execute("select sql from sqlite_master where tbl_name='event_posts' and type in ('index','trigger') and sql is not null").fetchall()
        new_schema = schema.replace(old_check, "check(payment_method in ('free','on_site','bank_transfer'))")
        new_schema, count = re.subn(r'(?i)^CREATE TABLE\s+"?event_posts"?', "CREATE TABLE event_posts_payment_v2", new_schema, count=1)
        if count != 1:
            raise RuntimeError("Unrecognized event_posts schema; migration stopped")
        conn.execute(new_schema)
        columns = ",".join('"' + row["name"].replace('"', '""') + '"' for row in conn.execute("pragma table_info(event_posts)"))
        conn.execute(f"insert into event_posts_payment_v2 ({columns}) select {columns} from event_posts")
        conn.execute("drop table event_posts")
        conn.execute("alter table event_posts_payment_v2 rename to event_posts")
        for obj in objects:
            conn.execute(obj["sql"])
        for table in ("event_posts", "event_applications", "event_notifications", "event_messages"):
            if conn.execute(f"pragma foreign_key_check({table})").fetchone():
                raise RuntimeError(f"Payment migration foreign key check failed: {table}")
        conn.commit()
        log("event payment migration complete")
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.execute("pragma foreign_keys=on")


def migrate_event_target_total(conn):
    if "target_total_amount" in {row["name"] for row in conn.execute("pragma table_info(event_posts)")}:
        return
    if conn.in_transaction:
        raise RuntimeError("Target total migration must precede startup data changes")
    backup_path = DB_PATH.with_name(DB_PATH.name + ".pre-target-total-" + datetime.now().strftime("%Y%m%d%H%M%S") + ".sqlite")
    backup = sqlite3.connect(backup_path)
    try:
        conn.backup(backup)
    finally:
        backup.close()
    log(f"event target total migration backup: {backup_path}")
    conn.execute("alter table event_posts add column target_total_amount integer check(target_total_amount between 0 and 1000000000)")
    log("event target total migration complete")


def migrate_event_formation(conn):
    additions = {
        "event_posts": {
            "minimum_participants": "integer not null default 0",
            "minimum_notice_sent": "integer not null default 0",
            "announcement_version": "integer not null default 0",
            "announcement_details": "text not null default ''",
            "announced_at": "text",
            "bank_transfer_details": "text not null default ''",
            "payment_deadline": "text",
        },
        "event_applications": {
            "attendance_version": "integer not null default 0",
            "attendance_confirmed_at": "text",
        },
    }
    missing = [(table, name, definition) for table, fields in additions.items()
               for name, definition in fields.items()
               if name not in {row["name"] for row in conn.execute(f"pragma table_info({table})")}]
    if not missing:
        return
    if conn.in_transaction:
        raise RuntimeError("Formation migration must precede startup data changes")
    backup_path = DB_PATH.with_name(DB_PATH.name + ".pre-formation-" + datetime.now().strftime("%Y%m%d%H%M%S%f") + ".sqlite")
    backup = sqlite3.connect(backup_path)
    try:
        conn.backup(backup)
    finally:
        backup.close()
    log(f"event formation migration backup: {backup_path}")
    conn.execute("begin immediate")
    try:
        for table, name, definition in missing:
            conn.execute(f"alter table {table} add column {name} {definition}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def migrate_event_operations(conn):
    additions = {
        "event_posts": {"attendance_deadline": "text"},
        "event_applications": {
            "payment_status": "text not null default 'unpaid'",
            "payment_note": "text not null default ''",
            "payment_updated_at": "text",
            "operation_revision": "integer not null default 0",
            "requested_participant_count": "integer",
        },
    }
    missing = [(table, name, definition) for table, fields in additions.items()
               for name, definition in fields.items()
               if name not in {row["name"] for row in conn.execute(f"pragma table_info({table})")}]
    if missing:
        if conn.in_transaction:
            raise RuntimeError("Operations migration must precede startup data changes")
        path = DB_PATH.with_name(DB_PATH.name + ".pre-operations-" + datetime.now().strftime("%Y%m%d%H%M%S%f") + ".sqlite")
        with sqlite3.connect(path) as backup:
            conn.backup(backup)
        backup.close()
        log(f"event operations migration backup: {path}")
    conn.execute("begin immediate")
    try:
        for table, name, definition in missing:
            conn.execute(f"alter table {table} add column {name} {definition}")
        conn.execute("""create table if not exists event_reminder_deliveries (
            application_id text not null references event_applications(application_id),
            announcement_version integer not null, kind text not null, created_at text not null,
            primary key(application_id, announcement_version, kind))""")
        conn.execute("create index if not exists idx_event_attendance_deadline on event_posts(attendance_deadline, status)")
        conn.execute("create index if not exists idx_event_messages_sender_time on event_messages(sender_user_id, created_at)")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


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
          public_contact_email text,
          public_contact_consent integer not null default 0,
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
        create table if not exists event_posts (
          event_id text primary key,
          organizer_user_id text not null references user_accounts(user_id),
          linked_circle_id text references circles(circle_id),
          organizer_name text not null,
          organizer_contact_email text not null,
          event_type text not null check(event_type in ('大会','交流イベント','練習試合','合同練習')),
          sport_category text not null,
          title text not null,
          starts_at text not null,
          ends_at text,
          prefecture text,
          location text not null,
          description text not null,
          participation_type text not null check(participation_type in ('individual','team','both')),
          capacity integer,
          capacity_unit text not null default '人',
          eligibility text,
          fee_amount integer,
          fee_unit text,
          target_total_amount integer check(target_total_amount between 0 and 1000000000),
          payment_method text not null default 'free' check(payment_method in ('free','on_site','bank_transfer')),
          application_deadline text,
          acceptance_mode text not null check(acceptance_mode in ('first_come','approval')),
          cancellation_policy text,
          status text not null default 'draft' check(status in ('draft','published','closed','cancelled')),
          published_at text,
          created_at text not null,
          updated_at text not null
        );
        create table if not exists event_applications (
          application_id text primary key,
          event_id text not null references event_posts(event_id) on delete cascade,
          applicant_user_id text not null references user_accounts(user_id),
          participation_type text not null check(participation_type in ('individual','team')),
          applicant_name text,
          team_name text,
          representative_name text,
          participant_count integer not null default 1,
          answers_json text not null default '{}',
          applicant_message text,
          organizer_note text,
          status text not null check(status in ('pending','confirmed','declined','cancelled')),
          created_at text not null,
          updated_at text not null,
          unique(event_id, applicant_user_id)
        );
        create table if not exists event_application_history (
          history_id integer primary key,
          application_id text not null,
          snapshot_json text not null,
          archived_at text not null
        );
        create table if not exists event_notifications (
          notification_id text primary key,
          recipient_user_id text not null references user_accounts(user_id) on delete cascade,
          event_id text references event_posts(event_id) on delete cascade,
          notification_type text not null,
          title text not null,
          body text not null,
          email_status text not null default 'not_configured' check(email_status in ('not_configured','sent','failed')),
          email_error text,
          read_at text,
          created_at text not null
        );
        create table if not exists event_messages (
          message_id text primary key,
          event_id text not null references event_posts(event_id) on delete cascade,
          sender_user_id text not null references user_accounts(user_id),
          recipient_user_id text not null references user_accounts(user_id),
          body text not null,
          read_at text,
          created_at text not null
        );
        create table if not exists event_email_outbox (
          notification_id text primary key references event_notifications(notification_id) on delete cascade,
          payload_json text not null,
          status text not null default 'queued' check(status in ('queued','sending','retry','sent','failed')),
          attempts integer not null default 0,
          next_attempt_at integer not null default 0,
          first_attempt_at integer,
          lease_until integer,
          provider_id text,
          last_error text,
          sent_at text
        );
        create index if not exists idx_event_email_outbox_due on event_email_outbox(status,next_attempt_at);
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
        create table if not exists circle_listing_reviews (
          circle_id text primary key references circles(circle_id),
          reason text not null,
          review_status text not null default 'pending',
          created_at text not null
        );
        create table if not exists app_state (
          state_key text primary key,
          state_value text not null,
          updated_at text not null
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
        create index if not exists idx_event_posts_public on event_posts(status, starts_at, sport_category, prefecture);
        create index if not exists idx_event_posts_organizer on event_posts(organizer_user_id, status, updated_at);
        create index if not exists idx_event_posts_circle on event_posts(linked_circle_id, status);
        create index if not exists idx_event_applications_event on event_applications(event_id, status, created_at);
        create index if not exists idx_event_applications_user on event_applications(applicant_user_id, status, created_at);
        create index if not exists idx_event_notifications_recipient on event_notifications(recipient_user_id, read_at, created_at);
        create index if not exists idx_event_messages_event on event_messages(event_id, created_at);
        create index if not exists idx_circle_candidates_university on circle_candidates(university_id);
        create index if not exists idx_circle_candidates_status on circle_candidates(review_status);
        """)
        migrate_event_payment_methods(conn)
        migrate_event_target_total(conn)
        migrate_event_formation(conn)
        migrate_event_operations(conn)
        for column, definition in _CIRCLE_RUNTIME_COLUMNS:
            ensure_column(conn, "circles", column, definition)
        ensure_column(conn, "circle_claims", "university_email_domain_checked", "integer not null default 0")
        ensure_column(conn, "circle_claims", "university_email_verified_at", "text")
        ensure_column(conn, "circle_public_profiles", "public_contact_email", "text")
        ensure_column(conn, "circle_public_profiles", "public_contact_consent", "integer not null default 0")
        ensure_column(conn, "match_posts", "period_start", "text")
        ensure_column(conn, "match_posts", "period_end", "text")
        ensure_column(conn, "match_posts", "practice_detail", "text")
        ensure_column(conn, "match_posts", "capacity", "text")
        ensure_column(conn, "match_posts", "created_by", "text")
        conn.execute("create index if not exists idx_circles_organization_type on circles(organization_type)")
        conn.execute("create index if not exists idx_circles_public_status on circles(public_status)")
        conn.execute(
            "update circles set public_status='published' "
            "where public_status is null or trim(public_status)=''"
        )
        review_sources = tuple(LISTING_REVIEW_SOURCES)
        conn.execute(
            "insert or ignore into circle_listing_reviews(circle_id,reason,created_at) "
            "select circle_id,?,? from circles where source_url in (" + ','.join('?' for _ in review_sources) + ")",
            ("UX監査: スポーツ団体との関連を要確認。原データは保持。", now(), *review_sources),
        )

        # The public data lives on Render's persistent disk.  Importing the CSV
        # and iterating every circle on every process restart caused large write
        # spikes and unnecessary memory pressure.  A fresh database still gets
        # the full seed, while an existing database keeps its data as-is.
        if state_value(conn, "reference_data_revision") != REFERENCE_DATA_REVISION:
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
            set_state_value(conn, "reference_data_revision", REFERENCE_DATA_REVISION)

        if conn.execute("select count(*) from circles").fetchone()[0] == 0:
            seed_public_circles_from_csv(conn)

        # Historical cleanup is intentionally one-time per revision.  The
        # marker lives in SQLite so routine restarts only run schema checks.
        if state_value(conn, "startup_maintenance_revision") != STARTUP_MAINTENANCE_REVISION:
            log("running one-time startup data maintenance")
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
            normalize_circle_records(conn)
            delete_known_circle_noise(conn)
            remove_demo_content(conn)
            migrate_circle_private_data(conn)
            redact_existing_audit_logs(conn)
            seed_collection_targets(conn)
            set_state_value(conn, "startup_maintenance_revision", STARTUP_MAINTENANCE_REVISION)

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
    imported = 0
    for seed_path in (PUBLIC_SEED_PATH, SOCIAL_SEED_PATH):
        if not seed_path.exists():
            continue
        seed_imported = 0
        with seed_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for item in reader:
                uni_name = (item.get("university_name") or "").strip()
                circle_name = clean_circle_name(item.get("circle_name") or "")
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
                seed_imported += 1
        if seed_imported:
            audit(conn, "public_seed_import", "circle", None, {
                "imported": seed_imported,
                "source": str(seed_path),
            })
            imported += seed_imported
    return imported


def normalize_circle_records(conn):
    removed = 0
    updated = 0
    for row in conn.execute("select circle_id, university_id, circle_name, sport_category, source_url from circles").fetchall():
        name = row["circle_name"]
        if is_invalid_circle_name(name, row["source_url"] or ""):
            conn.execute("delete from data_sources where entity_type='circle' and entity_id=?", (row["circle_id"],))
            conn.execute("delete from circle_private_profiles where circle_id=?", (row["circle_id"],))
            conn.execute("delete from circle_claims where circle_id=?", (row["circle_id"],))
            conn.execute("delete from match_posts where circle_id=?", (row["circle_id"],))
            conn.execute("delete from circles where circle_id=?", (row["circle_id"],))
            removed += 1
            continue
        clean_name = clean_circle_name(name)
        if clean_name != name:
            duplicate = conn.execute(
                "select circle_id from circles where university_id=? and circle_name=? and circle_id<>?",
                (row["university_id"], clean_name, row["circle_id"]),
            ).fetchone()
            if duplicate:
                conn.execute("delete from data_sources where entity_type='circle' and entity_id=?", (row["circle_id"],))
                conn.execute("delete from circle_private_profiles where circle_id=?", (row["circle_id"],))
                conn.execute("delete from circle_claims where circle_id=?", (row["circle_id"],))
                conn.execute("delete from match_posts where circle_id=?", (row["circle_id"],))
                conn.execute("delete from circles where circle_id=?", (row["circle_id"],))
                removed += 1
                continue
            conn.execute(
                "update circles set circle_name=?, updated_at=? where circle_id=?",
                (clean_name, now(), row["circle_id"]),
            )
            name = clean_name
            updated += 1
        sport = infer_sport_category(name, row["sport_category"])
        if sport != row["sport_category"]:
            conn.execute(
                "update circles set sport_category=?, updated_at=? where circle_id=?",
                (sport, now(), row["circle_id"]),
            )
            updated += 1
    if removed or updated:
        audit(conn, "normalize_circle_records", "circle", None, {"removed": removed, "updated": updated})


def delete_known_circle_noise(conn):
    noise = [
        ("武蔵大学", "Web展覧会"),
        ("武蔵大学", "利用可能団体"),
        ("武蔵大学", "All in Musashi"),
        ("武蔵大学", "TRPG&"),
        ("武蔵大学", "Web"),
        ("武蔵大学", "マガジン編集部"),
        ("武蔵大学", "舞踏研究部（白雉祭）"),
        ("武蔵大学", "モダンジャズ研究会（白雉祭）"),
    ]
    removed = 0
    for university_name, circle_name in noise:
        rows = conn.execute(
            """
            select c.circle_id
            from circles c
            join universities u on u.university_id = c.university_id
            where u.university_name = ? and c.circle_name = ?
            """,
            (university_name, circle_name),
        ).fetchall()
        for row in rows:
            circle_id = row["circle_id"]
            conn.execute("delete from data_sources where entity_type='circle' and entity_id=?", (circle_id,))
            conn.execute("delete from circle_private_profiles where circle_id=?", (circle_id,))
            conn.execute("delete from circle_claims where circle_id=?", (circle_id,))
            conn.execute("delete from match_posts where circle_id=?", (circle_id,))
            conn.execute("delete from circles where circle_id=?", (circle_id,))
            removed += 1
    if removed:
        audit(conn, "delete_known_circle_noise", "circle", None, {"removed": removed})


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
          atmosphere, experience_ratio, practice_frequency, activity_place, representative_comment, public_contact_email,
          public_contact_consent, is_published, created_at, updated_at)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        on conflict(circle_id) do update set
          catch_copy=excluded.catch_copy,
          introduction=excluded.introduction,
          member_count=excluded.member_count,
          atmosphere=excluded.atmosphere,
          experience_ratio=excluded.experience_ratio,
          practice_frequency=excluded.practice_frequency,
          activity_place=excluded.activity_place,
          representative_comment=excluded.representative_comment,
          public_contact_email=excluded.public_contact_email,
          public_contact_consent=excluded.public_contact_consent,
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
            (data.get("public_contact_email") or "").strip(),
            1 if data.get("public_contact_consent") else 0,
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
    if data.get("source_url") in LISTING_REVIEW_SOURCES:
        conn.execute("insert or ignore into circle_listing_reviews(circle_id,reason,created_at) values(?,?,?)",
                     (saved_id, "UX監査: スポーツ団体との関連を要確認。原データは保持。", timestamp))
    upsert_circle_private_profile(conn, saved_id, data)
    if data.get("source_url"):
        conn.execute(
            "insert or replace into data_sources(source_id, entity_type, entity_id, source_type, source_url, memo, checked_at, created_at) values(?,?,?,?,?,?,?,?)",
            (slug("src", saved_id + data.get("source_url", "")), "circle", saved_id, data.get("source_type", "other"), data.get("source_url", ""), "circle source", now()[:10], timestamp),
        )
    if audit_entry:
        audit(conn, "upsert", "circle", saved_id, data)
    return saved_id


def official_email_domain(conn, university_id):
    row = conn.execute(
        "select official_url from universities where university_id=?",
        (university_id,),
    ).fetchone()
    official_url = row["official_url"] if row else ""
    hostname = (urlparse(official_url or "").hostname or "").lower().rstrip(".")
    return hostname.removeprefix("www.")


def email_matches_university(conn, university_id, email):
    domain = (email.rsplit("@", 1)[-1] if "@" in email else "").lower().rstrip(".")
    expected = official_email_domain(conn, university_id)
    return bool(expected and (domain == expected or domain.endswith("." + expected)))


def verification_mailto(claim_id, circle_name, university_name):
    subject = f"【大学メール確認】{circle_name} / {claim_id}"
    body = "\n".join([
        "Circle Match 運営 ご担当者様",
        "",
        "団体代表者としての申請にあたり、大学メールの確認をお願いします。",
        "",
        f"申請ID: {claim_id}",
        f"大学: {university_name}",
        f"団体名: {circle_name}",
        "",
        "このメールは、申請時に入力した大学メールアドレスから送信しています。",
    ])
    return f"mailto:{quote(CONTACT_EMAIL, safe='@')}?{urlencode({'subject': subject, 'body': body})}"


def social_representative_verification_mailto(claim_id, circle_name):
    subject = f"【代表者メール確認】{circle_name} / {claim_id}"
    body = "\n".join([
        "Circle Match 運営 ご担当者様",
        "",
        "社会人サークルの代表者としての申請にあたり、代表者メールの確認をお願いします。",
        "",
        f"申請ID: {claim_id}",
        f"団体名: {circle_name}",
        "",
        "このメールは、申請時に入力した代表者メールアドレスから送信しています。",
    ])
    return f"mailto:{quote(CONTACT_EMAIL, safe='@')}?{urlencode({'subject': subject, 'body': body})}"


def create_circle_claim(conn, data):
    audience = (data.get("audience") or "university").strip()
    is_social = audience == "social"
    selected_circle_id = (data.get("circle_id") or "").strip()
    university_id = (data.get("university_id") or "").strip()
    circle_name = clean_circle_name(data.get("circle_name") or "")
    claimant_email = (data.get("claimant_email") or "").strip()
    claimant_name = (data.get("claimant_name") or "").strip()
    public_contact_email = (data.get("public_contact_email") or "").strip()
    public_contact_consent = bool(data.get("public_contact_consent"))
    if not claimant_email:
        raise ValueError("claimant_email is required")
    if "@" not in claimant_email:
        raise ValueError("valid claimant_email is required")
    if public_contact_email and "@" not in public_contact_email:
        raise ValueError("valid public_contact_email is required")
    if public_contact_email and not public_contact_consent:
        raise ValueError("public contact consent is required")
    if public_contact_consent and not public_contact_email:
        raise ValueError("public_contact_email is required when consent is given")
    if selected_circle_id:
        selected = conn.execute(
            """
            select c.circle_id, c.circle_name, c.organization_type, c.university_id, u.university_name
            from circles c join universities u on u.university_id=c.university_id
            where c.circle_id=?
            """,
            (selected_circle_id,),
        ).fetchone()
        if not selected:
            raise ValueError("選択した団体が見つかりません。もう一度検索してください。")
        selected_is_social = selected["organization_type"] == SOCIAL_AUDIENCE_TYPE
        if selected_is_social != is_social:
            raise ValueError("選択した団体の区分が一致しません。団体区分を選び直してください。")
        circle_id = selected["circle_id"]
        circle_name = selected["circle_name"]
        university_id = selected["university_id"]
        university_name = selected["university_name"]
        if not is_social and not email_matches_university(conn, university_id, claimant_email):
            expected = official_email_domain(conn, university_id)
            raise ValueError(f"選択した大学の公式メールアドレスを入力してください（{expected or '大学公式ドメイン'}）")
    else:
        if not circle_name:
            raise ValueError("新規団体の団体名を入力してください")
        if is_social:
            prefecture = (data.get("prefecture") or "").strip()
            city = (data.get("social_city") or "").strip()
            if prefecture not in PREFECTURES:
                raise ValueError("社会人サークルの主な活動都道府県を選択してください")
            university_name = f"社会人サークル（{prefecture}）"
            university_id = upsert_university(conn, {
                "university_name": university_name,
                "prefecture": prefecture,
                "city": city,
                "campus_name": "社会人サークル",
            }, audit=False)
            organization_type = SOCIAL_AUDIENCE_TYPE
        else:
            if not university_id:
                raise ValueError("大学を検索して候補から選択してください")
            university = conn.execute(
                "select university_name from universities where university_id=?",
                (university_id,),
            ).fetchone()
            if not university:
                raise ValueError("大学が見つかりません")
            if not email_matches_university(conn, university_id, claimant_email):
                expected = official_email_domain(conn, university_id)
                raise ValueError(f"選択した大学の公式メールアドレスを入力してください（{expected or '大学公式ドメイン'}）")
            university_name = university["university_name"]
            organization_type = data.get("organization_type") if data.get("organization_type") in ORGANIZATION_TYPES else "不明"
        circle_id = upsert_circle(conn, {
            "university_id": university_id,
            "circle_name": circle_name,
            "organization_type": organization_type,
            "sport_category": data.get("sport_category") if data.get("sport_category") in SPORTS else "その他",
            "activity_area": data.get("social_city", "") if is_social else "",
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
        insert into circle_claims(claim_id, circle_id, claimant_name, claimant_email, university_email_verified, university_email_domain_checked, status, evidence_url, reviewed_at, created_at, updated_at)
        values(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (claim_id, circle_id, claimant_name, claimant_email, 0, 0 if is_social else 1, "pending", data.get("evidence_url", ""), "", timestamp, timestamp),
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
        "public_contact_email": public_contact_email,
        "public_contact_consent": public_contact_consent,
    })
    audit(conn, "representative_claim", "circle_claim", claim_id, {
        "circle_id": circle_id,
        "audience": audience,
        "claimant_name": claimant_name,
        "claimant_email": claimant_email,
        "evidence_url": data.get("evidence_url", ""),
        "message": data.get("message", ""),
    })
    verification_url = social_representative_verification_mailto(claim_id, circle_name) if is_social else verification_mailto(claim_id, circle_name, university_name)
    return claim_id, circle_id, verification_url, is_social


def representative_claim_rows():
    return rows("""
        select cc.claim_id, cc.claimant_name, cc.claimant_email, cc.university_email_verified,
          cc.university_email_domain_checked, cc.university_email_verified_at, cc.status, cc.evidence_url,
          cc.reviewed_at, cc.created_at, c.circle_id, c.circle_name, c.sport_category,
          u.university_name, u.prefecture, c.organization_type
        from circle_claims cc
        join circles c on c.circle_id=cc.circle_id
        join universities u on u.university_id=c.university_id
        order by
          case cc.status when 'pending' then 0 when 'university_email_verified' then 1 else 2 end,
          cc.created_at desc
    """)


def mark_claim_university_email_verified(conn, claim_id):
    row = conn.execute("select circle_id, claimant_email from circle_claims where claim_id=?", (claim_id,)).fetchone()
    if not row:
        raise ValueError("representative claim not found")
    timestamp = now()
    conn.execute(
        """
        update circle_claims
        set university_email_verified=1, university_email_verified_at=?, status='university_email_verified',
          reviewed_at=?, updated_at=?
        where claim_id=?
        """,
        (timestamp, timestamp, timestamp, claim_id),
    )
    conn.execute(
        "update circles set verification_status='admin_verified', last_checked_at=?, updated_at=? where circle_id=?",
        (timestamp[:10], timestamp, row["circle_id"]),
    )
    audit(conn, "university_email_verified", "circle_claim", claim_id, {"circle_id": row["circle_id"]})


def remove_demo_content(conn):
    """Remove legacy demonstration records from the production data set once."""
    demo_circle_ids = [
        row["circle_id"]
        for row in conn.execute(
            """
            select c.circle_id
            from circles c
            join universities u on u.university_id=c.university_id
            where c.public_status='demo'
               or c.circle_id like 'circle_demo_%'
               or u.university_name in ('Circle Match デモ大学', 'Circle Match 社会人デモ団体')
            """
        ).fetchall()
    ]
    if not demo_circle_ids:
        return
    placeholders = ",".join("?" for _ in demo_circle_ids)
    conn.execute(f"delete from match_posts where circle_id in ({placeholders})", demo_circle_ids)
    conn.execute(f"delete from circles where circle_id in ({placeholders})", demo_circle_ids)
    # Keep the empty legacy university rows: collection targets may still
    # reference them, while all public counts are derived from circles.
    log(f"removed {len(demo_circle_ids)} legacy demo circles and their match posts")


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


def seed_demo_match_posts(conn):
    """Create clearly labelled sample posts without polluting the public DB."""
    timestamp = now()
    base_date = datetime.now(timezone.utc).date()
    demo_university_id = upsert_university(conn, {
        "university_name": "Circle Match デモ大学",
        "prefecture": "東京都",
        "city": "渋谷区",
        "campus_name": "サンプルキャンパス",
    }, audit=False)

    samples = [
        ("demo_baseball", "【サンプル】デモ野球サークル", "野球", "非公認サークル", 7, "練習試合", "中級", "東京都江東区・夢の島野球場", "9イニングまたは7イニング。ユニフォーム不問で、試合後の合同練習も歓迎です。"),
        ("demo_tennis", "【サンプル】デモテニスサークル", "テニス", "非公認サークル", 10, "合同練習", "初級〜中級", "東京都世田谷区・区営テニスコート", "ダブルス中心の合同練習です。コート代は参加団体で分担します。"),
        ("demo_pickleball", "【サンプル】デモピックルボールサークル", "ピックルボール", "非公認サークル", 14, "合同練習", "初心者歓迎", "東京都品川区・屋内スポーツ施設", "ルール説明から一緒に行う体験・合同練習会です。"),
        ("demo_running", "【サンプル】デモランニングサークル", "ランニング", "非公認サークル", 18, "助っ人募集", "レベル不問", "東京都千代田区・皇居外周", "5kmまたは10kmのペース走。給水係を含む助っ人も募集しています。"),
    ]
    social_university_id = upsert_university(conn, {
        "university_name": "Circle Match 社会人デモ団体",
        "prefecture": "東京都",
        "city": "品川区",
        "campus_name": "社会人サークル",
    }, audit=False)
    samples.extend([
        ("demo_social_futsal", "【サンプル】デモ社会人フットサル", "サッカー・フットサル", SOCIAL_AUDIENCE_TYPE, 9, "合同練習", "初級〜中級", "東京都品川区・屋内フットサルコート", "仕事帰りの1.5時間練習。初参加の方も歓迎です。"),
        ("demo_social_badminton", "【サンプル】デモ社会人バドミントン", "バドミントン", SOCIAL_AUDIENCE_TYPE, 16, "助っ人募集", "初級〜中級", "東京都目黒区・区民体育館", "ダブルス中心。ラケット貸出あり、1名から参加できます。"),
    ])

    for sample_id, circle_name, sport, organization_type, days, match_type, level, place, detail in samples:
        university_id = social_university_id if organization_type == SOCIAL_AUDIENCE_TYPE else demo_university_id
        circle_id = f"circle_{sample_id}"
        upsert_circle(conn, {
            "circle_id": circle_id,
            "university_id": university_id,
            "circle_name": circle_name,
            "organization_type": organization_type,
            "sport_category": sport,
            "activity_area": place,
            "source_type": "other",
            "verification_status": "unverified",
            "public_status": "demo",
            "last_checked_at": timestamp[:10],
        }, audit_entry=False)
        scheduled_at = f"{(base_date + timedelta(days=days)).isoformat()} 18:00"
        conn.execute(
            """
            insert into match_posts(match_post_id, circle_id, match_type, level_label, scheduled_at,
              period_start, period_end, place, practice_detail, capacity, conditions, status, created_at, updated_at)
            values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            on conflict(match_post_id) do update set
              match_type=excluded.match_type,
              level_label=excluded.level_label,
              scheduled_at=excluded.scheduled_at,
              period_start=excluded.period_start,
              period_end=excluded.period_end,
              place=excluded.place,
              practice_detail=excluded.practice_detail,
              conditions=excluded.conditions,
              status=excluded.status,
              updated_at=excluded.updated_at
            """,
            (
                f"match_{sample_id}", circle_id, match_type, level, scheduled_at,
                scheduled_at, scheduled_at, place, detail, "1団体または個人", f"【サンプル募集】{detail}",
                "open", timestamp, timestamp,
            ),
        )


def seed_collection_targets(conn):
    timestamp = now()
    universities = conn.execute("select university_id, university_name, prefecture from universities").fetchall()
    for university in universities:
        count = conn.execute(
            "select count(*) from circles where university_id=? and coalesce(public_status, 'published')<>'demo'",
            (university["university_id"],),
        ).fetchone()[0]
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
        self.send_header("Cache-Control", "no-store")
        for cookie in cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, body, status=200):
        body = personalize_navigation(body, self.cookie_value("cm_session"), self.path)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, max-age=0, must-revalidate")
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
        event_request = urlparse(self.path).path.startswith('/api/events')
        if event_request:
            origin = self.headers.get('Origin', '')
            host = self.headers.get('Host', '')
            if (self.headers.get('Sec-Fetch-Site') == 'cross-site' or
                    (origin and origin not in {f'https://{host}', f'http://{host}'})):
                raise PermissionError('別サイトからの操作は受け付けられません')
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                raise ValueError('JSON形式で送信してください')
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or (event_request and length > 65536):
            raise ValueError('送信内容が大きすぎます')
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
        if self.path.startswith("/_tweet-bot/"):
            from chatgpt_bridge import handle_http
            handle_http(self)
            return
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                self.send_html(render_public_html(query))
            elif parsed.path == "/events":
                query["tab"] = ["events"]
                self.send_html(render_public_html(query, event_listing=True))
            elif parsed.path == "/events/new":
                user = current_user(self.cookie_value("cm_session"))
                if not user.get("authenticated"):
                    self.redirect("/signin?" + urlencode({"return_to": safe_return_path(self.path, "/events/new")}))
                    return
                page = render_event_form_html(query, user)
                if page:
                    self.send_html(page.encode("utf-8"))
                else:
                    self.send_html(event_page("ログインが必要です", '<div class="error-box">編集するにはログインしてください。</div>').encode("utf-8"), 401)
            elif parsed.path.startswith("/events/"):
                parts = [unquote(part) for part in parsed.path.strip("/").split("/")]
                if len(parts) in {3, 4} and parts[2] in {"applications", "contact"}:
                    user = current_user(self.cookie_value("cm_session"))
                    if not user.get("authenticated"):
                        self.redirect("/signin?" + urlencode({"return_to": safe_return_path(self.path, "/")}))
                        return
                    if parts[2] == "contact" and len(parts) == 3:
                        page = render_event_contact_html(parts[1], user, query.get("peer_user_id", [""])[0])
                    elif parts[2] == "applications":
                        page = render_event_application_operations(parts[1], user, parts[3] if len(parts) == 4 else "")
                    else:
                        raise ValueError("ページが見つかりません")
                    self.send_html(page.encode("utf-8"))
                elif len(parts) == 3 and parts[2] in {"organize", "attendance"}:
                    user = current_user(self.cookie_value("cm_session"))
                    if not user.get("authenticated"):
                        self.redirect("/signin?" + urlencode({"return_to": safe_return_path(self.path, "/")}))
                        return
                    page = render_event_organize_html(parts[1], user) if parts[2] == "organize" else render_event_attendance_html(parts[1], user)
                    self.send_html(page.encode("utf-8"))
                elif len(parts) == 3 and parts[2] == "apply":
                    user = current_user(self.cookie_value("cm_session"))
                    if not user.get("authenticated"):
                        self.redirect("/signin?" + urlencode({"return_to": safe_return_path(self.path, "/")}))
                        return
                    page = render_event_apply_html(parts[1], user)
                    if page:
                        self.send_html(page.encode("utf-8"))
                    else:
                        self.send_html(event_page("募集が見つかりません", '<div class="error-box">募集が見つからないか、現在受け付けていません。</div>').encode("utf-8"), 404)
                elif len(parts) == 2:
                    page = render_event_detail_html(parts[1], current_user(self.cookie_value("cm_session")))
                    if page:
                        self.send_html(page.encode("utf-8"))
                    else:
                        self.send_html(event_page("募集が見つかりません", '<div class="error-box">募集が見つかりません。</div>').encode("utf-8"), 404)
                else:
                    self.send_json({"error": "not found"}, 404)
            elif parsed.path == "/mypage":
                if query.get("tab") == ["notifications"]:
                    self.redirect("/notifications")
                    return
                user = current_user(self.cookie_value("cm_session"))
                if not user.get("authenticated"):
                    self.redirect("/signin?" + urlencode({"return_to": "/mypage"}))
                    return
                self.send_html(render_mypage_html(user).encode("utf-8"))
            elif parsed.path == "/notifications":
                user = current_user(self.cookie_value("cm_session"))
                if not user.get("authenticated"):
                    self.redirect("/signin?" + urlencode({"return_to": "/notifications"}))
                    return
                try:
                    page = max(0, int(query.get("page", ["0"])[0]))
                except ValueError:
                    page = 0
                self.send_html(render_notifications_html(user, page).encode("utf-8"))
            elif parsed.path == "/signin":
                self.send_html(render_signin_html(safe_return_path(query.get("return_to", ["/"])[0])))
            elif parsed.path == "/logout":
                session_id = self.cookie_value("cm_session")
                body = ('<h1>ログアウト</h1><p>この端末のCircle Matchからログアウトします。</p>'
                        '<form method="post" action="/logout">'
                        f'<input type="hidden" name="csrf_token" value="{logout_token(session_id)}">'
                        '<button class="button" type="submit">ログアウトする</button></form>')
                self.send_html(event_page("ログアウト", body).encode("utf-8"))
            elif parsed.path == "/auth/google":
                self.redirect("/signin?" + urlencode({"return_to": safe_return_path(query.get("return_to", ["/"])[0])}))
            elif parsed.path == "/auth/google/callback":
                self.handle_google_callback(query)
            elif parsed.path == "/post-match":
                self.redirect("/events/new" + (("?" + urlencode({key: values[0] for key, values in query.items() if values and key in {"sport", "region", "prefecture"}})) if query else ""))
            elif parsed.path == "/representative":
                self.send_html(render_representative_html())
            elif parsed.path == "/social/circles":
                self.send_html(render_social_circles_html())
            elif parsed.path == "/social/sports":
                sport = (parse_qs(parsed.query).get("sport", ["野球"])[0] or "野球").strip()
                self.send_html(render_social_sport_html(sport))
            elif parsed.path == "/social":
                self.send_html(render_social_html())
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
            elif parsed.path == "/assets/hero-social-adults.png":
                self.send_file(ROOT / "hero-social-adults.png", "image/png")
            elif parsed.path == "/assets/circle-match-mark.png":
                self.send_file(ROOT / "circle-match-mark.png", "image/png")
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
            elif parsed.path == "/operator":
                self.send_html(operator_page())
            elif parsed.path == "/guides":
                self.send_html(guides_page())
            elif parsed.path.startswith("/guides/"):
                guide_slug = unquote(parsed.path.removeprefix("/guides/").strip("/"))
                page = guide_page(guide_slug)
                if page:
                    self.send_html(page)
                else:
                    self.send_html("<h1>記事が見つかりません</h1>".encode("utf-8"), 404)
            elif parsed.path == "/healthz":
                self.send_json({"ok": True, **summary()})
            elif parsed.path == "/robots.txt":
                self.send_text(robots_txt())
            elif parsed.path == "/ads.txt":
                self.send_text(ADSENSE_ADS_TXT)
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
                params = parse_qs(parsed.query)
                try:
                    limit = int((params.get("limit", ["120"])[0] or "120").strip())
                except ValueError:
                    limit = 120
                try:
                    offset = int((params.get("offset", ["0"])[0] or "0").strip())
                except ValueError:
                    offset = 0
                self.send_json(search_circles(params, limit=max(1, min(limit, 200)), offset=max(0, offset)))
            elif parsed.path == "/api/circle-stats":
                self.send_json(circle_query_stats(parse_qs(parsed.query)))
            elif parsed.path == "/api/region-counts":
                self.send_json(region_counts(parse_qs(parsed.query)))
            elif parsed.path == "/api/circle-search":
                params = parse_qs(parsed.query)
                query = (params.get("q", [""])[0] or "").strip()
                self.send_json(search_circles(params, limit=12) if len(query) >= 2 else [])
            elif parsed.path == "/api/matches":
                params = parse_qs(parsed.query)
                try:
                    limit = int((params.get("limit", ["100"])[0] or "100").strip())
                except ValueError:
                    limit = 100
                self.send_json(search_matches(params, limit=max(1, min(limit, 200))))
            elif parsed.path == "/api/events":
                try:
                    limit = int((query.get("limit", ["60"])[0] or "60").strip())
                except ValueError:
                    limit = 60
                self.send_json(search_events(query, limit=max(1, min(limit, 100))))
            elif parsed.path == "/api/events/mine":
                user = current_user(self.cookie_value("cm_session"))
                if not user.get("authenticated"):
                    self.send_json({"error": "login required"}, 401)
                    return
                self.send_json(event_my_page(user))
            elif parsed.path == "/api/notifications/unread":
                user = current_user(self.cookie_value("cm_session"))
                if not user.get("authenticated"):
                    self.send_json({"error": "login required"}, 401)
                    return
                self.send_json({"unread_count": unread_notification_count(user)})
            elif parsed.path == "/api/my-organizations":
                self.send_json(claimed_circles_for_user(current_user(self.cookie_value("cm_session"))))
            elif parsed.path.startswith("/api/events/"):
                parts = [unquote(part) for part in parsed.path.strip("/").split("/")]
                user = current_user(self.cookie_value("cm_session"))
                if len(parts) == 3:
                    event = get_event(parts[2])
                    self.send_json(event if event else {"error": "not found"}, 200 if event else 404)
                elif len(parts) == 4 and parts[3] == "applications":
                    if not user.get("authenticated"):
                        self.send_json({"error": "login required"}, 401)
                        return
                    self.send_json(event_applications_for_owner(parts[2], user))
                elif len(parts) == 4 and parts[3] == "messages":
                    if not user.get("authenticated"):
                        self.send_json({"error": "login required"}, 401)
                        return
                    self.send_json(event_messages_for_user(parts[2], user, (query.get("peer_user_id", [""])[0] or "").strip()))
                else:
                    self.send_json({"error": "not found"}, 404)
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
            elif parsed.path == "/api/claims":
                if not self.require_admin():
                    return
                self.send_json(representative_claim_rows())
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
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, 403)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            log(f"GET {parsed.path} failed: {type(exc).__name__}: {exc}")
            self.send_json({"error": "server error"}, 500)

    def do_POST(self):
        if self.path.startswith("/_tweet-bot/"):
            from chatgpt_bridge import handle_http
            handle_http(self)
            return
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/logout":
                session_id = self.cookie_value("cm_session")
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 2048:
                    self.send_json({"error": "invalid request"}, 400)
                    return
                form = parse_qs(self.rfile.read(length).decode("utf-8"))
                token = form.get("csrf_token", [""])[0]
                if not hmac.compare_digest(token, logout_token(session_id)):
                    self.send_json({"error": "ページを再読み込みしてからログアウトしてください"}, 403)
                    return
                with connect() as conn:
                    conn.execute("update user_sessions set expires_at=datetime('now') where session_id=?", (session_id,))
                self.redirect("/", [f"cm_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax{secure_cookie_suffix()}"])
                return
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
            if parsed.path == "/api/notifications/read":
                data = self.read_json()
                user = current_user(self.cookie_value("cm_session"))
                if not user.get("authenticated"):
                    self.send_json({"error": "login required"}, 401)
                    return
                ids = data.get("notification_ids", [])
                if not isinstance(ids, list) or len(ids) > 50 or any(not isinstance(value, str) for value in ids):
                    raise ValueError("通知の指定が正しくありません")
                with connect() as conn:
                    conn.executemany("update event_notifications set read_at=? where notification_id=? and recipient_user_id=? and read_at is null",
                                     [(now(), value, user["user_id"]) for value in ids])
                self.send_json({"ok": True, "unread_count": unread_notification_count(user)})
                return
            if parsed.path == "/api/events":
                data = self.read_json()
                user = current_user(self.cookie_value("cm_session"))
                if not user.get("authenticated"):
                    self.send_json({"error": "login required"}, 401)
                    return
                with connect() as conn:
                    event_id = save_event_post(conn, data, user)
                    conn.commit()
                self.send_json({"ok": True, "event_id": event_id})
                return
            if parsed.path.startswith("/api/events/"):
                parts = [unquote(part) for part in parsed.path.strip("/").split("/")]
                data = self.read_json()
                user = current_user(self.cookie_value("cm_session"))
                if not user.get("authenticated"):
                    self.send_json({"error": "login required"}, 401)
                    return
                if len(parts) == 4 and parts[3] in {"announce", "attendance"}:
                    with connect() as conn:
                        if parts[3] == "announce":
                            announce_event(conn, parts[2], data, user)
                        else:
                            confirm_event_attendance(conn, parts[2], data, user)
                        conn.commit()
                    self.send_json({"ok": True})
                    return
                if len(parts) == 4 and parts[3] == "applications":
                    with connect() as conn:
                        result = submit_event_application(conn, parts[2], data, user)
                        conn.commit()
                    self.send_json({"ok": True, **result})
                    return
                if len(parts) == 6 and parts[3] == "applications" and parts[5] == "status":
                    with connect() as conn:
                        next_status = set_event_application_status(conn, parts[2], parts[4], data.get("action", ""), user, data.get("organizer_note", ""))
                        conn.commit()
                    self.send_json({"ok": True, "status": next_status})
                    return
                if len(parts) == 6 and parts[3] == "applications" and parts[5] == "cancel":
                    with connect() as conn:
                        cancel_event_application(conn, parts[2], parts[4], user)
                        conn.commit()
                    self.send_json({"ok": True})
                    return
                if len(parts) == 6 and parts[3] == "applications" and parts[5] in {"count", "count-review", "payment", "release"}:
                    with connect() as conn:
                        if parts[5] == "count":
                            result = change_application_count(conn, parts[2], parts[4], data, user)
                        elif parts[5] == "count-review":
                            decision = data.get("decision")
                            if decision not in {"approve", "decline"}:
                                raise ValueError("人数変更の処理を選んでください")
                            result = change_application_count(conn, parts[2], parts[4], data, user, decision)
                        elif parts[5] == "payment":
                            result = set_application_payment(conn, parts[2], parts[4], data, user)
                        else:
                            result = release_unconfirmed_application(conn, parts[2], parts[4], data, user)
                        conn.commit()
                    self.send_json({"ok": True, "result": result})
                    return
                if len(parts) == 4 and parts[3] == "status":
                    with connect() as conn:
                        set_event_status(conn, parts[2], data.get("status", ""), user)
                        conn.commit()
                    self.send_json({"ok": True})
                    return
                if len(parts) == 4 and parts[3] == "messages":
                    with connect() as conn:
                        message_id = send_event_message(conn, parts[2], data, user)
                        conn.commit()
                    self.send_json({"ok": True, "message_id": message_id})
                    return
                self.send_json({"error": "not found"}, 404)
                return
            if parsed.path == "/api/claims":
                data = self.read_json()
                with connect() as conn:
                    claim_id, circle_id, verification_mailto_url, is_social = create_circle_claim(conn, data)
                    conn.commit()
                    self.send_json({
                        "ok": True,
                        "claim_id": claim_id,
                        "circle_id": circle_id,
                        "profile_url": f"/circles/{quote(circle_id)}",
                        "verification_mailto": verification_mailto_url,
                        "verification_label": "代表者メールから確認メール" if is_social else "大学メールから確認メール",
                        "verification_note": "入力した代表者メールのアカウントから送信してください。運営が差出人を確認した後に「代表者メール確認済み」と表示します。" if is_social else "入力した大学メールアドレスのアカウントから送信してください。運営が差出人を確認した後に「大学メール確認済み」と表示します。",
                    })
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
                elif parsed.path == "/api/claims/verify":
                    mark_claim_university_email_verified(conn, data.get("claim_id", ""))
                    conn.commit()
                    self.send_json({"ok": True})
                else:
                    self.send_json({"error": "not found"}, 404)
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, 403)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception as exc:
            log(f"POST {parsed.path} failed: {type(exc).__name__}: {exc}")
            self.send_json({"error": "server error"}, 500)


SOCIAL_AUDIENCE_TYPE = "社会人サークル"


def audience_scope(params, default="all"):
    """Read the public audience scope without allowing a mixed-page fallback."""
    if isinstance(params, dict):
        value = params.get("audience", [default])
        audience = value[0] if isinstance(value, list) else value
    else:
        audience = params
    audience = (audience or default).strip()
    return audience if audience in {"all", "university", "social"} else default


def audience_clause(audience, alias="c"):
    if audience == "university":
        return f"coalesce({alias}.organization_type, '')<>?", [SOCIAL_AUDIENCE_TYPE]
    if audience == "social":
        return f"{alias}.organization_type=?", [SOCIAL_AUDIENCE_TYPE]
    return "", []


# Exact source records identified during the UX audit; approval restores visibility
# without rewriting or deleting the source record or its original verification flag.
LISTING_REVIEW_SOURCES = {
    "https://circle-book.com/circles/68885", "https://circle-book.com/circles/72830",
    "https://circle-book.com/circles/74139", "https://circle-book.com/circles/46401",
    "https://circle-book.com/circles/73839", "https://circle-book.com/circles/73747",
    "https://circle-book.com/circles/73788", "https://circle-book.com/circles/72173",
    "https://circle-book.com/circles/65966", "https://circle-book.com/circles/66812",
}


def public_circle_clause(alias="c"):
    return f"(coalesce({alias}.public_status, 'published')<>'demo' and not exists (select 1 from circle_listing_reviews lr where lr.circle_id={alias}.circle_id and lr.review_status='pending'))"


def current_open_match_clause(alias="m"):
    """Keep closed and expired postings out of public counts and results."""
    return f"""
        {alias}.status='open'
        and (
          (coalesce(trim({alias}.period_end), '')<>''
           and substr({alias}.period_end, 1, 10)>=date('now', 'localtime'))
          or
          (coalesce(trim({alias}.period_end), '')=''
           and (coalesce(trim({alias}.scheduled_at), '')=''
                or substr({alias}.scheduled_at, 1, 10)>=date('now', 'localtime')))
        )
    """


def summary(audience="all"):
    audience = audience_scope(audience)
    circle_scope, audience_args = audience_clause(audience, "c")
    filters = [public_circle_clause("c")]
    if circle_scope:
        filters.append(circle_scope)
    where = " where " + " and ".join(filters)
    args = audience_args
    verified_where = f"{where}{' and ' if where else ' where '}c.verification_status in ('claimed','university_verified','admin_verified')"
    match_filters = [public_circle_clause("c"), current_open_match_clause("m")]
    if circle_scope:
        match_filters.append(circle_scope)
    match_where = " where " + " and ".join(match_filters)
    with connect() as conn:
        return {
            "prefectures": conn.execute(
                f"select count(distinct u.prefecture) from circles c join universities u on u.university_id=c.university_id{where}", args
            ).fetchone()[0],
            "universities": conn.execute(
                f"select count(distinct c.university_id) from circles c{where}", args
            ).fetchone()[0],
            "circles": conn.execute(f"select count(*) from circles c{where}", args).fetchone()[0],
            "verified_circles": conn.execute(f"select count(*) from circles c{verified_where}", args).fetchone()[0],
            "circle_candidates": conn.execute("select count(*) from circle_candidates").fetchone()[0] if audience == "all" else 0,
            "match_posts": conn.execute(
                f"select count(*) from match_posts m join circles c on c.circle_id=m.circle_id{match_where}", audience_args
            ).fetchone()[0],
        }


def social_summary():
    """Summary values for the social-circle top page's server-rendered metrics."""
    organization_type = SOCIAL_AUDIENCE_TYPE
    with connect() as conn:
        return {
            "prefectures": conn.execute(
                """select count(distinct u.prefecture)
                   from circles c join universities u on u.university_id=c.university_id
                   where c.organization_type=? and """ + public_circle_clause("c"),
                (organization_type,),
            ).fetchone()[0],
            # The existing client contract calls this field universities. On the
            # social page it represents the number of covered activity regions.
            "universities": conn.execute(
                """select count(distinct u.prefecture)
                   from circles c join universities u on u.university_id=c.university_id
                   where c.organization_type=? and """ + public_circle_clause("c"),
                (organization_type,),
            ).fetchone()[0],
            "circles": conn.execute(
                "select count(*) from circles c where organization_type=? and " + public_circle_clause("c"),
                (organization_type,),
            ).fetchone()[0],
            "verified_circles": conn.execute(
                """select count(*) from circles c
                   where organization_type=?
                     and (verification_status='claimed'
                          or (public_status='published' and coalesce(source_url, '')<>'')) and """ + public_circle_clause("c"),
                (organization_type,),
            ).fetchone()[0],
            "match_posts": conn.execute(
                """select count(*) from match_posts m
                   join circles c on c.circle_id=m.circle_id
                   where c.organization_type=? and """ + public_circle_clause("c") + " and " + current_open_match_clause("m"),
                (organization_type,),
            ).fetchone()[0],
        }


def sport_options(audience="all"):
    audience = audience_scope(audience)
    scope, args = audience_clause(audience)
    where = f" where {public_circle_clause()}"
    if scope:
        where += f" and {scope}"
    with connect() as conn:
        db_sports = [
            row["sport_category"]
            for row in conn.execute(
                f"select c.sport_category from circles c{where}{' and ' if where else ' where '}c.sport_category is not null and c.sport_category<>'' group by c.sport_category order by count(*) desc, c.sport_category",
                args,
            ).fetchall()
        ]
    return list(dict.fromkeys([*SPORTS, *db_sports]))


def region_options():
    return [{"value": key, "label": data["label"], "prefectures": data["prefectures"]} for key, data in REGION_GROUPS.items()]


def region_prefectures(region):
    return REGION_GROUPS.get(region, {}).get("prefectures", [])


def circle_query_conditions(params):
    query = (params.get("q", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    region = (params.get("region", [""])[0] or "").strip()
    organization_type = (params.get("organization_type", [""])[0] or "").strip()
    sport = (params.get("sport", [""])[0] or "").strip()
    status = (params.get("status", [""])[0] or "").strip()
    audience = audience_scope(params)
    where = [public_circle_clause("c")]
    args = []
    scope, scope_args = audience_clause(audience, "c")
    if scope:
        where.append(scope)
        args.extend(scope_args)
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
        where.append("c.sport_category like ?")
        args.append(f"%{sport}%")
    if status:
        where.append("c.verification_status=?")
        args.append(status)
    return where, args


def circle_query_stats(params):
    where, args = circle_query_conditions(params)
    sql = """
        select
          count(*) as circles,
          count(distinct c.university_id) as universities,
          count(distinct u.prefecture) as prefectures,
          count(distinct c.sport_category) as sports,
          sum(case when c.verification_status in ('claimed','university_verified','admin_verified') then 1 else 0 end) as verified_circles
        from circles c join universities u on u.university_id=c.university_id
    """
    if where:
        sql += " where " + " and ".join(where)
    with connect() as conn:
        row = conn.execute(sql, args).fetchone()
    return {key: int(row[key] or 0) for key in row.keys()}


def search_circles(params, limit=None, offset=0):
    sort = (params.get("sort", ["university"])[0] or "university").strip()
    where, args = circle_query_conditions(params)
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
          case when p.public_contact_consent=1 then p.public_contact_email else '' end as public_contact_email,
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
    if limit is not None:
        sql += " limit ?"
        args.append(max(1, min(int(limit), 200)))
        if offset:
            sql += " offset ?"
            args.append(max(0, int(offset)))
    result = rows(sql, args)
    for row in result:
        row["profile_url"] = f"/circles/{quote(row['profile_slug'])}" if row.get("profile_slug") else ""
    return result


def region_counts(params):
    """Return compact map data without transferring every circle to the browser."""
    audience = audience_scope(params, "university")
    scope, audience_args = audience_clause(audience, "c")
    circle_filters = [public_circle_clause("c")]
    if scope:
        circle_filters.append(scope)
    circle_where = " where " + " and ".join(circle_filters)
    match_filters = [public_circle_clause("c"), current_open_match_clause("m")]
    if scope:
        match_filters.append(scope)
    match_where = " where " + " and ".join(match_filters)
    with connect() as conn:
        circle_rows = conn.execute(
            """
            select u.prefecture, count(*) as count
            from circles c join universities u on u.university_id=c.university_id
            """ + circle_where + " group by u.prefecture",
            audience_args,
        ).fetchall()
        match_rows = conn.execute(
            """
            select u.prefecture, count(*) as count
            from match_posts m join circles c on c.circle_id=m.circle_id
            join universities u on u.university_id=c.university_id
            """ + match_where + " group by u.prefecture",
            audience_args,
        ).fetchall()
    circle_by_prefecture = {row["prefecture"]: row["count"] for row in circle_rows}
    match_by_prefecture = {row["prefecture"]: row["count"] for row in match_rows}
    return [
        {
            "value": key,
            "label": data["label"],
            "circle_count": sum(circle_by_prefecture.get(prefecture, 0) for prefecture in data["prefectures"]),
            "match_count": sum(match_by_prefecture.get(prefecture, 0) for prefecture in data["prefectures"]),
        }
        for key, data in REGION_GROUPS.items()
    ]


def match_query_conditions(params):
    sport = (params.get("sport", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    region = (params.get("region", [""])[0] or "").strip()
    organization_type = (params.get("organization_type", [""])[0] or "").strip()
    audience = audience_scope(params)
    where = [public_circle_clause("c"), current_open_match_clause("m")]
    args = []
    scope, scope_args = audience_clause(audience, "c")
    if scope:
        where.append(scope)
        args.extend(scope_args)
    if sport:
        where.append("c.sport_category like ?")
        args.append(f"%{sport}%")
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
    return where, args


def match_query_count(params):
    where, args = match_query_conditions(params)
    sql = """
        select count(*) as count
        from match_posts m join circles c on c.circle_id=m.circle_id
        join universities u on u.university_id=c.university_id
    """
    if where:
        sql += " where " + " and ".join(where)
    with connect() as conn:
        return int(conn.execute(sql, args).fetchone()["count"] or 0)


def grouped_circle_counts(params, group):
    field = {
        "prefecture": "u.prefecture",
        "sport": "c.sport_category",
    }.get(group)
    if not field:
        raise ValueError("unsupported circle count group")
    where, args = circle_query_conditions(params)
    sql = f"""
        select {field} as value, count(*) as count
        from circles c join universities u on u.university_id=c.university_id
    """
    if where:
        sql += " where " + " and ".join(where)
    sql += f" group by {field}"
    with connect() as conn:
        return {row["value"]: int(row["count"] or 0) for row in conn.execute(sql, args).fetchall()}


def grouped_match_counts(params, group):
    field = {
        "prefecture": "u.prefecture",
        "sport": "c.sport_category",
    }.get(group)
    if not field:
        raise ValueError("unsupported match count group")
    where, args = match_query_conditions(params)
    sql = f"""
        select {field} as value, count(*) as count
        from match_posts m join circles c on c.circle_id=m.circle_id
        join universities u on u.university_id=c.university_id
    """
    if where:
        sql += " where " + " and ".join(where)
    sql += f" group by {field}"
    with connect() as conn:
        return {row["value"]: int(row["count"] or 0) for row in conn.execute(sql, args).fetchall()}


def search_matches(params, limit=None):
    where, args = match_query_conditions(params)
    sql = """
        select m.*, c.circle_name, c.sport_category, u.university_name, u.prefecture
        from match_posts m join circles c on c.circle_id=m.circle_id join universities u on u.university_id=c.university_id
    """
    if where:
        sql += " where " + " and ".join(where)
    sql += " order by coalesce(m.scheduled_at, ''), m.created_at desc"
    if limit is not None:
        sql += " limit ?"
        args.append(max(1, min(int(limit), 200)))
    return rows(sql, args)


def sport_overview(params):
    sport = (params.get("sport", ["野球"])[0] or "野球").strip()
    region = (params.get("region", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    organization_type = (params.get("organization_type", [""])[0] or "").strip()
    audience = audience_scope(params, "university")
    if prefecture:
        matching_region = next((key for key, data in REGION_GROUPS.items() if prefecture in data["prefectures"]), "")
        if region and prefecture not in region_prefectures(region):
            prefecture = ""
        elif not region:
            region = matching_region
    scope = {"sport": [sport], "audience": [audience]}
    if organization_type:
        scope["organization_type"] = [organization_type]
    region_scope = {**scope, "region": [region]}
    current_scope = {**region_scope, "prefecture": [prefecture]}
    all_circle_counts = grouped_circle_counts(scope, "prefecture")
    all_match_counts = grouped_match_counts(scope, "prefecture")
    region_circle_counts = grouped_circle_counts(region_scope, "prefecture")
    region_match_counts = grouped_match_counts(region_scope, "prefecture")
    current_stats = circle_query_stats(current_scope)
    circles = search_circles(current_scope, limit=120)
    matches = search_matches(current_scope, limit=50)
    region_summaries = []
    for key, data in REGION_GROUPS.items():
        circle_count = sum(all_circle_counts.get(pref, 0) for pref in data["prefectures"])
        match_count = sum(all_match_counts.get(pref, 0) for pref in data["prefectures"])
        region_summaries.append({
            "value": key,
            "label": data["label"],
            "circle_count": circle_count,
            "match_count": match_count,
        })
    areas = []
    region_prefs = region_prefectures(region)
    for pref in region_prefs if region_prefs else PREFECTURES:
        circle_count = region_circle_counts.get(pref, 0)
        match_count = region_match_counts.get(pref, 0)
        if circle_count or match_count or region:
            areas.append({"prefecture": pref, "circle_count": circle_count, "match_count": match_count})
    return {
        "sport": sport,
        "region": region,
        "prefecture": prefecture,
        "circle_count": current_stats["circles"],
        "match_count": match_query_count(current_scope),
        "regions": region_summaries,
        "areas": areas,
        "matches": matches,
        "circles": circles,
    }


def region_overview(params):
    region = (params.get("region", ["kanto"])[0] or "kanto").strip()
    if region not in REGION_GROUPS:
        region = "kanto"
    sport = (params.get("sport", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    audience = audience_scope(params, "university")
    if prefecture and prefecture not in region_prefectures(region):
        prefecture = ""
    region_label = REGION_GROUPS[region]["label"]
    base_scope = {"region": [region], "audience": [audience]}
    current_scope = {**base_scope, "sport": [sport], "prefecture": [prefecture]}
    region_stats = circle_query_stats(base_scope)
    region_circle_counts = grouped_circle_counts(base_scope, "sport")
    region_match_counts = grouped_match_counts(base_scope, "sport")
    current_stats = circle_query_stats(current_scope)
    circles = search_circles(current_scope, limit=120)
    matches = search_matches(current_scope, limit=50)
    sports = []
    for name in sport_options(audience):
        circle_count = region_circle_counts.get(name, 0)
        match_count = region_match_counts.get(name, 0)
        if circle_count or match_count or name in SPORTS:
            sports.append({
                "name": name,
                "circle_count": circle_count,
                "match_count": match_count,
            })
    sports.sort(key=lambda item: (-item["circle_count"], -item["match_count"], item["name"]))
    scoped_scope = {**base_scope, "sport": [sport]}
    scoped_circle_counts = grouped_circle_counts(scoped_scope, "prefecture")
    scoped_match_counts = grouped_match_counts(scoped_scope, "prefecture")
    areas = []
    for pref in region_prefectures(region):
        circle_count = scoped_circle_counts.get(pref, 0)
        match_count = scoped_match_counts.get(pref, 0)
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
        "region_circle_count": region_stats["circles"],
        "region_match_count": match_query_count(base_scope),
        "circle_count": current_stats["circles"],
        "match_count": match_query_count(current_scope),
        "sports": sports,
        "areas": areas,
        "matches": matches,
        "circles": circles,
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


def safe_return_path(value, fallback="/"):
    """Allow only same-site relative paths after an authentication hand-off."""
    value = (value or "").strip()
    if value.startswith("/") and not value.startswith("//") and "\r" not in value and "\n" not in value:
        return value
    return fallback


def event_datetime(value, field, required=True):
    value = (value or "").strip()
    if not value:
        if required:
            raise ValueError(f"{field}を入力してください")
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}の形式が正しくありません") from exc
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M")


def event_form_value(data, key, label, required=False, max_length=5000):
    value = str(data.get(key) or "").strip()
    if required and not value:
        raise ValueError(f"{label}を入力してください")
    if len(value) > max_length:
        raise ValueError(f"{label}は{max_length}文字以内で入力してください")
    return value


def event_capacity_value(data):
    raw = str(data.get("capacity") or "").strip()
    if not raw:
        return None
    try:
        capacity = int(raw)
    except ValueError as exc:
        raise ValueError("定員は整数で入力してください") from exc
    if capacity < 1 or capacity > 100000:
        raise ValueError("定員は1から100000の範囲で入力してください")
    return capacity


def event_fee_value(data, key="fee_amount", label="参加費", maximum=10000000):
    raw = str(data.get(key) if data.get(key) is not None else "").strip()
    raw = raw.translate(str.maketrans("０１２３４５６７８９，", "0123456789,")).replace(",", "")
    if not raw:
        return None
    try:
        fee = int(raw)
    except ValueError as exc:
        raise ValueError(f"{label}は整数で入力してください") from exc
    if fee < 0 or fee > maximum:
        raise ValueError(f"{label}は0から{maximum}の範囲で入力してください")
    return fee


def event_participation_label(value):
    return {"individual": "個人参加", "team": "チーム参加", "both": "個人・チーム参加"}.get(value, value)


def event_acceptance_label(value):
    return {"first_come": "先着順", "approval": "主催者承認制"}.get(value, value)


def event_status_label(value):
    return {"draft": "下書き", "published": "受付中", "closed": "受付終了", "cancelled": "開催中止"}.get(value, value)


def application_status_label(value):
    return {"pending": "承認待ち", "confirmed": "参加確定", "declined": "見送り", "cancelled": "取消済み"}.get(value, value)


def event_admission_label(event, application):
    event, application = dict(event), dict(application)
    if event["status"] == "cancelled":
        return "開催中止"
    status = application.get("application_status", application.get("status"))
    if status != "confirmed" or not event.get("minimum_participants"):
        return application_status_label(status)
    if not event.get("announcement_version"):
        return "受付確定・開催決定待ち"
    if application.get("attendance_version") == event["announcement_version"]:
        return "最終参加確認済み"
    return "開催決定・参加確認待ち"


def event_formation_label(event):
    event = dict(event)
    if event["status"] == "cancelled":
        return "開催中止"
    if not event.get("minimum_participants"):
        return ""
    if event.get("announcement_version"):
        return "開催決定"
    if event.get("confirmed_count", 0) >= event["minimum_participants"]:
        return "仮成立・主催者の開催決定待ち"
    return "最低開催数に向けて募集中"


def update_event_formation(conn, event_id):
    # Call inside the same write transaction as admission/cancellation.
    event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
    if not event or not event["minimum_participants"] or event["status"] not in {"published", "closed"}:
        return
    count = active_confirmed_capacity(conn, event_id)
    ready = count >= event["minimum_participants"]
    if ready and not event["minimum_notice_sent"]:
        if not event["announcement_version"]:
            add_event_notification(conn, event["organizer_user_id"], event_id, "event_provisional",
                                   "最低開催数に達しました（仮成立）",
                                   f"{event['title']} は{count}{event['capacity_unit']}を受け付けました。マイページから開催日時・会場・詳細を確認し、開催を決定してください。まだ入金を依頼しないでください。")
        conn.execute("update event_posts set minimum_notice_sent=1 where event_id=?", (event_id,))
    elif not ready and event["minimum_notice_sent"]:
        conn.execute("update event_posts set minimum_notice_sent=0 where event_id=?", (event_id,))
        add_event_notification(conn, event["organizer_user_id"], event_id, "event_below_minimum",
                               "最低開催数を下回りました",
                               f"{event['title']} は現在{count}{event['capacity_unit']}です。開催可否をご確認ください。自動で中止・返金はされません。")


def event_expected_version(data):
    try:
        return int(data.get("version", -1))
    except (ValueError, TypeError) as exc:
        raise ValueError("開催案内を再読み込みしてください") from exc


def announce_event(conn, event_id, data, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    conn.execute("begin immediate")
    event = event_owner(conn, event_id, user["user_id"])
    if event["status"] not in {"published", "closed"} or event["starts_at"] <= event_local_now():
        raise ValueError("中止済み・開催済み・下書きの募集は開催決定できません")
    if not event["minimum_participants"]:
        raise ValueError("募集編集で最低開催人数・チーム数を設定してください")
    if not event["announcement_version"] and active_confirmed_capacity(conn, event_id) < event["minimum_participants"]:
        raise ValueError("まだ最低開催人数・チーム数に達していません")
    if event_expected_version(data) != event["announcement_version"]:
        raise ValueError("開催案内が更新されています。再読み込みしてください")
    starts_at = event_datetime(data.get("starts_at"), "開催日時", required=True)
    if starts_at <= event_local_now():
        raise ValueError("開催日時は現在より後にしてください")
    if event["application_deadline"] and starts_at < event["application_deadline"]:
        raise ValueError("開催日時は応募締切以降にしてください。先に募集の応募締切を変更してください")
    location = event_form_value(data, "location", "会場", required=True, max_length=250)
    details = event_form_value(data, "announcement_details", "開催案内", required=True, max_length=5000)
    bank = event["payment_method"] == "bank_transfer" and bool(event["fee_amount"])
    bank_details = event_form_value(data, "bank_transfer_details", "振込先口座", required=bank, max_length=1200) if bank else ""
    deadline = event_datetime(data.get("payment_deadline"), "振込期限", required=bank) if bank else ""
    if bank and (deadline <= event_local_now() or deadline > starts_at):
        raise ValueError("振込期限は現在より後、開催日時以前にしてください")
    attendance_deadline = event_datetime(data.get("attendance_deadline") or deadline or starts_at, "最終参加確認の期限")
    if attendance_deadline <= event_local_now() or attendance_deadline > starts_at or (bank and attendance_deadline > deadline):
        raise ValueError("最終参加確認の期限は現在より後、開催日時・振込期限以前にしてください")
    if event["announcement_version"] and bank_details != event["bank_transfer_details"]:
        raise ValueError("案内済みの振込先は変更できません。必要な変更は参加者へ個別に連絡してください")
    fields = {"starts_at": starts_at, "location": location, "announcement_details": details,
              "bank_transfer_details": bank_details, "payment_deadline": deadline or None,
              "attendance_deadline": attendance_deadline}
    if event["announcement_version"] and all(event[key] == value for key, value in fields.items()):
        return event["announcement_version"]
    version = event["announcement_version"] + 1
    conn.execute("""update event_posts set starts_at=?,ends_at=null,location=?,announcement_details=?,
                 bank_transfer_details=?,payment_deadline=?,attendance_deadline=?,announcement_version=?,announced_at=?,updated_at=? where event_id=?""",
                 (starts_at, location, details, bank_details, deadline or None, attendance_deadline, version, now(), now(), event_id))
    for application in conn.execute("select applicant_user_id from event_applications where event_id=? and status='confirmed'", (event_id,)):
        add_event_notification(conn, application["applicant_user_id"], event_id, "event_announced",
                               "開催が決定しました・最終参加確認のお願い" if version == 1 else "開催案内が変更されました・再確認のお願い",
                               f"{event['title']}\n開催日時: {starts_at}\n会場: {event['prefecture']} / {location}\n{details}\n最終参加確認の期限: {attendance_deadline}\n\nマイページから開催内容・キャンセル条件を確認し、参加する旨をお知らせください。振込先は最終参加確認後にアプリ内で表示されます。すでに支払い済みの場合、再度振り込まないでください。")
    audit(conn, "event_announce", "event_post", event_id, {"version": version})
    return version


def confirm_event_attendance(conn, event_id, data, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    conn.execute("begin immediate")
    event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
    application = conn.execute("select * from event_applications where event_id=? and applicant_user_id=?",
                               (event_id, user["user_id"])).fetchone()
    if not event or not application or application["status"] != "confirmed":
        raise PermissionError("受付が確定しているご本人のみ確認できます")
    if event["status"] not in {"published", "closed"} or event["starts_at"] <= event_local_now():
        raise ValueError("中止済み・開催済みの募集は参加確認できません")
    version = event["announcement_version"]
    if not version or event_expected_version(data) != version:
        raise ValueError("最新の開催案内を再読み込みして確認してください")
    if event["payment_method"] == "bank_transfer" and event["payment_deadline"] <= event_local_now():
        raise ValueError("振込期限を過ぎています。主催者へ連絡してください")
    if event["attendance_deadline"] and event["attendance_deadline"] <= event_local_now():
        raise ValueError("最終参加確認の期限を過ぎています。主催者へ連絡してください")
    if application["attendance_version"] == version:
        return
    conn.execute("update event_applications set attendance_version=?,attendance_confirmed_at=?,updated_at=?,operation_revision=operation_revision+1 where application_id=?",
                 (version, now(), now(), application["application_id"]))
    add_event_notification(conn, event["organizer_user_id"], event_id, "attendance_confirmed", "最終参加確認が届きました",
                           f"{event['title']} に{application['participant_count']}名の最終参加確認が届きました。入金確認とは異なります。")
    add_event_notification(conn, user["user_id"], event_id, "attendance_recorded", "最終参加確認を受け付けました",
                           f"{event['title']} の最終参加確認を受け付けました。支払方法・期限はマイページの開催案内でご確認ください。")
    audit(conn, "event_attendance", "event_application", application["application_id"], {"version": version})


def owner_financial_summary(event):
    target = event.get("target_total_amount")
    if target is None:
        return ""
    result = f'<p>損益分岐点（主催者のみ）：{target:,}円</p>'
    compatible = (event.get("capacity_unit"), event.get("fee_unit")) in {("人", "1人"), ("チーム", "1チーム")}
    if event.get("capacity") and event.get("fee_amount") is not None and compatible:
        revenue = event["capacity"] * event["fee_amount"]
        result += f'<p>満員時の参加費見込：{revenue:,}円 / 損益分岐点との差額：{revenue - target:+,}円</p><small>定員 × 単価での見込みです。実際の入金額・利益ではありません。</small>'
    else:
        result += '<p>定員・料金単位が確定すると、満員時の差額を表示します。</p>'
    return result


def can_link_circle(conn, user, circle_id):
    """Only a verified representative can present an existing DB circle as host."""
    if not circle_id:
        return True
    if not user.get("email"):
        return False
    row = conn.execute(
        """
        select 1 from circle_claims
        where circle_id=? and lower(claimant_email)=lower(?) and university_email_verified=1
        limit 1
        """,
        (circle_id, user["email"]),
    ).fetchone()
    return bool(row)


def event_payload_from_data(conn, data, user, event_id=""):
    publishing = str(data.get("status") or "draft").strip() == "published"
    event_type = event_form_value(data, "event_type", "募集種別", required=True, max_length=50)
    if event_type not in EVENT_TYPES:
        raise ValueError("募集種別が正しくありません")
    sport = event_form_value(data, "sport_category", "競技", required=publishing, max_length=100)
    title = event_form_value(data, "title", "タイトル", required=True, max_length=120)
    starts_at = event_datetime(data.get("starts_at"), "開催日時", required=publishing)
    ends_at = event_datetime(data.get("ends_at"), "終了日時", required=False)
    if ends_at and starts_at and ends_at < starts_at:
        raise ValueError("終了日時は開催日時より後にしてください")
    participation_type = event_form_value(data, "participation_type", "参加単位", required=True, max_length=20)
    if participation_type not in EVENT_PARTICIPATION_TYPES:
        raise ValueError("参加単位が正しくありません")
    capacity_unit = "チーム" if participation_type == "team" else "人"
    fee_unit = "1チーム" if participation_type == "team" else "1人"
    existing = event_owner(conn, event_id, user["user_id"]) if event_id else None
    # Keep legacy counting/pricing semantics when editing an existing event.
    if existing and existing["participation_type"] == participation_type:
        capacity_unit = existing["capacity_unit"]
        fee_unit = existing["fee_unit"] or fee_unit
    acceptance_mode = event_form_value(data, "acceptance_mode", "受付方式", required=True, max_length=30)
    if acceptance_mode not in EVENT_ACCEPTANCE_MODES:
        raise ValueError("受付方式が正しくありません")
    payment_method = event_form_value(data, "payment_method", "支払方法", required=True, max_length=30)
    if payment_method not in {"free", "on_site", "bank_transfer"}:
        raise ValueError("支払方法は現地払い・口座振込から選択してください")
    status = str(data.get("status") or "draft").strip()
    if status not in {"draft", "published"}:
        raise ValueError("保存状態が正しくありません")
    deadline = event_datetime(data.get("application_deadline"), "応募締切", required=False)
    if deadline and starts_at and deadline > starts_at:
        raise ValueError("応募締切は開催日時以前にしてください")
    linked_circle_id = event_form_value(data, "linked_circle_id", "主催団体", max_length=120)
    if linked_circle_id and not can_link_circle(conn, user, linked_circle_id):
        raise ValueError("団体との紐付けには、確認済みの代表権限が必要です。団体なしで公開することはできます")
    organizer_name = event_form_value(data, "organizer_name", "主催者の表示名", max_length=80) or (user.get("display_name") or user.get("email") or "主催者")
    contact_email = event_form_value(data, "organizer_contact_email", "主催者連絡先", max_length=255) or (user.get("email") or "")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", contact_email):
        raise ValueError("主催者連絡先にはメールアドレスを入力してください")
    payload = {
        "linked_circle_id": linked_circle_id or None,
        "organizer_name": organizer_name,
        "organizer_contact_email": contact_email,
        "event_type": event_type,
        "sport_category": sport,
        "title": title,
        "starts_at": starts_at,
        "ends_at": ends_at or None,
        "prefecture": event_form_value(data, "prefecture", "都道府県", required=publishing, max_length=30) or None,
        "location": event_form_value(data, "location", "会場", required=publishing, max_length=250),
        "description": event_form_value(data, "description", "説明", required=publishing, max_length=5000),
        "participation_type": participation_type,
        "capacity": event_capacity_value(data),
        "capacity_unit": capacity_unit,
        "eligibility": event_form_value(data, "eligibility", "参加条件", max_length=1200),
        "fee_amount": event_fee_value(data),
        "fee_unit": fee_unit,
        "target_total_amount": (event_fee_value(data, "target_total_amount", "損益分岐点", 1000000000)
                                if "target_total_amount" in data else (existing["target_total_amount"] if existing else None)),
        "payment_method": payment_method,
        "application_deadline": deadline or None,
        "acceptance_mode": acceptance_mode,
        "cancellation_policy": event_form_value(data, "cancellation_policy", "キャンセル・中止条件", required=publishing, max_length=1600),
        "status": status,
    }
    if status == "published" and starts_at <= event_local_now():
        raise ValueError("公開する募集の開催日時は現在より後にしてください")
    if publishing and payload["prefecture"] not in PREFECTURES:
        raise ValueError("都道府県を選択してください")
    if publishing and deadline and deadline < event_local_now():
        raise ValueError("応募締切を過ぎています。将来の日時を指定してください")
    if publishing and payment_method != "free" and payload["fee_amount"] is None:
        raise ValueError("有料の募集には参加費を入力してください")
    if publishing and payment_method == "free" and payload["fee_amount"]:
        raise ValueError("参加費がある場合は、現地払い・口座振込を選択してください")
    if payment_method == "free" and payload["fee_amount"] is None:
        payload["fee_amount"] = 0
    if payload["fee_amount"] == 0:
        payload["payment_method"] = "free"
    payload["minimum_participants"] = (event_fee_value(data, "minimum_participants", "最低開催人数・チーム数", 100000)
                                       if "minimum_participants" in data else (existing["minimum_participants"] if existing else 0)) or 0
    if "minimum_participants" in data and payload["minimum_participants"] < 1 and not (existing and existing["minimum_participants"] == 0):
        raise ValueError("最低開催人数・チーム数は1以上にしてください")
    if payload["capacity"] and payload["minimum_participants"] > payload["capacity"]:
        raise ValueError("最低開催人数・チーム数は定員以下にしてください")
    return payload


def event_public_select(where="", params=()):
    sql = """
        select e.event_id, e.linked_circle_id, e.organizer_name, e.event_type, e.sport_category,
          e.title, e.starts_at, e.ends_at, e.prefecture, e.location, e.description,
          e.participation_type, e.capacity, e.capacity_unit, e.eligibility, e.fee_amount,
          e.fee_unit, e.payment_method, e.application_deadline, e.acceptance_mode,
          e.cancellation_policy, e.status, e.published_at, e.created_at, e.updated_at,
          e.minimum_participants, e.announcement_version, e.announcement_details, e.announced_at, e.payment_deadline, e.attendance_deadline,
          c.circle_name as linked_circle_name, cp.profile_slug as linked_circle_profile_slug,
          coalesce(sum(case when a.status='confirmed' then
            case when e.participation_type='team' and e.capacity_unit='チーム' then 1 else a.participant_count end
            else 0 end), 0) as confirmed_count,
          coalesce(sum(case when a.status in ('pending','confirmed') then 1 else 0 end), 0) as application_count
        from event_posts e
        left join circles c on c.circle_id=e.linked_circle_id
        left join circle_public_profiles cp on cp.circle_id=e.linked_circle_id and cp.is_published=1
        left join event_applications a on a.event_id=e.event_id
    """
    if where:
        sql += " where " + where
    sql += " group by e.event_id "
    return sql, list(params)


def event_query_conditions(params, include_all_statuses=False):
    sport = (params.get("sport", [""])[0] or "").strip()
    region = (params.get("region", [""])[0] or "").strip()
    prefecture = (params.get("prefecture", [""])[0] or "").strip()
    event_type = (params.get("event_type", [""])[0] or "").strip()
    participation = (params.get("participation", [""])[0] or "").strip()
    date_from = (params.get("date_from", [""])[0] or "").strip()
    date_to = (params.get("date_to", [""])[0] or "").strip()
    where = [] if include_all_statuses else ["e.status='published'", "e.starts_at>=?"]
    args = [] if include_all_statuses else [event_local_now()]
    if sport:
        where.append("e.sport_category like ?")
        args.append(f"%{sport}%")
    if prefecture:
        where.append("e.prefecture=?")
        args.append(prefecture)
    elif region:
        prefectures = region_prefectures(region)
        if prefectures:
            where.append("e.prefecture in (%s)" % ",".join("?" * len(prefectures)))
            args.extend(prefectures)
    if event_type in EVENT_TYPES:
        where.append("e.event_type=?")
        args.append(event_type)
    if participation in {"individual", "team"}:
        where.append("e.participation_type in (?, 'both')")
        args.append(participation)
    if date_from:
        where.append("substr(e.starts_at,1,10)>=?")
        args.append(date_from[:10])
    if date_to:
        where.append("substr(e.starts_at,1,10)<=?")
        args.append(date_to[:10])
    return where, args


def search_events(params, limit=60):
    where, args = event_query_conditions(params)
    sql, args = event_public_select(" and ".join(where), args)
    sql += " order by e.starts_at asc, e.created_at desc limit ?"
    args.append(max(1, min(int(limit), 100)))
    data = rows(sql, args)
    for event in data:
        event["availability_label"], event["can_apply"] = event_availability(event)
    return data


def get_event(event_id, include_private=False):
    where = "e.event_id=?"
    if not include_private:
        where += " and e.status in ('published','closed','cancelled')"
    sql, args = event_public_select(where, [event_id])
    with connect() as conn:
        row = conn.execute(sql, args).fetchone()
    return dict(row) if row else None


def organizer_form_defaults(user):
    defaults = {"organizer_name": user.get("display_name") or "", "organizer_contact_email": user.get("email") or ""}
    with connect() as conn:
        previous = conn.execute(
            "select organizer_name, organizer_contact_email from event_posts "
            "where organizer_user_id=? order by updated_at desc, event_id desc limit 1",
            (user["user_id"],),
        ).fetchone()
    if previous:
        defaults.update({key: previous[key] for key in defaults if previous[key]})
    return defaults


def event_owner(conn, event_id, user_id):
    row = conn.execute(
        "select * from event_posts where event_id=? and organizer_user_id=?",
        (event_id, user_id),
    ).fetchone()
    if not row:
        raise PermissionError("この募集を管理する権限がありません")
    return row


def add_event_notification(conn, recipient_user_id, event_id, notification_type, title, body):
    """The notification and its email job commit with the application change."""
    notification_id = slug("notification", f"{recipient_user_id}:{event_id}:{notification_type}:{now()}:{secrets.token_hex(4)}")
    conn.execute(
        """
        insert into event_notifications(notification_id, recipient_user_id, event_id, notification_type,
          title, body, email_status, created_at)
        values(?,?,?,?,?,?, 'not_configured', ?)
        """,
        (notification_id, recipient_user_id, event_id, notification_type, title, body, now()),
    )
    if email_notifications_ready():
        account = conn.execute("select email from user_accounts where user_id=?", (recipient_user_id,)).fetchone()
        email = (account["email"] or "").strip() if account else ""
        if not re.fullmatch(r"[^@\s\r\n]+@[^@\s\r\n]+\.[^@\s\r\n]+", email):
            conn.execute("update event_notifications set email_status='failed',email_error='invalid_recipient' where notification_id=?", (notification_id,))
        else:
            # Freeze the exact payload so retries use Resend's same idempotency key.
            payload = {
                "from": EMAIL_FROM, "to": [email], "subject": f"Circle Match | {title}",
                "text": f"{title}\n\n{body}\n\n通知の詳細はCircle Matchでご確認ください。\n"
                        f"{SITE_BASE_URL.rstrip('/')}/notifications\n\n"
                        "Circle Matchからの自動通知です。このメールには返信できません。",
            }
            conn.execute("insert into event_email_outbox(notification_id,payload_json) values(?,?)",
                         (notification_id, json.dumps(payload, ensure_ascii=False)))
    return notification_id


def email_notifications_ready():
    return bool(EMAIL_NOTIFICATIONS_ENABLED and RESEND_API_KEY and EMAIL_FROM
                and urlparse(SITE_BASE_URL).scheme == "https" and urlparse(SITE_BASE_URL).netloc)


def email_delivery_label(status):
    return {
        "not_configured": "未設定（アプリ内通知のみ）", "queued": "送信待ち",
        "sending": "送信処理中", "retry": "再送待ち", "sent": "送信サービス受付済み",
        "failed": "送信失敗（アプリ内通知をご確認ください）",
    }.get(status, "未送信")


def send_notification_email(notification_id, payload_json):
    request = Request(
        "https://api.resend.com/emails", data=payload_json.encode("utf-8"),
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json",
                 "Accept": "application/json", "User-Agent": "CircleMatch/1.0 (+https://circle-match.jp)",
                 "Idempotency-Key": "circlematch-notification/" + hashlib.sha256(notification_id.encode("utf-8")).hexdigest()},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        data = json.loads(response.read(65536).decode("utf-8"))
    if not isinstance(data, dict) or not data.get("id"):
        raise ValueError("missing_provider_id")
    return str(data["id"])


def process_event_email():
    """Claim one persisted job, release SQLite before doing any network I/O."""
    if not email_notifications_ready():
        return False
    timestamp = int(time.time())
    with connect() as conn:
        conn.execute("begin immediate")
        job = conn.execute(
            """select * from event_email_outbox
            where (status in ('queued','retry') and next_attempt_at<=?)
               or (status='sending' and lease_until<=?)
            order by next_attempt_at, notification_id limit 1""", (timestamp, timestamp),
        ).fetchone()
        if not job:
            return False
        job = dict(job)
        # Provider idempotency lasts 24 hours. Do not blindly resend an uncertain
        # result after that window, or after the bounded retry budget is exhausted.
        if job["attempts"] >= 5 or (job["first_attempt_at"] is not None and timestamp - job["first_attempt_at"] >= 23 * 3600):
            conn.execute("update event_email_outbox set status='failed',last_error='retry_window_exhausted',lease_until=null where notification_id=?", (job["notification_id"],))
            conn.execute("update event_notifications set email_status='failed',email_error='retry_window_exhausted' where notification_id=?", (job["notification_id"],))
            return True
        conn.execute(
            """update event_email_outbox set status='sending',attempts=attempts+1,
               first_attempt_at=coalesce(first_attempt_at,?),lease_until=? where notification_id=?""",
            (timestamp, timestamp + 120, job["notification_id"]),
        )
    try:
        provider_id = send_notification_email(job["notification_id"], job["payload_json"])
    except Exception as exc:
        code = exc.code if isinstance(exc, HTTPError) else None
        retryable = code is None or code in (408, 409, 429) or code >= 500
        state = "retry" if retryable and job["attempts"] + 1 < 5 else "failed"
        # Provider errors can contain email addresses or credentials. Store only
        # a diagnostic class/status code, never the response body or request.
        error = f"HTTP_{code}" if code else type(exc).__name__
        with connect() as conn:
            conn.execute(
                """update event_email_outbox set status=?,next_attempt_at=?,lease_until=null,last_error=?
                   where notification_id=? and status='sending'""",
                (state, timestamp + min(3600, 60 * 2 ** job["attempts"]), error, job["notification_id"]),
            )
            conn.execute("update event_notifications set email_status='failed',email_error=? where notification_id=?", (error, job["notification_id"]))
        log(f"event email {job['notification_id']} {state}: {error}")
    else:
        with connect() as conn:
            conn.execute(
                """update event_email_outbox set status='sent',provider_id=?,sent_at=?,lease_until=null,last_error=null
                   where notification_id=? and status='sending'""", (provider_id, now(), job["notification_id"]),
            )
            conn.execute("update event_notifications set email_status='sent',email_error=null where notification_id=?", (job["notification_id"],))
    return True


def start_event_email_worker():
    stop = threading.Event()

    def run():
        next_reminder_check = 0
        while not stop.is_set():
            try:
                if time.monotonic() >= next_reminder_check:
                    process_attendance_reminders()
                    next_reminder_check = time.monotonic() + 60
                processed = process_event_email()
            except Exception as exc:
                log(f"event email worker failed: {type(exc).__name__}")
                processed = False
            stop.wait(1 if processed else 5)

    thread = threading.Thread(target=run, name="event-email-outbox", daemon=True)
    thread.start()
    return stop, thread


def save_event_post(conn, data, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    if not conn.in_transaction:
        conn.execute("begin immediate")
    event_id = event_form_value(data, "event_id", "募集ID", max_length=120)
    payload = event_payload_from_data(conn, data, user, event_id)
    timestamp = now()
    values = (
        payload["linked_circle_id"], payload["organizer_name"], payload["organizer_contact_email"],
        payload["event_type"], payload["sport_category"], payload["title"], payload["starts_at"],
        payload["ends_at"], payload["prefecture"], payload["location"], payload["description"],
        payload["participation_type"], payload["capacity"], payload["capacity_unit"], payload["eligibility"],
        payload["fee_amount"], payload["fee_unit"], payload["payment_method"], payload["application_deadline"],
        payload["acceptance_mode"], payload["cancellation_policy"], payload["status"],
    )
    if event_id:
        existing = event_owner(conn, event_id, user["user_id"])
        has_payment = conn.execute("select 1 from event_applications where event_id=? and payment_status!='unpaid' limit 1", (event_id,)).fetchone()
        if has_payment and any(payload[key] != existing[key] for key in ("fee_amount", "fee_unit", "payment_method", "cancellation_policy")):
            raise ValueError("入金・精算の記録があるため料金・支払方法・キャンセル条件は変更できません")
        if existing["status"] == "cancelled":
            raise ValueError("中止した募集は再公開できません。複製して新しい募集を作成してください")
        if existing["announcement_version"] and any(payload[key] != existing[key] for key in (
                "starts_at", "ends_at", "prefecture", "location", "description", "eligibility", "fee_amount", "fee_unit",
                "payment_method", "cancellation_policy", "minimum_participants")):
            raise ValueError("開催決定後の日時・会場変更はマイページの開催案内から行ってください。料金・参加条件・振込方法は変更できません")
        if existing["minimum_participants"] and not payload["minimum_participants"]:
            raise ValueError("最低開催人数・チーム数は1以上にしてください")
        has_applications = conn.execute(
            "select 1 from event_applications where event_id=? and status in ('pending','confirmed') limit 1", (event_id,)
        ).fetchone()
        if has_applications:
            if any(payload[key] != existing[key] for key in ("participation_type", "capacity_unit", "acceptance_mode")):
                raise ValueError("申込受付後は参加単位・定員の単位・受付方式を変更できません")
            if payload["status"] == "draft":
                raise ValueError("申込受付後は下書きに戻せません。締切または中止を選択してください")
        if payload["capacity"] and payload["capacity"] < active_confirmed_capacity(conn, event_id):
            raise ValueError("参加確定済みの枠数より定員を少なくできません")
        conn.execute(
            """
            update event_posts set linked_circle_id=?, organizer_name=?, organizer_contact_email=?, event_type=?,
              sport_category=?, title=?, starts_at=?, ends_at=?, prefecture=?, location=?, description=?,
              participation_type=?, capacity=?, capacity_unit=?, eligibility=?, fee_amount=?, fee_unit=?,
              payment_method=?, application_deadline=?, acceptance_mode=?, cancellation_policy=?, status=?,
              published_at=case when ?='published' and published_at is null then ? else published_at end,
              updated_at=? where event_id=?
            """,
            values + (payload["status"], timestamp, timestamp, event_id),
        )
        if existing["status"] != "draft" and any(payload[key] != existing[key] for key in payload if key != "target_total_amount"):
            for recipient in conn.execute(
                "select applicant_user_id from event_applications where event_id=? and status in ('pending','confirmed')", (event_id,)
            ).fetchall():
                add_event_notification(conn, recipient["applicant_user_id"], event_id, "event_updated",
                                       "開催内容が変更されました", f"{payload['title']} の最新の開催内容・参加条件をご確認ください。")
    else:
        event_id = slug("event", f"{user['user_id']}:{payload['title']}:{payload['starts_at']}:{timestamp}")
        conn.execute(
            """
            insert into event_posts(event_id, organizer_user_id, linked_circle_id, organizer_name, organizer_contact_email,
              event_type, sport_category, title, starts_at, ends_at, prefecture, location, description,
              participation_type, capacity, capacity_unit, eligibility, fee_amount, fee_unit, payment_method,
              application_deadline, acceptance_mode, cancellation_policy, status, published_at, created_at, updated_at)
            values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (event_id, user["user_id"], *values[:22], timestamp if payload["status"] == "published" else None, timestamp, timestamp),
        )
    conn.execute("update event_posts set target_total_amount=?, minimum_participants=? where event_id=? and organizer_user_id=?",
                 (payload["target_total_amount"], payload["minimum_participants"], event_id, user["user_id"]))
    update_event_formation(conn, event_id)
    audit(conn, "event_save", "event_post", event_id, {"status": payload["status"], "organizer_user_id": user["user_id"]})
    return event_id


def event_is_open_for_application(event):
    if event["status"] != "published":
        raise ValueError("この募集は現在受け付けていません")
    deadline = event["application_deadline"] or ""
    if deadline and deadline < event_local_now():
        raise ValueError("応募締切を過ぎています")
    if event["starts_at"] <= event_local_now():
        raise ValueError("開催日時を過ぎています")
    if event["announcement_version"] and event["payment_deadline"] and event["payment_deadline"] <= event_local_now():
        raise ValueError("振込期限を過ぎているため申し込めません。主催者へお問い合わせください")
    if event["announcement_version"] and event["attendance_deadline"] and event["attendance_deadline"] <= event_local_now():
        raise ValueError("最終参加確認の期限を過ぎているため申し込めません")


def event_local_now():
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")


def event_availability(event):
    """One admission state for SSR, API cards and application entry points."""
    if event.get("status") == "cancelled":
        return "開催中止", False
    if event.get("status") != "published":
        return event_status_label(event.get("status")), False
    current = event_local_now()
    if event.get("starts_at", "") <= current:
        return "開催済み", False
    if event.get("application_deadline") and event["application_deadline"] < current:
        return "応募締切", False
    if event.get("announcement_version") and event.get("payment_deadline") and event["payment_deadline"] <= current:
        return "振込期限終了", False
    if event.get("announcement_version") and event.get("attendance_deadline") and event["attendance_deadline"] <= current:
        return "参加確認期限終了", False
    if event.get("capacity") and int(event.get("confirmed_count", 0)) >= int(event["capacity"]):
        return "満員", False
    return "受付中", True


def user_event_application(event_id, user):
    if not (user or {}).get("authenticated"):
        return None
    with connect() as conn:
        row = conn.execute("select * from event_applications where event_id=? and applicant_user_id=?",
                           (event_id, user["user_id"])).fetchone()
    return dict(row) if row else None


def active_confirmed_capacity(conn, event_id):
    value = conn.execute(
        """select coalesce(sum(case when e.participation_type='team' and e.capacity_unit='チーム'
          then 1 else a.participant_count end), 0)
          from event_applications a join event_posts e on e.event_id=a.event_id
          where a.event_id=? and a.status='confirmed'""",
        (event_id,),
    ).fetchone()[0]
    return int(value or 0)


def application_capacity_cost(event, participant_count):
    return 1 if event["participation_type"] == "team" and event["capacity_unit"] == "チーム" else participant_count


def submit_event_application(conn, event_id, data, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    conn.execute("begin immediate")
    event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
    if not event:
        raise ValueError("募集が見つかりません")
    event_is_open_for_application(event)
    if event["organizer_user_id"] == user["user_id"]:
        raise ValueError("主催者本人はこの募集に申し込めません")
    existing = conn.execute(
        "select * from event_applications where event_id=? and applicant_user_id=?",
        (event_id, user["user_id"]),
    ).fetchone()
    if existing and existing["status"] != "cancelled":
        raise ValueError("この募集にはすでに申し込み済みです")
    if existing and existing["payment_status"] in {"paid", "refund_pending"}:
        raise ValueError("前回の申込の精算を主催者へ確認してから、再度お申し込みください")
    participation_type = event_form_value(data, "participation_type", "参加単位", required=True, max_length=20)
    allowed = {"individual", "team"} if event["participation_type"] == "both" else {event["participation_type"]}
    if participation_type not in allowed:
        raise ValueError("この募集で選択できない参加単位です")
    applicant_name = event_form_value(data, "applicant_name", "参加者名", required=participation_type == "individual", max_length=80)
    team_name = event_form_value(data, "team_name", "チーム名", required=participation_type == "team", max_length=100)
    representative_name = event_form_value(data, "representative_name", "代表者名", required=participation_type == "team", max_length=80)
    raw_count = str(data.get("participant_count", "1" if participation_type == "individual" else "")).strip()
    try:
        participant_count = int(raw_count)
    except ValueError as exc:
        raise ValueError("参加予定人数は整数で入力してください") from exc
    if participant_count < 1 or participant_count > 100000:
        raise ValueError("参加予定人数は1から100000の範囲で入力してください")
    if event["capacity"]:
        if application_capacity_cost(event, participant_count) > int(event["capacity"]):
            raise ValueError("参加予定人数が募集の定員を超えています")
        if active_confirmed_capacity(conn, event_id) >= int(event["capacity"]):
            raise ValueError("定員に達しているため申し込めません")
    if event["capacity"] and event["acceptance_mode"] == "first_come":
        if active_confirmed_capacity(conn, event_id) + application_capacity_cost(event, participant_count) > int(event["capacity"]):
            raise ValueError("定員に達しているため申し込めません")
    status = "confirmed" if event["acceptance_mode"] == "first_come" else "pending"
    application_id = existing["application_id"] if existing else slug("application", f"{event_id}:{user['user_id']}:{now()}:{secrets.token_hex(4)}")
    if existing:
        # Preserve the previous answers privately before reusing the unique admission record.
        conn.execute("insert into event_application_history(application_id, snapshot_json, archived_at) values(?,?,?)",
                     (application_id, json.dumps(dict(existing), ensure_ascii=False), now()))
    conn.execute(
        """
        insert into event_applications(application_id, event_id, applicant_user_id, participation_type,
          applicant_name, team_name, representative_name, participant_count, answers_json, applicant_message,
          status, created_at, updated_at)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?)
        on conflict(event_id, applicant_user_id) do update set
          participation_type=excluded.participation_type, applicant_name=excluded.applicant_name,
          team_name=excluded.team_name, representative_name=excluded.representative_name,
          participant_count=excluded.participant_count, answers_json=excluded.answers_json,
          applicant_message=excluded.applicant_message, status=excluded.status, organizer_note=null,
          created_at=excluded.created_at, updated_at=excluded.updated_at,
          attendance_version=0, attendance_confirmed_at=null,
          payment_status='unpaid',payment_note='',payment_updated_at=null,
          requested_participant_count=null,operation_revision=event_applications.operation_revision+1
        """,
        (
            application_id, event_id, user["user_id"], participation_type, applicant_name or None,
            team_name or None, representative_name or None, participant_count,
            json.dumps(data.get("answers") or {}, ensure_ascii=False),
            event_form_value(data, "applicant_message", "主催者への連絡", max_length=1200) or None,
            status, now(), now(),
        ),
    )
    add_event_notification(
        conn, event["organizer_user_id"], event_id, "new_application", "新しい参加申込があります",
        f"{event['title']} に" + (f"1チーム（{participant_count}名）" if participation_type == "team" else f"{participant_count}名") + "の申込がありました。",
    )
    add_event_notification(
        conn, user["user_id"], event_id, "application_received",
        "参加申込を受け付けました" if status == "confirmed" else "参加申請を受け付けました",
        f"{event['title']} の受付状況は「{event_admission_label(event, {'status': status})}」です。マイページでご確認ください。",
    )
    update_event_formation(conn, event_id)
    audit(conn, "event_apply", "event_application", application_id, {"event_id": event_id, "status": status, "applicant_user_id": user["user_id"]})
    return {"application_id": application_id, "status": status}


def set_event_application_status(conn, event_id, application_id, action, user, organizer_note=""):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    conn.execute("begin immediate")
    event = event_owner(conn, event_id, user["user_id"])
    application = conn.execute(
        "select * from event_applications where application_id=? and event_id=?",
        (application_id, event_id),
    ).fetchone()
    if not application:
        raise ValueError("申込が見つかりません")
    if application["status"] != "pending":
        raise ValueError("この申込はすでに処理済みです")
    if action not in {"confirm", "decline"}:
        raise ValueError("処理内容が正しくありません")
    next_status = "confirmed" if action == "confirm" else "declined"
    if next_status == "confirmed":
        if event["announcement_version"] and event["payment_deadline"] and event["payment_deadline"] <= event_local_now():
            raise ValueError("振込期限を過ぎています。開催案内の期限をご確認ください")
        if event["attendance_deadline"] and event["attendance_deadline"] <= event_local_now():
            raise ValueError("最終参加確認の期限を過ぎています。開催案内の期限をご確認ください")
        if event["status"] not in {"published", "closed"} or event["starts_at"] <= event_local_now():
            raise ValueError("中止済み・開催済みの募集は参加確定にできません")
        if event["capacity"] and active_confirmed_capacity(conn, event_id) + application_capacity_cost(event, int(application["participant_count"] or 0)) > int(event["capacity"]):
            raise ValueError("定員を超えるため参加確定にできません")
    conn.execute(
        "update event_applications set status=?, organizer_note=?, updated_at=?,operation_revision=operation_revision+1 where application_id=?",
        (next_status, str(organizer_note or "").strip()[:1200] or None, now(), application_id),
    )
    add_event_notification(
        conn, application["applicant_user_id"], event_id, f"application_{next_status}",
        ("受付が確定しました" if event["minimum_participants"] else "参加が確定しました") if next_status == "confirmed" else "申込を見送りました",
        f"{event['title']} の受付状況は「{event_admission_label(event, {'status': next_status})}」です。マイページでご確認ください。",
    )
    update_event_formation(conn, event_id)
    audit(conn, "event_application_status", "event_application", application_id, {"event_id": event_id, "status": next_status})
    return next_status


def cancel_event_application(conn, event_id, application_id, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    if not conn.in_transaction:
        conn.execute("begin immediate")
    application = conn.execute(
        "select * from event_applications where application_id=? and event_id=? and applicant_user_id=?",
        (application_id, event_id, user["user_id"]),
    ).fetchone()
    if not application:
        raise PermissionError("この申込を取り消す権限がありません")
    if application["status"] not in {"pending", "confirmed"}:
        raise ValueError("この申込は取り消せません")
    event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
    conn.execute("""update event_applications set status='cancelled', updated_at=?,
                 payment_status=case when payment_status='paid' then 'refund_pending' else payment_status end,
                 requested_participant_count=null,operation_revision=operation_revision+1 where application_id=?""", (now(), application_id))
    update_event_formation(conn, event_id)
    add_event_notification(
        conn, event["organizer_user_id"], event_id, "application_cancelled", "参加申込が取り消されました",
        f"{event['title']} の申込が参加者により取り消されました。",
    )
    add_event_notification(conn, user["user_id"], event_id, "cancellation_received",
                           "申込の取り消しを受け付けました", f"{event['title']} の受付状況は「取消済み」です。")
    audit(conn, "event_application_cancel", "event_application", application_id, {"event_id": event_id})


def set_event_status(conn, event_id, status, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    if not conn.in_transaction:
        conn.execute("begin immediate")
    if status not in {"closed", "cancelled", "published"}:
        raise ValueError("募集状態が正しくありません")
    event = event_owner(conn, event_id, user["user_id"])
    if event["status"] == "draft":
        raise ValueError("下書きは内容を確認して作成フォームから公開してください")
    if event["status"] == status:
        return
    if event["status"] == "cancelled" and status != "cancelled":
        raise ValueError("中止した募集は再公開できません。複製して作り直してください")
    conn.execute("update event_posts set status=?, updated_at=? where event_id=?", (status, now(), event_id))
    if status == "cancelled":
        conn.execute("""update event_applications set payment_status=case when payment_status='paid' then 'refund_pending' else payment_status end,
                     requested_participant_count=null,operation_revision=operation_revision+1 where event_id=?""", (event_id,))
    recipients = conn.execute(
        "select distinct applicant_user_id from event_applications where event_id=? and status in ('pending','confirmed')",
        (event_id,),
    ).fetchall()
    title = "開催中止のお知らせ" if status == "cancelled" else ("募集を締め切りました" if status == "closed" else "募集を再開しました")
    for recipient in recipients:
        add_event_notification(conn, recipient["applicant_user_id"], event_id, f"event_{status}", title, f"{event['title']} の状態が「{event_status_label(status)}」に変更されました。")
    audit(conn, "event_status", "event_post", event_id, {"status": status})


def event_applications_for_owner(event_id, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    with connect() as conn:
        event = event_owner(conn, event_id, user["user_id"])
        rows_data = conn.execute(
            """
            select a.application_id, a.applicant_user_id, a.participation_type, a.applicant_name, a.team_name, a.representative_name,
              a.participant_count, a.applicant_message, a.status, a.created_at, a.updated_at,
              a.attendance_version, a.attendance_confirmed_at, a.payment_status, a.payment_note,
              a.payment_updated_at, a.operation_revision, a.requested_participant_count,
              u.display_name as account_name
            from event_applications a join user_accounts u on u.user_id=a.applicant_user_id
            where a.event_id=? order by a.created_at desc
            """,
            (event_id,),
        ).fetchall()
    can_review = event["status"] in {"published", "closed"} and event["starts_at"] > event_local_now()
    return [dict(row, can_review=can_review, can_release=can_release_unconfirmed(event, row), display_status=event_admission_label(event, row)) for row in rows_data]


def unread_notification_count(user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    with connect() as conn:
        return conn.execute("select count(*) from event_notifications where recipient_user_id=? and read_at is null",
                            (user["user_id"],)).fetchone()[0]


def notifications_for_user(user, offset=0):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    with connect() as conn:
        notes = conn.execute("""
            select n.notification_id, n.event_id, n.notification_type, n.title, n.body, n.created_at, n.read_at,
              coalesce(o.status, n.email_status) as email_status, e.title as event_title
            from event_notifications n left join event_posts e on e.event_id=n.event_id
            left join event_email_outbox o on o.notification_id=n.notification_id
            where n.recipient_user_id=? order by n.created_at desc, n.notification_id desc limit 50 offset ?
            """, (user["user_id"], max(0, offset))).fetchall()
    return [dict(row) for row in notes]


def event_my_page(user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    with connect() as conn:
        hosted = conn.execute(
            """
            select e.*, coalesce(sum(case when a.status='confirmed' then
              case when e.participation_type='team' and e.capacity_unit='チーム' then 1 else a.participant_count end
              else 0 end),0) as confirmed_count,
              count(a.application_id) as application_count
              ,coalesce(sum(case when a.status='confirmed' and e.announcement_version>0 and a.attendance_version=e.announcement_version
                then case when e.participation_type='team' and e.capacity_unit='チーム' then 1 else a.participant_count end else 0 end),0) as final_attendance_count
            from event_posts e left join event_applications a on a.event_id=e.event_id
            where e.organizer_user_id=? group by e.event_id order by e.updated_at desc
            """,
            (user["user_id"],),
        ).fetchall()
        attending = conn.execute(
            """
            select a.application_id, a.status as application_status, a.participation_type, a.team_name, a.applicant_name,
              a.participant_count, a.created_at as application_created_at, e.event_id, e.title,
              e.starts_at, e.location, e.status, e.capacity, e.capacity_unit, e.application_deadline,
              e.minimum_participants, e.announcement_version, e.payment_deadline, e.attendance_deadline, a.attendance_version,
              e.fee_amount, a.payment_status, a.requested_participant_count,
              (select coalesce(sum(case when e.participation_type='team' and e.capacity_unit='チーム'
                then 1 else confirmed.participant_count end),0)
               from event_applications confirmed where confirmed.event_id=e.event_id
                 and confirmed.status='confirmed') as confirmed_count
            from event_applications a join event_posts e on e.event_id=a.event_id
            where a.applicant_user_id=? order by e.starts_at asc, a.created_at desc
            """,
            (user["user_id"],),
        ).fetchall()
    return {"hosted": [dict(row) for row in hosted], "attending": [dict(row) for row in attending], "notifications": notifications_for_user(user)}


def event_messages_for_user(event_id, user, peer_user_id=""):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    with connect() as conn:
        event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
        if not event:
            raise ValueError("募集が見つかりません")
        application = conn.execute(
            "select 1 from event_applications where event_id=? and applicant_user_id=?",
            (event_id, user["user_id"]),
        ).fetchone()
        if user["user_id"] != event["organizer_user_id"] and not application and not message_peer_eligible(conn, event, user["user_id"], allow_new=True):
            raise PermissionError("この募集の連絡を閲覧する権限がありません")
        peer_user_id = (peer_user_id or "").strip()
        if peer_user_id and user["user_id"] == event["organizer_user_id"]:
            eligible = conn.execute(
                "select 1 from event_applications where event_id=? and applicant_user_id=?",
                (event_id, peer_user_id),
            ).fetchone()
            if not eligible and not message_peer_eligible(conn, event, peer_user_id):
                raise PermissionError("この参加者との連絡を閲覧する権限がありません")
        elif peer_user_id and peer_user_id != event["organizer_user_id"]:
            raise PermissionError("この連絡先は選択できません")
        other_user_id = peer_user_id or (event["organizer_user_id"] if user["user_id"] != event["organizer_user_id"] else "")
        message_sql = """
            select m.message_id, m.body, m.created_at, m.sender_user_id, u.display_name as sender_name
            from event_messages m join user_accounts u on u.user_id=m.sender_user_id
            where m.event_id=? and (m.sender_user_id=? or m.recipient_user_id=?)
        """
        message_args = [event_id, user["user_id"], user["user_id"]]
        if other_user_id:
            message_sql += " and (m.sender_user_id=? or m.recipient_user_id=?)"
            message_args.extend([other_user_id, other_user_id])
        message_sql += " order by m.created_at asc"
        data = conn.execute(
            message_sql,
            message_args,
        ).fetchall()
        conn.execute("""update event_messages set read_at=? where event_id=? and recipient_user_id=?
                     and read_at is null and (?='' or sender_user_id=?)""",
                     (now(), event_id, user["user_id"], other_user_id, other_user_id))
    return [dict(row) for row in data]


def send_event_message(conn, event_id, data, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    if not conn.in_transaction:
        conn.execute("begin immediate")
    event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
    if not event:
        raise ValueError("募集が見つかりません")
    sender = user["user_id"]
    recipient = event["organizer_user_id"]
    if sender == recipient:
        applicant_user_id = event_form_value(data, "recipient_user_id", "宛先", required=True, max_length=120)
        eligible = conn.execute(
            "select 1 from event_applications where event_id=? and applicant_user_id=?",
            (event_id, applicant_user_id),
        ).fetchone()
        if not eligible and not message_peer_eligible(conn, event, applicant_user_id):
            raise PermissionError("この参加者には連絡できません")
        recipient = applicant_user_id
    else:
        eligible = conn.execute(
            "select 1 from event_applications where event_id=? and applicant_user_id=?",
            (event_id, sender),
        ).fetchone()
        if not eligible and not message_peer_eligible(conn, event, sender, allow_new=True):
            raise PermissionError("この募集の主催者へ連絡する権限がありません")
    body = event_form_value(data, "body", "メッセージ", required=True, max_length=2000)
    recent = conn.execute("""select count(*) as hour_count,
              sum(case when julianday(created_at)>=julianday('now','-1 minute') then 1 else 0 end) as minute_count
              from event_messages where sender_user_id=? and julianday(created_at)>=julianday('now','-1 hour')""", (sender,)).fetchone()
    if recent["hour_count"] >= 60 or (recent["minute_count"] or 0) >= 10:
        raise ValueError("送信が続いています。少し時間を空けてからお試しください")
    message_id = slug("message", f"{event_id}:{sender}:{recipient}:{now()}:{secrets.token_hex(4)}")
    conn.execute(
        "insert into event_messages(message_id,event_id,sender_user_id,recipient_user_id,body,created_at) values(?,?,?,?,?,?)",
        (message_id, event_id, sender, recipient, body, now()),
    )
    add_event_notification(conn, recipient, event_id, "new_message", "新しいメッセージがあります", f"{event['title']} について新しい連絡があります。")
    return message_id


def message_peer_eligible(conn, event, user_id, allow_new=False):
    existing = conn.execute("""select 1 from event_messages where event_id=? and
                  ((sender_user_id=? and recipient_user_id=?) or (sender_user_id=? and recipient_user_id=?)) limit 1""",
                  (event["event_id"], user_id, event["organizer_user_id"], event["organizer_user_id"], user_id)).fetchone()
    return bool(existing or (allow_new and event["status"] == "published" and event["starts_at"] > event_local_now()))


PAYMENT_STATUSES = {"unpaid": "未入金", "paid": "入金確認済み", "refund_pending": "精算・返金確認中", "refunded": "返金済み"}


def application_operation_revision(application, data):
    try:
        revision = int(data.get("revision", -1))
    except (TypeError, ValueError):
        revision = -1
    if revision != application["operation_revision"]:
        raise ValueError("申込情報が更新されています。再読み込みして確認してください")


def change_application_count(conn, event_id, application_id, data, user, decision=""):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    conn.execute("begin immediate")
    event = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
    application = conn.execute("select * from event_applications where event_id=? and application_id=?", (event_id, application_id)).fetchone()
    if not event or not application:
        raise PermissionError("この申込を変更する権限がありません")
    if decision:
        event_owner(conn, event_id, user["user_id"])
    elif application["applicant_user_id"] != user["user_id"]:
        raise PermissionError("この申込を変更する権限がありません")
    application_operation_revision(application, data)
    if application["status"] not in {"pending", "confirmed"} or event["status"] not in {"published", "closed"} or event["starts_at"] <= event_local_now():
        raise ValueError("中止済み・開催済み・取消済みの申込は変更できません")
    if application["payment_status"] != "unpaid":
        raise ValueError("入金・精算の記録があります。人数変更は主催者へご相談ください")
    if decision not in {"", "approve", "decline"}:
        raise ValueError("処理が正しくありません")
    raw_count = application["requested_participant_count"] if decision else data.get("participant_count")
    if decision and raw_count is None:
        raise ValueError("人数変更の申請はありません")
    if decision == "decline":
        conn.execute("update event_applications set requested_participant_count=null,operation_revision=operation_revision+1,updated_at=? where application_id=?", (now(), application_id))
        add_event_notification(conn, application["applicant_user_id"], event_id, "count_changed", "人数変更の申請が見送られました", f"{event['title']} は元の{application['participant_count']}名の申込を維持しています。")
        return "declined"
    if not re.fullmatch(r"[0-9]+", str(raw_count or "")) or not 1 <= int(raw_count) <= 100000:
        raise ValueError("参加人数は1から100000の整数で入力してください")
    count, previous = int(raw_count), application["participant_count"]
    if count == previous:
        conn.execute("update event_applications set requested_participant_count=null,operation_revision=operation_revision+1 where application_id=?", (application_id,))
        return "unchanged"
    if event["attendance_deadline"] and event["attendance_deadline"] <= event_local_now():
        raise ValueError("最終参加確認の期限を過ぎています。主催者へ連絡してください")
    if count > previous:
        event_is_open_for_application(event)
    new_cost = application_capacity_cost(event, count)
    if event["capacity"]:
        used = active_confirmed_capacity(conn, event_id)
        if application["status"] == "confirmed":
            used -= application_capacity_cost(event, previous)
        if new_cost > event["capacity"] or (application["status"] == "confirmed" and used + new_cost > event["capacity"]):
            raise ValueError("定員を超えるため人数を変更できません。元の申込は維持されます")
    if not decision and event["acceptance_mode"] == "approval" and application["status"] == "confirmed" and count > previous:
        if application["requested_participant_count"] == count:
            return "pending"
        conn.execute("update event_applications set requested_participant_count=?,operation_revision=operation_revision+1,updated_at=? where application_id=?", (count, now(), application_id))
        add_event_notification(conn, event["organizer_user_id"], event_id, "count_requested", "人数変更の申請があります", f"{event['title']} の申込人数：{previous}名 → {count}名。承認するまでは元の人数を維持します。")
        return "pending"
    conn.execute("insert into event_application_history(application_id,snapshot_json,archived_at) values(?,?,?)", (application_id, json.dumps(dict(application), ensure_ascii=False), now()))
    conn.execute("""update event_applications set participant_count=?,requested_participant_count=null,
                 attendance_version=0,attendance_confirmed_at=null,operation_revision=operation_revision+1,updated_at=? where application_id=?""", (count, now(), application_id))
    update_event_formation(conn, event_id)
    for recipient in {application["applicant_user_id"], event["organizer_user_id"]}:
        add_event_notification(conn, recipient, event_id, "count_changed", "申込人数が変更されました", f"{event['title']}：{previous}名 → {count}名。開催決定済みの場合は、申込代表者が最新人数で最終参加確認を行ってください。")
    audit(conn, "event_count_change", "event_application", application_id, {"from": previous, "to": count, "actor": user["user_id"]})
    return "updated"


def set_application_payment(conn, event_id, application_id, data, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    conn.execute("begin immediate")
    event = event_owner(conn, event_id, user["user_id"])
    application = conn.execute("select * from event_applications where event_id=? and application_id=?", (event_id, application_id)).fetchone()
    if not application:
        raise PermissionError("この申込は管理できません")
    application_operation_revision(application, data)
    status = data.get("payment_status")
    if status not in PAYMENT_STATUSES or not event["fee_amount"]:
        raise ValueError("入金状態を確認してください。無料の募集は入金管理の対象外です")
    if application["status"] == "pending" or application["status"] == "declined":
        raise ValueError("受付確定前の入金は記録できません")
    if status == "paid" and event["minimum_participants"] and (not event["announcement_version"] or application["attendance_version"] != event["announcement_version"]):
        raise ValueError("最終参加確認後に入金を記録してください")
    if status in {"refund_pending", "refunded"} and application["payment_status"] == "unpaid":
        raise ValueError("入金確認の記録がありません")
    note = event_form_value(data, "payment_note", "主催者用メモ", max_length=500)
    if status == application["payment_status"] and note == application["payment_note"]:
        return
    conn.execute("""update event_applications set payment_status=?,payment_note=?,payment_updated_at=?,
                 operation_revision=operation_revision+1,updated_at=? where application_id=?""", (status, note, now(), now(), application_id))
    if status != application["payment_status"]:
        add_event_notification(conn, application["applicant_user_id"], event_id, "payment_updated", "主催者が入金・精算状態を更新しました", f"{event['title']}：{PAYMENT_STATUSES[status]}。主催者による手動記録です。この操作で送金・返金は行われません。ご不明点は主催者へご連絡ください。")
    audit(conn, "event_payment_update", "event_application", application_id, {"from": application["payment_status"], "to": status, "actor": user["user_id"]})


def release_unconfirmed_application(conn, event_id, application_id, data, user):
    if not user.get("authenticated"):
        raise PermissionError("ログインが必要です")
    conn.execute("begin immediate")
    event = event_owner(conn, event_id, user["user_id"])
    application = conn.execute("select * from event_applications where event_id=? and application_id=?", (event_id, application_id)).fetchone()
    if not application:
        raise PermissionError("この申込は管理できません")
    application_operation_revision(application, data)
    if not can_release_unconfirmed(event, application):
        raise ValueError("期限切れ・最終参加未確認・未入金の受付のみ取り消せます")
    reason = event_form_value(data, "reason", "取消理由", required=True, max_length=500)
    conn.execute("""update event_applications set status='cancelled',requested_participant_count=null,
                 organizer_note=?,operation_revision=operation_revision+1,updated_at=? where application_id=?""", (reason, now(), application_id))
    update_event_formation(conn, event_id)
    add_event_notification(conn, application["applicant_user_id"], event_id, "application_released", "主催者が受付を取り消しました", f"{event['title']}\n理由：{reason}\nご不明点は主催者へご連絡ください。")
    audit(conn, "event_application_release", "event_application", application_id, {"actor": user["user_id"]})


def can_release_unconfirmed(event, application):
    return bool(event["status"] in {"published", "closed"} and event["starts_at"] > event_local_now()
                and event["attendance_deadline"] and event["attendance_deadline"] <= event_local_now()
                and event["announcement_version"] and application["status"] == "confirmed"
                and application["attendance_version"] != event["announcement_version"] and application["payment_status"] == "unpaid")


def process_attendance_reminders():
    # Persist the deduplication key and notification together; restarts cannot duplicate them.
    current = event_local_now()
    upcoming = (datetime.strptime(current, "%Y-%m-%d %H:%M") + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
    with connect() as conn:
        conn.execute("begin immediate")
        due = conn.execute("""select a.application_id,a.applicant_user_id,e.event_id,e.title,e.organizer_user_id,
                 e.announcement_version,e.attendance_deadline,
                 case when e.attendance_deadline<=? then 'expired' else 'reminder' end as kind
            from event_posts e join event_applications a on a.event_id=e.event_id
            where e.status in ('published','closed') and e.starts_at>? and e.announcement_version>0
              and e.attendance_deadline<=? and a.status='confirmed' and a.attendance_version!=e.announcement_version
              and not exists(select 1 from event_reminder_deliveries r where r.application_id=a.application_id
                and r.announcement_version=e.announcement_version
                and r.kind=case when e.attendance_deadline<=? then 'expired' else 'reminder' end)
            order by e.attendance_deadline limit 100""", (current, current, upcoming, current)).fetchall()
        for row in due:
            conn.execute("insert into event_reminder_deliveries values(?,?,?,?)", (row["application_id"], row["announcement_version"], row["kind"], now()))
            if row["kind"] == "reminder":
                add_event_notification(conn, row["applicant_user_id"], row["event_id"], "attendance_reminder", "最終参加確認の期限が近づいています", f"{row['title']}\n確認期限：{row['attendance_deadline']}\n開催案内を確認して最終参加確認をお願いします。")
            else:
                add_event_notification(conn, row["organizer_user_id"], row["event_id"], "attendance_expired_host", "最終参加未確認の申込があります", f"{row['title']} の確認期限を過ぎました。申込管理から連絡・期限の見直し・個別の受付取消を行ってください。自動取消はしていません。")
                add_event_notification(conn, row["applicant_user_id"], row["event_id"], "attendance_expired", "最終参加確認の期限を過ぎました", f"{row['title']} の確認期限を過ぎています。主催者へ連絡してください。現在は自動取消されていません。")
        return len(due)


def event_copy_for_owner(conn, event_id, user):
    event = event_owner(conn, event_id, user["user_id"])
    data = dict(event)
    for key in ("event_id", "organizer_user_id", "status", "published_at", "created_at", "updated_at",
                "bank_transfer_details", "payment_deadline", "attendance_deadline", "announcement_version", "announcement_details", "announced_at", "minimum_notice_sent"):
        data.pop(key, None)
    return data


def claimed_circles_for_user(user):
    if not user.get("authenticated") or not user.get("email"):
        return []
    with connect() as conn:
        data = conn.execute(
            """
            select c.circle_id, c.circle_name, c.sport_category, u.university_name, u.prefecture
            from circle_claims cc join circles c on c.circle_id=cc.circle_id
            join universities u on u.university_id=c.university_id
            where lower(cc.claimant_email)=lower(?) and cc.university_email_verified=1
            order by u.university_name, c.circle_name
            """,
            (user["email"],),
        ).fetchall()
    return [dict(row) for row in data]


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
        circle_name = clean_circle_name(item.get("circle_name") or "")
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
        candidate_name = clean_circle_name(item.get("candidate_name") or item.get("circle_name") or "")
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
        email_stop, email_thread = start_event_email_worker()
        from tweetbot_scheduler import start_worker as start_tweetbot_scheduler
        tweetbot_stop, tweetbot_thread = start_tweetbot_scheduler()
        try:
            server.serve_forever()
        finally:
            tweetbot_stop.set()
            if tweetbot_thread:
                tweetbot_thread.join(timeout=25)
            email_stop.set()
            if email_thread:
                email_thread.join(timeout=20)
            server.server_close()
    except Exception as exc:
        log(f"failed {type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
