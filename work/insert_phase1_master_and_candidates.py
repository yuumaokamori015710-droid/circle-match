import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("outputs/circlematch.sqlite")


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:48]}"


PHASE1_UNIVERSITIES = [
    ("一橋大学", "東京都", "国立市", "", "https://www.hit-u.ac.jp/"),
    ("東京科学大学", "東京都", "目黒区", "", "https://www.isct.ac.jp/"),
    ("お茶の水女子大学", "東京都", "文京区", "", "https://www.ocha.ac.jp/"),
    ("東京外国語大学", "東京都", "府中市", "", "https://www.tufs.ac.jp/"),
    ("東京学芸大学", "東京都", "小金井市", "", "https://www.u-gakugei.ac.jp/"),
    ("東京農工大学", "東京都", "府中市", "", "https://www.tuat.ac.jp/"),
    ("東京都立大学", "東京都", "八王子市", "", "https://www.tmu.ac.jp/"),
    ("青山学院大学", "東京都", "渋谷区", "", "https://www.aoyama.ac.jp/"),
    ("立教大学", "東京都", "豊島区", "", "https://www.rikkyo.ac.jp/"),
    ("中央大学", "東京都", "八王子市", "", "https://www.chuo-u.ac.jp/"),
    ("法政大学", "東京都", "千代田区", "", "https://www.hosei.ac.jp/"),
    ("上智大学", "東京都", "千代田区", "", "https://www.sophia.ac.jp/"),
    ("学習院大学", "東京都", "豊島区", "", "https://www.univ.gakushuin.ac.jp/"),
    ("成蹊大学", "東京都", "武蔵野市", "", "https://www.seikei.ac.jp/university/"),
    ("成城大学", "東京都", "世田谷区", "", "https://www.seijo.ac.jp/"),
    ("明治学院大学", "東京都", "港区", "", "https://www.meijigakuin.ac.jp/"),
    ("國學院大學", "東京都", "渋谷区", "", "https://www.kokugakuin.ac.jp/"),
    ("日本大学", "東京都", "千代田区", "", "https://www.nihon-u.ac.jp/"),
    ("東洋大学", "東京都", "文京区", "", "https://www.toyo.ac.jp/"),
    ("駒澤大学", "東京都", "世田谷区", "", "https://www.komazawa-u.ac.jp/"),
    ("専修大学", "東京都", "千代田区", "", "https://www.senshu-u.ac.jp/"),
    ("東海大学", "神奈川県", "平塚市", "", "https://www.u-tokai.ac.jp/"),
    ("神奈川大学", "神奈川県", "横浜市", "", "https://www.kanagawa-u.ac.jp/"),
    ("関西大学", "大阪府", "吹田市", "", "https://www.kansai-u.ac.jp/"),
    ("関西学院大学", "兵庫県", "西宮市", "", "https://www.kwansei.ac.jp/"),
    ("同志社大学", "京都府", "京都市", "", "https://www.doshisha.ac.jp/"),
    ("立命館大学", "京都府", "京都市", "", "https://www.ritsumei.ac.jp/"),
    ("近畿大学", "大阪府", "東大阪市", "", "https://www.kindai.ac.jp/"),
    ("甲南大学", "兵庫県", "神戸市", "", "https://www.konan-u.ac.jp/"),
    ("龍谷大学", "京都府", "京都市", "", "https://www.ryukoku.ac.jp/"),
    ("京都産業大学", "京都府", "京都市", "", "https://www.kyoto-su.ac.jp/"),
    ("大阪公立大学", "大阪府", "大阪市", "", "https://www.omu.ac.jp/"),
    ("兵庫県立大学", "兵庫県", "神戸市", "", "https://www.u-hyogo.ac.jp/"),
    ("名古屋工業大学", "愛知県", "名古屋市", "", "https://www.nitech.ac.jp/"),
    ("名古屋市立大学", "愛知県", "名古屋市", "", "https://www.nagoya-cu.ac.jp/"),
    ("南山大学", "愛知県", "名古屋市", "", "https://www.nanzan-u.ac.jp/"),
    ("中京大学", "愛知県", "名古屋市", "", "https://www.chukyo-u.ac.jp/"),
    ("豊田工業大学", "愛知県", "名古屋市", "", "https://www.toyota-ti.ac.jp/"),
    ("小樽商科大学", "北海道", "小樽市", "", "https://www.otaru-uc.ac.jp/"),
    ("室蘭工業大学", "北海道", "室蘭市", "", "https://muroran-it.ac.jp/"),
    ("北海学園大学", "北海道", "札幌市", "", "https://www.hgu.jp/"),
    ("東北学院大学", "宮城県", "仙台市", "", "https://www.tohoku-gakuin.ac.jp/"),
    ("国際教養大学", "秋田県", "秋田市", "", "https://web.aiu.ac.jp/"),
    ("会津大学", "福島県", "会津若松市", "", "https://u-aizu.ac.jp/"),
    ("茨城大学", "茨城県", "水戸市", "", "https://www.ibaraki.ac.jp/"),
    ("高崎経済大学", "群馬県", "高崎市", "", "https://www.tcue.ac.jp/"),
    ("電気通信大学", "東京都", "調布市", "", "https://www.uec.ac.jp/"),
    ("国際基督教大学", "東京都", "三鷹市", "", "https://www.icu.ac.jp/"),
    ("芝浦工業大学", "東京都", "江東区", "", "https://www.shibaura-it.ac.jp/"),
    ("東京理科大学", "東京都", "新宿区", "", "https://www.tus.ac.jp/"),
    ("津田塾大学", "東京都", "小平市", "", "https://www.tsuda.ac.jp/"),
    ("日本女子大学", "東京都", "文京区", "", "https://www.jwu.ac.jp/"),
    ("同志社女子大学", "京都府", "京田辺市", "", "https://www.dwc.doshisha.ac.jp/"),
    ("西南学院大学", "福岡県", "福岡市", "", "https://www.seinan-gu.ac.jp/"),
    ("福岡大学", "福岡県", "福岡市", "", "https://www.fukuoka-u.ac.jp/"),
]


BIG6_BASEBALL_CANDIDATES = [
    ("東京大学", "硬式野球部"),
    ("早稲田大学", "野球部"),
    ("慶應義塾大学", "野球部"),
    ("明治大学", "硬式野球部"),
    ("法政大学", "硬式野球部"),
    ("立教大学", "硬式野球部"),
]


def audit(conn, action, entity_type, entity_id, payload):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), now()),
    )


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inserted_universities = 0
    inserted_candidates = 0
    timestamp = now()

    for name, pref, city, campus, url in PHASE1_UNIVERSITIES:
        university_id = slug("u", name + "_" + campus)
        before = conn.execute(
            "select university_id from universities where university_name=? and campus_name=?",
            (name, campus),
        ).fetchone()
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
            (university_id, name, pref, city, campus, url, url, timestamp, timestamp),
        )
        saved = conn.execute(
            "select university_id from universities where university_name=? and campus_name=?",
            (name, campus),
        ).fetchone()["university_id"]
        conn.execute(
            """
            insert into collection_targets(university_id, collection_status, priority, source_search_query, source_url, notes, last_checked_at, updated_at)
            values(?,?,?,?,?,?,?,?)
            on conflict(university_id) do update set
              source_search_query=coalesce(collection_targets.source_search_query, excluded.source_search_query),
              updated_at=excluded.updated_at
            """,
            (saved, "not_started", 2, f"{name} 公認団体 サークル 一覧", "", "Phase 1主要大学として追加。公式サークル一覧の収集待ち", "", timestamp),
        )
        if not before:
            inserted_universities += 1

    source_url = "http://www.big6.gr.jp/"
    source_note = "東京六大学野球連盟で発見。大学公式ページとの突合前の候補として保存"
    for university_name, candidate_name in BIG6_BASEBALL_CANDIDATES:
        uni = conn.execute(
            "select university_id from universities where university_name=? order by campus_name limit 1",
            (university_name,),
        ).fetchone()
        if not uni:
            continue
        candidate_id = slug("cand", uni["university_id"] + "_" + candidate_name + "_" + source_url)
        before = conn.execute(
            "select candidate_id from circle_candidates where university_id=? and candidate_name=? and source_url=?",
            (uni["university_id"], candidate_name, source_url),
        ).fetchone()
        conn.execute(
            """
            insert into circle_candidates(candidate_id, university_id, candidate_name, sport_category, source_type, source_url,
              evidence_text, review_status, notes, created_at, updated_at)
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
                uni["university_id"],
                candidate_name,
                "野球",
                "other",
                source_url,
                source_note,
                "needs_check",
                "候補DB。正式公開前に大学公式または連盟個別ページで再確認",
                timestamp,
                timestamp,
            ),
        )
        if not before:
            inserted_candidates += 1

    audit(conn, "phase1_master_import", "university", None, {"inserted": inserted_universities})
    audit(conn, "candidate_import", "circle_candidate", None, {"inserted": inserted_candidates, "source_url": source_url})
    conn.commit()
    print(json.dumps({
        "inserted_universities": inserted_universities,
        "inserted_candidates": inserted_candidates,
        "total_universities": conn.execute("select count(*) from universities").fetchone()[0],
        "total_candidates": conn.execute("select count(*) from circle_candidates").fetchone()[0],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
