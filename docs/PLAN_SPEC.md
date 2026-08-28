# PLAN_SPEC.md — every strategy declares its intent BEFORE the trigger

**v1.15 · 2026-08-28 · r174 — the teenie lesson: floor-clears-spread; one runaway per break (§20).**
**v1.14 · 2026-08-28 · r170 — the readers (§19).**
**v1.13 · 2026-08-27 · r169 — the butterfly rides to the close (§18); the exit map, complete.**
**v1.12 · 2026-08-27 · r168 — the runaway's 20% floor; the structure stop is ORB's (§17).**
**v1.11 · 2026-08-27 · r167 — managed exits: the plan decides (§16).**
**v1.10 · 2026-08-27 · r166 — the management plan (§15).**
**v1.9 · 2026-08-27 · r165 — the runaway: gamma leverage over the run (§14). The inversion is complete.**
**v1.8 · 2026-08-27 · r164 — TCS in the §10 shape (§13).**
**v1.7 · 2026-08-27 · r163 — a tine is a moving liquidity level; a touch is its event (§12).**
**v1.6 · 2026-08-27 · r161 — the butterfly earns its entry (§11).**
**v1.5 · 2026-08-27 · r160 — the plan is anticipatory, the strategy confirmatory; the condor authorizes and manages. §10 supersedes §8 where they differ.**
**v1.3 · 2026-08-26 · r147 — leg two and the butterfly, §9.**
**v1.2 · 2026-08-26 · r146 — AS BUILT. See §8 before reading anything below.**
**v1.0 · 2026-08-25 · FIRST PASS, EXPLICITLY UNFITTED.**
Operator: *"every strategy SPEC now needs a plan — use your best judgement on the
1st pass. We will fit later. Allow for relaxed and tight entry conditions."*

Every number in this document that is not read from an existing constant is a
**STATED PRIOR**, not a measurement. They are marked `⟨PRIOR⟩`. Nothing here is
validated against a tape.

---

## 0. WHY — the failure this exists to end

**2026-08-25, TSLA.** Price ran 351.4 → 356.86 between roughly 11:35 and 13:00
ET. Verified from `strategy_note`: `TrendCreditSpread` evaluated 182 times in
that window and produced one signal; `TrendCS2nd` signalled on 207 of 218 looks
and traded nothing. Verified from `main.py`: **only `ORBStrategy` ever calls
`open_plan`.** The PLANS panel on that box therefore showed six ORB rows, all
`EXPIRED / left_confirmed_state`, the newest at 10:38 — and nothing whatsoever
about the largest directional move of the session.

Operator: *"Right now it's looking like nothing was watching it & that's where
my aggravation lies."*

The old engine's flaw, in his words: *"it was watching EVERYTHING, the flaw was
that it was circular logic, making it regressive and late."* A score computed
per tick from data that already contains the move can only ever report the move
after it happens.

---

## 1. THE GOVERNING RULE

> **Evidence decides whether a plan is WRITTEN.
> Price decides whether it FIRES.**

The instant a score, label, or conviction is consulted at fire time, the loop is
back. A plan's trigger is a **number fixed at declaration** and compared against
the tape. Nothing more.

**The anchor test — apply to every plan input:**
*Would this number be the same if I asked ten minutes from now, absent a
structural event?*

| Admissible anchors (fixed) | Inadmissible (re-derived) |
|---|---|
| ORB high / low | a rolling N-bar high |
| named levels (`levels` store) | "current support" |
| pitchfork rails at a stamped index | a rail re-projected each tick |
| session high / low | a moving average |
| GEX pin | ADX / conviction / any score |
| prior-day high / low / close | anything with `_now` in its name |

Scores may appear ONLY in `justification` — the frozen evidence vector — and in
the decision to declare. Never in the trigger.

---

## 2. THE PLAN RECORD

`derived/plan_ledger.py` already carries `trigger_price`, the four strike
fields, `underlying_at_decision`, `expected_move`, and `justification`
(the frozen vector: price, adx, atm_iv, expected_move_iv, VRP, realised vol,
charm, vanna, gex, session fraction, levels, fork rails).

**FIELDS TO ADD:**

| field | why |
|---|---|
| `invalidation_price` | the plan's own death line. Today the exit re-derives it. |
| `expires_ts` | a plan with no expiry is a standing order nobody placed. |
| `mode` | `tight` \| `relaxed` — see §5. Keeps the populations separable forever. |
| `distance_to_trigger` | updated on transition only, never per tick. Makes "how close did we get" answerable. |
| `arm_reason` | one line: what structure justified declaring. |

**STATES:** `DECLARED → ARMED → TRIGGERED → FILLED` with terminal
`EXPIRED` / `INVALIDATED` / `SUPERSEDED` / `WIPED_BY_RESTART`.

`DECLARED` = structure exists, evidence gathered, trigger set.
`ARMED` = still valid, still inside its window, trigger not yet crossed.
The split matters because a plan can be declared and then fall out of its
window without ever being wrong.

---

## 3. THE INVERSION — what each strategy asks per tick

Not *"is this a breakout?"* but ***"what price, from here, would constitute
one — and what would I sell or buy when it comes?"***

Each strategy gains one method:

```
declare_plan(ctx) -> Plan | None
```

It runs on ticks where **no plan of its type stands**. It answers the forward
question, prices the contract, stamps the evidence, and returns. Once a plan
stands, the tick loop does one thing: compare price to `trigger_price`.

---

## 4. THE PLANS, ONE PER STRATEGY

Each carries: **trigger** (fixed price), **invalidation** (fixed price),
**instrument** (pre-selected contract), **window**, **declare-when**.

### 4.1 ORB — `ORBStrategy` — 🔴 **LEAVE IT ALONE**
Operator, 2026-08-25: *"leave orb alone. That one can't get encumbered with
extra hurdles & it already pretty much plans."*
**NO CHANGES. ORB IS THE MODEL, NOT A CANDIDATE.** It already declares a range
at 09:35, fixes a trigger, names an invalidation, and fires on a price
comparison — which is exactly why it has never been late, and why every other
plan in this document is written in its shape. It opens plans today
(`main.py` 1291/1353) and those calls stand unchanged.
⚠️ The temptation to "formalise" it into the new interface is the hurdle he is
refusing. A working thing does not get rewritten to match a document.
Strike selection is a **later, separate** fine-tune and is out of scope here.

### 4.2 RUNAWAY CONTINUATION — `RunawayContinuation` (DEBIT)
- **declare when** ORB has broken and gone `runaway` (no retest)
- **trigger** ⟨PRIOR⟩ close beyond `orb_break_price + 0.25 × ATR` — the
  continuation confirming, not the break itself
- **invalidation** close back below the ORB boundary
- **instrument** the staged call/put at `CONT_TARGET_DELTA`
- **window** break → `DEBIT_DIRECTIONAL_CUTOFF_ET` (11:30)

### 4.3 TREND PARTICIPATION — `TrendCreditSpread` (CREDIT)
**This is the one that failed on 2026-08-25 and the changes are the point.**
- **declare when** 11:31, ORB range known, trend vote directional
- **trigger** close beyond the ORB boundary (`orb_high` for a PCS)
- **invalidation** close back through that boundary
- **instrument** — 🔴 **CHANGED. THE STRIKE MUST BE ABLE TO FOLLOW THE MOVE.**
  Today `_inside[-1]` pins the short strike inside the opening range for the
  whole session, so as price advances the strike goes deeper OTM, the credit
  collapses, and the trade refuses *the harder it rips.* Verified in source at
  `strategy/trend_credit_spread.py` lines 341-352 and confirmed by the two
  fires being the only two moments price sat near the boundary.
  **NEW RULE: the floor is re-anchored per plan, not per session.**
  A plan declares its short strike as the first strike at or below
  `max(orb_high, session_low_since_break)` ⟨PRIOR⟩ — so a second plan declared
  at 12:30 sits under the 12:30 structure, while the FIRST plan keeps the strike
  it was born with. Plans do not move; new plans get new strikes.
- **window** `TCS_START_ET` (11:31) → `TCS_ENTRY_END_ET` (14:00)
- **re-declaration** ⟨PRIOR⟩ a new plan may be declared when price has advanced
  ≥ 0.5 × ATR beyond the last plan's trigger. This is what "participate in a
  move that keeps going" requires, and it is bounded so it cannot become the
  CVX loop.

### 4.4 SWEEP CREDIT SPREAD — `SweepCreditSpread`
🔴 Carries the 2026-08-25 CVX finding, still open and NOT yet built.
- **declare when** a named level is pierced AND a bar **closes** back on the
  rejected side. Operator: *"a wick can be a pierce. But it takes a close to log
  a rejection."* The plan's identity is `(pool, reclaim_bar_ts)`.
- **trigger** the close itself — so the plan is declared and triggered by one
  event, and **that event is consumed.** One plan per reclaim bar. Re-firing
  requires a NEW closing bar. This is the operator's *"you tried once, you lost,
  it should be gone"* falling out of the definition rather than bolted on.
- **invalidation** close beyond the pierce extreme (acceptance)
- **instrument** short strike beyond the pool, existing selector
- ⟨PRIOR⟩ **pierce depth becomes a plan attribute**, not a pass/fail ceiling.
  Operator: *"the depth of the pierce is what's going to discriminate on what
  constitutes a pierce."* Recorded now, fitted later; a deep pierce may warrant
  a wider stop or no plan at all.

### 4.5 IRON CONDOR — `IronCondorStrategy`
- **declare when** RANGING, both boundaries identified
- **trigger** per side, price travels `CONDOR_TRIGGER_APPROACH` of the way from
  `bb_middle` toward that short strike
- **invalidation** close beyond the short strike
- **one plan, two triggers.** This is what makes the second leg legible: the
  plan stands with `leg2_pending`, so the PLANS panel shows a half-built condor
  waiting rather than 406 silent refusals (verified on CRM today).

### 4.6 GEX PIN BUTTERFLY — `GEXPinButterfly`
- **declare when** a firm pin exists and price is away from it
- **trigger** ⟨PRIOR⟩ price crosses within `0.5 × EM` of the pin, moving toward it
- **invalidation** close beyond `1.5 × EM` from the pin
- **window** `BUTTERFLY_ENTRY_START_ET` (12:00) → 14:00

### 4.7 DAILY FORK — `DailyForkCreditSpread`
- **declare when** a 1d fork is BUILT with containment
- **trigger** price touches the projected tine (rail at the plan's stamped index —
  **the rail is frozen at declaration**, never re-projected)
- **invalidation** close beyond the tine by ⟨PRIOR⟩ `0.25 × ATR`

### 4.8 CONDOR ROLL — `condor_roll`
Management, not entry: a roll is a plan whose trigger is the tested short strike
and whose instrument is the replacement leg. Declared when a leg is tested,
not when it is breached.

---

## 5. TIGHT AND RELAXED

`strategy/relaxed.py` already exists and is already loud
(`relaxed_entry=1`, populations separable forever). Plans inherit it with one
addition: **`mode` is stamped on the plan at DECLARATION and never changes.**

- **TIGHT** — the specified trigger, unwidened.
- **RELAXED** — `relaxed.widen()` may loosen the **declare-when** conditions and
  the instrument constraints (credit floors, POP, distance).
  🔴 **RELAXED MAY NEVER MOVE A TRIGGER OR AN INVALIDATION.** Those are
  structural prices. Widening the evidence bar produces more plans; widening the
  trigger produces a different trade wearing the same name — which is how the
  relaxed population would silently contaminate the tight fit.

A plan declared relaxed that fires is a relaxed trade, permanently.

---

## 6. THE TICK — AN ELIMINATION CASCADE, NOT A PRIORITY QUEUE

Operator, 2026-08-25, and this is the architecture:

> *"The primal question at every tick is 'are one of my available plans
> executable from HERE' not 'would any strategy FIRE here' — that is a TRIGGER
> not a PLAN. Every tick should be able to assign a binary to each available
> plan until it gets invalidated somewhere in the chain until only one strategy
> remains. Often that remaining strategy might be a GEX pin butterfly, other
> times it might be leg 2 of a condor, followed by GEX pin butterfly."*

**THIS REPLACES `if signal is None`.** Today dispatch is a priority chain: the
first strategy to produce a signal wins the slot and everything behind it is
never evaluated. That is why CRM's second condor leg re-signalled on 406
consecutive ticks with nothing in any log, and why the shape of a tick is
invisible after the fact.

**THE NEW TICK:**

1. Every standing plan is asked ONE question: **executable from here?** — a
   binary, answered by comparing the tape to prices fixed at declaration.
   Not a score. Not a ranking. Yes or no.
2. Plans that answer NO are **eliminated with a reason**, and the reason is
   recorded. A plan is not silently skipped; it drops out of the chain
   somewhere, and where it dropped is the finding.
3. **What survives is what trades.** The residual is not a fallback — it is the
   correct read of a tape on which everything else has been ruled out.

⚠️ **THE RESIDUAL IS MEANINGFUL, AND THIS IS THE PART THAT IS NOT OBVIOUS.**
When the directional plans have all been eliminated, a GEX pin butterfly is not
a consolation prize; it is the trade the tape is describing. The operator's own
sequence — *"leg 2 of a condor, followed by GEX pin butterfly"* — is an
ordering that FALLS OUT of what remains executable, not a hard-coded priority.
Elimination is what produces it.

⚠️ **AND THE ELIMINATION RECORD IS THE INSTRUMENT.** A tick that produces no
trade currently produces one line: `STRATEGY: NO TRADE`. Under the cascade it
produces a full account — six plans stood, five were eliminated, here is where
each one dropped, and the survivor was declined for this reason. That is the
visibility that was missing on TSLA today.

**INVARIANT:** every elimination test is a comparison against a fixed price or
a stamped structural fact. The moment a test re-derives a score, the cascade
becomes the old confluence engine with new vocabulary.

---

## 6b. STALENESS AND CONCURRENCY — still open, operator's call

Not settled by this pass, flagged rather than guessed:

1. **Staleness.** A plan declared at 11:00 on 10:55 evidence may be stale by
   11:40. Options: clock expiry ⟨PRIOR: 45 min⟩, structural expiry (the anchor
   itself moves), or invalidation-only. **Re-scoring is not an option — it
   reintroduces the loop.**
2. **Concurrency.** How many plans may stand at once, and if two survive the
   cascade on the same tick, what breaks the tie? Note the cascade makes this
   rarer than the old chain did — most ticks eliminate down to one or zero —
   but "two survivors" needs an answer before it happens live.

---

## 7. WHAT THIS BUYS

The PLANS panel becomes the primary instrument: every standing intent, its
trigger, its distance from firing, and the evidence that justified it —
**including every plan that never fired.** Today that population is invisible;
`strategy_note` records 182 evaluations and cannot say what any of them wanted.

⚠️ **AND IT IS A MAJOR BUILD.** Operator acknowledged it up front: *"It will be
a major build and it will likely set us back."* Eight strategies, a schema
change, a dispatch rewrite, and the tick loop inverted from evaluate-and-fire to
declare-then-compare.

---

## 8. AS BUILT — r146 (2026-08-26). This section governs where it disagrees with §3-§6.

**What r126-r145 delivered was not this document.** It was a second
implementation of every strategy inside `derived/plans.py` that guessed at what
the real one would do and recorded the guess (zero calls into `strategy/`; see
`docs/HANDOFF_PLAN_ARCHITECTURE_REBUILD.md`). Operator, 2026-08-26: *"The
strategy is the spec, the specification. The plan is how it executes according
to the spec … I don't need two strategies for every strategy."* r146 tears the
mirror out and builds the plan as he described it.

**THE SHAPE.** `strategy/plan.py` — one `Plan` per strategy, held as
`self.planner`. The strategy detects the setup, fixes the trigger and the
invalidation, selects the contracts and EXECUTES. The plan is the informer it
consults on the way: it prices the what-if off the contracts the strategy
chose (credit/debit, risk, **R**), runs the antagonistic checks — the
**session-map geometry** (`analysis/session_map.py`, the 2026-08-25 ruling)
and the **R hurdle** (`strategy/criteria.py`) — records every check every
tick into `plan_tick`/`plan_check` (schema unchanged from r126b), feeds the
edge-triggered gate reporter, and hands back a verdict the strategy honours.

```
t = self.planner.tick(price)
…  return t.refuse("gate", "why")          # every spec refusal — writes the row
…  return t.starved("chain")               # a missing input — NO PLAN row naming it
…  t.level(level, role, name, orb_hi, orb_lo)   # geometry; False = eliminated
…  t.credit_spread(short, long, credit)     # the what-if, REAL width
…  ok, why = t.executable()                 # R hurdle: STRICT refuses, RELAXED records
…  return t.take(signal)                    # the fire — clears the gate, opens the ledger row
```

**THE PLAN NEVER DETECTS A SETUP AND NEVER SELECTS A STRIKE.** `§3
declare_plan()` is NOT built and will not be: a plan that declares is a plan
that decides. The inversion §3 asks for — *"what price from here …"* — is
answered by the strategies that already fix a trigger (ORB, the condor's tine,
the sweep's pool, TC.6's bound) and recorded as `trigger_price` /
`invalidation` / `dist_to_trigger` on every row.

**THE CASCADE (§6) IS NOT BUILT.** Dispatch is still the priority chain.
What §6 wanted from it — *"everything that was still on the table at each
tick"* — is delivered by the board instead: `derived/plans.py` v2.0 writes a
**NOT ASKED** row, carrying the dispatcher's reason (`main.py` v4.16 states
it at every skip point), for every strategy the chain never called. So every
tick has one row per strategy: TAKE / DECLINE / NO PLAN / NOT ASKED / HOLD /
ROLL. Replacing `if signal is None` is a separate decision.

**STRICT / RELAXED (§5).** Under STRICT a plan below `R_FLOOR` (1.00,
`OT_PLAN_R_FLOOR`) REFUSES and the strategy returns None — **this changes what
trades on a strict box**, deliberately; it is the "gating on 1:1" the operator
asked for. Under RELAXED the R value is recorded, the row carries the
`r_muted` check, and the trade proceeds. The R floor can therefore only ever be
fitted from strict sessions. Triggers and invalidations are never widened.

**ORB — zero hurdles, recorded.** Operator, 2026-08-26: *"Include orb in
that, zero hurdles."* ORB's three post-confirmation refusals and its fire
write rows; `executable()` is never called on it; main.py records the
engine-not-confirmed state. The 2026-08-25 ruling stands.

**R DEFINITIONS.** Credit vertical: `credit / (width − credit)`, real width
(the builders assumed $5 everywhere). Debit directional (runaway): stop = the
ORB boundary, target = the stop distance mirrored, `gain = δ·d + ½γd²`,
`loss = δ·d − ½γd²`. Butterfly: `(width − debit)/debit` — NOT YET PRICED,
because the butterfly spec never selects its legs (its signal cannot be valid
today; parked anyway).

**FOUND WHILE WIRING.** `RunawayContinuation`'s signal was ALWAYS invalid —
`target_delta` had one writer and zero readers, no strike/premium/contract,
`is_valid` False on every fire (`main.py`: "Invalid signal from
RunawayContinuation"). Fixed in r146: the strategy resolves its contract off
the chain the dispatcher already passes. The flagship v4 entry rule could not
have placed a trade before this revision.

**NOTED, NOT CHANGED (operator's call):** the condor and daily fork select
strikes ONCE at plan-build; they do not follow the sloped tine to the trigger,
which the fork thesis ("that's the level, but sloped") implies they should.

---

## 9. r147 — leg two is a ONE-LEVEL plan; the butterfly is unparked

**The condor is opportunistic, not a structure.** Operator, 2026-08-26: *"If
the complementary vertical spread becomes available on mapper, the plan
should account for it and confirm a rejection of the level before deploying
the second leg. Acceptance of the level invalidates it and the plan should
start looking at the next available level … it cannot pre-select strikes
beyond the next available one until it's invalidated by acceptance … We would
not sell a complementary spread on a level that's getting breached."*

- **Leg one is unchanged** — its own trigger, no thought of a second.
- **Leg two** (`IronCondorStrategy.plan_second_leg`, plan name `CondorLeg2`)
  runs only while exactly one credit side is open. Each tick it takes the
  **next available level** of the complementary role from the shared session
  map — fork tines (both timeframes) and the mapper's named pools, geometry-
  valid, not finished today, of a class the Rule 4 pairing table permits —
  ONE level, and prices the what-if for that level only (first strike beyond
  it, condor wing, credit off the live chain, R at real width).
- **Four states at the level** (`analysis/level_test.py`, the sweep detector's
  own definitions): UNTESTED → hold · BREACHED (through it, no close back, not
  yet accepted) → hold, **no fire** · REJECTED (tested, last 1m close back
  inside) → fire, R hurdle strict/relaxed as everywhere · ACCEPTED
  (`ACCEPT_CLOSES` closes beyond) → the level is **finished for the session**
  and the plan moves to the next. Finished levels persist in `plan_ledger`
  (strategy `CondorLeg2`, EXPIRED/accepted) and are reloaded after a restart.
- **Consequence:** the sweep and TC.6 no longer fire a second leg directly;
  a named pool completes a condor only as a rejected level inside this plan,
  which is the rejection the operator always required of the sweep class.
  `_can_open_credit_spread` still gates the fire (Rules 1/3/4 + geometry).

**GEX pin butterfly — ON** (`GEX_BUTTERFLY_ENABLED`, `OT_GEX_BUTTERFLY=0`
parks it). Apex on the pin; wings at ⟨PRIOR⟩ 0.25 × expected move rounded to
the increment, floor one increment, ceiling the pin distance; call fly below
the pin, put fly above it; exact strikes or no trade; net debit off marks;
R = (width − debit)/debit — strict vetoes below 1:1, relaxed records.
Its signal is valid for the first time (three contracts, `is_butterfly`).

---

## 10. r160 — the plan is ANTICIPATORY, the strategy is CONFIRMATORY (supersedes §8 where they differ)

Operator, 2026-08-27, read back and confirmed: the plan *"evaluates the
current tick what would need to be true on the next tick for the active
strategies to execute. That means strike selection, wing width, stop
placement (for r-value), minimum r-value acceptable for entry."* The strategy
*"execute[s] the transaction with the variables selected by the plan."*

**The split.** On tick *t*, in the strategy's slot, the plan reads the feed,
evaluates every condition the strategy DECLARES (`CONDITIONS`, name → what
"true" means), selects every variable of the trade — level, side, short
strike beyond it, wing searched to `R_FLOOR`, credit on bid/ask, stop and its
survivability, R and its minimum — and writes the row. On *t+1* the strategy
checks the declared conditions against the tick and, if all are true,
executes THAT trade. The strategy holds no chain and picks no strike. Which
layer decides? The declared conditions do; the plan reads them and reports.

**The rows, per tick, per active strategy:** DORMANT (outside the slot, one
row, no narration) · NO PLAN naming a missing input · DECLINE on a
STRUCTURAL fault the trigger cannot cure (spent level, geometry, no wing
clears R, no credit, stop inside the spread — never muted by relaxed) ·
HOLD "PREPARED — sell 95P / buy 92.5P credit 1.30 stop 1.50 R 1.08 (min
1.00). Waiting on: reclaimed" · TAKE with those exact variables.

**Built in r160: the sweep** (`SweepCreditSpreadStrategy.prepare()` is the
plan, `generate_signal()` the spec). The r146 informer shape — strategy
selects, then asks the plan to price — is inverted for it. TCS, runaway,
daily fork and butterfly still carry the r146 shape and are next, one at a
time. ORB excluded by ruling.

**The condor is a management plan, not a strategy** (operator, 2026-08-27):
*"If there is already an active vertical spread of type (call/put) then only
a complementary vertical (call/put) SWEEP trade is authorized to fire.
Everything else is gated off. The condor doesn't select anything, but it
starts managing once leg 2 is born … a roll if threatened, and the inverted
hedge butterfly if breached, in order of escalation and closed entirely if
uneconomical to save it."*
- `authorize(open_sides)` → the complementary side, only as a sweep; the
  sweep's own plan prepares its own level. `plan_second_leg` and all level
  selection (r147/r158/r159) are deleted. Rule 4's table reads sweep
  everywhere (the fork tine is fine for leg one; leg two is universally a
  sweep — *"only a rejection at the site of the second vertical spread would
  inspire enough confidence to sell credit there"*).
- `manage()` writes the per-tick management row for a formed condor: which
  rung (1 ROLL to risk-free / 2b TENT / 3 CLOSE — TRADES.md "Exits — a
  management LADDER"), what the next rung costs right now, does it clear.
  Execution stays in `condor_roll`. The tent's hedge is the OPPOSITE type of
  the surviving vertical (call vertical → buy a put; put vertical → buy a
  call), equidistant, boxing price in.
- 🔴 **Found in source, named on every such tick:** rung 1 executes only a
  risk-free roll and the tent arms only after a roll, so a formed condor
  with no risk-free roll available is on NO RUNG while price walks through
  a short. The row says "NO RUNG — the ladder says never do nothing on a
  tested structure." Whether rung 2 (invert: roll the untested side
  adjacent to the tested short, TRADES.md) should execute when risk-free is
  unreachable is the operator's call; today it is documented, not built.

**Audit of r148–r158 (r159, folded in):** the layering held at HEAD —
`permit()` carried no contracts, the condor constructed nothing. Three
defects fixed: the land gate had been red since r152 (the exorcism gate
tripped on r152's own test); three files changed without a version bump or
changelog entry (recorded retroactively); leg two was dead whenever the
nearest complementary level was a tine — moot now that the condor selects
no level. On `docs/HANDOFF_PLAN_INPUTS.md`'s "plan-side gatherer that
searches the feed": correct in its goal, dangerous in its wording — the plan
gathers measurements and selects variables; it never decides that a setup
exists. Starvation by name is the part of that handoff that is built.

**Tested on hypotheticals** (`tests/check_plan_prepares.py`, 16 scenarios):
a sweep not yet reclaimed holds with the trade fully prepared; reclaimed
fires with the plan's numbers; no wing clears R → declined even with the
trigger true, relaxed included; no chain → starved; outside the slot →
dormant; a call vertical open → the plan prepares the LOW sweep, not the
fresher HIGH; a spent pool → declined. The condor: nothing open → no
restriction; one open → its complement, sweep only; both → nothing. Formed:
untested → hold; tested with a risk-free roll → ROLL with the numbers;
tested without one → NO RUNG; rolled and breached → TENT, opposite type,
floor stated. One hypothetical was wrong before the code was — a wing
priced at 0.30 on a 2.5-wide spread gives R 0.79 and the plan refused it.

---

## 11. r161 — the butterfly earns its entry, and is exempt from the slot rule

Operator, 2026-08-27: *"I want it to be able to fire regardless if any other
open trades are found. Reason: it has such a high hurdle to clear. GEX
pinning, pin reachable, economic feasibility. If it can achieve all that,
it's earned an entry."* TRADES.md §3 has said since r33: *"no position slot,
no capital, no competition."*

- `GEXPinButterflyStrategy.prepare()` is its plan (the §10 shape): dormant
  outside the slot; each declared condition with its reading — enabled,
  pinning, pin concentration, window, expected move, pin reachable
  (30–100% of EM); the three legs SELECTED around the pin (exact strikes,
  wing from the expected move); R = (width−debit)/debit against `R_FLOOR`
  as a STRUCTURAL check — feasibility is the third hurdle, so relaxed does
  not waive it. `generate_signal()` executes the prepared legs.
- `main.py` v4.19 asks it every tick of its slot in both branches of
  `main_loop`, position open or not, and a fire APPENDS its record
  (`add_open_position`, position_manager v4.4) — never replacing the
  vertical under management. The execution tail is one function
  (`_execute_entry_signal`) for both paths. The condor's authorization no
  longer gates it.
- Hypotheticals (B1–B7): a weak pin holds with the fly prepared, naming
  the wait; strong, reachable, R≥1 fires with the plan's legs; R 0.47 is
  declined, relaxed included; NEUTRAL with a published pin strike holds
  with the fly prepared, waiting on pinning; no exact apex strike is
  declined, never substituted; the open-position branch asks it; the
  append does not drop the vertical.

---

## 12. r163 — a tine is a moving liquidity level; a touch is its event

Operator, 2026-08-27: the daily fork is *"essentially a moving target
liquidity mapper but with the elements of slope and time"* — *"basically a
moving level that sweep is allowed to use, but with a touch, not a reject.
The plan would still need to select a strike beyond the move that caused the
touch."* And: *"it's allowed to be the 1st leg of a condor too, but again as a
touch not identical to sweep which requires rejection."*

- **The mapper owns the level** (`liquidity_mapper` v4.2). `publish_tines`
  runs at the assembly point right after the condor trigger map: each active
  rail becomes a moving named pool ("1h upper tine", "1d lower tine") with
  `price_at(t)` = price − slope·(minutes back). `_detect_touch` walks the
  last 30 one-minute bars and compares each bar to the rail **where it was
  on that bar** — a bar that reaches today's value but not the rail as it
  stood then is not a touch. The event is emitted as a sweep-shaped
  `LiquiditySweep` (`touch=True`, `moving=True`, born `reclaimed`,
  `sweep_price` = the extreme of the touching move); `ACCEPT_CLOSES` closes
  beyond `rail(t)` since the first touch invalidate it.
- **The sweep's plan uses it** (v4.7) exactly as a pool, with three
  differences: under the condor's authorization a touch is never selected
  (leg two requires a rejection); the spent lock is keyed by the tine's
  name, since its price drifts; the signal is classed `{tf}_fork` under
  Rule 4. The strike is selected beyond the touching extreme, as for any
  sweep.
- **The daily-fork strategy is deleted** (373 lines + its dispatch). The
  1h and 1d tines reach the trade through one detector, one plan and one
  construction path.
- **Hypotheticals T1–T7:** a rising rail is touched by a bar that reached
  it where it was (99.95 vs 99.90 then, 100.00 now); the same bar against a
  falling rail is no touch; two closes beyond invalidate; the touch fires
  leg one with the short beyond the high, classed `1h_fork`; as leg two the
  touch is never selected; an invalidated tine holds naming `invalidated`; a
  stopped-out tine stays spent by name after its price has moved. Two
  hypotheticals were wrong before the code was — both pricing a wing that
  could not clear R≥1 — and the plan refused them.

---

## 13. r164 — TCS in the §10 shape

`TrendCreditSpread.prepare()` is the plan: dormant outside TCS_START_ET–
TCS_ENTRY_END_ET; each declared condition with its reading (active, window,
no condor plan, directional vote, ADX floor, price still outside the range
on the trend side); the spread SELECTED — short at the first strike inside
the opening range from the trend side, wing searched to `R_FLOOR`, bid/ask
credit, POP, EV margin, nickel floor; exit stays BREACH-or-nickel (no premium
stop, so `stop_survivable` does not apply). `generate_signal()` executes it.
The muteable R hurdle is gone from TCS — `wing_r_best` refuses structurally.
When the vote is not directional there is no side to prepare, and the row
says so. When a structural fault and an unmet condition coincide, the
structural fault is reported first (a trade the plan could not build
outranks a trigger that has not fired); the condition is still recorded.
Hypotheticals C1–C6.

---

## 14. r165 — the runaway: the plan holds the contract, gamma does the lifting

Operator, 2026-08-27: *"the symbol did not even entertain coming back for a
retest, it just broke out & ran. We want in on the move, but it needs to be
over quickly … purchase and wait for our trailing stop"* and *"Make gamma do
the heavy lifting. Try to get just enough OTM to really leverage gamma based
on the intensity of the move."* Stops are deliberately not in this cut.

- `prepare()` is the plan: dormant past the cutoff; each declared condition
  with its reading (ATR reachable, ORB broken with a direction — including
  the handoff after the engine invalidates on "runaway" — a 1m close beyond
  the 50% TP still holding); the CONTRACT selected before the confirmation,
  so the fire is a purchase.
- **Selection is gamma leverage over the move's own run.** The distance
  price has already travelled from the ORB boundary is the intensity, taken
  as the expected continuation (mirrored, no fitted multiple). For every
  liquid OTM contract on the move's side: gain = δ·run + ½γ·run², scored per
  dollar of premium. Raw leverage-per-dollar always crowns the cheapest
  far-OTM ticket; "just enough OTM" is the **reachability band** — the
  highest leverage among strikes within the run, else the first OTM. On a
  0.90 run the plan picks the 102; on a 1.90 run the 103. The ATR delta band
  (DELTA_NEAR/DEEP) no longer selects; ATR keeps its one job, the
  reachability floor.
- The R hurdle stays muteable for this debit (strict vetoes, relaxed
  records) — there is no wing to search to a floor.
- Hypotheticals R1–R8. One was wrong before the code was: the test assumed
  the raw leverage ranking would crown the 103; it crowns the 105, which is
  exactly why the band exists.
- Also fixed on the way: `ensure_tables` guarded on `id(store)`, and recycled
  ids let a fresh store skip CREATE TABLE (plan.py v1.4).

**The inversion is complete for every strategy except ORB (excluded by
ruling).** Sweep, butterfly, TCS, runaway all prepare then execute; the
condor authorizes and manages; the tines ride the mapper.

---

## 15. r166 — the management plan: one watcher per open position

Operator, 2026-08-27, on where stops live: *"The plan seems like the right
place for them … I like the thought of it watching & thinking if it does
'this' or 'this' we're out!"* And: *"if there is a way to incorporate those
vectors back into the management (and stop functions) I think that is the
logical next step."*

The same split as entries, per open record:
- **The strategy declares its exit conditions** as data
  (`strategy/management.py` `EXIT_CONDITIONS`) — the runaway's hard stop,
  structure stop, trail and target; the sweep's premium stop, acceptance
  through the pool and nickel; TCS's breach-or-nickel; the condor's ladder;
  the butterfly's stop and target.
- **The management plan watches.** After `manage_open_position` has priced
  and decided, it reads each condition's current value off the record and
  the exit engine's own state (premium now, stop premium, trail stop, target,
  underlying stop, MFE/MAE, ticks held) and writes one row under
  `<Strategy>/manage`: *"RunawayContinuation call 1.00 → now 1.30 (+30%),
  MFE 1.34, 12 ticks: premium <= 0.75 → out (hard_stop); 1m close < 101.00
  → out (structure_stop); trail not armed yet; premium >= 2.00 → out
  (target)."* Credit spreads read with credit semantics (value falling is
  profit; the stop reads ≥). It holds no threshold of its own — M9 refuses a
  literal compared to a premium.
- **The r66 vector is recorded for the open position** every tick
  (`strategy_note`, outcome "manage", trade_id attached) — aggression at the
  level, tape, VRP, charm — so a stop can later be fitted against what the
  tape was doing while the position lived, not only at entry. Two gaps
  closed: TCS now has a vector (vote, ADX, ORB width over EM, tape); the
  condor's vector, silent since r158, is written from its `manage()`.
- **The exit engine executes, unchanged.** Nothing in this cut moves a stop.
  When the stop conversation happens, this row is where it lands: the plan
  will *compute* the trail instead of reading it, and the exit engine will
  act on the plan's number.

Hypotheticals M1–M11. One caught a defect before it shipped: a SHORT runaway
is hurt by a close *above* its stop, and the first draft's direction logic
would have narrated "<".

---

## 16. r167 — managed exits: the plan decides, the engine calculates and executes

Operator, 2026-08-27: *"I'm ready for the managed exits build, if on the next
tick is this, cut it loose, or roll, or whatever the management is."* With
the rulings: *"Everything tied to the orb stays. Even the trailing stop armed
at 50% and the tightening after 100% on the peak. The other variables for the
other strategies were all good except for the BOS"*; *"We still have the 15%
floor & the 'breach' stops"*; *"the condor doesn't start managing until both
legs are in the table. Prior to that a lone credit spread stops out at a 15%
floor & the level that it sold at is marked 'finished'."*

- **`ManagementPlan.decide()`** returns the intent for the next tick —
  CLOSE / TRAIL / HOLD — for the records it covers: the runaway, the
  butterfly, and a sweep or TCS vertical while it stands alone. Order, and it
  matters: (1) the declared spec conditions read off the record — the 15%
  floor / hard stop, the breach stops (a 1m close through the ORB boundary,
  the bound, the pool), the target, the nickel — never outranked; (2) the
  engine's calculators — the 50% trail, the tightening after 100% on the
  peak, theta bleed, velocity stall — reached through `evaluate()` and
  adopted as the plan's own. Every intent is a row before it is an act.
- **`position_manager` asks the plan first** and executes the intent through
  the same `_execute_exit` and trail persistence as before. Records the plan
  does not cover — ORB, ADOPTED, tents, a formed condor — go to the engine
  exactly as before. **ORB is untouched end to end.**
- **BOS is retired** from the decision path (measured 34% / 217 / −$7,085).
  Nothing else the engine did is lost.
- **A lone credit vertical that stops out finishes its level** for the
  session — the spent lock now covers every credit vertical (TCS keys on the
  ORB bound it sold against).
- Hypotheticals D1–D15: floor → CUT with the calculator never consulted; a
  close through the boundary → structure stop; the engine's trail adopted;
  theta bleed adopted; the 15% floor on a lone sweep; acceptance through the
  pool; the nickel; TCS at +38% against with no premium floor holds, and the
  breach closes it; two legs → not the plan's; ORB/ADOPTED/tent → never the
  plan's; the butterfly's target; BOS gone; the seam order; ORB's path intact.

---

## 17. r168 — the runaway's stop is a 20% premium floor; the structure stop is ORB's alone

Operator, 2026-08-27: *"the orb structure stop only applies to the orb. The
runaway stop is the orb boundary — but I think that's a terrible stop
location. I would prefer (since it's a debit), a decay or adverse movement
amounting to a 20% loss — I know that is an odd choice, but I still want the
15% on credit spreads. The runaway needs room to breathe. A few pullbacks in
an uptrend are ok."*

Read back from `orb_engine.py` / `exit_engine.py` for the record: the ORB's
**impulsive candle** opens inside the opening range and closes outside it —
definitional, no tolerances; its **structure stop** anchors to that candle's
wick (low for a long, high for a short) and fires only on a 1m close beyond
it; closing back inside the range is not an invalidation. **That rule is
ORB's and only ORB's.**

The runaway (`RUNAWAY_MAX_LOSS_PCT` 0.20): no `underlying_stop` on the
signal, so neither the plan's breach check nor the engine's structure stop
can fire on price; `stop_loss_pct` 0.20 becomes the record's immutable
floor; the trail at +50% and the tightening past 100% still apply through
the calculator. The plan's R prices the risk as 20% of premium against the
modelled gain over the run. r146–r167 had carried the ORB boundary as the
runaway's invalidation — retired.

Hypotheticals: D1 the 20% floor cuts; **D2 a 1m close back through the ORB
boundary with the premium above the floor HOLDS** — the test that would have
caught the earlier mistake; D2b/D16 pin the split; R2b the signal's shape.

---

## 18. r169 — the butterfly rides to the close

Operator, 2026-08-27: *"I want both adjusted for best case. 1545 flatten or
25% loss. Whichever comes first."* The 20%-of-max-profit target and the
150-minute max hold were v3 inheritances chosen for no premise of this
trade: a 1.00-wide fly bought for 0.18 is worth 1.00 at the apex at the
close and the target closed it at 0.34. Both are retired from the decision
path (exit_engine v4.8; the constants stay informational). The butterfly's
exits are exactly two, like the credits: the 25% floor and the 15:45 hard
close. The management row reads *"premium <= 0.14 → out (floor); 15:45 →
flatten (rides to the close)."* Hypotheticals D12/D12a/D12c, M5.

**The exit map, complete (r168 + r169):**
ORB — 25% floor, impulsive-origin structure stop, trail +50%, tightening past
100% · Runaway — 20% floor, trail +50%, tightening past 100%, no price stop ·
Sweep / TCS / lone condor leg — hold to the close, 15% floor, a close through
the level, the nickel; a stop-out finishes the level · Formed condor — the
ladder · Butterfly — 25% floor, 15:45 flatten. Nothing else closes a trade.

---

## 19. r170 — the readers

Operator, 2026-08-28: *"I need a reader outfitted in devtools and have
query.py snapshot active trade decisions 'enter on' and 'exit on' for active
plans. Trade log & all time performance should stay."*

- **On the box** (`query.py` v4.2): a DECISIONS panel at the top of the
  derived half — ENTER ON: the newest `plan_tick` row per strategy (the
  PREPARED trade and what it waits on, the structural fault, the missing
  input, or the slot); EXIT ON: the newest `<Strategy>/manage` row per open
  position. Rows older than five minutes are flagged STALE by the box
  itself. `python query.py --decisions` renders only the snapshot; the full
  dashboard — trade log, all-time performance, market — is the unchanged
  default.
- **On control** (day_trader_pro devtools v1.56): SENSORS item **DECISIONS
  NOW** runs the box's own `--decisions` across the chosen scope. The
  formatter lives on the box, so the fleet reader and a shell on any box
  always show the same thing.
- Order of landing matters: otv4 r170 to the boxes first, then the dtp
  menu — the item is transport for a flag the boxes must understand.

---

## 20. r174 — the teenie lesson: two structural gates on the runaway

2026-08-28, first live session of the gamma pick, relaxed collection: every
runaway fill was ~$1,000 of far-band teenies (AMZN 270C ×63 @ $0.17, GOOGL
352.5C ×77 @ $0.14), each dead in minutes at −20 %/−35 %, some twice on the
same break. Three mechanisms stacked: a 20 % floor on a $0.15 option is
three cents — inside its own bid/ask, so the stop was the next mark wobble
and it gapped; gain-per-dollar rises with distance, so the leverage score
crowned exactly those contracts at the band's far edge, and R against a
pennies denominator looked spectacular to the sizer; and a stopped runaway
re-armed on the same still-true conditions. Operator: *"Yes to both, even on
relaxed."*

- **The floor must clear the spread** (`gamma_leverage_pick`): a contract
  qualifies only if `RUNAWAY_MAX_LOSS_PCT × premium` exceeds its own
  bid/ask spread; no candidate clears → structural DECLINE naming the count
  rejected. No new knob — the spread is the tape's own number. This is what
  keeps the leverage score off the teenies and lands the pick on
  real-premium strikes.
- **One runaway per break**: a floor stop-out finishes that (direction,
  boundary) for the session — `finish_break()` called from trade_logger's
  losing-exit hook, refused structurally in `prepare()`. A NEW break at a
  new boundary is a new trade. In-process registry; a restart clears it,
  recorded as acceptable.

Hypotheticals R9–R13. Both gates are structural: relaxed waives neither.
