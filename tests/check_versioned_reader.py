#!/usr/bin/env python3
"""
tests/check_versioned_reader.py  v1.0
v1.0  2026-09-10  r332 / BRF.1 — the land gate for warehouse_source's
      version-aware reader.

🔴 WHAT IT PROTECTS. `iter_versioned` reaches PAST a delete marker on purpose,
so its failure modes are the two that would quietly corrupt a study:
  · reading BOTH a current object and an older version of the same key —
    one trade counted twice, which looks like a busier session;
  · reading past a marker WITHOUT SAYING SO — a severed sample silently
    re-widened, which is exactly what dtp r314 was run to prevent.

  V1  a key with only a current version reads once, severed=0
  V2  a key whose latest is a delete marker reads the newest version UNDER it
      and counts as severed
  V3  never both: one object per key, never a duplicate
  V4  load_trades_versioned dedupes by trade_id on pushed_at_utc
  V5  the banner reports the severed count
  V6  the symbols filter applies
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


class FakeS3:
    """Two keys: one live, one behind a delete marker with two versions under."""

    def __init__(self):
        self.reads = []
        self.objects = {
            ("raw/trades/dt=2026-09-02/sym=NVDA/live.json", "v-live"):
                {"record": {"trade_id": 1, "pnl_usd": 10}, "dt": "2026-09-02",
                 "pushed_at_utc": "2026-09-02T20:00:00"},
            ("raw/trades/dt=2026-07-08/sym=NVDA/old.json", "v-new"):
                {"record": {"trade_id": 2, "pnl_usd": -5}, "dt": "2026-07-08",
                 "pushed_at_utc": "2026-07-08T20:05:00"},
            ("raw/trades/dt=2026-07-08/sym=NVDA/old.json", "v-older"):
                {"record": {"trade_id": 2, "pnl_usd": -999}, "dt": "2026-07-08",
                 "pushed_at_utc": "2026-07-08T19:00:00"},
            ("raw/trades/dt=2026-07-08/sym=AMD/amd.json", "v-amd"):
                {"record": {"trade_id": 3, "pnl_usd": 7}, "dt": "2026-07-08",
                 "pushed_at_utc": "2026-07-08T20:00:00"},
        }

    def get_paginator(self, _name):
        outer = self

        class P:
            def paginate(self, Bucket=None, Prefix=None):
                if "dt=2026-09-02" in Prefix:
                    yield {"Versions": [
                        {"Key": "raw/trades/dt=2026-09-02/sym=NVDA/live.json",
                         "VersionId": "v-live", "IsLatest": True,
                         "LastModified": "2026-09-02T20:00:00"}]}
                elif "dt=2026-07-08" in Prefix:
                    yield {"Versions": [
                        {"Key": "raw/trades/dt=2026-07-08/sym=NVDA/old.json",
                         "VersionId": "v-new", "IsLatest": False,
                         "LastModified": "2026-08-25T00:00:00"},
                        {"Key": "raw/trades/dt=2026-07-08/sym=NVDA/old.json",
                         "VersionId": "v-older", "IsLatest": False,
                         "LastModified": "2026-08-14T00:00:00"},
                        {"Key": "raw/trades/dt=2026-07-08/sym=AMD/amd.json",
                         "VersionId": "v-amd", "IsLatest": False,
                         "LastModified": "2026-08-20T00:00:00"}],
                        "DeleteMarkers": [
                        {"Key": "raw/trades/dt=2026-07-08/sym=NVDA/old.json",
                         "VersionId": "m1", "IsLatest": True,
                         "LastModified": "2026-09-07T19:16:19"},
                        {"Key": "raw/trades/dt=2026-07-08/sym=AMD/amd.json",
                         "VersionId": "m2", "IsLatest": True,
                         "LastModified": "2026-09-07T19:16:19"}]}
                else:
                    yield {}
        return P()

    def get_object(self, Bucket=None, Key=None, VersionId=None):
        self.reads.append((Key, VersionId))
        env = self.objects[(Key, VersionId)]

        class B:
            @staticmethod
            def read():
                return json.dumps(env).encode()
        return {"Body": B()}


def main():
    try:
        import warehouse_source as ws
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  warehouse_source did not import: {}".format(exc))
        return 1
    for need in ("iter_versioned", "load_trades_versioned"):
        if not hasattr(ws, need):
            print("  FAIL  warehouse_source.{} does not exist".format(need))
            return 1

    s3 = FakeS3()
    meta = ws.Meta("t")
    envs = list(ws.iter_versioned("trades", ["2026-09-02"], meta, s3=s3))
    check("V1", len(envs) == 1 and meta.severed == 0,
          "{} env(s), severed={}".format(len(envs), meta.severed))

    s3b = FakeS3()
    meta2 = ws.Meta("t")
    envs2 = list(ws.iter_versioned("trades", ["2026-07-08"], meta2, s3=s3b))
    ids = sorted(e["record"]["trade_id"] for e in envs2)
    pnls = {e["record"]["trade_id"]: e["record"]["pnl_usd"] for e in envs2}
    check("V2", ids == [2, 3] and pnls.get(2) == -5 and meta2.severed == 2,
          "ids={} nvda_pnl={} severed={}".format(ids, pnls.get(2), meta2.severed))

    keys = [k for k, _v in s3b.reads]
    check("V3", len(keys) == len(set(keys)),
          "{} read(s), {} distinct".format(len(keys), len(set(keys))))

    s3c = FakeS3()
    rows, meta3 = ws.load_trades_versioned(["2026-09-02", "2026-07-08"], s3=s3c)
    tids = sorted(r["trade_id"] for r in rows)
    dts = {r["trade_id"]: r.get("_dt") for r in rows}
    check("V4", tids == [1, 2, 3] and dts.get(2) == "2026-07-08",
          "trade_ids={} _dt(2)={}".format(tids, dts.get(2)))

    check("V5", "behind a delete marker" in meta3.banner(),
          meta3.banner()[-60:])

    s3d = FakeS3()
    meta4 = ws.Meta("t")
    only = list(ws.iter_versioned("trades", ["2026-07-08"], meta4,
                                  symbols=["AMD"], s3=s3d))
    check("V6", len(only) == 1 and only[0]["record"]["trade_id"] == 3,
          "{} env(s) with symbols=[AMD]".format(len(only)))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
