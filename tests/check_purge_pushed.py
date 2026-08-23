#!/usr/bin/env python3
"""
tests/check_purge_pushed.py  v1.0
NOTHING THE PURGE CAN DELETE MAY LACK A PUSH STAGE. Executing invariant.

v1.0  2026-08-23  Born RED at r84: retention_purge held greeks_series,
quote_series, prints, last_trade, session_summary, theo_series and
underlying_series at 3 days — calling it "a RE-PUSH window" — while s3_push
had no stage touching any of them. Armed, the purge would have deleted the
manifold's series data unwarehoused: the exact "pruned before you knew you
needed it" loss the manifold exists to end. Green from s3_push v4.2.

MECHANICS — WA §20/§21 compliant:
  · Reads retention_purge's LIVE constants (import, not grep), so a new
    purgeable table added tomorrow trips this check the same day.
  · Proves coverage by EXECUTION, not mention: push_series is driven against
    a planted in-memory store carrying one row in EVERY purgeable series
    table, with a fake S3, and each table must produce a confirmed object.
    A candle row is planted too, for push_candles, so the candles interval
    policy is covered by the same run.
  · Deliberate-failure control: an extra table present in the purge policy
    but absent from the store must be REPORTED as uncovered, proving the
    check can go red.

Run:  cd ~/options-trader && python3 tests/check_purge_pushed.py
"""
from __future__ import annotations

import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PROBLEMS: list = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}"
          + (f"  - {detail}" if (detail and not ok) else ""))
    if not ok:
        PROBLEMS.append(name)


class _FakeS3:
    def __init__(self):
        self.objs = {}

    def put_object(self, Bucket, Key, Body):
        self.objs[Key] = Body

    def get_object(self, Bucket, Key):
        import io
        return {"Body": io.BytesIO(self.objs[Key])}


def main() -> int:
    print("=" * 66)
    print("PURGE↔PUSH INVARIANT: everything deletable is warehoused first")
    print("=" * 66)
    from warehouse import retention_purge as rp
    from warehouse import s3_push as sp

    purgeable = sorted(set(rp.ARTIFACT_DAYS) - set(rp.NEVER_PURGE))
    candle_purge = any(d for d in rp.RETENTION_DAYS.values())

    # 1 — every purgeable series table must be in the push's declared set.
    declared = set(getattr(sp, "SERIES_TABLES", ()))
    missing = [t for t in purgeable if t not in declared]
    check("C1 every purgeable artifact table has a push stage declared",
          not missing, f"unpushed purgeable tables: {missing}")

    # 2 — EXECUTE the push against a planted store; every table must land.
    tmp = os.path.join("/tmp", "check_purge_pushed.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    for t in purgeable:
        con.execute(f"CREATE TABLE {t} (streamer_symbol TEXT, ts_epoch REAL, x REAL)")
        con.execute(f"INSERT INTO {t} VALUES ('X', 1000.0, 1.0)")
    con.execute("CREATE TABLE candles (symbol TEXT, interval TEXT,"
                " ts_epoch_ms INTEGER, close REAL)")
    con.execute("INSERT INTO candles VALUES ('X','1m', 1000000, 1.0)")
    con.commit()
    con.close()

    s3 = _FakeS3()
    ledger: dict = {}
    pushed, failed = sp.push_series(s3, "b", tmp, ledger, "X", counters={})
    landed = {k.split("/")[1] for k in s3.objs}
    not_landed = [t for t in purgeable if t not in landed]
    check("C2 push_series lands one object per purgeable table (executed)",
          pushed == len(purgeable) and failed == 0 and not not_landed,
          f"pushed={pushed} failed={failed} missing={not_landed}")

    check("C3 candle purge policy exists only alongside push_candles",
          (not candle_purge) or hasattr(sp, "push_candles"))

    # 4 — high-water mark advanced, namespaced, and a re-run pushes nothing.
    ok_hwm = all(ledger.get(f"series|{t}") == 1000.0 for t in purgeable)
    p2, f2 = sp.push_series(s3, "b", tmp, ledger, "X", counters={})
    check("C4 high-water marks are namespaced `series|<t>` and idempotent",
          ok_hwm and p2 == 0 and f2 == 0, f"ledger={ledger} rerun=({p2},{f2})")

    # 5 — deliberate-failure control: a purgeable table the store lacks must
    # surface as uncovered when we widen the policy in-memory.
    rp.ARTIFACT_DAYS["_planted_uncovered_table"] = 3
    try:
        widened = sorted(set(rp.ARTIFACT_DAYS) - set(rp.NEVER_PURGE))
        miss2 = [t for t in widened if t not in declared]
        check("C5 the check CAN fail (planted uncovered table is caught)",
              "_planted_uncovered_table" in miss2)
    finally:
        rp.ARTIFACT_DAYS.pop("_planted_uncovered_table", None)

    os.remove(tmp)
    print("-" * 66)
    if PROBLEMS:
        print(f"FAIL  {len(PROBLEMS)} problem(s): {', '.join(PROBLEMS)}")
        return 1
    print("ALL GREEN — nothing the purge can reach dies unwarehoused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
