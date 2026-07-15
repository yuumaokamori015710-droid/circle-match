import csv
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "circlematch.sqlite"
OUT_PATH = ROOT / "outputs" / "public_circles_seed.csv"


PUBLIC_COLUMNS = [
    "university_name",
    "prefecture",
    "city",
    "campus_name",
    "official_url",
    "circle_name",
    "organization_type",
    "sport_category",
    "activity_area",
    "source_type",
    "source_url",
    "verification_status",
    "public_status",
    "last_checked_at",
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        select
          u.university_name,
          u.prefecture,
          coalesce(u.city, '') as city,
          coalesce(u.campus_name, '') as campus_name,
          coalesce(u.official_url, '') as official_url,
          c.circle_name,
          c.organization_type,
          c.sport_category,
          coalesce(c.activity_area, '') as activity_area,
          c.source_type,
          coalesce(c.source_url, '') as source_url,
          c.verification_status,
          c.public_status,
          coalesce(c.last_checked_at, '') as last_checked_at
        from circles c
        join universities u on u.university_id = c.university_id
        where c.public_status = 'published'
          and c.verification_status in ('university_verified', 'admin_verified')
        order by u.prefecture, u.university_name, c.circle_name
        """
    ).fetchall()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PUBLIC_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in PUBLIC_COLUMNS})
    print(f"exported {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
