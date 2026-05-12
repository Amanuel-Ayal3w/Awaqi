"""
Seed a new superadmin user into the Awaqi database.

Usage (from repo root):
    uv run python scripts/seed_superadmin.py

Prompts for email, name, and password interactively.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from getpass import getpass

# Allow running from repo root without installing the package
sys.path.insert(0, "packages/database/src")

from dotenv import load_dotenv

load_dotenv()

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


# ---------------------------------------------------------------------------
# DB setup (mirrors packages/database/src/database/db.py but standalone)
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ["DATABASE_URL"]
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    """Return a bcrypt hash compatible with Better Auth's credential provider."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=10)).decode()


async def seed(email: str, name: str, password: str) -> None:
    now = datetime.now(timezone.utc)
    user_id = uuid.uuid4()
    account_id = str(uuid.uuid4())

    async with SessionLocal() as session:
        # ------------------------------------------------------------------
        # 1. Insert into ba_user
        # ------------------------------------------------------------------
        await session.execute(
            text("""
                INSERT INTO ba_user
                    (id, name, email, "emailVerified", role, is_active, "createdAt", "updatedAt")
                VALUES
                    (:id, :name, :email, true, 'superadmin', true, :now, :now)
                ON CONFLICT (email) DO UPDATE
                    SET name       = EXCLUDED.name,
                        role       = 'superadmin',
                        is_active  = true,
                        "updatedAt" = EXCLUDED."updatedAt"
                RETURNING id
            """),
            {"id": user_id, "name": name, "email": email, "now": now},
        )

        # Fetch the actual user_id (in case ON CONFLICT fired and we got the existing one)
        row = await session.execute(
            text('SELECT id FROM ba_user WHERE email = :email'), {"email": email}
        )
        real_user_id = row.scalar_one()

        # ------------------------------------------------------------------
        # 2. Insert into ba_account (credential provider)
        # ------------------------------------------------------------------
        pw_hash = hash_password(password)
        # Delete any existing credential account for this user first (upsert-safe)
        await session.execute(
            text('DELETE FROM ba_account WHERE "userId" = :user_id AND "providerId" = \'credential\''),
            {"user_id": real_user_id},
        )
        await session.execute(
            text("""
                INSERT INTO ba_account
                    (id, "accountId", "providerId", "userId", password, "createdAt", "updatedAt")
                VALUES
                    (:id, :account_id, 'credential', :user_id, :pw_hash, :now, :now)
            """),
            {
                "id": account_id,
                "account_id": str(real_user_id),
                "user_id": real_user_id,
                "pw_hash": pw_hash,
                "now": now,
            },
        )

        await session.commit()

    print(f"\n✅  Superadmin seeded successfully!")
    print(f"   Email : {email}")
    print(f"   Name  : {name}")
    print(f"   Role  : superadmin")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    print("=== Awaqi — Seed Superadmin ===\n")
    email = input("Email: ").strip()
    if not email:
        print("❌  Email cannot be empty.")
        sys.exit(1)

    name = input("Name (display): ").strip() or "Super Admin"

    password = getpass("Password: ")
    if len(password) < 8:
        print("❌  Password must be at least 8 characters.")
        sys.exit(1)

    confirm = getpass("Confirm password: ")
    if password != confirm:
        print("❌  Passwords do not match.")
        sys.exit(1)

    asyncio.run(seed(email, name, password))


if __name__ == "__main__":
    main()
