"""
execution/entry_ladder.py  v4.0
The entry ladder: start 25% in from the best price, step ONE VENUE INCREMENT
toward mark, never worse than mark, and never re-offer a refused price.

v4.0  2026-08-20  Built at the OTV4 split. Operator's spec, read back and
confirmed.

INHERITED DOCTRINE
MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
WORKING_AGREEMENT 32 requires this block be read before the file is edited.

════════════════════════════════════════════════════════════════════════════
WHY FILL QUALITY OUTRANKS EVERY SELECTION LEVER
════════════════════════════════════════════════════════════════════════════
FRC.1 measured the fleet's gross edge at **+$2.70/trade against $126/trade of
round-trip friction - about 2% of the spread it trades in.** Capturing half the
half-spread on entry is worth on the order of **$31/trade**. **Fill quality is
an order of magnitude larger than anything on the trade-selection list**, and
this file is where it is captured or given away.

════════════════════════════════════════════════════════════════════════════
THE SPEC, IN THE OPERATOR'S OWN EXAMPLES
════════════════════════════════════════════════════════════════════════════
Spread 1.00 (bid 0.00 / ask 1.00, mark 0.50), SELLING:
  · $0.05 increments -> start .75, then .70 .65 .60 .55 .50   (six rungs)
  · $0.10 increments -> start .70, then .60 .50               (three rungs)

**Granularity falls out of the venue increment, not a fraction list.** A tighter
grid gives more rungs and more chances at a better fill. The v3 ladder used a
FIXED `[0.50, 0.25, 0.00]` and could not express that: on a dime grid it posted
three prices whether or not more were available, and on a penny grid it skipped
dozens of postable levels between them.

⚠️ 25% AND NOT 50%. Operator: *"always start at 25% of best price to not waste a
lot of time on hopeless attempts."* The half-spread opener spent a fill window
on a price the book was never going to take.

⚠️ .75 -> .70 ON A DIME GRID ROUNDS **TOWARD MARK**, deliberately. v3's
`round_to_increment` rounded a sell UP - away from mark - reasoning that
nearest-rounding would make half the rungs more aggressive than specified. That
is the right instinct for a rung you intend to hold, and the wrong one for an
OPENING rung whose entire purpose is to be plausible. Rounding away from mark
recreates the hopeless attempt the 25% start exists to avoid.

════════════════════════════════════════════════════════════════════════════
THE THREE RULES, AND THEY COMPOSE IN THIS ORDER
════════════════════════════════════════════════════════════════════════════
1. **RATCHET.** The rung index only ever advances. Operator: *"If it's not
   accepting 80 at the first attempt, it won't accept 80 at the next attempt as
   price fluctuates - 80 is off the table."* A refused price never returns, even
   if the market moves back through it.

   ⚠️ THIS IS THE RULE v3 DID NOT HAVE. `entry_ladder_prices` recomputed every
   rung from the LIVE quote each cycle, so a mark that drifted up could place
   rung 2 at or above rung 1 - re-offering a level already refused and burning
   the fill window on it.

2. **REPRICE.** Each attempt recomputes from the CURRENT mark, not the
   entry-time one. A ladder anchored to a stale mark chases a market that has
   already left.

3. **MARK FLOOR - never post worse than mark.** Operator: *"If Mark ever turns
   out to be better than our first offer or subsequent offers, take Mark."*
   Selling posts `max(rung, mark)`; buying posts `min(rung, mark)`.

   ⚠️ THIS RESOLVES THE CONFLICT BETWEEN 1 AND 2. If the mark rises past the
   last refusal, the ratchet alone would hold the order BELOW mark - posting
   worse than the market is offering. The floor takes mark instead, which is the
   terminal rung anyway, so the ladder simply arrives there early. **On a market
   moving in your favour this collapses to mark and fills. That is correct: the
   rungs only ever existed to try for BETTER than mark.**

⚠️ AND IT APPLIES TO EVERY ORDER - debits and credits alike, every strategy.
Not a per-strategy option.
"""

import logging
import math
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

START_FRACTION = 0.25          # 25% in from the best price
MAX_RUNGS = 24                 # a penny grid on a wide quote could go forever


def _increment(symbol: str, price: float, bid: float, ask: float) -> float:
    """The venue's increment. Resolved from the quote where possible.

    ⚠️ THE QUOTE IS BETTER EVIDENCE THAN THE HARDCODED LIST. `tick_size.resolve`
    prefers a venue rule, then PROVES penny eligibility from the observed book,
    and only then falls back to `PENNY_CLASSES` - which FRC.2's own notes call
    "a STARTING list ... unverified - membership is a broker/OCC fact, not
    derivable here", and whose own log calls it the path that should not be
    reached.
    """
    try:
        from execution.tick_size import resolve
        inc, _src = resolve(symbol, price, bid, ask)
        return float(inc) if inc and inc > 0 else 0.05
    except Exception:                                          # noqa: BLE001
        return 0.05


def _snap_toward_mark(px: float, mark: float, inc: float) -> float:
    """Round to the venue grid, TOWARD mark. See the header on why."""
    if inc <= 0:
        return round(px, 2)
    if px > mark:
        return math.floor(px / inc + 1e-9) * inc      # a sell rung: come down
    if px < mark:
        return math.ceil(px / inc - 1e-9) * inc       # a buy rung: come up
    return round(mark / inc) * inc


def rungs(bid: float, ask: float, side: str, symbol: str = "") -> list:
    """Every price this ladder will post, in order, ending at mark.

    Returns [] on an unusable quote - crossed, zero or missing. **An empty
    ladder means the caller posts at mark**, never at a guess.
    """
    # ⚠️ float() ACCEPTS NaN AND inf. The stress test crashed here with
    # "cannot convert float NaN to integer" inside the snap - a raise that
    # `_safe_strategy` would have logged as "no signal", hiding it entirely.
    from utils.math_utils import safe_float
    b, a = safe_float(bid), safe_float(ask)
    if b is None or a is None or b <= 0 or a <= 0 or a < b:
        return []

    mark = (a + b) / 2.0
    spread = a - b
    if spread <= 0:
        return [round(mark, 4)]

    inc = _increment(symbol, mark, b, a)
    sell = str(side).lower().startswith("s")

    # 25% in from the BEST price - the ask when selling, the bid when buying
    start = (a - spread * START_FRACTION) if sell else (b + spread * START_FRACTION)
    start = _snap_toward_mark(start, mark, inc)

    out, px = [], start
    for _ in range(MAX_RUNGS):
        # ⚠️ NEVER PAST MARK. Mark is the terminal rung, not a waypoint.
        if (sell and px <= mark) or ((not sell) and px >= mark):
            break
        r = round(px, 4)
        if r not in out:
            out.append(r)
        px = px - inc if sell else px + inc

    m = round(_snap_toward_mark(mark, mark, inc), 4)
    if m not in out:
        out.append(m)
    return out


class LadderState:
    """One order's walk down the ladder. Carries the ratchet.

    ⚠️ STATE IS THE POINT. A stateless ladder recomputed from the live quote
    re-offers refused prices when the mark drifts - which is exactly what v3
    did, and why a refusal cost more than one fill window.
    """

    def __init__(self, side: str, symbol: str = ""):
        self.side = str(side).lower()
        self.symbol = symbol
        self.rung = 0
        self.best_refused: Optional[float] = None

    def next_price(self, bid: float, ask: float) -> Optional[Tuple[float, str]]:
        """(price, why) for the next attempt, or None when the quote is unusable.

        Call once per attempt. Advancing the rung is `refuse()`'s job, so a
        caller that re-reads the price without refusing gets the same rung -
        repricing to the current mark, which is rule 2.
        """
        table = rungs(bid, ask, self.side, self.symbol)
        if not table:
            return None
        sell = self.side.startswith("s")
        mark = (float(ask) + float(bid)) / 2.0

        idx = min(self.rung, len(table) - 1)
        px = table[idx]
        why = f"rung {idx + 1}/{len(table)}"

        # ── rule 1: the ratchet. A refused price never returns. ─────────────
        if self.best_refused is not None:
            inc = _increment(self.symbol, mark, bid, ask)
            if sell and px >= self.best_refused - 1e-9:
                px = self.best_refused - inc
                why += " (ratcheted below a refusal)"
            elif (not sell) and px <= self.best_refused + 1e-9:
                px = self.best_refused + inc
                why += " (ratcheted above a refusal)"

        # ── rule 3: never worse than mark. If mark is better, TAKE MARK. ────
        if sell and px < mark:
            px, why = mark, "mark (better than the rung)"
        elif (not sell) and px > mark:
            px, why = mark, "mark (better than the rung)"

        return round(px, 4), why

    def refuse(self, price: float):
        """Record a refusal and advance. Called when an attempt does not fill."""
        try:
            p = float(price)
        except (TypeError, ValueError):
            return
        sell = self.side.startswith("s")
        if self.best_refused is None:
            self.best_refused = p
        elif sell:
            self.best_refused = min(self.best_refused, p)
        else:
            self.best_refused = max(self.best_refused, p)
        self.rung += 1
