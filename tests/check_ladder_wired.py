#!/usr/bin/env python3
"""
tests/check_ladder_wired.py  v1.0

r104 — THE ENTRY LADDER IS CALLED, WALKS, RATCHETS, AND NEVER CROSSES.

Born RED at 3f23ab5 (r103) on L1..L5: entry_ladder.py had ZERO importers and
every live entry posted a single limit at mark. FRC.1: +$2.70/trade gross edge
against $126/trade round-trip friction — half the half-spread is ~$31/trade.

  L1  entry_ladder / ladder_registry HAVE importers in the live order path
  L2  a walk RESUMES across calls (one rung per tick is the whole design) and
      the ratchet never re-offers a refused price
  L3  the walk never posts WORSE THAN MARK, on either side
  L4  a refusal advances the rung; a fill clears the walk (no stale ratchet)
  L5  PAPER IS UNTOUCHED — no paper path imports the ladder
  L6  the per-rung deadline is a SLICE of the entry budget, not all of it

Run:  python3 tests/check_ladder_wired.py
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

# ── L1 — it is actually called ───────────────────────────────────────────────
importers = []
for rel in ("execution/entry_engine.py", "main.py", "execution/exit_engine.py",
            "strategy/condor_roll.py"):
    src = open(os.path.join(ROOT, rel)).read()
    if "ladder_registry" in src or "entry_ladder" in src:
        importers.append(rel)
check("L1 the ladder has importers in the order path", 
      "execution/entry_engine.py" in importers, f"importers: {importers}")

src = open(os.path.join(ROOT, "execution/entry_engine.py")).read()
tree = ast.parse(src)
fns = {n.name: ast.unparse(n) for n in ast.walk(tree)
       if isinstance(n, ast.FunctionDef)}
check("L1a _place_single_leg prices through the walk",
      "_walk_price" in fns.get("_place_single_leg", ""))
check("L1b _place_butterfly prices through the walk",
      "_walk_price" in fns.get("_place_butterfly", ""))
check("L1c single-leg no longer posts a bare limit_at_mark",
      "limit_at_mark" not in fns.get("_place_single_leg", ""))

# ── L2 — the walk resumes and ratchets ───────────────────────────────────────
from execution import ladder_registry as lr
lr.reset_all()
K = lr.intent_key("TEST 260825C81", "open", "single")
seen = []
for _ in range(6):
    got = lr.price_for(K, "buy", 0.00, 1.00, "QQQ")
    assert got, "price_for returned None on a usable quote"
    seen.append(got[0])
    lr.refuse(K, got[0])
check("L2a the walk advances across calls", len(set(seen)) > 1, f"{seen}")
check("L2b it never re-offers a refused price", len(seen) == len(set(seen)), f"{seen}")
check("L2c and it walks TOWARD mark, never past it",
      all(p <= 0.50 + 1e-9 for p in seen), f"{seen} vs mark 0.50")

# ── L3 — never worse than mark, both sides ───────────────────────────────────
lr.reset_all()
K2 = lr.intent_key("T2", "open", "single")
sells = []
for _ in range(6):
    got = lr.price_for(K2, "sell", 0.00, 1.00, "QQQ")
    sells.append(got[0]); lr.refuse(K2, got[0])
check("L3 selling never posts BELOW mark", all(p >= 0.50 - 1e-9 for p in sells), f"{sells}")

# ── L4 — a fill clears the walk ──────────────────────────────────────────────
lr.reset_all()
K3 = lr.intent_key("T3", "open", "single")
lr.price_for(K3, "buy", 0.40, 0.50, "NFLX")
check("L4a a walk in flight is tracked", lr.active() == 1, f"active={lr.active()}")
lr.clear(K3)
check("L4b a filled walk is cleared (no stale ratchet)", lr.active() == 0)

# ── L5 — paper is untouched ──────────────────────────────────────────────────
paper_fns = [n for n in ("_paper_fill_single", "_paper_fill_butterfly")]
leaked = [f for f in paper_fns
          if "ladder_registry" in fns.get(f, "") or "_walk_price" in fns.get(f, "")]
check("L5 no PAPER path touches the ladder", not leaked, f"{leaked}")

# ── L6 — the rung deadline is a slice ────────────────────────────────────────
import config
from execution.entry_engine import EntryEngine
rd = EntryEngine._rung_deadline()
total = float(getattr(config, "LIVE_ENTRY_DEADLINE_SECONDS", 20.0))
check("L6a a rung gets a SLICE of the entry budget", rd < total, f"{rd}s of {total}s")
check("L6b and never so short a fillable price is abandoned unseen", rd >= 4.0, f"{rd}s")
import inspect
from execution.order_confirm import confirm_order_fill
check("L6c confirm_order_fill accepts a per-call deadline",
      "deadline_s" in inspect.signature(confirm_order_fill).parameters)

print(f"\n{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} problem(s) {FAILURES}")
sys.exit(1 if FAILURES else 0)
