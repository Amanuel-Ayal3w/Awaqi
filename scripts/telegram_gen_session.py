#!/usr/bin/env python3
"""
Generate TELEGRAM_SESSION_STRING for server-side channel scraping.

Requires TELEGRAM_API_ID and TELEGRAM_API_HASH in the environment (or .env).

Usage:
  uv run python scripts/telegram_gen_session.py

Sign in with the Telegram account that can read @morwestaa (join the channel first).
Paste the printed session string into .env as TELEGRAM_SESSION_STRING=...
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

# Load .env before reading environment variables
load_dotenv()

async def main() -> None:
    api_id = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    if not api_id or not api_hash:
        raise SystemExit(
            "Set TELEGRAM_API_ID and TELEGRAM_API_HASH (from https://my.telegram.org/apps)"
        )

    async with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        await client.start()
        session = client.session.save()
        print("\n--- Add to .env ---\n")
        print(f"TELEGRAM_SESSION_STRING={session}")
        print("\n--- End ---\n")


if __name__ == "__main__":
    asyncio.run(main())
