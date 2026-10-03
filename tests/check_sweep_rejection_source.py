#!/usr/bin/env python3
"""
tests/check_sweep_rejection_source.py  v1.0
v1.0  2026-10-03  CND.9 — A SWEEP CAN COMPLETE A CONDOR AGAIN.

  🔴 THE DEFECT, FOUND BY OTV4TEST'S AUDIT (MSG-1003-06) AND MEASURED HERE.
  main._sweep_has_rejection read ctx["sweep"], a key NOTHING has ever written:
  run_analysis builds ctx with `liq_map` (whose `recent_sweep` is the live
  LiquiditySweep) and no "sweep". _PAIRING_TABLE lets ONLY a sweep complete
  any leg-1 class, so since OTV4 r133 (2026-08-26) every second credit leg
  failed closed with "no sweep state available" and no condor could form.

  Drives the REAL main._pairing_allowed with a ctx shaped like run_analysis's
  (a liq_map carrying recent_sweep, no "sweep" key):
  S1  a reclaimed, live, young sweep on liq_map COMPLETES a sweep leg-1 (the
      defect: refused as "no sweep state available")
  S2  ...and completes a trend leg-1 too (every class is completed by a sweep)
  S3  INVALIDATED (price accepted through) is refused — a breakout
  S4  a wick with no reclaiming close is refused
  S5  older than _SWEEP_REJECTION_MAX_BARS is refused — a latched flag
  S6  no liq_map and no sweep at all is refused (fails closed, unchanged)
  S7  a fork completion needs no rejection (unchanged)

  BORN RED on otv4 2220461 at S1-S5 (S3-S5 because the refusal reason never
  reached the rule — every case read 'no sweep state available'). S6/S7 green on
  both: the fix only adds a SOURCE and loosens nothing.

Run:  python3 tests/check_sweep_rejection_source.py
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# main attaches a RotatingFileHandler to config.LOG_FILE at import; point it at
# scratch so this check never writes into a bot.log (OTV4TEST's BOX.16 class).
import config                                                   # noqa: E402
_tmp = tempfile.mkdtemp(prefix="check_sweep_src_")
config.LOG_FILE = os.path.join(_tmp, "bot.log")

PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def main():
    import main as M
    from analysis.liquidity_mapper import LiquiditySweep, LiquidityMap

    sweep_src = sorted(M._SWEEP_TRIGGERS)[0]
    trend_src = sorted(M._TREND_TRIGGERS)[0]
    fork_src = sorted(M._FORK_TRIGGERS)[0]

    def ctx_with(**kw):
        sw = LiquiditySweep(pool_price=100.0, sweep_price=100.4, kind="high_sweep",
                            reclaimed=kw.get("reclaimed", True),
                            invalidated=kw.get("invalidated", False),
                            bars_ago=kw.get("bars_ago", 2))
        lmap = LiquidityMap()
        lmap.recent_sweep = sw
        return {"price": 100.1, "liq_map": lmap}     # no "sweep" key, like run_analysis

    ok, why = M._pairing_allowed(sweep_src, sweep_src, ctx=ctx_with())
    check("S1 a live reclaimed sweep on liq_map completes a SWEEP leg-1", ok, why)
    ok, why = M._pairing_allowed(trend_src, sweep_src, ctx=ctx_with())
    check("S2 ...and completes a TREND leg-1", ok, why)
    ok, why = M._pairing_allowed(sweep_src, sweep_src, ctx=ctx_with(invalidated=True))
    check("S3 an INVALIDATED sweep is refused (a breakout)", not ok and "INVALIDATED" in why, why)
    ok, why = M._pairing_allowed(sweep_src, sweep_src, ctx=ctx_with(reclaimed=False))
    check("S4 a wick with no reclaiming close is refused", not ok and "wick" in why, why)
    old = M._SWEEP_REJECTION_MAX_BARS + 1
    ok, why = M._pairing_allowed(sweep_src, sweep_src, ctx=ctx_with(bars_ago=old))
    check("S5 a rejection older than the max is refused", not ok and "old" in why, why)
    ok, why = M._pairing_allowed(sweep_src, sweep_src, ctx={"price": 100.0})
    check("S6 no liq_map and no sweep fails CLOSED", not ok, why)
    ok, why = M._pairing_allowed(sweep_src, fork_src, ctx={"price": 100.0})
    _c2 = M._trigger_class(fork_src)
    _permitted = _c2 in M._PAIRING_TABLE.get(M._trigger_class(sweep_src), ())
    check("S7 UNCHANGED: a fork completion is decided by the table alone, no "
          "rejection asked", ok == _permitted and "rejection" not in why.lower(), why)

    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — a sweep completes a condor when, and only when, it is a live rejection")
    return 0


if __name__ == "__main__":
    sys.exit(main())
