from __future__ import annotations

from .catalog_feeds import (
    channel_audit_from_snapshot,
    channel_snapshot,
    feed_status_from_snapshot,
    google_csv_from_snapshot,
    meta_csv_from_snapshot,
)


def audit():
    """Admin sales-channel audit from the exact same snapshot as live feeds."""
    return channel_audit_from_snapshot(channel_snapshot())


def _live_feed_meta(csv_text: str, generated_at: float) -> dict:
    rows = max(0, len(csv_text.splitlines()) - 1)
    return {
        "exists": True,
        "live": True,
        "size": len(csv_text.encode("utf-8")),
        "updated_at": generated_at,
        "rows": rows,
    }


def channels_status():
    snap = channel_snapshot()
    current_audit = channel_audit_from_snapshot(snap)
    generated_at = float(snap.get("generated_at") or 0)
    google = google_csv_from_snapshot(snap)
    meta = meta_csv_from_snapshot(snap)
    status = feed_status_from_snapshot(snap)

    return {
        "source": snap.get("source"),
        "audit": current_audit,
        "channels": {
            "google": {
                "name": "Google Merchant",
                "feed_url": "/api/v1/catalog/feeds/google-merchant.csv",
                "mode": "live",
                "file": _live_feed_meta(google, generated_at),
            },
            "meta": {
                "name": "Meta Catalog",
                "feed_url": "/api/v1/catalog/feeds/meta-catalog.csv",
                "mode": "live",
                "file": _live_feed_meta(meta, generated_at),
            },
        },
        "feed_status": status,
    }
