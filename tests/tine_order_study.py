#!/usr/bin/env python3
"""
tests/tine_order_study.py  v4.0
Does the fork's slope predict which rail price taps first? And does being WRONG
matter?

v4.0  2026-08-20  Built at the OTV4 split.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
THE QUESTION, AND WHY IT IS TWO QUESTIONS
════════════════════════════════════════════════════════════════════════════
v3's PF.5 spec derived the condor's leg order from the fork's apparent slope:
an UP-sloping fork means price travels lower rail -> upper rail over the
session, so it taps the LOWER rail first and the PUT side fills first.

**That ordering is no longer used.** `v-indep-legs` (2026-07-28) made both sides
independent - each fires on its own price trigger, checked every tick - so
whichever tine price actually strikes first fills first. `_leg_order_from_slope`
survives as a helper **with no caller**, and docs/TRADES.md still described the
superseded design.

Operator, 2026-08-20: *"Is hitting the 'wrong' tine first kind of scary in that
it already is deviating from our belief in the structure?"*

**That is a better question than the ordering one**, and it splits in two:
  1. **IS THE SLOPE PREDICTIVE AT ALL?** If first-tap is an even split, order is
     noise, the helper gets deleted, and the doc gets corrected. Done.
  2. **DOES A WRONG-TINE TAP PREDICT TROUBLE?** This is the one that matters
     even if (1) is a coin. The slope is not a coin flip in principle - **it is
     a claim about where price sits in its own channel.** An up-sloping fork
     with price near the lower rail says the traverse runs upward. If price
     taps the UPPER rail first, either the fork was drawn on the wrong pivots or
     price is moving against the channel's geometry - and **the condor's first
     position would be opened by an event that contradicts the model that
     placed it.**

⚠️ **AN EVEN SPLIT ON (1) WITH A SKEW ON (2) IS THE INTERESTING RESULT**, not a
contradiction: order would predict nothing while wrong-order predicted trouble.

⚠️ AND THE OPERATOR'S OWN ACCEPTED RISK MAKES (2) SHARPER: *"If it gets
breached, then our fork may also become invalid & I can live with that."* A
wrong-tine tap is not a breach - but it is the first evidence pointing there,
and a condor is a structure where being told early beats being right late.

════════════════════════════════════════════════════════════════════════════
METHOD
════════════════════════════════════════════════════════════════════════════
Per (session, symbol) with a valid DAILY fork:
  · which rail did price reach FIRST, and did the slope call it
  · did price then TRAVERSE to the other rail  (the condor completing)
  · did the fork SURVIVE the session, or was a rail decisively breached

⚠️ ONE OBSERVATION PER SESSION, NOT PER TICK. A fork observed on 300 ticks is
one event. Counting ticks would inflate every interval into fiction.
⚠️ AND THE FORK IS BUILT FROM BARS UP TO THE DECISION POINT ONLY. A fork fitted
on the whole session would be drawn using the very moves it is meant to predict.
"""

import argparse
import csv
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OHLC = os.path.expanduser("~/day_trader_pro/ohlc")
POLLUTED = {"2026-08-14"}


def _wilson(k, n):
    if n == 0:
        return (0.0, 1.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load(path):
    rows = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            try:
                rows.append((r["timestamp"][11:16], float(r["open"]),
                             float(r["high"]), float(r["low"]), float(r["close"])))
            except Exception:                                  # noqa: BLE001
                continue
    return rows


def simple_channel(rows, upto):
    """A regression channel over bars[:upto] - slope plus 2-sigma rails.

    ⚠️ A STAND-IN FOR THE PITCHFORK, AND NAMED AS ONE. `analysis/pitchfork.py`
    needs a pandas frame, ATR and its own pivot qualification; a regression
    channel is not that and is not called one. **What it shares is the property
    under test** - a slope and two parallel rails - which is enough to ask
    whether slope predicts first contact. If the answer is interesting, the real
    fork is the follow-up, not the conclusion.
    """
    seg = rows[:upto]
    if len(seg) < 40:
        return None
    cs = [r[4] for r in seg]
    n = len(cs)
    mx = (n - 1) / 2.0
    my = sum(cs) / n
    den = sum((k - mx) ** 2 for k in range(n)) or 1e-9
    slope = sum((k - mx) * (cs[k] - my) for k in range(n)) / den
    resid = [cs[k] - (my + slope * (k - mx)) for k in range(n)]
    sd = (sum(r * r for r in resid) / n) ** 0.5 or 1e-9
    return {"slope": slope, "sd": sd, "mid_at": lambda i: my + slope * (i - mx),
            "n0": n}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ohlc", default=OHLC)
    ap.add_argument("--decide-bar", type=int, default=60,
                    help="bars into the session at which the fork is fitted")
    ap.add_argument("--rail-sigma", type=float, default=2.0)
    ap.add_argument("--flat-eps", type=float, default=0.0,
                    help="|slope| below this counts as FLAT and is excluded")
    a = ap.parse_args(argv[1:])

    obs = []
    days = sorted(os.path.basename(d) for d in
                  glob.glob(os.path.join(os.path.expanduser(a.ohlc), "*"))
                  if os.path.isdir(d))
    days = [d for d in days if d not in POLLUTED]
    for day in days:
        for p in sorted(glob.glob(os.path.join(
                os.path.expanduser(a.ohlc), day, "*_ohlc_*.csv"))):
            sym = os.path.basename(p).split("_ohlc_")[0].upper()
            try:
                rows = [r for r in load(p) if "09:30" <= r[0] <= "16:00"]
            except Exception:                                  # noqa: BLE001
                continue
            if len(rows) < a.decide_bar + 60:
                continue
            ch = simple_channel(rows, a.decide_bar)
            if not ch or abs(ch["slope"]) <= a.flat_eps:
                continue

            up_slope = ch["slope"] > 0
            # ⚠️ THE PREDICTION: an UP-sloping channel means price travels
            # lower rail -> upper rail, so it should tap the LOWER rail first.
            predicted = "lower" if up_slope else "upper"

            first, first_i = None, None
            traversed = False
            breached = False
            for i in range(a.decide_bar, len(rows)):
                mid = ch["mid_at"](i)
                up_rail = mid + a.rail_sigma * ch["sd"]
                lo_rail = mid - a.rail_sigma * ch["sd"]
                _, _, h, l, c = rows[i]
                if first is None:
                    if h >= up_rail:
                        first, first_i = "upper", i
                    elif l <= lo_rail:
                        first, first_i = "lower", i
                else:
                    other = lo_rail if first == "upper" else up_rail
                    if (first == "upper" and l <= other) or \
                       (first == "lower" and h >= other):
                        traversed = True
                    # decisive breach: a CLOSE beyond the rail by a further
                    # half-sigma - a wick is a touch, a close is a decision
                    if c >= up_rail + 0.5 * ch["sd"] or \
                       c <= lo_rail - 0.5 * ch["sd"]:
                        breached = True
            if first is None:
                continue
            obs.append({"day": day, "sym": sym, "predicted": predicted,
                        "first": first, "correct": first == predicted,
                        "traversed": traversed, "breached": breached,
                        "up_slope": up_slope})

    if not obs:
        print("no sessions with a rail tap. ABSENT MEASUREMENT, not a null.")
        return 1

    n = len(obs)
    k = sum(1 for o in obs if o["correct"])
    lo, hi = _wilson(k, n)
    print("=" * 80)
    print("TINE ORDER STUDY - does the slope predict which rail is tapped first?")
    print(f"  {n:,} (session, symbol) observations, "
          f"{len({o['day'] for o in obs})} dates, "
          f"{len({o['sym'] for o in obs})} symbols")
    print(f"  channel fitted on the first {a.decide_bar} bars only - no lookahead")
    print("=" * 80)

    print(f"\n  1. IS THE SLOPE PREDICTIVE AT ALL?")
    print(f"     slope called the first rail: {k}/{n} = {k/n:.0%}   "
          f"95% CI [{lo:.0%}, {hi:.0%}]")
    if hi < 0.50:
        print("     ⚠️ INVERSE - price taps the rail it is moving AWAY from first.")
    elif lo > 0.50:
        print("     ✅ PREDICTIVE - the interval excludes a coin.")
    else:
        print("     ❌ A COIN - the interval spans 50%. **Order is noise**: delete")
        print("        `_leg_order_from_slope` and correct docs/TRADES.md §5,")
        print("        which still describes the superseded PF.5 ordering.")

    print(f"\n  2. DOES A WRONG-TINE TAP PREDICT TROUBLE?")
    print("     ⚠️ THE QUESTION THAT MATTERS EVEN IF (1) IS A COIN.")
    print(f"    {'first tap':16}{'n':>7}{'traversed':>12}{'breached':>11}")
    print("    " + "-" * 46)
    for lbl, sel in (("as predicted", [o for o in obs if o["correct"]]),
                     ("WRONG tine", [o for o in obs if not o["correct"]])):
        if not sel:
            continue
        t = sum(1 for o in sel if o["traversed"]) / len(sel)
        b = sum(1 for o in sel if o["breached"]) / len(sel)
        print(f"    {lbl:16}{len(sel):>7}{t:>11.0%}{b:>11.0%}")

    ct = [o for o in obs if o["correct"]]
    wt = [o for o in obs if not o["correct"]]
    if len(ct) >= 30 and len(wt) >= 30:
        tc = sum(1 for o in ct if o["traversed"]) / len(ct)
        tw = sum(1 for o in wt if o["traversed"]) / len(wt)
        bc = sum(1 for o in ct if o["breached"]) / len(ct)
        bw = sum(1 for o in wt if o["breached"]) / len(wt)
        print(f"\n     traverse gap: {tc - tw:+.0%}   breach gap: {bw - bc:+.0%}")
        print("     **A traverse is the condor COMPLETING; a breach is the")
        print("     thesis dying.** A wrong-tine tap that traverses less AND")
        print("     breaches more is the operator's instinct measured.")
        if abs(tc - tw) < 0.05 and abs(bw - bc) < 0.05:
            print("     ❌ NEITHER GAP IS MATERIAL - a wrong-tine tap is not")
            print("        informative, and order is moot in both senses.")

    print("\n  ⚠️ THIS USES A REGRESSION CHANNEL, NOT THE PITCHFORK. It shares the")
    print("     property under test - a slope and two parallel rails - which is")
    print("     enough to ask whether slope predicts first contact. **If the")
    print("     answer is interesting, the real fork is the follow-up, not the")
    print("     conclusion.**")
    print("  ⚠️ AND ONE OBSERVATION PER SESSION. A fork seen on 300 ticks is one")
    print("     event, not 300.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
