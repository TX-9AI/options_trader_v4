#!/usr/bin/env python3
"""
tests/exit_replay.py  v1.0
REPLAY EVERY CLOSED TRADE'S REAL PREMIUM PATH — rebuilt from `quote_series` —
under alternative exit ladders. The manifold's first paying consumer.

v1.0  2026-08-23  Built for the R-factor project. stop_sweep.py works on two
extremes per trade; this works on the WHOLE PATH, so trail parameters (arm
level, giveback width) become measurable instead of argued. This is exactly
the data FEED_MANIFOLD.md said was being destroyed when chain_marks was
last-write-wins — kept per tick since r61, consumed here for the first time.

HOW A PATH IS BUILT
  · Legs come from the row's own symbol columns (short/long/lower/center/
    upper). Sign: shorts −, longs +, orientation flipped for
    is_short_position so a RISING path is always FAVOURABLE. Single-leg
    debit rows carry no leg columns and fall back to `symbol`-prefix
    matching in quote_series only when it resolves to EXACTLY ONE contract;
    ambiguity is refused, never guessed.
  · Each leg's mid = (bid+ask)/2, forward-filled onto the union clock.
    Marks outside (0, 1e6) are dropped at ingest — finite is not sane.
  · ⚠️ COVERAGE IS A GATE. Expected points = trade lifetime / 15s. Below
    50% the trade is refused BY NAME with its drop reason (r39: a tool-caused
    absence must not wear the costume of a null). Refusals are summarised;
    a report with silent drops is the defect class this repo keeps finding.

RULES REPLAYED (premium-fraction space, per side convention as live):
  stop only · stop+TP · trail(arm A, give G): once favourable ≥ A, exit when
  path falls G below its running peak. The RECORDED exit is replayed too and
  must reconcile with pnl_usd within tolerance — a path that cannot
  reproduce what actually happened is not trusted to score hypotheticals
  (positive control, DRF.1's lesson).

Run:  python3 tests/exit_replay.py [--db trades.db] [--feed feed_store.db]
      python3 tests/exit_replay.py --selftest
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r_ledger import _f, DEFAULT_DB  # noqa: E402

DEFAULT_FEED = os.path.join(os.path.expanduser("~"), "options-trader", "data",
                            "feed_store.db")
POLL_S = 15.0
MIN_COVERAGE = 0.50
RECONCILE_TOL = 0.35        # |replayed recorded-rule pnl − pnl_usd| / risk

TRAILS = [(0.25, 0.10), (0.25, 0.15), (0.50, 0.15), (0.50, 0.25), (0.75, 0.25)]
STOPS = [0.15, 0.25]


def _ts(v):
    try:
        return datetime.fromisoformat(str(v)).timestamp()
    except Exception:                                           # noqa: BLE001
        return None


def legs_of(row: dict):
    """[(streamer_symbol, +1/-1 in FAVOURABLE orientation)] or (None, reason)."""
    short = -1
    long_ = +1
    legs = []
    for col, sign in (("short_symbol", short), ("long_symbol", long_),
                      ("lower_symbol", long_), ("upper_symbol", long_),
                      ("center_symbol", short)):
        s = row.get(col)
        if s:
            legs.append((str(s), sign))
    if not legs:
        return None, "no leg symbols on row"
    # orientation: make favourable positive. For a credit position the
    # combo value FALLS when we win, so flip.
    flip = -1 if row.get("is_short_position") else 1
    return [(s, sign * flip) for s, sign in legs], ""


def path_for(feed_con, legs, t0, t1):
    """Combined signed-mid path on the union clock, forward-filled per leg."""
    series = {}
    for sym, _sign in legs:
        rows = feed_con.execute(
            "SELECT ts_epoch, bid_price, ask_price FROM quote_series"
            " WHERE streamer_symbol=? AND ts_epoch BETWEEN ? AND ?"
            " ORDER BY ts_epoch", (sym, t0 - 60, t1 + 60)).fetchall()
        pts = []
        for ts, b, a in rows:
            b, a = _f(b), _f(a)
            if b and a and 0 < b < 1e6 and 0 < a < 1e6 and a >= b:
                pts.append((ts, (b + a) / 2.0))
        if not pts:
            return None, f"no usable quotes for {sym}"
        series[sym] = pts
    clock = sorted({ts for pts in series.values() for ts, _ in pts if t0 <= ts <= t1})
    if not clock:
        return None, "no timestamps inside the trade window"
    idx = {s: 0 for s in series}
    last = {s: None for s in series}
    out = []
    for t in clock:
        val = 0.0
        ok = True
        for (sym, sign) in legs:
            pts = series[sym]
            i = idx[sym]
            while i < len(pts) and pts[i][0] <= t:
                last[sym] = pts[i][1]
                i += 1
            idx[sym] = i
            if last[sym] is None:
                ok = False
                break
            val += sign * last[sym]
        if ok:
            out.append((t, val))
    return out, ""


def replay(path, entry_val, risk, rule):
    """pnl in combo-value points for one rule. rule = ('stop',s) | ('tp',s,t)
    | ('trail',s,arm,give). Favourable = value UP (legs_of already oriented)."""
    kind = rule[0]
    stop = rule[1]
    peak = entry_val
    armed = False
    for _t, v in path:
        move = v - entry_val
        peak = max(peak, v)
        if move <= -stop * risk:
            return -stop * risk
        if kind == "tp" and move >= rule[2] * risk:
            return rule[2] * risk
        if kind == "trail":
            if not armed and move >= rule[2] * risk:
                armed = True
            if armed and (peak - v) >= rule[3] * risk:
                return v - entry_val
    return path[-1][1] - entry_val if path else 0.0


def run(db, feed) -> int:
    tcon = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    tcon.row_factory = sqlite3.Row
    fcon = sqlite3.connect(f"file:{feed}?mode=ro", uri=True)
    rows = [dict(r) for r in tcon.execute(
        "SELECT * FROM trades WHERE status='closed' AND COALESCE(relaxed_entry,0)=0")]
    refused = defaultdict(int)
    totals = defaultdict(lambda: defaultdict(float))
    counts = defaultdict(int)
    recon_fail = 0
    for r in rows:
        t0, t1 = _ts(r.get("entry_time")), _ts(r.get("exit_time"))
        if not t0 or not t1 or t1 <= t0:
            refused["bad timestamps"] += 1
            continue
        legs, why = legs_of(r)
        if legs is None:
            refused[why] += 1
            continue
        path, why = path_for(fcon, legs, t0, t1)
        if not path:
            refused[why or "empty path"] += 1
            continue
        cov = len(path) / max(1.0, (t1 - t0) / POLL_S)
        if cov < MIN_COVERAGE:
            refused[f"coverage<{MIN_COVERAGE:.0%}"] += 1
            continue
        entry_val = path[0][1]
        entry_prem = _f(r.get("entry_premium")) or abs(entry_val) or 1.0
        lot = 100.0 * (_f(r.get("contracts")) or 1)
        # positive control: the recorded stop, replayed, must land near pnl_usd
        rec_stop = 0.25
        rec = replay(path, entry_val, entry_prem, ("stop", rec_stop)) * lot
        pnl = _f(r.get("pnl_usd")) or 0.0
        if abs(rec - pnl) > max(50.0, RECONCILE_TOL * rec_stop * entry_prem * lot * 4):
            recon_fail += 1
        key = (r.get("strategy") or "?", (r.get("option_side") or "?").lower())
        counts[key] += 1
        totals[key]["recorded"] += pnl
        for s in STOPS:
            totals[key][f"stop {s:.2f}"] += replay(path, entry_val, entry_prem,
                                                   ("stop", s)) * lot
        for arm, give in TRAILS:
            totals[key][f"trail a{arm:.2f}/g{give:.2f}"] += replay(
                path, entry_val, entry_prem, ("trail", 1.0, arm, give)) * lot
    print("=" * 70)
    print("  EXIT REPLAY — real premium paths from quote_series, dollars")
    print("=" * 70)
    for key in sorted(counts):
        print(f"\n  {key[0]} · {key[1]}   n={counts[key]} replayed")
        for rule, net in sorted(totals[key].items(), key=lambda kv: -kv[1]):
            mark = "  <- recorded" if rule == "recorded" else ""
            print(f"    {rule:<22} ${net:>10,.0f}{mark}")
    if refused:
        print("\n  REFUSED (named, per r39 — these are the tool's gaps, not the tape's):")
        for why, n in sorted(refused.items(), key=lambda kv: -kv[1]):
            print(f"    {why:<40} {n}")
    if recon_fail:
        print(f"\n  ⚠️ POSITIVE CONTROL: {recon_fail} trade(s) whose replayed "
              f"recorded-rule pnl did not reconcile with pnl_usd — treat every "
              f"hypothetical above as suspect until this is zero or explained.")
    if not counts:
        print("\n  nothing replayable yet — quote_series needs its first live "
              "sessions (and the series push, s3_push v4.2, to reach control).")
    return 0


def selftest() -> int:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE quote_series (streamer_symbol TEXT, ts_epoch REAL,"
                " bid_price REAL, ask_price REAL)")
    # A long call: mid runs 1.00 -> 2.00 by t=300 then back to 1.20 at t=600
    for i in range(41):
        t = i * 15.0
        mid = 1.0 + (t / 300.0) if t <= 300 else 2.0 - 0.8 * ((t - 300) / 300.0)
        con.execute("INSERT INTO quote_series VALUES (?,?,?,?)",
                    ("X 260823C100", 1000 + t, mid - 0.02, mid + 0.02))
    legs = [("X 260823C100", +1)]
    path, why = path_for(con, legs, 1000, 1600)
    ok = bool(path) and not why and len(path) == 41
    r_hold = replay(path, path[0][1], 1.0, ("stop", 0.25))
    ok &= abs(r_hold - 0.20) < 0.03           # rode up, gave back to +0.20
    r_trail = replay(path, path[0][1], 1.0, ("trail", 1.0, 0.25, 0.15))
    ok &= 0.80 < r_trail < 0.92               # trail keeps ~+0.85 of the +1.00 peak
    r_tp = replay(path, path[0][1], 1.0, ("tp", 0.25, 0.50))
    ok &= abs(r_tp - 0.50) < 1e-9
    # deliberate failures: coverage refusal + ambiguity refusal
    sparse, _ = path_for(con, legs, 0, 20000)
    cov = len(sparse or []) / ((20000 - 0) / POLL_S)
    ok &= cov < MIN_COVERAGE
    lg, why2 = legs_of({"is_short_position": 0})
    ok &= lg is None and "no leg symbols" in why2
    print("exit_replay selftest:", "ALL PASS" if ok else
          f"FAIL hold={r_hold} trail={r_trail} tp={r_tp} cov={cov:.2f}")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--feed", default=DEFAULT_FEED)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    for p, name in ((a.db, "trades db"), (a.feed, "feed store")):
        if not os.path.exists(p):
            print(f"exit_replay: no {name} at {p}")
            return 0
    return run(a.db, a.feed)


if __name__ == "__main__":
    sys.exit(main())
