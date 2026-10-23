#!/usr/bin/env python3
"""
tests/check_tape_band_column.py  v1.0
v1.0  2026-10-23  r499 / TAPE.1 — `tape_band` IS A COLUMN OF `trades`.

  analysis/tape_at_level.measure (r120) returns tape_vol_at_level, tape_prints_at_level
  and tape_band; entry_engine record.update()s all three into the trade record, and
  log_entry's TCS.4 filter DROPPED tape_band on every insert (no column; one "[schema]
  ... NO COLUMN" warning per process). 10-22: 28 of 28 mainline Runaway rows carry
  tape_vol_at_level, none tape_band. Shape proposed by OTV4TEST (MSG-QQQ-1022-08).
  Drives the REAL TradeLogger on scratch databases:
  T1  a fresh DB: an inserted record's tape_band reads back equal
  T2  a pre-r499 DB (the old CREATE, without the column) holding a row migrates on open:
      the column is added and the row is kept, every value unchanged
  T3  the insert logs no "[schema] ... NO COLUMN" line for tape_band
  T4  the pre-r499 row's tape_band is NULL (not recorded), never 0
  T5  the column sits in BOTH the CREATE and _MIGRATION_ADDS, REAL, no default

Run:  python3 tests/check_tape_band_column.py   (exit 0 green, 1 red)
"""
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
os.environ.setdefault("OT_INSTRUMENT", "QQQ")

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  — {detail}"))
    if not ok:
        FAILED.append(name.split()[0])


class _Cap(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def rec(tid, **kw):
    from database.trade_logger import make_record
    r = make_record(trade_id=tid, symbol="QQQ", strategy="RunawayContinuation",
                    setup_type="runaway_continuation", direction="long", option_side="call",
                    strike=710.0, expiry="2026-10-23", contracts=2, entry_premium=1.50,
                    stop_premium=1.20, target_premium=3.00, trail_activation=2.25,
                    underlying_entry=709.5, tape_vol_at_level=12345.0,
                    tape_prints_at_level=88, tape_band=0.455)
    r.update(kw)
    return r


def cols(path):
    c = sqlite3.connect(path)
    try:
        return {r[1]: r for r in c.execute("PRAGMA table_info(trades)")}
    finally:
        c.close()


def main():
    import database.trade_logger as TLm
    from database.trade_logger import TradeLogger
    cap = _Cap()
    TLm.logger.addHandler(cap)
    TLm.logger.setLevel(logging.DEBUG)
    TLm.logger.propagate = False
    TLm._WARNED_UNKNOWN_COLS.clear()
    tmp = tempfile.mkdtemp(prefix="tapeband_")

    # T1 / T3 — fresh DB
    p1 = os.path.join(tmp, "fresh.db")
    tl = TradeLogger(p1)
    tl.log_entry(rec("t1"))
    c = sqlite3.connect(p1)
    try:
        row = c.execute("SELECT tape_band, tape_vol_at_level FROM trades WHERE trade_id='t1'").fetchone()
    except sqlite3.OperationalError as e:
        row = f"error: {e}"
    c.close()
    check("T1 a fresh DB: the inserted tape_band reads back equal (0.455)",
          isinstance(row, tuple) and row[0] == 0.455 and row[1] == 12345.0, f"row={row}")
    dropped = [ln for ln in cap.lines if "NO COLUMN" in ln and "tape_band" in ln]
    check("T3 the insert logs no '[schema] ... NO COLUMN' line for tape_band",
          not dropped, f"lines={dropped}")

    # T2 / T4 — a pre-r499 DB migrates and keeps its row
    p2 = os.path.join(tmp, "old.db")
    old_schema = "\n".join(ln for ln in TradeLogger.SCHEMA.splitlines()
                           if not ln.strip().startswith("tape_band"))
    c = sqlite3.connect(p2)
    c.executescript(old_schema)
    oldcols = [r[1] for r in c.execute("PRAGMA table_info(trades)")]
    c.execute("INSERT INTO trades (trade_id, symbol, strategy, entry_premium, "
              "tape_vol_at_level, tape_prints_at_level, status) "
              "VALUES ('old1', 'QQQ', 'RunawayContinuation', 1.85, 999.0, 7, 'closed')")
    c.commit()
    before = c.execute("SELECT * FROM trades WHERE trade_id='old1'").fetchone()
    c.close()
    TradeLogger(p2)                                      # opening it runs the boot migration
    after_cols = cols(p2)
    c = sqlite3.connect(p2)
    c.row_factory = sqlite3.Row
    r2 = c.execute("SELECT * FROM trades WHERE trade_id='old1'").fetchone()
    c.close()
    kept = r2 is not None and all(r2[k] == v for k, v in zip(oldcols, before))
    check("T2 a pre-r499 DB migrates on open: tape_band added, the old row kept unchanged",
          "tape_band" not in oldcols and "tape_band" in after_cols and kept,
          f"old had tape_band={'tape_band' in oldcols} after={'tape_band' in after_cols} kept={kept}")
    v4 = r2["tape_band"] if (r2 is not None and "tape_band" in r2.keys()) else "absent"
    check("T4 the pre-r499 row's tape_band is NULL (not recorded), never 0",
          v4 is None, f"tape_band={v4!r}")

    # T5 — the declared shape
    ci = after_cols.get("tape_band")
    fresh = cols(p1).get("tape_band")
    src = open(os.path.join(_root, "database", "trade_logger.py")).read()
    in_migr = '("tape_band",              "REAL")' in src
    in_create = any(ln.strip().startswith("tape_band") and "REAL" in ln and "DEFAULT" not in ln
                    for ln in TradeLogger.SCHEMA.splitlines())
    check("T5 the column is in the CREATE and _MIGRATION_ADDS, REAL, no default",
          in_create and in_migr and ci is not None and ci[2] == "REAL" and ci[4] is None
          and fresh is not None and fresh[2] == "REAL" and fresh[4] is None,
          f"create={in_create} migration={in_migr} migrated={ci} fresh={fresh}")

    print()
    if FAILED:
        print(f"RED: {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
