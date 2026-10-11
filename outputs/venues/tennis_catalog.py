"""Public, curated Tokyo tennis directory. No user data or live booking access."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

CATALOG_PATH = Path(__file__).resolve().parent / "catalogs" / "tokyo_tennis.json"
WARDS = frozenset(("千代田 中央 港 新宿 文京 台東 墨田 江東 品川 目黒 大田 世田谷 渋谷 中野 杉並 豊島 北 荒川 板橋 練馬 足立 葛飾 江戸川".split()))
CITIES = frozenset("八王子 立川 武蔵野 三鷹 青梅 府中 昭島 調布 町田 小金井 小平 日野 東村山 国分寺 国立 福生 狛江 東大和 清瀬 東久留米 武蔵村山 多摩 稲城 羽村 あきる野 西東京".split())
TAMA_TOWNS = frozenset(("瑞穂町", "日の出町", "檜原村", "奥多摩町"))
ISLANDS = frozenset(("大島町", "利島村", "新島村", "神津島村", "三宅村", "御蔵島村", "八丈町", "青ヶ島村", "小笠原村"))
MUNICIPALITIES = frozenset({w + "区" for w in WARDS} | {c + "市" for c in CITIES} | TAMA_TOWNS | ISLANDS)


def _url(value: str) -> bool:
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        return False
    try:
        parsed = urlsplit(value)
        return bool(parsed.scheme in {"https", "http"} and parsed.hostname and not parsed.username
                    and not parsed.password and not re.search(r"(?:sessionid|session_id|token)=", value, re.I))
    except ValueError:
        return False


def hourly_price(price, unit: str):
    """Normalize only explicit per-court hour units, never per-person/day rates."""
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price < 0:
        return None
    if price == 0 and unit == "無料（コート利用）":
        return 0
    match = re.fullmatch(r"1面(\d+(?:\.\d+)?)(時間|分)(?:（[^（）]*）|\([^()]*\))?", unit)
    if not match or float(match[1]) <= 0:
        return None
    normalized = round(price / float(match[1]) * (60 if match[2] == "分" else 1), 2)
    return int(normalized) if normalized.is_integer() else normalized


def validate_catalog(rows: list) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("Catalog must contain facilities")
    ids = set()
    facilities = set()
    result = []
    strings = ("name", "operator", "municipality", "area", "address", "price_unit", "price_note", "booking_method", "booking_note", "booking_url", "official_url", "checked_at")
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("Invalid facility")
        row = dict(raw)
        if not isinstance(row.get("id"), str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", row["id"]) or row["id"] in ids:
            raise ValueError("Invalid or duplicate facility id")
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in strings):
            raise ValueError(f"Missing facility fields: {row['id']}")
        if row.get("operator_type") not in {"PUBLIC", "PRIVATE"} or row["municipality"] not in MUNICIPALITIES:
            raise ValueError(f"Invalid Tokyo facility: {row['id']}")
        if row.get("facility_kind", "COURT") not in {"COURT", "SCHOOL"}:
            raise ValueError(f"Invalid facility kind: {row['id']}")
        expected_area = "島しょ" if row["municipality"] in ISLANDS else "23区" if row["municipality"].endswith("区") else "多摩"
        if row["area"] != expected_area or not row["address"].startswith("東京都"):
            raise ValueError(f"Invalid facility location: {row['id']}")
        pair = (row["name"].replace(" ", "").replace("　", ""), row["address"].replace(" ", "").replace("　", ""))
        if pair in facilities:
            raise ValueError(f"Duplicate facility: {row['id']}")
        for key in ("indoor", "night_lighting"):
            if row.get(key) is not None and type(row[key]) is not bool:
                raise ValueError(f"Invalid {key}: {row['id']}")
        count = row.get("courts_count")
        if count is not None and (type(count) is not int or count <= 0):
            raise ValueError(f"Invalid court count: {row['id']}")
        price = row.get("price_from")
        if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price < 0):
            raise ValueError(f"Invalid price: {row['id']}")
        date.fromisoformat(row["checked_at"])
        sources = row.get("sources")
        if not isinstance(sources, list) or not sources or any(not isinstance(s, dict) or not isinstance(s.get("title"), str) or not s["title"].strip() or not _url(s.get("url")) for s in sources):
            raise ValueError(f"Missing official sources: {row['id']}")
        if not _url(row["official_url"]) or not _url(row["booking_url"]):
            raise ValueError(f"Invalid public URL: {row['id']}")
        if row.get("availability_status") not in {None, "OPEN", "SUSPENDED", "UNKNOWN"}:
            raise ValueError(f"Invalid operating status: {row['id']}")
        if row.get("availability_status") == "SUSPENDED" and not row.get("availability_note"):
            raise ValueError(f"Missing suspension note: {row['id']}")
        # Whitelist fields: this public endpoint must never acquire credentials or private notes.
        public = {key: row.get(key) for key in ("id", *strings, "operator_type", "courts_count", "surface", "indoor", "night_lighting", "price_from")}
        public["sources"] = [{"title": s["title"], "url": s["url"]} for s in sources]
        public["availability_status"] = row.get("availability_status", "UNKNOWN")
        public["facility_kind"] = row.get("facility_kind", "COURT")
        public["availability_note"] = row.get("availability_note", "")
        public["price_per_hour"] = hourly_price(price, row["price_unit"])
        result.append(public)
        ids.add(row["id"])
        facilities.add(pair)
    return result


@lru_cache(maxsize=1)
def _load(path: str, modified_ns: int) -> dict:
    rows = validate_catalog(json.loads(Path(path).read_text(encoding="utf-8-sig")))
    municipalities = sorted({row["municipality"] for row in rows})
    return {"courts": rows, "meta": {
        "checked_at": max(row["checked_at"] for row in rows),
        "total": len(rows), "municipalities": municipalities,
        "municipalities_total": 62,
        "areas": dict(Counter(row["area"] for row in rows)),
        "operators": dict(Counter(row["operator_type"] for row in rows)),
        "prices_confirmed": sum(row["price_from"] is not None for row in rows),
        "coverage_note": "公式情報を確認した施設を掲載しています。都内全施設の掲載は順次拡充中です。空き状況は各施設の公式予約先で確認してください。",
    }}


def get_catalog(path: Path = CATALOG_PATH) -> dict:
    return _load(str(path), path.stat().st_mtime_ns)
