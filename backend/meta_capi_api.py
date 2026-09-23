from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Cookie, Header, Request
from pydantic import BaseModel, Field

from .services.meta_capi import send_event, status as meta_status

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_ALLOWED = {"ViewContent", "AddToCart", "InitiateCheckout", "Purchase"}


class MetaContent(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    quantity: int = Field(default=1, ge=1, le=1000)
    item_price: float | None = Field(default=None, ge=0)


class MetaEvent(BaseModel):
    event_name: str = Field(min_length=1, max_length=64)
    event_id: str = Field(min_length=8, max_length=200)
    event_source_url: str = Field(min_length=8, max_length=2000)
    currency: str = Field(default="UAH", min_length=3, max_length=3)
    value: float | None = Field(default=None, ge=0)
    order_id: str | None = Field(default=None, max_length=200)
    contents: list[MetaContent] = Field(default_factory=list, max_length=100)


@router.post("/meta-capi")
def meta_capi_event(
    body: MetaEvent,
    request: Request,
    user_agent: str | None = Header(default=None),
    x_forwarded_for: str | None = Header(default=None),
    fbp: str | None = Cookie(default=None, alias="_fbp"),
    fbc: str | None = Cookie(default=None, alias="_fbc"),
):
    if body.event_name not in _ALLOWED:
        return {"accepted": False, "reason": "unsupported_event"}
    if not meta_status().get("configured"):
        return {"accepted": False, "reason": "not_configured"}

    origin = (request.headers.get("origin") or "").lower().rstrip("/")
    if origin and origin not in {"https://market.bb610.com.ua", "https://www.market.bb610.com.ua"}:
        return {"accepted": False, "reason": "origin_not_allowed"}

    ip = ""
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    if not ip and request.client:
        ip = request.client.host or ""

    try:
        response = send_event(
            event_name=body.event_name,
            event_id=body.event_id,
            event_source_url=body.event_source_url,
            contents=[x.model_dump(exclude_none=True) for x in body.contents],
            currency=body.currency.upper(),
            value=body.value,
            order_id=body.order_id,
            client_ip=ip,
            client_user_agent=user_agent or "",
            fbp=fbp or "",
            fbc=fbc or "",
        )
        return {
            "accepted": True,
            "events_received": response.get("events_received"),
            "messages": response.get("messages") or [],
            "fbtrace_id": response.get("fbtrace_id"),
        }
    except Exception as exc:
        # Tracking must never break storefront actions.
        return {"accepted": False, "reason": "upstream_error", "detail": str(exc)[:300]}
