from __future__ import annotations

import sqlite3


DB = "outputs/circlematch.sqlite"
CANONICAL_ID = "u_hitotsubashi"
DUPLICATE_ID = "u_一橋大学"


def main() -> None:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    canonical = cur.execute(
        "select university_id from universities where university_id = ?",
        (CANONICAL_ID,),
    ).fetchone()
    duplicate = cur.execute(
        "select university_id from universities where university_id = ?",
        (DUPLICATE_ID,),
    ).fetchone()
    if not canonical:
        raise SystemExit(f"missing canonical university: {CANONICAL_ID}")
    moved = 0
    if duplicate:
        # Avoid unique collisions if the canonical row already has the same circle name.
        duplicate_circles = cur.execute(
            "select circle_id, circle_name from circles where university_id = ?",
            (DUPLICATE_ID,),
        ).fetchall()
        for circle_id, circle_name in duplicate_circles:
            exists = cur.execute(
                "select circle_id from circles where university_id = ? and circle_name = ?",
                (CANONICAL_ID, circle_name),
            ).fetchone()
            if exists:
                cur.execute("delete from data_sources where entity_type='circle' and entity_id=?", (circle_id,))
                cur.execute("delete from circle_private_profiles where circle_id=?", (circle_id,))
                cur.execute("delete from circle_claims where circle_id=?", (circle_id,))
                cur.execute("delete from match_posts where circle_id=?", (circle_id,))
                cur.execute("delete from circles where circle_id=?", (circle_id,))
            else:
                cur.execute(
                    "update circles set university_id = ?, updated_at = date('now') where circle_id = ?",
                    (CANONICAL_ID, circle_id),
                )
                moved += 1
        cur.execute("delete from collection_targets where university_id = ?", (DUPLICATE_ID,))
        cur.execute("delete from universities where university_id = ?", (DUPLICATE_ID,))
    con.commit()
    count = cur.execute(
        """
        select count(*)
        from circles
        where university_id = ?
          and public_status = 'published'
        """,
        (CANONICAL_ID,),
    ).fetchone()[0]
    print({"moved": moved, "published": count})


if __name__ == "__main__":
    main()
