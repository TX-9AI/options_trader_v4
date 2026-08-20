# FINDINGS — adversarial audit of options_trader_v4
**2026-08-20 · audited at HEAD `35a6ba4` · fixes in `otv4_audit_fixes_20260820.tar.gz`**
**Every mechanism below was demonstrated by EXECUTION, not read. Born-red runs
against pristine `35a6ba4` are quoted where a new check exists.**

The handoff said the failure class is plausible silence and told me to hunt the
next one. It is F0, and it is the largest instance of the class yet: **every
intraday exit in the repo was dead code, behind a green board.**

---

### F0  `class ExitEngine` was bisected — every intraday exit was dead code
```
SEVERITY : P0 stops the fleet (no position could ever be exited intraday)
FILE     : execution/exit_engine.py:782 (def _track_excursion, column 0)
MECHANISM: r38 landed `_track_excursion` as a module-level function PHYSICALLY
           INSIDE the class region. Python read column-0 `def` as the end of
           `class ExitEngine`; the ~2,000 lines below — `evaluate` and all 33
           evaluators, indented as methods — became NESTED LOCAL FUNCTIONS of
           _track_excursion, created and discarded per call, bound to nothing.
           The file compiles. `import main` passes. At runtime the first
           `exit_eng.evaluate(...)` on any open position raises AttributeError
           into the loop's catch-all — every tick, every position: no premium
           stop, no trail, no theta bleed, no nickel close, no structure stop,
           no condor ladder. Only the independent 15:45 flatten_all() stood
           between an open position and the close.
EVIDENCE : pristine HEAD:
             python3 -c "from execution.exit_engine import ExitEngine;
                         print(hasattr(ExitEngine,'evaluate'))"   -> False
             _track_excursion.__code__ nested code objects: ['evaluate',
             '_evaluate_orb', '_update_post_target_trail', ...] total 34
             ExitEngine().evaluate({...},1.0) -> AttributeError
           tests/check_exit_executes.py at pristine HEAD:
             FAIL ExitEngine.evaluate exists on the class — 2 problem(s) —
             exits are DEAD CODE
FIX      : shipped. The function block relocated BELOW the class (doctrine
           block carries the mechanism); tests/check_exit_executes.py (NEW,
           plain script) drives evaluate() and the evaluators so the class
           cannot fall apart silently again.
BLAST    : every open position since r38. Why nothing screamed: no check
           executed an exit — check_imports proves parsing, stress covers
           entries, and the position_manager call site has no local handler,
           so the error surfaced only as generic loop-error noise. This is
           `import` != `execute`, at maximum size.
```

### F2  A sixth strategy traded live on the 34.2% trend vote, defaulted ON
```
SEVERITY : P1 trades wrong
FILE     : config.py:368 (TREND_CREDIT_ACTIVE default "1"); main.py:2279
           (dispatch); strategy/trend_credit_spread.py:89 + GATES block
MECHANISM: TrendCreditSpread is instantiated (main:867) and dispatched inside
           attempt_new_entry with direction from `trend.overall_direction` —
           the vote measured 34.2% on puts, the quantity v4 exists to retire;
           its own record is 21 trades, 28.6% direction accuracy. Meanwhile:
           its GATES block says "NOT SPECCED, DELIBERATELY, AND NOT
           DISPATCHED"; TRADES.md specs five strategies without it;
           check_dispatch's EXPECTED_ORDER omits it; check_no_regime cannot
           see it (the vote is not a Regime label). Five guards, five
           different documents, all missed the same live path.
EVIDENCE : grep -n '_trend_credit_strategy' main.py -> 867 instantiate, 2279
           dispatch; config default "1"; the GATES comment quoted above.
FIX      : shipped: default flipped to "0" with a doctrine block — the code
           now matches its own stated design. Re-enabling requires the env
           var AND a v4 spec in TRADES.md; the missing spec is the real gap.
           NOT deleted: that is the operator's call (§6).
BLAST    : every afternoon tick until now; any TCS rows in the young book are
           vote-directed and should be window-tagged before any study.
```

### F6  The 15%-unhedged condor-leg stop was not implemented
```
SEVERITY : P1 trades wrong
FILE     : execution/exit_engine.py (_evaluate_condor_leg, base_stop line)
MECHANISM: TRADES.md §5: "BEFORE LEG 2 FILLS — leg 1 manages exactly like the
           sweep credit spread: a 15% stop", and names the 25% as "never
           validated... calibrated for a complete structure collecting credit
           on both sides — not for one naked leg" (condor_stop: 16 trades,
           19% win, −$1,156, worst −$300). The code ran a flat 25% from leg-1
           birth. This is also the handoff's planted challenge — "a stop
           calibrated for a complete structure is being applied to a single
           leg somewhere; find it."
EVIDENCE : no 0.15/unhedged branch existed in the evaluator; check_condor_spec
           was green via F5. Post-fix, executed: lone leg at −16% exits
           `condor_stop ... (unhedged 15%)`; hedged holds −16%, exits −26%.
FIX      : shipped. Stop derived at evaluate time from `_condor_sibling_open`
           (gains `default=` — the probe's error path returns the CALLER'S
           safe direction: TP caller True = no TP; stop caller False = the
           TIGHTER stop). stop_premium in the row remains the widest bound,
           not rewritten. Threshold traceability: 15% is the spec's own
           number (the sweep spread's family), per 5.1.
BLAST    : every leg-1 lifetime before leg 2 fills; F5.
```

### F5  check_condor_spec asserted a stub of its own making — could not fail
```
SEVERITY : P2 measures wrong (a green board over F6)
FILE     : tests/check_condor_spec.py (the old ladder section)
MECHANISM: the section defined a LOCAL `leg1_stop` — `0.25 if leg2_filled
           else 0.15` — then check()ed that leg1_stop(False)==0.15. It proves
           0.15 equals 0.15; it imports nothing from the engine. The third
           can't-fail checker the handoff predicted, guarding exactly the
           unimplemented rule (F6) — and structurally identical to the two
           already caught (word-assert, `or True`).
EVIDENCE : the quoted section at HEAD; green at HEAD while F6 was live.
FIX      : shipped. The section now DRIVES `_evaluate_condor_leg` in both
           hedge states with a pinned clock. Its executing predecessor draft
           is also what exposed F0 — the AttributeError a stub can never see.
BLAST    : trust in the board. See also F-dispatch note below.
```

### F4  The relaxed tag was dropped before the insert
```
SEVERITY : P2 measures wrong (population separability), P1 if ever fitted on
FILE     : execution/entry_engine.py (make_record kwargs); main.py:1439
MECHANISM: relaxed.tag() sets `signal.relaxed_entry = 1`; both record
           builders enumerate kwargs explicitly and neither copied it; the
           column (schema + migration, DEFAULT 0) read 0 on every row ever
           written. Only the `_relaxed` setup_type suffix kept the population
           separable — by accident of riding setup_type. Exactly the failure
           §1.1 predicted, verbatim.
EVIDENCE : `grep -rn relaxed_entry execution/ main.py` at HEAD -> no hits
           outside schema/migration.
FIX      : shipped at both builders: `relaxed_entry=getattr(signal,
           'relaxed_entry', 0)`.
BLAST    : any relaxed-session rows already written carry relaxed_entry=0 —
           recover via the `_relaxed` suffix if they matter.
```

### F10  The flagship's exits routed to a fall-through naming a deleted strategy
```
SEVERITY : P1 trades wrong
FILE     : execution/exit_engine.py (evaluate router, else branch)
MECHANISM: the router keys on exact class names; `RunawayContinuation` has no
           branch and fell into `else: # SweepReversal and any other
           directional strategies` — SweepReversal was DELETED at r33. The
           runaway's spec (TRADES.md §1/r17) cites orb_trail_stop 96%/85/
           +$30,696 as its exit; the sweep evaluator is a cousin (no theta
           bleed, no structure-stop slot, different trail arming), not the
           measured family. A v3 assumption surviving a changed context — in
           the least-changed code, exactly where §1.2 said to look.
EVIDENCE : router source at HEAD; executed post-fix: a RunawayContinuation
           record reaches _evaluate_orb (sentinel assert in
           check_exit_executes).
FIX      : shipped: explicit Runaway -> ORB-family branch (structure stop
           reads underlying_stop, which the runaway does not set — the ORB
           path already treats 0.0 as INERT and says so). The else now
           WARNS once per trade: an unrouted strategy is a routing decision
           nobody made. Fail direction unchanged (sweep rules: 25% stop +
           hard close — survivable).
BLAST    : every runaway position's management until now (moot pre-fix — F0
           had all exits dead anyway; post-F0 this would have become live).
```

### F8  A light-filled roll wore the risk-free label and stood the ladder down
```
SEVERITY : P2 measures wrong + management stand-down
FILE     : strategy/condor_roll.py (post-fill verification block)
MECHANISM: on `actual_total_credit < tested_width` the code alerted "NOT
           fully risk-free" and then FELL THROUGH — set is_broken_wing=1 and
           announced "RISK-FREE ... FINAL FORM" from PLAN numbers. Since
           `any(is_broken_wing)` blocks further rolls, a light fill parked
           residual risk (width − actual credit) with the primary risk
           response disarmed and a green label on it.
EVIDENCE : the quoted fall-through at HEAD (two contradictory alerts from one
           code path).
FIX      : shipped: on shortfall the ladder stays ARMED (a further
           smallest-roll can close the gap), no flag, both alerts state it.
BLAST    : the roll ladder's integrity; any is_broken_wing=1 row should be
           audited against its fills if one ever lands from the old path.
```

### F7  mfe_bars / mae_bars received 15-second tick counts
```
SEVERITY : P2 measures wrong
FILE     : execution/exit_engine.py (_track_excursion)
MECHANISM: `n` counts evaluate() calls (15s poll); the columns are named
           *_bars and their schema comment says "bars from entry to that
           peak". Every consumer of r38's question — how long until a winner
           declares itself — would mis-time it 4×. A wrong number is worse
           than a crash.
EVIDENCE : `n = excursion_ticks + 1` written directly to mfe_bars at HEAD.
FIX      : shipped: bars = round(n × POLL_INTERVAL_SECONDS / 60). Still
           COUNTED, not timed — the file's own halt/feed-gap doctrine is
           preserved; only the unit stops lying. excursion_ticks keeps the
           raw count.
BLAST    : any *_bars rows already written are ticks; the book is ~30h old.
```

### F1  check_gates could not see an aliased relax call
```
SEVERITY : P2 measures wrong (a guard that spelling escapes)
FILE     : tests/check_gates.py
MECHANISM: detection matched the literal `relaxed.widen(NAME)` AND gated the
           whole file on the literal import string — `from strategy import
           relaxed as rx` + `rx.widen(<any constant>, 99)` ran GREEN
           (mutation-verified), the same exemption-by-default shape as the
           scope hole the file itself documents.
EVIDENCE : mutation at HEAD -> "every gate is declared..." (green).
FIX      : shipped: imports resolved (module matched, not the word); every
           strategy walked; every Name in a relax call categorized; a call
           with NO Name refused as uncategorizable. Re-mutation now red;
           clean tree green. (First draft narrowed to arg[0] and wrongly
           flagged runaway's `relaxed.window("00:00", CUTOFF_ET, ...)`; kept
           the old any-position semantics — recorded so it is not re-made.)
BLAST    : trust in the relaxed-mode boundary (§1.1).
```

### F9  Finite-but-insane marks could close live positions
```
SEVERITY : P2 trades wrong on garbage input (self-announcing via a booked exit)
FILE     : execution/position_manager.py (_fetch_current_premium, 6 filters)
MECHANISM: filters were `c.mark > 0` — NaN excluded (NaN > 0 is False), but
           1e12 passes and drives pnl_pct to an absurdity that fires a stop
           or target on a phantom print. The excursion tracker already
           rejects > 1e6; the DECISION path had no ceiling. "Finite is not
           sane" (§4).
EVIDENCE : filter source at HEAD; the tracker's ceiling four lines away.
FIX      : shipped: `0 < c.mark < 1e6` on all six sites. Fail direction:
           None -> tick skipped -> no decision on garbage.
BLAST    : all mark-driven decisions.
```

---

## Findings WITHOUT shipped fixes (operator calls / proposals)

**FD-1 (P3, proposal): check_dispatch executes 3 of 6 strategies** and prints
"each generate_signal executes". ORB, the condor and TCS are not in its order
list or execution block. check_exit_executes now covers the exit side;
the entry-side claim should either execute all six or say three.

**FD-2 (P3, proposal): check_no_regime cannot see `Regime` through an import
alias** (`from analysis.market_state import Regime as _R; _R.RANGING` ran
green in mutation; `primary_regime` reads ARE caught, which is the main
vector). Same fix family as F1 — resolve imports. Also: `conviction` as a
gate is checked by nothing, while PORT_STATE says it "must not be
reintroduced as a gate" — worth a detector before the 49 reads are gone.

**FD-3 (P3, doc): TRADES.md's "No take-profit ... ever" contradicts the code
AND the measurement it quotes.** The condor_tp block (post-cutoff, standalone,
min-hold) implements the split the numbers support (−$242.77 → −$8.43 on 18
standalone legs; worse at every level on 28 formed legs). The CODE is right;
the spec headline is overbroad. check_condor_spec stayed green over the
disagreement — more F5. Fix the sentence, not the block.

**FD-4 (P3): the `is_trend_credit`-era coupling note in TCS's doctrine block
describes v3;** with F2 parking it, the block's "NOT DISPATCHED" claim is now
TRUE — but main still carries the dispatch site. If the operator confirms
retirement, the dispatch block should go the way of r33's deletions.

## Attacked and CLEAN (executed, not read)
- **Entry ladder, all three claims**: worked examples reproduce exactly
  (`0.05` → 2.25 2.20 2.15 2.10 2.05 2.00; `0.10` → 2.20 2.10 2.00); the
  ratchet never re-offers a refused price even when the quote returns
  (posted 2.15, not 2.25/2.20); reprice takes a better mark; the mark floor
  takes mark. The v3 re-offer defect is genuinely fixed.
- **strategy/structure.py fails closed**: unknown strategy, empty record and
  None all derive DIRECTIONAL (flattened at 15:40); condor legs and
  butterflies derive their classes. The 11:30 cutoff cannot be escaped by an
  undeclared name.
- **Roll plan-time arithmetic**: `roll_credit <= 0` refused; the post-fill
  verification recomputes from ACTUAL fills (its disposition was F8).
- **MFE tracking NaN-safety**: safe_float + first-call guard + 1e6 ceiling,
  as documented, and threaded through position_manager to log_exit —
  producer, column, migration and persist all present for all five new
  fields (with F4 restoring the fifth's producer bridge and F7 its unit).
- **The condor stub question (handoff §2)**: the handoff's second thought was
  right — `generate_signal` returning None is correct; the condor trades
  through decide() + the leg machine, and check_dispatch's "executes"
  assertion passes it vacuously (see FD-1).
- **report_orphaned_plan** sits in the manage branch (main:2765) — the only
  branch that runs with a leg open; `_seed_trail_from_record` is called at
  the top of evaluate (now that evaluate exists).

## COULD NOT DETERMINE (absence reported as absence)
- **tick_size fallback frequency on live boxes.** In this sandbox the
  PENNY_CLASSES fallback fires for every symbol (no venue-rule source
  present); whether boxes have one is unknowable from here. The list's
  guesses are right for the majors; propose a per-session counter so the
  "path that should never price a live order" reports how often it does.
- **The 15:45–16:00 retry loop's paging** and **the invert-to-butterfly rung
  arithmetic** were read but not executed — no broker stub deep enough here.
  Named as unexamined; both deserve the check_exit_executes treatment.
- **relaxed `is_live()` fail-closed** was read (r29's explicit-assertion
  doctrine present) but not executed against a hostile env matrix.
- **GEX real-OI plumbing** (r19/r20): parked pending accumulation; its
  thresholds remain stated priors, as the handoff already declares.

## Validation
All seven checks green on the fixed tree (`check_imports`, `check_gates`,
`check_no_regime`, `check_condor_spec`, `check_dispatch`,
`check_exit_executes` NEW, `gen_file_map --check` after regeneration), stress
119/119. Born-red: `check_exit_executes` at pristine `35a6ba4` fails
"exits are DEAD CODE"; the F1 mutation is red under the new check_gates and
was green under the old. No check was loosened; two were strengthened and one
added — stated here per AUDIT.md §4.
