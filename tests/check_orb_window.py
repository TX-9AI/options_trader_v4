#!/usr/bin/env python3
"""tests/check_orb_window.py  v1.1
THE ORB ENTRY WINDOW IS 11:30, IT AGREES WITH THE DEBIT BLOCK, AND EVERY COPY
OF IT AGREES WITH config.

v1.1  2026-09-12  r365 — W6 widened and W7 added, both on the operator's
      ruling that the ORB acts on NO awareness of levels, period. W6 no longer
      asks only that the target is unadjusted; it asks that the read does not
      exist — no map parameter, no analysis method, no result subscript. W7 is
      new and pins the strike: the engine's selection on every path, never
      re-derived from a pool. Born red at 6e193b98 on W6 and W7. BOTH ARE
      ANCHORED ON CODE SHAPE rather than words, because v4.6's changelog must
      name pools and levels to describe removing them and a bare word match
      would go red on its own documentation (§20) — W7 did exactly that on its
      first run and was re-anchored on the assignment.
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
    # 🔴 W6 REWRITTEN WITH THE RULING (r365), NOT LOOSENED TO STAY GREEN. It
    # asserted the pool was still RECORDED — the counterfactual r193 kept. The
    # operator's 2026-09-12 ruling removes ORB's level awareness entirely, so
    # the property to pin is the opposite one: this strategy holds NO liquidity
    # read of any kind.
    # ⚠️ ANCHORED ON CODE SHAPE, NOT THE WORDS. The v4.6 changelog above
    # necessarily names pools and levels while describing their removal, so a
    # bare word match would go red on its own documentation (§20). A definition
    # header and a subscript cannot appear in prose.
    check("W6 the ORB holds NO liquidity read — no map, no analysis, no result",
          "def _analyze_liquidity(" not in st
          and "liq_result[" not in st
          and "liq_map" not in st)
    # r365 — and the strike comes from the engine on EVERY path. The branch that
    # re-derived it fired on 8.7% of ORB trades, which is why this is pinned.
    # ⚠️ THE ASSIGNMENT, NOT THE CALL — and this check went red on its own
    # documentation the first time it ran: v4.6's changelog quotes the old
    # expression verbatim while explaining its removal, which is §20 exactly.
    # A re-derivation is an ASSIGNMENT to target_strike; prose cannot be one.
    check("W7 the strike is the engine's selection, never re-derived from a pool",
          "target_strike = orb.target_strike" in st
          and "target_strike = round_to_strike(" not in st)

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_orb_window: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
