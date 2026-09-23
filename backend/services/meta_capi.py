from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from .integration_secrets import get_value

PIXEL_ID = "1103668908981910"
GRAPH_VERSION = "v26.0"
GRAPH_ROOT = "https://graph.facebook.com"


def send_event(*, event_name, event_id, event_source_url, contents, currency="UAH",
               value=None, order_id=None, client_ip="", client_user_agent=""):
    token = get_value("meta.access_token", "")
    if not token:
        return {"accepted": False, "reason": "not_configured"}

    user_data = {}
    if client_ip:
        user_data["client_ip_address"] = client_ip
    if client_user_agent:
        user_data["client_user_agent"] = client_user_agent
    if not user_data:
        return {"accepted": False, "reason": "missing_user_data"}

    custom_data = {
        "currency": currency or "UAH",
        "content_type": "product",
        "contents": contents or [],
        "content_ids": [str(x.get("id") or "").strip() for x in (contents or []) if str(x.get("id") or "").strip()],
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

    query = urllib.parse.urlencode({"access_token": token})
    url = f"{GRAPH_ROOT}/{GRAPH_VERSION}/{PIXEL_ID}/events?{query}"
    body = json.dumps({"data": [event]}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
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
            data = json.loads(response.read().decode("utf-8") or "{}")
            return {
                "accepted": True,
                "events_received": data.get("events_received"),
                "messages": data.get("messages") or [],
                "fbtrace_id": data.get("fbtrace_id"),
            }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return {"accepted": False, "reason": "meta_http_error", "status": exc.code, "detail": detail}
    except urllib.error.URLError as exc:
        return {"accepted": False, "reason": "meta_network_error", "detail": str(exc)[:300]}
