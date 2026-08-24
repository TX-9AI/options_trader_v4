# HANDOFF_CONDOR_STOP_20260824.md — the 25% stop must not apply to a paired condor

**To:** Fable
**From:** Claude, 2026-08-24, audit of `otv4_condor_remodel_20260824_r1`
**Ships with:** `otv4_condor_remodel_r89c_20260824_r1.tar.gz` (the remodel, the
pin fix, AND the stop-suppression fix this document asked for)
**Status:** the remodel is sound and audits clean. This was a SEPARATE defect
the remodel makes materially more likely, not a fault in your work.

> **REVISED r89c (2026-08-24), same day.** Two corrections against a fresh
> clone at r88 `0a84266`, and one status change: (1) the mechanism section
> below originally claimed the exit path had no complement awareness — that
> was traced against the wrong tree and is FALSE at r88; the corrected trace
> is below, and the true defect is narrower and worse-labelled than "missing
> awareness". (2) Line references updated to this archive's files. (3) The
> fix is now IMPLEMENTED in this archive (see "What shipped in r89c") — what
> remains open for you is review, plus the operator question at the end,
> which is still deliberately unanswered.

---

## The operator's ruling

> **"The 25% stop should only apply to a lone vertical spread — never the
> condor."**

## Why it matters, in the operator's own prior evidence

`risk_manager.compute_condor_leg_size` already states the case, and it is the
justification for full-sizing each leg:

> *"When both sides DO fill, the two verticals cannot both reach max loss at
> expiry (price can only be at one extreme), so the notional is less risky than
> 2× suggests. Caveat, stated honestly: **a 25% stop that closes the tested side
> breaks that offset** — 5 of 14 condor symbol-days in the sample had BOTH sides
> stopped on a whipsaw."*

🔑 **THE OFFSET IS THE WHOLE REASON FULL-SIZING IS SAFE.** Each leg is sized at
the full grade budget (v3.2, operator directive 2026-07-23, because 18 of 46
legs never got a second side). That is correct for a standalone vertical. It is
only defensible for a PAIR because the pair cannot lose max on both ends — and
**a stop that closes one end converts the structure back into a single
full-sized directional position at the worst possible moment**, holding the
untested side alone with the hedge gone.

⚠️ **THE REMODEL MAKES THIS STRICTLY MORE LIKELY, WHICH IS WHY IT IS URGENT
NOW.** Under the old design a condor was planned as a pair and both legs were
expected. Under the remodel four triggers fire INDEPENDENTLY and a second leg is
*allowed, never expected* — so legs fill at different times, on different
triggers, far more often. Every one of those is a window where leg 1 is armed
with a standalone stop and then silently becomes half of a condor.

---

## The mechanism — traced, not assumed

**`stop_premium` is stamped ONCE, at fill, and never revisited.**

`main.py:1696` (this archive's v4.7) writes it at entry:

```python
stop_premium = (0.0 if _is_tcs
                else fill_credit * (1 + CONDOR_STOP_LOSS_PCT))
```

From then on it is a fixed number on the position record — the immutable
entry-time floor, and it stays that way.

**CORRECTION (r89c):** the original version of this section said nothing in
the exit path asks whether a complement is open. That trace was run against
the wrong tree. At r88 the exit path is ALREADY complement-aware:
`exit_engine._condor_sibling_open()` exists and is consulted at three sites
in `_evaluate_condor_leg` — the stop multiplier, the ratchet scope (v4.2,
the 2026-08-13 ruling), and the take-profit gate. The actual defect was
narrower and nastier: **the hedged branch still armed a premium stop.**
AUDIT F6 set `lone → 15%, complement open → 25%` — so forming the condor
WIDENED the stop instead of removing it, and the exit label
`[formed: base only]` made a formed-leg stop-out read like a designed
behavior. The pin below catches exactly that string.

The damaging sequence (unchanged in substance):

1. **Leg 1 fires alone** (say the put side, on the 1h fork). `stop_premium` is
   stamped at 125% of its credit. **Correct — it IS a lone vertical.**
2. **Leg 2 fires later** (call side, different trigger, maybe an hour later).
   The structure is now a condor and the offset applies.
3. **Leg 1 still carries an armed premium stop** (at r88, the 25% "formed"
   number). Price tests the put side, the stop fires, and the operator is left
   holding the call side alone, full-sized, with the hedge gone — the exact
   "both sides stopped on a whipsaw" case, reached one leg at a time.

---

## What is asked for

**The stop must become complement-aware.** When a complementary leg fills, the
existing leg's premium stop is SUPPRESSED; if the complement later closes and
the leg is alone again, it is RE-ARMED.

### 🔴 Do NOT mutate `stop_premium` — the repo already learned this

`database/trade_logger.py:568` records the lesson explicitly:

> *"persist the ratcheted trail SEPARATELY from stop_premium. `stop_premium` is
> the IMMUTABLE entry-time floor; the old code overwrote `stop_premium` with the
> trail, so **every trail-armed exit was labeled** [as a floor exit]."*

Overwriting it a second way would re-create that reporting bug in a new
disguise. **Add a separate field** — `stop_suppressed_ts` / `paired_with_id`,
or whatever fits — and have the exit rule consult it. `stop_premium` keeps
recording what the entry-time floor WAS, which is what `r_ledger`,
`exit_replay` and `query.py` read.

### Requirements

1. **Suppression is an EXIT-TIME question, not an entry-time one.** The state
   changes after the fill, so it cannot be baked into the record at entry.
2. **RE-ARM when the leg is alone again.** A complement that closes on the
   nickel rule leaves a genuine lone vertical, and the 25% floor is correct
   again. A one-way suppression is a naked full-sized position with no stop.
3. **⚠️ SUPPRESSED IS NOT UNMANAGED.** The paired structure still needs a
   defined loss boundary — the operator's ruling removes the PER-LEG 25% floor,
   it does not say a condor runs to expiry unmanaged. State plainly what the
   paired structure's stop IS, or that it deliberately has none and why.
   **This is the part I would not guess at; it is an operator call.**
4. **Say it out loud when it happens.** A suppression and a re-arm are both
   decisions with money attached; they belong in the log and in
   `gate_disposition` or the plan ledger, edge-triggered per r73. A stop that
   silently stops existing is the failure class this repo has spent a week
   removing.
5. **The trend credit spread already carries `stop_premium=0.0` deliberately**
   (`_is_tcs` — its measured EV was held to expiry, unmanaged). Do not disturb
   that path; the comment at `main.py:1693` explains why a $0.06 credit must not
   be closeable on one cent of widening.

### A pin that can fail

Born red at r89: drive a leg to fill, then a complement to fill, and assert the
first leg's stop no longer triggers on a move that WOULD have triggered it
standalone. Then close the complement and assert it triggers again. **A test
that only checks the suppression direction passes a naked position.**

---

## What shipped in r89c — implemented, for your review

- **`execution/exit_engine.py` v4.4** — `_evaluate_condor_leg`'s premium stop
  and ratchet now run ONLY when `_condor_sibling_open()` says the leg is
  alone. While a complement is open they are SUPPRESSED; they RE-ARM the
  moment the leg is alone again. Edge bookkeeping in
  `_sync_stop_suppression()`: the suppress edge writes
  `stop_suppressed_ts`/`stop_suppressed_by`, the re-arm edge clears them,
  both announce at INFO once per flip. Edge detection reads the persisted
  field, so it is restart-safe with no in-memory state (F4's reasoning).
  Fail direction stated in-line: sibling probe error → treated as LONE → the
  15% stop stays armed, because a spurious stop on a formed leg loses less
  than a stopless ride toward max loss.
- **`database/trade_logger.py` v4.3** — the two columns, schema + migration.
  `stop_premium` untouched, exactly per the v3.1 lesson quoted below. (v4.2
  is a backfilled bump: `condor_trigger_source` shipped in r89b without one.)
- **Lone calibration UNCHANGED at 15%** (TRADES.md §5 via F6). ⚠️ One reading
  of the operator's ruling — "the 25% stop should only apply to a lone
  vertical" — is that the LONE stop should be 25%, reverting F6's 15%. I took
  the minimal reading (the ruling removes the stop from the CONDOR and does
  not re-litigate the lone number, which has its own documented spec) and
  flagged the ambiguity to the operator rather than deciding it.
- **`tests/check_condor_stop_suppression.py` v1.0** — born RED at r89b with
  10 failures, including S2 red on the exact string `[formed: base only]`;
  green at v4.4. It tests BOTH directions — S2 suppression AND S4 re-arm —
  because a pin that only checks suppression passes a naked position. The
  breach premium is 1.30 on a 1.00 entry deliberately: it clears BOTH the
  lone 1.15 floor and the pre-fix hedged 1.25 floor, so the pre-fix red is
  genuine rather than hidden behind the wider stop. Mutation-proven: removing
  the `_sync_stop_suppression` call goes red naming the bookkeeping pins.
- **Requirement 3 remains OPEN**, on purpose: the formed structure keeps the
  15:45 close, the nickel close, and the roll — any loss boundary beyond
  those is the operator's call and nothing in this archive invents one.

---

## About the accompanying tarball

`otv4_condor_remodel_r89.tar.gz` is your remodel with one fix: your own audit
pin `check_audit_20260823.py` went red, because A3 drove `notify_leg_filled` on
a `LEG1_FILLED` plan — the pair-expectation machinery the remodel correctly
deleted — and failed on `AttributeError: CondorState`.

**Stale test, not a regression.** I nearly reported it as one: my first grep for
`_ledger_move` returned zero and I was about to say F6 had been silently undone.
It had not — the remodel renamed the mechanism to `_ledger_expire` and all four
abandon paths call it. Reading the function instead of trusting the grep is what
caught my own false alarm.

I rewrote A3 against the new mechanism rather than deleting it, because the
invariant still holds: **an abandoned plan must close its ledger row.** A3b now
checks ALL FOUR abandon paths where the original checked only the one branch
that had a bug. Mutation-proven — remove one `_ledger_expire` and it goes red
naming the path.

Two minor notes: the manifest said 12 files and the archive had 10; and
`config.py` shipped byte-unchanged, so I dropped it from a changed-files-only
archive.

Everything else audited clean — geometry gate (PG1/PG2/PG3, including crossed
strikes), Rule 1 / Rule 3 pairing, `condor_trigger_source` on the schema,
`best()` correctly ignoring inactive triggers, and the live tine recomputation.
