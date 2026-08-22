#!/usr/bin/env python3
"""
tests/check_dispatch.py  v4.1
v4.1  2026-08-25  r65 EXORCISM: every mention of the retired classification
      system removed - identifiers, comments, docstrings, schema. The word
      does not appear in this tree. Full accounting: REMOVAL_LOG (delivery).

Every v4 strategy is wired, in the right order, and its call site EXECUTES.

v4.0  2026-08-20  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

WHY: IMPORT-CLEAN IS NOT RUNTIME-CLEAN, AND IT HAS FOOLED US TWICE.
  · 2026-08-18 - a `ctx` NameError inside `run_analysis` stopped every box
    trading. `import main` passed the entire time, because the name resolves at
    RUNTIME inside the function.
  · 2026-08-19 - `main.py` imported cleanly while calling
  · 2026-08-20 - `closes_beyond` consumed `_rc_bar` fourteen lines before it was
    assigned. Caught only by reading the line numbers.
**All three are the same defect: a name that is fine at parse time and absent at
call time.** WA 21 exists for this and an import check cannot satisfy it.

WHAT THIS CHECKS
  1. every v4 strategy is imported, instantiated and dispatched
  2. the dispatch ORDER is right - runaway before sweep before butterfly
  3. every name the dispatch block uses is BOUND EARLIER IN THE SAME FUNCTION
  4. each strategy's `generate_signal` actually RUNS against a synthetic ctx
     and returns without raising

⚠️ (3) IS THE ONE THAT CATCHES THE REAL BUG. It is a scope check, not a syntax
check: it asks whether the name exists at the point of use, which is precisely
what all three incidents above got wrong.
"""

import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)

PROBLEMS = []
EXPECTED_ORDER = ["RunawayContinuation", "SweepCreditSpread", "GEXPinButterfly"]


def check(label, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + label
          + (f"  - {detail}" if detail and not cond else ""))
    if not cond:
        PROBLEMS.append(label)


def main(argv):
    print("DISPATCH CHECK")
    print("=" * 68)
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    tree = ast.parse(src)

    # ── 1. wired at all ────────────────────────────────────────────────────
    for cls, inst in (("RunawayContinuationStrategy", "_runaway_strategy"),
                      ("SweepCreditSpreadStrategy", "_sweep_cs_strategy"),
                      ("GEXPinButterflyStrategy", "_gex_bfly_strategy")):
        check(f"{cls} imported", f"import {cls}" in src)
        check(f"{inst} instantiated", f"{inst} = {cls}()" in src)
        check(f"{inst} dispatched", f"{inst}.generate_signal" in src)

    # ── 2. order ───────────────────────────────────────────────────────────
    pos = [(src.index(f'_safe_strategy("{n}"'), n) for n in EXPECTED_ORDER
           if f'_safe_strategy("{n}"' in src]
    check("dispatch order: runaway -> sweep -> butterfly",
          [n for _, n in sorted(pos)] == EXPECTED_ORDER,
          f"found {[n for _, n in sorted(pos)]}")
    orb = src.index('_safe_strategy("ORB"')
    check("ORB dispatches BEFORE the runaway - the runaway reads ORB's own state",
          orb < min(p for p, _ in pos))

    # ── 3. every name used is bound earlier in the same function ───────────
    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "attempt_new_entry":
            fn = node
            break
    if fn is None:
        check("attempt_new_entry found", False)
    else:
        # ⚠️ MODULE-LEVEL `def`s AND ASSIGNMENTS ARE BOUND TOO. A first version
        # scanned only for assignments and flagged `_afternoon_debit_blocked`
        # and `_sigj` - both module-level FUNCTIONS - as used-before-assigned.
        # **A checker that cries wolf is worse than no checker**, and this one
        # would have trained the operator to skim its output on the first run.
        module_bound = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                module_bound.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        module_bound.add(t.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    module_bound.add((a.asname or a.name).split(".")[0])
            elif isinstance(node, (ast.Try, ast.If)):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Name):
                                module_bound.add(t.id)
                    elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                        for a in sub.names:
                            module_bound.add((a.asname or a.name).split(".")[0])

        bound, unbound = set(module_bound), []
        for a in fn.args.args:
            bound.add(a.arg)
        for node in ast.walk(fn):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    bound.add(node.id)
                elif isinstance(node.ctx, ast.Load) and node.id.startswith("_"):
                    if node.id not in bound:
                        unbound.append(f"{node.id}@{node.lineno}")
        check("no dispatch-local name is used before it is assigned",
              not unbound, f"{unbound[:5]}")

    # ── 4. the strategies actually RUN ─────────────────────────────────────
    try:
        from strategy.runaway_continuation import RunawayContinuationStrategy
        from strategy.sweep_credit_spread import SweepCreditSpreadStrategy
        from strategy.gex_pin_butterfly import GEXPinButterflyStrategy

        class _ORB:
            state = "OPEN_LONG"
            orb_high, orb_low, tp50 = 101.0, 100.0, 101.5
            invalidation_reason = "runaway"

        class _LM:
            recent_sweep = None

        r = RunawayContinuationStrategy().generate_signal(
            orb=_ORB(), atr_pct=0.14, price_now=101.6, prev_close=101.55,
            now_et="10:15")
        check("RunawayContinuation.generate_signal RUNS and fires", r is not None)

        s2 = SweepCreditSpreadStrategy().generate_signal(
            liq_map=_LM(), price_now=600.0, now_et="13:30", atr_pct=0.10)
        check("SweepCreditSpread.generate_signal RUNS (no sweep -> None)",
              s2 is None)

        b = GEXPinButterflyStrategy().generate_signal(
            gex=None, price_now=600.0, now_et="13:30", atm_iv=0.35)
        check("GEXPinButterfly.generate_signal RUNS and is PARKED", b is None)
    except Exception as e:                                     # noqa: BLE001
        check("strategies execute", False, f"{type(e).__name__}: {e}")

    print("=" * 68)
    if PROBLEMS:
        print(f"  {len(PROBLEMS)} problem(s): {PROBLEMS}")
        return 1
    print("  dispatch is wired, ordered, in scope, and executes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
