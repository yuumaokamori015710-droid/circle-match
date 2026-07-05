import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "outputs" / "circlematch_db_app.py"
SEED_PATH = ROOT / "outputs" / "public_circles_seed.csv"


def load_app():
    spec = importlib.util.spec_from_file_location("circlematch_db_app", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    app = load_app()
    with SEED_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)

    cleaned = []
    seen = set()
    removed = 0
    recategorized = 0
    for row in rows:
        name = (row.get("circle_name") or "").strip()
        university = (row.get("university_name") or "").strip()
        if app.is_invalid_circle_name(name):
            removed += 1
            continue
        new_sport = app.infer_sport_category(name, row.get("sport_category") or "その他")
        if new_sport != row.get("sport_category"):
            row["sport_category"] = new_sport
            recategorized += 1
        row["organization_type"] = row.get("organization_type") or app.infer_organization_type(name, row.get("source_type") or "other")
        key = (university, name)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        cleaned.append(row)

    cleaned.sort(key=lambda r: (r.get("prefecture", ""), r.get("university_name", ""), r.get("sport_category", ""), r.get("circle_name", "")))
    with SEED_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned)

    print(f"removed={removed} recategorized={recategorized} remaining={len(cleaned)}")


if __name__ == "__main__":
    main()
