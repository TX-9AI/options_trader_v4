#!/usr/bin/env python3
"""
tests/check_cap_event.py  v1.0
v1.0  2026-10-03  r459 / AUD.7 — A CAP LATCH WRITES ONE circuit_breaker_events ROW.

  TradeLogger.log_circuit_breaker had ZERO callers on mainline, so the table
  query.py shows and s3_push pushes was always empty; the only record of a cap
  episode was a log line and a page. Mirrors OTV4TEST r199's "hit" site
  (mainline latches; there is no re-arm transition here).

  Drives the REAL RiskManager.is_halted with today's realized P&L forced past
  the limit, against a scratch TradeLogger (never the live store):
  E1  the first breach writes ONE row with reason 'daily_cap_hit'
  E2  a second is_halted() in the same latch writes NO second row
  E3  a failing page WARNS (it was `except: pass`) and the halt still latches
  BORN RED on otv4 d87bafb at E1 E2 E3 (E2 because no row is ever written there).

Run:  python3 tests/check_cap_event.py
"""
import logging
import os
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def main():
    from database import trade_logger as tl
    from risk.risk_manager import RiskManager
    import notifications.alert_manager as am
    tmp = tempfile.mkdtemp(prefix="check_cap_event_")
    db = os.path.join(tmp, "trades.db")
    T = tl.TradeLogger(db_path=db, paper_trading=True)
    real_tl, real_am = tl._trade_logger, am.get_alert_manager
    tl._trade_logger = T

    class _Pager:
        def _send(self, msg):
            raise RuntimeError("telegram down")
    am.get_alert_manager = lambda: _Pager()
    records = []
    h = logging.Handler()
    h.emit = lambda r: records.append(r)
    lg = logging.getLogger("risk.risk_manager")
    lg.addHandler(h)
    try:
        rm = RiskManager()
        rm.day_realized_pnl = lambda: -(rm._daily_loss_limit + 10.0)
        halted = rm.is_halted()
        rows = sqlite3.connect(db).execute(
            "SELECT reason FROM circuit_breaker_events").fetchall()
        check("E1 the first breach writes ONE 'daily_cap_hit' row",
              rows == [("daily_cap_hit",)], f"rows={rows}")
        rm.is_halted()
        rows2 = sqlite3.connect(db).execute(
            "SELECT COUNT(*) FROM circuit_breaker_events").fetchone()[0]
        check("E2 a second call inside the latch writes no second row", rows2 == 1,
              f"count={rows2}")
        warned = any(r.levelno >= logging.WARNING and "page NOT sent" in r.getMessage()
                     for r in records)
        check("E3 a failing page WARNS and the halt still latches",
              warned and halted is True, f"warned={warned} halted={halted}")
    finally:
        tl._trade_logger = real_tl
        am.get_alert_manager = real_am
        lg.removeHandler(h)
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — a cap latch is recorded once, and a failed page is said")
    return 0


if __name__ == "__main__":
    sys.exit(main())
