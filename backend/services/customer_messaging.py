from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from .integration_secrets import configured, get_value, set_values, source_for

API_BASE = "https://api.turbosms.ua"
CHANNEL = "customer_message"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_phone(value: str) -> str:
    """Return a provider-ready international number without '+'.

    Ukrainian local mobile numbers such as 0660573374 are normalized to
    380660573374. International numbers entered with '+' are preserved.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""
    had_plus = raw.startswith("+")
    digits = re.sub(r"\D+", "", raw)
    if digits.startswith("00"):
        digits = digits[2:]
        had_plus = True
    if len(digits) == 10 and digits.startswith("0"):
        digits = "38" + digits
    elif len(digits) == 11 and digits.startswith("80"):
        digits = "3" + digits
    if not 10 <= len(digits) <= 15:
        return ""
    if digits.startswith("0"):
        return ""
    if not had_plus and len(digits) == 12 and digits.startswith("380"):
        return digits
    return digits


def customer_messaging_status() -> dict[str, Any]:
    token_ok = configured("messaging.turbosms_token")
    viber_sender = get_value("messaging.viber_sender", "")
    sms_sender = get_value("messaging.sms_sender", "")
    configured_any = bool(token_ok and (viber_sender or sms_sender))
    return {
        "id": "customer_messaging",
        "label": "Клієнтські повідомлення",
        "provider": "TurboSMS",
        "configured": configured_any,
        "api_token": {
            "configured": token_ok,
            "masked": "••••••••••••" if token_ok else "",
            "source": source_for("messaging.turbosms_token"),
        },
        "viber": {
            "configured": bool(token_ok and viber_sender),
            "sender": viber_sender,
            "two_way_note": "Для двостороннього Viber-чату потрібен власний 2-way sender.",
        },
        "sms": {
            "configured": bool(token_ok and sms_sender),
            "sender": sms_sender,
        },
        "hybrid_ready": bool(token_ok and viber_sender and sms_sender),
        "fallback_order": ["viber", "sms"] if viber_sender and sms_sender else (["viber"] if viber_sender else ["sms"]),
    }


def save_customer_messaging_settings(
    *,
    api_token: str | None = None,
    viber_sender: str | None = None,
    sms_sender: str | None = None,
) -> dict[str, Any]:
    values: dict[str, str | None] = {}
    if api_token is not None:
        values["messaging.turbosms_token"] = api_token
    if viber_sender is not None:
        values["messaging.viber_sender"] = viber_sender
    if sms_sender is not None:
        values["messaging.sms_sender"] = sms_sender
    if values:
        set_values(values)
    return customer_messaging_status()


def _api(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    token = get_value("messaging.turbosms_token", "")
    if not token:
        raise RuntimeError("TurboSMS API token is not configured")
    body = json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        API_BASE + path,
        data=body,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "BB610-Market/1.0",
        },
        method="POST",
    )
    try:
        # sequence_id is used for send operations, so a caller can safely retry
        # after a transport failure without creating a duplicate message.
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"TurboSMS HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"TurboSMS network error: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("TurboSMS returned an unexpected response")
    if int(data.get("response_code") or 0) != 0:
        raise RuntimeError(
            "TurboSMS API error: "
            + str(data.get("response_status") or data.get("response_code") or "unknown")
        )
    return data


def test_customer_messaging() -> dict[str, Any]:
    data = _api("/user/balance.json", {})
    result = data.get("response_result") if isinstance(data.get("response_result"), dict) else {}
    return {
        "ok": True,
        "provider": "turbosms",
        "balance": result.get("balance"),
        "checked_at": _now(),
    }


def _provider_message_ids(data: dict[str, Any]) -> list[str]:
    result = data.get("response_result")
    rows = result if isinstance(result, list) else ([result] if isinstance(result, dict) else [])
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ("message_id", "id"):
            value = row.get(key)
            if value not in (None, ""):
                ids.append(str(value))
                break
    return ids


def send_customer_message(
    *,
    phone: str,
    text: str,
    sequence_id: str,
) -> dict[str, Any]:
    number = normalize_phone(phone)
    if not number:
        return {
            "channel": CHANNEL,
            "provider": "turbosms",
            "mode": "",
            "status": "invalid_phone",
            "error": "Invalid customer phone",
            "provider_message_id": "",
        }

    status = customer_messaging_status()
    if not status["configured"]:
        return {
            "channel": CHANNEL,
            "provider": "turbosms",
            "mode": "",
            "status": "not_configured",
            "error": "Customer messaging is not configured",
            "provider_message_id": "",
        }

    viber_sender = str((status.get("viber") or {}).get("sender") or "").strip()
    sms_sender = str((status.get("sms") or {}).get("sender") or "").strip()
    clean_text = " ".join(str(text or "").split()).strip()
    if not clean_text:
        return {
            "channel": CHANNEL,
            "provider": "turbosms",
            "mode": "",
            "status": "failed",
            "error": "Message text is empty",
            "provider_message_id": "",
        }

    payload: dict[str, Any] = {
        "sequence_id": str(sequence_id or "")[:40],
        "recipients": [number],
    }
    if viber_sender:
        payload["viber"] = {
            "sender": viber_sender,
            "text": clean_text[:1000],
            # Fast fallback: if Viber cannot deliver within one minute,
            # SMS may take over instead of waiting for the default 24h TTL.
            "ttl": 60,
        }
    if sms_sender:
        payload["sms"] = {
            "sender": sms_sender,
            "text": clean_text[:661],
            "hybrid_ttl": 300,
        }

    mode = "viber_sms" if viber_sender and sms_sender else ("viber" if viber_sender else "sms")
    try:
        data = _api("/message/send.json", payload)
        ids = _provider_message_ids(data)
        return {
            "channel": CHANNEL,
            "provider": "turbosms",
            "mode": mode,
            "status": "accepted",
            "error": "",
            "provider_message_id": ",".join(ids),
            "sent_at": _now(),
            "phone": number,
        }
    except Exception as exc:
        return {
            "channel": CHANNEL,
            "provider": "turbosms",
            "mode": mode,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "provider_message_id": "",
            "phone": number,
        }


def format_price_request_ack(row: dict[str, Any]) -> str:
    code = str(row.get("request_code") or "").strip()
    product = str(row.get("product_name") or "товар").strip()
    quantity = int(row.get("quantity") or 1)
    return (
        f"BB610 Market. Запит {code} отримано: {product}, {quantity} шт. "
        "Відповідь щодо ціни та доставки надішлемо сюди."
    )


def notify_price_request_customer(row: dict[str, Any]) -> dict[str, Any]:
    code = str(row.get("request_code") or "").strip()
    return send_customer_message(
        phone=str(row.get("contact") or ""),
        text=format_price_request_ack(row),
        sequence_id=("bb610-ack-" + code)[:40],
    )


def reply_price_request_customer(
    row: dict[str, Any],
    *,
    message: str,
    client_request_id: str,
) -> dict[str, Any]:
    import hashlib

    code = str(row.get("request_code") or "").strip()
    digest = hashlib.sha1(f"{code}|{client_request_id}".encode("utf-8")).hexdigest()[:24]
    return send_customer_message(
        phone=str(row.get("contact") or ""),
        text=message,
        sequence_id="bb610-r-" + digest,
    )
