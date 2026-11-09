from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .services.telegram_notifications import send_admin_login_code

router = APIRouter()

_CODE_TTL = 300
_PER_IP_COOLDOWN = 60
_GLOBAL_COOLDOWN = 8
_MAX_ATTEMPTS = 5
_lock = threading.Lock()
_codes: dict[str, dict[str, Any]] = {}
_last_global_send = 0.0


class VerifyCodeBody(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


def _origin_ok(request: Request) -> bool:
    origin = (request.headers.get("origin") or "").lower().rstrip("/")
    return origin in {
        "https://market.bb610.com.ua",
        "https://www.market.bb610.com.ua",
    }


def _client_key(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else "unknown")
    agent = (request.headers.get("user-agent") or "")[:200]
    return hashlib.sha256(f"{ip}|{agent}".encode("utf-8")).hexdigest()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _prune(now: float) -> None:
    expired = [k for k, v in _codes.items() if float(v.get("expires_at") or 0) <= now]
    for key in expired:
        _codes.pop(key, None)


@router.post("/api/v1/admin/auth/request-code")
def request_login_code(request: Request):
    global _last_global_send
    if not _origin_ok(request):
        raise HTTPException(403, "Admin login is available only from market.bb610.com.ua")

    now = time.time()
    key = _client_key(request)
    with _lock:
        _prune(now)
        current = _codes.get(key)
        if current:
            retry_after = int(_PER_IP_COOLDOWN - (now - float(current.get("sent_at") or 0)))
            if retry_after > 0:
                raise HTTPException(429, f"Новий код можна запросити через {retry_after} с")
        global_retry = int(_GLOBAL_COOLDOWN - (now - _last_global_send))
        if global_retry > 0:
            raise HTTPException(429, f"Повторіть через {global_retry} с")

        code = f"{secrets.randbelow(1_000_000):06d}"
        _codes[key] = {
            "digest": _hash_code(code),
            "expires_at": now + _CODE_TTL,
            "sent_at": now,
            "attempts": 0,
        }
        _last_global_send = now

    try:
        send_admin_login_code(code)
    except Exception as exc:
        with _lock:
            _codes.pop(key, None)
        raise HTTPException(503, f"Не вдалося надіслати код у Telegram: {exc}") from exc

    return {"ok": True, "expires_in": _CODE_TTL, "destination": "BB610 Market — Operations"}


@router.post("/api/v1/admin/auth/verify-code")
def verify_login_code(body: VerifyCodeBody, request: Request):
    if not _origin_ok(request):
        raise HTTPException(403, "Admin login is available only from market.bb610.com.ua")

    now = time.time()
    key = _client_key(request)
    with _lock:
        _prune(now)
        current = _codes.get(key)
        if not current:
            raise HTTPException(400, "Код не запитано або він уже прострочений")
        attempts = int(current.get("attempts") or 0) + 1
        current["attempts"] = attempts
        if attempts > _MAX_ATTEMPTS:
            _codes.pop(key, None)
            raise HTTPException(429, "Забагато невдалих спроб. Запросіть новий код")
        valid = hmac.compare_digest(str(current.get("digest") or ""), _hash_code(body.code))
        if not valid:
            raise HTTPException(401, "Невірний код")
        _codes.pop(key, None)

    token = os.getenv("BB610_ADMIN_TOKEN")
    if not token:
        raise HTTPException(503, "Admin API is not configured")
    return {"ok": True, "token": token}
