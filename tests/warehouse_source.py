#!/usr/bin/env python3
"""
tests/warehouse_source.py  v1.0
THE R SUITE'S S3 SOURCE. Control reads the bucket; boxes are never touched.

v1.0  2026-08-23  Operator's baseline requirement, verbatim in effect: reports
run on CONTROL, the target is S3, nothing runs on a trading instance and
nothing is pulled to control to digest. This module is the one place the four
R tools get data, so the rule lives in one file instead of four.

DESIGN RULES
  1. STDLIB + boto3 ONLY, same as s3_push. No repo imports, no pandas. It
     must run under control's system python and under the dtp venv alike.
  2. ⚠️ DEDUPE IS MANDATORY AND LIVES HERE. trades and the derived CDC tables
     are pushed on every state change, so S3 holds several objects per key.
     `latest wins by pushed_at_utc` — without it every ratio in the suite
     inflates silently. (Same contract as day_trader_pro's warehouse_reader;
     re-implemented because a module never imports from a sibling repo.)
  3. ⚠️ "EMPTY" AND "UNREACHABLE" ARE DIFFERENT FACTS. Every loader returns
     (rows, meta) where meta carries objects listed, objects read, and any
     error string. banner() renders it, and every tool prints it — a flat day
     and a broken credential must never look alike (this conflation has cost
     the project twice in one week).

KEY LAYOUT READ (must match warehouse/s3_push.py):
  raw/trades/dt=<D>/sym=<S>/...            envelope.record = trade row (CDC)
  raw/<series>/dt=<D>/sym=<S>/...          envelope.record = [rows] (batch)
  raw/derived_<table>/dt=<D>/sym=<S>/...   envelope.record = [rows w/ _rid] (CDC batch)

Run:  python3 tests/warehouse_source.py --selftest
"""
from __future__ import annotations

import json
import os

BUCKET = os.environ.get("OT_S3_BUCKET", "vertigo-warehouse-tx9ai")
REGION = os.environ.get("OT_S3_REGION", "us-east-2")
PREFIX = os.environ.get("OT_S3_PREFIX", "raw")


class Meta:
    def __init__(self, what):
        self.what = what
        self.listed = 0
        self.read = 0
        self.bad = 0
        self.error = ""

    def banner(self) -> str:
        if self.error:
            return (f"SOURCE: s3://{BUCKET}/{PREFIX} [{self.what}] — "
                    f"🔴 COULD NOT READ THE WAREHOUSE: {self.error}")
        return (f"SOURCE: s3://{BUCKET}/{PREFIX} [{self.what}] — "
                f"{self.listed} object(s) listed, {self.read} read"
                + (f", {self.bad} unreadable" if self.bad else "")
                + ("  (a real, empty result — not a missing path)"
                   if self.listed == 0 else ""))


def client():
    import boto3
    return boto3.client("s3", region_name=REGION)


def _iter(s3, prefix, meta):
    pg = s3.get_paginator("list_objects_v2")
    for page in pg.paginate(Bucket=BUCKET, Prefix=prefix):
        for o in page.get("Contents", []) or []:
            meta.listed += 1
            yield o["Key"]


def _envelopes(s3, datatype, dates, meta, symbols=None):
    for d in dates:
        try:
            keys = list(_iter(s3, f"{PREFIX}/{datatype}/dt={d}/", meta))
        except Exception as exc:                                # noqa: BLE001
            meta.error = f"{type(exc).__name__}: {exc}"
            return
        for k in keys:
            if symbols:
                sym = next((p[4:] for p in k.split("/") if p.startswith("sym=")), "")
                if sym not in symbols:
                    continue
            try:
                body = s3.get_object(Bucket=BUCKET, Key=k)["Body"].read()
                meta.read += 1
                yield json.loads(body)
            except Exception:                                   # noqa: BLE001
                meta.bad += 1


def load_trades(dates, s3=None):
    """Deduped closed+open trade rows for the dates. -> (rows, Meta)."""
    meta = Meta(f"trades {dates[0]}..{dates[-1]}")
    s3 = s3 or client()
    best = {}
    for env in _envelopes(s3, "trades", dates, meta):
        rec = env.get("record") or {}
        tid = rec.get("trade_id")
        if tid is None:
            continue
        stamp = str(env.get("pushed_at_utc") or "")
        if tid not in best or stamp >= best[tid][0]:
            best[tid] = (stamp, rec)
    return [rec for _s, rec in best.values()], meta


def load_series(table, dates, symbols=None, s3=None):
    """Rows of one manifold series table (batched objects). -> (rows, Meta)."""
    meta = Meta(f"{table} {dates[0]}..{dates[-1]}")
    s3 = s3 or client()
    rows = []
    for env in _envelopes(s3, table, dates, meta, symbols):
        rec = env.get("record")
        if isinstance(rec, list):
            rows.extend(r for r in rec if isinstance(r, dict))
    return rows, meta


def load_derived(table, dates, s3=None):
    """Rows of one derived CDC table, latest state per _rid. -> (rows, Meta)."""
    meta = Meta(f"derived_{table} {dates[0]}..{dates[-1]}")
    s3 = s3 or client()
    best = {}
    for env in _envelopes(s3, f"derived_{table}", dates, meta):
        stamp = str(env.get("pushed_at_utc") or "")
        sym = env.get("symbol") or "?"
        for r in (env.get("record") or []):
            if not isinstance(r, dict):
                continue
            key = (sym, r.get("_rid"))
            if key not in best or stamp >= best[key][0]:
                best[key] = (stamp, r)
    return [r for _s, r in best.values()], meta


def dates_of(argns) -> list:
    """--date / --from/--to -> ISO list; default today."""
    from datetime import date as _d, datetime, timedelta
    if getattr(argns, "date", None):
        return [argns.date]
    frm, to = getattr(argns, "frm", None), getattr(argns, "to", None)
    if frm and to:
        d0 = datetime.strptime(frm, "%Y-%m-%d").date()
        d1 = datetime.strptime(to, "%Y-%m-%d").date()
        if d1 < d0:
            d0, d1 = d1, d0
        out, d = [], d0
        while d <= d1:
            out.append(d.isoformat())
            d += timedelta(days=1)
        return out
    return [_d.today().isoformat()]


# ── selftest ────────────────────────────────────────────────────────────
class _FakeS3:
    def __init__(self, objs):
        self.objs = objs

    def get_paginator(self, _):
        objs = self.objs

        class P:
            def paginate(self, Bucket, Prefix):
                yield {"Contents": [{"Key": k} for k in objs if k.startswith(Prefix)]}
        return P()

    def get_object(self, Bucket, Key):
        import io
        return {"Body": io.BytesIO(self.objs[Key])}


def selftest() -> int:
    def env(dt, rec, stamp, sym="X", datatype="trades"):
        return json.dumps({"datatype": datatype, "symbol": sym, "dt": dt,
                           "pushed_at_utc": stamp, "record": rec}).encode()
    objs = {
        # same trade pushed twice — the LATER state must win
        f"{PREFIX}/trades/dt=2026-08-24/sym=X/1-aa.json":
            env("2026-08-24", {"trade_id": "t1", "status": "open", "pnl_usd": None}, "T1"),
        f"{PREFIX}/trades/dt=2026-08-24/sym=X/2-bb.json":
            env("2026-08-24", {"trade_id": "t1", "status": "closed", "pnl_usd": 50.0}, "T2"),
        f"{PREFIX}/quote_series/dt=2026-08-24/sym=X/3-cc.json":
            env("2026-08-24", [{"streamer_symbol": "C1", "ts_epoch": 1.0,
                                "bid_price": 1.0, "ask_price": 1.1}], "T1",
                datatype="quote_series"),
        f"{PREFIX}/derived_fire_snapshot/dt=2026-08-24/sym=X/4-dd.json":
            env("2026-08-24", [{"_rid": 1, "trade_id": "t1", "payload": "{}"}], "T1",
                datatype="derived_fire_snapshot"),
        f"{PREFIX}/derived_fire_snapshot/dt=2026-08-24/sym=X/5-ee.json":
            env("2026-08-24", [{"_rid": 1, "trade_id": "t1", "payload": "{\"a\":1}"}], "T2",
                datatype="derived_fire_snapshot"),
    }
    s3 = _FakeS3(objs)
    ok = True
    rows, m = load_trades(["2026-08-24"], s3=s3)
    ok &= len(rows) == 1 and rows[0]["status"] == "closed" and m.read == 2
    q, _ = load_series("quote_series", ["2026-08-24"], s3=s3)
    ok &= len(q) == 1 and q[0]["streamer_symbol"] == "C1"
    d, _ = load_derived("fire_snapshot", ["2026-08-24"], s3=s3)
    ok &= len(d) == 1 and d[0]["payload"] == "{\"a\":1}"
    # deliberate-failure control: an unreadable bucket must report an ERROR
    class _Boom:
        def get_paginator(self, _):
            raise RuntimeError("AccessDenied")
    _r, m2 = load_trades(["2026-08-24"], s3=_Boom())
    ok &= "AccessDenied" in m2.error and "COULD NOT READ" in m2.banner()
    # and an empty day must NOT look like an error
    _r3, m3 = load_trades(["2026-08-25"], s3=s3)
    ok &= not m3.error and "empty result" in m3.banner()
    print("warehouse_source selftest:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(selftest() if "--selftest" in sys.argv else
             print("this module is imported by the R tools; --selftest to prove it") or 0)
