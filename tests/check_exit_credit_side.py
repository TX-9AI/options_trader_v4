#!/usr/bin/env python3
"""
tests/check_exit_credit_side.py  v1.0
v1.0  2026-09-10  r345 / RPT.27 — the exit path must resolve the side, not
      read one field.

🔴 WHY THIS IS DIFFERENT FROM RPT.26. That was a reporting sign error. This is
an ORDER. `is_short_position` had no writer until r343, so every credit spread
reached `_close_order` as 0 and resolved to **SELL_TO_CLOSE — selling more
short instead of buying to close.** Paper absorbed it; a live broker would
not. The stop's `pnl_pct` had the same input and measured the wrong direction
of premium move.

  X1  a historical credit row (flag 0, credit > 0) resolves SHORT
  X2  a condor leg with neither flag nor credit still resolves SHORT
  X3  a debit resolves LONG — the half that was accidentally correct
  X4  the flag wins when set
  X5  NEITHER exit-path site reads `is_short_position` directly any more
      (AST: the raw key must not appear in those two functions)
  X6  `r_ledger.is_credit` and `trade_logger.is_credit_position` AGREE across
      the truth table — two call sites, one rule, pinned rather than trusted
"""
import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def _resolver():
    """Compile is_credit_position from source — trade_logger imports config
    and a timezone library that live on the boxes, and this gate runs on
    control at land time (the r340 lesson)."""
    src = open(os.path.join(REPO, "database", "trade_logger.py"),
               encoding="utf-8").read()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == "is_credit_position":
            ns = {}
            exec(compile(ast.parse(ast.get_source_segment(src, node).lstrip()),
                         "<resolver>", "exec"), ns)
            return ns["is_credit_position"], src
    return None, src


def main():
    fn, _src = _resolver()
    if fn is None:
        print("  FAIL  trade_logger.is_credit_position does not exist")
        return 1

    hist = {"is_short_position": 0, "credit_received": 0.435,
            "is_condor_leg": 1, "strategy": "SweepCreditSpread"}
    check("X1", fn(hist) is True, "flag 0 + credit 0.435 -> SHORT")

    leg = {"is_short_position": 0, "credit_received": 0,
           "is_condor_leg": 1, "strategy": "TrendCreditSpread"}
    check("X2", fn(leg) is True, "condor_leg with no credit -> SHORT")

    debit = {"is_short_position": 0, "credit_received": 0,
             "is_condor_leg": 0, "strategy": "ORBStrategy"}
    check("X3", fn(debit) is False, "ORB debit -> LONG")

    flagged = {"is_short_position": 1}
    check("X4", fn(flagged) is True, "flag set -> SHORT")

    # X5 — the two exit-path functions must not read the raw key.
    esrc = open(os.path.join(REPO, "execution", "exit_engine.py"),
                encoding="utf-8").read()
    tree = ast.parse(esrc)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        seg = ast.get_source_segment(esrc, node) or ""
        code = "\n".join(l for l in seg.splitlines()
                         if not l.lstrip().startswith("#"))
        if '"is_short_position"' in code or "'is_short_position'" in code:
            offenders.append(node.name)
    check("X5", not offenders,
          "still reads the raw key in: {}".format(offenders) if offenders
          else "no direct reads in exit_engine")

    # X6 — the reporting resolver and the execution resolver must agree.
    try:
        from r_ledger import is_credit as ledger_credit
    except Exception as exc:                                    # noqa: BLE001
        check("X6", False, "r_ledger.is_credit missing: {}".format(exc))
    else:
        rows = [hist, debit, flagged,
                {"is_short_position": 0, "credit_received": 0},
                {"is_short_position": 0, "credit_received": None}]
        # the ledger sees only flag + credit; compare on that shared domain
        bad = [r for r in rows if bool(ledger_credit(r)) != bool(fn(r))]
        check("X6", not bad,
              "disagree on {}".format(bad) if bad
              else "{} row(s), both resolvers agree".format(len(rows)))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
