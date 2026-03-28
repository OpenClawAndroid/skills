---
name: telegram-bridge-send
description: Send Telegram bot messages using token and chatIds stored in ~/.codex/telegram-bridge.json. Use this when a user asks to send any text update to Telegram; if news is requested, research it first, then send the composed summary text.
---

# Telegram Bridge Send

## Overview

Use this skill to send outbound Telegram messages via bot token from `~/.codex/telegram-bridge.json`.

## Config

Expected file shape:

```json
{
  "botToken": "<telegram-bot-token>",
  "chatIds": [123456789]
}
```

`chatIds[0]` is used by default when `--chat-id` is not passed.

## When To Use

Use this skill when the user asks to:
- send a message to Telegram
- send status updates to Telegram
- send a researched summary (for example latest AI news) to Telegram

## Workflow

1. Confirm `~/.codex/telegram-bridge.json` exists and contains `botToken`.
2. Prepare the final message text.
3. Run the sender script.
4. If `--chat-id` is not provided, script uses `chatIds[0]`; if missing, it falls back to Telegram updates.

## Commands

Send a custom message:

```bash
python3 /Users/igor/.codex/skills/telegram-bridge-send/scripts/send_telegram.py \
  --message "Build completed successfully"
```

Send to a specific chat id:

```bash
python3 /Users/igor/.codex/skills/telegram-bridge-send/scripts/send_telegram.py \
  --chat-id 123456789 \
  --message "Hello from Codex"
```

## Example: Latest AI News

1. Research latest AI news using web search.
2. Create a concise multi-line summary with links.
3. Send that text:

```bash
python3 /Users/igor/.codex/skills/telegram-bridge-send/scripts/send_telegram.py \
  --message "Latest AI news:\n1) ...\n2) ..."
```

## Example: Daily AI News via Cron + codex exec

Create a helper script (example path: `~/bin/send_ai_news_daily.sh`):

```bash
#!/usr/bin/env bash
set -euo pipefail

NEWS_TEXT="$(codex exec 'Get latest news about AI (top 5), with short bullet summary and links. Return plain text only, max 1200 chars.')"
python3 /Users/igor/.codex/skills/telegram-bridge-send/scripts/send_telegram.py \
  --message "$NEWS_TEXT"
```

Make it executable:

```bash
chmod +x ~/bin/send_ai_news_daily.sh
```

Add daily cron (every day at 09:00):

```bash
crontab -e
```

```cron
0 9 * * * /Users/igor/bin/send_ai_news_daily.sh >> /Users/igor/.codex/logs/send_ai_news_daily.log 2>&1
```

## Notes

- This skill only sends provided text; it does not fetch news by itself.
- In the cron example, `codex exec` is what fetches and composes the news text.
- If no chat id is available yet, send `/start` to your bot once, then rerun.
