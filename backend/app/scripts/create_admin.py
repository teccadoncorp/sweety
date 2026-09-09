"""Create or reset a board login. Run inside the API container."""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or reset a Sweety admin user")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", ""), help="Login email")
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", ""), help="Login password")
    return parser.parse_args(argv)


def upsert_admin(email: str, password: str) -> str:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise SystemExit("Email is required (--email or ADMIN_EMAIL)")
    if len(password) < 4:
        raise SystemExit("Password must be at least 4 characters (--password or ADMIN_PASSWORD)")

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, hashed_password=hash_password(password))
            db.add(user)
            db.commit()
            db.refresh(user)
            return f"created admin {email} ({user.id})"
        user.hashed_password = hash_password(password)
        db.commit()
        return f"updated password for {email} ({user.id})"
    finally:
        db.close()


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    print(upsert_admin(args.email, args.password), file=sys.stdout)


if __name__ == "__main__":
    main()
