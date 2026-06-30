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


UNIVERSITIES = [
    ("桃山学院大学", "大阪府", "和泉市", "https://www.andrew.ac.jp/"),
    ("神戸学院大学", "兵庫県", "神戸市", "https://www.kobegakuin.ac.jp/"),
    ("大阪教育大学", "大阪府", "柏原市", "https://osaka-kyoiku.ac.jp/"),
    ("名城大学", "愛知県", "名古屋市", "https://www.meijo-u.ac.jp/"),
    ("四日市大学", "三重県", "四日市市", "https://www.yokkaichi-u.ac.jp/"),
    ("日本福祉大学", "愛知県", "知多郡美浜町", "https://www.n-fukushi.ac.jp/"),
    ("東北工業大学", "宮城県", "仙台市", "https://www.tohtech.ac.jp/"),
    ("北里大学", "東京都", "港区", "https://www.kitasato-u.ac.jp/"),
    ("仙台大学", "宮城県", "柴田郡柴田町", "https://www.sendaidaigaku.jp/"),
    ("国士舘大学", "東京都", "世田谷区", "https://www.kokushikan.ac.jp/"),
    ("順天堂大学", "千葉県", "印西市", "https://www.juntendo.ac.jp/"),
    ("日本体育大学", "東京都", "世田谷区", "https://www.nittai.ac.jp/"),
    ("大阪体育大学", "大阪府", "泉南郡熊取町", "https://www.ouhs.jp/"),
    ("流通経済大学", "茨城県", "龍ケ崎市", "https://www.rku.ac.jp/"),
    ("桐蔭横浜大学", "神奈川県", "横浜市", "https://toin.ac.jp/univ/"),
    ("阪南大学", "大阪府", "松原市", "https://www.hannan-u.ac.jp/"),
    ("新潟医療福祉大学", "新潟県", "新潟市", "https://www.nuhw.ac.jp/"),
    ("大阪商業大学", "大阪府", "東大阪市", "https://ouc.daishodai.ac.jp/"),
]


CANDIDATE_BATCHES = [
    {
        "source_url": "https://www.kansai-football.jp/division/",
        "source_type": "other",
        "evidence_text": "関西学生アメリカンフットボールリーグの公開リーグ情報から候補化。正式昇格前に大学公式またはチーム公式も確認",
        "sport_category": "アメリカンフットボール",
        "items": [
            ("立命館大学", "アメリカンフットボール部 パンサーズ"),
            ("近畿大学", "アメリカンフットボール部 ビッグブルー"),
            ("桃山学院大学", "アメリカンフットボール部 サンダーリングリージョンライオンズ"),
            ("関西学院大学", "アメリカンフットボール部 ファイターズ"),
            ("関西大学", "アメリカンフットボール部 カイザーズ"),
            ("同志社大学", "アメリカンフットボール部 ワイルドローバー"),
            ("龍谷大学", "アメリカンフットボール部 シーホース"),
            ("神戸学院大学", "アメリカンフットボール部 ネイビーシールズ"),
            ("大阪教育大学", "アメリカンフットボール部 ドラゴンズ"),
            ("兵庫県立大学", "アメリカンフットボール部 トレイルブレイザーズ"),
        ],
    },
    {
        "source_url": "http://www.tkcafa.jp/",
        "source_type": "other",
        "evidence_text": "東海学生アメリカンフットボール連盟の公開情報を起点に候補化。公式ページ確認待ち",
        "sport_category": "アメリカンフットボール",
        "items": [
            ("名城大学", "アメリカンフットボール部 ゴールデンライオンズ"),
            ("名古屋大学", "アメリカンフットボール部 グランパス"),
            ("中京大学", "アメリカンフットボール部 イーグルス"),
            ("名古屋工業大学", "アメリカンフットボール部 シルバーバックス"),
            ("四日市大学", "アメリカンフットボール部 ワイルドドランカーズ"),
            ("岐阜大学", "アメリカンフットボール部 ファントムズ"),
            ("日本福祉大学", "アメリカンフットボール部 ウィングス"),
            ("静岡大学", "アメリカンフットボール部 キャバリアーズ"),
            ("東海大学", "アメリカンフットボール部 ポセイドンズ"),
        ],
    },
    {
        "source_url": "https://www.tcaa.jp/",
        "source_type": "other",
        "evidence_text": "東北学生アメリカンフットボール連盟の公開情報を起点に候補化。公式ページ確認待ち",
        "sport_category": "アメリカンフットボール",
        "items": [
            ("東北学院大学", "アメリカンフットボール部 カヤックス"),
            ("仙台大学", "アメリカンフットボール部 シルバーファルコンズ"),
            ("東北大学", "アメリカンフットボール部 ホーネッツ"),
            ("岩手大学", "アメリカンフットボール部 バイソンズ"),
            ("秋田大学", "アメリカンフットボール部"),
            ("弘前大学", "アメリカンフットボール部 スターキング"),
            ("山形大学", "アメリカンフットボール部 トムキャッツ"),
            ("東北工業大学", "アメリカンフットボール部 ブルーレイダース"),
            ("日本大学", "アメリカンフットボール部"),
            ("北里大学", "アメリカンフットボール部 カウボーイズ"),
        ],
    },
    {
        "source_url": "https://www.jufa.jp/",
        "source_type": "other",
        "evidence_text": "全日本大学サッカー大会・大学サッカー公開情報を起点に候補化。大学公式/連盟個別ページ確認待ち",
        "sport_category": "サッカー",
        "items": [
            ("早稲田大学", "ア式蹴球部"),
            ("慶應義塾大学", "ソッカー部"),
            ("明治大学", "体育会サッカー部"),
            ("中央大学", "学友会サッカー部"),
            ("法政大学", "体育会サッカー部"),
            ("立教大学", "体育会サッカー部"),
            ("日本大学", "サッカー部"),
            ("筑波大学", "蹴球部"),
            ("駒澤大学", "サッカー部"),
            ("関西大学", "体育会サッカー部"),
            ("関西学院大学", "体育会サッカー部"),
            ("同志社大学", "体育会サッカー部"),
            ("立命館大学", "体育会サッカー部"),
            ("京都産業大学", "体育会サッカー部"),
            ("東洋大学", "体育会サッカー部"),
            ("新潟医療福祉大学", "サッカー部"),
        ],
    },
]


def audit(conn, action, entity_type, entity_id, payload):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), now()),
    )


def upsert_university(conn, name, pref, city, url):
    timestamp = now()
    university_id = slug("u", name)
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
        (university_id, name, pref, city, "", url, url, timestamp, timestamp),
    )
    saved = conn.execute(
        "select university_id from universities where university_name=? order by campus_name limit 1",
        (name,),
    ).fetchone()["university_id"]
    conn.execute(
        """
        insert into collection_targets(university_id, collection_status, priority, source_search_query, source_url, notes, last_checked_at, updated_at)
        values(?,?,?,?,?,?,?,?)
        on conflict(university_id) do update set updated_at=excluded.updated_at
        """,
        (saved, "not_started", 2, f"{name} 公認団体 サークル 一覧", "", "競技候補収集のため追加。公式団体一覧は確認待ち", "", timestamp),
    )
    return saved


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inserted_universities = 0
    inserted_candidates = 0
    for name, pref, city, url in UNIVERSITIES:
        exists = conn.execute("select 1 from universities where university_name=?", (name,)).fetchone()
        upsert_university(conn, name, pref, city, url)
        if not exists:
            inserted_universities += 1

    for batch in CANDIDATE_BATCHES:
        for university_name, candidate_name in batch["items"]:
            uni = conn.execute(
                "select university_id from universities where university_name=? order by campus_name limit 1",
                (university_name,),
            ).fetchone()
            if not uni:
                continue
            candidate_id = slug("cand", uni["university_id"] + "_" + candidate_name + "_" + batch["source_url"])
            before = conn.execute(
                "select candidate_id from circle_candidates where university_id=? and candidate_name=? and source_url=?",
                (uni["university_id"], candidate_name, batch["source_url"]),
            ).fetchone()
            timestamp = now()
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
                    batch["sport_category"],
                    batch["source_type"],
                    batch["source_url"],
                    batch["evidence_text"],
                    "needs_check",
                    "候補DB。正式公開前に大学公式・連盟個別ページ・団体公式SNSのいずれかで再確認",
                    timestamp,
                    timestamp,
                ),
            )
            if not before:
                inserted_candidates += 1

    audit(conn, "candidate_batch_import", "circle_candidate", None, {
        "inserted_universities": inserted_universities,
        "inserted_candidates": inserted_candidates,
    })
    conn.commit()
    print(json.dumps({
        "inserted_universities": inserted_universities,
        "inserted_candidates": inserted_candidates,
        "total_universities": conn.execute("select count(*) from universities").fetchone()[0],
        "total_candidates": conn.execute("select count(*) from circle_candidates").fetchone()[0],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
