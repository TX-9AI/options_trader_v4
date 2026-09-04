#!/usr/bin/env python3
"""
tests/check_tcs_fifty.py  v1.0
v1.0  2026-09-04  r238 — THE CREDIT VERSION OF THE RUNAWAY. Operator's spec,
      2026-09-04: after 11:31, no open debit, a 1m close beyond the 50 HELD at
      the next tick, sell the nearest OTM strike from CURRENT PRICE on the
      floor side, wing set for 1:1, stop at 15% of credit.

⚠️ EXECUTED, NOT READ (§21). Every check drives the real `prepare()`.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


class K:
    def __init__(self, k, b, a):
        self.strike, self.bid, self.ask = float(k), b, a
        self.mark = (b + a) / 2.0


class Chain:
    def __init__(self, puts):
        self.puts, self.calls = puts, []


class Orb:
    def __init__(self, accepted=True, fifty=947.0, d="long"):
        self.fifty_accepted, self.target_50pct, self.break_direction = accepted, fifty, d


def main():
    from strategy.trend_credit_spread import TrendCreditSpread
    from utils.time_utils import ET
    import config as C

    # the operator's own example: 50 at 947, strikes 5 apart, spot just above.
    # ⚠️ THE BID IS 2.95, NOT 2.70, AND THE FIRST DRAFT PROVED WHY. At 2.70 the
    # credit is 2.30 on a 5-wide, R = 2.30/2.70 = 0.85, and the plan REFUSED —
    # correctly. 1:1 on the expiry basis needs credit >= 50% OF WIDTH, so a
    # near-ATM short is not a nicety, it is the only way the floor is reachable.
    # The fixture was wrong; the code was right.
    puts = [K(945, 2.95, 3.05), K(940, 0.30, 0.40), K(935, 0.10, 0.18)]
    noon = datetime(2026, 9, 4, 12, 0, tzinfo=ET)

    def run(price=947.05, orb=None, ch=None):
        return TrendCreditSpread().prepare(
            None, None, ch or Chain(puts), None, price,
            now_et=noon, orb=orb if orb is not None else Orb())

    p = run()
    check("F1 the trigger is fifty_accepted and the plan reaches a wing",
          p.short is not None and p.long is not None, str(p.structural))
    # 🔴 THE OPERATOR'S EXAMPLE, VERBATIM: sell the 945.
    check("F2 the short is the NEAREST OTM strike from CURRENT PRICE",
          p.short is not None and p.short.strike == 945.0,
          str(p.short and p.short.strike))
    # widest wing clearing 1:1 — 940 gives credit 2.30 on width 5 (R 1.85);
    # 935 gives 2.52 on width 10 (R 0.34, refused). So 940 wins.
    check("F3 the wing is the WIDEST that still clears 1:1, not the best-R one",
          p.long is not None and p.long.strike == 940.0,
          str(p.long and p.long.strike))
    check("F4 R is on the EXPIRY basis and clears 1.00",
          p.r is not None and p.r >= C.TCS_R_FLOOR_EXPIRY, str(p.r))

    # ══ F5 — NO ACCEPTANCE, NO TRADE ══════════════════════════════════════
    p2 = run(orb=Orb(accepted=False))
    check("F5 without fifty_accepted the plan does not reach a strike",
          p2.short is None and not p2.ready)

    # ══ F6 — THE 50 MUST STILL HOLD ═══════════════════════════════════════
    # 🔴 The latch is sticky and the strike follows SPOT, so without this an
    # acceptance at 947 then a collapse to 930 would sell the 925 put into a
    # level price had already retaken.
    p3 = run(price=930.0)
    check("F6 price back through the 50 refuses on holds_fifty",
          not p3.ready and any("holds_fifty" in str(u) for u in p3.unmet),
          str(p3.unmet))

    # ══ F7 — THIN CREDIT FAILS BOTH RULES AT ONCE ═════════════════════════
    # The 1:1 floor and the 15%-of-credit stop PULL THE SAME WAY: a thin
    # far-OTM sale cannot clear 1:1 and its stop cannot clear 2x the quote.
    thin = [K(945, 0.20, 0.30), K(940, 0.05, 0.12)]
    p4 = run(ch=Chain(thin))
    check("F7 a thin sale is refused, and the reason names the rung",
          not p4.ready and bool(p4.structural), str(p4.structural))

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 7 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
