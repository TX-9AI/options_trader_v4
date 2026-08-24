#!/usr/bin/env python3
"""
tools/manifold_health.py  v4.0

One bulb per stream. All green = manifold green.

v4.0  2026-08-25  Operator's design: "every data stream that it's splitting
should have its own red light or green light, and if they're all green,
manifold health is green" — plus a single rollup bulb for status.py.

🔴 WHY THIS EXISTS. On 2026-08-21 the intraday tape was dead from 09:30 and
nothing said so. The operator found it by hand at 09:31; the blind latch pages
ONCE per outage so the silence afterwards meant nothing; the fleet traded zero
and the cause took until evening to establish. **A stream that stops must be
visible in one glance, per stream, before the open.**

⚠️ IT READS THE STORE, NOT THE CODE. A subscription list proves what we ASKED
for. This proves what ARRIVED. Every failure this month lived in that gap.

⚠️ MISSING IS NOT STALE AND NEITHER IS ZERO. Three distinct states:
    GREEN   fresh rows inside the budget
    AMBER   rows exist but the newest is older than the budget  (STALE)
    RED     no rows at all                                      (MISSING)
An entitlement that does not cover a stream and a stream that died look
identical in a row count — so the bulb says which, and never guesses.

⚠️ OFF-HOURS IS NOT A FAULT. Outside RTH every intraday stream is legitimately
stale, and painting fifteen boxes red every evening is how an operator learns
to ignore the board. `--rth-only` (default ON) reports staleness as GREY/IDLE
when the market is shut.

Run:  python3 tools/manifold_health.py            # the board
      python3 tools/manifold_health.py --json     # machine-readable
      python3 tools/manifold_health.py --bulb     # one line, for status.py
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, time as dtime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GREEN, AMBER, RED, GREY = "🟢", "🟡", "🔴", "⚪"

# Freshness budgets, seconds. Generous — this asks "did the pipe break", not
# "is latency good".
CANDLE_BUDGET = {"1m": 180, "5m": 900, "15m": 2700, "1h": 9000, "1d": 200000}

# (table, ts column, budget seconds, label, critical)
# ⚠️ `critical` MARKS WHAT TRADING ACTUALLY DEPENDS ON. prints and theo are
# rich and new; the bot does not yet require them, so their absence must not
# paint the rollup red and teach the operator to ignore it.
STREAMS = [
    ("greeks_series",     "ts_epoch",      300,  "greeks (series)",   True),
    ("quote_series",      "ts_epoch",      300,  "quotes (series)",   True),
    ("chain_marks",       "updated_epoch", 300,  "chain marks",       True),
    ("prints",            "ts_epoch",      600,  "prints (T&S)",      False),
    ("last_trade",        "ts_epoch",      600,  "last trade",        False),
    ("session_summary",   "ts_epoch",     3600,  "session summary",   False),
    ("underlying_series", "ts_epoch",     3600,  "underlying",        False),
    ("theo_series",       "ts_epoch",     3600,  "theo price",        False),
]

DERIVED = [
    ("indicator_series", "ts_epoch",  600, "indicators (ADX/ATR/VWAP)"),
    ("fork_series",      "ts_epoch",  600, "pitchfork"),
    ("level_ledger",     "created_ts", 0,  "levels"),
    ("surface_series",   "ts_epoch",  900, "surface (charm/vanna)"),
]


def _rth_now(now=None) -> bool:
    n = now or datetime.now()
    if n.weekday() >= 5:
        return False
    return dtime(9, 30) <= n.time() <= dtime(16, 0)


def _q1(conn, sql, args=()):
    try:
        return conn.execute(sql, args).fetchone()
    except sqlite3.Error:
        return None


def _bulb(rows, age, budget, in_rth) -> str:
    if not rows:
        return RED
    if budget and age is not None and age > budget:
        return AMBER if in_rth else GREY
    return GREEN


def collect(feed_db: str, derived_db: str, in_rth: bool) -> dict:
    now = time.time()
    out = {"streams": [], "candles": [], "derived": [], "in_rth": in_rth}

    fc = None
    if os.path.exists(feed_db):
        fc = sqlite3.connect(f"file:{feed_db}?mode=ro", uri=True)

    if fc is None:
        out["fatal"] = f"no feed store at {feed_db}"
        return out

    for tbl, tscol, budget, label, critical in STREAMS:
        r = _q1(fc, f"SELECT COUNT(*), MAX({tscol}) FROM {tbl}")
        rows = (r[0] if r else 0) or 0
        age = (now - r[1]) if (r and r[1]) else None
        out["streams"].append({
            "label": label, "table": tbl, "rows": rows,
            "age_s": round(age) if age is not None else None,
            "bulb": _bulb(rows, age, budget, in_rth), "critical": critical})

    r = _q1(fc, "SELECT symbol, interval, COUNT(*), MAX(ts_epoch_ms)"
                " FROM candles GROUP BY symbol, interval")
    try:
        rows = fc.execute("SELECT symbol, interval, COUNT(*), MAX(ts_epoch_ms)"
                          " FROM candles GROUP BY symbol, interval").fetchall()
    except sqlite3.Error:
        rows = []
    for sym, iv, n, newest in rows:
        age = now - (newest or 0) / 1000.0
        out["candles"].append({
            "label": f"{sym}/{iv}", "rows": n, "age_s": round(age),
            "bulb": _bulb(n, age, CANDLE_BUDGET.get(iv, 3600), in_rth)})

    if os.path.exists(derived_db):
        dc = sqlite3.connect(f"file:{derived_db}?mode=ro", uri=True)
        # Engine self-reports, if the layer has run at all.
        try:
            rows = conn.execute(
                "SELECT name, runs, failures, last_rows, last_error"
                " FROM derived_engine_status ORDER BY name").fetchall()
            rep["engines"] = [{"name": r[0], "runs": r[1], "failures": r[2],
                               "last_rows": r[3], "last_error": r[4]}
                              for r in rows]
        except Exception:                                       # noqa: BLE001
            # ⚠️ NOT AN ERROR ON AN OLD BOX — the table only exists once a box
            # runs the build that writes it. None means "cannot say"; [] would
            # claim the layer ran and reported nothing, which is a real and
            # different finding.
            rep["engines"] = None

        for tbl, tscol, budget, label in DERIVED:
            r = _q1(dc, f"SELECT COUNT(*), MAX({tscol}) FROM {tbl}")
            rows = (r[0] if r else 0) or 0
            age = (now - r[1]) if (r and r[1]) else None
            out["derived"].append({
                "label": label, "rows": rows,
                "age_s": round(age) if age is not None else None,
                # ⚠️ DERIVED PORTS NEVER PAINT THE ROLLUP RED. Operator's
                # standing rule: derivers are contributors, never gates. A
                # missing derived value is not an outage.
                "bulb": _bulb(rows, age, budget, in_rth)})
    return out


def rollup(rep: dict) -> str:
    """One bulb for status.py. RED only when something TRADING needs is gone."""
    if rep.get("fatal"):
        return RED
    crit = [s for s in rep["streams"] if s["critical"]]
    cand = rep["candles"]
    if any(s["bulb"] == RED for s in crit) or not cand:
        return RED
    if any(c["bulb"] == RED for c in cand):
        return RED
    if any(s["bulb"] == AMBER for s in crit) or any(c["bulb"] == AMBER for c in cand):
        return AMBER
    return GREEN


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--bulb", action="store_true",
                    help="one line for status.py")
    ap.add_argument("--feed-db",
                    default=os.path.expanduser("~/options-trader/data/feed_store.db"))
    ap.add_argument("--derived-db",
                    default=os.environ.get(
                        "OT_DERIVED_DB",
                        os.path.expanduser("~/options-trader/data/derived_store.db")))
    a = ap.parse_args()

    in_rth = _rth_now()
    rep = collect(a.feed_db, a.derived_db, in_rth)
    r = rollup(rep)

    if a.bulb:
        bad = [s["label"] for s in rep.get("streams", [])
               if s["critical"] and s["bulb"] in (RED, AMBER)]
        bad += [c["label"] for c in rep.get("candles", []) if c["bulb"] in (RED, AMBER)]
        # ⚠️ NEVER PRINT A DANGLING ARROW. When the store is missing entirely
        # there are no per-stream labels to name, and "DOWN  ← " reads like a
        # truncated message rather than a diagnosis.
        if rep.get("fatal"):
            bad = ["no feed store"]
        note = ("  ← " + ", ".join(bad[:4])) if (r != GREEN and bad) else ""
        print(f"{r} Manifold:    {'GREEN' if r == GREEN else ('DEGRADED' if r == AMBER else 'DOWN')}{note}")
        return 0 if r == GREEN else 1

    if a.json:
        print(json.dumps({"rollup": r, **rep}, indent=2))
        return 0 if r == GREEN else 1

    print("=" * 62)
    print(f"  MANIFOLD HEALTH   {r}   " +
          ("RTH" if in_rth else "outside RTH — idle streams are ⚪, not faults"))
    print("=" * 62)
    if rep.get("fatal"):
        print(f"  {RED} {rep['fatal']}")
        return 1

    print("  RAW STREAMS")
    for s in rep["streams"]:
        age = "—" if s["age_s"] is None else f"{s['age_s']}s"
        star = "*" if s["critical"] else " "
        print(f"   {s['bulb']}{star} {s['label']:<22} rows={s['rows']:<8} age={age}")

    print("\n  CANDLES")
    for c in sorted(rep["candles"], key=lambda x: x["label"]):
        print(f"   {c['bulb']}  {c['label']:<22} rows={c['rows']:<8} age={c['age_s']}s")

    if rep["derived"]:
        print("\n  DERIVED  (contributors — never gate trading)")
        for d in rep["derived"]:
            age = "—" if d["age_s"] is None else f"{d['age_s']}s"
            print(f"   {d['bulb']}  {d['label']:<22} rows={d['rows']:<8} age={age}")
    # 🔴 THE ENGINE'S OWN ACCOUNT, NEXT TO THE ROW COUNT. On 2026-08-24 two
    # engines showed rows=0 with no error anywhere, and the row count alone
    # could not distinguish "never ran", "ran and wrote nothing", and "ran and
    # failed". Those are three different faults with three different fixes.
    # ⚠️ ABSENT IS SAID OUT LOUD. An engine missing from the table has never
    # completed a single pass since the last restart, which is itself a finding
    # — and printing nothing for it would hide exactly that.
    st = rep.get("engines")
    if st:
        print("\n  ENGINES  (each engine's own account of itself)")
        for e in st:
            err = e.get("last_error") or ""
            print(f"   {e['name']:<14} runs={e['runs']:<6} fail={e['failures']:<4}"
                  f" last_rows={e['last_rows']:<5}"
                  + (f"  ERR {err[:40]}" if err else ""))
    elif st is not None:
        print("\n  ENGINES  no engine has completed a pass since restart")

    print("=" * 62)
    print(f"  ROLLUP: {r}   (* = trading depends on it)")
    return 0 if r == GREEN else 1


if __name__ == "__main__":
    sys.exit(main())
