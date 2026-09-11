#!/usr/bin/env python3
"""
tests/tcs_wing_study.py  v1.0
v1.0  2026-09-10  r351 / TCS.1 — WHAT R DID THE CHAIN ACTUALLY OFFER? Answered
      from data already in the warehouse, tonight.

🔴 THE QUESTION. `wing_r_best` is the single most common last refusal in the
book: over 2026-09-05..09-10 it was the ONLY failing rung on 8,381 TCS ticks —
52% of every "exactly one gate short" — and TCS cleared every gate 7 times in
34,686. The operator watched trending signals all day with no trend trades.
The floor is `r_expiry = credit / (width − credit) >= 1.00`, which demands
**credit >= half the strike width**.

⚠️ THE VALUE WAS NEVER RECORDED, so `PLAN GATES` printed a BLANK fail range
for that rung while `pin_concentration` beside it has percentiles. r351's
in-strategy change fixes that FORWARD. This file answers it BACKWARD, from
`raw/chain_snapshots` — which carry `strike`, `bid` and `ask` per contract —
so the floor can be chosen tonight instead of after another session.

🔑 IT RECOMPUTES THE STRATEGY'S OWN ARITHMETIC, not an approximation of it:

    width  = |short_strike − long_strike|      long beyond the short
    credit = short.bid − long.ask              the judged side (r219)
    r      = credit / (width − credit)

Same three lines as `trend_credit_spread`. A wing is a candidate only if the
credit is positive and narrower than the width, exactly as there.

⚠️ WHAT IT CANNOT REPRODUCE. The snapshot cadence is ~5 minutes and a tick is
15 seconds, so this measures the chain AT THE NEAREST SNAPSHOT, not the exact
quote the strategy saw. That is fine for a DISTRIBUTION and wrong for
attributing any single tick — the report says so on every run.
⚠️ AND IT DOES NOT APPLY `stop_survivable`, so the counts here are an UPPER
bound on what a lower floor would admit.

⚠️ DESCRIPTIVE. Nothing here sizes or gates anything. The floor is the
operator's call (§5): this only says what the tape was offering.

Run (CONTROL):
    python3 tests/tcs_wing_study.py --from 2026-09-05 --to 2026-09-10
    python3 tests/tcs_wing_study.py --date 2026-09-10 --symbol SPX
    python3 tests/tcs_wing_study.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FLOORS = (0.15, 0.20, 0.25, 0.33, 0.50, 0.75, 1.00)


def wings(short_bid, contracts, short_strike, side):
    """[(r_expiry, width, credit)] for every priceable wing beyond the short.

    The strategy's arithmetic, verbatim: a put's wing sits BELOW the short and
    a call's ABOVE, the credit is the short's bid minus the long's ask, and a
    wing prices only if that credit is positive and smaller than the width.
    """
    out = []
    for c in contracts:
        k = c.get("strike")
        ask = c.get("ask")
        if not k or ask is None or ask < 0:
            continue
        if side == "put" and k >= short_strike:
            continue
        if side == "call" and k <= short_strike:
            continue
        width = abs(short_strike - k)
        credit = short_bid - ask
        if width <= 0 or credit <= 0 or credit >= width:
            continue
        out.append((credit / (width - credit), width, credit))
    return out


def best_r(short_bid, contracts, short_strike, side):
    ws = wings(short_bid, contracts, short_strike, side)
    return max(ws)[0] if ws else None


def _pct(xs, f):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(len(s) * f))]


def render(rows, window, note):
    print("=" * 72)
    print("  TCS WING STUDY — what R did the chain OFFER?   [{}]".format(window))
    print("=" * 72)
    if note:
        print("  " + note)
    if not rows:
        print("  no snapshots with a usable short leg — nothing to measure.")
        return
    rs = [r for _s, _d, r in rows]
    print("\n  best available r_expiry, per symbol-snapshot   (n={})".format(len(rs)))
    print("     p10 {:.3f} · p25 {:.3f} · median {:.3f} · p75 {:.3f} · p90 {:.3f} "
          "· max {:.3f}".format(
              _pct(rs, .10), _pct(rs, .25), _pct(rs, .50),
              _pct(rs, .75), _pct(rs, .90), max(rs)))
    print("\n  {:<8} {:>8} {:>8}   what a floor at this level would admit".format(
        "floor", "admits", "share"))
    print("  " + "-" * 58)
    for f in FLOORS:
        n = sum(1 for r in rs if r >= f)
        bar = "█" * int(round(24 * n / len(rs)))
        print("  {:<8.2f} {:>8} {:>7.1%}   {}".format(f, n, n / len(rs), bar))
    print("\n  ⚠️ LIVE FLOOR IS 1.00 (TCS_R_FLOOR_EXPIRY) — the bottom row.")

    per = collections.defaultdict(list)
    for sym, _d, r in rows:
        per[sym].append(r)
    print("\n  per symbol")
    print("  {:<7} {:>5} {:>8} {:>8} {:>8}".format("sym", "n", "median", "p90", "max"))
    print("  " + "-" * 40)
    for sym in sorted(per, key=lambda s: -_pct(per[s], .50)):
        v = per[sym]
        print("  {:<7} {:>5} {:>8.3f} {:>8.3f} {:>8.3f}".format(
            sym, len(v), _pct(v, .50), _pct(v, .90), max(v)))

    print("\n  ⚠️ Snapshot cadence is ~5 min and a tick is 15s, so this measures")
    print("     the chain at the NEAREST SNAPSHOT — sound for a distribution,")
    print("     wrong for attributing any single tick.")
    print("  ⚠️ `stop_survivable` is NOT applied, so these counts are an UPPER")
    print("     bound on what a lower floor would actually admit.")
    print("  ⚠️ Descriptive. The floor is the operator's call (WA §31, §5).")


def selftest() -> int:
    ok = True
    # a $5-wide put spread: short bid 1.00, long ask 0.40 -> credit 0.60,
    # width 5 -> r = 0.6 / 4.4 = 0.1364. Refused by 1.00, admitted by 0.15? no.
    cs = [{"strike": 95.0, "ask": 0.40}, {"strike": 98.0, "ask": 0.70}]
    r = best_r(1.00, cs, 100.0, "put")
    ok &= abs(r - (0.30 / (2.0 - 0.30))) < 1e-9      # the 98 wing wins: 0.1765
    # a call spread takes strikes ABOVE the short
    r2 = best_r(1.00, [{"strike": 102.0, "ask": 0.70}], 100.0, "call")
    ok &= abs(r2 - (0.30 / (2.0 - 0.30))) < 1e-9
    # credit >= width is not a spread
    ok &= best_r(5.0, [{"strike": 99.0, "ask": 0.10}], 100.0, "put") is None
    # a wing at half the width is exactly r = 1.00 — the live floor
    ok &= abs(best_r(1.00, [{"strike": 98.0, "ask": 0.0}], 100.0, "put") - 1.0) < 1e-9
    # no candidates -> None, never 0.0
    ok &= best_r(1.0, [], 100.0, "put") is None
    print("tcs_wing_study selftest:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to", dest="to")
    ap.add_argument("--symbol")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    import warehouse_source as ws
    dates = ws.dates_of(a)
    meta = ws.Meta("chain_snapshots {}..{}".format(dates[0], dates[-1]))
    syms = [a.symbol.upper()] if a.symbol else None

    rows = []
    skipped = 0
    for env in ws._envelopes(ws.client(), "chain_snapshots", dates, meta, syms):
        rec = env.get("record") or {}
        sym, day = env.get("symbol"), env.get("dt")
        cs = rec.get("contracts") or rec.get("chain") or []
        if not sym or not isinstance(cs, list) or not cs:
            skipped += 1
            continue
        for side in ("put", "call"):
            leg = [c for c in cs if str(c.get("type", "")).lower().startswith(side[0])]
            if len(leg) < 2:
                continue
            # the short leg the strategy would price against: the nearest
            # priceable strike to spot on that side. Without the tick's own
            # `fifty` level this is an approximation, and it is named as one.
            spot = rec.get("underlying") or rec.get("spot")
            if not spot:
                continue
            near = min((c for c in leg if (c.get("bid") or 0) > 0),
                       key=lambda c: abs((c.get("strike") or 0) - spot),
                       default=None)
            if not near:
                continue
            r = best_r(near.get("bid") or 0.0, leg,
                       near.get("strike") or 0.0, side)
            if r is not None:
                rows.append((sym, day, r))
    print("  SOURCE: " + meta.banner())
    render(rows, "{}..{}".format(dates[0], dates[-1]),
           "⚠️ short leg approximated as the nearest priceable strike to spot; "
           "the tick's own level is not in this stream.")
    if skipped:
        print("  ⚠️ {} snapshot(s) had no readable contract list.".format(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
