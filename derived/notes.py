"""
derived/notes.py  v4.0
Owns `strategy_note`. What each engine SAW, every time it looked.

v4.0  2026-08-25  Operator: the derived data should "start by informing, but
not changing anything — we're just taking notes. We will be fitting these
trades when we have enough data to do so."

🔴 THE POINT IS THE REJECTIONS. `fire_snapshot` captures the world at the
instant a trade FIRED — but a fired trade is a biased sample of what the
engine saw. Fitting needs both arms: the setups taken AND the setups declined,
with the same derived vector attached to each.

⚠️ ON 2026-08-21 THE FLEET DECLINED EVERY SETUP ON EVERY BOX ALL SESSION AND
COULD NOT SAY WHY. The signal journal held exactly one event type all day;
every other refusal was a debug line. This table is the fix for that class:
one row per strategy per evaluation, with the reason and the evidence.

⚠️ NOTHING HERE CHANGES A DECISION. The note is written AFTER the strategy has
already decided. A note that could alter an outcome would make the record a
participant in what it is supposed to be measuring.

⚠️ EACH STRATEGY GETS THE VECTOR THAT MATTERS TO IT, not a uniform dump. From
the analysis in docs/WHAT_THE_DATA_TELLS_EACH_TRADE.md:
  · sweep     — aggression AT THE REJECTION replaces pierce-depth as a proxy
                for whether the level was actually defended
  · runaway   — is the proven move being BOUGHT, or just drifting?
  · condor    — VRP (is premium rich?) and EM vs the fork channel
  · butterfly — charm IS the trade; gamma flow says if the pin is building
  · ORB       — RECORD ONLY. Its 96% record exists because it never asked
                permission. Nothing here may ever gate it.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from derived.base import DerivedEngine

logger = logging.getLogger(__name__)


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


class NoteWriter:
    """Writes one row per strategy evaluation. Never raises, never decides."""

    def __init__(self, store=None, symbol: str = ""):
        self._store = store
        self.symbol = symbol
        self._made = False

    def _ensure(self):
        if self._made or self._store is None:
            return
        try:
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_note (
                    ts_epoch REAL NOT NULL,
                    symbol   TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    fired    INTEGER NOT NULL,
                    trade_id TEXT,
                    outcome  TEXT,
                    price    REAL,
                    payload  TEXT NOT NULL,
                    PRIMARY KEY (ts_epoch, symbol, strategy));""")
            self._store.conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_note_strat "
                "ON strategy_note(strategy, ts_epoch)")
            self._made = True
        except Exception as exc:                                # noqa: BLE001
            logger.debug("strategy_note table: %s", exc)

    # ── the per-strategy vectors ────────────────────────────────────────
    @staticmethod
    def _common(ctx: dict) -> dict:
        """What every strategy's note carries, regardless of type."""
        return {
            "price": _f(ctx.get("price")),
            "adx": _f(getattr(ctx.get("trend"), "primary_adx", None)),
            "atr_normalized": _f(getattr(ctx.get("vol"), "atr_normalized", None)),
            "vwap": _f(getattr(ctx.get("vol"), "vwap", None)),
            "session_fraction_remaining": _f(ctx.get("session_fraction_remaining")),
            "expected_move_iv": _f(ctx.get("expected_move_iv")),
            "expected_move_straddle": _f(ctx.get("expected_move_straddle")),
            "realised_vol_cc": _f(ctx.get("realised_vol_cc")),
            "realised_vol_parkinson": _f(ctx.get("realised_vol_parkinson")),
            "variance_risk_premium": _f(ctx.get("variance_risk_premium")),
            "atm_iv": _f(ctx.get("atm_iv")),
            "iv_slope": _f(ctx.get("iv_slope")),
            "charm": _f(ctx.get("charm")),
            "vanna": _f(ctx.get("vanna")),
            "gex": _f(ctx.get("gex")),
            "levels": ctx.get("levels"),
            # ⚠️ CHARACTER IS CONTEXT ON THE NOTE, NOT A FACTOR IN IT. It says
            # what the tape was doing when this engine looked — it does not
            # score, weight or gate anything.
            "character": ctx.get("character"),
            "character_held_s": ctx.get("character_held_s"),
            "gap_pct": _f((ctx.get("gap") or {}).get("gap_pct")),
            "gap_class": (ctx.get("gap") or {}).get("gap_class"),
        }

    def _specific(self, strategy: str, ctx: dict) -> dict:
        """The vector this particular engine's success actually depends on."""
        s = (strategy or "").lower()
        conn = ctx.get("_flow_conn")
        out: dict = {}
        try:
            from analysis.order_flow import aggression, pressure_into_level
        except Exception:                                       # noqa: BLE001
            return out

        if "sweep" in s:
            # 🔴 The spec's sharpest finding is a PROXY: "a deep pierce means a
            # WEAK level, not a strong rejection — price went that far because
            # it was WILLING TO." Aggression at the level measures the thing
            # the pierce ceiling was approximating.
            lvl = _f(ctx.get("swept_level_price"))
            kind = ctx.get("swept_level_kind") or "resistance"
            if conn is not None and lvl:
                out["defence"] = pressure_into_level(conn, self.symbol, lvl, kind)
            out["swept_level_price"] = lvl
            out["swept_level_touches"] = ctx.get("swept_level_touches")

        elif "runaway" in s or "continuation" in s:
            # Is the proven move being BOUGHT, or merely drifting? "In
            # evidence" has until now meant only that price moved.
            if conn is not None:
                out["tape"] = aggression(conn, self.symbol)
            out["prev_close"] = _f(ctx.get("prev_close"))

        elif "condor" in s:
            # VRP is the condor's core question — short vol with no measure of
            # whether vol is rich. Plus the channel against the expected move.
            f = ctx.get("fork_rails") or {}
            up, lo = _f(f.get("upper")), _f(f.get("lower"))
            out["fork_upper"], out["fork_lower"] = up, lo
            out["fork_reject_reason"] = f.get("reject_reason")
            if up and lo:
                out["channel_width"] = up - lo
                em = _f(ctx.get("expected_move_iv"))
                # >1 means the market prices LESS movement than the structure
                # allows — the shorts can sit inside the rails with room.
                out["channel_over_em"] = ((up - lo) / em) if em else None

        elif "butterfly" in s or "gex" in s:
            # Charm IS this trade. Distance is the edge — the apex's distance
            # as a fraction of EM is the asymmetry the spec is built on.
            pin = _f(ctx.get("gex_pin"))
            px, em = _f(ctx.get("price")), _f(ctx.get("expected_move_iv"))
            out["gex_pin"] = pin
            out["pin_distance_over_em"] = (
                abs(pin - px) / em if (pin and px and em) else None)
            out["pin_concentration"] = _f(ctx.get("pin_concentration"))

        elif "orb" in s:
            # ⚠️ RECORD ONLY. 96% win / +$30,696 / worst -$16, and the spec is
            # explicit that it worked BECAUSE it consulted nothing. Nothing in
            # this note may ever become a gate on it.
            if conn is not None:
                out["break_tape"] = aggression(conn, self.symbol, 180.0)
            out["orb_state"] = str(getattr(ctx.get("orb"), "state", "") or "")
        return out

    def write(self, strategy: str, ctx: dict, fired: bool,
              outcome: str = "", trade_id: str = "") -> int:
        """One note. Called AFTER the strategy decided. Never raises."""
        if self._store is None:
            return 0
        try:
            self._ensure()
            payload = self._common(ctx)
            payload["specific"] = self._specific(strategy, ctx)
            self._store.conn.execute(
                "INSERT OR IGNORE INTO strategy_note (ts_epoch, symbol,"
                " strategy, fired, trade_id, outcome, price, payload)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (time.time(), self.symbol, strategy, 1 if fired else 0,
                 trade_id or None, outcome or None, _f(ctx.get("price")),
                 json.dumps(payload, default=str)))
            return 1
        except Exception as exc:                                # noqa: BLE001
            logger.debug("[notes] %s: %s", strategy, exc)
            return 0


class NotesEngine(DerivedEngine):
    """Registry wrapper. Event-driven — `derive` does nothing per tick.

    ⚠️ THE WRITER IS REACHED VIA `.writer` FROM main's dispatch hook, because a
    note is written per STRATEGY EVALUATION, not per tick. Modelling it as a
    tick engine would either miss evaluations or invent them.
    """

    name = "notes"
    table = "strategy_note"

    def __init__(self, store=None, symbol: str = ""):
        super().__init__(store)
        self.writer = NoteWriter(store, symbol)

    def derive(self, ctx: dict) -> int:
        return 0
