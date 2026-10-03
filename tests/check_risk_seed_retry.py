#!/usr/bin/env python3
"""
tests/check_risk_seed_retry.py  v1.0
v1.0  2026-10-03  CND.12 — A FAILED BOOT SEED IS RETRIED, AND SAID.

  🔴 RiskManager._ensure_seeded set _seeded=True BEFORE reading today's P&L
  and swallowed the exception, so one unreadable DB at boot left the session
  P&L at 0 with no retry. Found by OTV4TEST's audit; shared. (is_halted is
  unaffected — it re-reads the DB on every call.)

  R1  the first read fails -> not marked seeded, and a WARNING is logged
  R2  the next call retries and seeds the real P&L
  R3  a loss past the limit on the retry latches the halt flag

  Drives the REAL method with get_trade_logger patched. BORN RED on otv4
  2220461 at R1 R2 R3.

Run:  python3 tests/check_risk_seed_retry.py
"""
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def main():
    from risk.risk_manager import RiskManager
    from database import trade_logger as tl
    rm = RiskManager()
    limit = rm._daily_loss_limit
    real = tl.get_trade_logger
    records = []
    h = logging.Handler()
    h.emit = lambda r: records.append(r)
    lg = logging.getLogger("risk.risk_manager")
    lg.addHandler(h)
    try:
        def _boom():
            raise RuntimeError("store unreadable")
        tl.get_trade_logger = _boom
        rm._ensure_seeded()
        warned = any(r.levelno >= logging.WARNING for r in records)
        check("R1 a failed read is NOT marked seeded, and warns",
              rm._seeded is False and warned, f"seeded={rm._seeded} warned={warned}")

        class _Book:
            def today_summary(self):
                return {"total_pnl": -(limit + 50.0)}
        tl.get_trade_logger = lambda: _Book()
        rm._ensure_seeded()
        check("R2 the next call retries and seeds the real P&L",
              rm._seeded is True and abs(rm._session_pnl_usd + limit + 50.0) < 1e-9,
              f"seeded={rm._seeded} pnl={rm._session_pnl_usd}")
        check("R3 a loss past the limit on the retry latches the halt flag",
              rm._session_halted is True, f"halted={rm._session_halted}")
    finally:
        tl.get_trade_logger = real
        lg.removeHandler(h)
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — the boot seed retries until it reads, and says when it cannot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
