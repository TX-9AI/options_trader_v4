#!/usr/bin/env python3
"""check_entry_windows.py — v1.1
v1.1  2026-08-26  r146: W7 re-pinned to each strategy's PLAN_CHECKS after the
      builder engine was deleted.

🔴 ONE START TIME FOR EVERY CREDIT SPREAD, AND ONE MINUTE OF DAYLIGHT.

Operator, 2026-08-26: a universal credit start "to keep things tidy". The
number is 11:31 rather than 11:30 because of his own 2026-08-24 ruling —
*"Handoff (credit) needs to start at 1131 - it's colliding with runaway (same
trigger)"* — and because the debit cutoff test is `>= (11, 30)`, so the debit
is blocked AT 11:30. A credit start of 11:30 would hand both the same minute
and reproduce the collision that ruling fixed.

⚠️ SECONDS CANNOT EXPRESS A FINER BOUNDARY. Every gate compares
`(now.hour, now.minute)`; 11:30:01 and 11:30:59 are the same tuple. The tick is
30s besides, so a sub-minute boundary would land wherever each box's restart
drift happened to put it.
"""
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    import config as C

    start = C.CREDIT_ENTRY_START_ET

    # ⚠️ FOUR PATHS, NOT THREE. The sweep read its start from a getattr
    # DEFAULT that was never in config, so it kept 11:11 while the other three
    # moved — caught by check_sweep_spread's S8a, not by me. Any credit path
    # that carries its own literal is the failure this check exists to prevent.
    _sw = tuple(int(x) for x in C.SWEEP_CS_EARLIEST_ET.split(":"))
    check("W1 there is ONE credit start and every credit path uses it",
          C.CONDOR_ENTRY_START_ET == start and C.TCS_START_ET == start
          and _sw == start,
          f"credit={start} condor={C.CONDOR_ENTRY_START_ET} "
          f"tcs={C.TCS_START_ET} sweep={_sw}")

    # 🔴 THE DAYLIGHT RULE. The debit cutoff is `>= (11, 30)` — debit is blocked
    # AT 11:30 — so the credit must start STRICTLY LATER than 11:30, or both
    # own the same minute and the handover is ambiguous in the log and the
    # record. This is the operator's 08-24 collision, and it is the single
    # thing most likely to be "tidied" back into existence later.
    check("W2 credit starts strictly AFTER the debit cutoff minute",
          start > (11, 30), f"credit start {start} vs debit cutoff (11, 30)")

    check("W3 the credit window is non-empty",
          start < C.CONDOR_ENTRY_CUTOFF_ET,
          f"{start} -> {C.CONDOR_ENTRY_CUTOFF_ET}")

    # ⚠️ THE BUTTERFLY OPENS LATER THAN THE CREDIT SPREADS, AND THAT IS THE
    # RULING, not an oversight. Operator, 2026-08-26: *"Butterfly is debit &
    # any sooner than noon to reach a pin is unlikely to hold all the way to
    # the closing bell."* It is a DEBIT that needs the pin to hold into the
    # close, so a later start is protective rather than restrictive.
    bf = C.BUTTERFLY_ENTRY_START_ET
    print(f"  NOTE  butterfly (debit) starts {bf}, "
          f"{(bf[0]*60+bf[1]) - (start[0]*60+start[1])} min after the credit "
          f"spreads — RULED 2026-08-26, a debit needs the pin to hold to the bell")

    # ⚠️ AND THE WINDOW LENGTH IS A REAL COST, so state it rather than bury it.
    mins = ((C.CONDOR_ENTRY_CUTOFF_ET[0]*60 + C.CONDOR_ENTRY_CUTOFF_ET[1])
            - (start[0]*60 + start[1]))
    print(f"  NOTE  credit entry window is {mins} min "
          f"(was 169 at the old 11:11 condor start)")

    # ── 🔴 W4-W6 — THE STRATEGIES AND THE PLANS MUST AGREE ───────────────
    # ⚠️ TWO MORE getattr DEFAULTS WITH NO CONFIG KEY, found the same way as
    # the sweep: `GEX_BFLY_EARLIEST_ET` defaulted to "11:00" — so the LIVE
    # butterfly gate opened a full hour before BUTTERFLY_ENTRY_START_ET, a
    # constant production read NOWHERE — and `RUNAWAY_CUTOFF_ET` defaulted to
    # "11:30". A config value nobody reads is decorative; a default nobody can
    # see is the real setting.
    import strategy.gex_pin_butterfly as _bf
    import strategy.runaway_continuation as _rc
    import strategy.sweep_credit_spread as _sc

    def _hm(t):
        return tuple(int(x) for x in t.split(":")) if isinstance(t, str) else tuple(t)

    check("W4 the butterfly STRATEGY honours the config noon rule",
          _hm(_bf.EARLIEST_ET) == tuple(C.BUTTERFLY_ENTRY_START_ET),
          f"strategy {_bf.EARLIEST_ET} vs config {C.BUTTERFLY_ENTRY_START_ET}")

    check("W5 the sweep STRATEGY honours the universal credit start",
          _hm(_sc.EARLIEST_ET) == tuple(start),
          f"strategy {_sc.EARLIEST_ET} vs config {start}")

    # 🔴 THE DAYLIGHT, MEASURED FROM BOTH SIDES. The debit cutoff and the
    # credit start must be exactly one minute apart — the operator's 08-24
    # collision fix, expressed as arithmetic instead of a comment.
    _dc = _hm(_rc.CUTOFF_ET)
    check("W6 debit cutoff and credit start are exactly one minute apart",
          (start[0]*60 + start[1]) - (_dc[0]*60 + _dc[1]) == 1,
          f"debit cutoff {_dc} -> credit start {start}")

    # ── W7 — the PLAN side declares and applies the same window ──────────
    # ⚠️ NO PLAN BUILDER CHECKED THE CLOCK AT ALL until r142. A fork plan read
    # TAKE at 11:05 while the strategy could not act until 11:31 — the row
    # looked tradeable and was not, and nothing in the table said why.
    # r146 — the plan is now the strategy's own (strategy/plan.py); each
    # strategy declares the checks it owns as PLAN_CHECKS. ORB is exempt by
    # ruling (record-only, zero hurdles) and the roll is management.
    from strategy.runaway_continuation import RunawayContinuationStrategy
    from strategy.trend_credit_spread import TrendCreditSpread
    from strategy.sweep_credit_spread import SweepCreditSpreadStrategy
    from strategy.gex_pin_butterfly import GEXPinButterflyStrategy
    from strategy.iron_condor_strategy import IronCondorStrategy
    _missing = [c.__name__ for c in (
        RunawayContinuationStrategy, TrendCreditSpread, SweepCreditSpreadStrategy,
        GEXPinButterflyStrategy, IronCondorStrategy)
        if "entry_window" not in getattr(c, "PLAN_CHECKS", ())]
    check("W7 every entry strategy's plan declares an entry_window check",
          not _missing, ", ".join(_missing) or "none")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_entry_windows: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
