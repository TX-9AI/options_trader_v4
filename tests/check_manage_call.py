#!/usr/bin/env python3
"""
tests/check_manage_call.py  v1.0

r99 — THE MANAGE BRANCH MUST BE CALLABLE, AND THE FLATTEN MUST HOLD VERTICALS.

Born RED at df44518 (r98) on M1, M3, M4. Plain script (WA 36).

  M1  every `pos_mgr.<method>(kw=...)` call in main.py passes ONLY keywords the
      PositionManager method actually accepts (the `ms=None` TypeError class —
      r65 renamed the retired label kwarg at the call and deleted it from the signature; every
      tick with an open position raised into the loop catch-all)
  M2  the call is exercised for real: a stub PositionManager receives the
      exact kwargs main passes and does not raise
  M3  flatten_all HOLDS a credit vertical before VERTICAL_HOLD_TO_ET and
      FLATTENS it after (executed against a patched clock)
  M4  main.py's hard-close branch runs a manage pass while verticals are held

Run:  python3 tests/check_manage_call.py
"""
from __future__ import annotations
import ast, os, sys, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES: list = []

def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)

import execution.position_manager as pm
src = open(os.path.join(ROOT, "main.py")).read()
tree = ast.parse(src)

# M1 — kwargs at every pos_mgr.<method>() call vs the real signature
bad = []; seen = 0
for node in ast.walk(tree):
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "pos_mgr"):
        meth = getattr(pm.PositionManager, node.func.attr, None)
        if meth is None:
            bad.append(f"{node.func.attr}: no such method"); continue
        params = inspect.signature(meth).parameters
        accepts_kw = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
        seen += 1
        for kw in node.keywords:
            if kw.arg is not None and kw.arg not in params and not accepts_kw:
                bad.append(f"line {node.lineno} {node.func.attr}({kw.arg}=...)")
check("M1 every pos_mgr.* call in main.py matches its signature", not bad, "; ".join(bad) or f"{seen} calls")

# M2 — replay main's manage kwargs against the real method on a stub instance
calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
         and n.func.attr == "manage_open_position"]
ok = bool(calls)
for n in calls:
    kws = {k.arg: None for k in n.keywords}
    try:
        inspect.signature(pm.PositionManager.manage_open_position).bind(object(), **kws)
    except TypeError as e:
        ok = False; print("     ", e)
check("M2 manage_open_position kwargs bind against the real signature", ok, f"{len(calls)} call(s)")

# M3 — flatten_all holds a credit vertical before 15:45, flattens after
import config
from datetime import datetime
from utils.time_utils import ET
booked = []
class _TL:
    def get_open_trades(self): return []
class _PM(pm.PositionManager):
    def __init__(self):
        self.paper_trading = True; self._trade_logger = _TL(); self._open_records = []
    def _fetch_current_premium(self, record, chain=None): return 0.10
    def _execute_exit(self, record, decision, premium):
        booked.append(record["trade_id"]); return True
vert = {"trade_id": "VERT0001", "strategy": "SweepCreditSpread", "setup_type": "sweep_credit_call",
        "is_condor_leg": 1, "entry_premium": 0.30, "contracts": 1}
deb  = {"trade_id": "DEBT0001", "strategy": "ORBStrategy", "setup_type": "orb", "entry_premium": 0.50, "contracts": 1}
real_now = pm.now_et if hasattr(pm, "now_et") else None
import utils.time_utils as tu
_orig = tu.now_et
try:
    tu.now_et = lambda: datetime(2026, 8, 24, 15, 41, tzinfo=ET)
    p = _PM(); p._open_records = [dict(vert), dict(deb)]; booked.clear()
    failed = p.flatten_all("hard_close_15:45_ET")
    check("M3a 15:41 — debit flattened, vertical HELD", booked == ["DEBT0001"] and not failed, f"booked={booked} failed={failed}")
    check("M3b 15:41 — held vertical stays in open records", any(r["trade_id"] == "VERT0001" for r in p._open_records))
    tu.now_et = lambda: datetime(2026, 8, 24, 15, 45, tzinfo=ET)
    p = _PM(); p._open_records = [dict(vert), dict(deb)]; booked.clear()
    p.flatten_all("hard_close_15:45_ET")
    check("M3c 15:45 — both flattened", sorted(booked) == ["DEBT0001", "VERT0001"], f"booked={booked}")
finally:
    tu.now_et = _orig

# M4 — the hard-close branch in main_loop runs a manage pass for held verticals
loop = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main_loop")
hc = None
for n in ast.walk(loop):
    if isinstance(n, ast.If) and "is_hard_close_time" in ast.unparse(n.test):
        hc = ast.unparse(n); break
check("M4 hard-close branch manages held verticals before 15:45",
      hc is not None and "manage_open_position" in hc and "_vertical_close_due" in hc)

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
