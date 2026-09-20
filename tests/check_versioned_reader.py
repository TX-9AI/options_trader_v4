#!/usr/bin/env python3
"""
tests/check_versioned_reader.py  v1.2
v1.2  2026-09-20  r397 / D2 - V9, V9b, V10 and V10b, plus SELF-COUNTING.
V9 pins that an object read but not understood is counted and NAMED in the
banner rather than dropped into a silent zero; V10/V10b pin that the tape has a
sanctioned reader and that it follows the header BY NAME. All three are BORN
RED at ff02d37 and V9b is GREEN there as a control, proving the refusal did not
become blanket.
  ⚠️ EVERY NEW ASSERTION IS GUARDED WITH getattr/hasattr ON PURPOSE, so against
the pre-r397 module they FAIL rather than raise - a checker that crashes reports
breakage rather than a finding.
  ⚠️ AND THE TAIL NO LONGER PRINTS A HARDCODED "ALL PASS (8)", which is
[[CHK.6]]'s shape exactly: a count that rots the moment a check is added while
reading as authoritative. It counts itself.
v1.1  2026-09-10  r335 - V7 and V8. The reader was passing a VersionId on
      EVERY key and `s3:GetObjectVersion` is a permission control does not
      hold, so AWS denied all 10,741 objects - including CURRENT ones it could
      read plainly. V7 pins that a current object is fetched WITHOUT a version
      id. V8 pins that a read failure keeps its FIRST error and puts it in the
      banner, because r332 counted failures and printed nothing else, so the
      denial rendered as an empty table with no cause on screen.
      Also: the FIXTURE was stricter than the S3 it stands in for - it keyed
      objects by (key, version) and raised on a VersionId-less read. A fixture
      that cannot represent the real behaviour cannot catch a bug in it.
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
  V7  a CURRENT object is fetched WITHOUT a VersionId (passing one needs
      s3:GetObjectVersion, which control does not hold — r332 denied itself
      all 10,741 objects this way)
  V8  a read failure keeps its FIRST error and puts it in the banner
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
FAILS = []


RAN = []


def check(name, ok, detail=""):
    # ⚠️ r397 — SELF-COUNTING. The tail printed a HARDCODED "ALL PASS (8)",
    # which is [[CHK.6]]'s shape: a number that rots the moment a check is
    # added and reads as authoritative while it does. It counts itself now.
    RAN.append(name)
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

    # the LATEST version id per key, so a VersionId-less read resolves the
    # way S3 does rather than raising — the fixture must not be stricter
    # than the thing it stands in for.
    LATEST = {"raw/trades/dt=2026-09-02/sym=NVDA/live.json": "v-live"}

    def get_object(self, Bucket=None, Key=None, VersionId=None):
        self.reads.append((Key, VersionId))
        vid = VersionId or self.LATEST.get(Key)
        if vid is None:
            raise KeyError("no current version for " + Key)
        env = self.objects[(Key, vid)]

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

    check("V7", ("raw/trades/dt=2026-09-02/sym=NVDA/live.json", None)
          in s3.reads,
          "current read: {}".format([r for r in s3.reads if r[0].endswith("live.json")]))

    class Boom(FakeS3):
        def get_object(self, **_kw):
            raise RuntimeError("AccessDenied: no s3:GetObjectVersion")

    mb = ws.Meta("t")
    list(ws.iter_versioned("trades", ["2026-07-08"], mb, s3=Boom()))
    check("V8", mb.read == 0 and mb.bad and "AccessDenied" in mb.banner(),
          "read={} bad={} banner-has-error={}".format(
              mb.read, mb.bad, "AccessDenied" in mb.banner()))

    # ══ r397 — THE RECORD SHAPE. load_series RETURNED A SILENT ZERO. ══════
    # 🔴 WHAT THESE PIN. `raw/ohlc` stores a whole session as ONE CSV STRING
    # in `record`, and `load_series` collected only when `record` was a LIST,
    # with no `else`. So `load_series("ohlc", ...)` returned 0 rows while its
    # banner read "15 object(s) listed, 15 read" and `meta.error` was empty —
    # the deepest corpus this project owns, 54 sessions back to 2026-07-08,
    # silently unreadable through the sanctioned loader.
    # ⚠️ EVERY ASSERTION BELOW IS GUARDED WITH getattr/hasattr ON PURPOSE.
    # Against the pre-r397 module these must FAIL, not raise: a checker that
    # crashes reports breakage rather than a finding, and the two get
    # triaged differently.
    class ShapeS3:
        """`Contents` paginator — the plain (non-versioned) read path.

        One CSV-string record under `ohlc` and one list record under
        `indicator_series`, so the refusal and the control share a fixture.
        """

        CSV = ("timestamp,open,high,low,close,volume\n"
               "2026-09-18T09:30:00-04:00,547.6,548.82,544.0,545.56,1918319.0\n"
               "2026-09-18T09:31:00-04:00,545.94,548.73,545.16,548.485,67262.67\n")

        OBJ = {
            "raw/ohlc/dt=2026-09-18/sym=AMD/bars.json": {
                "record": CSV, "dt": "2026-09-18", "symbol": "AMD"},
            "raw/indicator_series/dt=2026-09-18/sym=AMD/s.json": {
                "record": [{"ts_epoch": 1, "adx": 22.0},
                           {"ts_epoch": 2, "adx": 23.0}],
                "dt": "2026-09-18", "symbol": "AMD"},
        }

        def get_paginator(self, _name):
            outer = self

            class P:
                def paginate(self, Bucket=None, Prefix=None):
                    yield {"Contents": [{"Key": k} for k in outer.OBJ
                                        if k.startswith(Prefix)]}
            return P()

        def get_object(self, Bucket=None, Key=None, VersionId=None):
            env = self.OBJ[Key]

            class B:
                @staticmethod
                def read():
                    return json.dumps(env).encode()
            return {"Body": B()}

    sh = ShapeS3()
    r9, m9 = ws.load_series("ohlc", ["2026-09-18"], s3=sh)
    _flagged = getattr(m9, "unhandled", 0)
    check("V9", len(r9) == 0 and _flagged == 1
          and "NOT PARSED" in m9.banner(),
          "an object READ but not understood is counted and NAMED in the "
          "banner, never dropped into a silent zero: rows={} unhandled={} "
          "banner-says-so={}".format(len(r9), _flagged,
                                     "NOT PARSED" in m9.banner()))

    # CONTROL — the refusal must not have become blanket. A LIST record still
    # loads, and must NOT be flagged.
    r9b, m9b = ws.load_series("indicator_series", ["2026-09-18"], s3=sh)
    check("V9b", len(r9b) == 2 and getattr(m9b, "unhandled", 0) == 0
          and "NOT PARSED" not in m9b.banner(),
          "CONTROL — a normal list-record series is untouched and unflagged: "
          "rows={} unhandled={}".format(len(r9b), getattr(m9b, "unhandled", 0)))

    if not hasattr(ws, "load_ohlc"):
        check("V10", False, "warehouse_source.load_ohlc does not exist — the "
                            "tape has no sanctioned reader")
        check("V10b", False, "load_ohlc does not exist")
    else:
        r10, m10 = ws.load_ohlc(["2026-09-18"], s3=sh)
        _ok = (len(r10) == 2
               and r10[0]["symbol"] == "AMD" and r10[0]["dt"] == "2026-09-18"
               and abs((r10[0]["open"] or 0) - 547.6) < 1e-9
               and abs((r10[1]["close"] or 0) - 548.485) < 1e-9
               and isinstance(r10[0]["open"], float))
        check("V10", _ok,
              "the tape parses into typed rows carrying their own symbol and "
              "date: n={} first={}".format(len(r10), r10[0] if r10 else None))
        # ⚠️ THE HEADER IS READ FROM THE FILE, NOT ASSUMED. A reordered header
        # must follow the NAMES, or a hardcoded order silently puts plausible
        # numbers in the wrong columns — [[RPL.3]]'s shape exactly.
        class Swapped(ShapeS3):
            OBJ = {"raw/ohlc/dt=2026-09-18/sym=AMD/bars.json": {
                "record": ("volume,close,low,high,open,timestamp\n"
                           "1918319.0,545.56,544.0,548.82,547.6,"
                           "2026-09-18T09:30:00-04:00\n"),
                "dt": "2026-09-18", "symbol": "AMD"}}
        r10b, _m = ws.load_ohlc(["2026-09-18"], s3=Swapped())
        check("V10b", len(r10b) == 1
              and abs((r10b[0]["open"] or 0) - 547.6) < 1e-9
              and abs((r10b[0]["volume"] or 0) - 1918319.0) < 1e-9,
              "a REORDERED header is followed by name, not by position: "
              "{}".format(r10b[0] if r10b else None))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS ({})".format(len(RAN)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
