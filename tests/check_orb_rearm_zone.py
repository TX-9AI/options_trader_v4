#!/usr/bin/env python3
"""
tests/check_orb_rearm_zone.py  v1.0
v1.0  2026-09-03  r221 — THE BAND BETWEEN THE BOUNDARY AND THE 50% HAD NO OWNER.

🔴 `notify_position_closed` ALWAYS CALLED `_rearm()`, WHICH WIPES ORBData. The
impulsive candle went with it and the engine sat in AWAITING_RANGE_REENTRY, so
a second retest of the boundary FROM OUTSIDE could arm nothing. Meanwhile the
runaway will not take the move until a 1m close beyond `target_50pct` HOLDS.
Measured on NVDA, 2026-09-03: broke 227.43, retested, entered, exited in
profit — and 227.43 -> 228.77 was owned by NO strategy.

🔑 A RETEST AND A RE-ENTRY ARE DIFFERENT EVENTS. The operator's correction, and
the distinction the whole change rests on:
  · RETEST   = wick into the range, close back OUTSIDE. A TEST. Fires a trade,
               leaves the impulsive candle intact.
  · RE-ENTRY = a CLOSE back INSIDE the range. ACCEPTANCE. Terminates the
               thesis; a fresh break must set a new impulsive candle.
"Wicks are tests & closes are acceptance."

⚠️ AND THE 50% HANDOFF USES THE RUNAWAY'S OWN TWO-PART TEST. Standing down on a
TOUCH of the 50% would end the ORB thesis while the runaway never armed —
re-opening the same gap one level higher.

Born red at 9b29ec5 (r220), where Z1 and Z4 fail.
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def _bars(closed_bar_close, forming=None, closed_high=None):
    """Bars where the CLOSED candle is `iloc[-2]`, as the engine reads it.

    🔴 MY FIRST FIXTURE PUT THE TEST BAR AT `iloc[-1]` AND PROVED NOTHING.
    Every latch in orb_engine reads `df_1m.iloc[-2]` — the last CLOSED candle;
    `iloc[-1]` is still forming. Z2 "passed" against a wick it never examined.
    I read that convention in the source and then did not apply it, so the
    helper now makes the closed bar explicit and impossible to misplace.
    """
    import pandas as pd
    c0 = float(closed_bar_close)
    c1 = float(c0 if forming is None else forming)
    h0 = float(c0 + .05 if closed_high is None else closed_high)
    return pd.DataFrame({"open":  [c0, c1],
                         "high":  [h0, c1 + .05],
                         "low":   [c0 - .05, c1 - .05],
                         "close": [c0, c1]})


def main():
    from analysis import orb_engine as OE

    def armed_long_engine():
        """An engine mid-setup: broke 227.43 long, impulse candle recorded."""
        e = OE.ORBEngine() if hasattr(OE, "ORBEngine") else OE.get_orb_engine()
        d = OE.ORBData()
        d.state = OE.ORBState.OPEN_LONG
        d.orb_high, d.orb_low = 227.43, 226.23
        d.orb_width = d.orb_high - d.orb_low
        d.break_candle_low, d.break_candle_high = 226.90, 227.60
        d.break_direction = "LONG"
        d.stop_distance_px = 0.53
        d.target_50pct = d.orb_high + d.orb_width * 0.5      # 228.03
        d.attempt_number = 1
        e._data = d
        return e, d

    # ── Z1 — A RESOLVED TRADE IN THE ZONE STAYS ARMED ───────────────────
    # ⚠️ READ `e._data`, NEVER A HELD REFERENCE. r96's lesson: `_rearm()`
    # REPLACES ORBData wholesale, so a `d` captured before the call is stale
    # and still reports OPEN_LONG. My first draft asserted against that stale
    # object and so would have passed on the OLD code for the wrong reason —
    # the engine is the source of truth, not a snapshot of it.
    e, _d0 = armed_long_engine()
    e.notify_position_closed()
    d = e._data
    check("Z1 a resolved trade with the 50% unaccepted stays ARMED_LONG",
          d.state == OE.ORBState.ARMED_LONG, d.state)

    # 🔑 THE IMPULSIVE CANDLE IS THE POINT. `_rearm()` wipes ORBData, so if it
    # ran, the stop geometry is gone and the next retest would size off 0.0 —
    # the sizer's "degenerate branch takes it to a 1-lot loudly".
    check("Z1b the ORIGINAL impulsive candle and stop distance survive",
          abs(d.break_candle_low - 226.90) < 1e-9
          and abs(d.stop_distance_px - 0.53) < 1e-9,
          f"candle {d.break_candle_low} dist {d.stop_distance_px}")
    check("Z1c the attempt number advances",
          d.attempt_number == 2, str(d.attempt_number))

    # ── Z2 — A WICK THROUGH THE 50% ARMS NOTHING ────────────────────────
    # ⚠️ Wicks are tests. The tracker reads the CLOSED candle, so a bar whose
    # HIGH pierces 228.03 while its CLOSE sits below must not hand the move to
    # the runaway.
    e, d = armed_long_engine()
    import pandas as pd
    # the CLOSED bar wicks to 228.60 and closes at 227.80 — below the 50%
    e._update_break_latches(_bars(227.80, forming=227.85, closed_high=228.60))
    d = e._data
    check("Z2 a WICK through the 50% does not accept it",
          not d.fifty_accepted and not d.fifty_pending,
          f"accepted={d.fifty_accepted} pending={d.fifty_pending}")

    # ── Z3 — A CLOSE BEYOND THAT DOES NOT HOLD IS DISCARDED ─────────────
    # ⚠️ The runaway requires the hold at the next tick. A close that reverses
    # immediately is a wick with extra steps, and the ORB setup must stand.
    e, d = armed_long_engine()
    e._update_break_latches(_bars(228.40))              # closed beyond -> pending
    check("Z3 one close beyond the 50% is PENDING, not accepted",
          d.fifty_pending and not d.fifty_accepted,
          f"pending={d.fifty_pending}")
    e._update_break_latches(_bars(227.90))              # fell back
    check("Z3b a pending close that does not hold is cleared",
          not d.fifty_pending and not d.fifty_accepted)
    e.notify_position_closed()
    check("Z3c and the ORB is still armed after that failed acceptance",
          e._data.state == OE.ORBState.ARMED_LONG, e._data.state)

    # ── Z4 — ACCEPTED 50% HANDS THE MOVE TO THE RUNAWAY ─────────────────
    # 🔴 "If it reaches the 50, then the runaway owns it unequivocally — that
    # move in itself invalidates an ORB trade."
    e, d = armed_long_engine()
    e._update_break_latches(_bars(228.40))              # close beyond
    e._update_break_latches(_bars(228.50))              # held
    check("Z4 a close beyond the 50% that HOLDS is accepted",
          d.fifty_accepted, f"accepted={d.fifty_accepted}")
    e.notify_position_closed()
    check("Z4b an accepted 50% stands the ORB down as 'runaway'",
          e._data.state == OE.ORBState.INVALIDATED
          and e._data.invalidation_reason == "runaway",
          f"{e._data.state}/{e._data.invalidation_reason}")

    # ── Z5 — ACCEPTANCE IS A LATCH ──────────────────────────────────────
    # ⚠️ Once the runaway owns the move it keeps it for the session, even if
    # price falls back. Same discipline as broke_high/broke_low.
    e, d = armed_long_engine()
    e._update_break_latches(_bars(228.40))
    e._update_break_latches(_bars(228.50))
    e._update_break_latches(_bars(227.50))              # well back below
    check("Z5 acceptance does not clear when price falls back",
          d.fifty_accepted)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_orb_rearm_zone: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
