#!/usr/bin/env python3
"""
tests/character_band_study.py  v1.0
v1.0  2026-09-11  r354 / CHR.1 — DERIVE THE BANDS FROM THE SAMPLE THAT WAS
      COLLECTED FOR EXACTLY THIS.

🔴 WHY THE ENGINE IS OFF. r85 set `BANDS_SET = False` after F4 found the old
measure computed an INTRABAR WICK RATIO rather than directional persistence.
`efficiency()` — net travel / total travel — is a different quantity, so the
four provisional numbers carry no information about it:

    PERSIST_TREND = 0.62   PERSIST_RANGE = 0.38
    VOL_EXPAND    = 1.25   VOL_COMPRESS  = 0.80

The ruling was to emit NOTHING rather than a guess, and `analysis/character.py`
names the exit condition itself: *"read_character RETURNS None UNTIL A SESSION
OF REAL EFFICIENCY VALUES EXISTS TO SET BANDS FROM… flip this to True in the
same commit that replaces the four numbers below with measured ones."*

🔑 THAT SAMPLE HAS EXISTED SINCE r270 (2026-09-05). `character_axis_sample`
carries `efficiency`, `vol_ratio`, `close_capture`, both realised-vol
estimators, ADX, ATR and price, per symbol, strided, pushed to S3. The bar was
ONE session. This reads what is actually there.

⚠️ PERCENTILES, NOT A FIT. The bands are cut points on the OBSERVED
distribution — no outcome is consulted, nothing is optimised against P&L. That
is deliberate: this names the tape, it does not predict it, and fitting a
descriptor to returns is how a label ends up traded (the v3 argmax, which
produced a winner even when there was nothing to choose between).

⚠️ AND IT REPORTS PER SYMBOL BEFORE POOLING. CVX and SPX are unlikely to share
an efficiency distribution; one global pair of bands would label them wrongly
in OPPOSITE directions. The spread across symbols is printed so that choice is
made on evidence rather than convenience.

⚠️ `MIN_WINDOW_BARS` — the engine refuses an efficiency below 20 bars as noise.
Rows with a null axis are counted and excluded, never read as zero.

Run (CONTROL):
    python3 tests/character_band_study.py --from 2026-09-05 --to 2026-09-10
    python3 tests/character_band_study.py --date 2026-09-10 --symbol SPX
    python3 tests/character_band_study.py --selftest
"""
from __future__ import annotations

import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The shape the four constants take: trend/range as a high/low split of
# efficiency, expand/compress as a high/low split of the vol ratio.
CUTS = ((0.70, 0.30), (0.75, 0.25), (0.80, 0.20))


def pct(xs, f):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(len(s) * f))]


def summarise(vals):
    return {k: pct(vals, v) for k, v in
            (("p10", .10), ("p25", .25), ("p50", .50),
             ("p75", .75), ("p90", .90))}


def coverage(rows):
    """-> (per-symbol axis lists, nulls). A null axis is EXCLUDED and counted."""
    eff = collections.defaultdict(list)
    vr = collections.defaultdict(list)
    nulls = collections.Counter()
    for r in rows:
        sym = r.get("symbol") or "?"
        e, v = r.get("efficiency"), r.get("vol_ratio")
        if e is None:
            nulls["efficiency"] += 1
        else:
            eff[sym].append(float(e))
        if v is None:
            nulls["vol_ratio"] += 1
        else:
            vr[sym].append(float(v))
    return eff, vr, nulls


def render(eff, vr, nulls, window):
    all_e = [x for v in eff.values() for x in v]
    all_v = [x for v in vr.values() for x in v]
    print("=" * 74)
    print("  CHARACTER BANDS — from the measured sample   [{}]".format(window))
    print("=" * 74)
    if not all_e:
        print("  no efficiency values in the window — nothing to derive from.")
        return
    print("  rows: efficiency {:,} · vol_ratio {:,} · symbols {}".format(
        len(all_e), len(all_v), len(eff)))
    if nulls:
        print("  ⚠️ excluded nulls: " + ", ".join(
            "{} {:,}".format(k, n) for k, n in sorted(nulls.items())))

    for name, vals, live in (("efficiency", all_e, (0.62, 0.38)),
                             ("vol_ratio", all_v, (1.25, 0.80))):
        if not vals:
            continue
        s = summarise(vals)
        print("\n  {} (pooled, n={:,})".format(name, len(vals)))
        print("     p10 {:.3f} · p25 {:.3f} · median {:.3f} · p75 {:.3f} · "
              "p90 {:.3f}".format(s["p10"], s["p25"], s["p50"],
                                  s["p75"], s["p90"]))
        print("     PROVISIONAL bands now: high {:.2f} / low {:.2f}  "
              "-> would tag {:.1%} high, {:.1%} low".format(
                  live[0], live[1],
                  sum(1 for x in vals if x >= live[0]) / len(vals),
                  sum(1 for x in vals if x <= live[1]) / len(vals)))
        print("     {:<12} {:>9} {:>9}   share tagged".format(
            "candidate", "high", "low"))
        print("     " + "-" * 52)
        for hi, lo in CUTS:
            h, l = pct(vals, hi), pct(vals, lo)
            print("     {:<12} {:>9.3f} {:>9.3f}   {:.0%} / {:.0%}".format(
                "p{:.0f}/p{:.0f}".format(hi * 100, lo * 100), h, l,
                1 - hi, lo))

    print("\n  PER SYMBOL — efficiency")
    print("  {:<7} {:>6} {:>8} {:>8} {:>8}".format("sym", "n", "p25", "median", "p75"))
    print("  " + "-" * 42)
    for sym in sorted(eff, key=lambda s: -(pct(eff[s], .50) or 0)):
        v = eff[sym]
        print("  {:<7} {:>6,} {:>8.3f} {:>8.3f} {:>8.3f}".format(
            sym, len(v), pct(v, .25), pct(v, .50), pct(v, .75)))
    meds = [pct(v, .50) for v in eff.values() if v]
    if len(meds) > 1:
        print("     ⚠️ spread of per-symbol medians: {:.3f} .. {:.3f}. If that "
              "gap is".format(min(meds), max(meds)))
        print("        wide, ONE global pair of bands labels symbols wrongly "
              "in OPPOSITE")
        print("        directions — per-symbol bands are the alternative.")

    print("\n  ⚠️ PERCENTILES, NOT A FIT — no outcome is consulted and nothing")
    print("     is optimised against P&L. This names the tape; it does not")
    print("     predict it.")
    print("  ⚠️ Descriptive. Flipping BANDS_SET is the operator's call, and")
    print("     `analysis/character.py` requires it in the SAME commit that")
    print("     replaces the four numbers (WA §31, §5).")


def selftest() -> int:
    ok = True
    rows = [{"symbol": "A", "efficiency": e, "vol_ratio": 1.0}
            for e in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
    rows.append({"symbol": "A", "efficiency": None, "vol_ratio": None})
    eff, vr, nulls = coverage(rows)
    ok &= len(eff["A"]) == 10 and nulls["efficiency"] == 1
    ok &= abs(pct(eff["A"], .50) - 0.6) < 1e-9
    # a null axis must be EXCLUDED, never read as zero
    ok &= 0.0 not in eff["A"]
    ok &= summarise([])["p50"] is None
    print("character_band_study selftest:", "ALL PASS" if ok else "FAIL")
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
    syms = [a.symbol.upper()] if a.symbol else None
    rows, meta = ws.load_series("character_axis_sample", dates, symbols=syms)
    print("  SOURCE: " + meta.banner())
    eff, vr, nulls = coverage(rows)
    render(eff, vr, nulls, "{}..{}".format(dates[0], dates[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
