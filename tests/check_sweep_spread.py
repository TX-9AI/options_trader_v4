#!/usr/bin/env python3
"""
tests/check_sweep_spread.py  v1.0

r99 — THE SWEEP CREDIT SPREAD CAN FIRE, AND IT FIRES AS A CREDIT SPREAD.

Born RED at df44518 (r98) on S1, S2, S4, S5, S6. Plain script (WA 36).

  S1  is_valid accepts a ONE-SIDED credit vertical (call side / put side)
  S2  is_valid FAILS CLOSED: naked short, wing without short, wing inside short,
      zero credit, two-sided with one side broken
  S3  a four-legged signal still validates (no regression)
  S4  main.py's sweep block never does `signal = sc_sig` and DOES route
      `_execute_condor_leg(sc_sig, ...)` behind `_can_open_credit_spread` (AST)
  S5  structure.of("SweepCreditSpread") is CONDOR_LEG — lone-vertical
      management (15% floor, 15:45), not the TC.6 breach arm
  S6  `_execute_condor_leg` stamps the sweep's OWN strategy name and its own
      stop pct (AST + source shape; the live branch is not executable here)

Run:  python3 tests/check_sweep_spread.py
"""
from __future__ import annotations
import ast, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

from strategy.base_strategy import OptionsSignal
from data.options_chain import OptionContract
from strategy.structure import of, Structure, is_credit_vertical, is_trend_participation

def c(strike, typ="C"):
    return OptionContract(symbol=f"X {strike}{typ}", strike=strike, option_type=typ, bid=0.4, ask=0.5, mark=0.45)

def sig(**kw):
    s = OptionsSignal(strategy_name="SweepCreditSpread", is_credit_vertical=True, net_credit=0.35)
    for k, v in kw.items():
        setattr(s, k, v)
    return s

# S1
check("S1a call-side vertical valid", sig(short_call_contract=c(100), long_call_contract=c(105)).is_valid)
check("S1b put-side vertical valid",  sig(short_put_contract=c(100,"P"), long_put_contract=c(95,"P")).is_valid)
# S2
check("S2a naked short call INVALID", not sig(short_call_contract=c(100)).is_valid)
check("S2b naked short put INVALID",  not sig(short_put_contract=c(100,"P")).is_valid)
check("S2c wing without short INVALID", not sig(long_call_contract=c(105)).is_valid)
check("S2d wing INSIDE short (debit shape) INVALID",
      not sig(short_call_contract=c(105), long_call_contract=c(100)).is_valid)
check("S2e put wing ABOVE short INVALID",
      not sig(short_put_contract=c(95,"P"), long_put_contract=c(100,"P")).is_valid)
check("S2f zero credit INVALID", not sig(short_call_contract=c(100), long_call_contract=c(105), net_credit=0.0).is_valid)
check("S2g clean call side + naked put side INVALID",
      not sig(short_call_contract=c(100), long_call_contract=c(105), short_put_contract=c(90,"P")).is_valid)
check("S2h no contracts at all INVALID", not sig().is_valid)
# S3
check("S3 four-legged condor still valid",
      sig(short_call_contract=c(100), long_call_contract=c(105),
          short_put_contract=c(90,"P"), long_put_contract=c(85,"P")).is_valid)

# S4 — dispatch routing, by AST
src = open(os.path.join(ROOT, "main.py")).read()
tree = ast.parse(src)
sweep_assigns = 0; sweep_exec = False; sweep_gated = False
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        if (isinstance(node.value, ast.Name) and node.value.id == "sc_sig"
                and any(isinstance(t, ast.Name) and t.id == "signal" for t in node.targets)):
            sweep_assigns += 1
    if isinstance(node, ast.If):
        # an `if` whose test calls _can_open_credit_spread with sc_sig, whose body executes the leg
        test_src = ast.unparse(node.test)
        if "_can_open_credit_spread" in test_src and "sc_sig" in test_src:
            body_src = "\n".join(ast.unparse(b) for b in node.body)
            if "_execute_condor_leg(sc_sig" in body_src:
                sweep_exec = True; sweep_gated = True
check("S4a main.py never assigns `signal = sc_sig`", sweep_assigns == 0, f"{sweep_assigns} assignment(s)")
check("S4b sweep executes via _execute_condor_leg behind _can_open_credit_spread", sweep_exec and sweep_gated)

# S5 — routing of the persisted record
rec = {"strategy": "SweepCreditSpread", "setup_type": "sweep_credit_call", "is_condor_leg": 1}
check("S5a structure.of(sweep) is CONDOR_LEG", of(rec) is Structure.CONDOR_LEG, str(of(rec)))
check("S5b sweep is a credit vertical", is_credit_vertical(rec))
check("S5c sweep is NOT trend participation (would lose its 15% stop)", not is_trend_participation(rec))
check("S5d TC.6 row still routes to TREND_PARTICIPATION",
      of({"strategy": "TrendCreditSpread", "setup_type": "trend_credit_short"}) is Structure.TREND_PARTICIPATION)

# S6 — _execute_condor_leg's record identity, by AST
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_execute_condor_leg")
fsrc = ast.unparse(fn)
check("S6a _execute_condor_leg names SweepCreditSpread as a strategy identity", "SweepCreditSpread" in fsrc)
check("S6b _execute_condor_leg reads the signal's max_loss_pct for the stop", "max_loss_pct" in fsrc)

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
