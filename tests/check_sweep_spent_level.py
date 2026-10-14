#!/usr/bin/env python3
"""
tests/check_sweep_spent_level.py  v1.0
v1.0  2026-10-14  r490 / SWEEP.13 — A LOSING SWEEP SPENDS ITS LEVEL, AND THE SWEEP'S
      INTERACTION LATCH IS SET WHERE SWEEPS EXECUTE.

  SPX 2026-10-14 sold puts under NY Low (R3) 7731.26 (the 10-08 NY session low)
  three times in 30 minutes, the third one second after the second stopped out,
  -$545. The r154/r167 level lock had never armed: log_exit read the column
  `is_credit_vertical`, which the trades table has never had, and `pool_price`
  was in the CREATE TABLE but never migrated onto an existing trades.db.

  Drives the REAL TradeLogger on a scratch trades.db shaped like the boxes'
  (pool_price dropped), and the real sweep lock:
  L1  an existing trades.db without pool_price gains the column at boot
  L2  a losing sweep at NY Low (R3) 7731.26 spends 7731.26 (put side)
  L3  the lock is keyed by PRICE: another rung with the same label (NY Low
      (R2) 7779.34) and the call side of 7731.26 stay tradeable
  L4  a WINNING close spends nothing
  L5  the stop-out logs no "could not mark the level spent" warning
  L6  a restart (fresh process state, new TradeLogger) keeps 7731.26 spent;
      a loss closed YESTERDAY is not re-armed
  L7  a stop-out with no level price says so (WARNING), it does not raise
  L8  main._execute_condor_leg latches the sweep interaction
      (mark_event_fired_key) before it writes the record

Run:  python3 tests/check_sweep_spent_level.py   (exit 0 green, 1 red)
"""
import ast
import glob as _glob
import logging
import os
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
for _sp in _glob.glob(os.path.join(_root, "venv", "lib", "python*", "site-packages")):
    if _sp not in sys.path:                                  # r106 venv bootstrap
        sys.path.insert(1, _sp)
_S = tempfile.mkdtemp(prefix="check_sweep_spent_level_")
for _k, _f in (("OT_TRADES_DB", "trades.db"), ("OT_DERIVED_DB", "d.db"), ("OT_RESTING_DB", "r.db")):
    os.environ.setdefault(_k, os.path.join(_S, _f))
os.environ.setdefault("OT_SIGNAL_JOURNAL_DIR", os.path.join(_S, "sj"))
os.environ.setdefault("OT_LOG_FILE", os.path.join(_S, "bot.log"))
os.environ.setdefault("OT_INSTRUMENT", "SPX")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Grab(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, rec):
        self.lines.append((rec.levelno, rec.getMessage()))


def _cols(db):
    con = sqlite3.connect(db)
    c = {r[1] for r in con.execute("PRAGMA table_info(trades)")}
    con.close()
    return c


def _reset_lock(sc):
    sc._SPENT.clear()
    sc._SPENT_DAY = ""


def main():
    from database import trade_logger as tl
    from strategy import sweep_credit_spread as sc

    grab = _Grab()
    logging.getLogger().addHandler(grab)
    logging.getLogger().setLevel(logging.DEBUG)

    # ── a trades.db shaped like the boxes': the table exists, pool_price absent
    db = os.path.join(_S, "gate_trades.db")
    tl.TradeLogger(db_path=db, paper_trading=True)
    con = sqlite3.connect(db)
    con.execute("ALTER TABLE trades DROP COLUMN pool_price")
    con.commit()
    con.close()
    pre = "pool_price" in _cols(db)
    T = tl.TradeLogger(db_path=db, paper_trading=True)
    check("L1 boot migrates pool_price onto an existing trades.db",
          not pre and "pool_price" in _cols(db),
          f"before={pre} after={'pool_price' in _cols(db)}")

    _reset_lock(sc)

    def sweep(tid, pool, name, side="put", **f):
        T.log_entry(tl.make_record(
            trade_id=tid, symbol="SPX", strategy="SweepCreditSpread",
            setup_type="sweep_credit_spread", option_side=side, contracts=6,
            entry_premium=1.90, credit_received=1.90, pool_price=pool,
            swept_level_name=name, underlying_stop=0.0, paper_trade=1,
            is_short_position=1, status="open", **f))

    sweep("t1", 7731.26, "NY Low (R3)")
    grab.lines.clear()
    T.log_exit(trade_id="t1", exit_price=2.25, pnl_usd=-210.0,
               exit_reason="premium_stop_15% pnl=-18.4%")
    spent, why = sc.is_spent("SPX", "put", 7731.26)
    check("L2 a losing sweep spends NY Low (R3) 7731.26", spent, f"why={why!r}")

    check("L3 another 'NY Low' rung (7779.34) is NOT spent",
          not sc.is_spent("SPX", "put", 7779.34)[0])
    check("L3b the call side of 7731.26 is NOT spent",
          not sc.is_spent("SPX", "call", 7731.26)[0])

    sweep("t2", 7779.34, "NY Low (R2)")
    T.log_exit(trade_id="t2", exit_price=1.00, pnl_usd=+540.0, exit_reason="nickel")
    check("L4 a WINNING close spends nothing",
          not sc.is_spent("SPX", "put", 7779.34)[0])

    bad = [m for lv, m in grab.lines if "could not mark the level spent" in m]
    check("L5 the stop-out raised nothing into the close path", not bad, f"{bad[:1]}")

    # a loss closed YESTERDAY must not be re-armed by the reseed
    sweep("t0", 7700.51, "NY Low (R4)")
    T.log_exit(trade_id="t0", exit_price=2.50, pnl_usd=-300.0, exit_reason="premium_stop_15%")
    con = sqlite3.connect(db)
    con.execute("UPDATE trades SET exit_time=? WHERE trade_id='t0'",
                ("2026-01-02T15:00:00+00:00",))
    con.commit()
    con.close()

    _reset_lock(sc)                                     # a restart: fresh memory
    tl.TradeLogger(db_path=db, paper_trading=True)
    check("L6 a restart keeps 7731.26 SPENT (rebuilt from trades.db)",
          sc.is_spent("SPX", "put", 7731.26)[0])
    check("L6b a loss closed yesterday is NOT re-armed",
          not sc.is_spent("SPX", "put", 7700.51)[0])

    grab.lines.clear()
    T.log_entry(tl.make_record(
        trade_id="t3", symbol="SPX", strategy="SweepCreditSpread",
        option_side="put", contracts=1, entry_premium=1.0, pool_price=0.0,
        swept_level_name="", underlying_stop=0.0, paper_trade=1, status="open"))
    raised = None
    try:
        T.log_exit(trade_id="t3", exit_price=1.2, pnl_usd=-20.0, exit_reason="stop")
    except Exception as e:                                   # noqa: BLE001
        raised = e
    warned = any(lv >= logging.WARNING and "CANNOT be spent" in m for lv, m in grab.lines)
    check("L7 a stop-out with no level price warns and does not raise",
          raised is None and warned, f"raised={raised!r} warned={warned}")

    # ── L8: the path sweeps actually execute through latches the interaction
    src = open(os.path.join(_root, "main.py")).read()
    fn = next((n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "_execute_condor_leg"), None)
    latch = log = None
    if fn is not None:
        for n in ast.walk(fn):
            if isinstance(n, ast.Call):
                f = n.func
                nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if nm == "mark_event_fired_key" and latch is None:
                    latch = n.lineno
                if nm == "log_entry" and log is None:
                    log = n.lineno
    check("L8 _execute_condor_leg latches the sweep interaction before log_entry",
          latch is not None and log is not None and latch < log,
          f"mark_event_fired_key line={latch} log_entry line={log}")

    print()
    if FAILED:
        print(f"RED: {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
