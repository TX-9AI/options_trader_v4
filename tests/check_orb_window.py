#!/usr/bin/env python3
"""tests/check_orb_window.py  v1.0
THE ORB ENTRY WINDOW IS 11:30, IT AGREES WITH THE DEBIT BLOCK, AND EVERY COPY
OF IT AGREES WITH config.

v1.0  2026-08-30  r193 — the window moved 11:00 -> 11:30 and the pool stopped
      moving the target. Born red at r192 (81a6233): the constant reads (11,0)
      there, two test files hardcode their own (11,0), and orb_strategy pulls
      the target to a named pool.

🔴 W3 EXISTS BECAUSE THE CONSTANT HAD THREE COPIES AND ONLY ONE OF THEM IS THE
ONE THAT TRADES. `tests/cascade_harness.py` and `tests/cascade_real.py` each
declared their own `ORB_NO_ENTRY_AFTER_ET = (11, 0)`. A harness rehearsing an
11:00 window against a fleet running 11:30 stays GREEN while measuring a
different system — the same fourth-copy shape as the PANEL mirror. This check
makes a fourth copy impossible to add quietly.

🔑 W2 IS THE ONE THAT WOULD COST A SESSION IF IT DRIFTED. Both cutoffs are
`>=` tests: the ORB window at orb_engine ~441 and the long-debit block in
`_afternoon_debit_blocked`. Equal values mean entries run to 11:29:59 and the
block takes over at 11:30:00 — no gap, no overlap. If they ever diverge, either
ORB stops arming while trades that depend on its state keep firing (the exact
contradiction the 08-20 extension was written to fix), or an ORB entry is
permitted into a window where the debit block refuses it and the refusal
arrives from somewhere confusing.

Run:  python3 tests/check_orb_window.py
"""
import os
import re
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")

_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    import config

    orb = tuple(config.ORB_NO_ENTRY_AFTER_ET)
    debit = tuple(config.DEBIT_DIRECTIONAL_CUTOFF_ET)

    check("W1 the ORB entry window closes at 11:30", orb == (11, 30), str(orb))

    check("W2 the ORB window and the long-debit block are the SAME boundary",
          orb == debit, f"orb={orb} debit={debit}")

    # ── W3: every copy of the constant, anywhere in the tree ──────────────
    pat = re.compile(r"^\s*ORB_NO_ENTRY_AFTER_ET\s*=\s*\((\d+),\s*(\d+)\)", re.M)
    copies = {}
    for base, _dirs, files in os.walk(_root):
        if os.sep + ".git" in base:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(base, fn)
            try:
                body = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for m in pat.finditer(body):
                copies[os.path.relpath(path, _root)] = (int(m.group(1)), int(m.group(2)))
    wrong = {k: v for k, v in copies.items() if v != orb}
    check(f"W3 all {len(copies)} declared copies of the window agree with config",
          not wrong and len(copies) >= 1, f"disagreeing: {wrong or 'none'}")

    # ── W4: the ORB engine reads the constant, it does not restate it ─────
    eng = open(os.path.join(_root, "analysis", "orb_engine.py"),
               encoding="utf-8").read()
    check("W4 orb_engine compares against the imported constant",
          "(now.hour, now.minute) >= ORB_NO_ENTRY_AFTER_ET" in eng)

    # ── W5/W6: the pool records but does not steer ────────────────────────
    # ⚠️ Shape of the ASSIGNMENT, not a mention: orb_strategy's v4.3 changelog
    # and the notes line both name `adjusted_target` while describing the
    # change, so a bare string match would go red on its own documentation
    # (WORKING_AGREEMENT §20).
    st = open(os.path.join(_root, "strategy", "orb_strategy.py"),
              encoding="utf-8").read()
    check("W5 the target is the pure measured move, not a pool",
          "target_100 = orb.target_100pct" in st
          and 'target_100 = liq_result.get("adjusted_target"' not in st)
    check("W6 pool presence is still RECORDED — the study stays possible",
          'result["target_adjusted"]   = True' in st
          and "RECORDED ONLY" in st)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_orb_window: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
