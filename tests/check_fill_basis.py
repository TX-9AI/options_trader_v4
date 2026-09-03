#!/usr/bin/env python3
"""
tests/check_fill_basis.py  v1.3
v1.3  2026-09-03  r234 — RE-DERIVED. F0 asserted "five values" — the
      exact invariant r219 broke by adding a fifth and missing two guard
      returns, which this check could not see because it only drove the
      success path. It now pins the SHAPE, read by name, on the guard path
      too. And the 0.60-wide fixture r219 called "the shape the fleet trades"
      is now REFUSED by the narrow-side bracket, which is r219's own verdict
      ("born at its stop") enforced at selection; F1c pins that refusal and
      names the rung, F1/F1b move to a surviving shape.
v1.2  2026-09-02  r220 — F6/F7: every live entry walks a ladder EXCEPT ORB.
      Credit verticals posted a static limit at `net_credit` and never walked
      it — not exempt, just unwired. ORB's standing offer stays exempt by
      design and F7 guards that carve-out.
v1.1  2026-09-02  r220 — F5 WALKS EVERY STRATEGY'S FILL PATH. r219 fixed the
      prepare layer and TrendCreditSpread undid it at the signal layer:
      `_build_signal` had no credit in scope and recomputed bid/ask three
      hundred lines below the fix. A fix applied at one layer and reversed at
      another looks complete from either end.
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

    # ⚠️ r234 — THE LEGS NARROW FROM 0.60 TO 0.10, AND THAT IS A FINDING, NOT
    # A CONVENIENCE. r219's original fixture was "the shape the fleet trades":
    # a 0.60-wide short and a 0.60-wide long. Under r234's narrow-side bracket
    # that shape is now REFUSED — stop room 0.69 against a 0.60 short spread
    # needs 1.20 to clear `stop_survivable`'s 2x — which is the correct answer
    # and exactly r219's own conclusion ("the position was born at its stop"),
    # now enforced at selection instead of discovered at the exit. F1/F1b are
    # about the CREDIT BASIS, so they use a shape that survives; F1c pins that
    # the wide one is refused, and names which rung did it.
    short = _C(100.0, 1.20, 1.30)
    long_ = _C(105.0, 0.23, 0.33)
    out = search_wing([short, long_], short, "call", 1.0, r_floor_stop=0.0)

    # 🔴 RE-DERIVED AT r234. "Five values" was the invariant precisely because
    # r219 added a fifth and MISSED two guard returns that still returned four
    # — and this check could not see it, because it only ever drove the
    # success path. A NamedTuple makes arity unrepresentable as a bug: F0 now
    # pins that EVERY return path, including the guards, yields the same type
    # read BY NAME.
    check("F0 search_wing returns a WingResult read by name",
          hasattr(out, "credit") and hasattr(out, "fill")
          and hasattr(out, "r_stop"), type(out).__name__)
    _bad = type(short)(0.0, short.ask, getattr(short, "mark", 0.0), short.strike) \
        if False else None
    class _NoBid:
        strike, bid, ask, mark = 100.0, 0.0, 1.10, 1.05
    _g = search_wing([_NoBid(), long_], _NoBid(), "call", 1.0, r_floor_stop=0.0)
    check("F0b the no-bid GUARD returns the same shape, not a short tuple",
          type(_g) is type(out) and _g.long is None and _g.why,
          f"{type(_g).__name__}: {_g.why}")
    if not hasattr(out, "fill"):
        print()
        print("FAILED 1: pre-r219 shape — the fill credit does not exist")
        return 1
    r, wing, judged = out.r, out.long, out.credit
    width, fill = out.width, out.fill
    # F1c — the wide-spread shape r219 measured is now refused AT SELECTION,
    # by the rung that owns the decision rather than by a later gate.
    _ws, _wl = _C(100.0, 1.20, 1.80), _C(105.0, 0.23, 0.83)
    _wide = search_wing([_ws, _wl], _ws, "call", 1.0, r_floor_stop=0.0)
    check("F1c a stop that cannot clear 2x the short spread is refused",
          _wide.long is None and _wide.why_key == "stop_vs_spread",
          f"{_wide.why_key}: {_wide.why}")

    # ── F1 — THE TWO CREDITS ARE DIFFERENT AND BOTH ARE RETURNED ────────
    check("F1 the booked (mark) credit differs from the judged (bid/ask) one",
          # r234 — the narrower fixture: judged 1.20-0.33 = 0.87 (bid/ask),
          # booked 1.25-0.28 = 0.97 (mark). The GAP is unchanged in meaning,
          # only in size: still exactly the two half-spreads.
          fill is not None and abs(fill - 0.97) < 1e-9
          and abs(judged - 0.87) < 1e-9,
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
    # r234 — by NAME, so a future field can never break this line again.
    fill2 = search_wing([short, nm], short, "call", 1.0, r_floor_stop=0.0).fill
    check("F3 a leg without a usable mark returns NO fill credit",
          fill2 is None, str(fill2))

    # ── F4 — NaN IS NOT A MARK ──────────────────────────────────────────
    # ⚠️ safe_float, not float(): every comparison against NaN is False, so a
    # bare conversion would let it through and book a NaN entry premium.
    nan = _C(105.0, 0.23, 0.83)
    nan.mark = float("nan")
    fill3 = search_wing([short, nan], short, "call", 1.0, r_floor_stop=0.0).fill
    check("F4 a NaN mark is not booked as a price", fill3 is None, str(fill3))

    # ── F5 — EVERY FILL PATH BOOKS THE MARK ─────────────────────────────
    # 🔴 r219 FIXED THE PREPARE LAYER AND TCS UNDID IT AT THE SIGNAL LAYER.
    # `_build_signal` had no credit in scope, so it recomputed
    # `short.bid - long.ask` three hundred lines below the fix — and
    # `main.py:2220` hands that to `paper_fill_credit`, whose parameter is
    # named `mark`. A fix applied at one layer and reversed at another looks
    # complete from either end; only walking EVERY strategy's fill path finds
    # it. This check is that walk, kept.
    # ⚠️ SOURCE-LEVEL ON PURPOSE. Constructing six live signals needs six sets
    # of chain, trend and market-state fixtures; the claim here is narrow —
    # no strategy computes its booked price from bid/ask — and that is exactly
    # what the source shows.
    # ⚠️ LINE BY LINE, NO REGEX WITH ESCAPES. Two attempts at this check died
    # on a backslash-n collapsing a level inside a generator — the same trap
    # that broke a shell command earlier today. Iterating lines needs no
    # escapes at all, so there is nothing to get wrong.
    paths = ("orb_strategy.py", "runaway_continuation.py",
             "gex_pin_butterfly.py", "sweep_credit_spread.py",
             "trend_credit_spread.py")
    bad = []
    for fn in paths:
        src = open(os.path.join(_root, "strategy", fn), encoding="utf-8")
        for ln in src.read().splitlines():
            t = ln.strip()
            if t.startswith("#"):
                continue
            if ("net_credit" in t or "entry_premium" in t) and "=" in t \
                    and ".bid" in t and ".ask" in t:
                bad.append(f"{fn}: {t[:56]}")
    check("F5 no strategy books its entry from bid/ask", not bad, "; ".join(bad))

    # ⚠️ AND THE HURDLE MUST STILL USE IT — if bid/ask vanished from
    # credit_vertical entirely, the conservative R test would have gone with it.
    cvsrc = open(os.path.join(_root, "strategy", "credit_vertical.py"),
                 encoding="utf-8").read()
    check("F5b the R hurdle still prices on bid/ask",
          "credit = max(0.0, bid - ask)" in cvsrc)

    # ── F6 — EVERY LIVE ENTRY WALKS A LADDER, EXCEPT ORB ────────────────
    # 🔴 CREDIT VERTICALS POSTED A STATIC LIMIT AND NEVER WALKED IT. Both
    # entry_engine paths price through `_walk_price` -> `ladder_registry`, and
    # ORB is exempt BY DESIGN — `_place_standing_offer`: "ORB only: ONE limit
    # at the mark, posted once, left to rest." The credit verticals were not
    # exempt, just unwired, so a spread that did not fill at `net_credit` sat
    # there instead of conceding.
    # ⚠️ OPERATOR, 2026-09-02: "everything but ORB using ladder entries", and
    # the walk for a credit spread runs FROM THE TOP — best credit first,
    # conceding toward mark, which is where the ladder's own "never posts worse
    # than mark" rule stops it.
    mainsrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    check("F6 the credit-vertical live order prices through the ladder",
          "_lr.price_for(_lkey" in mainsrc and '"sell"' in mainsrc)

    # 🔑 A LADDER THAT NEVER ADVANCES IS THE STATIC LIMIT WITH A NEW NAME.
    # `refuse` on a non-fill, `clear` on a complete fill — and NOT on a
    # partial, because the remainder is still an open intent.
    check("F6b a non-fill advances the walk and a full fill ends it",
          "_lr.refuse(_lkey" in mainsrc and "_lr.clear(_lkey)" in mainsrc
          and "fill.quantity >= _req_contracts" in mainsrc)

    # ⚠️ AND THE STRUCTURE QUOTE IS BUILT PER LEG. `short.ask - long.bid` is
    # the best credit and `short.bid - long.ask` the worst; their midpoint is
    # `short.mid - long.mid`, exactly what paper books — so live and paper
    # share a floor. Building it from the combined mark plus a shade is
    # limit_ladder v1.1's recorded mistake.
    check("F6c the structure quote is built from the four leg quotes",
          "_sa - _lb" in mainsrc and "_sb - _la" in mainsrc)

    # ── F7 — ORB STAYS EXEMPT ───────────────────────────────────────────
    # ⚠️ THE CARVE-OUT IS DELIBERATE AND MUST SURVIVE. A standing offer that
    # walks is not a standing offer.
    eesrc = open(os.path.join(_root, "execution", "entry_engine.py"),
                 encoding="utf-8").read()
    offer = eesrc[eesrc.index("def _place_standing_offer"):]
    offer = offer[:offer.index("def _place_butterfly")]
    # ⚠️ CODE LINES ONLY. The first draft matched the COMMENT that documents
    # the carve-out — "NO `_walk_price`, NO `ladder_registry`" — and went red
    # on the very prose asserting the property it was checking. Same class as
    # the §20 canaries that keep matching changelog text.
    _code = [l for l in offer.splitlines()
             if l.strip() and not l.strip().startswith(("#", '"', "⚠", "🔑", "🔴"))]
    _code = "\n".join(_code)
    check("F7 ORB's standing offer still does NOT walk",
          "self._walk_price(" not in _code and "_lr.price_for(" not in _code,
          "the carve-out is deliberate: a standing offer that walks is not one")

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_fill_basis: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
