#!/usr/bin/env python3
"""
tests/check_fill_basis.py  v1.0
v1.0  2026-09-02  r219 — THE ENTRY AND THE MARK WERE ON DIFFERENT SIDES OF THE
      QUOTE, AND THE DIFFERENCE WAS BOOKED AS A LOSS AT FILL.

🔴 `credit_vertical.search_wing` priced the credit as `short.BID - long.ASK`,
and that number became `sig.entry_premium` and therefore the position's entry
of record. `position_manager._fetch_current_premium` marks a credit vertical at
`short.MARK - long.MARK`. Two bases. The gap is BOTH HALF-SPREADS, present the
instant the position opens, with no market movement — and for a credit vertical
a higher mark is a LOSS.

🔑 MEASURED, NOT ARGUED. Sweep forensics over 2026-08-25..09-02: 38 of 41 trades
exited on the lone stop, which carries 60.5 cents of room, while price NEVER
reached the short strike on any of 22 measurable trades and closed only 0.63
points toward it. That move implies a spread delta of 0.96, which a 5-wide
cannot carry. The underlying never explained the loss.

⚠️ OPERATOR RULING, 2026-09-02: "I have a ladder for live offers, all paper
needs to fill at mark, period." So the MARK is booked. The bid/ask credit is
kept for the R hurdle — deciding on the conservative number and booking the
mark refuses trades that only clear R when priced optimistically, so the error
runs in the safe direction.

⚠️ AND THE OLD BEHAVIOUR HAD A PASSING TEST. check_plan_prepares S2 asserted
`net_credit == 1.30` — the bid/ask figure — so the suite certified the mismatch
for the life of the strategy. It is re-derived to 1.33, the mark.

Born red at fd84426 (r218), where F1 and F3 fail.
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


class _C:
    def __init__(self, k, bid, ask, mark=None):
        self.strike, self.bid, self.ask = float(k), bid, ask
        self.mark = (bid + ask) / 2.0 if mark is None else mark


def main():
    from strategy.credit_vertical import search_wing

    # a 0.60-wide short and a 0.60-wide long — the shape the fleet trades
    short = _C(100.0, 1.20, 1.80)
    long_ = _C(105.0, 0.23, 0.83)
    out = search_wing([short, long_], short, "call", 1.0)

    check("F0 search_wing returns five values", len(out) == 5, str(len(out)))
    if len(out) != 5:
        print()
        print("FAILED 1: pre-r219 signature — the fill credit does not exist")
        return 1
    r, wing, judged, width, fill = out

    # ── F1 — THE TWO CREDITS ARE DIFFERENT AND BOTH ARE RETURNED ────────
    check("F1 the booked (mark) credit differs from the judged (bid/ask) one",
          fill is not None and abs(fill - 0.97) < 1e-9
          and abs(judged - 0.37) < 1e-9,
          f"judged {judged} / booked {fill}")

    # 🔑 THE GAP IS EXACTLY BOTH HALF-SPREADS. That is the quantity that was
    # being charged as a loss at fill, and it is the same order as the stop's
    # 60.5 cents of room — the position was born at its stop.
    gap = (fill or 0) - judged
    half = ((short.ask - short.bid) + (long_.ask - long_.bid)) / 2.0
    check("F1b and the gap is exactly the sum of the two half-spreads",
          abs(gap - half) < 1e-9, f"gap {gap:.2f} vs half-spreads {half:.2f}")

    # ── F2 — R IS STILL JUDGED ON BID/ASK ───────────────────────────────
    # ⚠️ IF R MOVED TO THE MARK the hurdle would pass trades that only clear
    # it when priced optimistically. The conservative test is the point.
    # ⚠️ TOLERANCE MATCHED TO THE RETURN, WHICH IS ROUNDED TO 4dp. The first
    # draft used 1e-6 and failed on a 1.4e-5 rounding residual — a check that
    # fails for arithmetic reasons rather than behavioural ones teaches nobody
    # anything and gets suppressed next time it goes red.
    r_judged = judged / (width - judged)
    r_booked = (fill or 0) / (width - (fill or 0))
    check("F2 R is computed from the judged credit, not the booked one",
          abs(r - r_judged) < 5e-5 and abs(r - r_booked) > 1e-3,
          f"R {r:.4f}; judged-basis {r_judged:.4f}, booked-basis {r_booked:.4f}")

    # ── F3 — A LEG WITH NO MARK YIELDS NO FILL PRICE ────────────────────
    # 🔴 SUBSTITUTING THE BID/ASK NUMBER HERE IS THE ORIGINAL DEFECT. Unknown
    # and "use the other basis" are different facts; the callers refuse.
    nm = _C(105.0, 0.23, 0.83)
    nm.mark = None
    _r2, _w2, _j2, _wd2, fill2 = search_wing([short, nm], short, "call", 1.0)
    check("F3 a leg without a usable mark returns NO fill credit",
          fill2 is None, str(fill2))

    # ── F4 — NaN IS NOT A MARK ──────────────────────────────────────────
    # ⚠️ safe_float, not float(): every comparison against NaN is False, so a
    # bare conversion would let it through and book a NaN entry premium.
    nan = _C(105.0, 0.23, 0.83)
    nan.mark = float("nan")
    *_x, fill3 = search_wing([short, nan], short, "call", 1.0)
    check("F4 a NaN mark is not booked as a price", fill3 is None, str(fill3))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_fill_basis: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
