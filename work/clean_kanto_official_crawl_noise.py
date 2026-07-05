import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "circlematch.sqlite"

BAD_PATTERNS = [
    r"\d{4}",
    r"[0-9０-９]+月",
    r"[0-9０-９]+日",
    r"令和",
    r"年度",
    r"STUDENTS",
    r"お知らせ",
    r"募集",
    r"大会",
    r"選手",
    r"実施",
    r"開催",
    r"支給",
    r"申請",
    r"参考",
    r"資料",
    r"案内",
    r"昇格",
    r"金メダル",
    r"講習会",
    r"活躍",
    r"受賞",
    r"手続",
    r"責任者",
    r"届出",
    r"掲示板",
    r"保険",
    r"加入",
    r"部室",
    r"部長",
    r"監督",
    r"部員",
    r"必要書類",
    r"書類",
    r"紹介$",
    r"一覧$",
    r"団体一覧$",
    r"団体名簿",
    r"所属団体$",
    r"様式",
    r"@",
    r"運動系 団体$",
    r"文化系 団体$",
    r"本学のサークル",
    r"サークルの取りまとめ",
    r"オナーズ部門",
    r"写真部門",
    r"社会調査士",
    r"任意団体$",
    r"サークル活動$",
    r"クラブ・サークル活動$",
    r"課外活動",
    r"クラブガイド",
    r"出展",
    r"出店",
    r"ステージ",
    r"更新しました",
    r"企業",
    r"連携",
    r"キャリアナビ",
    r"外部リンク",
    r"短大の",
    r"結果",
    r"制度$",
    r"HP$",
    r"YouTube",
    r"会長メッセージ",
    r"支部",
    r"補助金",
    r"事務局",
    r"学友会$",
    r"執行部$",
    r"クラブ活動時",
    r"各部紹介$",
]
GOOD_MARKERS = ["部", "サークル", "クラブ", "同好会", "愛好会", "研究会", "研修会", "委員会", "準備会", "団", "隊", "局"]


def is_noise(name, source_url):
    if any(re.search(pattern, name, re.I) for pattern in BAD_PATTERNS):
        return True
    if not any(marker in name for marker in GOOD_MARKERS) and not name.endswith("会"):
        return True
    if name in {"クラブ・サークル", "クラブ・サークル活動", "体育会", "文化会", "団体"}:
        return True
    if source_url.endswith("/campuslife/") or "/journal/" in source_url or "/report" in source_url:
        return True
    return False


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        select c.circle_id, c.circle_name, c.source_url, u.university_name
        from circles c
        join audit_logs a on a.entity_id = c.circle_id and a.action = 'kanto_official_crawl_import'
        join universities u on u.university_id = c.university_id
        """
    ).fetchall()
    targets = [r for r in rows if is_noise(r["circle_name"], r["source_url"] or "")]
    ids = [r["circle_id"] for r in targets]
    if ids:
        marks = ",".join("?" * len(ids))
        conn.execute(f"delete from data_sources where entity_type='circle' and entity_id in ({marks})", ids)
        conn.execute(f"delete from circles where circle_id in ({marks})", ids)
        conn.execute(f"delete from audit_logs where action='kanto_official_crawl_import' and entity_id in ({marks})", ids)
    conn.commit()
    print(json.dumps({
        "reviewed": len(rows),
        "deleted": len(ids),
        "samples": [
            {"university": r["university_name"], "circle_name": r["circle_name"], "source_url": r["source_url"]}
            for r in targets[:40]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
