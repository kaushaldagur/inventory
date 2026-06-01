#!/usr/bin/env python3
"""Create an app login user (admin/CLI only — not exposed in the UI)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.user_service import UserAlreadyExistsError, create_user_account


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a yourinventory login user")
    parser.add_argument("--name", required=True, help="Full name")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Password (min 8 characters)")
    parser.add_argument(
        "--skip-if-exists",
        action="store_true",
        help="Exit 0 if the email is already registered (for deploy seeding)",
    )
    args = parser.parse_args()

    if len(args.password) < 8:
        print("Error: password must be at least 8 characters", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = create_user_account(db, full_name=args.name, email=args.email, password=args.password)
    except UserAlreadyExistsError as exc:
        if args.skip_if_exists:
            print(f"Skip: {exc}")
            return 0
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(f"Created user id={user.id} email={user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
