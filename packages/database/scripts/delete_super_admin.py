"""Delete the default super admin in Better Auth tables.

Usage (from packages/database):
    uv run python scripts/delete_super_admin.py
"""

from __future__ import annotations

import asyncio

from database.db import AsyncSessionLocal
from sqlalchemy import text

ADMIN_EMAIL = "admin@admin.com"


async def delete_super_admin() -> None:
    async with AsyncSessionLocal() as session:
        try:
            # Get user id
            user_result = await session.execute(
                text('SELECT id FROM ba_user WHERE email = :email LIMIT 1'),
                {"email": ADMIN_EMAIL},
            )
            user_id = user_result.scalar_one_or_none()

            if user_id is None:
                print(f"No user found for {ADMIN_EMAIL}")
                return

            # Delete account
            await session.execute(
                text('DELETE FROM ba_account WHERE "userId" = :user_id'),
                {"user_id": user_id},
            )
            print(f"Deleted ba_account for {ADMIN_EMAIL}")

            # Delete sessions
            await session.execute(
                text('DELETE FROM ba_session WHERE "userId" = :user_id'),
                {"user_id": user_id},
            )
            print(f"Deleted ba_session for {ADMIN_EMAIL}")

            # Delete user
            await session.execute(
                text('DELETE FROM ba_user WHERE id = :id'),
                {"id": user_id},
            )
            print(f"Deleted ba_user for {ADMIN_EMAIL}")

            await session.commit()
            print("Super admin deletion completed successfully.")
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(delete_super_admin())