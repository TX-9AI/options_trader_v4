#!/usr/bin/env python3
"""
tests/r_ledger.py  v1.1
v1.1  2026-08-23  S3 IS THE DEFAULT SOURCE. Operator's baseline requirement:
reports run on control against the bucket; nothing runs on a trading box and
nothing is pulled to control. --db survives as a local-debug escape hatch
ONLY when passed explicitly. The SOURCE line prints on every run so an empty
day and an unreachable warehouse can never look alike.
v1.0  2026-08-23
THE R BASELINE. avg win / avg loss, expectancy, capture and giveback —
per strategy, per option side, per exit reason. Dollars (WA §31).

v1.0  2026-08-23  Built for the R-factor project. The operator's frame:
*"by controlling risk it is not essential to have a high win rate if the
R-value is sufficient across all trades taken."* Nothing in the repo printed
R, so the project starts by building the instrument (a number that has never
been measured cannot be boosted; it can only be talked about).

DEFINITIONS — one place, so every later tool agrees:
  R              = avg(win $) / |avg(loss $)|      (breakeven win-rate = 1/(1+R))
  expectancy     = mean(pnl_usd)                   per trade, in dollars
  MFE$ / MAE$    = the excursion columns converted to position dollars,
                   sign-aware: for a SHORT (credit) position a FALLING premium
                   is favourable, so mfe/mae premium map inversely.
  capture        = pnl / MFE$ on trades whose MFE$ > 0 — how much of what the
                   tape offered the exit kept. THE GIVEBACK POPULATION LIVES
                   HERE and it is the R lever the v3 book proved (trails
                   +$62k vs floors/BOS −$44k).
  giveback       = MFE$ − pnl on winners.

⚠️ RELAXED ROWS ARE EXCLUDED BY DEFAULT (`relaxed_entry=1` is deliberately
junk traffic; fitting anything to it is the exact failure §1.1 of the audit
handoff predicted). `--include-relaxed` exists for plumbing checks only.
⚠️ CALLS AND PUTS SEPARATE — 34.2% put accuracy is the sharpest signature in
the inherited data and pooling blunts it.
⚠️ n < 10 rows print with a THIN tag and no R claim. Thin samples find
mechanisms, not conclusions (WA §12).

Run:  python3 tests/r_ledger.py                          # ~/options-trader/trades.db
      python3 tests/r_ledger.py --db path/to/trades.db
      python3 tests/r_ledger.py --selftest               # planted-data proof
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(os.path.expanduser("~"), "options-trader", "trades.db")
MIN_N = 10


def _f(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def position_dollars(row: dict):
    """(mfe_usd, mae_usd) in POSITION dollars, sign-aware, or (None, None).

    Long/debit: favourable = premium UP  -> mfe$ = (mfe_prem − entry)·100·k
    Short/credit: favourable = premium DOWN -> mfe$ = (entry − mae_prem)·100·k
    ⚠️ For a short position the tracker's *premium* mfe (highest premium seen)
    is the ADVERSE extreme — the mapping below is the whole reason this helper
    exists, and the selftest plants both directions.
    """
    entry = _f(row.get("entry_premium"))
    mfe_p = _f(row.get("mfe_premium"))
    mae_p = _f(row.get("mae_premium"))
    k = _f(row.get("contracts")) or 1
    if entry is None:
        return None, None
    short = bool(row.get("is_short_position"))
    lot = 100.0 * k
    if short:
        mfe = (entry - mae_p) * lot if mae_p is not None else None
        mae = (mfe_p - entry) * lot if mfe_p is not None else None
    else:
        mfe = (mfe_p - entry) * lot if mfe_p is not None else None
        mae = (entry - mae_p) * lot if mae_p is not None else None
    return mfe, mae


def load(db: str, include_relaxed: bool) -> list:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    q = "SELECT * FROM trades WHERE status='closed'"
    if not include_relaxed:
        q += " AND COALESCE(relaxed_entry,0)=0"
    rows = [dict(r) for r in con.execute(q)]
    con.close()
    return rows


def bucket_stats(rows: list) -> dict:
    wins = [r["pnl_usd"] for r in rows if _f(r.get("pnl_usd")) and r["pnl_usd"] > 0]
    losses = [r["pnl_usd"] for r in rows if _f(r.get("pnl_usd")) is not None and r["pnl_usd"] <= 0]
    n = len(wins) + len(losses)
    aw = sum(wins) / len(wins) if wins else None
    al = sum(losses) / len(losses) if losses else None
    R = (aw / abs(al)) if (aw and al) else None
    exp = (sum(wins) + sum(losses)) / n if n else None
    cap_n = cap_sum = give = 0.0
    caps = 0
    for r in rows:
        mfe, _mae = position_dollars(r)
        p = _f(r.get("pnl_usd"))
        if mfe is not None and mfe > 0 and p is not None:
            cap_sum += p / mfe
            caps += 1
            if p > 0:
                give += (mfe - p)
    cap = cap_sum / caps if caps else None
    return {"n": n, "wins": len(wins), "R": R, "avg_win": aw, "avg_loss": al,
            "expectancy": exp, "capture": cap, "giveback": give,
            "net": (sum(wins) + sum(losses)) if n else 0.0}


def _fmt(v, money=False):
    if v is None:
        return "      —"
    return f"{'-' if v < 0 else '+' if money else ''}${abs(v):,.0f}" if money else f"{v:7.2f}"


def render(rows: list) -> int:
    groups = defaultdict(list)
    for r in rows:
        side = (r.get("option_side") or "?").lower()
        groups[(r.get("strategy") or "?", side)].append(r)
    exits = defaultdict(list)
    for r in rows:
        exits[r.get("exit_reason") or "?"].append(r)

    print("=" * 78)
    print("  R LEDGER — dollars only. R = avg win / |avg loss|. breakeven WR = 1/(1+R)")
    print("=" * 78)
    tot = bucket_stats(rows)
    print(f"  BOOK   n={tot['n']}  net={_fmt(tot['net'], True)}  "
          f"R={_fmt(tot['R'])}  expectancy/trade={_fmt(tot['expectancy'], True)}  "
          f"capture={_fmt(tot['capture'])}  giveback={_fmt(tot['giveback'], True)}")
    print()
    print(f"  {'strategy × side':<34}{'n':>4} {'win%':>5} {'R':>7} "
          f"{'avgW':>8} {'avgL':>8} {'exp':>8} {'capture':>8}")
    print("  " + "-" * 76)
    for (strat, side), rs in sorted(groups.items()):
        s = bucket_stats(rs)
        wr = 100.0 * s["wins"] / s["n"] if s["n"] else 0
        thin = "  THIN" if s["n"] < MIN_N else ""
        rr = "  —  " if (s["n"] < MIN_N or s["R"] is None) else f"{s['R']:5.2f}"
        print(f"  {strat[:28] + ' · ' + side:<34}{s['n']:>4} {wr:>4.0f}% {rr:>7} "
              f"{_fmt(s['avg_win'], True):>8} {_fmt(s['avg_loss'], True):>8} "
              f"{_fmt(s['expectancy'], True):>8} {_fmt(s['capture']):>8}{thin}")
    print()
    print("  BY EXIT REASON — where the R actually gets made or given back")
    print(f"  {'exit_reason':<30}{'n':>4} {'win%':>5} {'net':>10} {'capture':>8} {'giveback':>10}")
    print("  " + "-" * 70)
    for reason, rs in sorted(exits.items(), key=lambda kv: -bucket_stats(kv[1])["net"]):
        s = bucket_stats(rs)
        wr = 100.0 * s["wins"] / s["n"] if s["n"] else 0
        print(f"  {reason[:30]:<30}{s['n']:>4} {wr:>4.0f}% {_fmt(s['net'], True):>10} "
              f"{_fmt(s['capture']):>8} {_fmt(s['giveback'], True):>10}")
    print()
    print("  ⚠️ Every number above is descriptive. Nothing here sizes or gates")
    print("     anything until it clears edge_scan's pre-registered bar (WA §31).")
    return 0


def selftest() -> int:
    """Planted rows with KNOWN answers, plus a deliberate failure."""
    rows = [
        # long winner: entry 1.00 -> exit +$150, MFE prem 3.00 => MFE$=200, capture .75
        dict(pnl_usd=150.0, entry_premium=1.0, mfe_premium=3.0, mae_premium=0.8,
             contracts=1, is_short_position=0, strategy="ORB", option_side="call",
             exit_reason="orb_trail_stop", status="closed"),
        # long loser
        dict(pnl_usd=-50.0, entry_premium=1.0, mfe_premium=1.1, mae_premium=0.5,
             contracts=1, is_short_position=0, strategy="ORB", option_side="call",
             exit_reason="premium_stop", status="closed"),
        # SHORT credit winner: entry 2.00, premium fell to 0.50 -> MFE$ = 150
        dict(pnl_usd=120.0, entry_premium=2.0, mfe_premium=2.4, mae_premium=0.5,
             contracts=1, is_short_position=1, strategy="SweepCreditSpread",
             option_side="put", exit_reason="hard_close", status="closed"),
    ]
    ok = True
    mfe, mae = position_dollars(rows[0])
    ok &= abs(mfe - 200.0) < 1e-9 and abs(mae - 20.0) < 1e-9
    mfe, mae = position_dollars(rows[2])
    ok &= abs(mfe - 150.0) < 1e-9 and abs(mae - 40.0) < 1e-9
    s = bucket_stats(rows[:2])
    ok &= abs(s["R"] - 3.0) < 1e-9 and abs(s["expectancy"] - 50.0) < 1e-9
    # deliberate failure: the short mapping must NOT read premium-mfe as favourable
    bad_mfe, _ = position_dollars(dict(rows[2], is_short_position=0))
    ok &= bad_mfe != 150.0
    print("r_ledger selftest:", "ALL PASS" if ok else "FAIL")
    if ok:
        render(rows)
    return 0 if ok else 1


def load_s3(a):
    import warehouse_source as ws
    dates = ws.dates_of(a)
    rows, meta = ws.load_trades(dates)
    print("  " + meta.banner())
    if meta.error:
        return None
    out = [r for r in rows if (r.get("status") or "").lower() == "closed"]
    if not a.include_relaxed:
        out = [r for r in out if not r.get("relaxed_entry")]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="LOCAL sqlite escape hatch; "
                    "default source is the S3 warehouse")
    ap.add_argument("--date")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to", dest="to")
    ap.add_argument("--include-relaxed", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.db:
        if not os.path.exists(a.db):
            print(f"  SOURCE: local {a.db} — 🔴 PATH DOES NOT EXIST (this is a "
                  f"tool fault, not an empty day)")
            return 1
        print(f"  SOURCE: local sqlite {a.db}")
        rows = load(a.db, a.include_relaxed)
    else:
        rows = load_s3(a)
        if rows is None:
            return 1
    if not rows:
        print("r_ledger: zero closed unrelaxed rows in this window — the "
              "baseline does not exist yet")
        return 0
    return render(rows)


if __name__ == "__main__":
    sys.exit(main())
