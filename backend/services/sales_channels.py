from __future__ import annotations

from .catalog_feeds import channel_audit, feed_status, google_csv, meta_csv


def audit():
    """Admin sales-channel audit from the exact same snapshot as live feeds."""
    return channel_audit()


def _live_feed_meta(csv_text: str, generated_at: float) -> dict:
    # CSV is generated on request from the canonical Product Master snapshot.
    # The admin therefore reports live feed readiness rather than stale files.
    rows = max(0, len(csv_text.splitlines()) - 1)
    return {
        "exists": True,
        "live": True,
        "size": len(csv_text.encode("utf-8")),
        "updated_at": generated_at,
        "rows": rows,
    }


def channels_status():
    current_audit = channel_audit()
    generated_at = float(current_audit.get("generated_at") or 0)
    google = google_csv()
    meta = meta_csv()
    status = feed_status()

    return {
        "source": current_audit.get("source"),
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
