# TRADES — the specs

**Every strategy: what it trades, what may be relaxed, and what may never be.**
**Written 2026-08-20. This is the operator-facing document; the code is the
authority and `tests/check_gates.py` enforces the categories mechanically.**

---

## How to read this

Each spec declares its gates in three categories (WA §36):

| category | meaning | relaxable |
|---|---|---|
| **SELECTION** | a measured preference. Loosening gives a *worse example of the same trade* — which is what a debug session wants. | **yes** |
| **FOUNDATIONAL** | defines the setup's **identity**. Relax it and this is not that trade. **A gate can be perfectly winnable and still be foundational.** | never |
| **FEASIBILITY** | the trade cannot win, however good it looks. | never |

⚠️ **The relaxed toggle is `configure.sh` option 7, per box, paper only.** It
exists to get trades *firing* so the sequence can be watched, plumbing errors
surfaced, and the stops exercised on deliberately mediocre entries. Every relaxed
trade carries `relaxed_entry=1` and a `_relaxed` setup suffix. **Data collected
under it must never validate a tight threshold.**

---

## 1. Runaway Continuation — `runaway_continuation.py`

**The ORB ran to its 50% TP and held. Buy the direction that already proved
itself.**

It does not predict a direction; **it observes one already in evidence.** Four
independent searches found no directional predictor in this data — entry
conditions (all ambient), recorded columns (gates or empty), opening bias (a
coin, forward-only, 797 sessions) and the tape harness (every surviving
condition helped UP *and* DOWN). The live book agreed at 44.9%.

**FOUNDATIONAL**
· the ORB reached its 50% TP and **HELD** — a 1m *close* beyond, still on the
  right side at the next tick. **This is the entire premise.**
· direction comes from the ORB state, never from a forecast.
· firing **disarms the retest**: the runaway *is* the evidence price never came
  back for it.

**SELECTION** — cutoff 11:30 → 14:00 relaxed.

**FEASIBILITY** — the ATR floor and the ATR→delta map. Below **0.05% ATR the
required move was reached on 0% of 5,517 measured bars.**

**Strike** — ATR-mapped: 0.20–0.35 delta at ≥0.12% ATR (60% reachable),
0.35–0.50 at ≥0.20% (85%). **ADX is not used and that is a measurement** — every
band from 0-15 to 40-100 produced the same median excursion.

**Exit** — trailing stop. `orb_trail_stop` 96% / 85 trades / **+$30,696**, worst
−$16. `bos_exit` 34% / 217 / **−$7,085** with the largest single loss in the v3
book, so **BOS is not used.**

---

## 2. Sweep Credit Spread — `sweep_credit_spread.py`

**A named pool was swept and rejected. Sell the boundary it just became.**

    sweep UP into a pool, rejected   -> CEILING -> CALL credit spread
    sweep DOWN into a pool, rejected -> FLOOR   -> PUT credit spread

**Credit, not long, and that is the point.** A long reversal needs price to
*travel*: 155 of 190 directionally-**correct** continuation entries — **82%** —
never reached +25% MFE, because a 0.30-0.60 delta 0DTE contract needs a 0.90%
move to pay that after the spread, and the tape delivers it in a specified
direction on 22% of windows. **A credit spread needs the level to hold**, and
two thirds of 90-minute windows produce no 0.5% move at all.

**Short strike** — the **nearest strike price actually pierced**, not the pool.
Further from spot than the boundary: less credit, more room, and the position is
threatened only if price returns to a level it already failed at.

**FOUNDATIONAL**
· the pool is **NAMED**. An unnamed swing high is not a liquidity pool.
· it **RECLAIMED** — a bar *closed* back inside. A wick is a touch, not a
  decision.
· it is **NOT INVALIDATED**. Reclaimed-then-accepted-through is a **breakout**,
  and selling a boundary that already gave way is the worst version of this.
· price is already on the profitable side.

**SELECTION**, all measured on **2,169 sweep events**
· window **13:00–15:00** → 09:45–15:30. *(39% survival vs 26% before 10:30)*
· pierce ceiling **0.25%** → 0.75%. *(33-34% survival vs 19-21% deeper)*
· max age **6 bars** → 18, measured from the **reclaim**.

⚠️ **A DEEP PIERCE MEANS A WEAK LEVEL, NOT A STRONG REJECTION** — 1.28% median
adverse against 0.46%. Price went that far because it was willing to.

**FEASIBILITY** — ATR ≤ 0.20%. Above it the tape produced a 0.5% move on **92%
of 90-bar windows**; a boundary does not hold in that.

**Exit — exactly two.** 15% stop, and the 15:45 hard close. **No trail, no
profit target**, exempt from the 15:40 flatten ladder as a credit vertical.

---

## 3. GEX Pin Butterfly — `gex_pin_butterfly.py` ⏸ PARKED

**Apex on the gamma pin, out of the money. Buy the move to the magnet.**

⚠️ **PARKED until real open interest accumulates (~2 weeks from 2026-08-19).**
`open_interest` was a declared field with **no producer**, so GEX has been
`~100,000 × gamma² × spot` — a gamma-squared surface, not dealer positioning.
The "pin" therefore always sat at spot, and swung 12.4M → 0.1M → 2.0M in three
minutes.

**THE ASYMMETRY IS THE TRADE.** Apex payoff is fixed at the wing width while the
**debit collapses as the apex moves OTM.** A pin at 90% of the expected move
costs a fraction of one at 20% and pays the same. **Distance is the edge.**

**FOUNDATIONAL** — `PINNING`; the apex sits **on** the pin; the pin is **OTM**.

**SELECTION** — pin concentration 0.25 (⚠️ *relaxed with reluctance*: far out,
the trade **relies** on the magnet pulling, so a weak pin far away is the worst
cell in the matrix); window; EM ceiling 1.00 → 1.30.

**FEASIBILITY** — no ATM IV means **no trade**, not a fallback; and the EM floor
at 0.30, because nearer than that the asymmetry — the whole reason for the
structure — is gone.

**Expected move comes from the chain's ATM IV**, not VIX. v3 applied SPX 30-day
implied vol to every symbol on a 0DTE horizon.

⚠️ **RARE BY DESIGN — an opportunity-cost question, not a defect.** It needs a
strong pin far from spot, most likely near monthly expiration when real
positioning sits at a strike. **It costs nothing while it waits**: no position
slot, no capital, no competition. Its evidence will be **structural, not
statistical** — the test is *"when it fires, does the payoff justify keeping
it?"*, answerable on a small sample in a way a win rate is not.

---

## 4. Opening Range Breakout — `orb_strategy.py`

**The one strategy with a positive record, and the reason is in the spec: it
never asked permission.**

`orb_trail_stop` — **96% win / 85 trades / +$30,696, worst −$16.** ORB
consulted no regime label, so it kept working while every gated strategy
degraded on a classifier picking the wrong side 55% of the time. Operator:
*"every day where P&L was green or very green is nearly entirely based on the
ORB trade and the quality of our stops."*

**Trigger** — the opening range breaks and **retests**, confirmed by 1m
body/wick rules. Self-validating geometry.
**Direction** — from which side broke. Not forecast.
**Targets** — `tp50` and the 100% range extension.
**Exit** — `MAX_LOSS_PCT` at entry, then the trailing stop. **No BOS** —
`bos_exit` measured 34% / 217 trades / **−$7,085** with the largest single loss
in the v3 book.

**FOUNDATIONAL** — the break AND the retest. A break alone is not the setup.
**SELECTION** — the confluence notes (named level in the break, VWAP alignment,
clear liquidity path) describe the setup; **none of them gate it.**
**FEASIBILITY** — the range must exist. `_opening_range` reads today's 09:30
bar, after TCS.3 found the 60-bar 1m frame no longer reached it by 10:35.

⚠️ **v4.0 MADE IT PURELY MECHANICAL.** Three vestigial reads went: the regime
label stamped onto the signal, a confluence note for regime agreement that could
never fire, and `signal.conviction += regime.conviction * 0.7`. All were inert —
`regime.conviction` is permanently 0.0 — **but a dead branch reads as a live one
to anyone auditing the file.** The remaining conviction additions are structural
facts (a named level in the break, a Fed day); they describe the setup and do not
authorise it.

---

## 5. Iron Condor — `iron_condor_strategy.py` + `condor_roll.py`

**The most intricate spec in the book, and the one where the overlay and the
structure agree on when the thesis died.**

### The anchor — the daily pitchfork

Operator, verbatim: *"It's a guardrail, not the road."* → **daily fork only.**
*"Consider the condor off the table if we don't have guardrails."* →
**NO FORK, NO PLAN.**

Short **call** rides the **upper rail**, short **put** the **lower rail**.

### Leg order falls out of the slope

**The slope predicts which rail ranging or condensing price taps first.**
An **up-sloping** fork means price travels lower rail → upper rail across the
session, so it reaches the **lower** rail first and the **PUT** side fills
first. A **down-sloping** fork mirrors it: upper rail first, **CALL** first.

⚠️ **This is a claim about the PATH THROUGH THE SESSION, not about where price
is now** — which is also why leg 2 *queues* rather than fires: you are waiting
for the traversal the slope told you to expect.

### Strike selection

*"The short strike should be just outside the range of the rail at the MOST
LIQUID strike WHERE PRICE HAS STILL NOT EXCEEDED."*

· **not-exceeded** — a strike price has already traded through today is one the
  market has **proven it can reach**.
· **most liquid keys on BID/ASK WIDTH.** The old `liq()` summed OI + volume and
  a factor sweep found **both constant across the whole sample**, so "most
  liquid" had silently resolved to "nearest the floor". Width is populated, and
  on a 0DTE credit spread a nickel-wide quote is what trips a stop on noise.
· **`0.80 × EM` minimum distance** survives as a floor: a rail sitting on top of
  spot must not produce a strike with no breathing room.

### Legging

Leg 1 fires on approach to the first side's short. Leg 2 queues after leg 1
**fills**, and fires on approach to the opposite short. **If leg 2 never fires,
leg 1 stands alone as a vertical and manages identically.** A filled leg is
**never** cancelled.

### The roll — integral, not an add-on

One side gets tested → close the **untested** vertical, re-open it closer, and
collect fresh credit. When

    total_credit_collected  >=  tested_side_width

**the tested side can no longer lose** and the structure is a broken-wing
butterfly. The search takes the **smallest** roll that achieves it — least new
risk assumed.

⚠️ **THE ROLL IS THE PRIMARY RISK RESPONSE TO A TESTED SIDE and should be
attempted before a stop is taken.** A silent refusal to roll is the most
consequential of all the silent declines, which is why v1.1 made it name the leg
that had no mark.

### Gates

**FOUNDATIONAL**
· a **daily fork exists**. No fork, no plan — there is no anchor, no leg order,
  and no expected path.
· short strikes sit **outside the rails**.
· the strike has **not been exceeded** today.
· leg 2 requires leg 1 **filled**.

**SELECTION** — the approach distance, the entry window, the wing width.

**FEASIBILITY** — the `0.80 × EM` floor, and no liquid strike beyond it.

⚠️ **THE `RANGING` GATE IS REPLACED BY FORK INVALIDATION.** v3 cancelled a
pending leg when the regime flipped away from RANGING — and that label is
exactly what v4 removed for picking the wrong side 55% of the time. The fork
already provides the structural equivalent, and the operator's own accepted risk
says the two are the same event: *"If it gets breached, then our fork may also
become invalid & I can live with that, because we are accepting that risk for an
asymmetric payoff if it holds."* **The structure and the overlay agree on when
the thesis died instead of arguing about it.**

### Exits — a management LADDER, not a stop

**No take-profit, no trail, no BOS, ever.** Measured: on 18 standalone legs a
TP@25% turned −$242.77 into −$8.43, and **on 28 condor legs a TP was worse at
every level.** A credit vertical is *earning* from decay; closing it early buys
back the theta it was opened to collect. The nickel close ($0.05) is always
available — that is a win, not an abandonment.

**BEFORE LEG 2 FILLS — leg 1 manages exactly like the sweep credit spread: a
15% stop.**

⚠️ **THE GEOMETRY IS WHY.** The traverse that completes the condor is the same
move that makes leg 1 profitable: an up-sloping fork fills the put at the lower
rail, and price must then travel *up* toward the upper rail to trigger leg 2 —
moving the short put spread *away* from its short strike the whole way. **So a
leg 1 that is losing is a leg 1 whose condor will never form.** Waiting out a
25% loss on it is not protecting a condor thesis; the thesis is already dead and
what remains is an unhedged vertical being held in hope.
· `condor_stop` measured 16 trades, 19% win, −$1,156, worst −$300. The 25% was
  never validated, and it was calibrated for a *complete structure collecting
  credit on both sides* — not for one naked leg.
· **The stop widens only when there is offsetting credit to justify it.** That
  is the honest reason a wider stop is ever acceptable.
· Fewer condors will complete. **That is the point, not the cost** — the ones
  declined are the ones whose traverse already failed.

**ONCE FORMED — the roll has FIRST RIGHT OF REFUSAL, and there is no competing
percentage stop.**

A stop on a formed condor is close to incoherent: it pays to exit a position the
roll could have made **risk-free**. The ladder, in order, and **each rung states
what is behind it**:

**1. ROLL TO RISK-FREE — arithmetic.**
Close the untested vertical, re-open it closer, collect fresh credit. When
`total_credit_collected >= tested_side_width` the tested side **cannot lose**.
Smallest qualifying roll wins — least new risk assumed. *Provable.*

**2. INVERT TO A BUTTERFLY — the operator's experience.**
If no roll clears the width, roll the untested side **all the way adjacent to
the tested short**: shared body, which *is* a butterfly. That is the maximum
credit a roll can produce when risk-free is out of reach.
⚠️ **It also converts the thesis honestly.** The condor said *"price stays
between the rails"* — dead, one rail is being tested. The butterfly says
*"price is here now, and I take max profit if it stays."* You trade the position
you actually have rather than the one you opened.
⚠️ **PROVENANCE, STATED: no v3 trade ever did this. It is discretionary
practice, not a measured rule** — sound mechanically, with no sample behind it.
It ships as a documented rung and is **instrumented rather than trusted**: every
inversion journals what the roll search rejected and why, the credit at
inversion, and what the position did afterward. A rare adjustment will never be
validated statistically, so **the evidence has to be a legible record of each
individual case** — the same footing as the GEX butterfly.
⚠️ **AND THE FORMERLY-UNTESTED SIDE BECOMES EXPOSED.** It was rolled to where
price is. A hard reversal now loses on that side too — capped by the wings,
which is exactly why this is acceptable where a naked roll would not be.
**EXIT THE INVERTED BUTTERFLY IF IT BLEEDS 25% OF TOTAL PREMIUM COLLECTED** —
measured against the *cumulative* credit (original condor + every roll), because
after inversion the position is one structure, not two legs.

**3. STOP AND PAGE — the fallback, and the page is the point.**
Reaching this means **both risk-reduction steps were unavailable**: no roll
cleared the width and no inversion was possible — an expensive buy-back, no
liquid strike, a gapped chain. ⚠️ `condor_roll` v1.1 exists because a missing
mark caused a **silent** refusal, and *"the roll IS the risk-reduction step, so
a quiet refusal is the most consequential of the three silent declines."*
**A roll declining is information wanted in the moment, not at EOD.**

**And 15:45 applies throughout** — both legs are credit verticals, exempt from
the 15:40 flatten ladder.

---

## Not specced, deliberately

**`continuation_strategy`** — inert. The runaway handoff already *is* the
trend-participation trade, and it observes a move in evidence where this one had
to forecast persistence. Kept as a shell in case a case arises the runaway does
not cover.

**`trend_credit_spread` (TC.6)** — inert, and the record supports it: 21 trades,
28.6% direction accuracy. **The sweep spread sells a boundary that proved
itself; the ORB edge has proven nothing except that the first fifteen minutes
had a high and a low.** It is also redundant against the runaway — one trades
the ORB *breaking and holding*, the other the ORB *holding*. Between them they
cover every outcome, which is not coverage.

### DELETED 2026-08-20 — superseded, not shelved

`butterfly_strategy.py`, `continuation_strategy.py` and
`sweep_reversal_strategy.py` are **gone from the repo**, along with their imports
and dispatch blocks in `main.py`.

⚠️ **They were briefly carried as "inert shells" exempt from
`tests/check_no_regime.py`, and that was wrong.** They were not future work —
they were the v3 implementations the new specs replace, and **a permanent
exemption for superseded code is a growing blind spot an audit will ask about.**
All three were gated on `regime.primary_regime`, which v4 leaves permanently
UNKNOWN, so they were dead code that still had to be read and reasoned about.

Git has them. The replacements are sections 1, 2 and 3 above.
