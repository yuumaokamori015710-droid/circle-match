import json
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

DB_PATH = Path("outputs/circlematch.sqlite")


class LinkTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.links = []
        self._in_a = False
        self._href = ""
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._in_a = True
            self._href = dict(attrs).get("href", "")
            self._text = []

    def handle_endtag(self, tag):
        if tag == "a" and self._in_a:
            text = clean_name(" ".join(self._text))
            if text:
                self.links.append((text, self._href))
            self._in_a = False

    def handle_data(self, data):
        text = clean_name(data)
        if text:
            self.parts.append(text)
            if self._in_a:
                self._text.append(text)


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:80]}"


def clean_name(name):
    return re.sub(r"\s+", " ", name or "").strip()


def club_label(part):
    part = clean_name(part)
    part = part.lstrip("・◎■●○ ").strip()
    part = re.sub(r"^【準備団体】", "", part).strip()
    if len(part) > 45 and ("（" in part or "(" in part):
        part = re.split(r"[（(]", part, maxsplit=1)[0]
    return clean_name(part)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    parser = LinkTextParser()
    parser.feed(data)
    return parser


def sport_category(name):
    rules = [
        ("サッカー", ["サッカー", "蹴球", "ソッカー"]),
        ("フットサル", ["フットサル"]),
        ("バスケットボール", ["バスケット"]),
        ("テニス", ["テニス", "庭球"]),
        ("バレーボール", ["バレーボール", "排球"]),
        ("野球", ["野球", "ベースボール"]),
        ("バドミントン", ["バドミントン"]),
        ("ラグビー", ["ラグビー"]),
        ("アメリカンフットボール", ["アメリカンフットボール"]),
        ("ラクロス", ["ラクロス"]),
        ("ハンドボール", ["ハンドボール"]),
        ("ホッケー", ["ホッケー"]),
        ("卓球", ["卓球"]),
        ("陸上競技", ["陸上"]),
        ("水泳", ["水泳", "泳"]),
        ("武道", ["合気道", "空手", "弓道", "剣道", "拳法", "柔道", "少林寺", "居合"]),
        ("ダンス", ["ダンス", "Dance"]),
        ("音楽", ["合唱", "吹奏楽", "管弦楽", "軽音", "ギター", "ジャズ", "マンドリン"]),
        ("その他", []),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name, default="公認サークル"):
    if "体育会" in name:
        return "体育会"
    if name.endswith("部") or "部(" in name or "部（" in name or "部・" in name:
        return "部活"
    if "同好会" in name:
        return "同好会"
    if "愛好会" in name:
        return "非公認サークル"
    if "学生団体" in name or "委員会" in name or "自治会" in name:
        return "学生団体"
    if "サークル" in name:
        return "公認サークル"
    return default


def audit(conn, action, entity_type, entity_id, payload):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), now()),
    )


def upsert_circle(conn, university_name, circle_name, source_url, note, org_default="公認サークル"):
    circle_name = clean_name(circle_name)
    if not circle_name or len(circle_name) > 80:
        return 0
    uni = conn.execute(
        "select university_id from universities where university_name=? order by campus_name limit 1",
        (university_name,),
    ).fetchone()
    if not uni:
        raise ValueError(f"university not found: {university_name}")
    existing = conn.execute(
        "select circle_id from circles where university_id=? and circle_name=?",
        (uni["university_id"], circle_name),
    ).fetchone()
    circle_id = existing["circle_id"] if existing else slug("c", f"{uni['university_id']}_{circle_name}")
    timestamp = now()
    conn.execute(
        """
        insert into circles(
          circle_id, university_id, circle_name, organization_type, sport_category, activity_area,
          source_type, source_url, verification_status, public_status,
          last_checked_at, sns_url, owner_notes, created_at, updated_at
        )
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
            uni["university_id"],
            circle_name,
            organization_type(circle_name, org_default),
            sport_category(circle_name),
            university_name,
            "university_official",
            source_url,
            "university_verified",
            "published",
            timestamp[:10],
            "",
            "",
            timestamp,
            timestamp,
        ),
    )
    conn.execute(
        """
        insert or replace into data_sources(
          source_id, entity_type, entity_id, source_type, source_url, memo, checked_at, created_at
        )
        values(?,?,?,?,?,?,?,?)
        """,
        (slug("src", f"{circle_id}_{source_url}"), "circle", circle_id, "university_official", source_url, note, timestamp[:10], timestamp),
    )
    if not existing:
        audit(conn, "official_club_import", "circle", circle_id, {"university": university_name, "circle_name": circle_name, "source_url": source_url})
        return 1
    return 0


def extract_hosei():
    urls = [
        ("https://www.hosei.ac.jp/campuslife/club/taiikukai", "部活"),
        ("https://www.hosei.ac.jp/campuslife/club/toroku", "公認サークル"),
        ("https://www.hosei.ac.jp/campuslife/club/gakujutsu", "学生団体"),
    ]
    stop = {"あ行", "か行", "さ行", "た行", "な行", "は行", "ま行", "や行", "ら行", "わ行", "体育会", "登録団体", "学術団体"}
    names = []
    for url, default in urls:
        parser = fetch(url)
        for part in parser.parts:
            if part in stop or len(part) > 60:
                continue
            if any(word in part for word in ["部", "会", "団", "サークル", "同好", "愛好", "研究", "委員"]):
                names.append((part, url, default))
    return "法政大学", names, "法政大学公式のクラブ・サークル活動ページから団体名のみ登録"


def extract_senshu():
    url = "https://www.senshu-u.ac.jp/campuslife/activity/club/"
    parser = fetch(url)
    names = []
    for text, href in parser.links:
        full_url = urllib.parse.urljoin(url, href)
        if not full_url.startswith("https://www.senshu-u.ac.jp/"):
            continue
        if len(text) > 70:
            continue
        if any(word in text for word in ["部", "会", "団", "サークル", "同好", "愛好", "研究", "委員", "クラブ"]):
            default = "部活" if "/sports/clubs/" in full_url else "公認サークル"
            names.append((text, full_url, default))
    return "専修大学", names, "専修大学公式の自治会・クラブ・サークルページから団体名のみ登録"


def extract_kobe():
    url = "https://www.kobe-u.ac.jp/ja/campus-life/general/clubs/official/"
    parser = fetch(url)
    names = []
    current_default = "公認サークル"
    for part in parser.parts:
        if part.startswith("Ａ.文化総部") or part.startswith("A.文化総部"):
            current_default = "公認サークル"
            continue
        if part.startswith("Ｂ.体育会") or part.startswith("B.体育会"):
            current_default = "部活"
            continue
        if part.startswith("Ｃ.応援団") or part.startswith("C.応援団"):
            current_default = "学生団体"
            continue
        if part.startswith("Ｄ.学生学会") or part.startswith("D.学生学会"):
            current_default = "学生団体"
            continue
        m = re.match(r"^[A-DＡ-Ｄ]\d{3}\s+(.+)$", part)
        if m:
            name = clean_name(m.group(1))
            names.append((name, url, current_default))
    return "神戸大学", names, "神戸大学公式の課外活動団体紹介ページから団体名のみ登録"


def extract_ocha():
    url = "https://www.ocha.ac.jp/campuslife/circle/r_extracurricular-activities.html"
    parser = fetch(url)
    names = []
    current_default = "公認サークル"
    stop = {"文化系公認団体", "体育系公認団体", "準公認団体"}
    for idx, part in enumerate(parser.parts):
        if idx < 37 or idx > 93:
            continue
        if part == "体育系公認団体":
            current_default = "部活"
            continue
        if part == "準公認団体":
            current_default = "同好会"
            continue
        if part in stop:
            continue
        names.append((club_label(part), url, current_default))
    return "お茶の水女子大学", names, "お茶の水女子大学公式の課外活動団体一覧から団体名のみ登録"


def extract_chiba():
    url = "https://www.chiba-u.ac.jp/campus-life/club/"
    parser = fetch(url)
    names = []
    current_default = "公認サークル"
    headings = {
        "全学公認・西千葉キャンパス 体育会",
        "全学公認・西千葉キャンパス 体育系サークル",
        "全学公認・西千葉キャンパス 文化系サークル",
        "全学公認・西千葉キャンパス 音楽系サークル",
        "全学準公認・西千葉キャンパス",
        "全学公認・亥鼻キャンパス 体育系サークル",
        "全学公認・亥鼻キャンパス 文科系サークル",
        "全学公認・亥鼻キャンパス 音楽系サークル",
        "全学準公認・亥鼻キャンパス",
        "国際教養学部 公認",
        "文学部 公認",
        "法政経学部 公認",
        "工学部 公認",
        "理学部 公認",
        "園芸学部 公認",
        "医学部 公認",
        "薬学部 公認",
        "看護学部 公認",
    }
    stop = {"HP", "X", "Instagram", "ホーム", "学生生活", "課外活動団体", "メイン", "コンテンツ"}
    for idx, part in enumerate(parser.parts):
        if idx < 108 or idx > 317:
            continue
        if part in headings:
            current_default = "部活" if "体育会" in part else ("同好会" if "準公認" in part else "公認サークル")
            continue
        if part in stop or len(part) > 80:
            continue
        names.append((club_label(part), url, current_default))
    return "千葉大学", names, "千葉大学公式の課外活動団体一覧から団体名のみ登録"


def extract_sophia():
    url = "https://www.sophia.ac.jp/jpn/campuslife/kagai/"
    parser = fetch(url)
    names = []
    current_default = "部活"
    headings = {"体育団体連合会", "文化団体連合会", "音楽協議会", "演劇協議会", "同好会愛好会連合", "その他"}
    stop = {"課外活動団体一覧（クラブ・サークル）", "2025年3月現在"}
    for idx, part in enumerate(parser.parts):
        if idx < 195 or idx > 293:
            continue
        if part in headings:
            current_default = "部活" if part == "体育団体連合会" else ("同好会" if part == "同好会愛好会連合" else "公認サークル")
            continue
        if part in stop:
            continue
        names.append((club_label(part), url, current_default))
    return "上智大学", names, "上智大学公式の課外活動団体一覧から団体名のみ登録"


def extract_kokushikan():
    url = "https://www.kokushikan.ac.jp/campus_life/activity/"
    parser = fetch(url)
    names = []
    current_default = "部活"
    stop = {
        "詳細", "活動案内", "紹介動画", "部", "同好会",
        "スポーツ協議会指定クラブ", "クラブ（スポーツ系）", "クラブ（武道系）", "クラブ（文化系）",
        "サークル", "届出団体", "学園祭実行委員",
    }
    for idx, part in enumerate(parser.parts):
        if idx < 801 or idx > 1039:
            continue
        if part in {"クラブ（スポーツ系）", "クラブ（武道系）", "スポーツ協議会指定クラブ"}:
            current_default = "部活"
            continue
        if part == "クラブ（文化系）":
            current_default = "公認サークル"
            continue
        if part == "サークル":
            current_default = "公認サークル"
            continue
        if part in stop or part.endswith("KB)") or "MB" in part:
            continue
        if len(part) > 80 or part.startswith("（"):
            continue
        names.append((club_label(part), url, current_default))
    return "国士舘大学", names, "国士舘大学公式のクラブ・サークル一覧から団体名のみ登録"


def extract_icu():
    url = "https://www.icu.ac.jp/campuslife/club/"
    parser = fetch(url)
    names = []
    for idx, part in enumerate(parser.parts):
        if idx < 259 or idx > 300:
            continue
        default = "部活" if "部" in part else "公認サークル"
        names.append((club_label(part), url, default))
    return "国際基督教大学", names, "国際基督教大学公式の部活・サークル一覧から団体名のみ登録"


def extract_aiu():
    url = "https://web.aiu.ac.jp/campuslife/clubs/"
    parser = fetch(url)
    names = []
    current_default = "部活"
    headings = {"スポーツ系", "音楽・ダンス系", "学術系", "文化系", "社会活動・ボランティア系", "特別団体"}
    for idx, part in enumerate(parser.parts):
        if idx < 255 or idx > 317:
            continue
        if part in headings:
            current_default = "部活" if part == "スポーツ系" else ("学生団体" if part in {"社会活動・ボランティア系", "特別団体"} else "公認サークル")
            continue
        names.append((club_label(part), url, current_default))
    return "国際教養大学", names, "国際教養大学公式の公認クラブ・特別団体一覧から団体名のみ登録"


def extract_seijo():
    url = "https://www.seijo.ac.jp/about/campus-life/club/"
    parser = fetch(url)
    names = []
    current_default = "公認サークル"
    stop_fragments = ["所属団体", "団体紹介", "学友会", "■", "※"]
    for idx, part in enumerate(parser.parts):
        if idx < 164 or idx > 280:
            continue
        if "体育部連合会" in part:
            current_default = "部活"
            continue
        if "届け出サークル" in part:
            current_default = "公認サークル"
            continue
        if any(fragment in part for fragment in stop_fragments) or part.startswith("（"):
            continue
        label = club_label(part)
        if len(label) >= 2:
            names.append((label, url, current_default))
    return "成城大学", names, "成城大学公式の学友会団体紹介ページから団体名のみ登録"


def extract_seikei():
    url = "https://www.seikei.ac.jp/university/campuslife/club.html"
    parser = fetch(url)
    names = []
    current_default = "公認サークル"
    stop = {"課外活動団体一覧", "本部団体", "体育会団体", "文化会団体", "届出団体（体育系）", "届出団体（文化系）"}
    for idx, part in enumerate(parser.parts):
        if idx < 196 or idx > 429:
            continue
        if part == "体育会団体":
            current_default = "部活"
            continue
        if part == "文化会団体":
            current_default = "公認サークル"
            continue
        if part.startswith("届出団体"):
            current_default = "公認サークル"
            continue
        if part in stop or part.startswith("（") or len(part) > 80:
            continue
        label = club_label(part)
        if len(label) >= 2:
            names.append((label, url, current_default))
    return "成蹊大学", names, "成蹊大学公式の課外活動団体一覧から団体名のみ登録"


def extract_nittai():
    url = "https://www.nittai.ac.jp/club/"
    parser = fetch(url)
    names = []
    current_default = "部活"
    headings = {"総務部", "運動部", "応援部", "厚生文化部", "運動部2部", "研究・調査部", "公認団体"}
    for idx, part in enumerate(parser.parts):
        if idx < 20 or idx > 96:
            continue
        if part in headings:
            current_default = "部活" if part in {"総務部", "運動部", "応援部", "運動部2部"} else "公認サークル"
            continue
        names.append((club_label(part), url, current_default))
    return "日本体育大学", names, "日本体育大学公式の学友会クラブ活動一覧から団体名のみ登録"


def extract_kitasato():
    url = "https://www.kitasato-u.ac.jp/jp/campuslife/club/"
    parser = fetch(url)
    names = []
    current_default = "部活"
    prefix = ""
    stop_fragments = ["合同会報", "詳細は", "紹介", "ガイド", "一覧", "北里会", "体育会", "文化会", "体育系", "文化系", "MB)"]
    for idx, part in enumerate(parser.parts):
        if idx < 816 or idx > 995:
            continue
        if "獣医学部" in part:
            prefix = "獣医学部 "
            continue
        if "医学部" in part:
            prefix = "医学部 "
            continue
        if "海洋生命科学部" in part:
            prefix = "海洋生命科学部 "
            continue
        if "看護学部" in part:
            prefix = "看護学部 "
            continue
        if "理学部" in part:
            prefix = "理学部 "
            continue
        if "医療衛生学部" in part:
            prefix = "医療衛生学部 "
            continue
        if "未来工学部" in part:
            prefix = "未来工学部 "
            continue
        if part.startswith("体育会") or part == "体育系":
            current_default = "部活"
            continue
        if part.startswith("文化会") or part == "文化系":
            current_default = "公認サークル"
            continue
        if any(fragment in part for fragment in stop_fragments) or part.startswith("("):
            continue
        label = club_label(part)
        if len(label) < 2 or len(label) > 70:
            continue
        names.append((f"{prefix}{label}", url, current_default))
    return "北里大学", names, "北里大学公式の北里会団体紹介ページから団体名のみ登録"


def extract_toin():
    url = "https://toin.ac.jp/univ/club/"
    parser = fetch(url)
    names = []
    current_default = "部活"
    stop = {"－運動部－", "－運動部支援－", "－文化部－", "同好会", "サークル", "クラブ・サークル"}
    for idx, part in enumerate(parser.parts):
        if idx < 34 or idx > 211:
            continue
        if part == "－文化部－":
            current_default = "公認サークル"
            continue
        if part == "同好会":
            current_default = "同好会"
            continue
        if part == "サークル":
            current_default = "公認サークル"
            continue
        if part in stop or len(part) > 70:
            continue
        if not any(word in part for word in ["部", "会", "団", "サークル", "同好", "愛好", "クラブ"]):
            continue
        names.append((club_label(part), url, current_default))
    return "桐蔭横浜大学", names, "桐蔭横浜大学公式のクラブ・サークル活動ページから団体名のみ登録"


def extract_ouhs():
    url = "https://www.ouhs.jp/campuslife/club/"
    parser = fetch(url)
    names = []
    current_default = "部活"
    stop = {"クラブ", "クラブTOP", "クラブニュース", "動画で見るクラブ活動", "クラブハウス", "同好会"}
    for idx, part in enumerate(parser.parts):
        if idx < 41 or idx > 98:
            continue
        if part == "同好会":
            current_default = "同好会"
            continue
        if part in stop or len(part) > 70:
            continue
        if not any(word in part for word in ["部", "会", "同好"]):
            continue
        names.append((club_label(part), url, current_default))
    return "大阪体育大学", names, "大阪体育大学公式のクラブ・スポーツ局ページから団体名のみ登録"


def extract_iwate():
    url = "https://www.iwate-u.ac.jp/campus/activity/club.html"
    parser = fetch(url)
    names = []
    current_default = "公認サークル"
    stop = {
        "学生委員会", "学友会", "体育系サークル", "文化系サークル", "同好会",
        "サークル紹介", "サークル・同好会紹介・パンフレット", "サークル・同好会紹介パンフレット",
    }
    for idx, part in enumerate(parser.parts):
        if idx < 275 or idx > 444:
            continue
        if part == "体育系サークル":
            current_default = "部活"
            continue
        if part == "文化系サークル":
            current_default = "公認サークル"
            continue
        if part == "同好会":
            current_default = "同好会"
            continue
        if part in stop or len(part) > 80:
            continue
        if not any(word in part for word in ["部", "会", "団", "サークル", "同好", "愛好", "研究", "クラブ", "委員"]):
            continue
        names.append((club_label(part), url, current_default))
    return "岩手大学", names, "岩手大学公式のサークル紹介ページから団体名のみ登録"


def extract_hirosaki():
    url = "https://www.hirosaki-u.ac.jp/campuslife/kagai/club/"
    parser = fetch(url)
    names = []
    current_default = "部活"
    stop_fragments = ["団体", "現在", "サークル・課外活動", "課外活動", "その他体育系", "文化系"]
    for idx, part in enumerate(parser.parts):
        if idx < 24 or idx > 320:
            continue
        if "その他体育系" in part:
            current_default = "公認サークル"
            continue
        if "文化系" in part:
            current_default = "公認サークル"
            continue
        if any(fragment in part for fragment in stop_fragments) or len(part) > 80:
            continue
        if not any(word in part for word in ["部", "会", "団", "サークル", "同好", "愛好", "研究", "クラブ", "委員"]):
            continue
        names.append((club_label(part), url, current_default))
    return "弘前大学", names, "弘前大学公式の課外活動団体ページから団体名のみ登録"


def extract_nagasaki():
    url = "https://www.nagasaki-u.ac.jp/ja/campuslife/circle/all/index.html"
    parser = fetch(url)
    names = []
    current_default = "部活"
    current_faculty = ""
    faculty_names = {"経済学部", "医学部", "保健学科", "歯学部", "薬学部", "工学部", "水産学部"}
    stop = {
        "文化系サークル", "体育系サークル", "その他の学生団体", "学部毎の団体", "●・・・ 新規団体",
        "Instagram", "Instagrami", "Instagramr", "Twitter", "Youtube", "Homepage", "Facebook", "・", "●",
    }
    for idx, part in enumerate(parser.parts):
        if idx < 190 or idx > 915:
            continue
        if part in faculty_names:
            current_faculty = part
            current_default = "公認サークル"
            continue
        if part == "体育系サークル":
            current_default = "部活"
            continue
        if part == "文化系サークル":
            current_default = "公認サークル"
            continue
        if part in stop or len(part) > 80:
            continue
        name = club_label(part)
        if not name or name in stop:
            continue
        if len(name) > 70 or any(fragment in name for fragment in ["問い合わせ", "奨学金", "授業料", "免除", "制度"]):
            continue
        if idx >= 656 and current_faculty:
            name = f"{current_faculty} {name}"
        if not any(word in name for word in ["部", "会", "団", "サークル", "同好", "研究", "クラブ", "委員", "連合", "NGO", "PROJECT", "Factory"]):
            continue
        names.append((name, url, current_default))
    return "長崎大学", names, "長崎大学公式のサークル一覧ページから団体名のみ登録"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    total_inserted = 0
    detail = []
    for university, names, note in [
        extract_hosei(),
        extract_senshu(),
        extract_kobe(),
        extract_ocha(),
        extract_chiba(),
        extract_sophia(),
        extract_kokushikan(),
        extract_icu(),
        extract_aiu(),
        extract_seijo(),
        extract_seikei(),
        extract_nittai(),
        extract_kitasato(),
        extract_toin(),
        extract_ouhs(),
        extract_iwate(),
        extract_hirosaki(),
        extract_nagasaki(),
    ]:
        inserted = 0
        seen = set()
        for circle_name, source_url, org_default in names:
            key = circle_name
            if key in seen:
                continue
            seen.add(key)
            inserted += upsert_circle(conn, university, circle_name, source_url, note, org_default)
        detail.append({"university": university, "candidate_names": len(seen), "inserted": inserted})
        total_inserted += inserted
    conn.commit()
    print(json.dumps({
        "inserted": total_inserted,
        "detail": detail,
        "total_circles": conn.execute("select count(*) from circles").fetchone()[0],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
