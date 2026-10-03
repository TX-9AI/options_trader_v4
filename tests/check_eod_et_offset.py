#!/usr/bin/env python3
"""
tests/check_eod_et_offset.py  v1.0
v1.0  2026-10-03  r459 / TZ.2 — THE EOD SUMMARY'S ET DATE FOLLOWS DAYLIGHT SAVING.

  eod_summary.py filtered closed trades with a literal '-4 hours' (EDT), so
  from 2026-11-01 (EST, -5) a trade's ET date is computed an hour late. Drives
  the REAL compute_summary on a SCRATCH trades.db with the clock pinned
  (mirrors OTV4TEST r191's Z4 idea; this file is otv4's own):
  E1  EST: clock 2026-11-02 23:45 ET, entry 2026-11-03T04:30Z (= 23:30 ET on
      the 2nd) -> counted (the defect: 0, it read 00:30 on the 3rd)
  E2  EDT: clock 2026-10-02 23:45 ET, entry 2026-10-03T03:30Z (= 23:30 ET on
      the 2nd) -> counted (unchanged)
  E3  et_offset_sql() returns "-5 hours" in EST and "-4 hours" in EDT
  BORN RED on otv4 d87bafb at E1 E3.

Run:  python3 tests/check_eod_et_offset.py
"""
import os
import sqlite3
import sys
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PROBLEMS = []
ET = ZoneInfo("America/New_York")


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        PROBLEMS.append(name)


def _db(path, entry_iso):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE trades (trade_id TEXT, status TEXT, entry_time TEXT, pnl_usd REAL)")
    con.execute("INSERT INTO trades VALUES ('t1','closed',?,10.0)", (entry_iso,))
    con.commit()
    con.close()


def main():
    import eod_summary as es
    tmp = tempfile.mkdtemp(prefix="check_eod_et_")
    real_now, real_db = es.now_et, es.DB_PATH
    try:
        for tag, clock, entry in (
                ("E1 EST", datetime(2026, 11, 2, 23, 45, tzinfo=ET), "2026-11-03T04:30:00+00:00"),
                ("E2 EDT", datetime(2026, 10, 2, 23, 45, tzinfo=ET), "2026-10-03T03:30:00+00:00")):
            path = os.path.join(tmp, tag.split()[0] + ".db")
            _db(path, entry)
            es.DB_PATH = path
            es.now_et = lambda c=clock: c
            n = es.compute_summary()["n_trades"]
            check(f"{tag}: an entry at 23:30 ET on the clock's date is counted",
                  n == 1, f"n_trades={n} for entry {entry}")
        f = getattr(es, "et_offset_sql", None)
        got = (f(datetime(2026, 11, 2, 12, tzinfo=ET)), f(datetime(2026, 10, 2, 12, tzinfo=ET))) if f else None
        check("E3 et_offset_sql gives -5 hours in EST and -4 hours in EDT",
              got == ("-5 hours", "-4 hours"), f"got {got}")
    finally:
        es.now_et, es.DB_PATH = real_now, real_db
    print("=" * 60)
    if PROBLEMS:
        print(f"RED — {len(PROBLEMS)} failed: {PROBLEMS}")
        return 1
    print("GREEN — the EOD summary's ET date follows daylight saving")
    return 0


if __name__ == "__main__":
    sys.exit(main())
