import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "circlematch.sqlite"
sys.path.insert(0, str(ROOT / "work"))

from import_kanto_official_crawl import crawl_university, upsert_circle  # noqa: E402


PRIVATE_UNIVERSITIES = [
    ("帝京大学", "東京都", "板橋区", "https://www.teikyo-u.ac.jp/"),
    ("大東文化大学", "東京都", "板橋区", "https://www.daito.ac.jp/"),
    ("拓殖大学", "東京都", "文京区", "https://www.takushoku-u.ac.jp/"),
    ("東京電機大学", "東京都", "足立区", "https://www.dendai.ac.jp/"),
    ("東京経済大学", "東京都", "国分寺市", "https://www.tku.ac.jp/"),
    ("武蔵大学", "東京都", "練馬区", "https://www.musashi.ac.jp/"),
    ("武蔵野大学", "東京都", "江東区", "https://www.musashino-u.ac.jp/"),
    ("亜細亜大学", "東京都", "武蔵野市", "https://www.asia-u.ac.jp/"),
    ("大妻女子大学", "東京都", "千代田区", "https://www.otsuma.ac.jp/"),
    ("共立女子大学", "東京都", "千代田区", "https://www.kyoritsu-wu.ac.jp/"),
    ("昭和女子大学", "東京都", "世田谷区", "https://www.swu.ac.jp/"),
    ("東京女子大学", "東京都", "杉並区", "https://www.twcu.ac.jp/"),
    ("白百合女子大学", "東京都", "調布市", "https://www.shirayuri.ac.jp/"),
    ("清泉女子大学", "東京都", "品川区", "https://www.seisen-u.ac.jp/"),
    ("聖心女子大学", "東京都", "渋谷区", "https://www.u-sacred-heart.ac.jp/"),
    ("東京家政大学", "東京都", "板橋区", "https://www.tokyo-kasei.ac.jp/"),
    ("東京農業大学", "東京都", "世田谷区", "https://www.nodai.ac.jp/"),
    ("玉川大学", "東京都", "町田市", "https://www.tamagawa.jp/"),
    ("桜美林大学", "東京都", "町田市", "https://www.obirin.ac.jp/"),
    ("多摩美術大学", "東京都", "八王子市", "https://www.tamabi.ac.jp/"),
    ("武蔵野美術大学", "東京都", "小平市", "https://www.musabi.ac.jp/"),
    ("東京工科大学", "東京都", "八王子市", "https://www.teu.ac.jp/"),
    ("東京工芸大学", "東京都", "中野区", "https://www.t-kougei.ac.jp/"),
    ("二松學舍大学", "東京都", "千代田区", "https://www.nishogakusha-u.ac.jp/"),
    ("大正大学", "東京都", "豊島区", "https://www.tais.ac.jp/"),
    ("立正大学", "東京都", "品川区", "https://www.ris.ac.jp/"),
    ("和光大学", "東京都", "町田市", "https://www.wako.ac.jp/"),
    ("明星大学", "東京都", "日野市", "https://www.meisei-u.ac.jp/"),
    ("杏林大学", "東京都", "三鷹市", "https://www.kyorin-u.ac.jp/univ/"),
    ("帝京平成大学", "東京都", "豊島区", "https://www.thu.ac.jp/"),
    ("東京国際大学", "埼玉県", "川越市", "https://www.tiu.ac.jp/"),
    ("獨協大学", "埼玉県", "草加市", "https://www.dokkyo.ac.jp/"),
    ("文教大学", "埼玉県", "越谷市", "https://www.bunkyo.ac.jp/"),
    ("城西大学", "埼玉県", "坂戸市", "https://www.josai.ac.jp/"),
    ("埼玉工業大学", "埼玉県", "深谷市", "https://www.sit.ac.jp/"),
    ("日本工業大学", "埼玉県", "南埼玉郡宮代町", "https://www.nit.ac.jp/"),
    ("淑徳大学", "千葉県", "千葉市", "https://www.shukutoku.ac.jp/"),
    ("千葉工業大学", "千葉県", "習志野市", "https://www.it-chiba.ac.jp/"),
    ("麗澤大学", "千葉県", "柏市", "https://www.reitaku-u.ac.jp/"),
    ("城西国際大学", "千葉県", "東金市", "https://www.jiu.ac.jp/"),
    ("神田外語大学", "千葉県", "千葉市", "https://www.kandagaigo.ac.jp/kuis/"),
    ("東京情報大学", "千葉県", "千葉市", "https://www.tuis.ac.jp/"),
    ("明海大学", "千葉県", "浦安市", "https://www.meikai.ac.jp/"),
    ("千葉商科大学", "千葉県", "市川市", "https://www.cuc.ac.jp/"),
    ("敬愛大学", "千葉県", "千葉市", "https://www.u-keiai.ac.jp/"),
    ("中央学院大学", "千葉県", "我孫子市", "https://www.cgu.ac.jp/"),
    ("東邦大学", "千葉県", "習志野市", "https://www.toho-u.ac.jp/"),
    ("鶴見大学", "神奈川県", "横浜市", "https://www.tsurumi-u.ac.jp/"),
    ("関東学院大学", "神奈川県", "横浜市", "https://univ.kanto-gakuin.ac.jp/"),
    ("フェリス女学院大学", "神奈川県", "横浜市", "https://www.ferris.ac.jp/"),
    ("横浜商科大学", "神奈川県", "横浜市", "https://www.shodai.ac.jp/"),
    ("湘南工科大学", "神奈川県", "藤沢市", "https://www.shonan-it.ac.jp/"),
    ("神奈川工科大学", "神奈川県", "厚木市", "https://www.kait.jp/"),
    ("産業能率大学", "神奈川県", "伊勢原市", "https://www.sanno.ac.jp/"),
    ("相模女子大学", "神奈川県", "相模原市", "https://www.sagami-wu.ac.jp/"),
    ("白鴎大学", "栃木県", "小山市", "https://hakuoh.jp/"),
    ("作新学院大学", "栃木県", "宇都宮市", "https://www.sakushin-u.ac.jp/"),
    ("常磐大学", "茨城県", "水戸市", "https://www.tokiwa.ac.jp/"),
    ("茨城キリスト教大学", "茨城県", "日立市", "https://www.icc.ac.jp/"),
    ("関東学園大学", "群馬県", "太田市", "https://www.kanto-gakuen.ac.jp/univer/"),
    ("上武大学", "群馬県", "伊勢崎市", "https://www.jobu.ac.jp/"),
    ("共愛学園前橋国際大学", "群馬県", "前橋市", "https://www.kyoai.ac.jp/"),
    ("高崎健康福祉大学", "群馬県", "高崎市", "https://www.takasaki-u.ac.jp/"),
    ("目白大学", "東京都", "新宿区", "https://www.mejiro.ac.jp/"),
    ("高千穂大学", "東京都", "杉並区", "https://www.takachiho.jp/"),
    ("東京富士大学", "東京都", "新宿区", "https://www.fuji.ac.jp/"),
    ("嘉悦大学", "東京都", "小平市", "https://www.kaetsu.ac.jp/"),
    ("東京成徳大学", "東京都", "北区", "https://www.tsu.ac.jp/"),
    ("東京医療保健大学", "東京都", "品川区", "https://www.thcu.ac.jp/"),
    ("日本社会事業大学", "東京都", "清瀬市", "https://www.jcsw.ac.jp/"),
    ("日本文化大学", "東京都", "八王子市", "https://www.nihonbunka-u.ac.jp/"),
    ("デジタルハリウッド大学", "東京都", "千代田区", "https://www.dhw.ac.jp/"),
    ("ルーテル学院大学", "東京都", "三鷹市", "https://www.luther.ac.jp/"),
    ("江戸川大学", "千葉県", "流山市", "https://www.edogawa-u.ac.jp/"),
    ("聖徳大学", "千葉県", "松戸市", "https://www.seitoku-u.ac.jp/"),
    ("和洋女子大学", "千葉県", "市川市", "https://www.wayo.ac.jp/"),
    ("川村学園女子大学", "千葉県", "我孫子市", "https://www.kgwu.ac.jp/"),
    ("植草学園大学", "千葉県", "千葉市", "https://www.uekusa.ac.jp/"),
    ("清和大学", "千葉県", "木更津市", "https://www.seiwa-univ.ac.jp/"),
    ("開智国際大学", "千葉県", "柏市", "https://www.kaichi.ac.jp/"),
    ("東京基督教大学", "千葉県", "印西市", "https://www.tci.ac.jp/"),
    ("東京福祉大学", "群馬県", "伊勢崎市", "https://www.tokyo-fukushi.ac.jp/"),
    ("育英大学", "群馬県", "高崎市", "https://www.ikuei-g.ac.jp/university/"),
]


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:80]}"


def upsert_university(conn, name, prefecture, city, official_url):
    timestamp = now()
    university_id = slug("u", name)
    existing = conn.execute(
        "select university_id from universities where university_name=? order by campus_name limit 1",
        (name,),
    ).fetchone()
    if existing:
        conn.execute(
            """
            update universities
            set prefecture=?, city=?, official_url=?, source_url=?, updated_at=?
            where university_id=?
            """,
            (prefecture, city, official_url, official_url, timestamp, existing["university_id"]),
        )
        return existing["university_id"], False
    conn.execute(
        """
        insert into universities(
          university_id, university_name, prefecture, city, campus_name,
          official_url, source_url, created_at, updated_at
        )
        values(?,?,?,?,?,?,?,?,?)
        """,
        (university_id, name, prefecture, city, "", official_url, official_url, timestamp, timestamp),
    )
    return university_id, True


def main():
    new_only = "--new-only" in sys.argv
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inserted_universities = 0
    total_inserted_circles = 0
    detail = []
    for name, prefecture, city, official_url in PRIVATE_UNIVERSITIES:
        university_id, created = upsert_university(conn, name, prefecture, city, official_url)
        conn.commit()
        if created:
            inserted_universities += 1
        existing_count = conn.execute(
            "select count(*) from circles where university_id=?",
            (university_id,),
        ).fetchone()[0]
        if new_only and not created:
            detail.append({"university": name, "existing_before": existing_count, "inserted": 0, "skipped": "not_new"})
            continue
        if existing_count >= 120:
            detail.append({"university": name, "existing_before": existing_count, "inserted": 0, "skipped": "already_enough"})
            continue
        pages, names_by_page = crawl_university(name, official_url)
        inserted = 0
        for source_url, names in names_by_page.items():
            for circle_name in names:
                inserted += upsert_circle(conn, university_id, name, circle_name, source_url)
        conn.commit()
        total_inserted_circles += inserted
        item = {
            "university": name,
            "prefecture": prefecture,
            "existing_before": existing_count,
            "pages_seen": len(pages),
            "candidate_names": sum(len(v) for v in names_by_page.values()),
            "inserted": inserted,
        }
        detail.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
    print(json.dumps({
        "inserted_universities": inserted_universities,
        "inserted_circles": total_inserted_circles,
        "detail": detail,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
