import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"


NOISE_NAMES = [
    "本部学生支援センター",
]


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    timestamp = now()
    hidden = []
    for name in NOISE_NAMES:
        rows = list(conn.execute(
            "select circle_id, circle_name from circles where circle_name=? and public_status='published'",
            (name,),
        ))
        for row in rows:
            conn.execute(
                """
                update circles
                set public_status='rejected',
                    verification_status='unverified',
                    owner_notes=coalesce(owner_notes, '') || ' / サークル・部活ではなく窓口情報のため非公開化。',
                    updated_at=?
                where circle_id=?
                """,
                (timestamp, row["circle_id"]),
            )
            conn.execute(
                "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
                (
                    "screen_non_circle_noise_round7",
                    "circle",
                    row["circle_id"],
                    json.dumps({"circle_name": row["circle_name"], "reason": "not a circle"}, ensure_ascii=False),
                    timestamp,
                ),
            )
            hidden.append(dict(row))
    conn.commit()
    print(json.dumps({"hidden": hidden}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
