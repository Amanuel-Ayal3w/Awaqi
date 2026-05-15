"""
Awaqi Telegram Bot — entry point.

Runs in long-polling mode (suitable for local development).
For production, configure a webhook instead.

Usage:
    uv run --package telegram-bot telegram-bot
  OR
    python -m telegram_bot.main
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Load .env from the repo root (works when running from any directory)
_repo_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
load_dotenv(os.path.join(_repo_root, ".env"), override=False)

from . import session
from .handlers import (
    cmd_help,
    cmd_lang,
    cmd_newchat,
    cmd_start,
    handle_error,
    handle_message,
)

logging.basicConfig(
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def _set_commands(app: Application) -> None:
    """Register the bot command menu visible in the Telegram UI."""
    await app.bot.set_my_commands([
        BotCommand("start",   "Show welcome message"),
        BotCommand("help",    "List available commands"),
        BotCommand("lang",    "Switch language (English ↔ Amharic)"),
        BotCommand("newchat", "Start a new conversation"),
    ])


async def _on_shutdown(app: Application) -> None:
    await session.close()


def build_app(token: str) -> Application:
    app = (
        Application.builder()
        .token(token)
        .post_init(_set_commands)
        .post_shutdown(_on_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("lang",    cmd_lang))
    app.add_handler(CommandHandler("newchat", cmd_newchat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(handle_error)

    return app


def run() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Add it to your .env file or export it before starting the bot."
        )
        sys.exit(1)

    logger.info("Starting @ERATaxBot in polling mode …")
    app = build_app(token)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run()
