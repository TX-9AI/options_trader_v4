"""
analysis/level_test.py  v1.0
v1.0  2026-08-26  r147 — THE FOUR STATES OF A LEVEL UNDER TEST, for the condor's
      second leg. Operator, 2026-08-26: *"If the complementary vertical spread
      becomes available on mapper, the plan should account for it and confirm
      a REJECTION of the level before deploying the second leg. ACCEPTANCE of
      the level invalidates it and the plan should start looking at the next
      available level … We would not sell a complementary spread on a level
      that's getting breached."*

ONE DEFINITION OF REJECTION AND ACCEPTANCE, FLEET-WIDE. This reads the same
facts the sweep detector reads (`analysis/liquidity_mapper.py`: a wick through
is a TEST, a close back inside is a RECLAIM, `_ACCEPT_CLOSES` closes beyond is
ACCEPTANCE — "bodies decide, wicks test"). It does not invent a second rule.

    UNTESTED   price has not reached the level since arming
    BREACHED   price is THROUGH the level right now — the last close is on the
               wrong side and acceptance is not yet reached. Unresolved. NO FIRE.
    REJECTED   the level was tested (a wick through is fine; depth is an
               attribute, not a gate) and the LAST close is back on the inside
    ACCEPTED   >= ACCEPT_CLOSES closes beyond. The level is FINISHED for the
               session — the operator's level lifecycle: a touch is a hold, and
               when it does not hold the level is done.

⚠️ MEASURED FROM ARMING, on 1-minute bars. `since_ts` is the moment the plan
armed on the level; bars before it are not this test. A ceiling that was
already below price at arming reads BREACHED at once and ACCEPTED two closes
later — honest, and it moves the plan on.

⚠️ NEVER RAISES. An unreadable frame returns UNTESTED with the reason — a
reader that cannot see the tape must not confirm a rejection.
"""
from __future__ import annotations

from typing import Optional, Tuple

try:
    from analysis.liquidity_mapper import _ACCEPT_CLOSES as ACCEPT_CLOSES
except Exception:                                              # noqa: BLE001
    ACCEPT_CLOSES = 2

from analysis.session_map import CEILING, FLOOR

UNTESTED, BREACHED, REJECTED, ACCEPTED = "UNTESTED", "BREACHED", "REJECTED", "ACCEPTED"


def level_state(df_1m, level: float, role: str, since_ts: Optional[float] = None
                ) -> Tuple[str, dict]:
    """(state, detail) for `level` with `role` (CEILING / FLOOR) on the 1m tape
    since `since_ts` (epoch seconds; None = whole frame)."""
    detail = {"tested": False, "closes_beyond": 0, "pierce": 0.0,
              "last_close": None, "bars": 0, "why": ""}
    try:
        if df_1m is None or getattr(df_1m, "empty", True):
            detail["why"] = "no 1m frame"
            return UNTESTED, detail
        df = df_1m
        if since_ts is not None:
            try:
                import pandas as pd
                ts0 = pd.Timestamp(since_ts, unit="s", tz="UTC")
                idx = df.index
                if getattr(idx, "tz", None) is None:
                    idx = idx.tz_localize("UTC")
                df = df[idx >= ts0]
            except Exception:                                  # noqa: BLE001
                pass
        if df is None or len(df) == 0:
            detail["why"] = "no bars since arming"
            return UNTESTED, detail
        lvl = float(level)
        highs = df["high"].astype(float)
        lows = df["low"].astype(float)
        closes = df["close"].astype(float)
        detail["bars"] = int(len(df))
        detail["last_close"] = float(closes.iloc[-1])
        if role == CEILING:
            tested = bool((highs >= lvl).any())
            beyond = int((closes > lvl).sum())
            pierce = float(max(0.0, highs.max() - lvl))
            last_inside = detail["last_close"] < lvl
        elif role == FLOOR:
            tested = bool((lows <= lvl).any())
            beyond = int((closes < lvl).sum())
            pierce = float(max(0.0, lvl - lows.min()))
            last_inside = detail["last_close"] > lvl
        else:
            detail["why"] = f"unknown role {role!r}"
            return UNTESTED, detail
        detail.update(tested=tested, closes_beyond=beyond, pierce=round(pierce, 4))
        if not tested:
            return UNTESTED, detail
        if beyond >= ACCEPT_CLOSES:
            detail["why"] = f"{beyond} closes beyond (>= {ACCEPT_CLOSES}) — accepted"
            return ACCEPTED, detail
        if last_inside:
            detail["why"] = (f"tested (pierce {pierce:.2f}) and the last close "
                             f"{detail['last_close']:.2f} is back inside")
            return REJECTED, detail
        detail["why"] = (f"through the level — last close {detail['last_close']:.2f} "
                         f"beyond it, {beyond} of {ACCEPT_CLOSES} closes to acceptance")
        return BREACHED, detail
    except Exception as exc:                                    # noqa: BLE001
        detail["why"] = f"unreadable: {type(exc).__name__}: {exc}"
        return UNTESTED, detail
