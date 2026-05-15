"""
Telegram command and message handlers for @ERATaxBot.

Commands:
  /start    — Welcome message (English + Amharic)
  /help     — List all commands
  /lang     — Toggle language between English and Amharic
  /newchat  — Reset the current session and start fresh
  (any text) — Forwarded to the Awaqi FastAPI chat endpoint
"""

import logging
import re

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from . import api_client, formatters, session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application-level error handler
# ---------------------------------------------------------------------------

async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log uncaught exceptions that bubble up from handlers."""
    logger.error("Unhandled exception in update handler", exc_info=context.error)


# ---------------------------------------------------------------------------
# Static message strings
# ---------------------------------------------------------------------------

_WELCOME_EN = (
    "Welcome to *Awaqi* — your Ethiopian Revenue Authority tax information assistant\\.\n\n"
    "Ask me anything about Ethiopian tax law in *English or Amharic*\\.\n\n"
    "Commands:\n"
    "  /help — Show available commands\n"
    "  /lang — Switch language \\(English ↔ Amharic\\)\n"
    "  /newchat — Start a fresh conversation\n\n"
    "_Responses are for informational purposes only and do not constitute legal advice\\._"
)

_WELCOME_AM = (
    "እንኳን ወደ *Awaqi* በደህና መጡ — የኢትዮጵያ ገቢዎች ባለስልጣን የታክስ መረጃ ረዳትዎ\\.\n\n"
    "ስለ ኢትዮጵያ የታክስ ሕግ ጥያቄዎን በ *አማርኛ ወይም እንግሊዝኛ* ይጠይቁ\\.\n\n"
    "ትዕዛዞች:\n"
    "  /help — ትዕዛዞቹን ያሳይ\n"
    "  /lang — ቋንቋ ቀይር \\(አማርኛ ↔ እንግሊዝኛ\\)\n"
    "  /newchat — አዲስ ውይይት ጀምር\n\n"
    "_መልሶቹ ለመረጃ ዓላማ ብቻ ናቸው፣ ህጋዊ ምክር አይሆኑም\\._"
)

_HELP_EN = (
    "*Available commands:*\n\n"
    "  /start — Show welcome message\n"
    "  /help — Show this help\n"
    "  /lang — Toggle language \\(English ↔ Amharic\\)\n"
    "  /newchat — Reset conversation \\(start fresh\\)\n\n"
    "Just type your tax question in English or Amharic to get started\\."
)

_HELP_AM = (
    "*የሚገኙ ትዕዛዞች:*\n\n"
    "  /start — የእንኳን አደረሰ መልዕክት ያሳይ\n"
    "  /help — ይህን ይዘት ያሳይ\n"
    "  /lang — ቋንቋ ቀይር \\(አማርኛ ↔ እንግሊዝኛ\\)\n"
    "  /newchat — ውይይቱን ዳግም አስጀምር\n\n"
    "ስለ ታክስ ጥያቄዎን ለመጀመር በአማርኛ ወይም እንግሊዝኛ ይጻፉ\\."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_retry(detail: str) -> int:
    """Extract the retry-after seconds from an API error message."""
    match = re.search(r"(\d+)\s+second", detail)
    return int(match.group(1)) if match else 60


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _, _, lang = await session.get_or_create(chat_id)

    text = _WELCOME_AM if lang == "am" else _WELCOME_EN
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _, _, lang = await session.get_or_create(chat_id)

    text = _HELP_AM if lang == "am" else _HELP_EN
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _, _, current_lang = await session.get_or_create(chat_id)

    new_lang = "am" if current_lang == "en" else "en"
    await session.set_language(chat_id, new_lang)

    if new_lang == "am":
        msg = "ቋንቋ ወደ *አማርኛ* ተቀይሯል\\."
    else:
        msg = "Language switched to *English*\\."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_newchat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _, _, lang = await session.get_or_create(chat_id)
    await session.reset(chat_id)

    if lang == "am":
        msg = "አዲስ ውይይት ተጀምሯል\\. ጥያቄዎን ይጠይቁ\\."
    else:
        msg = "New conversation started\\. Go ahead and ask your question\\."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward user text messages to the Awaqi API and reply with the answer."""
    message = update.message
    if not message or not message.text:
        return

    chat_id = update.effective_chat.id
    user_text = message.text.strip()

    # Show typing indicator while we wait for the API
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    session_id, token, lang = await session.get_or_create(chat_id)

    try:
        result = await api_client.send_message(
            message=user_text,
            session_id=session_id,
            session_token=token,
            language=lang,
            telegram_chat_id=chat_id,
        )
    except api_client.AwagiAPIError as exc:
        logger.warning("api_error chat_id=%s status=%s", chat_id, exc.status_code)
        if exc.status_code == 429:
            retry = _parse_retry(exc.detail)
            reply = formatters.format_rate_limit_error(retry, lang)
        else:
            reply = formatters.format_error(lang)
        await message.reply_text(reply, parse_mode=ParseMode.MARKDOWN_V2)
        return
    except Exception:
        logger.exception("unexpected_error chat_id=%s", chat_id)
        await message.reply_text(formatters.format_error(lang), parse_mode=ParseMode.MARKDOWN_V2)
        return

    # Persist the fresh session_token for the next request
    if result.session_token:
        await session.update_token(chat_id, result.session_token)

    reply = formatters.format_response(result, lang)
    for chunk in formatters.split_message(reply):
        await message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN_V2)
    logger.info(
        "chat_response chat_id=%s lang=%s confidence=%.2f citations=%d",
        chat_id,
        result.detected_language or lang,
        result.confidence_score,
        len(result.citations),
    )
