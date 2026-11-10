"""Retention cleanup CLI. Dry-run by default; pass --apply to delete and audit."""
from __future__ import annotations

import argparse
import json

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.retention import cleanup


def main() -> int:
    parser = argparse.ArgumentParser(description="AttendX AI retention cleanup")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform deletion. Without this flag the command only reports counts.",
    )
    args = parser.parse_args()
    settings = get_settings()
    with SessionLocal() as db:
        counts = cleanup(db, settings=settings, apply=args.apply)
    print(json.dumps({"applied": bool(args.apply), "counts": counts}, indent=2))
    if not args.apply:
        print("Dry run only. Re-run with --apply to delete the listed rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
