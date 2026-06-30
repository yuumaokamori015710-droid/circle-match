import json
import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect("outputs/circlematch.sqlite")
target = "c_u_神戸大学_アメリカンフットボール部_ravens"
deleted = conn.execute("delete from circles where circle_id = ?", (target,)).rowcount
conn.execute("delete from data_sources where entity_id = ?", (target,))
conn.execute(
    "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
    (
        "dedupe",
        "circle",
        target,
        json.dumps({"reason": "神戸大学RAVENSの重複を公式リーグ情報の日本語表記へ統一"}, ensure_ascii=False),
        datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    ),
)
conn.commit()
print(json.dumps({"deleted": deleted, "total_circles": conn.execute("select count(*) from circles").fetchone()[0]}, ensure_ascii=False))
