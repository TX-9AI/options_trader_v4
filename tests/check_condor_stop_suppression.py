#!/usr/bin/env python3
"""
tests/check_condor_stop_suppression.py  v1.0
CONDOR STOP SUPPRESSION: the per-leg premium stop applies to a LONE vertical
only — never the formed condor — and RE-ARMS when the leg is alone again.

v1.0  2026-08-24  Born RED at r89b (exit_engine v4.3 armed a 25% stop on the
  HEDGED branch); green at exit_engine v4.4 / trade_logger v4.3. Pins:
  S1  lone leg: a premium move past the 15% floor EXITS (condor_stop, lone)
  S2  complement open: the SAME move does NOT exit — stop suppressed
  S3  the suppress edge persists stop_suppressed_ts / stop_suppressed_by
      (NEW fields via update_fields — stop_premium is never the channel)
  S4  complement closed: the SAME move EXITS again — RE-ARMED.
      ⚠️ THE DIRECTION A ONE-WAY FIX FAILS: a pin that only checks S2
      passes a naked full-sized position with no stop.
  S5  the re-arm edge CLEARS both fields (record and DB write)
  S6  stop_premium on the record is byte-identical through all of it —
      the immutable entry-time floor is never mutated (v3.1 trail lesson)
  S7  a trend credit spread (TCS) never picks up suppression fields —
      its branch returns before the stop block and must stay uncontaminated
  S8  both columns exist in trade_logger's schema AND migration list

All executed against planted state, no real broker calls, no repo-root
artifacts (nothing is written outside /tmp).
Run:  cd ~/options-trader && python3 tests/check_condor_stop_suppression.py
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}"
          + (f"  — {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


# ── planted state ─────────────────────────────────────────────────────────────

class FakeTradeLogger:
    """Open-trades store + update_fields recorder. No sqlite, no disk."""

    def __init__(self, open_trades):
        self.open_trades = list(open_trades)
        self.updates: list = []

    def get_open_trades(self):
        return list(self.open_trades)

    def update_fields(self, trade_id, **fields):
        self.updates.append((trade_id, dict(fields)))


def _leg(trade_id: str, side: str, **extra) -> dict:
    r = dict(trade_id=trade_id, symbol="SPX", option_side=side,
             is_condor_leg=1, is_trend_credit=0, status="open",
             entry_premium=1.00, contracts=1, stop_premium=1.25,
             target_premium=0.05, trail_stop=0.0, underlying_stop=0.0,
             direction="short", stop_suppressed_ts="", stop_suppressed_by="")
    r.update(extra)
    return r


def main() -> int:
    import config
    # Deterministic clock gates: hold-to-close compare against (23,59) so the
    # hard-close branch cannot fire during the test, whatever the wall clock.
    config.VERTICAL_HOLD_TO_CLOSE = True
    config.VERTICAL_HOLD_TO_ET = (23, 59)

    import database.trade_logger as tlmod
    import execution.exit_engine as xe

    put_leg = _leg("T-PUT-001", "put")
    call_leg = _leg("T-CALL-002", "call")
    fake = FakeTradeLogger([put_leg])          # only the put is open → LONE

    # Patch BOTH bindings: the ctor uses exit_engine's imported name, the
    # sibling probe does a call-time import from database.trade_logger.
    tlmod.get_trade_logger = lambda: fake
    xe.get_trade_logger = lambda: fake
    engine = xe.ExitEngine(paper_trading=True)

    breach = 1.30   # entry 1.00 → breaches the lone 1.15 floor AND the
                    # pre-fix hedged 1.25 floor, so S2 is genuinely RED
                    # at r89b rather than passing behind the wider stop

    print("S1  lone leg — the 15% floor fires")
    d = engine._evaluate_condor_leg(put_leg, breach, df_1m=None)
    check("S1 exits", bool(d.should_exit), f"reason={d.exit_reason!r}")
    check("S1 reason is condor_stop (lone 15%)",
          str(d.exit_reason or "").startswith("condor_stop")
          and "(lone 15%)" in str(d.exit_reason or ""),
          f"reason={d.exit_reason!r}")

    print("S2  complement open — the SAME move is suppressed")
    fake.open_trades = [put_leg, call_leg]
    d = engine._evaluate_condor_leg(put_leg, breach, df_1m=None)
    check("S2 no exit while formed", not d.should_exit,
          f"reason={d.exit_reason!r}")

    print("S3  suppress edge persisted as NEW fields")
    check("S3 stop_suppressed_ts set on record",
          bool(put_leg.get("stop_suppressed_ts")))
    check("S3 stop_suppressed_by names the complement",
          put_leg.get("stop_suppressed_by") == "T-CALL-002",
          f"by={put_leg.get('stop_suppressed_by')!r}")
    wrote = [f for tid, f in fake.updates
             if tid == "T-PUT-001" and f.get("stop_suppressed_ts")]
    check("S3 DB write via update_fields", bool(wrote))

    print("S4  complement closed — RE-ARMED (the naked-position direction)")
    fake.open_trades = [put_leg]
    d = engine._evaluate_condor_leg(put_leg, breach, df_1m=None)
    check("S4 exits again once alone", bool(d.should_exit),
          f"reason={d.exit_reason!r}")

    print("S5  re-arm edge cleared the fields")
    check("S5 record fields cleared",
          put_leg.get("stop_suppressed_ts") == ""
          and put_leg.get("stop_suppressed_by") == "")
    cleared = [f for tid, f in fake.updates
               if tid == "T-PUT-001" and f.get("stop_suppressed_ts") == ""]
    check("S5 DB clear via update_fields", bool(cleared))

    print("S6  stop_premium never mutated")
    check("S6 immutable entry-time floor",
          put_leg["stop_premium"] == 1.25,
          f"stop_premium={put_leg['stop_premium']!r}")
    check("S6 no update ever touched stop_premium",
          not any("stop_premium" in f for _, f in fake.updates))

    print("S7  TCS branch stays uncontaminated")
    tcs = _leg("T-TCS-003", "put", is_trend_credit=1)
    fake.open_trades = [tcs, call_leg]
    d = engine._evaluate_condor_leg(tcs, breach, df_1m=None)
    check("S7 no premium-stop exit on TCS", not d.should_exit,
          f"reason={d.exit_reason!r}")
    check("S7 no suppression fields on a TCS row",
          not tcs.get("stop_suppressed_ts")
          and not any(tid == "T-TCS-003" for tid, _ in fake.updates))

    print("S8  columns exist in schema and migration")
    src = open(os.path.join(ROOT, "database", "trade_logger.py")).read()
    schema = re.search(r"CREATE TABLE IF NOT EXISTS trades.*?\n\s*\);", src, re.S)
    schema_txt = schema.group(0) if schema else ""
    for col in ("stop_suppressed_ts", "stop_suppressed_by"):
        check(f"S8 {col} in schema", col in schema_txt)
        check(f"S8 {col} in migration list",
              bool(re.search(r'\("%s",\s*"TEXT DEFAULT' % col, src)))

    print()
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failing: {', '.join(PROBLEMS)}")
        return 1
    print("GREEN — condor stop suppression pins all hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
