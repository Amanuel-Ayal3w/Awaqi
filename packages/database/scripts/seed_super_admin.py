"""Seed or update the default super admin in Better Auth tables.

Usage (from packages/database):
    uv run python scripts/seed_super_admin.py

This script writes to:
  - ba_user
  - ba_account
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import bcrypt
from database.db import AsyncSessionLocal
from sqlalchemy import text

ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "12345678"
ADMIN_NAME = "Super Admin"
PASSWORD_PROVIDER_ID = "credential"


async def seed_super_admin() -> None:
    password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )
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
            print("Super admin seed completed successfully.")
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_super_admin())