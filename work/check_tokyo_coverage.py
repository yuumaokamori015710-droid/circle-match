from __future__ import annotations

import sqlite3


con = sqlite3.connect("outputs/circlematch.sqlite")
cur = con.cursor()

zero_rows = cur.execute(
    """
    select u.university_name
    from universities u
    left join circles c
      on c.university_id = u.university_id
     and c.public_status = 'published'
    where u.prefecture = '東京都'
    group by u.university_id
    having count(c.circle_id) = 0
    order by u.university_name
    """
).fetchall()
print("Tokyo zero-count:")
print("\n".join(row[0] for row in zero_rows) or "なし")

for university in ["日本大学", "杏林大学", "東京工科大学", "東京家政大学"]:
    count = cur.execute(
        """
        select count(*)
        from circles c
        join universities u on u.university_id = c.university_id
        where u.university_name = ?
          and c.public_status = 'published'
        """,
        (university,),
    ).fetchone()[0]
    print(f"{university}: {count}")
