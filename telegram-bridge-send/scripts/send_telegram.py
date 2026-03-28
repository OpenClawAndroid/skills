#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request

CONFIG_PATH = os.path.expanduser("~/.codex/telegram-bridge.json")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_config() -> tuple[str, list[int]]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except FileNotFoundError:
        fail(f"Missing config file: {CONFIG_PATH}")
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {CONFIG_PATH}: {exc}")

    if not isinstance(payload, dict):
        fail(f"Invalid config format in {CONFIG_PATH}")

    token = payload.get("botToken")
    if not isinstance(token, str) or not token.strip():
        fail(f"botToken is missing in {CONFIG_PATH}")

    raw_chat_ids = payload.get("chatIds")
    chat_ids: list[int] = []
    if isinstance(raw_chat_ids, list):
        for value in raw_chat_ids:
            if isinstance(value, int):
                chat_ids.append(value)

    return token.strip(), chat_ids


def telegram_api(token: str, method: str, data: dict) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    payload = json.loads(raw)
    if not payload.get("ok"):
        fail(f"Telegram API {method} failed: {payload}")
    result = payload.get("result")
    return result if isinstance(result, dict) else {"result": result}


def discover_recent_chat_id_from_updates(token: str) -> int:
    result = telegram_api(token, "getUpdates", {"limit": 100, "allowed_updates": ["message", "callback_query"]})
    updates = result.get("result") if isinstance(result, dict) else None
    if not isinstance(updates, list):
        fail("Cannot discover chat id from updates")

    for update in reversed(updates):
        if not isinstance(update, dict):
            continue
        message = update.get("message")
        if isinstance(message, dict):
            chat = message.get("chat")
            if isinstance(chat, dict) and isinstance(chat.get("id"), int):
                return chat["id"]

        callback_query = update.get("callback_query")
        if isinstance(callback_query, dict):
            cb_message = callback_query.get("message")
            if isinstance(cb_message, dict):
                chat = cb_message.get("chat")
                if isinstance(chat, dict) and isinstance(chat.get("id"), int):
                    return chat["id"]

    fail("No chat id found. Send /start to your bot and retry.")


def resolve_chat_id(token: str, config_chat_ids: list[int], cli_chat_id: int | None) -> int:
    if cli_chat_id is not None:
        return cli_chat_id
    if config_chat_ids:
        return config_chat_ids[0]
    return discover_recent_chat_id_from_updates(token)


def send_message(token: str, chat_id: int, text: str) -> None:
    telegram_api(token, "sendMessage", {"chat_id": chat_id, "text": text})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send message to Telegram using ~/.codex/telegram-bridge.json")
    parser.add_argument("--chat-id", type=int, help="Target Telegram chat id. If omitted, use config chatIds[0], then updates fallback")
    parser.add_argument("--message", type=str, required=True, help="Message text to send")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    message = args.message.strip()
    if not message:
        fail("Message cannot be empty")

    token, chat_ids = load_config()
    chat_id = resolve_chat_id(token, chat_ids, args.chat_id)
    send_message(token, chat_id, message)
    print(f"Sent message to chat_id={chat_id}")


if __name__ == "__main__":
    main()
