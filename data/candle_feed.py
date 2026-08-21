"""
data/candle_feed.py  v4.3
v4.3  2026-08-20  THE RTH FEED GATE IS REMOVED. Subscriptions are held whenever
    the box is up; MAINTENANCE (OT_FEED_MODE) is the only stand-down left and it
    is now UNCONDITIONAL — the old block slept only until the next open and
    seconds_until_rth_open() returns 0 during RTH, so a maintenance window
    declared inside the session was silently defeated. The gate existed to stop
    a maintenance wake putting 29 boxes on the wire at once; the fleet is now
    15, the same 15 daily, and a normal session already carried ~20 without
    strain. Operator's call, 2026-08-20. The v4.2 write guard below is what
    makes this safe: every non-RTH bar still routes to <SYM>_EXT, for EVERY
    interval, so the plain series stays RTH-pure while the box streams 24h.
v4.2  2026-08-20  RTH GUARD AT THE WRITE — ported from the SMC thread's v3.17.
    The FEED.2 fix corrected STREAMING routes, and the restart's BACKFILL then
    wrote 24-HOUR bars into the plain series anyway. Measured on the fleet
    2026-08-20 after the v3.16 bake: plain-symbol 1h carried hours 00-23 on
    equities from 08-05 forward — ~12 bars/hour overnight against 38-39 in RTH.
    **SPX was clean (hours 13-20 only), and that control is the proof**: an
    index has no overnight session, so it had nothing to be contaminated with.

    ⚠️ THIS IS WORSE THAN THE HOLE IT REPLACED. A gap announces itself; a series
    that silently CHANGES CHARACTER mid-stream does not. 07-31 was RTH-only and
    08-19 was 24-hour, with nothing marking the seam — and structure_analyzer
    (weight 2.0), the pitchfork's 1h fractals, trend_engine's 0.20 context vote
    and entry_snapshot all read plain 1h expecting RTH.

    ⚠️ SEGREGATED, NEVER DROPPED, and that is the SMC thread's improvement on
    what I first proposed. I suggested deleting the non-RTH rows. **EXT_INTERVAL
    is 1h ONLY, so an overnight 5m or 15m bar has no other home anywhere** — and
    DXFeed history is use-it-or-lose-it. A non-RTH bar arriving on a plain route
    is RE-ROUTED to <SYM>_EXT; `tools/segregate_nonrth_bars.py` does the same for
    rows already written (moves, dry-run by default, backs up first, and reports
    destination collisions rather than silently merging them).

v4.1  2026-08-20  FEED.2 — EVERY 1h CANDLE ROUTED TO THE WRONG SYMBOL FOR SIX
    DAYS, FLEET-WIDE. Ported verbatim from the v3/SMC fix (v3.16); the body
    below the header was BYTE-IDENTICAL across all three repos, so this is one
    defect with one fix in three places.

    `symbol_map` was keyed on (dx_symbol, interval), and FEED.2 subscribes the
    SAME symbol at the SAME interval TWICE — RTH and extended. The second
    registration overwrote the first, so **the RTH 1h route was destroyed at
    construction** and every 1h bar landed under the EXT store symbol. Measured
    2026-08-20: plain QQQ and SPX 1h frozen at 2026-08-14 while *_EXT 1h was
    current.

    ⚠️ NOTHING RAISED. BARS_STALE warned every five minutes with
    `refused=False` and the bots traded on 08-14 bars regardless. **Six days of
    stale higher-timeframe structure** fed structure_analyzer's swings and S/R,
    the pitchfork and its observer, and entry_snapshot.

    ⚠️ AND IT LANDS ON WORK DONE THIS WEEK. r183 raised TIMEFRAMES["1h"] from
    50 to 80 because trend_engine needs EMA_SLOW+5=55, and that diagnosis —
    "the 1h vote never fired" — was correct about the DEPTH and blind to the
    STORE BEING FROZEN. **I tuned an instrument's configuration without
    checking whether its input was arriving**, which is the same failure as
    `oi_proxy`, `max_liq` and `vix_at_entry`: a plausible silence, fixed at the
    wrong layer.

    ⚠️ WHAT IS *NOT* AFFECTED: every study run on 2026-08-20 —
    fork_respect_study, tine_order_study, sweep_discriminator,
    magnitude_estimator, chain_feasibility — builds its own bars from the 1m
    OHLC CSVs and never reads the candle store. **Those numbers stand.**

    FIX: the map key carries the extended-hours flag, and the ingest router
    reads `tho=true` off the echoed symbol — the attribute `_interval_of`
    deliberately discards is exactly the one the router needed.
    GUARD: the feed REFUSES TO START if two subscriptions share a route key, if
    a subscription has no route, or if two subscriptions write the same
    (store_symbol, interval). **The defect was not a typo; it was a route table
    that could silently lose an entry, and that must be impossible rather than
    merely fixed.**

    ⚠️ EXISTING ROWS ARE NOT REPAIRED. Plain-symbol 1h history between 08-14 and
    the deploy is simply absent, and DXFeed history is use-it-or-lose-it.
    Backfill on restart refills what the API still serves.
"""
import argparse
import asyncio
import logging
import os
import json
import sqlite3
import traceback
import threading
import time as _time
from datetime import datetime, time as dtime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from tastytrade import DXLinkStreamer           # module-level so tests can patch
from tastytrade.dxfeed import Candle, Greeks, Quote

from config import INSTRUMENT, TIMEFRAMES
from data.tasty_client import get_session, get_loop

logger = logging.getLogger(__name__)

# ── Poison-candle sanity window (v3.2) ────────────────────────────────────────
# Any candle timestamp outside this window is junk. The observed failure is the
# signed-32-bit rollover (2**31 * 1000 = 2147483648000 ms => 2038-01-19), which
# is far in the future; a 0 / negative ts is equally invalid. Upper bound is
# computed at call time (now + 2 days) so a legitimately-fresh bar is never
# rejected for clock skew, while a 2038 bar always is.
TS_MS_MIN = 1_262_304_000_000        # 2010-01-01 — older than any bar we'd want


def _ts_ms_max() -> int:
    """Newest acceptable candle ts: now + 2 days (tolerates clock skew, kills 2038)."""
    return int((_time.time() + 172_800) * 1000)
ET = ZoneInfo("America/New_York")

# ─── Store location — single definition, imported by every reader ─────────────

def feed_db_path() -> str:
    """Resolve the shared store path. $OT_FEED_DB overrides; default is
    self-locating inside the repo's data/ dir so producer and consumers on the
    same checkout always agree."""
    env = os.environ.get("OT_FEED_DB", "").strip()
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "feed_store.db")


# ─── Tunables ──────────────────────────────────────────────────────────────────

SESSION_OPEN_HM   = (9, 30)          # ET
FLUSH_INTERVAL_S  = 2.0              # buffer -> SQLite cadence (also heartbeat)
PRUNE_FACTOR      = 4                # legacy; unused while PRUNE_KEEP_ROWS is 0
# FEED.3: 0 = NO PRUNING (default). Set OT_PRUNE_KEEP_ROWS to a positive row
# count to re-enable a flat per-(symbol,interval) cap. Kept as a mechanism
# rather than deleted so it is one env var to reverse, not a code change.
PRUNE_KEEP_ROWS   = int(os.environ.get("OT_PRUNE_KEEP_ROWS", "0"))
# TERM.1: an auxiliary-tenor subscription older than this is ignored. Stale
# strikes burn socket budget against a measured ~40-session cap for contracts
# nothing reads.
AUX_MAX_AGE_S     = 6 * 3600
PRUNE_EVERY_S     = 300
RECONNECT_MIN_S   = 3

# v4.3 — FEED_WARM_LEAD_S and the is_rth/seconds_until_rth_open imports are
# GONE with the RTH gate. There is no longer an open to warm up to: the feed
# holds its subscriptions continuously while the box is up, so the frames are
# never cold. `OT_FEED_WARM_LEAD_S` is now INERT — if it is still set in a
# box .env it does nothing, which is stated here so a future reader does not
# spend an evening looking for the code that reads it.

# ── FEED MODE (FEED.1, 2026-08-15) — THE THIRD PURPOSE ───────────────────────
# `_feed_stood_down` (v4.3, formerly `_idle_outside_session`) already says the
# right thing: **"THE DISTINCTION IS
# PURPOSE, NOT TIME."** It only had TWO purposes — service (hold a socket for a
# live session) and one-shot (`--once`, pull history and exit). A `--once` run
# is therefore allowed at ANY hour, which is correct for the EOD pull and wrong
# for the thing v3.9 was actually protecting: **a maintenance wake that brings
# all 29 boxes up for work needing no market data.**
#
# Operator's requirement: a dedicated MAINTENANCE window where the whole fleet
# can be up for fleet updates "without involving the feed or using api
# resources". That cannot be expressed as a clock rule — maintenance and the
# overnight capture pass happen at the same hours and want opposite behaviour.
#
#   service      today's behaviour, unchanged. The default, so nothing moves.
#   capture      a scoped one-shot pull. Same as service for gating; the name
#                exists so a capture wake is DISTINGUISHABLE in the logs from a
#                trader wake, and so a future window argument has somewhere to
#                live.
#   maintenance  HARD OFF. No socket, no subscription, not even `--once`.
#
# ⚠️ AND IT MUST ANNOUNCE ITSELF. On 2026-08-03/04 the gate silently blocked the
# EOD pull: the log read `Feed idle — outside RTH` at INFO four times, then
# `0 bars`, and fourteen 38-byte header-only CSVs were written. Nothing raised,
# and DXFeed history is same-evening only, so BOTH SESSIONS ARE PERMANENTLY
# LOST. A maintenance-suppressed run must never look like a failed fetch: it
# logs at WARNING and says the mode by name.
# ⚠️ A SENTINEL FILE, NOT ONLY AN ENV VAR. `Environment=` in the unit is read
# ONCE AT IMPORT, so flipping the mode on a RUNNING feed would need a restart —
# and the restart window is precisely when the box is on the wire during the
# maintenance it is supposed to be excused from. The file is checked on every
# gate evaluation, so `touch`/`rm` takes effect on the next loop with nothing
# to restart and no race to lose.
MAINT_FLAG = os.environ.get(
    "OT_FEED_MAINT_FLAG",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "data", "FEED_MAINTENANCE"))


def _maintenance_now() -> bool:
    """True if this box is in a maintenance window RIGHT NOW.

    Sentinel file first (live, no restart), env second (set at wake time).
    ⚠️ FAILS OPEN TO service ON AN UNREADABLE PATH: a box that cannot stat the
    flag must keep FEEDING, because the alternative is a silent tape loss that
    DXFeed's same-evening history makes permanent. A stray socket during
    maintenance is recoverable; a missing session is not.
    """
    try:
        if os.path.exists(MAINT_FLAG):
            return True
    except Exception:                                          # noqa: BLE001
        pass
    return FEED_MODE == "maintenance"


FEED_MODE = os.environ.get("OT_FEED_MODE", "service").strip().lower()
_VALID_FEED_MODES = ("service", "capture", "maintenance")
if FEED_MODE not in _VALID_FEED_MODES:
    # An unknown mode must not silently become "maintenance" (a box that never
    # feeds) NOR silently become "service" (a box on the wire during
    # maintenance). Fail to the DEFAULT and say so loudly.
    logging.getLogger(__name__).warning(
        "[feed-mode] OT_FEED_MODE=%r is not one of %s - falling back to "
        "'service'. Fix the unit/env; do not rely on this default.",
        FEED_MODE, ", ".join(_VALID_FEED_MODES))
    FEED_MODE = "service"
RECONNECT_MAX_S   = 60
def _is_ext_route(store_symbol: str) -> bool:
    """v3.17 — is this store symbol the extended-hours stream?"""
    return str(store_symbol or "").endswith("_EXT")


# v3.17 — RTH windows by interval, in ET, as (start, end) inclusive of start
# and exclusive of end. Interval-aware because DXFeed aligns hour bars to the
# HOUR: the 09:00 ET hour bar contains the 09:30 open and is legitimate RTH
# data, while a 09:00 ET *minute* bar is pre-market. Getting this wrong in the
# permissive direction leaves contamination; getting it wrong in the strict
# direction deletes real bars, so the hour case is deliberately generous.
_RTH_BY_INTERVAL = {
    "1m":  ((9, 30), (16, 0)),
    "5m":  ((9, 30), (16, 0)),
    "15m": ((9, 30), (16, 0)),
    "1h":  ((9, 0),  (16, 30)),
}


def _within_rth(ts_ms: int, interval: str) -> bool:
    """Does this bar START inside the regular session, in ET?

    Daily and coarser are always accepted — a 1d bar is stamped at midnight
    and would fail every intraday test, which would silently delete the daily
    series. That mistake is one line away and would be invisible until
    something asked for a daily level.
    """
    win = _RTH_BY_INTERVAL.get(interval)
    if win is None:                      # 1d, 1w, anything coarser
        return True
    try:
        et = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone(ET)
    except (OverflowError, OSError, ValueError):
        return True                      # unparseable: let the poison guard rule
    if et.weekday() >= 5:                # weekend bars are never RTH
        return False
    (sh, sm), (eh, em) = win
    minutes = et.hour * 60 + et.minute
    return (sh * 60 + sm) <= minutes < (eh * 60 + em)


VIX_SYMBOL        = os.environ.get("OT_DXFEED_VIX", "VIX")
VIX_INTERVALS     = ("1m", "1d")

# Backfill depth per interval: calendar days back from now that comfortably
# cover TIMEFRAMES count (RTH ~6.5h/day, ~78 5m bars, ~26 15m bars, ~7 1h bars).
# ── FEED.2 — the overnight (extended-hours) 1h stream ────────────────────────
# Stored under its OWN symbol so nothing that reads plain "1h" changes.
EXT_INTERVAL     = os.environ.get("OT_EXT_INTERVAL", "1h").strip()
EXT_STORE_SYMBOL = f"{INSTRUMENT}_EXT"
EXT_1H_ENABLED   = os.environ.get("OT_EXT_1H", "1").strip() not in ("0", "false", "")

BACKFILL_DAYS = {
    "1m":  1,      # today's session (plus yesterday if pre-open)
    "5m":  4,      # 100 bars ≈ 1.3 sessions -> 4 cal days covers weekends
    "15m": 6,      # 50 bars ≈ 2 sessions
    "1h":  16,     # 50 bars ≈ 8 sessions
    "1d":  30,     # 10 bars ≈ 2 weeks + margin
}


def _dxfeed_symbol() -> str:
    return os.environ.get("OT_DXFEED_SYMBOL", "").strip() or INSTRUMENT


def _explain_exc(e, _depth=0):
    """Flatten an exception (incl. ExceptionGroup / __cause__) to a readable line.
    v3.8 — asyncio TaskGroup wraps the real failure in an ExceptionGroup whose
    str() is just 'unhandled errors in a TaskGroup (1 sub-exception)', which hid
    XOM's actual stream-reject cause for two days."""
    if _depth > 5:
        return repr(e)
    parts = ["%s: %s" % (type(e).__name__, e)]
    subs = getattr(e, "exceptions", None)
    if subs:
        parts.append("[" + " | ".join(_explain_exc(x, _depth + 1) for x in subs) + "]")
    cause = getattr(e, "__cause__", None) or getattr(e, "__context__", None)
    if cause is not None and cause is not e:
        parts.append("<- caused by " + _explain_exc(cause, _depth + 1))
    return " ".join(parts)


def _base_symbol(event_symbol: str) -> str:
    """'QQQ{=5m}' -> 'QQQ'."""
    return (event_symbol or "").split("{")[0]


def _backfill_start(interval: str, now_et: Optional[datetime] = None) -> datetime:
    now_et = now_et or datetime.now(ET)
    days = BACKFILL_DAYS.get(interval, 4)
    if interval == "1m":
        # Today's session open; if pre-open, previous calendar day's open so the
        # most recent session is available (readers scope to one session).
        d = now_et.date()
        if now_et.time() < dtime(*SESSION_OPEN_HM):
            d = d - timedelta(days=1)
        return datetime.combine(d, dtime(*SESSION_OPEN_HM), tzinfo=ET)
    return now_et - timedelta(days=days)


# ─── SQLite store (WAL, one writer — this process) ────────────────────────────

class FeedStore:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # check_same_thread=False + an explicit lock (v3.3).
        # The store is constructed on the MAIN thread but every write
        # (_flush -> upsert_candles/heartbeat/commit) is driven from the asyncio
        # event-loop thread created by get_loop(). Python's sqlite3 rejects that
        # by default:
        #   ProgrammingError: SQLite objects created in a thread can only be
        #   used in that same thread.
        # which killed candle-feed on its first flush, every start (GOOGL,
        # 2026-07-13). We remain a SINGLE writer — the lock serializes access so
        # allowing cross-thread use is safe.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS candles (
                symbol      TEXT NOT NULL,
                interval    TEXT NOT NULL,
                ts_epoch_ms INTEGER NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                PRIMARY KEY (symbol, interval, ts_epoch_ms)
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS feed_meta (
                symbol   TEXT NOT NULL,
                interval TEXT NOT NULL,
                last_write_epoch REAL NOT NULL,
                PRIMARY KEY (symbol, interval)
            );""")
        # ── v3.4: chain-marks transport (Option 1b) ──────────────────────────
        # chain_subs: single row WRITTEN BY THE BOT (options_chain v3.2) naming
        # the streamer symbols + expiry it wants live marks for. chain_marks:
        # latest-value Greeks/Quote per option symbol, WRITTEN BY THE FEED.
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chain_subs (
                id            INTEGER PRIMARY KEY CHECK (id = 1),
                expiry        TEXT NOT NULL,
                symbols       TEXT NOT NULL,          -- JSON list
                updated_epoch REAL NOT NULL
            );""")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chain_marks (
                streamer_symbol TEXT PRIMARY KEY,
                bid REAL, ask REAL,
                delta REAL, gamma REAL, theta REAL, vega REAL, iv REAL,
                updated_epoch REAL NOT NULL
            );""")
        self.conn.commit()

    def upsert_candles(self, rows: List[Tuple]):
        """rows: (symbol, interval, ts_ms, o, h, l, c, v). Last write wins."""
        if not rows:
            return
        with self._lock:
            self._upsert_candles_locked(rows)

    def _upsert_candles_locked(self, rows: List[Tuple]):
        self.conn.executemany(
            "INSERT OR REPLACE INTO candles "
            "(symbol, interval, ts_epoch_ms, open, high, low, close, volume) "
            "VALUES (?,?,?,?,?,?,?,?)", rows)
        now = _time.time()
        touched = {(r[0], r[1]) for r in rows}
        self.conn.executemany(
            "INSERT OR REPLACE INTO feed_meta (symbol, interval, last_write_epoch) "
            "VALUES (?,?,?)", [(s, i, now) for (s, i) in touched])

    def purge_poison(self) -> int:
        """Delete any poison rows already in the store (v3.2). Runs at feed
        startup so a box whose DB was poisoned before this guard existed
        self-heals on restart — no manual sqlite surgery across the fleet."""
        with self._lock:
            cur = self.conn.execute(
                "DELETE FROM candles WHERE open <= 0 OR high <= 0 OR low <= 0 "
                "OR close <= 0 OR ts_epoch_ms < ? OR ts_epoch_ms > ?",
                (TS_MS_MIN, _ts_ms_max()))
            self.conn.commit()
            n = cur.rowcount or 0
        if n:
            logger.warning("purged %d poison candle row(s) from the store", n)
        return n

    def heartbeat(self):
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO feed_meta (symbol, interval, last_write_epoch) "
                "VALUES ('__feed__','heartbeat',?)", (_time.time(),))

    def commit(self):
        with self._lock:
            self.conn.commit()

    # ── v3.4: chain-marks transport ───────────────────────────────────────────
    def read_chain_subs(self):
        """(expiry, [streamer_symbols]) requested by the bot, or ("", []).

        ⚠️ TERM.1 (2026-08-18): the returned symbol list is the FRONT expiry
        UNIONED with any auxiliary tenors. `chain_subs` is `CHECK (id = 1)` — a
        single row by design — so extra expiries ride in a SEPARATE table and
        the front-expiry contract is untouched. The returned `expiry` string
        still names the FRONT expiry only: every existing caller reads it that
        way and none of them changes.

        ⚠️ FAILS OPEN, DELIBERATELY. A missing, empty or malformed aux table
        returns the front expiry exactly as before. **This function decides what
        a live trading box subscribes to** — the auxiliary tenors are archival
        enrichment and must never be able to cost the bot its own chain.
        """
        with self._lock:
            row = self.conn.execute(
                "SELECT expiry, symbols FROM chain_subs WHERE id=1").fetchone()
        if not row:
            return "", []
        try:
            expiry = row[0] or ""
            syms = json.loads(row[1] or "[]")
        except (ValueError, TypeError):
            return "", []
        try:
            aux = self._read_chain_subs_aux()
            if aux:
                seen = set(syms)
                for s in aux:
                    if s not in seen:
                        seen.add(s)
                        syms.append(s)
        except Exception:                                      # noqa: BLE001
            pass          # archival enrichment never costs the bot its chain
        return expiry, syms

    def _read_chain_subs_aux(self):
        """Extra-tenor streamer symbols, or [] if the table is absent/stale.

        ⚠️ STALENESS BOUND. An aux row older than the front expiry's own update
        is a leftover from a previous session — subscribing to last week's
        strikes wastes socket budget against a measured ~40-session cap and
        pollutes `chain_marks` with contracts nothing reads.
        """
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='chain_subs_aux'")
        if not cur.fetchone():
            return []
        cutoff = _time.time() - AUX_MAX_AGE_S
        rows = self.conn.execute(
            "SELECT symbols FROM chain_subs_aux WHERE updated_epoch >= ?",
            (cutoff,)).fetchall()
        out = []
        for r in rows:
            try:
                out.extend(json.loads(r[0] or "[]"))
            except (ValueError, TypeError):
                continue
        return out

    def upsert_chain_quotes(self, rows):
        """rows: (streamer_symbol, bid, ask, epoch) — preserves greeks columns."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT INTO chain_marks (streamer_symbol, bid, ask, updated_epoch) "
                "VALUES (?,?,?,?) ON CONFLICT(streamer_symbol) DO UPDATE SET "
                "bid=excluded.bid, ask=excluded.ask, "
                "updated_epoch=excluded.updated_epoch", rows)

    def upsert_chain_greeks(self, rows):
        """rows: (streamer_symbol, delta, gamma, theta, vega, iv, epoch) —
        preserves quote columns."""
        if not rows:
            return
        with self._lock:
            self.conn.executemany(
                "INSERT INTO chain_marks (streamer_symbol, delta, gamma, theta, "
                "vega, iv, updated_epoch) VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(streamer_symbol) DO UPDATE SET "
                "delta=excluded.delta, gamma=excluded.gamma, theta=excluded.theta, "
                "vega=excluded.vega, iv=excluded.iv, "
                "updated_epoch=excluded.updated_epoch", rows)

    def clear_chain_marks(self):
        with self._lock:
            self.conn.execute("DELETE FROM chain_marks")
            self.conn.commit()

    def prune(self, symbol: str, interval: str, keep: int):
        with self._lock:
            self._prune_locked(symbol, interval, keep)

    def _prune_locked(self, symbol: str, interval: str, keep: int):
        self.conn.execute("""
            DELETE FROM candles WHERE symbol=? AND interval=? AND ts_epoch_ms NOT IN
            (SELECT ts_epoch_ms FROM candles WHERE symbol=? AND interval=?
             ORDER BY ts_epoch_ms DESC LIMIT ?)""",
            (symbol, interval, symbol, interval, keep))

    def bar_count(self, symbol: str, interval: str) -> int:
        with self._lock:
            cur = self.conn.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol=? AND interval=?",
                (symbol, interval))
            return int(cur.fetchone()[0])

    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass


# ─── The producer ──────────────────────────────────────────────────────────────

class CandleFeed:
    """Persistent single subscription -> in-memory last-write-wins buffer ->
    periodic flush to the shared store."""

    def __init__(self, store: FeedStore):
        self.store = store
        self.dx_symbol = _dxfeed_symbol()
        # (dxfeed_symbol, interval) -> store symbol name
        self.symbol_map: Dict[Tuple[str, str], str] = {}
        # (dx_sym, interval, start, extended_trading_hours)
        self.subs: List[Tuple[str, str, datetime, bool]] = []
        for tf in TIMEFRAMES.keys():
            self.subs.append((self.dx_symbol, tf, _backfill_start(tf), False))
            # v3.16 — the key now carries the EXTENDED-HOURS FLAG, because
            # (dx_symbol, interval) is NOT unique: FEED.2 subscribes the same
            # symbol+interval twice and the second registration used to
            # overwrite the first. Three-tuple, one entry per subscription.
            self.symbol_map[(self.dx_symbol, tf, False)] = INSTRUMENT
        for tf in VIX_INTERVALS:
            self.subs.append((VIX_SYMBOL, tf, _backfill_start(tf), False))
            self.symbol_map[(VIX_SYMBOL, tf, False)] = "VIX"

        # ── FEED.2 (2026-08-15) — THE OVERNIGHT STREAM ───────────────────────
        # ⚠️ THE TAPE WAS NEVER UNAVAILABLE. WE WERE ASKING DXFEED TO EXCLUDE IT.
        # `subscribe_candle(..., extended_trading_hours=False)` is the SDK
        # DEFAULT, and when it is False the SDK appends **`tho=true`**
        # (trading-hours-only) to the symbol: `QQQ{=1h,tho=true}`. Every
        # subscription this feed has ever made carried it.
        #
        # That single default is what produced `ext=0` on 28 of 29 boxes, an
        # RTH-only 1h store (252 bars = 36 sessions x 7), and LIQ.6's Asia and
        # London sections having nothing to build from. It is NOT the session
        # guard, NOT the warm lead, NOT S3, NOT an entitlement tier.
        #
        # ⚠️ A SEPARATE STREAM, NOT A FLAG ON THE EXISTING 1h. `1h` is read by
        # structure_analyzer's swings and S/R, by the pitchfork and its observer,
        # and by entry_snapshot. Flipping it in place would silently rebuild all
        # of them on 24h bars — the pitchfork is a v4.0 milestone and its forks
        # would change shape overnight with nothing announcing it. This lands
        # under its OWN store symbol so **no existing consumer moves at all**;
        # only the named-level frame reads it.
        if EXT_1H_ENABLED:
            self.subs.append((self.dx_symbol, EXT_INTERVAL,
                              _backfill_start(EXT_INTERVAL), True))
            self.symbol_map[(self.dx_symbol, EXT_INTERVAL, True)] = EXT_STORE_SYMBOL
        # ── v3.16 — COLLISION GUARD. REFUSE TO START ON A DUPLICATE ROUTE ───
        # The FEED.2 defect was not that someone wrote a wrong key; it was that
        # TWO subscriptions could legally resolve to the SAME store target and
        # nothing said so. Six days of stale 1h structure followed, fleet-wide,
        # with no error. A route table that can silently lose an entry must not
        # be allowed to start.
        # Two invariants, both cheap and both checked before a socket opens:
        #   1. no two SUBSCRIPTIONS share a map key (one would overwrite the
        #      other, which is exactly what happened)
        #   2. no two map keys point at the SAME (store_symbol, interval) —
        #      two live streams writing one table is a silent merge
        _seen_keys, _seen_targets = set(), {}
        for (_ds, _tf, _st, _ex) in self.subs:
            _k = (_ds, _tf, bool(_ex))
            if _k in _seen_keys:
                raise RuntimeError(
                    f"candle_feed: DUPLICATE SUBSCRIPTION KEY {_k} — two "
                    f"subscriptions resolve to one route and one would "
                    f"silently overwrite the other (the FEED.2 defect, "
                    f"2026-08-14..20). Refusing to start.")
            _seen_keys.add(_k)
            _tgt = (self.symbol_map.get(_k), _tf)
            if _tgt[0] is None:
                raise RuntimeError(
                    f"candle_feed: SUBSCRIPTION {_k} HAS NO ROUTE in "
                    f"symbol_map — its candles would be dropped. Refusing "
                    f"to start.")
            if _tgt in _seen_targets:
                raise RuntimeError(
                    f"candle_feed: TWO SUBSCRIPTIONS WRITE {_tgt} — "
                    f"{_seen_targets[_tgt]} and {_k}. One stream would "
                    f"silently merge into the other's table. Refusing to "
                    f"start.")
            _seen_targets[_tgt] = _k
        logger.info("candle_feed routes verified: %d subscription(s), "
                    "%d distinct store target(s)",
                    len(_seen_keys), len(_seen_targets))

        # buffer[(store_symbol, interval)][ts_ms] = row tuple
        self.buffer: Dict[Tuple[str, str], Dict[int, Tuple]] = {}
        self._unmapped_seen: set = set()   # v3.7: warn-once on unmapped candles
        # v3.17 — non-RTH bars SEGREGATED per (symbol, interval). Warn ONCE
        # then count: a per-bar warning during a 15-day backfill buries the log.
        self._rth_moved: Dict[Tuple[str, str], int] = {}
        self.backfill_logged: Dict[Tuple[str, str], bool] = {}
        # ── v3.4 chain-marks state (reset on every socket (re)connect) ────────
        self._chain_expiry: str = ""
        self._chain_subscribed: set = set()
        self._quotes_buf: Dict[str, tuple] = {}    # sym -> (sym,bid,ask,epoch)
        self._greeks_buf: Dict[str, tuple] = {}    # sym -> (sym,d,g,t,v,iv,epoch)

    def _interval_of(self, event_symbol: str) -> Optional[str]:
        """Map DXFeed's echoed candle symbol back to OUR config timeframe key.

        'AAPL{=5m}'            -> '5m'
        'AAPL{=5m,tho=true}'   -> '5m'    (attributes stripped)
        'AAPL{=m,tho=true}'    -> '1m'    (DXFeed canonicalizes 1m -> m)
        'AAPL{=h,tho=true}'    -> '1h'
        'AAPL{=d,tho=true}'    -> '1d'

        v3.7 — TWO bugs that each SILENTLY DROP EVERY CANDLE (feed stays 'active',
        authenticated, streaming, store takes ZERO writes; bots read yesterday's
        bars; no ORB range for today; fleet EXPIRED/UNKNOWN; not one error logged
        — recurred every morning 07-13/14/15):
        (1) DXFeed echoes the symbol back WITH ATTRIBUTES ('...,tho=true'); the
            old parser returned '5m,tho=true' and never matched symbol_map.
        (2) DXFeed CANONICALIZES a leading 1: we subscribe '1m'/'1h'/'1d', it
            echoes 'm'/'h'/'d'. 1m is what fetch_quote() reads (the bot's price).
        """
        if "{=" not in (event_symbol or ""):
            return None
        token = event_symbol.split("{=", 1)[1].rstrip("}")
        token = token.split(",", 1)[0].strip()      # drop ',tho=true' etc.
        return {"m": "1m", "h": "1h", "d": "1d", "s": "1s"}.get(token, token)

    @staticmethod
    def _is_ext_of(event_symbol: str) -> bool:
        """v3.16 — IS THIS ECHO FROM THE EXTENDED-HOURS SUBSCRIPTION?

        🔴 THE BUG THIS EXISTS FOR. FEED.2 subscribes the SAME dx symbol at the
        SAME interval twice — once RTH-only, once with extended_trading_hours —
        and registered both in `symbol_map` under `(dx_symbol, interval)`. The
        keys are identical, so the second assignment silently overwrote the
        first and EVERY 1h candle was routed to the EXT store symbol. Measured
        2026-08-20 across the fleet: plain `QQQ`/`SPX` 1h frozen at 2026-08-14
        while `*_EXT` 1h was current — SIX DAYS of stale higher-timeframe
        structure feeding structure_analyzer's swings and S/R, the pitchfork
        and its observer, and entry_snapshot. Nothing raised; BARS_STALE warned
        every five minutes with `refused=False` and the bots kept trading on
        08-14 bars.
        `tho=true` is the ONLY thing that distinguishes the two echoes, and
        `_interval_of` deliberately discards it. So read it here instead: the
        attribute the parser drops is exactly the attribute the router needs.
        """
        if "{=" not in (event_symbol or ""):
            return False
        attrs = event_symbol.split("{=", 1)[1].rstrip("}")
        return "tho=true" in attrs.replace(" ", "").lower()

    def _on_candle(self, c: Candle):
        ev_sym = getattr(c, "event_symbol", "")
        base = _base_symbol(ev_sym)
        interval = self._interval_of(ev_sym) or ""
        is_ext = self._is_ext_of(ev_sym)
        key_sym = self.symbol_map.get((base, interval, is_ext))
        if key_sym is None:
            # v3.7: NEVER drop a candle silently. This branch swallowed the whole
            # feed on 07-13/14/15 (unparsed interval) with no log anywhere. Warn
            # once per distinct unmapped key so a future echo-format change is
            # visible within one line instead of a wasted session.
            if ev_sym and (base, interval, is_ext) not in self._unmapped_seen:
                self._unmapped_seen.add((base, interval, is_ext))
                logger.warning(
                    "DROPPING candles: event_symbol=%r -> (base=%r, interval=%r, "
                    "ext=%r) NOT in symbol_map %r — storing nothing for it",
                    ev_sym, base, interval, is_ext,
                    sorted(self.symbol_map.keys()))
            return
        if c.time is None or c.open is None:
            return

        # ── POISON GUARD (v3.2) ───────────────────────────────────────────────
        # DXFeed intermittently emits a junk candle: timestamp at the signed
        # 32-bit rollover (2147483648xxx ms => year 2038) with all prices 0.0.
        # Observed live on GOOGL 2026-07-13 (1m, then 15m). It is fatal
        # downstream: fetch_quote() sorts by ts DESC, so the 2038 row wins, its
        # age computes NEGATIVE (passes the freshness check), and it returns
        # close=0.0. run_analysis() treats 0.0 as falsy -> "Could not fetch
        # current price" -> the tick loop dies EVERY TICK while the unit still
        # reports ACTIVE. Silent, total. Reject it at the door: bad data must
        # never enter the store.
        try:
            ts_ms = int(c.time)
            o, h, l, cl = float(c.open), float(c.high), float(c.low), float(c.close)
        except (TypeError, ValueError):
            return

        if not (TS_MS_MIN <= ts_ms <= _ts_ms_max()):
            logger.warning(
                "REJECTED poison candle %s %s: insane ts=%d (%.1f) — outside sane window",
                key_sym, interval, ts_ms, ts_ms / 1000.0)
            return
        if o <= 0 or h <= 0 or l <= 0 or cl <= 0:
            logger.warning(
                "REJECTED poison candle %s %s ts=%d: non-positive price "
                "(o=%.4f h=%.4f l=%.4f c=%.4f)", key_sym, interval, ts_ms, o, h, l, cl)
            return

        # ── RTH GUARD (v3.17) ────────────────────────────────────────────────
        # 🔴 THE SECOND HALF OF THE FEED.2 DEFECT. Streaming routes correctly
        # after v3.16, but a RESTART's backfill asked DXFeed for plain-symbol
        # history and got 24-HOUR BARS back — ~12 bars/hour overnight against
        # 38–39 in RTH, reaching ~15 days back (the 08-05 boundary). SPX proves
        # it is real extended-hours data and not a timezone artifact: an index
        # has no overnight session, so it shows hours 13–20 UTC only and had
        # nothing to contaminate.
        # ⚠️ WORSE THAN THE ORIGINAL HOLE. A gap announces itself; this does
        # not. The series CHANGES CHARACTER MID-STREAM — 07-31 is RTH-only,
        # 08-19 is 24-hour — with nothing marking the seam, so swings, S/R and
        # the hourly pitchfork read a discontinuity they cannot detect.
        # THE FLAG IS NOT ENOUGH. `extended_trading_hours=False` is passed on
        # the subscription and the vendor returned 24h history anyway, so the
        # guarantee has to live HERE, at the write, where it is ours to
        # enforce: a PLAIN-symbol route accepts only RTH bars. `*_EXT` routes
        # are untouched — carrying overnight is their entire purpose.
        if not _is_ext_route(key_sym) and not _within_rth(ts_ms, interval):
            # SEGREGATE, DO NOT DROP. For 5m/15m/1m there is NO extended
            # stream — EXT_INTERVAL is 1h only — so an overnight bar arriving
            # here is the ONLY copy that will ever exist, and DXFeed history is
            # use-it-or-lose-it. Discarding it to protect the RTH series would
            # trade one irreversible loss for another.
            # The plain series stays RTH-pure (which is what structure_analyzer
            # at weight 2.0, the pitchfork's 1h fractals, trend_engine's 0.20
            # context vote and entry_snapshot were all built to read), and the
            # bar is still stored — under the symbol that means "this carries
            # overnight". Nothing RTH-scoped reads it; everything can query it.
            alt = f"{key_sym}_EXT"
            self._rth_moved[(key_sym, interval)] = \
                self._rth_moved.get((key_sym, interval), 0) + 1
            if self._rth_moved[(key_sym, interval)] == 1:
                logger.warning(
                    "RTH GUARD: non-RTH bars on the plain route for %s %s "
                    "(first ts=%d) — SEGREGATING to %s so the RTH series stays "
                    "pure and no bar is lost. Counting silently from here.",
                    key_sym, interval, ts_ms, alt)
            key_sym = alt

        row = (key_sym, interval, ts_ms, o, h, l, cl,
               float(getattr(c, "volume", 0) or 0))
        self.buffer[(key_sym, interval)] = self.buffer.get((key_sym, interval), {})
        self.buffer[(key_sym, interval)][ts_ms] = row

    # ── v3.4: chain-marks handlers ─────────────────────────────────────────
    def _on_quote(self, q: Quote):
        sym = getattr(q, "event_symbol", "") or ""
        if not sym:
            return
        try:
            bid = float(q.bid_price or 0)
            ask = float(q.ask_price or 0)
        except (TypeError, ValueError):
            return
        self._quotes_buf[sym] = (sym, bid, ask, _time.time())

    def _on_greeks(self, g: Greeks):
        sym = getattr(g, "event_symbol", "") or ""
        if not sym:
            return
        try:
            row = (sym, float(g.delta or 0), float(g.gamma or 0),
                   float(g.theta or 0), float(g.vega or 0),
                   float(g.volatility or 0), _time.time())
        except (TypeError, ValueError):
            return
        self._greeks_buf[sym] = row

    async def _reconcile_chain_subs(self, streamer):
        """Every flush cycle: make the socket's Greeks/Quote subscriptions match
        what the bot requested via chain_subs. Expiry rollover unsubscribes all
        and clears the marks table (yesterday's 0DTE symbols are dead air)."""
        expiry, symbols = self.store.read_chain_subs()
        if not symbols:
            return
        if expiry != self._chain_expiry:
            if self._chain_subscribed:
                logger.info("chain marks: expiry rollover %s -> %s — resubscribing",
                            self._chain_expiry or "(none)", expiry)
                await streamer.unsubscribe_all(Greeks)
                await streamer.unsubscribe_all(Quote)
            self._chain_subscribed.clear()
            self._quotes_buf.clear()
            self._greeks_buf.clear()
            self.store.clear_chain_marks()
            self._chain_expiry = expiry
        new = [s for s in symbols if s not in self._chain_subscribed]
        if new:
            # v3.5: CHUNKED subscribes. An SPX 0DTE chain is hundreds of
            # strikes; one giant subscribe frame risks a websocket 1009
            # (message too long) that would bounce the ENTIRE socket —
            # candles included. 75 symbols per frame is comfortably small.
            for i in range(0, len(new), 75):
                chunk = new[i:i + 75]
                await streamer.subscribe(Greeks, chunk)
                await streamer.subscribe(Quote,  chunk)
            self._chain_subscribed.update(new)
            logger.info("chain marks: subscribed %d new symbols (%d total, expiry %s)",
                        len(new), len(self._chain_subscribed), expiry)

    def _flush(self):
        rows: List[Tuple] = []
        for bucket in self.buffer.values():
            rows.extend(bucket.values())
        self.buffer = {}
        self.store.upsert_candles(rows)
        # v3.4: chain marks ride the same flush cadence
        q, g = list(self._quotes_buf.values()), list(self._greeks_buf.values())
        self._quotes_buf.clear()
        self._greeks_buf.clear()
        self.store.upsert_chain_quotes(q)
        self.store.upsert_chain_greeks(g)
        self.store.heartbeat()
        self.store.commit()
        return len(rows) + len(q) + len(g)

    def _log_backfill_depth(self):
        """One-time per (symbol, interval): report depth vs required count so
        entitlement gaps surface in the journal (FIRST-RUN CHECKLIST #1)."""
        for (dx_sym, tf, _start, _ext) in self.subs:
            sym = self.symbol_map[(dx_sym, tf, bool(_ext))]
            if self.backfill_logged.get((sym, tf)):
                continue
            n = self.store.bar_count(sym, tf)
            need = TIMEFRAMES.get(tf, {}).get("candles", 0) if sym == INSTRUMENT else 1
            level = logging.INFO if n >= need else logging.WARNING
            logger.log(level, "backfill %s %s: %d bars in store (need %d)%s",
                       sym, tf, n, need, "" if n >= need else "  << SHORT — check entitlement")
            self.backfill_logged[(sym, tf)] = True

    @staticmethod
    def _feed_stood_down() -> bool:
        """Should this run stand down? v4.3: MAINTENANCE, and nothing else.

        ONE predicate, TWO call sites (the reconnect gate and the RTH-over
        break). v3.9 wrote the same condition inline in both places and v3.10
        had to patch both; a third caller would have had to remember a third
        time. It is a method so the two can never disagree again.

        THE DISTINCTION IS PURPOSE, NOT TIME — which is the whole lesson of
        2026-08-01..08-04. What the gate protects against is a box HOLDING a
        live DXLink subscription when there is no session to serve it: the
        maintenance wake that put 29 boxes on the wire for work needing no
        market data. A `--once` run holds nothing. It connects, pulls HISTORY
        from 09:30, flushes and exits, and history does not stop existing at
        16:00 — so gating it on the clock blocked the ONLY path the EOD candle
        retrieval has, silently, for two sessions.

        SERVICE MODE (once=False) is unchanged from v3.9 in every respect.

        ── FEED.1 (2026-08-15) — THE THIRD PURPOSE ────────────────────────────
        MAINTENANCE is HARD OFF and overrides everything, `--once` included.
        It exists because the operator needs a window where all 29 boxes can be
        up for fleet updates with nothing on the wire — and that CANNOT be a
        clock rule, because the overnight capture pass runs at the same hours
        and wants the opposite.

        ⚠️ IT ANNOUNCES ITSELF AT WARNING. The 2026-08-03/04 loss was a silent
        gate: `Feed idle — outside RTH` at INFO, then `0 bars`, then fourteen
        38-byte header-only CSVs, and DXFeed history is same-evening only so
        both sessions are gone. **A suppressed run must never be mistakable for
        a failed fetch**, so this says the mode by name and says the data is
        NOT being collected.
        """
        if _maintenance_now():
            if not getattr(CandleFeed, "_maint_said", False):
                CandleFeed._maint_said = True
                # v4.3 — the trailing "%s" arg used to read
                # `"including this --once run" if once else "service mode"`.
                # `once` is no longer a parameter, so that line raised
                # NameError the first time maintenance was declared — and
                # `import candle_feed` could not see it, because the name is
                # only resolved when this branch RUNS. Found by
                # tests/check_feed_always_on.py driving the predicate, which is
                # the whole argument for executing checks rather than reading
                # source (WORKING_AGREEMENT 21).
                logger.warning(
                    "[feed-mode] MAINTENANCE - standing down completely. NO "
                    "candles will be collected on this box until OT_FEED_MODE "
                    "is cleared. This is DELIBERATE, not a fetch failure; if "
                    "you expected tape, the mode is wrong.")
            return True
        # v4.3 — THE RTH CLAUSE IS GONE. It used to read
        #     `return not is_rth() and not once`
        # and its own rationale above is what retired it: the gate existed so a
        # MAINTENANCE wake could not put 29 BOXES on the wire at once. The fleet
        # is 15 and they are the same 15 every day; a normal session already
        # carried ~20 boxes on this feed without strain, so the crowd the gate
        # was sized for no longer exists. Operator, 2026-08-20: boxes subscribe
        # whenever they are up.
        #
        # ⚠️ MAINTENANCE SURVIVES, AND IT IS NOW THE ONLY REASON TO STAND DOWN.
        # It was never the clock rule — it is the window where the fleet can be
        # up with nothing on the wire, and it must stay expressible.
        # ⚠️ `once` IS NO LONGER A PARAMETER. It existed to exempt the one-shot
        # EOD pull from a CLOCK rule; with no clock rule there is nothing to be
        # exempt from, and maintenance overrode it anyway. A parameter that can
        # no longer change the answer is a parameter that misleads the reader.
        return False

    async def run(self, once: bool = False):
        session = get_session()
        backoff = RECONNECT_MIN_S
        while True:
            # ── FEED STAND-DOWN GATE ─────────────────────────────────────────
            # HISTORY, kept because it is the reasoning and not the rule.
            # 2026-08-01 this became an RTH gate: the loop had no time gate at
            # all (`Restart=always`, no timer), so while a box was UP the feed
            # subscribed continuously — invisible on a normal day because
            # phase_report stopped the instances at EOD, but it meant every
            # MAINTENANCE wake put 29 boxes back on the wire at once for work
            # needing no market data. FEED.1 then added maintenance as a third
            # purpose, and v3.9/v3.10 had to exempt `--once` from the clock rule
            # after two sessions of tape were lost to header-only CSVs.
            #
            # v4.3 (2026-08-20) RETIRES THE CLOCK RULE ENTIRELY. The crowd it
            # was sized for is gone: 15 boxes, the same 15 daily. What remains
            # is MAINTENANCE — a purpose, not a time — which is exactly what
            # `_feed_stood_down`'s own doctrine said the distinction always was.
            #
            # ⚠️ WHAT HOLDING THE SOCKET 24h DOES AND DOES NOT DO.
            # It does NOT contaminate the RTH series: the v4.2 write guard
            # routes every non-RTH bar to <SYM>_EXT, for EVERY interval, so
            # overnight 1m/5m/15m are stored and segregated rather than dropped
            # or merged. It does NOT add chain snapshots outside RTH:
            # `analysis.chain_snapshot.snapshot()` takes the chain as an
            # ARGUMENT and is called from main.py's tick loop, which returns
            # early on `not is_rth()` — so chain archival is still RTH-only and
            # this change cannot alter it in either direction.
            # ⚠️ SPX HAS NO OVERNIGHT SESSION. An index producing nothing
            # between 16:00 and 09:30 is correct, not a fetch failure — it is
            # the same control that proved the v4.2 contamination was real.
            # v4.3 — MAINTENANCE ONLY. The sleep-until-open block that lived
            # here is deleted rather than left dead: a branch that can no longer
            # run still reads as live to anyone auditing the file.
            #
            # ⚠️ AND IT FIXES A LATENT DEFECT ON THE WAY OUT, stated because it
            # is a behaviour change and not merely a deletion. The old block
            # slept only while `seconds_until_rth_open() > FEED_WARM_LEAD_S`,
            # and that function RETURNS 0 DURING RTH — so maintenance declared
            # inside the session fell straight through and connected anyway.
            # The hard-off was silently defeated in exactly the hours a fleet
            # update is most disruptive. Standing down is now unconditional.
            if self._feed_stood_down():
                await asyncio.sleep(60)
                continue
            try:
                async with DXLinkStreamer(session) as streamer:
                    # v3.4: fresh socket — chain subscriptions must be rebuilt
                    self._chain_expiry = ""
                    self._chain_subscribed.clear()
                    # v3.8: subscribe each (symbol, tf) INDEPENDENTLY. A single
                    # failing subscribe_candle used to throw out of the whole
                    # `async with`, killing the ENTIRE stream — so one bad symbol
                    # or timeframe (e.g. an entitlement gap on XOM) took down all
                    # candles, for two days, with only a wrapped "unhandled errors
                    # in a TaskGroup" to show for it. Now a failure is logged with
                    # its REAL cause (see _explain_exc) and skipped.
                    ok_subs = 0
                    for (dx_sym, tf, start, ext) in self.subs:
                        try:
                            await streamer.subscribe_candle(
                                [dx_sym], tf, start_time=start,
                                extended_trading_hours=ext)
                            logger.info("subscribed %s %s from %s%s", dx_sym, tf,
                                        start.isoformat(),
                                        "  [EXTENDED HOURS]" if ext else "")
                            ok_subs += 1
                        except Exception as sub_e:
                            logger.error("SUBSCRIBE FAILED %s %s: %s — continuing without it",
                                         dx_sym, tf, _explain_exc(sub_e))
                    if ok_subs == 0:
                        raise RuntimeError("no candle subscriptions succeeded")
                    logger.info("%d/%d candle subscriptions live", ok_subs, len(self.subs))
                    await self._reconcile_chain_subs(streamer)
                    backoff = RECONNECT_MIN_S
                    last_flush = 0.0
                    last_prune = _time.time()
                    quiet_since: Optional[float] = None
                    while True:
                        try:
                            c = await asyncio.wait_for(streamer.get_event(Candle), timeout=1.0)
                            self._on_candle(c)
                            quiet_since = None
                        except asyncio.TimeoutError:
                            if quiet_since is None:
                                quiet_since = _time.monotonic()
                        # v3.4: drain any queued Greeks/Quote events, non-blocking
                        while True:
                            g = streamer.get_event_nowait(Greeks)
                            if g is None:
                                break
                            self._on_greeks(g)
                        while True:
                            q = streamer.get_event_nowait(Quote)
                            if q is None:
                                break
                            self._on_quote(q)
                        now = _time.monotonic()
                        if now - last_flush >= FLUSH_INTERVAL_S:
                            await self._reconcile_chain_subs(streamer)
                            n = self._flush()
                            last_flush = now
                            if n:
                                logger.debug("flushed %d bars", n)

                            # v3.9 — SESSION IS OVER: drop the socket. The gate at
                            # the top of the reconnect loop only decides whether
                            # to CONNECT; without this the feed would stream on
                            # past 16:00 for as long as the box happened to stay
                            # up. That is the case that matters — the operator
                            # must be able to FORGET a box is up and have it not
                            # be a problem, which is this project's standing rule
                            # about anything depending on someone remembering.
                            # Rides the existing flush cadence rather than adding
                            # a timer: we are already here, once per cycle.
                            # Flushed first (above), so no buffered bar is lost.
                            # v3.9 — `and not once` here too, and this one is the
                            # blocker a naive fix would have missed. This break
                            # sits ABOVE the --once drain-exit, so a one-shot run
                            # outside RTH would connect, break out on its first
                            # flush cycle, return to the outer loop, hit the gate
                            # again and sleep — the same hang, one layer down,
                            # with the backfill still undrained. Both sites had
                            # to move together or neither works.
                            # v4.3 — no longer an "RTH over" break: the socket
                            # is held through the close. This fires only when
                            # MAINTENANCE is declared mid-run, which must take
                            # effect without waiting for a restart.
                            if self._feed_stood_down():
                                logger.warning(
                                    "MAINTENANCE declared — closing DXLink "
                                    "socket and releasing all subscriptions. "
                                    "NO candles collected until OT_FEED_MODE "
                                    "is cleared."
                                )
                                break
                            self._log_backfill_depth()
                            if once and quiet_since is not None and (now - quiet_since) > 8.0:
                                logger.info("--once: backfill drained, exiting")
                                return
                        # ── FEED.3 (2026-08-15) — PRUNING IS OFF BY DEFAULT ──
                        # ⚠️ THE BOUND WAS SIZED FOR THE LIVE LOOP AND KEPT
                        # SILENTLY CONSTRAINING ANALYTICAL CONSUMERS THAT
                        # ARRIVED LATER. It has now bitten twice: PF.2 found the
                        # boxes held 84 daily bars while the engine was handed
                        # 10 ("the history was never missing - the frame was"),
                        # and LIQ.6's 10-day section lookback landed on exactly
                        # the 240-row 1h ceiling with ZERO margin.
                        #
                        # AND IT WAS NEVER BUYING ANYTHING. Measured: a FULL
                        # YEAR of every interval, extended hours, is **54 MB per
                        # box** - on an 8 GB root. Ten days is 1.5 MB. The
                        # pruner was tidiness, not capacity.
                        #
                        # Operator's call: no pruning. The local store keeps
                        # what it collects; S3 is the archive and the weekend
                        # reporting reads the bucket, so the box no longer has
                        # to be the deep copy of anything.
                        # ⚠️ THE POISON PURGE IS UNTOUCHED AND MUST STAY - it
                        # deletes BAD rows (non-positive prices, 2038-stamped
                        # DXFeed rollover junk), not OLD ones. Different method,
                        # different purpose.
                        if PRUNE_KEEP_ROWS and _time.time() - last_prune >= PRUNE_EVERY_S:
                            for (dx_sym, tf, _s, _e) in self.subs:
                                sym = self.symbol_map[(dx_sym, tf, bool(_e))]
                                self.store.prune(sym, tf, PRUNE_KEEP_ROWS)
                            self.store.commit()
                            last_prune = _time.time()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._flush()
                # v3.8: UNWRAP. asyncio TaskGroup raises an ExceptionGroup whose
                # str() is only "unhandled errors in a TaskGroup (1 sub-exception)"
                # — the real DXFeed cause is in .exceptions and was thrown away,
                # leaving XOM in a 60s reconnect loop with NO diagnosable reason
                # for two days (07-13 -> 07-15).
                logger.error("feed stream error: %s — reconnecting in %ds",
                             _explain_exc(e), backoff)
                logger.debug("feed stream traceback:\n%s",
                             "".join(traceback.format_exception(type(e), e, e.__traceback__)))
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_MAX_S)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="backfill, flush, exit (smoke test)")
    ap.add_argument("--db", default=None, help="override store path")
    args = ap.parse_args()

    if args.db:
        os.environ["OT_FEED_DB"] = args.db
    store = FeedStore(feed_db_path())
    logger.info("candle_feed v3.8 — store=%s symbol=%s (dxfeed=%s) vix=%s",
                feed_db_path(), INSTRUMENT, _dxfeed_symbol(), VIX_SYMBOL)
    store.purge_poison()   # v3.2: self-heal any pre-existing poison rows

    feed = CandleFeed(store)
    loop = get_loop()
    fut = asyncio.run_coroutine_threadsafe(feed.run(once=args.once), loop)
    try:
        fut.result()          # blocks for service lifetime
    except KeyboardInterrupt:
        fut.cancel()
    finally:
        store.close()


if __name__ == "__main__":
    main()
