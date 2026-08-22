#!/usr/bin/env python3
"""
tests/check_exit_executes.py  v4.2
v4.2  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).


The exit engine EXECUTES, or the board goes red. Plain script, exit code.

v4.1  2026-08-20  AUDIT F0. At HEAD 35a6ba4, `class ExitEngine` had been cut in
      half: `_track_excursion` landed at column 0 inside the class region
      (r38), so `evaluate` and all 33 evaluators below it were nested locals of
      a telemetry function — bound to nothing, dead. The file compiled,
      `import main` passed, and every standing check stayed green because NONE
      OF THEM EXECUTED AN EXIT. At runtime every tick with an open position
      raised AttributeError into the loop's catch-all: no stop, no trail, no
      theta bleed, no nickel close, no condor ladder — only the independent
      15:45 flatten stood between a position and the close. This script is the
      check that was missing: it drives `evaluate()` on real records and
      asserts DECISIONS, not imports. It fails at 35a6ba4 with the exact
      AttributeError that was firing in production silence.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 — NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

"Prefer executing to reading" (AUDIT_HANDOFF §5) exists because defects keep
being invisible to `import`: the ctx NameError of 2026-08-18, the vanished
bisected class. `import` proves a file parses; only a call proves it runs.
The 15%-unhedged / 25%-hedged condor-leg stop asserted here is TRADES.md §5's
own rule with its own measurement (condor_stop: 16 trades, 19% win, −$1,156,
calibrated for a complete structure, never for a naked leg).
"""
import os
import sys
import datetime as _dt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

PROBLEMS = []


def check(label, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + label
          + (f"  - {detail}" if detail and not cond else ""))
    if not cond:
        PROBLEMS.append(label)


def main(argv):
    print("EXIT ENGINE EXECUTION CHECK")
    print("=" * 68)
    os.environ.setdefault("OT_PAPER_TRADING", "1")

    import execution.exit_engine as XE
    from utils.time_utils import ET

    # ── 0. the class is WHOLE ────────────────────────────────────────────────
    check("ExitEngine.evaluate exists on the class",
          hasattr(XE.ExitEngine, "evaluate"),
          "the class has been bisected again - see AUDIT F0")
    check("ExitEngine._evaluate_condor_leg exists on the class",
          hasattr(XE.ExitEngine, "_evaluate_condor_leg"))
    if PROBLEMS:
        print(f"\n  {len(PROBLEMS)} problem(s) - exits are DEAD CODE")
        return 1

    # pin the clock inside the session so time exits cannot mask the asserts
    _real_dt = XE.datetime

    class _Frozen(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _real_dt(2026, 8, 20, 13, 0, tzinfo=ET)

    XE.datetime = _Frozen
    try:
        eng = XE.ExitEngine(paper_trading=True)

        # ── 1. a debit record flows through evaluate() and DECIDES ──────────
        rec = {"trade_id": "check-exit-1", "strategy": "ORBStrategy",
               "setup_type": "orb_long", "direction": "long",
               "entry_premium": 1.00, "contracts": 1, "status": "open",
               "stop_premium": 0.75, "target_premium": 2.00,
               "trail_activation": 1.50, "underlying_stop": 0.0,
               "underlying_entry": 100.0}
        d_hold = eng.evaluate(dict(rec), 1.00)
        check("evaluate() EXECUTES and returns a decision",
              d_hold is not None and hasattr(d_hold, "should_exit"))
        d_stop = eng.evaluate(dict(rec), 0.70)
        check("the premium floor fires on a breach (0.70 <= stop 0.75)",
              d_stop.should_exit, f"reason={getattr(d_stop, 'exit_reason', None)}")

        # ── 2. the condor leg stop: 15% unhedged / 25% hedged (TRADES.md 5) ──
        def leg():
            return {"trade_id": "check-exit-2", "strategy": "IronCondorStrategy",
                    "setup_type": "condor_leg_put", "is_condor_leg": 1,
                    "condor_leg_num": 1, "entry_premium": 1.00, "contracts": 1,
                    "status": "open", "direction": "neutral",
                    "underlying_stop": 0.0}
        eng._condor_sibling_open = lambda r, default=True: False
        d16_alone = eng._evaluate_condor_leg(leg(), 1.16)
        eng._condor_sibling_open = lambda r, default=True: True
        d16_hedged = eng._evaluate_condor_leg(leg(), 1.16)
        d26_hedged = eng._evaluate_condor_leg(leg(), 1.26)
        check("a LONE leg stops at 15% (-16% exits)",
              d16_alone.should_exit and "condor_stop" in d16_alone.exit_reason,
              f"reason={getattr(d16_alone, 'exit_reason', None)}")
        check("a HEDGED leg holds -16% and stops at 25% (-26% exits)",
              (not d16_hedged.should_exit) and d26_hedged.should_exit)
        # ── 3. the flagship routes to the ORB family (AUDIT F10) ────────────
        sentinel = []
        real_orb = eng._evaluate_orb
        eng._evaluate_orb = lambda *a, **k: (sentinel.append(1), real_orb(*a, **k))[1]
        r_rec = dict(rec, strategy="RunawayContinuation",
                     setup_type="runaway_long")
        eng.evaluate(r_rec, 1.00)
        eng._evaluate_orb = real_orb
        check("RunawayContinuation routes to the ORB exit family "
              "(spec cites orb_trail_stop 96%/85 as its exit)",
              bool(sentinel))
    finally:
        XE.datetime = _real_dt

    if PROBLEMS:
        print(f"\n  {len(PROBLEMS)} problem(s)")
        return 1
    print("=" * 68)
    print("  the exit engine executes, decides, and applies the specced stops")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
