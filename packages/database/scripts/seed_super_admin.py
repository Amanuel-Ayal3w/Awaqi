"""Seed or update the default super admin in Better Auth tables.

Usage (from packages/database):
    uv run python scripts/seed_super_admin.py

This script writes to:
  - ba_user
  - ba_account
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timezone
from secrets import token_hex
from unicodedata import normalize

from database.db import AsyncSessionLocal
from sqlalchemy import text

ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "12345678"
ADMIN_NAME = "Super Admin"
PASSWORD_PROVIDER_ID = "credential"

DEBUG_LOG_PATH = "/home/debbie/Awaqi/.cursor/debug-b8df3a.log"


def _debug_log(message: str, *, hypothesis_id: str, data: dict | None = None) -> None:
    # Avoid logging secrets/PII: do not include emails/passwords/tokens/hashes.
    payload = {
        "sessionId": "b8df3a",
        "runId": "seed_super_admin",
        "hypothesisId": hypothesis_id,
        "location": "packages/database/scripts/seed_super_admin.py",
        "message": message,
        "data": data or {},
        "timestamp": int(datetime.now(tz=timezone.utc).timestamp() * 1000),
    }
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{payload}\n")
    except Exception:
        # Debug logging must never break seeding
        pass


def _better_auth_scrypt_hash(password: str) -> str:
    """
    Match Better Auth v1.4.x hashing format:
      hash = f"{salt_hex}:{key_hex}"
    where salt_hex is hex-encoded 16 random bytes (32 chars) and key is scrypt-derived.
    """
    pw = normalize("NFKC", password)
    salt_hex = token_hex(16)  # 16 random bytes -> 32 hex chars
    key = hashlib.scrypt(
        pw.encode("utf-8"),
        salt=salt_hex.encode("utf-8"),
        n=16384,
        r=16,
        p=1,
        dklen=64,
        maxmem=128 * 16384 * 16 * 2,
    )
    hash_value = f"{salt_hex}:{key.hex()}"
    _debug_log(
        "Generated BetterAuth scrypt hash metadata",
        hypothesis_id="H1",
        data={
            "hash_has_colon": ":" in hash_value,
            "salt_len": len(salt_hex),
            "key_hex_len": len(key.hex()),
        },
    )
    return hash_value


async def seed_super_admin() -> None:
    # Better Auth uses scrypt (salt:hexKey), not bcrypt.
    password_hash = _better_auth_scrypt_hash(ADMIN_PASSWORD)
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        try:
            user_result = await session.execute(
                text('SELECT id FROM ba_user WHERE email = :email LIMIT 1'),
                {"email": ADMIN_EMAIL},
            )
            user_id = user_result.scalar_one_or_none()

            if user_id is None:
                user_id = uuid.uuid4()
                await session.execute(
                    text(
                        'INSERT INTO ba_user (id, name, email, "emailVerified", role, is_active, "createdAt", "updatedAt") '
                        'VALUES (:id, :name, :email, :email_verified, :role, :is_active, :created_at, :updated_at)'
                    ),
                    {
                        "id": user_id,
                        "name": ADMIN_NAME,
                        "email": ADMIN_EMAIL,
                        "email_verified": True,
                        "role": "superadmin",
                        "is_active": True,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                print(f"Created ba_user for {ADMIN_EMAIL}")
            else:
                await session.execute(
                    text(
                        'UPDATE ba_user SET name = :name, "emailVerified" = :email_verified, role = :role, '
                        'is_active = :is_active, "updatedAt" = :updated_at WHERE id = :id'
                    ),
                    {
                        "id": user_id,
                        "name": ADMIN_NAME,
                        "email_verified": True,
                        "role": "superadmin",
                        "is_active": True,
                        "updated_at": now,
                    },
                )
                print(f"Updated ba_user for {ADMIN_EMAIL}")

            account_result = await session.execute(
                text(
                    'SELECT id FROM ba_account WHERE "userId" = :user_id AND "providerId" = :provider_id LIMIT 1'
                ),
                {
                    "user_id": user_id,
                    "provider_id": PASSWORD_PROVIDER_ID,
                },
            )
            account_id = account_result.scalar_one_or_none()

            if account_id is None:
                account_id = str(uuid.uuid4())
                await session.execute(
                    text(
                        'INSERT INTO ba_account (id, "userId", "accountId", "providerId", password, "createdAt", "updatedAt") '
                        'VALUES (:id, :user_id, :account_id, :provider_id, :password, :created_at, :updated_at)'
                    ),
                    {
                        "id": account_id,
                        "user_id": user_id,
                        "account_id": ADMIN_EMAIL,
                        "provider_id": PASSWORD_PROVIDER_ID,
                        "password": password_hash,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                print(f"Created ba_account credentials for {ADMIN_EMAIL}")
            else:
                # Remove duplicates for this accountId/providerId to avoid stale hashes.
                await session.execute(
                    text(
                        'DELETE FROM ba_account WHERE "accountId" = :account_id AND "providerId" = :provider_id AND id <> :id'
                    ),
                    {"account_id": ADMIN_EMAIL, "provider_id": PASSWORD_PROVIDER_ID, "id": account_id},
                )
                await session.execute(
                    text(
                        'UPDATE ba_account SET "accountId" = :account_id, password = :password, "updatedAt" = :updated_at '
                        'WHERE id = :id'
                    ),
                    {
                        "id": account_id,
                        "account_id": ADMIN_EMAIL,
                        "password": password_hash,
                        "updated_at": now,
                    },
                )
                print(f"Updated ba_account credentials for {ADMIN_EMAIL}")

            await session.commit()
            _debug_log(
                "Seed committed successfully",
                hypothesis_id="H2",
                data={"provider_id": PASSWORD_PROVIDER_ID},
            )
            print("Super admin seed completed successfully.")
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_super_admin())