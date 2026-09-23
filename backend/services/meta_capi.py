from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .integration_secrets import configured, get_value, source_for

PIXEL_ID = "1103668908981910"
GRAPH_VERSION = "v26.0"
GRAPH_ROOT = "https://graph.facebook.com"


def status() -> dict[str, Any]:
    ready = configured("meta.access_token")
    return {
        "id": "meta_capi",
        "label": "Meta Conversions API",
        "configured": ready,
        "pixel_id": PIXEL_ID,
        "graph_version": GRAPH_VERSION,
        "access_token": {
            "configured": ready,
            "masked": "••••••••••••" if ready else "",
            "source": source_for("meta.access_token"),
        },
        "endpoint": "/api/v1/analytics/meta-capi",
        "deduplication": "event_id",
    }


def _post(payload: dict[str, Any]) -> dict[str, Any]:
    token = get_value("meta.access_token", "")
    if not token:
        raise RuntimeError("Meta Conversions API access token is not configured")
    query = urllib.parse.urlencode({"access_token": token})
    url = f"{GRAPH_ROOT}/{GRAPH_VERSION}/{PIXEL_ID}/events?{query}"
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "BB610-Market/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"Meta CAPI HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Meta CAPI network error: {exc}") from exc


def send_event(
    *,
    event_name: str,
    event_id: str,
    event_source_url: str,
    contents: list[dict[str, Any]],
    currency: str = "UAH",
    value: float | None = None,
    order_id: str | None = None,
    client_ip: str = "",
    client_user_agent: str = "",
    fbp: str = "",
    fbc: str = "",
) -> dict[str, Any]:
    if not event_name or not event_id:
        raise ValueError("event_name and event_id are required")

    user_data: dict[str, Any] = {}
    if client_ip:
        user_data["client_ip_address"] = client_ip
    if client_user_agent:
        user_data["client_user_agent"] = client_user_agent
    if fbp:
        user_data["fbp"] = fbp
    if fbc:
        user_data["fbc"] = fbc

    custom_data: dict[str, Any] = {
        "currency": currency or "UAH",
        "content_type": "product",
        "contents": contents,
        "content_ids": [str(x.get("id") or "").strip() for x in contents if str(x.get("id") or "").strip()],
        "num_items": sum(max(1, int(x.get("quantity") or 1)) for x in contents),
    }
    if value is not None:
        custom_data["value"] = round(float(value), 2)
    if order_id:
        custom_data["order_id"] = str(order_id)

    event = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "event_id": event_id,
        "action_source": "website",
        "event_source_url": event_source_url,
        "user_data": user_data,
        "custom_data": custom_data,
    }
    return _post({"data": [event]})
