import fnmatch
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BLOCKED_PATTERNS = [
    ".env",
    ".env.*",
    "*.sqlite",
    "*.sqlite3",
    "*.db",
    "*.log",
    "*.pem",
    "*.key",
    "token.json",
    "work/*.pdf",
    "outputs/circlematch.sqlite",
]

SENSITIVE_TEXT_PATTERNS = [
    "OPENAI_API_KEY",
    "DATABASE_URL=",
    "PRIVATE KEY",
    "BEGIN RSA",
    "sk-",
    "xoxb-",
]

FORBIDDEN_PUBLIC_SEED_COLUMNS = {
    "claimant_name",
    "claimant_email",
    "owner_notes",
    "internal_notes",
    "sns_url",
    "public_sns_url",
    "phone",
    "line_id",
}


def is_blocked(path):
    rel = path.as_posix()
    if rel == ".env.example":
        return False
    return any(fnmatch.fnmatch(rel, pattern) for pattern in BLOCKED_PATTERNS)


def main():
    blocked_files = []
    suspicious_text = []
    public_seed_errors = []
    for current_root, dirnames, filenames in os.walk(ROOT):
        rel_root = Path(current_root).relative_to(ROOT)
        dirnames[:] = [
            name for name in dirnames
            if name not in {".git", ".codex", ".agents", "__pycache__", "node_modules"}
        ]
        for filename in filenames:
            path = rel_root / filename
            full_path = ROOT / path
            if is_blocked(path):
                blocked_files.append(path.as_posix())
                continue
            if path.as_posix() == "outputs/public_circles_seed.csv":
                header = full_path.read_text(encoding="utf-8").splitlines()[0].split(",")
                forbidden = sorted(FORBIDDEN_PUBLIC_SEED_COLUMNS.intersection(header))
                if forbidden:
                    public_seed_errors.append(f"{path.as_posix()}: forbidden columns {', '.join(forbidden)}")
            if full_path.suffix.lower() in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".sqlite"}:
                continue
            try:
                text = full_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in SENSITIVE_TEXT_PATTERNS:
                if pattern in text and path.as_posix() not in {".env.example", "README.md", "scripts/check_publish_safety.py"}:
                    suspicious_text.append(f"{path.as_posix()}: contains {pattern}")

    if blocked_files:
        print("Files matching non-publish patterns exist locally:")
        for item in blocked_files:
            print(f"  - {item}")
        print("These are OK locally only if .gitignore excludes them.")

    if suspicious_text:
        print("Suspicious text found:")
        for item in suspicious_text:
            print(f"  - {item}")
        raise SystemExit(1)

    if public_seed_errors:
        print("Public seed errors found:")
        for item in public_seed_errors:
            print(f"  - {item}")
        raise SystemExit(1)

    print("Publish safety text scan passed.")


if __name__ == "__main__":
    main()
