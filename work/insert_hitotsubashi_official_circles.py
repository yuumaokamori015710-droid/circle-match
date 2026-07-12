from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


DB = "outputs/circlematch.sqlite"
SOURCE_URL = "https://www.hit-u.ac.jp/shien/campuslife/group_activity.html"
TODAY = datetime.now(timezone.utc).date().isoformat()


SPORT_KEYWORDS = [
    ("野球", "野球"), ("サッカー", "サッカー"), ("蹴球", "サッカー"), ("Fut", "フットサル"),
    ("テニス", "テニス"), ("庭球", "テニス"), ("バスケット", "バスケットボール"), ("籠人", "バスケットボール"),
    ("バレー", "バレーボール"), ("バドミントン", "バドミントン"), ("ラグビー", "ラグビー"),
    ("ラクロス", "ラクロス"), ("剣道", "剣道"), ("柔道", "柔道"), ("弓道", "弓道"),
    ("空手", "空手"), ("少林寺拳法", "少林寺拳法"), ("水泳", "水泳"), ("陸上", "陸上競技"),
    ("ゴルフ", "ゴルフ"), ("スキー", "スキー"), ("山岳", "山岳"), ("ワンダーフォーゲル", "アウトドア"),
    ("ボート", "ボート"), ("端艇", "ボート"), ("ヨット", "ヨット"), ("ホッケー", "ホッケー"),
    ("ボクシング", "ボクシング"), ("フェンシング", "フェンシング"), ("ダンス", "ダンス"),
    ("乗馬", "乗馬"), ("フライングディスク", "アルティメット"), ("ハンドボール", "ハンドボール"),
    ("合気道", "武道"), ("洋弓", "アーチェリー"), ("体操", "体操"), ("競技ダンス", "ダンス"),
    ("音楽", "音楽"), ("合唱", "音楽"), ("管弦楽", "音楽"), ("吹奏楽", "音楽"), ("軽音", "音楽"),
    ("ギター", "音楽"), ("ジャズ", "音楽"), ("アカペラ", "音楽"), ("ピアノ", "音楽"),
    ("フォークソング", "音楽"), ("ボーカロイド", "音楽"), ("写真", "写真"), ("美術", "美術"),
    ("書道", "美術"), ("演劇", "演劇"), ("劇団", "演劇"), ("映画", "映画"), ("映創", "映画"),
    ("茶道", "茶道"), ("将棋", "将棋"), ("囲碁", "囲碁"), ("クイズ", "クイズ"),
    ("天文", "天文"), ("鉄道", "鉄道"), ("旅行", "旅行"), ("かるた", "競技かるた"),
    ("ボードゲーム", "ゲーム"), ("スマブラ", "ゲーム"), ("ポケモン", "ゲーム"),
    ("ボランティア", "ボランティア"), ("TFT", "ボランティア"), ("模擬国連", "模擬国連"),
    ("ESS", "英語"), ("留学生", "国際交流"), ("韓国", "国際交流"), ("中国", "国際交流"),
    ("法律", "法律"), ("法学", "法律"), ("経済", "経済"), ("投資", "投資"),
    ("広告", "広告"), ("新聞", "メディア"), ("放送", "メディア"), ("コンピュータ", "プログラミング"),
    ("DTM", "音楽"),
]


def sport_for(name: str) -> str:
    for keyword, sport in SPORT_KEYWORDS:
        if keyword in name:
            return sport
    return "その他"


def org_type_for(name: str) -> str:
    if "体育会" in name or ("部" in name and not any(x in name for x in ["同好会", "サークル", "クラブ"])):
        return "部活"
    if "同好会" in name:
        return "同好会"
    if "委員会" in name:
        return "学生団体"
    if "サークル" in name or "クラブ" in name:
        return "公認サークル"
    return "公認サークル"


GROUPS = [
    "一橋祭運営委員会", "一橋新聞部", "院生自治会", "学生会館管理運営委員会", "学生会館別館管理委員会",
    "学部協議会", "KODAIRA祭実行委員会", "新入生歓迎委員会", "卒業アルバム委員会", "卒業祝賀会実行委員会",
    "体育会総務委員会", "硬式庭球同好会連盟", "文化団体連合", "一橋植樹会（学生理事）", "小平キャンパス自治組織",
    "体育会合気道部", "体育会アイスホッケー部", "アメリカンフットボール部CRIMSON", "体育会應援部", "空手道部",
    "体育会弓道部", "ALL一橋競技ダンス部", "剣道部", "体育会硬式庭球部（男子）", "体育会硬式庭球部（女子）",
    "硬式野球部", "体育会ゴルフ部", "体育会サイクリング部", "ア式蹴球部〔サッカー部〕", "一橋山岳部",
    "柔道部", "準硬式野球部", "一橋大学・津田塾大学少林寺拳法部", "女子ラクロス部", "男子ラクロス部",
    "水泳部", "体育会スキー部", "ソフトテニス部（男子）", "ソフトテニス部（女子）", "一橋大学・津田塾大学体操部",
    "体育会卓球部", "バスケットボール部", "体育会バドミントン部", "男子バレーボール部", "女子バレーボール部",
    "体育会ハンドボール部", "フィールドホッケー部", "端艇部〔ボート部〕", "一橋津田塾大学体育会ボクシング部",
    "体育会洋弓部", "体育会ヨット部", "ラグビー部", "ラフティング部ストローム会", "体育会陸上競技部",
    "体育会ワンダーフォーゲル部", "フェンシング部", "Unplugged", "囲碁部", "映創会",
    "一橋大学津田塾大学合唱団ユマニテ", "管弦楽団", "一橋観世会", "一橋・津田塾・農工大ギター部",
    "クイズ研究会", "軽音楽部", "経済学研究会", "劇団コギト", "男声合唱団コール・メルクール",
    "国際部〔ESS〕", "表千家茶道部", "アカペラサークル The First Cry", "一橋大学津田塾大学写真部",
    "将棋部", "一橋大学津田塾大学吹奏楽団", "淡成書道会", "鉄道研究会", "天文部",
    "電子計算機研究会（DSK)", "坐禅部如意団", "一橋・津田塾大学美術部", "フォークソングクラブ",
    "Pro-K", "放送集団オケアノス", "法学研究会", "モダンジャズ研究会",
    "総合アミューズメント研究サークルLaBomba", "旅行研究会", "基督教青年会", "ゆびっこ",
    "インカレ音楽サークルBLITZ", "広告研究会HASC", "Magnetism of Sweden", "一橋創作同好会",
    "BRIDGE FOR TWO TFT一橋大学プロジェクト", "ピアノ室内楽サークルScherzando", "学生団体澁澤塾",
    "一橋硬式庭球同好会", "一橋ALWAYS", "Do!TennisTeam", "FOCUS", "一橋・津田塾ソフトボールサークル ピーナッツ",
    "一橋ヤンキース", "STAY GOLD", "サッカー同好会", "鷹の台レイカーズ", "籠人",
    "ITB Ikkyo Tsuda Badminton", "ストリートダンスサークル CHERISH", "フラサークル パパリナ", "JOINUS",
    "オリエンテーリングクラブ", "Glacier Ski Team", "一橋・津田塾山友会", "バレーボール同好会", "杖道部",
    "ふりかけ", "FC.POLSTER", "一橋ホークス", "C.T.C.", "世界プロレスリング同盟",
    "フライングディスクサークルUFO", "Swings", "コピーダンスサークル Spica", "一橋乗馬＆競馬サークル Pacara!",
    "キャップ投げ倶楽部", "ガールズスタイルダンスサークル セファランセラ", "HITers", "ハンドボールサークルshots",
    "PerSeas", "Fut-Bashi", "キャッチボールサークル Catch!", "如水エル", "HEPSA学生事務局",
    "模擬国連国立研究会", "学生団体GEIL", "チーム・えんのした", "一橋かるた会", "投資サークル TOWALY",
    "お笑いサークルIOK", "生協委員会MACO", "一橋ポケモンだいすきクラブ", "韓国人留学生会",
    "ディズニー同好会マウス", "法科大学院 法教育サークル", "国立あかるくらぶ", "まれひと（一橋パフォーマンスサークル）",
    "中国留学生学友会", "劇団WICK", "たまこまち", "TEDxHitotsubashiU", "ボードゲームサークルJuego",
    "一橋地歴同好会アインズ", "一橋推しアイドル同好会", "ひとつむぎ", "DJ/DTMサークルResonance",
    "一橋スマブラサークルばしスマ", "Bashi.com（コンピュータ研究会）", "韓国フェミニズムサークル mimosa",
    "ボーカロイド同好会", "一橋map運営チーム", "くにたち時事研究会", "盆踊りサークル昇舞",
]


def main() -> None:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    university_id = cur.execute(
        """
        select university_id
        from universities
        where university_name = ?
        order by case when university_id = 'u_hitotsubashi' then 0 else 1 end,
                 case when campus_name <> '' then 0 else 1 end,
                 university_id
        limit 1
        """,
        ("一橋大学",),
    ).fetchone()[0]
    inserted = 0
    for name in GROUPS:
        row = (
            f"c_u_一橋大学_{''.join(ch if ch.isalnum() else '_' for ch in name).strip('_')}",
            university_id,
            name,
            org_type_for(name),
            sport_for(name),
            "東京都",
            "university_official",
            SOURCE_URL,
            "university_verified",
            "published",
            TODAY,
            TODAY,
            TODAY,
        )
        before = cur.execute(
            "select circle_id from circles where university_id = ? and circle_name = ?",
            (university_id, name),
        ).fetchone()
        cur.execute(
            """
            insert into circles (
              circle_id, university_id, circle_name, organization_type, sport_category,
              activity_area, source_type, source_url, verification_status, public_status,
              last_checked_at, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(university_id, circle_name) do update set
              organization_type = excluded.organization_type,
              sport_category = excluded.sport_category,
              activity_area = excluded.activity_area,
              source_type = excluded.source_type,
              source_url = excluded.source_url,
              verification_status = excluded.verification_status,
              public_status = excluded.public_status,
              last_checked_at = excluded.last_checked_at,
              updated_at = excluded.updated_at
            """,
            row,
        )
        inserted += before is None
    con.commit()
    print({"inserted": inserted, "total": len(GROUPS)})


if __name__ == "__main__":
    main()
