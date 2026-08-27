# HANDOFF — THE PLAN GATHERS INPUTS, THE STRATEGY EXECUTES

**Written 2026-08-27 for [[fable]]. Author: Claude (Opus). Status: r158 landed
the first half; this describes the end-state and what is left.**

---

## THE OPERATOR'S SPEC, IN HIS WORDS

Quoted rather than paraphrased, because the paraphrases are what went wrong
last time.

> "The strategy should have a list of inputs to fire and the plan should be
> looking at the feed, providing those inputs. **Strategy looking for inputs,
> plan gathering and providing those inputs.**"

> "The strategy is the bones of the execution layer, and it has to be fed
> inputs from the plan that is searching the data feed for the elements that
> the strategy requires."

> "**Every variable that the strategy needs to execute should be provided by
> the plan.**"

> "Nothing in the plan is executable. It's an information layer to feed the
> strategy and the strategy will execute."

> "I don't need two strategies for every strategy. I need a strategy, which is
> the specification, and the plan, that plans on how to execute it and is
> verbose about every decision it's making on each tick."

### 🔴 ORB IS EXCLUDED, BY RULING

> "Exclude ORB from everything I just said. **I don't need an additional layer
> of abstraction for a mechanical trade.**"

ORB reads `orb_engine` directly and keeps doing so. It has a record-only plan
(it narrates), no supplied inputs, no gates. This is consistent with the
standing 2026-08-26 ruling — *"Include ORB in that, zero hurdles."* Do not
"finish the job" by including it.

---

## WHY THIS KEEPS BEING NECESSARY — READ THIS BEFORE CODING

This is the **third** attempt at the plan/strategy separation. Both previous
attempts failed the same way, and the failure is seductive rather than obvious.

**Attempt 1 (r126–r145, mine).** Seven plan builders, 1,984 lines, of which
~1,200 re-implemented the strategies. **Zero of seven called the strategy they
claimed to describe** (AST-verified). Built from misreadings of docstrings and
tested against fixtures I wrote myself, so the board was green and measured
nothing. The operator said the speed made him incredulous at the time. He was
right.

**Attempt 2 (r147, Fable's).** Fixed the above, but `plan_second_leg` was born
with 143 lines that selected a short strike, applied a fixed wing, looked up
contracts, priced credit and gated R — **a credit vertical rebuilt inside a
management function.** It then drifted from the real one: mark instead of
bid/ask, fixed wing instead of a search, no `stop_survivable`, and an R gate
that relaxed could mute. Four divergences in code meant to build the same
object.

**Attempt 3 (r158, today).** Deleted 420 lines from the condor. But when the
sweep was given the condor's level, the first version made it a **constraint**
— the strategy went and found its own level, then refused if the plan
disagreed. That is the plan policing the strategy. The operator caught it in
one sentence.

⚠️ **THE PATTERN: every failure was construction logic migrating into the
informing layer, or the informing layer acquiring authority over the executing
one.** Both feel like progress while writing them. The test is not "is this
code good" but "**which layer is deciding?**"

---

## THE TARGET SHAPE

### The strategy declares what it needs

Each strategy owns a manifest of the inputs its spec requires. Not a docstring
— a declaration the plan layer can read:

```python
class SweepCreditSpreadStrategy:
    REQUIRES = ("sweep", "chain", "atr_pct", "price_now", "now_et",
                "orb_high", "orb_low")
```

### The plan gathers them from the feed and hands them over

The plan searches the feed for each named element, fills what it finds, and
reports what it could not. The strategy receives a filled set and evaluates it
under its own rules — every gate it has today, unchanged.

### The strategy never reaches for data itself

This is the load-bearing part. Today the sweep calls `getattr(liq_map,
"recent_sweep")`, reads `chain.puts`, pulls `vol.atr_pct`. Each of those is the
strategy going to find an input. In the end state they arrive.

### Missing input ⇒ STARVED, never REFUSED

Already the convention (`t.starved()`), and it matters more here: **starvation
names an absent input; a refusal blames the setup.** Collapsing them makes a
data outage look like a market judgement, and that has bitten this repo before
(the 08-27 runaway, where an unread field printed as "50% TP n/a" for a whole
session).

---

## WHAT IS ALREADY DONE (r158, landed 2026-08-27)

- The condor's `decide()`, `check_leg_triggers()`, `_build_leg_signal()` are
  **deleted** (366 lines). It is no longer dispatched as a strategy in main.py.
- `plan_second_leg` returns a `Permission(side, level, source, plan_id, why)`
  carrying **no contracts, no strikes, no premium**.
- main.py hands that permission to the **sweep**, which constructs.
- `_sweep_at_level()` looks a supplied level up in `liq_map.sweeps` (the full
  list — `recent_sweep` is only the latest) and hands that sweep to the
  strategy as an **input**.
- `strategy/plan.py` gained `permit()` and the `Permission` dataclass.

Pins: `tests/check_wing_search.py` W16–W19.

---

## WHAT IS LEFT

1. **The `REQUIRES` manifest** per strategy (ORB excluded), and a plan-side
   gatherer that fills it.
2. **Remove the strategies' own data reaches** — chain, ATR, liq_map, GEX,
   session map. One strategy at a time, with the board green at each step.
3. **The elimination cascade** (PLAN_SPEC §6) and `declare_plan()` — specified
   on 2026-08-25, never built. Dispatch order is still a hard-coded chain.
4. **Leg one, one level up.** The condor no longer builds one, but the sweep,
   TCS and the daily fork each still construct their own verticals with their
   own copies of similar logic. `credit_vertical.search_wing()` is now shared
   (r157); the rest is not. Worth asking the operator whether that is the same
   duplication one layer up.

---

## STANDING CONSTRAINTS — THESE ARE NOT NEGOTIABLE

- **Structural, never muted by relaxed:** the R floor as a construction target
  (r156/r157), `stop_survivable` (r154), the risk-anchored stop (r155),
  session-map geometry. Relaxed widens **evidence only** —
  `sweep_max_age_bars` 8→24, `sweep_pierce_ceiling` 0.25→0.75,
  `level_hold_min` 0.75→0.50. Operator: *"the integrity of the trade mechanics
  comes first."*
- **`R_FLOOR` is read directly, never through `r_hurdle()`**, which returns
  None under relaxed. `check_wing_search` W3/W10/W14 pin this; W14 asserts the
  **argument**, because an earlier version grepped for the name and stayed
  green when the argument was mutated to `0.0`.
- **Open the class before reading a field.** Five field-name defects shipped in
  one week (`all()`/`all_rails()`, `oi`/`open_interest`, a GEXSnapshot read as
  a float, `bars_since_reclaim`/`bars_ago`, `tp50`/`target_50pct`). `getattr`
  with a default cannot raise, so a dead gate and a passing gate look
  identical. `tests/check_attr_fidelity.py` (r150) catches this class — run it.
- **A fixture you wrote yourself proves only self-consistency.** Two tests were
  green all week against `tp50`, a field that exists nowhere. If you write both
  the caller and the double, they are wrong the same way.

---

## THE ONE-LINE TEST FOR ANY LINE YOU ADD

**Which layer is deciding?** If the plan decides, it has become a strategy. If
the strategy fetches, the separation has not happened. Everything else is
detail.
