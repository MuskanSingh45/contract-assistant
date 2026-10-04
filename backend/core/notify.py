"""Optional phone alert when someone new opens the public app (NOTIFY_URL, e.g. an ntfy.sh topic).

Sent from a background thread so a slow or failing notification service never delays a request.
Only the time is sent — never the visitor's address, workspace ID or contract data.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime

import httpx

from backend.core.config import settings

log = logging.getLogger(__name__)


def _send(url: str, message: str) -> None:
    try:
        httpx.post(url, content=message, headers={"Title": "Contract Assistant", "Tags": "eyes"}, timeout=10)
    except Exception as exc:  # noqa: BLE001 - an alert must never break the app
        log.warning("visitor alert failed: %s", exc)


def new_visitor() -> None:
    """Alert that a new browser opened the app (called when its workspace is first created)."""
    if not settings.notify_url:
        return
    when = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    message = f"New visitor opened the app ({when})"
    threading.Thread(target=_send, args=(settings.notify_url, message), daemon=True).start()
