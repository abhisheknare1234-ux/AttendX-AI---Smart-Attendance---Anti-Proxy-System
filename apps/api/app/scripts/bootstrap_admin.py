"""Create the first administrator. Never hardcodes a credential.

Usage (from apps/api):
    python -m app.scripts.bootstrap_admin --email admin@institution.ac.in --name "Admin"
"""
from __future__ import annotations

import argparse
import getpass
import sys

from app.core.config import get_settings
from app.core.db import SessionLocal, create_all
from app.services.auth import bootstrap_admin


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap an AttendX administrator")
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument("--name", default="Institutional Administrator")
    parser.add_argument("--password", help="Password (prompted securely when omitted)")
    args = parser.parse_args()

    settings = get_settings()
    password = args.password
    if not password:
        password = getpass.getpass("Administrator password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            return 2

    if settings.app_env in {"development", "test"}:
        create_all()

    with SessionLocal() as db:
        try:
            user = bootstrap_admin(
                db,
                email=args.email,
                password=password,
                full_name=args.name,
            )
        except Exception as exc:  # noqa: BLE001 - CLI boundary
            print(f"Administrator bootstrap failed: {exc}", file=sys.stderr)
            return 1

    print(f"Administrator ready: {user.email} ({user.full_name})")
    print("Remove any BOOTSTRAP_ADMIN_PASSWORD from the environment after first sign-in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
