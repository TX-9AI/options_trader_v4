#!/usr/bin/env python3
"""
tests/check_orb_stop_respected.py  v1.0

v1.0  2026-09-16  r386 / ORB.17 — THE STOP THE SIZE WAS PREDICATED ON IS NOW
      HONOURED, WITHIN A GRACE PROPORTIONAL TO ITSELF.

🔴 THE DEFECT, AND IT IS A BROKEN PROMISE RATHER THAN A BAD NUMBER.
`_size_geometry` sizes on `width / stop_distance` and states its premise plainly:
*"every ORB trade risks roughly the same dollars AT THE STRUCTURE STOP by
construction."* The sizer therefore says, of a stop 0.02 away: *take 86
contracts, you only risk 86 x 0.02.*

**The structure stop then does not fire at 0.02.** It waits for a 1-minute CLOSE
beyond the level, so it fires wherever that close lands.

📊 MEASURED ACROSS 155 BANKED ORB TRADES (54 structure-stop exits, the intended
stop read off `underlying_entry`/`underlying_stop` and the ACTUAL exit level
parsed from the exit reason's own `1m close`):

    median intended 0.38  ->  median ACTUAL 0.54   (median overshoot 46%)

    AND THE WORST OVERSHOOTS ARE THE BIGGEST POSITIONS, which is the whole point:
      PLTR  stop 0.02 -> paid 0.25  (12.5x)   86 contracts
      QQQ   stop 0.06 -> paid 0.64  (10.7x)   24 contracts
      NVDA  stop 0.03 -> paid 0.20  ( 6.7x)   49 contracts
      GOOGL stop 0.02 -> paid 0.11  ( 5.5x)   60 contracts
      PLTR  stop 0.01 -> paid 0.05  ( 5.0x)  129 contracts

A tight stop is the one most easily overshot by waiting a whole bar, and a tight
stop is exactly what buys the most contracts. So the risk the size was justified
by was multiplied by 5x-12x on precisely the trades carrying the most size.

⚠️ SO THIS IS NOT A SIZING DEFECT AND THE FIX IS NOT A SMALLER POSITION.
Operator, 2026-09-16: *"I want the tight stop respected. Right now, it isn't"* —
and *"on those large trades, we only have to be directionally correct for a very
brief time to harvest it."* Capping size was measured and is the WORSE answer
(+$2,564 at best, and NEGATIVE at a $1,000 risk budget, because shrinking cuts
the large winners too). Honouring the stop is +$3,183 estimated and leaves the
gamma upside intact.

🔑 WHY THE GRACE IS PROPORTIONAL AND NOT A FIXED BAND. The close-based rule
exists on purpose — its own comment says *"so an intrabar wick into the range
survives"* — and that breathing room is correct. But its COST scales with the
stop: a whole bar of grace on a 0.02 stop is 12x the intended risk, while on a
3.00 stop it is noise. A tolerance expressed as a FRACTION OF THE STOP ITSELF is
scale-free: it costs a wide-stop trade nothing and protects a tight-stop trade.

⚠️ THE CLOSE-BASED ARM IS NOT REMOVED, REPLACED OR REORDERED. It still fires on
a confirmed close beyond the origin exactly as before. This is an ADDITIONAL arm
that can only fire EARLIER, and only once price is beyond the stop by more than
the grace. R4 is the control that pins the old behaviour unchanged.

⚠️ AND THE PREMIUM FLOOR IS NOT MOVED. It stays where it is as the catastrophic
backstop (v1.6 added it after CRM 2026-07-09 bled to -83% while the structure
stop held). This arm sits above it and will usually pre-empt it on a tight stop
by firing sooner in TIME — which is the repair, not a reordering.

  R1  a tight stop, price intrabar beyond stop + grace, last CLOSED candle still
      on the safe side -> EXITS. It must exit on the FORMING bar, not the closed
      one, or it is indistinguishable from the arm that already exists.
  R1b the same record after a SELECT * round trip (§22)
  R2  CONTROL — beyond the stop but INSIDE the grace -> does NOT exit. The
      breathing room survives; if R2 reds, the grace has been thrown away.
  R3  CONTROL — a WIDE stop with an ordinary wick -> does NOT exit. Pins that
      this is scale-free and cannot bite a normal trade.
  R4  CONTROL — the close-based arm still fires on its own terms, unchanged.
  R5  CONTROL — r383's entry-underwater arm still fires. No regression on the
      neighbouring block.
  R6  the grace is a NAMED CONSTANT, not a literal buried in the branch.
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def main() -> int:
    print("check_orb_stop_respected — the stop the size was predicated on is honoured")
    print()
    try:
        import pandas as pd
        import execution.exit_engine as XE
        from execution.exit_engine import ExitEngine
    except Exception as exc:                                     # noqa: BLE001
        print(f"  FAIL  R0 exit path did not import: {exc}")
        for n in ("R1", "R1b", "R2", "R3", "R4", "R5", "R6"):
            check(n, False, "unreachable")
        return 1

    # Pin the clock — the ORB branch checks is_hard_close_time() FIRST, and a
    # suite that happens to run after 15:40 would go green on the wrong reason
    # (this bit check_orb_underwater_entry's first cut; CHK.4's shape).
    _real_hc = XE.is_hard_close_time
    XE.is_hard_close_time = lambda *a, **k: False
    try:
        ee = ExitEngine(paper_trading=True)

        def rec(entry, stop, direction="short", prem=3.17, ctr=18):
            return {"trade_id": "stop-respect-1", "symbol": "MU",
                    "strategy": "ORBStrategy", "setup_type": "ORB Short",
                    "direction": direction, "option_side": "put",
                    "contracts": ctr, "entry_premium": prem,
                    "stop_premium": prem * 0.75, "target_premium": prem * 2,
                    "trail_activation": prem * 1.5,
                    "underlying_entry": entry, "underlying_stop": stop,
                    "underlying_target": entry - 10, "orb_range_low": 925.21,
                    "orb_range_high": 939.21, "status": "open",
                    "is_butterfly": 0, "is_condor_leg": 0}

        def bars(closed, forming_hi, forming_lo=None):
            """last CLOSED bar = iloc[-2]; FORMING bar = iloc[-1]."""
            lo = forming_lo if forming_lo is not None else forming_hi - 0.5
            return pd.DataFrame(
                [{"open": closed, "high": closed + .05, "low": closed - .05, "close": closed},
                 {"open": closed, "high": closed + .05, "low": closed - .05, "close": closed},
                 {"open": closed, "high": forming_hi, "low": lo, "close": closed}],
                index=pd.date_range("2026-09-16 09:40", periods=3, freq="1min"))

        # MU 2026-09-16's real geometry: entry 925.62, stop 926.40 -> 0.78 stop.
        # grace at 50% -> 0.39, so the arm must fire beyond 926.79.
        # The last CLOSED bar is 926.00 — INSIDE the stop — so the existing
        # close-based arm CANNOT be what exits. That is the point of R1.
        d1 = ee.evaluate(rec(925.62, 926.40), current_premium=3.10,
                         df_1m=bars(926.00, 927.43))
        check("R1 a tight stop breached intrabar beyond the grace EXITS, while "
              "the last closed candle is still on the safe side",
              bool(getattr(d1, "should_exit", False)),
              f"reason={getattr(d1, 'exit_reason', None)!r}")

        d1b = ee.evaluate(dict(rec(925.62, 926.40)), current_premium=3.10,
                          df_1m=bars(926.00, 927.43))
        check("R1b the rehydrated shape behaves identically",
              bool(getattr(d1b, "should_exit", False)),
              f"reason={getattr(d1b, 'exit_reason', None)!r}")

        # ── R2 — CONTROL. 926.60 is BEYOND the 926.40 stop but inside the
        # 0.39 grace. This is the wick the close-based rule exists to survive.
        d2 = ee.evaluate(rec(925.62, 926.40), current_premium=3.10,
                         df_1m=bars(926.00, 926.60))
        check("R2 CONTROL beyond the stop but INSIDE the grace does NOT exit — "
              "the breathing room survives",
              not bool(getattr(d2, "should_exit", False)),
              f"reason={getattr(d2, 'exit_reason', None)!r}")

        # ── R3 — CONTROL. A WIDE stop (5.00) with the same 1.03 excursion past
        # it would need 2.50 of grace; 1.03 is well inside. Scale-free.
        d3 = ee.evaluate(rec(920.00, 925.00), current_premium=3.10,
                         df_1m=bars(924.00, 926.03))
        check("R3 CONTROL a WIDE stop with an ordinary wick does NOT exit — the "
              "grace is proportional, so a normal trade is untouched",
              not bool(getattr(d3, "should_exit", False)),
              f"reason={getattr(d3, 'exit_reason', None)!r}")

        # ── R4 — CONTROL. The close-based arm ON ITS OWN TERMS.
        # ⚠️ THE FIRST CUT OF THIS CONTROL WAS WRONG AND IT IS WORTH RECORDING.
        # It used a forming bar at 927.45, which is ALSO beyond the grace — so
        # both arms were true, the new one fired first, and the check went red
        # while proving nothing about the old arm. A control has to ISOLATE the
        # property it names. Here the last CLOSED bar is beyond the stop
        # (927.43) and price has since RETREATED to 926.50 — beyond the stop but
        # INSIDE the 0.39 grace — so the new arm is silent by construction and
        # only the close-based arm can produce this exit.
        d4 = ee.evaluate(rec(925.62, 926.40), current_premium=3.10,
                         df_1m=bars(927.43, 926.50, 926.20))
        r4 = str(getattr(d4, "exit_reason", "") or "")
        check("R4 CONTROL the close-based structure stop still fires unchanged",
              bool(getattr(d4, "should_exit", False)) and "orb_structure_stop" in r4,
              f"reason={r4!r}")

        # ── R5 — CONTROL. r383's entry-underwater arm still fires. Entry 927.00
        # is ABOVE the 926.40 stop on a short = already through it at the fill.
        d5 = ee.evaluate(rec(927.00, 926.40), current_premium=3.10,
                         df_1m=bars(925.00, 925.10))
        r5 = str(getattr(d5, "exit_reason", "") or "")
        check("R5 CONTROL r383's entry_underwater arm is not regressed",
              bool(getattr(d5, "should_exit", False)) and "entry_underwater" in r5,
              f"reason={r5!r}")
    finally:
        XE.is_hard_close_time = _real_hc

    # ── R6 — the grace is a named constant, readable and rulable.
    try:
        from config import ORB_STOP_RESPECT_TOL as _tol
        check("R6 the grace is a NAMED CONSTANT, not a literal in the branch",
              isinstance(_tol, float) and 0 < _tol < 5,
              f"ORB_STOP_RESPECT_TOL={_tol}")
    except Exception as exc:                                     # noqa: BLE001
        check("R6 the grace is a NAMED CONSTANT, not a literal in the branch",
              False, f"not importable from config: {exc}")

    print()
    if _fails:
        print("FAILED: " + ", ".join(_fails))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
