"""
execution/order_guard.py  v1.0
v1.0  2026-10-04  r466 / B2 — AN ORDER THAT WAS SENT IS NEVER FORGOTTEN BY AN ERROR.

🔴 THE DEFECT, found by OTV4TEST's live-readiness audit and measured on mainline:
every live entry path (single leg, butterfly, standing ORB offer, credit
vertical) calls place_order and then confirms, records or polls. If ANYTHING
raised after place_order returned, the except handler logged "order failed"
and returned nothing: the rung was not refused, the order id was dropped, and
no working-order record existed — so the next tick posted the SAME intent
again while the first order might still fill. A double position the DB never
sees.

THE GUARD, one place for all four paths:
  · after_failure(key, placed, session, account, what) — called from the except
    handler whenever an order WAS placed: it tries to CANCEL that order, records
    it as SUSPECT for this intent, and pages once.
  · clear_to_post(key, session, account) — called BEFORE posting for an intent:
    if a suspect order exists it reads its status from the broker. Dead
    (cancelled / expired / removed / rejected) -> cleared, post. Still working
    -> do NOT post. FILLED -> do NOT post, page once: the fill is real but
    unrecorded, and broker reconcile adopts it. Unreadable -> do NOT post.
⚠️ IN-MEMORY. A restart forgets the suspects; at restart the broker reconcile
(B1) adopts any position that exists. Paper never places, so this is inert there.
"""
import logging
import time

from data.tasty_client import sdk_result

logger = logging.getLogger(__name__)

_SUSPECT: dict = {}          # intent key -> {"order_id", "ts", "what", "paged_fill"}


def _page(text: str) -> None:
    try:
        from notifications.alert_manager import get_alert_manager
        get_alert_manager()._send(text)
    except Exception:                                          # noqa: BLE001
        pass


def _status_name(placed) -> str:
    st = getattr(placed, "status", None)
    return str(getattr(st, "name", st) or "").upper()


_DEAD = {"CANCELLED", "EXPIRED", "REMOVED", "PARTIALLY_REMOVED", "REJECTED"}


def after_failure(key: str, placed, session, account, what: str) -> None:
    """An order WAS placed and something after it raised. Cancel it, remember
    it, page. Never raises."""
    oid = str(getattr(placed, "id", "") or "") if placed is not None else ""
    if not oid:
        return
    cancelled = False
    try:
        sdk_result(account.delete_order(session, oid))
        cancelled = True
    except Exception as exc:                                   # noqa: BLE001
        logger.warning("[guard] %s: cancel of %s after an error failed: %s", what, oid, exc)
    _SUSPECT[key] = {"order_id": oid, "ts": time.time(), "what": what, "paged_fill": False}
    logger.error("[guard] %s: order %s was PLACED and then an error followed — "
                 "cancel %s; this intent posts nothing until the broker says "
                 "the order is dead", what, oid, "requested" if cancelled else "FAILED")
    _page(f"⚠️ ORDER GUARD — {what}: order {oid} was placed, then an error. Cancel "
          f"{'requested' if cancelled else 'FAILED'}; no re-post until it is confirmed dead.")


def clear_to_post(key: str, session, account) -> tuple:
    """(ok, why). ok=False means DO NOT POST for this intent this tick."""
    s = _SUSPECT.get(key)
    if not s:
        return True, ""
    try:
        placed = sdk_result(account.get_order(session, s["order_id"]))
        status = _status_name(placed)
    except Exception as exc:                                   # noqa: BLE001
        return False, f"suspect order {s['order_id']} unreadable ({type(exc).__name__})"
    if status in _DEAD:
        _SUSPECT.pop(key, None)
        logger.info("[guard] suspect order %s is %s — intent cleared", s["order_id"], status)
        return True, f"suspect {s['order_id']} {status}"
    if status == "FILLED":
        if not s["paged_fill"]:
            s["paged_fill"] = True
            _page(f"🔴 ORDER GUARD — {s['what']}: order {s['order_id']} FILLED after an error "
                  f"and is NOT in the DB. No new entry on this intent; reconcile adopts it.")
        return False, f"suspect {s['order_id']} FILLED but unrecorded"
    return False, f"suspect {s['order_id']} still {status or 'unknown'}"


def reset() -> None:
    """Tests only."""
    _SUSPECT.clear()
