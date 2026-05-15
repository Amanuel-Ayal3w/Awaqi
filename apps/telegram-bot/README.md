# Telegram Bot — @ERATaxBot

Telegram interface for the Awaqi tax information assistant.
The bot connects to the running FastAPI backend — no separate AI logic lives here.

## Prerequisites

- FastAPI backend running on `http://localhost:8000`
- Redis running on `redis://localhost:6379/0`
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Setup

### 1. Create a bot on Telegram

1. Open Telegram and message **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `1234567890:ABCdef...`)

### 2. Add the token to `.env`

In the repo root `.env` file, add:

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
```

For per-user rate limiting (recommended), also set:

```bash
TRUST_X_FORWARDED_FOR=true
TRUSTED_PROXIES=127.0.0.1
```

### 3. Install dependencies

From the repo root:

```bash
uv sync
```

### 4. Run the bot

```bash
# From repo root (recommended)
uv run --package telegram-bot telegram-bot

# Or via Makefile
make dev-bot
```

The bot starts in **long-polling** mode — no public URL required for local development.

## Available commands

| Command    | Description                           |
|------------|---------------------------------------|
| `/start`   | Welcome message (English + Amharic)   |
| `/help`    | List all commands                     |
| `/lang`    | Toggle language (English ↔ Amharic)   |
| `/newchat` | Reset the conversation, start fresh   |

Any other text is treated as a tax question and forwarded to the RAG pipeline.

## Architecture

```
Telegram user
    │  (Telegram Bot API)
    ▼
telegram_bot/handlers.py   ← receives update, reads/writes session
    │  (httpx, X-Forwarded-For: telegram:{chat_id})
    ▼
FastAPI  POST /v1/chat/send ← same endpoint the web UI uses
    │
    ▼
RAG pipeline → PostgreSQL + pgvector → Gemini
```

Session state (session_id, session_token, language preference) is stored in Redis
under the key `tg:session:{chat_id}` with a 24-hour sliding TTL.

## Production: Webhook mode

For a deployed environment with a public HTTPS URL, replace `run_polling` with
`run_webhook` in `main.py`. Example:

```python
app.run_webhook(
    listen="0.0.0.0",
    port=8443,
    webhook_url="https://your-domain.com/telegram/webhook",
)
```

Register the webhook with Telegram:

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-domain.com/telegram/webhook"
```
