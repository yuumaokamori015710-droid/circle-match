"""Read-only connection checks: never opens/migrates SQLite or creates Stripe objects."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outputs"))
from circlematch_payments import Payments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stripe", action="store_true", help="Also retrieve the Stripe platform account (read-only)")
    args = parser.parse_args()
    result = Payments(None, None).connection_status(check_stripe=args.stripe)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(check["ok"] for check in result["checks"]) and (not args.stripe or result["stripe_checked"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
