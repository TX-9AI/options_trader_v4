"""
data/tasty_client.py  v4.2
v4.2  2026-10-04  r465 / B1 — get_open_option_positions returns THIS BOX'S underlying
      only (SPX = SPX + SPXW roots); underlying="*" for the whole account. Boxes
      sharing an account would otherwise adopt each other's legs. Operator:
      "multiple boxes will trade that account but never duplicate symbols ever".
v4.1  2026-10-04  r464 / B0 — every Account call goes through tasty_client.sdk_result: on tastytrade
      13.x (the boxes run 13.0.0) Account methods are COROUTINES, and called bare
      a LIVE box could place and close nothing. Paper unaffected. Found by
      OTV4TEST (MSG-1004-06). Pinned by tests/check_sdk_async.py.
TastyTrade session and REST wrapper.

v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
Dated release framing and trivia are stripped; what remains is the
reasoning behind the thresholds, the design guarantees, and the
defects that recur when forgotten. WORKING_AGREEMENT 32 requires
this block be read before the file is edited.

data/tasty_client.py — TastyTrade session via the official tastytrade SDK.
Uses OAuth (client_secret + refresh_token) — never username/password.
Credentials come exclusively from environment variables set by setup_ec2.sh.
The SDK is async-native for streaming. We wrap the session in a thread-safe
singleton. Synchronous SDK calls (orders, chain fetching, market data) work
directly without async. The DXLinkStreamer (for Greeks/quotes) uses a
background async loop.
repo-wide v3.0 bump: Yahoo-Finance purge & data stream
        mapping optimization (all market data now flows from the single
        shared TastyTrade candle feed — see data/candle_feed.py). No logic
        change in this file.
"""

import asyncio
import os
import logging
import threading
from typing import Optional

from tastytrade import Session, Account

from config import get_tt_client_secret, get_tt_refresh_token, get_tt_account_number

logger = logging.getLogger(__name__)

# ─── Background event loop (for DXLinkStreamer async calls) ───────────────────

_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_thread: Optional[threading.Thread]   = None


def _start_background_loop():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


def get_loop() -> asyncio.AbstractEventLoop:
    """Return the background event loop, starting it if needed."""
    global _loop, _loop_thread
    if _loop is None or not _loop.is_running():
        _loop_thread = threading.Thread(
            target=_start_background_loop,
            name="tt-async-loop",
            daemon=True
        )
        _loop_thread.start()
        import time; time.sleep(0.1)
    return _loop


def sdk_result(x):
    """🔴 B0 (r464) — the SDK's Account methods are COROUTINES on tastytrade
    13.x (inspect.iscoroutinefunction is True for get, place_order, get_order,
    delete_order, get_positions, … on the boxes' 13.0.0). Called bare they
    return an unawaited coroutine, so a LIVE box could place and close nothing
    (paper never calls them). Every Account call goes through this: a
    coroutine is run on the background loop, anything else passes through, so
    it is correct on a sync SDK too."""
    return run_async(x) if asyncio.iscoroutine(x) else x


def run_async(coro):
    """
    Run an async coroutine from synchronous code using the background loop.
    Blocks until the coroutine completes and returns its result.
    """
    loop   = get_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


# ─── Session management ────────────────────────────────────────────────────────

_session: Optional[Session]  = None
_account: Optional[Account]  = None
_session_lock = threading.Lock()


def get_session() -> Session:
    """
    Return the active TastyTrade session, creating it if needed.
    Thread-safe. Credentials come from environment variables.
    """
    global _session
    with _session_lock:
        if _session is None:
            _session = _create_session()
    return _session


def _create_session() -> Session:
    client_secret = get_tt_client_secret()
    refresh_token = get_tt_refresh_token()

    logger.info("Connecting to TastyTrade...")
    session = Session(client_secret, refresh_token)
    logger.info("TastyTrade session established")
    return session


def get_account() -> Account:
    """
    Return the active TastyTrade Account object, creating it if needed.
    Uses TT_ACCOUNT_NUMBER env var to select the correct account.
    """
    global _account
    with _session_lock:
        if _account is None:
            session        = get_session()
            account_number = get_tt_account_number()
            _account       = sdk_result(Account.get(session, account_number))   # B0
            logger.info(f"TastyTrade account loaded: {account_number}")
    return _account


def get_account_number() -> str:
    return get_tt_account_number()


def _underlying_family(u: str) -> set:
    """B1 — the roots one box's instrument trades under. SPX lists SPX (AM) and
    SPXW (PM) roots; every other symbol is its own root."""
    u = str(u or "").upper().strip()
    return {"SPX", "SPXW"} if u in ("SPX", "SPXW") else {u}


def get_open_option_positions(underlying: str = None) -> list:
    """
    LIVE broker option positions, normalized for reconciliation (see
    execution/broker_reconcile.py). Returns a list of dicts:
        {symbol, underlying, quantity, direction, average_open_price}
    for OPEN option legs only (quantity != 0). The brokerage is the source of
    truth for whether a position exists; this is how we ask it.

    NEVER call on paper — there is no broker to query. Raises TastyClientError
    on failure so the caller can fall back to DB-only rather than trade blind.

    Version-robust: Account.get_positions is synchronous on tastytrade 12.x but
    a coroutine on 13.x — we detect and run it on the background loop if needed.

    NOTE: field access is verified against tastytrade 13.0.0 and the stable 12.x
    fields, but the deployed pin is >=12.4.0 — run this once against a live box
    and eyeball the output before relying on it for real orders.
    """
    account = get_account()
    session = get_session()
    try:
        raw = account.get_positions(session)
        if asyncio.iscoroutine(raw):
            raw = run_async(raw)
    except Exception as e:
        raise TastyClientError(f"get_positions failed: {e}") from e

    out = []
    for p in raw or []:
        try:
            itype = getattr(p, "instrument_type", "")
            itype = getattr(itype, "value", itype)          # enum -> str if needed
            if "Option" not in str(itype):
                continue                                     # options only
            qty = int(abs(float(getattr(p, "quantity", 0) or 0)))
            direction = str(getattr(p, "quantity_direction", "") or "")
            if qty == 0 or direction.lower() == "zero":
                continue                                     # closed leg
            out.append({
                "symbol":             getattr(p, "symbol", "") or "",
                "underlying":         getattr(p, "underlying_symbol", "") or "",
                "quantity":           qty,
                "direction":          direction,             # 'Long' / 'Short'
                "average_open_price": float(getattr(p, "average_open_price", 0) or 0),
            })
        except Exception as e:
            logger.error(
                f"Skipping unparseable broker position "
                f"{getattr(p, 'symbol', '?')}: {e}"
            )
            continue

    # 🔴 B1 (r465) — OWN INSTRUMENT ONLY. Boxes that share one account would
    # otherwise each see — and adopt — every other box's legs. The operator:
    # "multiple boxes will trade that account but never duplicate symbols ever".
    # Default is this box's instrument; underlying="*" returns the whole account.
    if underlying != "*":
        try:
            import config as _cfg
            fam = _underlying_family(underlying or os.environ.get("OT_INSTRUMENT", "")
                                     or getattr(_cfg, "INSTRUMENT", ""))
        except Exception:                                    # noqa: BLE001
            fam = set()
        if fam and fam != {""}:
            mine = []
            for q in out:
                root = (q.get("underlying") or "").upper()
                if not root:
                    sym = str(q.get("symbol") or "").lstrip(".")
                    root = sym[:-15].strip().upper() if len(sym) > 15 else ""
                if root in fam:
                    mine.append(q)
            if len(mine) != len(out):
                logger.info(f"Broker account holds {len(out)} option position(s); "
                            f"{len(mine)} are this box's ({sorted(fam)}) — the rest ignored")
            out = mine

    logger.info(f"Broker reports {len(out)} open option position(s)")
    return out


def reset_session():
    """Force a new session and account to be created on the next call."""
    global _session, _account
    with _session_lock:
        _session = None
        _account = None
    logger.info("TastyTrade session reset")


# ─── Backwards-compatibility aliases ──────────────────────────────────────────

class TastyClientError(Exception):
    """Raised when a TastyTrade API call fails."""
    pass


def get_client():
    """
    Legacy alias — returns the active Session object.
    New code should use get_session() and get_account() directly.
    """
    return get_session()
