#!/usr/bin/env python3
"""check_entry_windows.py — v1.4
v1.4  2026-10-11  r484: W4c — THE BUTTERFLY OPENS AT 13:00, DRIVEN. prepare() at 12:59 is
      dormant on entry_window and at 13:00 it is not; the config constant is
      (13, 0). Operator, 2026-10-11: "Move the flies to 1300."
v1.3  2026-09-08  r321: W9 — THE WINDOW A STRATEGY COMPUTES, NOT THE CONSTANT
      IT DECLARES. W5 asserts `sweep.EARLIEST_ET == CREDIT_ENTRY_START_ET` and
      was green while the sweep OPENED AT 09:45 under relaxed, because
      `prepare()` passes its constants through `relaxed.window()` and the
      `relaxed_earliest` default is "09:45" — a value nobody chose for this
      strategy. W9 drives the same call the strategy makes, in BOTH modes, and
      asserts the applied window is identical. Born red at 82d369e.
v1.2  2026-09-08  r317: W8 — THE END SIDE, WHICH THIS FILE NEVER ASSERTED.
      W1 has pinned ONE credit START across four paths since r146, written
      after the sweep kept 11:11 on a `getattr` default whose key did not
      exist. `SWEEP_CS_LATEST_ET` was the SAME DEFECT on the END and survived
      both sweeps because nothing here looked at ends at all. Born red at
      0498534, where `C.SWEEP_CS_LATEST_ET` raises AttributeError.
      ⚠️ W8 GOES RED ON A DELIBERATE DIVERGENCE TOO, and that is the point:
      if a future ruling gives one credit path its own cutoff, this check is
      how that decision gets recorded rather than absorbed. Update it WITH the
      ruling; do not loosen it to keep a run green.
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

    # ── W4c — r484: 13:00, DRIVEN through prepare(), not read off a constant ─
    def _window_open(hhmm):
        # Out of window, prepare() returns BEFORE recording the entry_window
        # condition; in window it records it. The condition list is the signal.
        p = _bf.GEXPinButterflyStrategy().prepare(gex=None, price_now=100.0, now_et=hhmm)
        return "entry_window" in repr(p.conditions)

    check("W4c the butterfly is (13, 0) and prepare() is dormant at 12:59, open at 13:00",
          tuple(C.BUTTERFLY_ENTRY_START_ET) == (13, 0)
          and not _window_open("12:59") and _window_open("13:00"),
          f"config={C.BUTTERFLY_ENTRY_START_ET} 12:59 open={_window_open('12:59')} "
          f"13:00 open={_window_open('13:00')}")

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

    # ── 🔴 W8 — ONE CREDIT END, THE MIRROR OF W1 ─────────────────────────
    # The sweep's END was `getattr(config, "SWEEP_CS_LATEST_ET", "14:00")` with
    # NO SUCH KEY — the third instance of the default-is-the-only-source shape
    # in this codebase, and the first on the END side. All four read 14:00
    # today, so this is latent: it costs nothing until the cutoff moves, and
    # then three paths move and the sweep does not.
    # ⚠️ NAMED FAILURE, NEVER A TRACEBACK. At 0498534 neither CREDIT_ENTRY_END_ET
    # nor SWEEP_CS_LATEST_ET exists, and a bare read raised AttributeError —
    # "the checker crashed" and "the constant is absent" must not look alike
    # (WORKING_AGREEMENT §0.5), least of all in the check whose whole subject is
    # a constant that was missing.
    _missing = [n for n in ("CREDIT_ENTRY_END_ET", "SWEEP_CS_LATEST_ET",
                            "CONDOR_ENTRY_CUTOFF_ET", "TCS_ENTRY_END_ET")
                if not hasattr(C, n)]
    if _missing:
        check("W8 there is ONE credit end and every credit path uses it",
              False, f"config defines no {', '.join(_missing)}")
        check("W8b the credit window is bounded the right way round", False,
              "cannot evaluate — the end constant is absent")
        _end = None
    else:
        _end = tuple(C.CREDIT_ENTRY_END_ET)
        check("W8 there is ONE credit end and every credit path uses it",
              tuple(C.CONDOR_ENTRY_CUTOFF_ET) == _end
              and tuple(C.TCS_ENTRY_END_ET) == _end
              and _hm(C.SWEEP_CS_LATEST_ET) == _end
              and _hm(_sc.LATEST_ET) == _end,
              f"end={_end} condor={C.CONDOR_ENTRY_CUTOFF_ET} tcs={C.TCS_ENTRY_END_ET} "
              f"sweep_cfg={C.SWEEP_CS_LATEST_ET} sweep_strategy={_sc.LATEST_ET}")
        check("W8b the credit window is bounded the right way round",
              tuple(start) < _end, f"{start} -> {_end}")

    # ── 🔴 W9 — THE APPLIED WINDOW, IN BOTH MODES ────────────────────────
    # Operator, 2026-09-08: *"The sweep window cannot be relaxed. It needs to
    # remain strict at all times at 11:31."* W5 above compares the module
    # CONSTANT to config and cannot see what `prepare()` actually computes;
    # this drives the identical `relaxed.window()` call under both flags.
    # 🔴 A FIRST CUT OF W9 CALLED `relaxed.window()` ITSELF, PASSING THE
    # ARGUMENTS THE FIX ADDS — and it was GREEN at the broken HEAD, because it
    # tested the assumption instead of the code (§0.4: a fixture built from
    # your own belief cannot fail). This RUNS `prepare()` and RECORDS what the
    # strategy actually passes, so the arguments come from the call site.
    import os as _os
    from strategy import relaxed as _rx

    class _StubMap:                      # the window gate is the first thing
        pools = []                       # prepare() reaches; nothing below it
        def __getattr__(self, _n): return []

    # ⚠️ RELAXED IS PAPER-ONLY AND `is_live()` FAILS CLOSED, so without this
    # the "relaxed" arm runs STRICT and the check passes on a broken tree —
    # verified: the first cut was GREEN at 82d369e for exactly that reason.
    # A checker whose two arms are secretly the same arm cannot fail.
    _prev = _os.environ.get("OT_RELAXED_ENTRY")
    _prev_paper = _os.environ.get("OT_PAPER_TRADING")
    _os.environ["OT_PAPER_TRADING"] = "1"
    assert _rx.is_live() is False, "relaxed arm would silently run strict"
    _orig_window, _applied = _rx.window, {}
    try:
        for _m in ("0", "1"):
            _os.environ["OT_RELAXED_ENTRY"] = _m
            _seen = {}
            def _rec(_e, _l, __o=_orig_window, __s=_seen, **_kw):
                __s["out"] = __o(_e, _l, **_kw)
                return __s["out"]
            _rx.window = _rec
            _sc.SweepCreditSpreadStrategy().prepare(
                liq_map=_StubMap(), price_now=100.0, now_et="10:00",
                atr_pct=0.5, chain=None)
            _applied[_m] = _seen.get("out")
    finally:
        _rx.window = _orig_window
        if _prev is None:
            _os.environ.pop("OT_RELAXED_ENTRY", None)
        else:
            _os.environ["OT_RELAXED_ENTRY"] = _prev
        if _prev_paper is None:
            _os.environ.pop("OT_PAPER_TRADING", None)
        else:
            _os.environ["OT_PAPER_TRADING"] = _prev_paper

    check("W9pre the relaxed arm was genuinely RELAXED (not silently strict)",
          _applied["1"] is not None, "prepare() never reached the window gate")
    check("W9 the sweep's APPLIED window is identical in both modes",
          _applied["0"] is not None and _applied["0"] == _applied["1"],
          f"strict={_applied['0']} relaxed={_applied['1']}")
    check("W9b and it starts at the universal credit start under RELAXED",
          _applied["1"] is not None and _hm(_applied["1"][0]) == tuple(start),
          f"applied start {_applied['1'] and _applied['1'][0]} vs credit start {start}")

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
