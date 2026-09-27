#!/usr/bin/env python3
"""tests/check_phantom_recovered.py — v1.0
A RECOVERED PHANTOM FILL BOOKS; IT DOES NOT RAISE.

v1.0  2026-09-27 — otv4 r452. SHARED FIX (WA §38.11) with OTV4TEST r165 (c35bf48),
      which found it. TradeLogger.close_phantom's RECOVERED branch wrote
      `exit_price`, a column the trades table has never had (it is exit_premium),
      so the first LIVE phantom whose real closing fill was recovered from order
      history (main.py -> match_closing_fills -> close_phantom(exit_price=...,
      pnl_usd=...)) raised OperationalError and left the row OPEN with no P&L.
      Paper never reaches the branch, which is why nothing ever showed it.
  X12  the peer's check, lines 131-139 of their tests/check_expiry_settlement.py
       @ c35bf48, carried BYTE-IDENTICAL (sha256 a6055495…, verified by hash from
       the message text, not retyped). Only these 9 lines are shared; the file
       around them is ours. The names X12 relies on are defined below as theirs
       are: TL, make_record, long_itm, c, check.
       ⚠️ ONE DELIBERATE DIFFERENCE: otv4's TradeLogger does NOT read
       OT_TRADES_DB, so TL is built with an explicit db_path — without it this
       check would write into the LIVE ~/options-trader/trades.db.
  X13  (ours) the fill-UNKNOWN branch is unchanged: closed, pnl 0.0, no raise.

🔴 NOTHING REAL IS TOUCHED: a scratch trades.db in a mkdtemp, HOME redirected.
Run:  python3 tests/check_phantom_recovered.py
"""
import os, sys, sqlite3, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_s = tempfile.mkdtemp(prefix="check_phantom_recovered_")
os.environ["HOME"] = _s
os.environ["OT_TRADES_DB"] = os.path.join(_s, "trades.db")
os.environ.setdefault("OT_INSTRUMENT", "QQQ")
sys.path.insert(0, ROOT)
from database.trade_logger import TradeLogger, make_record

FAILED = []
def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        FAILED.append(name.split()[0])

TL = TradeLogger(db_path=os.environ["OT_TRADES_DB"], paper_trading=True)
long_itm = {"symbol": "QQQ", "expiry": "2026-09-25", "option_side": "call", "contracts": 2,
            "strategy": "Breakout", "strike": 700.0, "entry_premium": 1.00}
c = sqlite3.connect(os.environ["OT_TRADES_DB"]); c.row_factory = sqlite3.Row

# ── X12 the pre-existing close_phantom column bug (v4 port, 08-19) ───────────
try:
    TL.log_entry(make_record(trade_id="x12-rec", **long_itm))
    TL.close_phantom("x12-rec", reason="phantom_closed_at_broker_pnl_recovered", exit_price=1.55, pnl_usd=110.0)
    r12 = c.execute("select exit_premium,pnl_usd,status from trades where trade_id='x12-rec'").fetchone()
    ok12, d12 = (r12 is not None and r12["exit_premium"] == 1.55 and r12["pnl_usd"] == 110.0 and r12["status"] == "closed"), str(dict(r12) if r12 else None)
except Exception as exc:
    ok12, d12 = False, f"{type(exc).__name__}: {exc}"
check("X12 a RECOVERED phantom fill books (exit_premium + pnl), no OperationalError", ok12, d12)

# ── X13 (otv4) the fill-UNKNOWN branch is unchanged ─────────────────────────
try:
    TL.log_entry(make_record(trade_id="x13-unk", **long_itm))
    TL.close_phantom("x13-unk", reason="phantom_closed_at_broker")
    r13 = c.execute("select pnl_usd,status from trades where trade_id='x13-unk'").fetchone()
    ok13, d13 = (r13 is not None and r13["pnl_usd"] == 0.0 and r13["status"] == "closed"), str(dict(r13) if r13 else None)
except Exception as exc:
    ok13, d13 = False, f"{type(exc).__name__}: {exc}"
check("X13 a phantom with NO recovered fill still closes at pnl 0.0 (unchanged)", ok13, d13)

print("GREEN" if not FAILED else f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
sys.exit(1 if FAILED else 0)
