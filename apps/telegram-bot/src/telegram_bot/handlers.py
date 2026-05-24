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

from telegram import ReplyKeyboardMarkup, Update
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
# Persistent reply keyboard
# ---------------------------------------------------------------------------

# Button labels — used both to build the keyboard and to match incoming text
_BTN = {
    "ask_en":     "💬 Ask a Question",
    "ask_am":     "💬 ጥያቄ ይጠይቁ",
    "help_en":    "❓ Help",
    "help_am":    "❓ እርዳታ",
    "lang_en":    "🌐 Switch Language",
    "lang_am":    "🌐 ቋንቋ ቀይር",
    "newchat_en": "🆕 New Chat",
    "newchat_am": "🆕 አዲስ ውይይት",
    "history_en": "📋 History",
    "history_am": "📋 ታሪክ",
    "link_en":    "🔗 Link Account",
    "link_am":    "🔗 መለያ አገናኝ",
}

# All button labels as a set for fast lookup
_ALL_BTN_LABELS: set[str] = set(_BTN.values())


def _menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Return the persistent bottom keyboard for the given language."""
    sfx = "am" if lang == "am" else "en"
    rows = [
        [_BTN[f"ask_{sfx}"],     _BTN[f"help_{sfx}"]],
        [_BTN[f"lang_{sfx}"],    _BTN[f"newchat_{sfx}"]],
        [_BTN[f"history_{sfx}"], _BTN[f"link_{sfx}"]],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=False)


# ---------------------------------------------------------------------------
# Static message strings
# ---------------------------------------------------------------------------

_WELCOME_EN = (
    "Welcome to *Awaqi* — your Ethiopian Revenue Authority tax information assistant\\.\n\n"
    "Ask me anything about Ethiopian tax law in *English or Amharic*\\.\n"
    "Use the menu below or just type your question\\.\n\n"
    "_Responses are for informational purposes only and do not constitute legal advice\\._"
)

_WELCOME_AM = (
    "እንኳን ወደ *Awaqi* በደህና መጡ — የኢትዮጵያ ገቢዎች ባለስልጣን የታክስ መረጃ ረዳትዎ\\.\n\n"
    "ስለ ኢትዮጵያ የታክስ ሕግ ጥያቄዎን በ *አማርኛ ወይም እንግሊዝኛ* ይጠይቁ\\.\n"
    "ከታች ያለውን ምናሌ ይጠቀሙ ወይም ጥያቄዎን ቀጥታ ይጻፉ\\.\n\n"
    "_መልሶቹ ለመረጃ ዓላማ ብቻ ናቸው፣ ህጋዊ ምክር አይሆኑም\\._"
)

_HELP_EN = (
    "*Awaqi — Menu guide:*\n\n"
    "💬 *Ask a Question* — Type any tax question\n"
    "🌐 *Switch Language* — Toggle English ↔ Amharic\n"
    "🆕 *New Chat* — Reset and start a fresh conversation\n"
    "📋 *History* — Show your last 5 Q&A exchanges\n"
    "🔗 *Link Account* — Connect Telegram to your Awaqi web account\n\n"
    "You can also use /lang, /newchat, /history, /link directly\\."
)

_HELP_AM = (
    "*Awaqi — የምናሌ መመሪያ:*\n\n"
    "💬 *ጥያቄ ይጠይቁ* — ማንኛውም የታክስ ጥያቄ ይጻፉ\n"
    "🌐 *ቋንቋ ቀይር* — አማርኛ ↔ እንግሊዝኛ ይቀያይሩ\n"
    "🆕 *አዲስ ውይይት* — ዳግም ጀምር\n"
    "📋 *ታሪክ* — ያለፉ 5 ጥያቄዎችን ያሳይ\n"
    "🔗 *መለያ አገናኝ* — ቴሌግራምን ከ Awaqi የድር መለያ ጋር ያገናኙ\n\n"
    "/lang, /newchat, /history, /link ትዕዛዞቹን ቀጥታ መጠቀምም ይቻላል\\."
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
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_menu_keyboard(lang),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _, _, lang = await session.get_or_create(chat_id)

    text = _HELP_AM if lang == "am" else _HELP_EN
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_menu_keyboard(lang),
    )


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _, _, current_lang = await session.get_or_create(chat_id)

    new_lang = "am" if current_lang == "en" else "en"
    await session.set_language(chat_id, new_lang)

    if new_lang == "am":
        msg = "ቋንቋ ወደ *አማርኛ* ተቀይሯል\\."
    else:
        msg = "Language switched to *English*\\."
    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_menu_keyboard(new_lang),
    )


async def cmd_newchat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    _, _, lang = await session.get_or_create(chat_id)
    await session.reset(chat_id)

    if lang == "am":
        msg = "አዲስ ውይይት ተጀምሯል\\. ጥያቄዎን ይጠይቁ\\."
    else:
        msg = "New conversation started\\. Go ahead and ask your question\\."
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the last 5 message exchanges in the current session."""
    chat_id = update.effective_chat.id
    _, _, lang = await session.get_or_create(chat_id)
    history = await session.get_history(chat_id)

    if not history:
        if lang == "am":
            msg = "ምንም የቀደሙ ጥያቄዎች የሉም\\."
        else:
            msg = "No messages in this conversation yet\\."
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
        return

    lines: list[str] = []
    if lang == "am":
        lines.append("*የቅርብ ጊዜ ጥያቄዎች:*\n")
    else:
        lines.append("*Recent messages:*\n")

    for i, pair in enumerate(history, 1):
        user_line = formatters._esc(f"You: {pair['user']}")
        bot_line = formatters._esc(f"Bot: {pair['bot'][:120]}{'…' if len(pair['bot']) > 120 else ''}")
        lines.append(f"{i}\\. {user_line}\n    {bot_line}")

    await update.message.reply_text("\n\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate a one-time link URL and send it to the user."""
    chat_id = update.effective_chat.id
    _, _, lang = await session.get_or_create(chat_id)

    try:
        result = await api_client.request_link(chat_id)
    except api_client.AwagiAPIError as exc:
        logger.warning("link_request_failed chat_id=%s status=%s", chat_id, exc.status_code)
        await update.message.reply_text(formatters.format_error(lang), parse_mode=ParseMode.MARKDOWN_V2)
        return
    except Exception:
        logger.exception("link_request_unexpected chat_id=%s", chat_id)
        await update.message.reply_text(formatters.format_error(lang), parse_mode=ParseMode.MARKDOWN_V2)
        return

    expires_min = result.expires_in_seconds // 60
    url = formatters._esc(result.link_url)

    if lang == "am":
        msg = (
            "ቴሌግራምን ከ Awaqi መለያዎ ጋር ለማገናኘት፡\n\n"
            f"1\\. ወደ Awaqi ድርብ ይግቡ \\(ካልገቡ\\)\n"
            f"2\\. ይህን ሊንክ ይጫኑ:\n\n"
            f"{url}\n\n"
            f"_ሊንኩ ለ {expires_min} ደቂቃ ብቻ ይሰራል\\._"
        )
    else:
        msg = (
            "To connect your Telegram to your Awaqi web account:\n\n"
            f"1\\. Log in to Awaqi in your browser \\(if not already\\)\n"
            f"2\\. Open this link:\n\n"
            f"{url}\n\n"
            f"_This link expires in {expires_min} minutes\\._"
        )

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

    # Route persistent-keyboard button taps to their respective handlers
    if user_text in _ALL_BTN_LABELS:
        if user_text in (_BTN["help_en"], _BTN["help_am"]):
            await cmd_help(update, context)
        elif user_text in (_BTN["lang_en"], _BTN["lang_am"]):
            await cmd_lang(update, context)
        elif user_text in (_BTN["newchat_en"], _BTN["newchat_am"]):
            await cmd_newchat(update, context)
        elif user_text in (_BTN["history_en"], _BTN["history_am"]):
            await cmd_history(update, context)
        elif user_text in (_BTN["link_en"], _BTN["link_am"]):
            await cmd_link(update, context)
        elif user_text in (_BTN["ask_en"], _BTN["ask_am"]):
            _, _, lang = await session.get_or_create(chat_id)
            prompt = "ጥያቄዎን ይጻፉ:" if lang == "am" else "Go ahead — type your tax question:"
            await message.reply_text(formatters._esc(prompt), parse_mode=ParseMode.MARKDOWN_V2)
        return

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

    # Store this exchange in the rolling history (raw text, not MarkdownV2)
    await session.add_message(chat_id, user_text, result.response_text)

    logger.info(
        "chat_response chat_id=%s lang=%s confidence=%.2f citations=%d",
        chat_id,
        result.detected_language or lang,
        result.confidence_score,
        len(result.citations),
    )
