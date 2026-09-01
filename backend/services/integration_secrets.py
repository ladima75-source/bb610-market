from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SECRETS_DIR = Path(os.getenv("BB610_SECRETS_DIR", str(PROJECT_ROOT / ".bb610-secrets")))
KEY_FILE = SECRETS_DIR / "integrations.key"
STORE_FILE = SECRETS_DIR / "integrations.enc"

_ENV_FALLBACKS = {
    "nova_poshta.api_key": "BB610_NOVA_POSHTA_API_KEY",
    "nova_poshta.api_url": "BB610_NOVA_POSHTA_API_URL",
    "nova_poshta.sender_ref": "BB610_NOVA_POSHTA_SENDER_REF",
    "nova_poshta.sender_contact_ref": "BB610_NOVA_POSHTA_SENDER_CONTACT_REF",
    "nova_poshta.sender_address_ref": "BB610_NOVA_POSHTA_SENDER_ADDRESS_REF",
    "payments.cod_enabled": "BB610_PAYMENT_COD_ENABLED",
}


def _ensure_dir() -> None:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(SECRETS_DIR, 0o700)
    except OSError:
        pass


def _fernet() -> Fernet:
    _ensure_dir()
    if not KEY_FILE.exists():
        KEY_FILE.write_bytes(Fernet.generate_key())
        try:
            os.chmod(KEY_FILE, 0o600)
        except OSError:
            pass
    return Fernet(KEY_FILE.read_bytes().strip())


def _load_store() -> dict[str, Any]:
    if not STORE_FILE.exists():
        return {}
    raw = STORE_FILE.read_bytes()
    if not raw:
        return {}
    try:
        payload = _fernet().decrypt(raw)
        data = json.loads(payload.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Integration secret store cannot be decrypted") from exc


def _save_store(data: dict[str, Any]) -> None:
    _ensure_dir()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encrypted = _fernet().encrypt(payload)
    tmp = STORE_FILE.with_suffix(".tmp")
    tmp.write_bytes(encrypted)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    tmp.replace(STORE_FILE)
    try:
        os.chmod(STORE_FILE, 0o600)
    except OSError:
        pass


def get_value(key: str, default: str = "") -> str:
    data = _load_store()
    value = data.get(key)
    if value is not None and str(value).strip() != "":
        return str(value).strip()
    env_name = _ENV_FALLBACKS.get(key)
    if env_name:
        return os.getenv(env_name, default).strip()
    return default


def has_secure_value(key: str) -> bool:
    data = _load_store()
    value = data.get(key)
    return value is not None and str(value).strip() != ""


def set_values(values: dict[str, str | None]) -> None:
    data = _load_store()
    for key, value in values.items():
        if value is None:
            continue
        text = str(value).strip()
        if text == "":
            data.pop(key, None)
        else:
            data[key] = text
    _save_store(data)


def source_for(key: str) -> str:
    if has_secure_value(key):
        return "secure_store"
    env_name = _ENV_FALLBACKS.get(key)
    if env_name and os.getenv(env_name, "").strip():
        return "env"
    return "not_configured"


def configured(key: str) -> bool:
    return bool(get_value(key))
