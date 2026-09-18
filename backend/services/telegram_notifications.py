from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from .integration_secrets import configured, get_value, set_values, source_for

TELEGRAM_API = "https://api.telegram.org"
CHANNEL = "telegram"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def telegram_status() -> dict[str, Any]:
    token_ok = configured("telegram.bot_token")
    chat_id = get_value("telegram.chat_id", "")
    return {
        "id": "telegram",
        "label": "Telegram",
        "configured": bool(token_ok and chat_id),
        "bot_token": {
            "configured": token_ok,
            "masked": "••••••••••••" if token_ok else "",
            "source": source_for("telegram.bot_token"),
        },
        "chat_id": {
            "configured": bool(chat_id),
            "value": chat_id,
            "source": source_for("telegram.chat_id"),
        },
        "price_request_notifications_ready": bool(token_ok and chat_id),
    }


def save_telegram_settings(*, bot_token: str | None = None, chat_id: str | None = None) -> dict[str, Any]:
    values: dict[str, str | None] = {}
    if bot_token is not None:
        values["telegram.bot_token"] = bot_token
    if chat_id is not None:
        values["telegram.chat_id"] = chat_id
    if values:
        set_values(values)
    return telegram_status()


def _api(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = get_value("telegram.bot_token", "")
    if not token:
        raise RuntimeError("Telegram bot token is not configured")
    url = f"{TELEGRAM_API}/bot{token}/{method}"
    body = urllib.parse.urlencode({k: str(v) for k, v in payload.items()}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "BB610-Market/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Telegram HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram network error: {exc}") from exc

    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    result = data.get("result")
    return result if isinstance(result, dict) else {"result": result}


def test_telegram() -> dict[str, Any]:
    chat_id = get_value("telegram.chat_id", "")
    if not chat_id:
        raise RuntimeError("Telegram chat ID is not configured")
    result = _api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": "✅ BB610 Market: тестове повідомлення. Telegram-сповіщення працюють.",
            "disable_web_page_preview": "true",
        },
    )
    return {
        "ok": True,
        "chat_id": str(result.get("chat", {}).get("id") or chat_id),
        "message_id": str(result.get("message_id") or ""),
        "checked_at": _now(),
    }


def discover_telegram_chats() -> dict[str, Any]:
    token = get_value("telegram.bot_token", "")
    if not token:
        raise RuntimeError("Telegram bot token is not configured")

    result = _api("getUpdates", {"limit": 100, "timeout": 0})
    updates = result if isinstance(result, list) else []
    chats: dict[str, dict[str, Any]] = {}
    for update in updates:
        if not isinstance(update, dict):
            continue
        message = update.get("message") or update.get("edited_message") or update.get("channel_post")
        if not isinstance(message, dict):
            continue
        chat = message.get("chat")
        if not isinstance(chat, dict) or chat.get("id") is None:
            continue
        cid = str(chat.get("id"))
        label_parts = [
            str(chat.get("title") or "").strip(),
            " ".join(
                x for x in [
                    str(chat.get("first_name") or "").strip(),
                    str(chat.get("last_name") or "").strip(),
                ] if x
            ).strip(),
            ("@" + str(chat.get("username")).strip()) if chat.get("username") else "",
        ]
        label = " · ".join(x for x in label_parts if x) or cid
        chats[cid] = {
            "chat_id": cid,
            "type": str(chat.get("type") or ""),
            "label": label,
            "username": str(chat.get("username") or ""),
            "last_message_at": message.get("date"),
        }
    rows = sorted(chats.values(), key=lambda x: int(x.get("last_message_at") or 0), reverse=True)
    return {"chats": rows}


def format_price_request_message(row: dict[str, Any]) -> str:
    parts = [
        "🔔 Новий запит ціни · BB610 Market",
        "",
        f"Код: {row.get('request_code') or '—'}",
        f"Товар: {row.get('product_name') or '—'}",
        f"Варіант: {row.get('variant') or '—'}",
        f"SKU: {row.get('sku') or '—'}",
        f"Кількість: {row.get('quantity') or 1} шт.",
        "",
        f"Клієнт: {row.get('customer_name') or '—'}",
        f"Контакт: {row.get('contact') or '—'}",
    ]
    comment = str(row.get("comment") or "").strip()
    if comment:
        parts.append(f"Коментар: {comment}")
    source_url = str(row.get("source_url") or "").strip()
    if source_url:
        parts.extend(["", f"Джерело: {source_url}"])
    return "\n".join(parts)


def notify_price_request(row: dict[str, Any]) -> dict[str, Any]:
    status = telegram_status()
    if not status["price_request_notifications_ready"]:
        return {
            "channel": CHANNEL,
            "status": "not_configured",
            "error": "Telegram notification settings are not configured",
            "provider_message_id": "",
        }

    chat_id = get_value("telegram.chat_id", "")
    try:
        result = _api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": format_price_request_message(row),
                "disable_web_page_preview": "true",
            },
        )
        return {
            "channel": CHANNEL,
            "status": "sent",
            "error": "",
            "provider_message_id": str(result.get("message_id") or ""),
            "sent_at": _now(),
        }
    except Exception as exc:
        return {
            "channel": CHANNEL,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "provider_message_id": "",
        }
