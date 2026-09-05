# BACKLOG.md — v1.88

**The record that survives the thread.** A commit is the change; this is what
the change was for, what is left, and what was ruled. WORKING_AGREEMENT §18
requires this file in every archive: *"EV moves only when the backlog records
it — shipping, testing and pushing five artifacts changes EV by zero until the
item is marked."*

---

## PART 0 — HOW TO READ THIS

**STATUS IS THREE CLAIMS, NEVER ONE (WA §18).**

| mark | means |
|---|---|
| ⬜ | OPEN. Not started, or started and not shipped. |
| ◐ **BUILT** | Written and proven on the desk. Nothing on origin. |
| ◐ **PUSHED** | On origin, control checkout in parity. **The fleet still runs the old code.** |
| ✅ **BAKED** | Live on the boxes. **Only this changes any data being collected.** |
| ❌ **DEAD** | Ruled out. Kept so it is not re-litigated (WA §25 / studies rule). |

A PUSHED item is ◐ and never ✅. Conflating them writes a green into the
record the tape does not support.

**IDs ARE STABLE; ORDER IS NOT.** Items carry a prefix ID (`S3.1`, `DOC.4`)
and nothing is ever renumbered. This is the menu lesson applied to the ledger:
*nothing may be tied to the number.* Reorder, insert and close freely — a
reference to `S3.1` in a commit message or a GENESIS line stays valid forever.

**⚠️ NO EARNED-VALUE FIGURES ARE REPORTED HERE, AND THAT IS DELIBERATE.**
There is no cost baseline for this project — no budgeted hours, no rate, no
performance measurement baseline — so CPI and CV are not computable and are
not quoted. What *is* honest is schedule status against the stated dates, and
the BUILT/PUSHED/BAKED split above, which is the completion criterion. An
index computed from an invented baseline would look like measurement and be
decoration; that is the failure class this repo already names as *plausible
silence*.

**RECORD THE GAP, NOT JUST THE WIN.** A verification that was planned and not
actually read goes in as an open step, not a closed one.

---

## PART 1 — OPEN

### Docs

| ID | item | status | notes |
|---|---|---|---|
| **DOC.9** | **Which docs carry no version line at all, and are therefore invisible to GATE.1?** | ⬜ | `README.md` had none in either place until r185 — which is exactly why nine days of a false fleet count went unflagged. `docs/TRADES.md` is the next known one. A doc the gate cannot see is a doc that can rot silently, and the gate reports it only as "carries no version header", never as a failure. Worth one sweep. |
| **DOC.6** | **9 of the last 18 otv4 revisions shipped at least one file with a STALE HEADER.** | ⬜ | Measured 2026-08-29 by replaying `check_land_discipline` over r162–r182. Named example: `strategy/trend_credit_spread.py` gained **22 lines in r175** and its title still reads **v4.5 / r164 / 2026-08-27** at HEAD — a strategy file whose changelog attributes its current content to a revision that did not write it. GATE.1 stops the next one; **this is the backlog of ones already shipped.** |
| **DOC.7** | `day_trader_pro/README.md` describes the fleet as **options_trader_v3**. | ⬜ | The control repo names the wrong trading repo. |
| **DOC.8** | `day_trader_pro/tests/check_ssh_decode.py` carries a title `v1.0` and **no dated changelog entry**. | ⬜ | Found by GATE.1 on its first run against dtp. Minor, and exactly the class the gate exists for. |
| **DEP.1** | 🔴 **THE DEPLOY WAS THE MOST REPEATED ACT IN THIS PROJECT AND THE ONLY ONE STILL DONE BY HAND.** | dtp r278 | ◐ **BUILT + PUSHED.** 🔑 **NINE OF THE OPERATOR'S TEN STAGES ALREADY EXISTED IN `tools/land.sh` (r235) AND WERE NOT REBUILT** — unpack, stage, find the repo by marker, pull first, content gate, regenerate both maps and fail on drift, append GENESIS before `git add`, `check_land_discipline` for the version/changelog/GENESIS bookkeeping, commit, push, clean up. r278 adds the ONE that was missing and fixes two defects the hand-run was hiding. **(1) IT RAN NO CHECKERS** — the content gate greps and never executes, which is the r201 shape §0.6 names; `CHECK <path>` now RUNS in the repo, and a half shipping a `.py` outside `docs/` that declares none is REFUSED, because *nothing was executed* must not read like *everything passed*. **(2) `git add -A`** staged whatever was in the tree, against the operator's own standing rule written after a stray file was pushed off main — every path is now named. **(3) THE ARCHIVE IT DELETED WAS A GUESS** (`ls … \| head -1`), and he routinely has two pending; `LAND_ARCHIVE` names it and an ambiguous glob now deletes NOTHING and says so. New `tools/deploy.sh` finds the tarball, prompts on ambiguity rather than picking, discovers the halves from their specs, ORDERs them, and execs the lander FROM THE ARCHIVE so a delivery that improves the lander is landed by the improved copy. |
| **DEP.2** | ✅ **CLOSED — POS/NEG MATCH AS FIXED STRINGS. THE GATE FAILED BOTH WAYS IN ONE DAY.** | dtp r289 | ◐ **BUILT + PUSHED.** `land.sh` used `grep -q`, a **basic regular expression**, on assertions that are ordinary text. Both directions were observed on 2026-09-05: **FAILED OPEN** — `POS docs/GENESIS.md|**r247**` degenerates to `r24` followed by *zero or more* 7s, so the gate said PASS against a ledger with no r247 row; **FAILED CLOSED** — `NEG menu_functions.sh|[ "$GO" = "y" ]` read the brackets as a character class, matched a file that does not contain the string, and refused a correct delivery, costing a re-cut. 🔑 **A GATE THAT CAN DO BOTH IS NOT A WEAK GATE — IT IS UNRELATED TO WHAT IT CLAIMS TO CHECK.** ⚠️ And regex bought nothing here by design: the operator's own supersession rule is that the assertion is *a distinctive LINE from the real change*, so `**bold**`, `[brackets]`, `$vars` and `.` are content, and an engine can only misread them. `grep -qF`. **F1/F2 drive a REAL land** rather than grepping the source for `-qF`, which would pass against the flag sitting in a comment; **F3 proves the literal form still refuses** a genuinely absent string, because loosening a check that misfires is the easy wrong fix. |
| **DEP.3** | ⬜ **LAND.1 IS REVERSED, BY THE OPERATOR, AND THE RECORD SHOULD NOT CONTRADICT ITSELF.** | ⬜ | LAND.1 ruled that `land.sh` gets no menu item: *"installer scripts should call it, not me manually running it."* **No installer ever called it** — every land since r235 has been a pasted command — so the premise was false in practice, and he asked for the item directly on 2026-09-05. Recorded rather than quietly overridden: **C.31** says a rule outliving its reason is a rule the next reader loosens for a worse reason. `menu_registry.sh` v1.10 carries the reversal in its own changelog; this row is so the ledger agrees with it. |
| **DEP.4** | 🔴 **A MULTI-HALF DELIVERY COULD LAND HALF-WAY, ON ORIGIN.** | dtp r279 | ◐ **BUILT + PUSHED.** Observed, not imagined: landing `r277_r2` before `r276_r2` in the sandbox, the dtp half passed its gate, committed **and pushed**, and only then did the otv4 half correctly refuse on a GENESIS row `r276` had not yet written. Origin held the code with no backlog entry — a half delivery on the shared truth fifteen boxes pull from — and re-running died at `git commit` with nothing left to stage. 🔑 **A PRE-FLIGHT OF EVERY GATE WOULD NOT HAVE WORKED**, and that is the design: a half is ALLOWED to gate on an artifact an earlier half produces, so verifying half two before half one lands would fail a gate that is not failing. **The split is COMMIT vs PUSH, which is where the irreversibility actually sits.** Phase 1 verifies and commits each half locally, in order, so a later half still sees an earlier half's files; phase 2 pushes, and only if every half reached a commit. Any phase-1 failure rolls every repo this run committed to back to its pre-run SHA. ⚠️ **THE ROLLBACK IS `reset --soft`** — a hard reset would revert an unrelated tracked file the operator had mid-edit, which is §35's own reason for refusing a blind `git checkout -- .`; a rolled-back half looks exactly like a gate failure today, files present and uncommitted, recovery printed. ⚠️ **AND THE LIMIT IS STATED:** two remotes are not a transaction. The pushes are last and back to back, and a failure names which repo is ahead and the one command that fixes it — a pushed half is NOT auto-reverted, because undoing something already on origin is a decision for a human. |
| **DEP.6** | 🔴 **THE RECLAIM RAN WHILE THE WRITERS HELD THE STORE OPEN.** | otv4 r255 / dtp r281 | ◐ **BUILT + PUSHED.** `wal_checkpoint(TRUNCATE)` returns **busy** while ANY other connection holds a read mark, and the WAL is only partly reclaimed — measured in `check_purge_reclaim` R2/R2b at **7.1MB → 4.4MB with a reader against 7.1MB → 0 without**. Both close paths purged with `optionsbot` and `candle-feed` still running, which is fine for deleting rows and fatal for getting the space back, and is almost certainly why MU's WAL reached 1.6 GB. **Conductor v2.2** gains `stop_services()` between the verdict and the purge; **`self_close` v1.3** gains step 2b after verification succeeds. ⚠️ **ON THE VERIFIED LIST ONLY** — a held box keeps its services, because it is up for the operator to look at (his 2026-08-25 ruling) and holds the only copy of its day. ⚠️ **AFTER the drain, not before**: stopping first would leave services down on boxes that then get HELD, which is a different state from the one the ruling describes. ⚠️ **STOP, NEVER DISABLE** — the units come back on the next wake, which is how MU lost its swapfile unnoticed for nine days. |
| **DEP.5** | ⬜ **THE LAND COMMAND IS NO LONGER PRINTED — §15 REWRITTEN.** | otv4 r253 | ◐ **PUSHED.** Operator, 2026-09-05: *"I no longer need you to print the landing/commit commands going forward."* The deploy is the devtools item **`LAND a tarball from /home/ubuntu`** (54 today — **cite it by LABEL**, C.15). §15's LANDING half is superseded and its archive rules survive intact as §15a, struck rather than deleted per r240. **WHAT THE ASSISTANT STILL OWES IS THE ARCHIVE AND A `land.spec` PER HALF** — the mechanics are generic, the gate is specific, and only the author of a change can write `POS`/`NEG`/`CHECK`/`ORDER`. §19's scope narrowed to say it no longer covers the land command. 🔴 **§33's SKETCH CORRECTED:** it said `git add -A` while the operator's own standing rule says never to, and the looser document was the one the code followed for four months; it now shows named staging and the CHECK stage. |

### S3 repoint — the reporting apparatus

The governing measurement, taken 2026-08-29 against `docs/WRITE_MAP.md` and
`warehouse/s3_push.py`: **19 of 27 tables already reach S3.** Not pushed:
`fork_series`, `indicator_series`, `surface_series`, `character_axis_sample`,
`chain_marks`, `chain_subs`, `chain_subs_aux`, `feed_meta`. The last four are
feed plumbing and are not warehouse candidates.

| ID | item | status | notes |
|---|---|---|---|
| **RPT.3** | ✅ **NOT A DEFECT — TWO LIVE CALLERS, AND THE SITE ALREADY SAYS SO.** | r272 | ✅ **CLOSED.** It read *"`excursion_report.py` is retired from the menu but NOT deleted."* That is the CORRECT state and `menu_registry.sh:55` already documents it: *"THE SCRIPT ITSELF IS NOT DELETED — it still has one caller, `tools/report_parity.py`, and the nightly `eod_analysis` phase."* The `_excursion` phase shelled it in tonight's chain. ⚠️ **AND `report_parity.py`'s FATE IS NOT OPEN EITHER:** it is WH.11's gate — its own output says *"OT_EOD_PULL=0 is now defensible"* — and `OT_EOD_PULL` still defaults to 1, so dual-write is live and the tool that decides when to sever it stays until it is severed. 🔑 **Retiring a menu item is not retiring a script**, and this row conflated them. |
| **RPT.1** | **Evaluate every remaining trade report on its merits, one by one, and rewrite for v4 where the INTENT is worth keeping.** Operator's direction, 2026-08-29: *"not necessarily salvaging the code but preserving the intent behind the report."* | ⬜ | Queue: **Re-run consolidation** (= S3.7, duplicates what `eod_analysis` already does from S3) — **Excursion report** (= S3.4 above) — **Trade breakdown** (done, r187) — **Fit readiness** (done, r184) — **Exit replay** and **Stop / TP sweep** (v4-native, no work known). The test for each is not "does it run" but **"is the question it asks still a v4 question, and is anything else already answering it?"** |
| **S3.1** | Three derived series had no push stage — and a purge that deletes them. | r191 | ◐ **BUILT + PUSHED, AWAITING BAKE.** `fork_series`, `indicator_series`, `surface_series` now ship via a second `push_series` call against `DERIVED_DB`, own ledger (`dseries_ledger.json`, namespace `dseries|`) because sharing the candle or CDC ledger is the r82 two-meanings-one-dict class. Key layout unchanged (`raw/<table>/dt=/sym=/`) so `warehouse_source.load_series` reads them with no reader change. 🔴 **THE FIND: `retention_purge` DELETES ALL THREE AT 20 DAYS AND HAS BEEN ARMED SINCE r162** — the same unwarehoused loss v4.2 fixed for the feed series, one store over. ⚠️ **AND `check_purge_pushed` COULD NOT SEE IT**, because that purge list was a HARDCODED TUPLE inside `purge()` while the checker imports `ARTIFACT_DAYS`. Promoted to `DERIVED_ARTIFACT_DAYS`; C9/C10 now cover it by execution, born red 2/2 at `54e72a4`. Purge policy itself UNCHANGED — same tables, same 20 days. |
| **ORB.7** | %s **NO WAY TO SEE WHAT EACH BOX WILL SIZE AN ORB WITH.** | r206 / dtp r234 | %s **PUSHED.** `tests/orb_budget_fleet.py` plus a devtools item beside the credentials audit: spot, ORB budget and budget/spot for every running box, with `(DEFAULT - not set)` on any box nobody configured. %s **v1.0 READ THE WRONG ENV LAYER** — it imported `config` over ssh and got its DEFAULTS, so INSTRUMENT read QQQ on all fifteen boxes and the budget read 200 instead of 1050. The spots were right (those are on disk), which made the table look plausible while every env-derived column was fiction. Fixed by reading the unit's `Environment=` lines the way `configure.sh:97` and `rotate_env_remote.sh:65` do, injecting them, and THEN importing config so config's own precedence applies rather than being reimplemented. The menu item CALLS the script rather than inlining a second copy. |
| **MEN.1** | ◐ **TWO MENU ITEMS FOR ONE SCRIPT, ONE FLAG APART.** | r206 / dtp r234 | ◐ **PUSHED.** "Warehouse inventory & cost" and "... (+ noncurrent versions)" were `warehouse_cost.py` with and without `--versions`. The split's justification ended at warehouse_cost v1.2, which made the base report print FIRST and the version pass strictly additive — before that an AccessDenied on `s3:ListBucketVersions` in the second pass discarded a completed whole-bucket scan. Merged into one item that PROMPTS. 🔑 The prompt carries what the second label used to: versioning is on with no lifecycle rule, so noncurrent versions accumulate with nobody deciding, and counting them is a second full pass over ~130k objects. A bare [y/N] would have deleted that fact from the menu. |
| **IV.1** | %s **`atm_iv` WAS COMPUTED AND NEVER STORED — EVERY fire_snapshot ROW CARRIED A NULL.** | r205 | %s **PUSHED.** Measured from the bucket, not reasoned: 31/31 rows from the first live session, all 13 symbols that fired, `price` present and `atm_iv` null. `chain.atm_iv` is a real property (r177) and `chain` is a PARAMETER of `run_analysis`, but the only two readers bound it to a LOCAL inside the butterfly dispatch branches; a grep for any assignment to `ctx["atm_iv"]` came back empty. %s **THE SNAPSHOT WAS THE SYMPTOM, NOT THE INJURY** — `ctx["atm_iv"]` feeds `volatility_measures.summarise`, so **expected_move_iv and variance_risk_premium have been derived from None since they were written**, and the comment above that call says the decay term was the entire point of passing a live IV. Fixed by one stored conversion, `atm_iv_from_chain`, which both branches now read so dispatch and snapshot cannot disagree about one tick. |
| **IV.2** | %s **HOW MUCH OF THE VOL LAYER WAS STARVED, AND FOR HOW LONG?** | %s | r205 fixes the supply. It does NOT establish what `expected_move_iv`, `variance_risk_premium` or anything gated on them did while the input was None, nor whether any strategy read a degraded value and acted on it. The bucket has the history — `derived_fire_snapshot` back to 2026-08-25. Wants a survey before any of those terms is trusted. |
| **WA.1** | %s **§0 OF THE WORKING AGREEMENT — "I GOT CAUGHT LYING AGAIN."** | r204 | %s **PUSHED.** The operator ordered this section in an earlier thread: a heading in the assistant's own voice, and beneath it an unequivocal statement that lying, fabricated claims and unproven assertions stated as fact will not be tolerated. **It was never written.** Later, asked whether a prompt could prevent the shortcuts, the assistant told him *"you already have Section 0 in the working agreement... written after the TSLA incident"* — there was no §0 and no such rule anywhere in `docs/`; the file began at §1. He found the original instruction in his own history and proved it. Numbered 0 because it is the floor, and because it has already been paraphrased out of existence once. Records the incidents, his own words on the cost, that a fixture built from one's own assumption is not verification, that silence is usually a choice, and that a rule changes the odds while a gate changes the outcome. §8 and §9 cross-reference it. |
| **CFG.1** | 🔴 **THE r201 SPOT HINT SHIPPED BROKEN AND THE FLEET BAKED IT.** | r203 | ◐ **PUSHED.** It read a `data/` subdirectory under the install root that does not exist — both files sit at the root, and both paths were in `config.py` (`DB_PATH` 1604, `LOG_FILE` 1613), in a file I had edited an hour earlier. `2>/dev/null` then turned the failure into a blank line that read as deliberate, on a feature whose entire job is to display a number. Paths are now IMPORTED from config, stderr is visible, and the land gate RUNS the function against a planted repo and REQUIRES output. |
| **RPT.6** | 🔴 **NO REPORT LISTED A TRADE.** | r202 / dtp r233 | ◐ **PUSHED.** `trade_report` grouped by strategy, symbol, setup type, exit reason, phase, hour and weekday; `r_ledger` by R bucket; `fit_readiness` by setup. On 2026-08-31 the operator asked what the fleet actually did and there was no answer short of reading the bundle JSON by hand. New `--rows` / `--rows-only` and a **TRADES TAKEN** menu item beside the cross-day breakdown: `sym time strat n entry exit pnl`, **43 chars for Termius on a phone**. ⚠️ Exit reason deliberately ABSENT — it has its own section and the operator ruled symbol and contracts earn the space. 🔑 **CONTRACTS IS NOT DECORATION**: `SPX 6.95 → 7.45` reads as a modest winner; `x50` is what makes it $2,500 and what r201's budget clips to 7. |
| **ORB.5** | 🔴 **ORB HAD NO BUDGET AT ALL, AND OPENED $34,750 OF PREMIUM ON ONE SPX SETUP.** | r201 | ◐ **PUSHED.** 08-31: `SPX PUT 7665 x50 @ $6.95`. ORB is the only strategy that sizes on GEOMETRY rather than risk, so `max(1, floor(width/stop))` grew without bound as the stop tightened. Operator: *"knowing that we can end up with a nominal position size in the 10s of thousands of dollars was eye opening. We are going to rein that in."* New `ORB_BUDGET_USD` (`OT_ORB_BUDGET_USD`, configure.sh item 8), **per box, set per underlying (~$3-5k)**, defaulting to `RISK_PER_TRADE_USD`. 🔑 **THE SCALING CURVE IS NOT A RAMP** — `min(floor(width/stop), floor(budget/cost))` produces the operator's rule as a consequence: tight stop → budget binds → maximum position; wide stop → geometry binds → 1 lot. B3 pins it monotone from 30 to 1. ⚠️ **LOCAL, NOT BROKER BP** — *"a dealer offering available capital is a license for the bot to use it"*; sizing is deterministic and never approaches the broker's limit. ⚠️ **APPLIES IN PAPER** — paper's unlimited is the ACCOUNT, not the trade; an unconstrained paper sizer overstates every P&L against live. ⚠️ A contract dearer than the whole budget is **REFUSED, not floored to 1**, matching `_size_budget`. |
| **ORB.6** | ⬜ **WHAT WOULD A GIVEN BUDGET HAVE CLIPPED?** | ⬜ | r201 records `geometry_wanted` and `budget_allowed` on every ORB row, so choosing a live budget per underlying is a QUERY against banked paper data rather than a guess. Same shape as r198's `wing_stretch`. Wants a report column or a small tool. |
| **BFLY.5** | ⬜ **DOES A CHEAPER AFTERNOON FLY ACTUALLY BUY MORE SIZE?** | ⬜ | The noon floor's NEW justification (r200) rests partly on this, so it is load-bearing and unmeasured. The butterfly sizes through `_size_budget` on `net_debit`, so a cheaper body should mean more contracts for the same dollars. **Comparison set exists and is closed:** the three tagged 09:45 flies of 2026-08-31 (MU, TSLA, NFLX) against every afternoon fly from r196 onward. Wants `contracts` and `net_debit` per butterfly row, afternoon vs pre-noon. If it does not hold, reason 2 comes out of the config and noon rests on pin probability alone. |
| **BFLY.6** | 🔴 **THE NOON RULE'S ORIGINAL PREMISE WAS FALSIFIED, AND THE COUNTEREXAMPLE IS THE ONLY SAMPLE THERE WILL BE.** | ⬜ | 2026-08-31: BFLY.1's relaxed floor let four flies open at 09:45; **three carried to the 15:40 hard close in profit** — MU +$637.50, TSLA +$692.00, NFLX +$47.00, together most of a +$1,543.50 fleet day. The retired premise said exactly this could not happen. ⚠️ **ONE SESSION, AND A PINNING TAPE** — GEX read PINNING or AMPLIFYING across the panel, which is the day an early fly works and precisely the population the rule distrusted. Not enough to overturn anything. 🔑 **The sample is now CLOSED**: r196 is baked, so no further pre-noon flies will occur unless deliberately reopened. Operator's call 2026-08-31: noon going forward. Recorded so the counterexample is not lost, and so nobody re-derives the retired premise from scratch. |
| **RPT.4** | 🔴 **BOTH DASHBOARDS SHOWED ONE OPEN POSITION AND CALLED IT THE BOOK.** | r199 | ◐ **PUSHED.** `status.py:290` and `query.py:194` both carried `ORDER BY entry_time DESC LIMIT 1`. **Latent since r161 made the butterfly additive** — before that, one position per box was TRUE and the limit was correct; nothing swept the readers when the rule changed. Measured 2026-08-31 on CRM, holding a runaway AND a butterfly, showing one, with `2 × $100 = $1010.00 at risk` describing the runaway alone. ⚠️ **r197 makes multi-position boxes the norm**, so this stopped being latent. Both now render every position, oldest-first, with the COUNT and the SUMMED exposure in the header — D3 pins the sum, because listing two cards while printing one card's risk recreates the r121 confusion (*"How is 2 contracts at $96 costing me $800???"*) one level up. |
| **RPT.5** | ⬜ **DUPLICATE PLAN-LEDGER ROWS.** CRM printed `RunawayContinuation [TRIGGERED] @ 259.38` **twice**. | ⬜ | r199 collapses them FOR DISPLAY and prints how many it collapsed, so the duplication stays visible — it does NOT fix the ledger. Two rows for one strategy at one trigger is a write-side question nobody has asked yet. Do not mask it further. |
| **BFLY.3** | 🔴 **THE BUTTERFLY'S WINGS WERE COMPUTED ON A STRIKE GRID THAT DOES NOT EXIST.** | r198 | ◐ **PUSHED.** `config.STRIKE_INCREMENT` is ONE global number for fifteen symbols, and `round_to_strike()` returns an **int** — so every wing quantised to whole dollars regardless of the symbol's ladder. **Measured 2026-08-31: PLTR pin 190, EM 3.25 → wing 1 → legs 189/191 on a $2.50 ladder; AMD pin 472.5 → legs 470.5/474.5.** Neither pair is listed, so the `legs` gate refused for **242 and 243 minutes** (~900 ticks each) on both boxes — an arithmetic problem wearing the costume of a market judgement. `_chain_increment()` now reads the real ladder off the chain (MEDIAN gap near the pin, so one stray half-strike cannot set the grid) and the wing snaps to it, float-safe. 🔑 **THE APEX NEVER MOVES** — both pins were LISTED strikes; only the wings were off-grid, so *"a nearest-strike substitute is a different one"* is untouched and W3 pins it. Operator ruled a wider-than-intended wing ACCEPTED (*"it will bear out in the metrics later on if that is viable"*), so `wing_intended`, `grid_increment` and `wing_stretch` ride on the signal — a ruling that defers to metrics needs the metrics to see it. |
| **BFLY.2** | 🔴 **AN OPEN BUTTERFLY BLOCKED EVERY OTHER ENTRY ON THE BOX — the reciprocal of r161, never built.** | r197 | ◐ **PUSHED.** r161 exempted the butterfly from the single-position rule ON ENTRY (*"no position slot, no capital, no competition"*), but `has_open_position()` still counted it — no slot going IN, one slot occupied once THERE. **Measured 2026-08-31: MU, NFLX and TSLA each held a 09:45 butterfly and each sat in the second-leg-only branch when the credit windows opened, `CondorManagement=HOLD(no credit verticals open)` on all three.** One opportunistic trade removed three boxes from the credit side for the session. `has_blocking_position()` counts everything except a butterfly. ⚠️ **CREDIT IS STILL BLOCKED BY AN OPEN ORB OR RUNAWAY DEBIT** — B3 pins that every non-butterfly strategy still blocks, so this cannot degrade into "nothing blocks". The branch was NOT flipped (that would leave a butterfly-only box unmanaged); the ENTRY half is added back after management. |
| **BFLY.1** | 🔴 **THE BUTTERFLY'S NOON FLOOR WAS RELAXABLE, AND THE FIRST LIVE-FLEET OPEN SPENT IT.** | r196 | ◐ **PUSHED.** Operator, watching butterflies at 09:45: *"the noon floor is non-negotiable."* Confirmed from the fleet's own logs: `DORMANT(entry_window: outside the butterfly slot 09:45-...)` and `Entry: gex_pin_butterfly_relaxed` on `[PAPER]` boxes — 09:45 is `relaxed.window()`'s `relaxed_earliest` DEFAULT exactly, not a pin forming early. `EARLIEST_ET` moves **SELECTION → FOUNDATIONAL** and is pinned via `relaxed_earliest=EARLIEST_ET`; `LATEST_ET` stays relaxable. Verified in paper with relaxed ON: window was `09:45-15:30`, is now `12:00-15:30`. |
| **ORB.2** | The ORB standing offer. | r195 | ◐ **PUSHED.** One DAY limit at the mark for the geometry count, posted ONCE on the firing tick, never re-priced. ORB leaves the r104 ladder; every other strategy keeps it (`check_standing_offer` S1 pins that exactly one is exempt). 🔑 **THE BROKER DECLARES THE POSITION** — fills are discovered from `get_open_option_positions()` grouped by strike+type, and `average_open_price` IS the blended basis, so there is no accretion arithmetic and no persisted remaining-quantity. New `execution/resting_orders.py` v1.0: durable SQLite outside `trades` (an unfilled offer is not a trade and r179's cap reads that table), the attempt's OWN levels frozen at placement so a re-arm cannot judge an old offer by a new attempt's stop, and `_record_kwargs` shared with `enter()` so both construction sites cannot drift. Supervised from BEFORE the `has_open_position()` split — an unfilled offer has no record, so the manage branch would never reach it. `check_standing_offer.py` v1.0, 8 checks, **born red at r194**. |
| **DOC.11** | 🔴 **THE GENESIS LEDGER WAS NESTING INTO ITSELF.** | r194 / dtp r232 | ◐ **PUSHED.** r184 and r191 each carried the literal `<table>`. GitHub renders raw HTML in table cells, so each OPENED a table that never closed: r184 swallowed r185-r191, r191 swallowed r192. Both mine, and the prose was correct — angle-bracket placeholders are this repo's idiom and `<date>`/`<SYM>`/`<prefix>` all render fine, so only a collision with a real element name breaks the page, invisibly in source. Repaired IN PLACE (GENESIS is append-only and never ships in a tarball) and guarded by `check_land_discipline` v1.1, which scans EVERY row in hook mode too. |
| **ORB.3** | ORB entry window 11:00 — 11:30. | r193 | ◐ **PUSHED.** Gates PLACING, not resting. 🔑 Lands EXACTLY on the debit block — both tests are `>=`, ORB declares `long_debit`, `DEBIT_DIRECTIONAL_CUTOFF_ET` is 11:30 — so entries run to 11:29:59 and the block takes over at 11:30:00, no gap, no overlap. ⚠️ Not only a later deadline: the constant also sets `entries_expired` and expires the engine from ANY state, and r60 made the re-arm check read it, so it buys 30 more minutes of breaks, retests and RE-ARMS. Two stale copies fixed (`cascade_harness.py`, `cascade_real.py`) and `tests/check_orb_window.py` W3 now pins EVERY declared copy against config, so a fourth cannot appear quietly. |
| **ORB.4** | Pool in path becomes RECORD-ONLY. | r193 | ◐ **PUSHED.** The named-pool target pull is gone; the target is the pure measured move. Detection, the counted clusters and the notes all stay — the note now names the pool and what the target WOULD have become, so the counterfactual survives for the later study the operator asked for. ⚠️ The pull was a grading-era survivor that CHANGED WHAT THE TRADE DOES while reading like an annotation. |
| **ORB.1** | **r181 shipped INERT: ORB has sized 1 lot since the 08-28 bake.** Sizing normalized into one handler and the geometry ACTIVATED. | r192 | ◐ **PUSHED.** `RiskManager.size_for(structure, ...)` is now the single door, dispatching on the strategy's declared `structure` — the same key `_afternoon_debit_blocked` uses, never a name list, because a name list rots permissively (the RunawayContinuation exemption). Four rules: budget, butterfly, vertical, and `orb_geometry` as a sub-rule of long_debit selected by SUPPLYING width/stop-distance. 🔑 **THE FIX IS STRUCTURAL:** every rule returns a `SizingResult` and the order reads only `SizingResult.contracts`, so "the sizer computed one thing and the order sent another" is now unrepresentable. The r181 override is DELETED from `main.py`, not rewired. ⚠️ `entry_engine.py` needed NO change — it already ordered `sizing.contracts`; the sizer was what wasn't answering. Parity **25/25** against a golden table captured from r191 BEFORE the edit. New `SizingResult.rule`. |
| **S3.6** | Two dedup rules ran on the same data with different tie-breaks. | r190 / dtp r231 | ◐ **PUSHED. THE HIGHEST-VALUE REMAINING CORRECTNESS ITEM, CLOSED.** The shim was never a design feature — its own v1.1 changelog says it existed only to survive pre-07-28 CUMULATIVE bundles, and r187 moved the source to `reports/warehouse` where every bundle is one dt= partition already collapsed by `latest_per_trade()`. 🔴 **KEEPING IT WAS THE DEFECT, NOT MERELY DEAD CODE:** `warehouse_reader` kept the newest `pushed_at_utc`, `trade_report` kept the MOST-FILLED row (`_filled()`), and they agreed only because the newest state also happened to be the fullest. **That is luck**, and report parity could never have caught it because parity runs both sides through the same rule. ⚠️ **NOT DELETED — INVERTED.** Duplicates are now FIRST-WINS by sorted filename and **reported by trade_id AND by file**, because the two conditions that can still cause one (a legacy cumulative bundle in an explicit `--bundles-dir`, or two bundles on one date) are real problems v1.9 absorbed without a word. `_filled()` removed outright, not orphaned. `tests/test_trade_report_dedup.py` v1.0, 5 cases, **born red 6/6 at `356d3f9`**. |
| **S3.4** | Menu 55 (excursion) — **HELD PENDING AN OPERATOR RULING, not blocked on work.** | ⬜ | Measured 2026-08-29: the MEASUREMENT is engine-agnostic and fine (`mfe_premium`/`mae_premium`/`mfe_bars`/`mae_bars`, units fixed by audit F7). **The INTERPRETIVE layer is v3.** Five of nine `TRAIL_FLAVORS` no longer exist anywhere in otv4 (`continuation_trail`, `orb_fvg_trail_stop`, `trail_stop_hit`, `adopted_trail`, `bos_exit`, `insurance_stop`), and `FLOOR_REASON_PREFIXES` is `("hard_stop", "max_loss_floor")` — **`max_loss_floor` is gone**, so half the floor taxonomy is dead. Six reasons v4 DOES emit are in neither list: `credit_hard_close`, `debit_hard_close`, `orb_structure_stop`, `structure_stop`, `tcs_breach`, `adopted_stop`. So the LEASH and FLOOR verdicts score v4 trades against v3 categories. 🔴 **AND IT MAY BE SUPERSEDED:** `otv4/tests/stop_sweep.py` (menu 31) reads the SAME four columns, defaults to S3, is v4-native, and asks a superset question with honest pessimistic/optimistic bounds. Three options: retire 55 for 31 — rebuild 55's taxonomy from v4's live reasons — repoint as-is and accept v3 verdicts. |
| **S3.8** | Cumulative excursions from the warehouse. | ⬜ | Menu 55's `--since` prompt is ALREADY dead: a bundle holds one session and the per-box DBs are gone (C.12), so `excursion_report` refuses. Restoring it means `load_day` unioning several `fleet_trades_*.json` across a date range. Real work, not a rider — and pointless until S3.4 is ruled on. |
| **S3.7** | ✅ **ALREADY DONE, AND THE ROW WAS STALE TWICE OVER.** | r272 | ✅ **CLOSED — resolved by observation, no work.** It read *"Menu 54 → retire, or repoint to `warehouse_reader.build()`"*. **54 is now the LAND item** — C.15 biting a row written before the menu shifted. And the item it meant, now labelled **`Rebuild a day's bundle FROM S3 → reports/warehouse/`**, already shells `warehouse_reader.py`, which is `build()`. The repoint it asked for exists. ⚠️ **A ROW CITING A MENU NUMBER IS WRONG THE MOMENT THE NEXT ITEM LANDS** — the reason C.15 says cite by LABEL, and the reason this one could not be evaluated without opening the registry. |
| **S3.9** | 🔴 **THE CDC COLLAPSE KEYED ON A ROWID, WHICH IS NOT AN IDENTITY.** | dtp r276 | ◐ **BUILT + PUSHED.** `_rid` is the source table's sqlite `rowid` (`s3_push:945`). r266 scoped it to the `dt=` partition after (QQQ, 1) on 09-01 collided with (QQQ, 1) on 09-04 — a real UNDER-count, fixed. ⚠️ **AND THE SAME EDIT OPENED AN OVER-COUNT:** `push_derived` files every CHANGED row under the PUSH day, so one CDC row touched on two days lands in two partitions and a partition-scoped key keeps BOTH. Under-count, then over-count, on the same data. 🔑 **EVERY ONE OF THESE TABLES EXCEPT `character_ledger` DECLARES A PRIMARY KEY THE BOX ALREADY ENFORCES** — the identity was in the schema the whole time, and `screen_plan_gates` (dtp r271) was already grouping its per-tick panel on `plan_check`'s own PK. `DERIVED_NATURAL_KEY` is diffed against otv4's real `CREATE TABLE` statements by N4b, so a PK change here goes red rather than collapsing on a key the box no longer enforces. **The row count becomes self-verifying:** distinct primary keys per ET day IS the population, which is what made *"is 2.38M plan_check rows complete"* unanswerable. ⚠️ `character_ledger`'s key is `id INTEGER PRIMARY KEY AUTOINCREMENT` — in sqlite that IS the rowid — so it keeps r266's partition-scoped fallback, and any row missing a key component falls back too and is **counted in the banner**. |
| **S3.11** | ✅ **CLOSED — AND THE DIAGNOSIS IN THE ORIGINAL ROW WAS WRONG.** | dtp r286 | ◐ **BUILT + PUSHED.** This was filed as *three collapse rules on one dataset*. Measured: **there was ONE, and it ran on a path nothing uses.** `warehouse_reader.load_derived` has carried the natural-key collapse since r276 and has **NO PRODUCTION CALLERS** — its only references outside its own definition are three test files and a `fit_readiness` docstring describing an architecture that changed. Every report reaches the warehouse through `WarehouseCache.load`, which streamed objects **uncollapsed**. 🔴 **r230's SHAPE: a correct fix on a road nobody drives**, and `test_natural_key` stayed green throughout because it calls the dead function directly — a test that exercises the wrong entrypoint cannot fail for the right reason. The collapse now runs in `WarehouseCache.load`, at O(one object) via a UNIQUE index, with `load_derived`'s own winner rule. ⚠️ **AND IT REFUSES A PARTIAL KEY:** the cache keeps only projected columns, and folding on a SUBSET of a primary key merges genuinely distinct rows — silently, in the direction that makes a report look tidier. `fit_readiness` requested `plan_ledger` without `plan_id`, which IS that table's key; it now requests it, and any table whose key does not survive its projection loads uncollapsed and says so. |
| **S3.12** | ✅ **WIRED — THE PER-STREAM BOARD IS A NIGHTLY PHASE.** | dtp r285 | ◐ **BUILT + PUSHED.** `eod_analysis` v1.3 gains a **STREAMS** phase, directly after COVERAGE and before the R suite. 🔑 **THE PRECONDITION WAS THE WHOLE POINT AND IT IS NOW MET:** r277 shipped `--streams` and deliberately left it unwired because the CONDITIONAL and DEAD classifications were read out of `s3_push`'s stage list and never checked against a real bucket. The first hand-run raised **nine flags and seven were the policy table** (r280), and the two real absences were closed as ACCEPTED_LOSS (r284). **An alarm wired before that would have cried wolf on night one and been ignored by night two.** ⚠️ **A SEPARATE PHASE FROM COVERAGE** — the VIX report answers *did the single-writer stream land*, this answers *did every box push every stream it owes*; two questions behind one green is how a passing check stops meaning anything. ⚠️ **IT PRINTS THE FLAGGED ROWS, NOT A COUNT** — `head -3` in the conductor's purge phase (dtp r282) is one phase over, and a summary that hides its rows is one nobody can act on. The **▪ accepted-loss rows print on a clean night too**, because r284's contract is that a closed absence stays VISIBLE. ⚠️ **WARN, NEVER STOP:** a gap is a fact about yesterday, and aborting would cost the R baseline over a missing OHLC file. |
| **S3.15** | 🔴 **DELETING ROWS RETURNED NO DISK, AND THE WAL WAS BIGGER THAN EVERYTHING THE PURGE COULD REACH.** | otv4 r255 | ◐ **BUILT + PUSHED.** `retention_purge` v1.2: delete → **checkpoint** → **gated vacuum**, plus four stores that grew by ABSENCE from every list rather than by policy. 📊 Measured fleet-wide 2026-09-05: `feed_store.db` carries **18-34% free pages** (330-690 MB/box) inside files this purge has trimmed nightly since r162 — the purge worked and the space never came back, because freed pages plateau at the high-water mark. **And MU carried a 1.6 GB `feed_store.db-wal`** beside a 2.3 GB store, META 1.1 GB, AMD 963 MB. ⚠️ **A WAL IS RECLAIMED BY A CHECKPOINT, NOT A VACUUM** — seconds, no temp space — so it runs first and unconditionally. **VACUUM IS GATED**, needing free disk above the live size, because the four boxes that needed it most had less; it refuses with the arithmetic printed and `SQLITE_TMPDIR` on the data dir (`/tmp` is a 476M tmpfs). **COVERAGE:** `plan_tick`/`plan_check` at 7 days in their own `DERIVED_CDC_DAYS` (they ship via `push_derived`, not `push_series`, and folding them into the existing list would turn `check_purge_pushed` C9 red for a TRUE reason); `chain_snapshots` at 3, closing a divergence where config has declared it since v4.4 with no reader; **`shadow` DECLARED AND NOT ENFORCED**. It also reports REMAINING rows per table, because no deletion count explains why MU holds 1.8 GB live against CVX's 0.20 GB. |
| **S3.17** | 🔴 **TWO PURGES FOUGHT OVER ONE DATABASE — AND THIS FILE HAD NO LOCK WHILE `s3_push` HAS HAD ONE SINCE WH.6.** | otv4 r256 / dtp r282 | ◐ **BUILT + PUSHED.** Measured 2026-09-05: the conductor's purge phase and a hand-run `--apply` overlapped, and four boxes raised `sqlite3.OperationalError: database is locked` at `DELETE FROM candles`. **THREE DEFECTS, ALL MINE.** (1) No mutual exclusion — `s3_push.acquire_lock()` guards every invocation path for exactly this reason and `retention_purge`, which DELETES, had nothing; same idiom now, own lock file, `OT_PURGE_LOCK_WAIT` 300s, and it WAITS rather than declining because a purge that silently does not run is the r162 failure again. (2) `_open()` connected at SQLite's **5-second default**, shorter than one 2 GB delete, so a brief overlap raised instead of waiting — `busy_timeout` is now explicit at 120s. (3) **The COUNT was wrapped and the DELETE was not**, so one locked table escaped `purge()`, killed `main()`, and **the reclaim never executed** — which is why AMD, AVGO, GOOGL and NVDA kept their WALs while the eleven that got through returned 8.7 GB. Each DELETE is guarded per table, the failures are named, and a partial purge exits 4 so the conductor can say PARTIAL per box instead of letting it read as done. |
| **S3.18** | 🔴 **`head -3` ATE THE CAUSE OF EVERY PURGE FAILURE, AND THE RECLAIM VERDICT EVERY NIGHT.** | dtp r282 | ◐ **BUILT + PUSHED.** The phase piped the remote purge through `head -3`, sized for the old one-line summary. All the operator saw was `Traceback (most recent call last): \| File ".../retention_purge.py", line 598, in <mo` — the OUTERMOST frame, with the exception type and the raising line cut off. **Three round trips to learn it was `database is locked`.** ⚠️ **A traceback puts its cause LAST**, and the reclaim line prints AFTER the deletion counts, so `head` also guaranteed the checkpoint verdict was invisible on every box on every run — the one line that says whether a 1.6 GB WAL came back. Now redirected to a file on the box, `$?` captured FIRST, then `tail -12`: piping into `tail` would have made `rc=$?` report tail's status, which is the swallowed-exit-code trap this project already records for pytest. |
| **S3.19** | ⬜ **AN SSH TIMEOUT KILLS THE CLIENT, NOT THE REMOTE PROCESS.** | ⬜ | `ssh_util.ssh_run` gives subprocess `SSH_CONNECT_TIMEOUT + 10` = 22s and returns `rc=255 ssh timeout` — but the remote `python3` KEEPS RUNNING with nobody reading its output. That is what created S3.17's collision: two option-14 fan-outs timed out on QQQ, their abandoned purges held `feed_store` open, and the conductor's checkpoint arrived to a busy database. S3.17's lock makes it harmless; it does not make it visible. 🔑 **This is the concrete argument for SSM Run Command** over SSH for the fan-out: instance IDs rather than IPs (WH.7's own conclusion, applied to the command path instead of only the stop path), async with no 22s ceiling, output to S3 rather than through a pipe, and a stopped instance returning a named failure instead of hanging. Needs a probe first — does the agent answer on all 15 — and two IAM changes. |
| **LAND.3** | 🔴 **A ROLLED-BACK HALF WAS TOLD ITS FILES WERE "IN THE TREE, UNCOMMITTED" — TRUE, AND MISLEADING.** | dtp r293 | ◐ **BUILT + PUSHED.** r279's rollback uses `reset --soft` deliberately, so an unrelated file the operator had mid-edit survives (§35). The consequence is that the payload stays **STAGED IN THE INDEX** — and the habitual cleanup `git checkout -- .` copies the INDEX into the working tree, **restoring exactly what it was meant to discard**. 📊 Observed on a real retry 2026-09-05: the tree read clean, the files were still there, and the next land appended a **SECOND GENESIS row for the same revision**. `check_land_discipline`'s duplicate-row check caught it, which is the only reason it was not silent. The message now says STAGED and prints a command that **unstages first**. ⚠️ **THE MECHANISM IS UNCHANGED** — the defect was in the sentence and in the absence of a command to act on. ⚠️ **AND TWO WRONG DRAFTS OF THE CHECK ARE RECORDED WITH IT:** the first failed at the CONTENT GATE, where nothing is committed or staged, so the broken command worked and the case passed at HEAD; the second read `die()`'s line, which belongs to the half that FAILED and never had anything staged either. **Only the rolled-back half reaches the defect**, and a case that does not take that path proves nothing. |
| **SEC.1** | 🔴🔴 **I LEAKED EVERY FLEET CREDENTIAL TO THE OPERATOR'S TERMINAL IN ONE COMMAND.** | r265 | ◐ **PUSHED.** To confirm ONE variable I ran `systemctl show shadow-observer -p Environment --value` across all 15 boxes. **That flag prints the WHOLE block.** Exposed: `TT_REFRESH_TOKEN` (live JWT, `read trade` scope, funded account), `TT_CLIENT_SECRET`, `GITHUB_TOKEN` with write on both repos, `TELEGRAM_TOKEN`. **Four rotations across fifteen boxes, on a Saturday evening, caused entirely by me.** ⚠️ **I HAD WRITTEN THE SAFE FORM EARLIER IN THE SAME SESSION** and reached for the unsafe one anyway — which is the argument for a checker rather than a note. `WORKING_AGREEMENT` **§18a** + `tests/check_no_env_dump.py`. 🔑 **THE CHECKER'S OWN FALSE POSITIVES FIXED THE RULE:** three install scripts do `EL=$(systemctl show … -p Environment --value)` and then filter with `grep "^$1="` — that CAPTURES and emits nothing, and is correct. The offence is **EMITTING** the block, not reading it; a rule banning the read would have flagged three working files and been switched off. ⚠️ Generalised at §18a: **ask what a command prints on the WIDEST input, not the one you are looking for** — a flag returning "the value" of a plural field returns all of them. |
| **SHD.1** | ⬜ **THE SHADOW ↔ PLAN DIVERGENCE JOIN — WHAT WE DID vs WHAT WE SHOULD HAVE DONE.** | ⬜ | Operator's actual instrument, and it does not exist. 🔑 **BOTH SIDES ARE WAREHOUSE-READABLE:** `push_jsonl_tree` does `json.loads` per line and wraps the parsed dict as `record`, so `cache.load("shadow", …, datatype="shadow")` works through r286's path. 🔴 **BUT THEY SHARE NEITHER CLOCK NOR TYPE:** `plan_tick` keys on `ts_epoch REAL` (UTC seconds); shadow's `ts` is `prim.ts_et`, an ET **string** — and two independent processes on their own loops never land on the same float, so an equality join is impossible by construction. **PROPOSED RULE: nearest PRECEDING shadow tick to each plan tick, with the gap reported** — not minute-bucketing, because the question is what was observable AT THE MOMENT the plan decided and averaging a minute destroys the lead-time signal, which is the entire point. Left side is every plan_tick **including the declines**. Blocked until Monday's tape carries stage 2. |
| **CND.1** | ✅ **THE FORMED CONDOR HAS NO FURTHER LOSS BOUNDARY, AND THAT IS A DECISION.** | r269 | ✅ **SETTLED — DO NOT RE-OPEN.** Operator, 2026-09-05: *"The current architecture covers all condor management. It's a settled issue."* The **15:45 close, the nickel close and the roll ARE the management**; the 25% floor stays a LONE-vertical rule with suppress-on-pair and re-arm-when-alone. 🔑 **THE REASONING IS THE REPO'S OWN:** `risk_manager.compute_condor_leg_size` full-sizes each leg because the two verticals cannot both reach max loss at expiry — price can only be at one extreme — so a stop on the tested side converts a structurally hedged position into a directional one at the worst possible moment. Precedent: the trend credit spread carries `stop_premium=0.0` deliberately. ⚠️ **RECORDED AT THE SITE**, in `exit_engine` v4.10, because `HANDOFF_CONDOR_STOP_20260824.md` held the ONLY statement of the open question and was deleted at r269 — the answer had to outlive the question. ⚠️ Suppression and re-arm remain edge-triggered into the log: *a stop that silently stops existing* is the failure class this repo spent a week removing. |
| **SHD.2** | 🔴 **SHADOW VELOCITY DID NOT SURVIVE A RESTART, AND A NULL READ AS A QUIET TAPE.** | r268 | ◐ **BUILT + PUSHED.** Operator's parameters: *"I want it collecting from the open and recoverable from a reboot or crash loops."* `TickAccumulator` is LIVE-ONLY — `add()` runs from inside `one_tick` — so every tick before the process existed is gone. With `Restart=always`/`RestartSec=30`, a reboot at 10:00 or the fourth pass of a crash loop entered RTH with an empty deque and emitted `typical_roc: null` for five minutes (`MIN_TYPICAL_SAMPLES=20`). 🔴 **AND THAT IS INDISTINGUISHABLE FROM A QUIET TAPE** in the corpus meant for fitting triggers — the same silent-empty shape that let seven weeks of stage-1 data look like data. **`seed_from_closes()`** rebuilds the ROC history from the 1m closes `one_tick` already holds, backfilled from the session open, so recovery does not depend on WHEN the process started — the first tick of the day and the fourth restart take the same path, with no timer. ⚠️ **`velocity_state` — `warming`/`seeded`/`live` — is stamped on every record**, because a seeded baseline is a median of MINUTE moves while live samples are poll-interval moves; the record states the scale rather than pretending they are interchangeable, and stays `seeded` while any seeded sample is inside `TYPICAL_LOOKBACK_S`. |
| **S3.21** | 🔴 **EVERY REPORT READ THE WRONG ROWS, IN BOTH DIRECTIONS, SINCE THE CACHE WAS WRITTEN.** | dtp r290 | ◐ **BUILT + PUSHED.** `WarehouseCache.load` listed only the requested `dt=` partitions and filtered nothing afterwards — but a DERIVED partition carries the **PUSH day**, not the row's ET day (C.9, which is why the coverage board grades those streams `pusher` grain). **A row whose session was in range but which pushed the next morning was NEVER READ** — silently, so the report showed a smaller, plausible number with nothing to indicate a hole — **and a row pushed inside the range whose own day fell before it was read anyway.** Neither consumer compensated: `collect()` takes `dates` and does not filter on them, `screen_plan_gates` bounds by strategy and symbol. 🔑 **`load_derived` HAS DONE THIS CORRECTLY SINCE r184** — scan forward, keep rows whose OWN timestamp lands in range — and it has no production callers (S3.11), so the right behaviour sat on the road with no traffic while every real report used the wrong one. ⚠️ **THE FILTER IS PER ROW IN PYTHON, NOT AN SQL OFFSET:** `_et_offset()` applies TODAY's UTC offset to every row — right for eight months, an hour wrong for four — the exact DST trap its own docstring warns about, one level up. ⚠️ Forward scanning is **derived-only**; raw streams are partitioned by the day they describe. |
| **S3.20** | 🔴 **THE QQQ 2026-09-03 RE-BASELINE — TWO ABSENCES, INVESTIGATED AND CLOSED.** | dtp r284 | ◐ **BUILT + PUSHED.** `warehouse_coverage` v1.4 gains `ACCEPTED_LOSS`, a fourth explanation beside `NOT_A_SESSION`, `PARTIAL_BY_DESIGN` and `DEAD`. Two entries: **QQQ/`eod`/2026-09-03** — `pnl_today.json` is a fixed filename and the 09-04 session overwrote it — and **QQQ/`ohlc`/2026-09-03** — date-partitioned so nothing overwrote it, but the directory was never written and `eod_backfill` returned STILL MISSING because DXFeed history is same-evening only. 🔴 **THE ALTERNATIVE WAS CONSIDERED AND REFUSED:** uploading placeholder objects would satisfy the check BY LYING TO IT — `raw/` is the durable record, an object there is a claim that a box wrote something, and `WAREHOUSE_MAP.md` is generated FROM THE BUCKET precisely so it states what is stored rather than what was intended. ⚠️ **IT PRINTS EVERY RUN** with its reason and the date accepted; an absence silently deleted from the board is as bad as one that cries wolf. ⚠️ **AND IT AUDITS ITSELF** — if the data ever turns up the row renders **RESOLVED and FAILS**, because a stale exemption is precisely what would suppress the next real gap on that stream. Keyed per (stream, day, box), never a wildcard. |
| **RPT.13** | 🔴 **`fit_readiness` PRINTED A COLLAPSE THAT NEVER TOUCHED ITS DATA.** | dtp r286 | ◐ **PUSHED.** The SOURCE banner read *"N after collapse by (_rid, ts)"* — a number computed over the cache — while the docstring above it claimed the real collapse ran upstream in `load_derived`. **Neither was true.** The count was real and the sentence was false, and **the sentence is the worse half**: a number nobody can check against a rule nobody applied. It now asks `cache.collapse_note()` which rule actually ran. ⚠️ **AND A FIRST CUT OF THE FIX REPRODUCED THE SAME DEFECT ONE LAYER DOWN** — `load()` returned the INSERT count, so a caller would print *"4 row(s), collapsed on …"* for two logical rows. Caught by the new checker's own detail line showing 2 in the table against 4 in the ticker; `load()` now returns what the table holds. |
| **RPT.14** | ⬜ **`tests/test_fit_readiness_s3.py` HAS BEEN DEAD, NOT PASSING.** | ⬜ | It calls `fr._rows_warehouse([DAY])` while that function has taken `(dates, cache)` since the streaming rewrite, so **every run ends in a TypeError before a single assertion executes**. ⚠️ **VERIFIED AT HEAD, NOT INFERRED** — it raises identically on an unmodified checkout. Repairing the call revealed a SECOND staleness: `collect()`'s return shape changed too (`fired`/`declined` are ints, not lists), so the file is two API generations behind. The half-repair was **reverted rather than shipped** — a test that runs and asserts the wrong shape is worse than one that visibly fails. 🔑 **A file whose presence reads as coverage while it cannot run is the exact failure §0.6 names.** Needs re-deriving against the current `collect()`, which is its own job. |
| **TZ.1** | 🔴 **ONE ET/UTC BOUNDARY FOR EVERY CONTROL-SIDE SCRIPT.** | dtp r287 | ◐ **BUILT + PUSHED.** Operator, 2026-09-05: *"Store everything as UTC, but when a report prompt asks me for a date, convert my choice assuming I mean ET. It's incredibly annoying when I run a report for 'today' at 6pm and it says nothing to report, because UTC has already started the next day."* 📊 **SURVEYED BEFORE WRITING A LINE: NINE naive sites against FIVE correct ones, and the five each carried their own private copy** — so this was never a missing translator, it was the absence of a boundary. The naive nine: `eod_analysis`, `eod_conductor_v2`, `fit_readiness`, `pnl_s3`, `excursion_report`, `orchestrator`, `tools/report_parity`, `trade_report`, and **`market_calendar` — the module that decides what a trading day IS, asking a UTC box**. ⚠️ **THE ROLL IS 20:00 ET IN SUMMER, 19:00 IN WINTER**, and past it a report finds nothing and SAYS SO rather than erroring — a defect in the clock reading as a fact about the market. `ettime.py` now owns `now_et`, `today_et`, `operator_date`, `days_back`, `stamp_et`, `et_day`, `et_bounds`; the five copies delegate. 🔑 **T4 IS THE DURABLE HALF** — it sweeps the repo for naive clock calls and fails on a NEW one, because fixing nine sites without a guard buys a year at most (C.30 turned into something that runs). |
| **TZ.2** | 🔴 **THREE MENU PROMPTS BYPASSED THE BOUNDARY IN SHELL — r287's SWEEP READ ONLY PYTHON.** | dtp r288 | ◐ **BUILT + PUSHED.** Found by the operator asking whether a 19:30 report would know he meant Monday. It would — **unless he pressed ENTER at one of three prompts**, which fell back to `$(date +%F)`: UTC on this box, handing the script tomorrow's date BEFORE any Python default could apply. `menu_functions.sh:220/395/577`, against three sibling prompts in the same file already using `TZ=America/New_York date +%F`. ⚠️ **THE MISS WAS THE GUARD'S SCOPE, NOT THE FIX.** r287's T4 walked `*.py` and I called it the repo; the gap was in the language the checker did not read, which is the same shape as the defect it exists to catch. **T6 now sweeps `.sh`** and was proven red against the three real sites before they were fixed — editing three lines without extending the sweep would have left the next `.sh` prompt free to do it again. ⚠️ Also worth recording: **at 19:30 ET in SUMMER it is not yet Tuesday in UTC** — the roll is 20:00 EDT / 19:00 EST, so this is a winter-hours failure and would have looked intermittent. |
| **DOC.15** | 🔴 **r247 AND r248 WERE SPENT NUMBERS WITH NO ROWS, AND THE LEDGER COULD NOT SAY WHY.** | r259 | ◐ **PUSHED.** Both were otv4 halves cut against a BACKLOG version that r278 superseded before they landed; each was re-cut as `_r2` and landed as r250/r251. `check_ledger_parity` reported them only inside *"15 unused revision number(s)"* — true, and useless to a reader who cannot tell a MISSING revision from a number that was never used without going through git. **Rows now exist IN SEQUENCE between r246 and r249**, marked cut-never-landed with what superseded them. ⚠️ **AND THE IN-SEQUENCE PLACEMENT IS WHY THIS SHIPPED AS A FILE RATHER THAN AN APPEND** — the operator's call, and correct: an append can only reach the bottom of the table, where a row for r247 would sit after r258 and break the newest-is-last property the whole ordering contract rests on. ⚠️ §35's rule that GENESIS never ships still holds for the ordinary case; this is the r194 exception — a REPAIR to existing rows — and it is safe only because the copy was taken from HEAD immediately before packaging and nothing landed in between. |
| **RPT.11** | 🔴 **SIX MENU CONFIRMS ACCEPTED LOWERCASE `y` AND NOTHING ELSE.** | dtp r283 | ◐ **BUILT + PUSHED.** Measured 2026-09-05: the operator answered the LIVE backfill prompt with **`Y`** and the run silently did not happen — no error, no message, just the next prompt. **A confirm that discards a plausible yes is worse than one that refuses**, because *declined* and *ran and did nothing* look identical. All six sites route through `_yes` in `devtools.sh`; the DESTRUCTIVE ones now say what they declined while a flag toggle stays quiet, which is why the helper is a pure predicate rather than one that prints. ⚠️ **C3 pins that NO lowercase-only comparison survives anywhere in the menu** — fixing the one site that bit and leaving five is how this returns (C.30: when a rule changes, sweep its readers). ⚠️ And it must still refuse `n`, `sure` and empty: these prompts wake boxes, stop trading and delete rows, so loosening it to *anything non-empty* would be worse than the bug. |
| **RPT.12** | 🔴 **THE OHLC BACKFILL'S STREAM CAP WAS 29-BOX ARITHMETIC, AND IT HARD-STOPS.** | dtp r283 | ◐ **BUILT + PUSHED.** A **one-box** backfill against a 15-box fleet was refused outright: `10 stream cap` with 15 running, and the check is `return 2`, not a warning — despite the file's own header describing a warn-never-stop pattern for a different check nearby. 🔑 **r53 ALREADY RETIRED THE FLEET-WIDE COPY OF THIS GUARD** on exactly this reasoning — *"it existed so a maintenance wake could not put 29 boxes on the wire at once; the fleet is 15 and a normal session already carried ~20 without strain"* — and this per-report copy was never swept after the 2026-08-20 pare. Same shape as the README fleet count that read 29 for nine days. Default moves to **20, which is r53's own recorded figure rather than one I chose**, `OT_STREAM_CAP`-overridable, and marked a PRIOR: if the DXFeed ceiling is ever measured rather than inferred, it moves again. |
| **S3.16** | ✅ **ANSWERED AND CLOSED — `quote_series` IS THE STORE, AND THE SPREAD IS TWO FACTORS, NOT ONE.** | measured r260 | ✅ **CLOSED.** Fleet-wide 2026-09-05, post-purge: `quote_series` dwarfs everything — QQQ **11,476,862** rows against greeks 431k, prints 394k, candles 17k. MU/CVX on that table is **13.8x** against a 9x store spread, so it is both the biggest table and the one that explains the variance. 🔑 **BUT THE DECOMPOSITION MATTERS MORE THAN THE HEADLINE.** `greeks_series` and `quote_series` ride the SAME per-contract chunked subscribe, so greeks is a clean proxy for chain width — it varies **4.2x** while quotes vary **15.0x**, and quotes-per-greek varies another **4.1x** (CVX and UNH near 6.7, QQQ and TSLA at 25-27). **Chain width and per-contract quote ACTIVITY contribute roughly equally** (4.2 x 4.1 = 17, against 15 observed). ⚠️ **THIS CORRECTS MY OWN EARLIER CLAIM** that the disk story and the 09-02 OOM are one root cause: they share a contributor, they are not the same number. ⚠️ One clean corroboration from a different measurement: **SPX reported `prints 0`**, independently confirming r280's `EVERY_EXCEPT:SPX`. |
| **S3.13** | ⬜ **THE 2026-08-25 PURGE DELETED 492,945 `raw/shadow` OBJECTS AS A DEAD STREAM. IT WAS NOT DEAD.** | ⬜ | The purge was justified by the same never-installed finding ASK.2 now records as false. `raw/` is the durable copy and by design never deletes; this deletion went through the console grant. **What is actually lost is not yet established and should be measured before it is described** — the boxes do not purge `shadow` (it is in neither `ARTIFACT_DAYS` nor `DERIVED_ARTIFACT_DAYS`), and QQQ holds 32 date dirs, so some or all of it may still be box-side and re-pushable. Two questions, in order: **how many of the deleted dates still exist on a box**, and **is the answer to re-push them or to accept the loss** given the stream's stated purpose was the Layer-1 freeze evidence. ⚠️ It is also a standing lesson: a purge argued from a finding rather than from the bucket deleted the bucket's own evidence that the finding was wrong. |
| **S3.14** | ⬜ **`shadow` IS UNBOUNDED ON THE BOXES, AND QQQ FILLED ITS DISK.** | otv4 r255 | 🔴 **REFUTED AND CLOSED — shadow is 21-40 MB, about a third of one percent of a 10 GiB volume. It was never the disk.** I raised it from a directory count without measuring a size; the measurement kills it. ✅ **CLOSED — DEAD**, recorded rather than dropped. **The real consumer is `feed_store.db` plus its WAL**, which S3.15 and DEP.6 now carry. | Nothing purges it: `shadow` appears in neither `ARTIFACT_DAYS` nor `DERIVED_ARTIFACT_DAYS`, and `NEVER_PURGE` does not name it either — it is untouched by absence rather than by policy. QQQ holds **32 date directories** of high-frequency jsonl and **ran out of space on 2026-09-03**, which is what cost that day's `eod` and `ohlc`. ⚠️ **THE LINK IS PLAUSIBLE AND NOT MEASURED** — no size was taken, and r162 already established `feed_store.db` as the disk story on the 08-27 outage. This is filed as a question, not a cause: **measure `du -sh` on the shadow tree across the fleet before anything is concluded or deleted.** Its disposition depends on ASK.2. |
| **S3.10** | ⬜ **NOTHING VERIFIES S3 COVERAGE PER STREAM PER DAY.** | dtp r277 | ◐ **BUILT + PUSHED.** `warehouse_coverage.py` v1.2 `--streams`, ADDITIVE — the v1.1 VIX report, its verdicts and its exit code are untouched, and `tests/test_warehouse_coverage.py` is byte-identically green before and after, which is the additive claim proven rather than asserted. Every stream carries its GRAIN (`record` / `batch` / `pusher`) and its EXPECTATION (`EVERY` / `OWNER` / `CONDITIONAL` / `DEAD`). 🔑 **A SILENT BOX IS ONE DIAGNOSIS, NOT TWENTY** — a box that pushed nothing is `BOX_SILENT` and its absences are attributed there rather than counted against every stream, which is v1.0's `PUSH_DEFECT`/`OWNER_DOWN` split generalised; without it the first fleet-wide outage makes the report unreadable. The panel is imported from `selector.PANEL` and an empty one REFUSES rather than grading against a guess. Presence is ONE delimited LIST per stream-day; object counts page and are opt-in behind `--counts`, pinned by counting paginator calls (dtp r253). | 🔑 **A TOOL ALREADY EXISTS TO EXTEND** — `warehouse_coverage.py` v1.1 is LIST-only, trading-day aware, and already carries `NOT_A_SESSION` and `PARTIAL_BY_DESIGN`. Building a second one is the WA §35 rot. ⚠️ **THE EXTENSION IS NOT ONE LINE:** `push_derived` writes ONE OBJECT PER TABLE PER RUN and `push_series` batches at 50k, so an object count on `raw/derived_*` counts PUSH RUNS, while `push_file` is one object per line and it does count rows. And the derived `dt=` is the PUSH day (C.9), so a partition check there answers *"did each box's pusher run"* and cannot answer *"are the rows complete."* **Delivered next as dtp r277.** |

### Sensor twins — control-side, read S3, boxes untouched

The whole SENSORS block (menu 19–30) is an SSH fan-out running `sqlite3`
against each box. That is right **during** a session and wrong after it.

| ID | item | status | notes |
|---|---|---|---|
| **SNS.1** | Control-side twin for sensor 30 (Order flow). | ⬜ | `prints` and `quote_series` are already in S3. **Portable today**, no dependency on S3.1. |
| **SNS.2** | Control-side twins for sensors 20, 21, 23, 24, 25, 29. | ⬜ | All six tables already in S3 via `DERIVED_TABLES`. |
| **SNS.4** | ✅ **CODIFIED AS WA §36a — AND IT NAMED THE WRONG FUNCTION.** | r272 | ✅ **CLOSED.** It read *"every future S3-sourced derived reader must use `warehouse_reader.load_derived()`, not a bare partition read."* 🔴 **`load_derived` HAS NO PRODUCTION CALLERS** (S3.11) — it carries the natural-key collapse, the forward scan and the ET-day filter, and nothing in the tree reaches it. **A standing rule pointing at the correct-but-unused path would have sent the next reader down the road with no traffic**, which is precisely how S3.11 and S3.21 happened. The rule now names `WarehouseCache.load`, which every report actually uses and which carries all three behaviours since dtp r286/r290. ⚠️ Moved to the WORKING_AGREEMENT because it is a STANDING RULE, not deferred work — a backlog row is a task, and this is a constraint. |
| **SNS.3** | Control-side twins for sensors 26 (Surface), 27 (Indicators), 28 (Forks). | ⬜ | **BLOCKED on S3.1 having baked and collected a session.** |
| — | Menu 19, 22, 58, 61 | ❌ **DEAD** | Deliberately NOT repointed. 19/22/58 are live diagnostics — S3 is the wrong source for *"is the feed fresh right now"*. 61 fetches from yfinance and writes to the box by design. |

### The end state — trades joined to feed context

| ID | item | status | notes |
|---|---|---|---|
| **END.1** | One query surface over `warehouse_source`: trades × `fire_snapshot` × the series, joined on `trade_id` and timestamp. | ⬜ | The spine exists — `edge_scan` already joins trades × `fire_snapshot` × `plan_ledger`, `exit_replay` already rebuilds premium paths from `quote_series`. This is assembly, not invention. |
| **END.2** | Build the chain⇔trade join. | ⬜ | ⚠️ Chains are warehoused but this join **has never existed** — `entry_snapshot` holds FVG context, **not chain state**. It must be built, not verified. |

### Strategy

| ID | item | status | notes |
|---|---|---|---|
| **ORB.3** | ORB entry window 11:00 — 11:30. | r193 | ◐ **PUSHED.** Gates PLACING, not resting. 🔑 Lands EXACTLY on the debit block — both tests are `>=`, ORB declares `long_debit`, `DEBIT_DIRECTIONAL_CUTOFF_ET` is 11:30 — so entries run to 11:29:59 and the block takes over at 11:30:00, no gap, no overlap. ⚠️ Not only a later deadline: the constant also sets `entries_expired` and expires the engine from ANY state, and r60 made the re-arm check read it, so it buys 30 more minutes of breaks, retests and RE-ARMS. Two stale copies fixed (`cascade_harness.py`, `cascade_real.py`) and `tests/check_orb_window.py` W3 now pins EVERY declared copy against config, so a fourth cannot appear quietly. |
| **ORB.4** | Pool in path becomes RECORD-ONLY. | r193 | ◐ **PUSHED.** The named-pool target pull is gone; the target is the pure measured move. Detection, the counted clusters and the notes all stay — the note now names the pool and what the target WOULD have become, so the counterfactual survives for the later study the operator asked for. ⚠️ The pull was a grading-era survivor that CHANGED WHAT THE TRADE DOES while reading like an annotation. |
| **ORB.8** | The ORB firing sequence is the gate; one confirmation, one order. | r207 | ◐ **PUSHED.** QQQ 2026-09-01 took TWO ORB shorts off ONE confirmation — 2 lots @ 1.56 stopped on the 25% floor, then 24 lots @ 1.15 (the exact premium the first exited at) on the same tick, dead two minutes later on the structure stop. Three defects stacked: r195 replaced `mark_triggered()` with `_orb_offer_working()`, which reads a table PAPER NEVER WRITES because `_place_single_leg` short-circuited to the paper filler above the standing-offer branch — so paper ran pre-r195 behaviour behind a green board; `main.py` bound `orb = ctx["orb"]` at the top of the tick and dispatched on it at the bottom, and `_rearm()` REPLACES ORBData, so after the exit the reference was an orphan still reading OPEN_SHORT (r96's defect at the manage→entry seam); and `_orb_d` measured the stop distance from the LIVE price, so the second fire — a few cents from its own invalidation — sized twelve times larger. Fixed by a latch on the CONFIRMATION (mode-independent) and an engine re-read at the dispatch that announces the stale copy. Paper now reaches the same door and fills whole. 🔴 AN INTERMEDIATE CUT ALSO CHANGED THE SIZER to a boundary-to-wick distance frozen at the break; the operator refused it before it landed — *"the true risk is based on where we entered, not the range boundary. That's arbitrary. The 2 factuals are the distance from entry to the stop"* — and he is right, and it was fixing a symptom the latch had already removed. Sizing is UNCHANGED at |entry - stop|; `stop_distance_px` survives RECORDED-ONLY for r119's question, pinned by S8/S8b. ⚠️ CHANGES WHAT GETS TRADED: fewer ORB entries, same sizing. Operator: *"the second bite honestly does not happen very often and muddies the water."* |
| **ORB.9** | Does the depth of the impulsive candle inside the range predict anything? | ⬜ | r119's open question, unanswered since 2026-08-29 and now measurable: r207 records `stop_distance_px` as a plan check on every ORB row, fired or not, beside `underlying_entry`, and `SizingResult` carries `geometry_wanted`/`budget_allowed` from r201. So "did shallow-break setups do better, and did the fill drift from the boundary" is a QUERY after a session rather than an argument. ⚠️ RECORDED, NOT GRADED — S8b fails if anything reads it in a decision first. |
| **ORB.10** | The 15-second fire drift is a WASH. | ruled | ✅ **CLOSED BY RULING**, 2026-09-01. The fire lands on the tick after the retest bar closes, so price can move before the fill and size the trade off slightly different room. Operator: *"I'm ok with fast tape because sometimes it works in our favor and sometimes it doesn't. It's a wash."* Symmetric, so no floor, no refusal, nothing to tune. Filed so it is not re-opened as a finding by a future reader who spots the asymmetry-shaped hole and assumes nobody looked. |
| **BFLY.7** | The butterfly has never had a stop-survivability gate. | r208 | ◐ **PUSHED.** 2026-09-01: five flies fired at 12:00:00, three stopped out inside the same minute — META 577.5 debit 0.17 (25% floor = **4.3c**), CRM 0.21 (5.3c), MU 0.28 (7.0c). A fly's value is `lower + upper - 2*center`, so THREE legs of quote noise compound into a figure itself worth 17 cents. Not stopped by price, stopped by their own marks. `criteria.stop_survivable` was built for exactly this at r154 and had ONE caller — the sweep; the butterfly was not even on r154's untouched list because on 08-27 it had never fired. Wired as FEASIBILITY, never mode-dependent. |
| **BFLY.8** | 🔴 R AND SURVIVABILITY PULL OPPOSITE WAYS, AND ONLY R WAS WIRED. | r208 | ◐ **PUSHED.** R = (width-debit)/debit RISES as the wing narrows; survivability FALLS. With only R in the code the selector steered to the **least survivable structure available and called it the best one** — META at R 10.8 was not a fly that happened to be fragile, it was the most fragile constructible fly, chosen because it was. Fix: the wing is SEARCHED over listed strikes, R_FLOOR caps the wide side, survivability floors the narrow side, narrowest qualifying wing wins, no wing qualifying is a definite answer. `WING_EM_FRAC` DELETED — it was a prior nobody fitted that was also deciding whether a survivable fly existed at all. |
| **BFLY.9** | Fit `STOP_VS_SPREAD_MIN` for a FOUR-leg structure from S3 chain data. | ⬜ | 2.0x is r154's prior, chosen for a two-leg vertical whose quote is ONE spread wide; a fly's is FOUR. The two bounds together require **width >= 64 x leg-spread** — 2c legs need $1.28 of wing, 3c $1.92, nickel $3.20 — and the wing may not cross spot, so on many symbols the two windows barely overlap and no fly will ever qualify. ⚠️ MUST BE QUERIED FROM S3, NOT CONTROL: the operator has purged control's chain data (2026-09-01), so `chain_marks`/`greeks_series` in the bucket back to 08-22 are the only source. Question: how many qualifying wings existed per symbol per session at 12:00. Sets the constant from data instead of from argument. |
| **BFLY.10** | Charm vs. butterfly outcomes. | ⬜ | Operator, 2026-09-01: "later, we are going to look at what charm was doing for all of our winners and losers." NO BUILD NEEDED — `derived/snapshot.py:99` already writes charm onto the fire snapshot and `_capture_fire_snapshot` runs on every fill (r144), so this is a join, not a collection problem. |
| **ORB.1** | Could ORB select long contracts via an OTM gamma play scaled by breakout/retest strength? | ⬜ | Operator's open question raised 2026-08-28 before r181 landed. Agreed to bring the design **after a session of r181 fills**, with the delta-aware geometry interaction for him to rule on. Filed here so it does not live only in a thread. |

### Awaiting an operator ruling

| ID | question | status |
|---|---|---|
| **ASK.1** | ✅ **RESOLVED — `character_axis_sample` IS PUSHED.** | otv4 r270 / dtp r292 | ◐ **BUILT + PUSHED.** Operator ruled 2026-09-05: push it. Append-only and keyed `(symbol, ts_epoch)`, so it joins `DERIVED_SERIES_TABLES` on the HIGH-WATER path rather than CDC. 🔑 **IT IS THE ONLY SURVIVING OUTPUT OF THE CHARACTER ENGINE:** r85 set `BANDS_SET=False`, so `character_ledger` records no transitions and pushed **0 boxes** in the 2026-09-05 census — and `character_engine`'s own comment states the consequence: *"the sample IS the deliverable right now — one session of real efficiency values is what the bands get derived from."* Holding the bands back was the reason for collecting it, and leaving it on the box meant the corpus the bands are derived FROM had no durable home. It carries `efficiency`, `vol_ratio`, `close_capture`, two realised-vol estimators, `adx`, `atr_normalized` and `price` — a feature vector, and STRIDED rather than per-tick, so it is a small stream. ⚠️ **SHIPPED WITH ITS PURGE ENTRY AND ITS COVERAGE ROW.** It was in NO list — neither purged nor protected — the same by-absence exposure as S3.15; and an undeclared stream renders UNDECLARED and fails the board on night one. `CONDITIONAL`, not `EVERY`, because a strided writer on a thin session legitimately produces none. |
| **ASK.2** | 🔴 **PREMISE FALSIFIED — `shadow` IS LIVE.** The question was *"shadow/ still ships to the boxes and `s3_push` still runs a shadow stage, but shadow was never installed on the v4 fleet — cut both, or leave?"* **The never-installed finding is wrong.** Measured on QQQ 2026-09-05: **32 date directories, newest 2026-09-04, and a shadow systemd unit present.** The bucket agrees from the other side — 15 boxes push it every session, and `WAREHOUSE_MAP.md` (generated 09-01) shows `raw/shadow` at 160,978 objects across 7 days. So the ruling is no longer *cut a dead stage or leave it*; it is **keep collecting a live stream, or stop it deliberately** — a different question with a different cost. | ⬜  🔴 **SETTLED 2026-09-05 — SHADOW IS THE FITTING CORPUS, AND STAGE 2 IS ARMED.** Operator: *"I am looking for market intelligence. What indicators recorded the earliest sign a tradeable move was imminent. The shadow data will tell us what primitives we should be fitting our trade triggers on and what exhaustion signals were appearing on the tape to better inform our stops. It should be fitting data."* 🔴 **AND IT WAS ONLY HALF COLLECTING.** Measured 2026-09-05, all 15 boxes: `"stage": 1`, `scores: []`, **zero scorer entries** — seven weeks of primitives with NO counterfactual. `OT_SHADOW_STAGE=1` is the de-risk default meant to hold "for a few sessions" and nothing ever forced step two; **same shape as the retention purge logging "WOULD remove" for two months (r162)**. What the period DOES hold is real and answers half the question: per tick, `current_roc` vs `typical_roc`, `atr_normalized`, `bb_width_pct`, `price_vs_bb` and nearest-level distance in pct AND ATR. What it cannot hold is `stages`, `conviction`, `invalidated` and `would_fire` across ten thresholds — the tape is gone. **Armed by drop-in on all 15 the same day; r265 moves the unit default so a re-install cannot revert it.** |
| **ASK.3** | ✅ **RESOLVED — EIGHT SPENT THREAD CONTRACTS DELETED, ONE MEASUREMENT LIFTED.** | r269 | ✅ **CLOSED.** ~89 KB / ~1,700 lines across `AUDIT.md`, `AUDIT_HANDOFF.md`, `AUDIT_FINDINGS.md` and five `HANDOFF_*` docs. Read before ruling: `AUDIT.md` is a DELIVERY CONTRACT whose every constraint `land.sh` and §15 now enforce mechanically; the five handoffs are REQUESTS whose work landed and which say so in their own opening lines (*"RESOLVED — r146"*, *"Ships with…"*). 🔑 **ONE DURABLE FACT WAS BURIED IN THEM** — v3's central premise measured FALSE: 715 closed directional trades over 16 sessions, the regime classifier picking the correct SIDE on **44.9%, 95% CI [41.3%, 48.6%]**, entirely below a coin flip; puts 34.2%; plus the P&L attribution that produced the v4 thesis. ⚠️ **IT DID NOT GO TO THE BACKLOG** — operator: *"backlog is deferred work"* — and not to an archive, which is where documents go to stop being read. It is in `config.py`'s **INHERITED DOCTRINE** block, which WA §32 requires be read before that file is edited. ⚠️ **AND DELETION WAS NOT FREE:** six live citations pointed into these files and were redirected first. |
| **RUN.1** | 🔴 **IS ONE RUNAWAY PER BREAK MEANT TO INCLUDE WINNERS?** r174's ruling reads *"one runaway per break, even on relaxed"*, but `finish_break` is called ONLY from the losing-exit hook — so a WINNING exit leaves the break live and the next tick re-enters. QQQ 2026-09-03 shows both halves: 09:52 trail **+$96**, then 09:53 re-entry stopping **−$204**; 10:16 trail, then 10:21 re-entry. ⚠️ **AND THE UNDERLYING CONDITION IS A STATE, NOT AN EVENT** — `_closed_beyond_and_held` is `prev_close > tp50 and price_now > tp50`, which stays true for as long as price remains beyond the 50%, so the trigger re-qualifies on every tick. Operator, 2026-09-03: *"the condition to enter is so loose that it will reenter a position as soon as the previous one closes, as long as it closes beyond the 50% boundary."* Options: (a) finish the break on ANY resolved runaway, win or lose; (b) require a fresh event — a pullback and a new close-and-hold — rather than the standing state; (c) cap attempts per break. **This alters what gets traded, so it is the operator's call**; r223 fixed only the key defect that was masking it. | ⬜ |
| **ASK.4** | `debug_status.py` and `stress_theta_bleed.py` sit at repo root. Move to `tests/` per WA §28, or are they entry points? | ⬜ |

### THE THREE REPORTS — operator's stated end state, 2026-09-02

⚠️ **THESE THREE ARE THE DESTINATION, NOT THREE TICKETS.** Each answers a
question the other two cannot, and the operator's framing is that conflating
them is the failure — a "good trade" today is a compound of entry, stop and
management, and no single number separates those.

| id | goal | state |
|---|---|---|
| **RPT.A** | 🔑 **ENTRIES — WHAT SEPARATES A GOOD ENTRY FROM A BAD ONE, PER STRATEGY.** Operator, 2026-09-02: *"I want to be sure that we don't conflate success entirely on the work of our stops."* So the outcome variable is **NOT P&L**: it is whether the entry was **directionally correct long enough to start out in profit** — MFE above entry — and *"whether it remained there is a separate question entirely, not for this report to decide."* That is NF.1's never-favourable line used as the DEPENDENT variable rather than as a footnote, and it is the one outcome the stop cannot manufacture. ⚠️ **THE VECTORS ARE NOT CHOSEN YET AND MUST NOT BE ASSUMED.** Operator: *"could be a 1-hr pitchfork, or maybe ATR/ADX or VWAP — who knows?"* and he is prepared to query the bucket repeatedly to find candidates. Everything on `fire_snapshot` is available at fill: adx / primary_adx, atr / atr_normalized / bb_width_pct, realised_vol_cc / realised_vol_parkinson, atm_iv, variance_risk_premium, price_vs_vwap, levels, fork / fork_state, charm, vanna, gex / net_gex, iv_slope, expected_move_iv / expected_move_straddle, session_fraction_remaining, gap / gap_pct / gap_class, trend_direction, overall_direction. ⚠️ **AND THE SAMPLE CAPS THE SEARCH:** the limiting figure is the smaller outcome class, at 10-20 events per variable — the candidate hunt is legitimate, but the CONFIRMING set must be named before it is tested or it is a fishing licence. | ⬜ |
| **RPT.B** | **MFE/MAE — ARE THE STOPS TOO LOOSE OR TOO TIGHT, AND WHAT SIGNALS AN EXIT.** Comprehensive, **per stop TYPE** rather than per strategy. Two halves: (1) placement — the heat WINNERS survived is the strongest available evidence about where a stop belongs, and if winners routinely take more than the stop allows then the stop is manufacturing the left tail (measured 2026-09-02: 21 of 22 runaway losses fell between −20% and −32%, σ 4.4 points — that is a threshold, not a market outcome); (2) corroboration — vectors that signal *a move is exhausted* or *a breach is imminent*. 🔴 **THE HARD PART IS THAT THESE MUST MOVE WHILE THE TRADE IS OPEN**, and `fire_snapshot` is FILL-TIME ONLY. Candidates that actually change intra-trade: `price_vs_vwap` crossing back, `adx` rolling over, `charm` at the strike, and the **sign of `net_gex`** — the flip from dampening to amplifying, the closest thing on hand to "the reason for this trade stopped being true". Requires joining `surface_series` and `indicator_series` by timestamp BETWEEN entry and exit. That is a build, not a column read. | ⬜ |
| **RPT.C** | **MANAGEMENT — THE CONDOR PLAN, WHICH IS NOT A STRATEGY.** Operator, 2026-09-02: the condor *"is not a standalone strategy, but more so a position management 'strategy' due to the special nature of how we intend to defend it"* — so it cannot be judged by the same measures as ORB or the runaway. 🔴 **AND NO CONDOR HAS FORMED TO DATE.** The question the study must answer is whether that is **the design protecting us** or **too strict to allow one to form**, and those two look identical from the outside — which is exactly why it needs a study rather than an opinion. Both halves are checkable: `plan_ledger` records every leg-one fill and its terminal state, and `gate_disposition` records which rung refused leg two, so "never got a first leg" and "got a leg and never paired" are distinguishable. ⚠️ Operator: *"that third one is going to take some teamwork and creativity"* — design it together before building. | ⬜ |

### FLEET MEMORY AND OPEN INTEREST — measured 2026-09-02

| id | finding | state |
|---|---|---|
| **MEM.1** | 🔴 **THE PRIMARY EXPIRY CHAIN IS NOT BANDED; THE AUX TENORS ARE.** `options_chain.publish` writes every listed `streamer_symbol` for the session expiry into `chain_subs`, while TERM.1 caps each aux tenor at ~9 strikes. MU lists **356 contracts spanning $450-$1370 against a $950 spot** — ±45%, most of it 30%+ OTM and untradeable by anything in the book. MEASURED 2026-09-02 against CVX, same uptime (5.96 h): MU `candle_feed` **117 MB vs CVX 28 MB — 4.2x**; MU bot 233 MB after 49 MINUTES vs CVX 180 MB after SIX HOURS. MU was OOM-killed at 14:20 ET (`Failed with result 'oom-kill'`, status 9/KILL). ⚠️ **AND THE CONSTRAINT WAS ALREADY UNDERSTOOD** — options_chain.py's own doctrine block says full chains would blow the subscription cap and *"SPX has already been OOM-KILLED at 419 MB on chain volume"*, then bands only the aux tenors. ⚠️ **NOT A LEAK — MEASURED AND REFUTED TWICE.** Twelve samples over 2.75 min: 242.7 → 244.2 MB, peak-to-trough 1.45 MB, drift 0.53 MB/min (~32 MB/h, ordinary heap growth). No spike, no runaway. A high baseline on the fleet's tightest margin (112 MB available vs 343-476 elsewhere) is the whole story. **OPERATOR RULING 2026-09-02: UPGRADE MU**, as SPX already was. Banding the primary chain stays open as a separate question — it would help every 951 MB box, and it risks hiding a strike the wing search legitimately walks out to. | ⬜ upgrade agreed  🔴 **BANDING RULED OUT 2026-09-05 — DECIDED, DO NOT RE-LITIGATE.** Operator: *"I like #1 the best and it will let us know soon if the checkpoint ever fails to run again. Let's close it out as decided — leave it."* 🔑 **THE UNBANDED CHAIN IS NOW A CANARY, AND THAT IS THE ARGUMENT.** Store growth is the fastest visible signal that the nightly reclaim has stopped running; band the chain and a silent failure hides behind a smaller footprint for weeks. Same shape as gating the alerting while leaving the detection on. ⚠️ **AND THE LEVER WAS SMALLER THAN IT LOOKED** (S3.16): chain width explains only ~4x of a 15x spread, and the strikes banding would remove are the deep-OTM ones that barely quote, so the reduction would be well under the contract count. ⚠️ **AND IT HAD A REAL COST:** `compute_gex` walks the WHOLE chain for `call_wall`/`put_wall`, and r215 deliberately left the walls unbounded — *"a wall IS allowed to be far away, that is what makes it a wall."* A band would have truncated the gamma surface and quietly weakened a signal the sweep reads for confluence. **The disk is solved by the nightly reclaim (S3.15/S3.17); the chain stays as it is.** |
| **OI.1** | 🔴 **OPEN INTEREST HAS NEVER WORKED IN v4, IN TWO STAGES.** v4.0 called `get_market_data_by_type` — a coroutine function — WITHOUT `await`; `for r in rows` raised `'coroutine' object is not iterable`, the broad `except` logged it as a warning, and nobody chased it. v4.1 added the missing await via `_await`, which fixes the syntax and inherits a LIFECYCLE fault: `_await` calls **`asyncio.run`, which creates a NEW event loop and closes it**, while `session` is the long-lived SDK session created once at startup and holding loop-bound primitives. The log names one: `<asyncio.locks.Event object at 0x…> is bound to a different event loop`, then `Event loop is closed` once that first loop is gone. A session built in one loop and driven from N others cannot work by construction. ⚠️ **`_BATCH = 100`, so a 356-contract chain is FOUR calls** — which is why this is MU-only in the fleet (2 occurrences in 30 min on MU, **zero on all fourteen others**): a narrow chain makes one call and the 300 s `_RETRY_S` backoff hides the rest. 🔑 **CONSEQUENCE: GEX IS A GAMMA-SQUARED SURFACE, NOT DEALER POSITIONING**, on any box where those batches fail — the file's own header already says so. FIX: one loop for the session's lifetime (`run_until_complete`), or build the session inside the loop that drives it. ⚠️ Touches a live data path on all fifteen boxes — build it against a stubbed SDK session and land it deliberately, not mid-session. | ⬜ |

### MOM.1 — MOMENTUM PARTICIPATION: THE STAGED BUILD (2026-09-03)

🔑 **THE TRADE.** ONE position held through a decided trend, replacing N
re-entries with one. Its bones are `RunawayContinuation`; the management plan
that watches every tick and feeds execution is the new part. **Built INSIDE the
runaway for now** — operator's ruling: designing for carryover first *"would
constrain our creativity at the moment"*, and a thing that works once is easier
to lift than an abstraction built for callers that do not exist.

🔴 **THE EVIDENCE IT EXISTS.** QQQ 2026-09-03, 11:03-11:12: **+$1,098.50, +$42,
+$406, +$357 — four entries, four exits, one move.** Operator: *"we didn't have
to exit any of those trades, in fact it should have been 1 entry on a strong
trend."* FRC.1 puts the fleet's gross edge at ~2% of its own round-trip spread,
so four entries pay the spread four times for one trend.

🔑 **THE INSIGHT THAT ORDERS THE WHOLE BUILD.** Strength is not one dial. It
sets the **entry gate**, the **strike (via delta)**, and the **initial stop
width** — and **exhaustion**, a SEPARATE meter, contracts that stop while the
position is open. Exhaustion is NOT the absence of strength: a tape can be
strong and exhausting at once (efficiency 1.00, acceptance collapsing) which is
exactly a top. One score averages those to "moderately strong" and says
nothing; two meters DISAGREEING is the signal.

🔑 **AND THE GREEKS CARRY THE ROLES.** Near the money is DELTA — converts now,
participates linearly, does not need continuation. Further out is GAMMA —
converts AS the move extends. That is the difference between "this might work"
and "this has committed", which is what strength measures. **Strength selects
the delta; gamma follows; theta is what exhaustion pays for.** Vega is ignored
deliberately: small on 0DTE, and optimising against it fits IV rather than tape.
⚠️ Further OTM is CHEAPER, so the same dollar budget buys MORE contracts —
strength buys room and size TOGETHER instead of trading one for the other.
⚠️ A barely-qualifying signal takes a near-the-money strike and so participates
in a small move; the contract selection itself refuses to reward a weak read
before any stop logic engages.
⚠️ **THE PIN IS NOT THE TARGET** (considered and rejected): a destination is the
wrong frame for a momentum trade. But the butterfly and this trade COMPETE FOR
NOTHING — a gamma-squeezed run into a pin serves both, the call on the traverse
and the fly on the settle. See stage 8.

**STRICT DEPENDENCY ORDER. Each stage needs the one above it established.**

| # | stage | needs | state |
|---|---|---|---|
| **1** | **STRENGTH, CALIBRATED.** 🔴 **FIRST RUN NEGATIVE (2026-09-03, 183 runaway trades):** every component under the noise floor — best AUC **0.63** against 0.65 guidance; at a 0.40 gate you refuse 109 of 183 to move the green rate **3 points**, and at 0.50 the rate is BELOW baseline. **DIAGNOSIS: the outcome was wrong, not necessarily the meter.** "Went 5% green" had a **74% base rate** (136/183) — a near-universal event leaves nothing to separate — and it is the wrong question for MOM.1 anyway, since five trades made 97% of the runaway P&L and going 5% green is not what those five did. **r229/r259 re-run:** outcome is now a sample QUANTILE ("did it run"), plus acceptance TRAJECTORY (slope / recent-vs-whole / consecutive) and FVG CONTINUATION. Does any component discriminate; settle the leg definition. `trend_strength` (r224) + `calibrate_trend_strength` (dtp r257). **EVERYTHING BELOW ANCHORS HERE** — if it cannot discriminate, 2-9 are moot and the runaway needs a different idea. | — | ⬜ |
| **2** | **GREEKS TRUST.** Is per-contract delta/gamma trustworthy? OI.1 says the GEX SURFACE is gamma-squared, which may or may not touch per-contract greeks. `greeks_series` is 4 GB, scopeable since dtp r253. **CAN INVALIDATE 3, 6 AND 7**, so it comes early. | 1 | ⬜ |
| **3** | **STRENGTH → DELTA.** Recorder first: log the delta a strength WOULD have chosen, gate nothing, calibrate against outcomes. | 1, 2 | ⬜ |
| **4** | **INITIAL STOP FROM STRENGTH.** The stop cannot be expressed until the contract is known — a 0.20-delta and a 0.45-delta strike need different units for the same underlying move. RPT.B already argues for it: 21 of 22 runaway losses fell between −20% and −32%, σ 4.4 — a fixed threshold defining the entire left tail. | 1, 3 | ⬜ |
| **5** | **EXHAUSTION METER.** Four components, none overlapping strength's: acceptance decay, range expansion without progress, upper-wick growth, distance from anchor in ATR. NO oscillators — the screen killed that family at AUC 0.47-0.51. | 1, 4 | ⬜ |
| **6** | **STOP CONTRACTION.** Per-tick, **RATCHETS IN ONLY, NEVER BACK OUT** — that is what stops a wide initial stop becoming a bigger loss. Open: may exhaustion force an exit, or only tighten toward one? | 4, 5 | ⬜ |
| **7** | **THETA GATE.** "Am I still paid for the decay I am eating?" Most consequential on the far-OTM strikes stage 3 selects, and possibly more important than the stop. | 2, 3 | ⬜ |
| **8** | **SLOT COMPATIBILITY.** Dispatch does not know the butterfly and this trade are the same bet — `GEXPinButterfly NOT ASKED — slot claimed by RunawayContinuation` on SPX and QQQ both. Two positions on one thesis is a PLAN-ARCHITECTURE change, not a strategy change. | trade fires | ⬜ |
| **9** | **LIVE PATH.** Ladder, fill basis, sizing; inherits r220. **Last because it is the only stage where being wrong costs real money.** | all | ⬜ |

⚠️ **WHY 5 SITS AFTER 4 AND NOT BEFORE.** Exhaustion calibrates against WHEN the
favourable excursion peaked (`mfe_bars`). On trades cut at −20% by a fixed
threshold, MFE peaks are truncated by the STOP rather than by the market —
calibrating exhaustion on that sample would fit it to the stop being replaced.

⚠️ **CARRYOVER IS DEFERRED, NOT FORGOTTEN.** Strength and exhaustion are
management primitives: ORB wants strength for re-arm quality and exhaustion for
the early exits (2026-09-03 NVDA); the condor is management by definition and
exhaustion is when to defend a tested side; the butterfly wants exhaustion
INVERTED — an exhausted move near a pin is a BETTER fly. Lift it once it works.

---

## PART 2 — CLOSED

| ID | item | closed | outcome |
|---|---|---|---|
| **DOC.1** | `tests/scrub_headers.py` had not parsed since r65. | r182 | ◐ **PUSHED.** r65's header pass matched the `v4.3` inside an **illustrative comment** in `_autodescribe()`, mistook it for the file's own version line, spliced a four-line changelog into the middle of it and stranded the tail at column 2. The real header was never touched and still read v4.0. Restored verbatim from `dfe5910`. **Born-red proof: `gen_file_map.py --check` rc=1 at `0241cb9`, rc=0 after.** |
| **DOC.2** | `docs/BACKLOG.md` did not exist. | r182 | ◐ **PUSHED.** WA §18 mandates it in every archive and `analysis/trade_readiness.py` references it. This file. |
| **S3.1** | Three derived series had no push stage — and a purge that deletes them. | r191 | ◐ **BUILT + PUSHED, AWAITING BAKE.** `fork_series`, `indicator_series`, `surface_series` now ship via a second `push_series` call against `DERIVED_DB`, own ledger (`dseries_ledger.json`, namespace `dseries|`) because sharing the candle or CDC ledger is the r82 two-meanings-one-dict class. Key layout unchanged (`raw/<table>/dt=/sym=/`) so `warehouse_source.load_series` reads them with no reader change. 🔴 **THE FIND: `retention_purge` DELETES ALL THREE AT 20 DAYS AND HAS BEEN ARMED SINCE r162** — the same unwarehoused loss v4.2 fixed for the feed series, one store over. ⚠️ **AND `check_purge_pushed` COULD NOT SEE IT**, because that purge list was a HARDCODED TUPLE inside `purge()` while the checker imports `ARTIFACT_DAYS`. Promoted to `DERIVED_ARTIFACT_DAYS`; C9/C10 now cover it by execution, born red 2/2 at `54e72a4`. Purge policy itself UNCHANGED — same tables, same 20 days. |
| **ORB.3** | ORB entry window 11:00 — 11:30. | r193 | ◐ **PUSHED.** Gates PLACING, not resting. 🔑 Lands EXACTLY on the debit block — both tests are `>=`, ORB declares `long_debit`, `DEBIT_DIRECTIONAL_CUTOFF_ET` is 11:30 — so entries run to 11:29:59 and the block takes over at 11:30:00, no gap, no overlap. ⚠️ Not only a later deadline: the constant also sets `entries_expired` and expires the engine from ANY state, and r60 made the re-arm check read it, so it buys 30 more minutes of breaks, retests and RE-ARMS. Two stale copies fixed (`cascade_harness.py`, `cascade_real.py`) and `tests/check_orb_window.py` W3 now pins EVERY declared copy against config, so a fourth cannot appear quietly. |
| **ORB.4** | Pool in path becomes RECORD-ONLY. | r193 | ◐ **PUSHED.** The named-pool target pull is gone; the target is the pure measured move. Detection, the counted clusters and the notes all stay — the note now names the pool and what the target WOULD have become, so the counterfactual survives for the later study the operator asked for. ⚠️ The pull was a grading-era survivor that CHANGED WHAT THE TRADE DOES while reading like an annotation. |
| **ORB.1** | **r181 shipped INERT: ORB has sized 1 lot since the 08-28 bake.** Sizing normalized into one handler and the geometry ACTIVATED. | r192 | ◐ **PUSHED.** `RiskManager.size_for(structure, ...)` is now the single door, dispatching on the strategy's declared `structure` — the same key `_afternoon_debit_blocked` uses, never a name list, because a name list rots permissively (the RunawayContinuation exemption). Four rules: budget, butterfly, vertical, and `orb_geometry` as a sub-rule of long_debit selected by SUPPLYING width/stop-distance. 🔑 **THE FIX IS STRUCTURAL:** every rule returns a `SizingResult` and the order reads only `SizingResult.contracts`, so "the sizer computed one thing and the order sent another" is now unrepresentable. The r181 override is DELETED from `main.py`, not rewired. ⚠️ `entry_engine.py` needed NO change — it already ordered `sizing.contracts`; the sizer was what wasn't answering. Parity **25/25** against a golden table captured from r191 BEFORE the edit. New `SizingResult.rule`. |
| **S3.6** | Two dedup rules ran on the same data with different tie-breaks. | r190 / dtp r231 | ◐ **PUSHED. THE HIGHEST-VALUE REMAINING CORRECTNESS ITEM, CLOSED.** The shim was never a design feature — its own v1.1 changelog says it existed only to survive pre-07-28 CUMULATIVE bundles, and r187 moved the source to `reports/warehouse` where every bundle is one dt= partition already collapsed by `latest_per_trade()`. 🔴 **KEEPING IT WAS THE DEFECT, NOT MERELY DEAD CODE:** `warehouse_reader` kept the newest `pushed_at_utc`, `trade_report` kept the MOST-FILLED row (`_filled()`), and they agreed only because the newest state also happened to be the fullest. **That is luck**, and report parity could never have caught it because parity runs both sides through the same rule. ⚠️ **NOT DELETED — INVERTED.** Duplicates are now FIRST-WINS by sorted filename and **reported by trade_id AND by file**, because the two conditions that can still cause one (a legacy cumulative bundle in an explicit `--bundles-dir`, or two bundles on one date) are real problems v1.9 absorbed without a word. `_filled()` removed outright, not orphaned. `tests/test_trade_report_dedup.py` v1.0, 5 cases, **born red 6/6 at `356d3f9`**. |
| **S3.4** | The excursion report scored v4 trades against v3 categories. | r189 / dtp r230 | ◐ **PUSHED. RETIRED AND ITS ONE UNIQUE MEASUREMENT REBUILT.** Both menu items go (local and the FROM THE WAREHOUSE twin — one script, so retiring it from one source and keeping the other would be moving the problem). `r_ledger` v1.2 gains the **SELECTION vs EXTENSION split**: never-favourable (no exit rule can save it) against gave-it-back (the entry was right, the management was not), at the same 0.00/0.02/0.05 cuts so the two tools' numbers stay comparable while both still run. 🔴 **THE THIRD BUCKET IS THE PART THAT MATTERS:** a row with no excursion telemetry is UNMEASURED, not never-favourable, and is counted on its own line — folding them together would turn missing instrumentation into a selection finding. Selftest extended with planted rows whose three buckets have different known answers, **born red** when `fav_frac` is made to return 0.0 instead of None for a blind row. |
| **RPT.2** | The R baseline could not be asked for on demand. | r189 / dtp r230 | ◐ **PUSHED.** `r_ledger` ran only inside the nightly conductor, which Telegrams a headline. Now a menu item via the existing `_r_tool`, no new plumbing. |
| **MENU.1** | TRADES DATA and R SUITE were two sections over one population. | r188 / dtp r229 | ◐ **PUSHED.** Operator: *"TRADES DATA should be merged with R SUITE"* and *"the control side comment is unnecessary — I'm aware our data is on s3."* Now one section, **TRADES DATA & R SUITE**; the `(control-side, reads S3 — boxes untouched)` qualifier described a migration rather than a property and is gone. **Every number after the fleet section shifts and that is free by construction** — `menu_extract --diff` confirms 0 labels removed, 0 added, 0 commands changed, 6 harmless section moves. Also fixed: the Trade breakdown LABEL still advertised a `grade` dimension r187 removed. |
| **S3.5** | Menu 56 read a directory nothing writes, and pooled two engines. | r187 / dtp r228 | ◐ **PUSHED.** Three changes. (1) **Default source is `reports/warehouse`** — the old default globbed the repo root, which `eod_analysis` v1.2 and the disabled harvest stopped filling (C.12); a default pointing at a dead folder does not fail, it **quietly reports old numbers**. (2) **Engine epoch, default 2026-08-25**, `--all-history` to override, and the count of excluded pre-epoch trades **prints every run** — a filter you cannot see is how you argue about a number that was never in the sample. An explicit `--since` before the epoch is HONOURED but flagged red. (3) **BY SETUP GRADE removed**: every v4 path hardcodes `UNGRADED` and nothing writes `setup_score`; the column stays (check_conviction_removed S6 pins it), only the dimension goes, replaced by one line of fact. `report_parity` v1.5 now passes `--all-history` on both sides so its printed "comparing over N shared dates" claim stays true. `tests/test_trade_report_epoch.py` v1.0, 6 cases, **born red 13/13 at `b08261e`**. |
| **S3.3** | The nightly EXCURSION phase had **no source at all**. | r186 / dtp r227 | ◐ **PUSHED.** `_consolidate` was pointed at S3 and writes to `reports/warehouse/`; one phase later `_excursion` still ran `excursion_report.py --date <date>` with no `--bundles-dir`, taking the per-box-DB path into `trades/<date>/` — **which `install_eod_v2.sh` stopped populating when it disabled `dtp-harvest.timer`**. The root-bundle fallback is not written either. Both sources gone, so it exited 1 **every night** with a warn-never-stop warning nobody chased. Now passes `--bundles-dir warehouse_reader.WAREHOUSE_OUT`, absolute, and checks the bundle exists first so a CONSOLIDATE failure reads as one. `tests/test_eod_excursion_source.py` v1.0 — case A pins the broken world and **stays red forever by design**. |
| **DOC.5** | WA §25 pointed at `docs/README.md`, never ported from v3. | r186 | ◐ **PUSHED.** The one rule whose job is to stop documents going unread was routing to a missing document, in a section written because two days of work were lost to unread docs. Replaced with a four-document reading order that all exists, plus the by-question index; the rule the missing file carried — **do not create a new doc** — restated in place with §33/§35 as evidence. WA gained a version line (DOC.9). |
| **DOC.10** | `excursion_report` **destroyed its own provenance line and called a deliberate source DEGRADED.** | r186 / dtp r227 | ◐ **PUSHED**, found by a fixture while wiring S3.3. v3.2 stamps `[SOURCE: WAREHOUSE via <dir>]` onto `src`; `build_report` rendered `src if "(" in src else os.path.basename(src)`, that string has no `(`, so basename split it on `/` and printed **`source: warehouse]`**. The same test drove `SOURCE DEGRADED: per-box DBs absent` — which, once S3.3 makes a bundle the INTENDED source, would have opened every nightly report by calling its own canonical input degraded. **A warning that fires when nothing is wrong is how you learn to skip the one that matters.** v3.5 keys both on whether `--bundles-dir` was EXPLICIT; an explicit run now says SOURCE CHOSEN with the one real caveat. |
| **DOC.4** | `README.md` claimed *"Fleet: 15 traders, 29 collectors. Collection is fleet-wide."* | r185 | ◐ **PUSHED.** False since the 2026-08-20 pare TERMINATED the other 14. r74 corrected the identical sentence in `ROADMAP.md` S.4 and WA §30 on 08-22 and **missed this copy** — three documents carrying one fact, and the front page was the one that rotted. **Four further staleness fixes found reading it end to end** (WA §5 requires that of any edit): the setup scorer is DELETED at r152 rather than merely absent; the LAYOUT table was **missing five of fifteen directories** and now defers to the generated `FILE_MAP.md`; WORKING_AGREEMENT no longer "carries over verbatim" (§26–§37 are v4-era); a reading order was added. A version line was added so the file is gateable at all — see DOC.9. |
| **S3.2** | `fit_readiness.py` sourced from a box path that does not exist on control. | r184 / dtp r226 | ◐ **PUSHED.** Menu **57 produces a number on control for the first time.** `warehouse_reader` v1.7 gains `load_derived()` (CDC collapse latest-per-(symbol,_rid) by `pushed_at_utc`); `fit_readiness` v1.1 defaults to S3 with `--db` kept as the explicit on-a-box escape hatch. **One aggregator, two sources** — `collect()` takes plain dicts and cannot tell them apart, proven by a row-for-row parity assertion. Also fixed in passing: v1.0 bounded its window with NAIVE LOCAL time on a UTC box, so "2026-08-25" meant 20:00 ET on the 24th — the operator's own "a report for today run after the close fails". Both paths now bound on the ET trading day. `tests/test_fit_readiness_s3.py` v1.0, 6 cases, born red at `438c827` (AttributeError — the loader did not exist). Full dtp suite unchanged before and after. |
| **GATE.1** | Nothing verified that a delivery bumped its headers, wrote its changelog, appended its GENESIS row, or regenerated its maps. | r183 / dtp r225 | ◐ **PUSHED.** `day_trader_pro/tools/check_land_discipline.py` v1.0 — one tool, both repos, capability-detected (dtp has no GENESIS or maps; those report **SKIP by name**, never a silent pass). Selftest is **7 born-red cases + a positive control, 7/7**. Replayed over r162–r182: **zero false positives on correct deliveries**, and it found the real misses now filed as DOC.6/DOC.8. Optional pre-commit hook via `tools/install_land_hook.sh`. ⚠️ **It proves the BOOKKEEPING, never the truth of the edit** — see C.7. |
| **DOC.3** | `FILE_MAP.md` and `WRITE_MAP.md` existed **twice** — repo root and `docs/`. | r182 | ◐ **PUSHED.** Both generators write to `docs/`; nothing read the root pair. They were last written at r160 and had gone stale: root `FILE_MAP.md` claimed **190 modules** against `docs/`'s **198**. Deleted per WA §28 and the SHIPPING_LOG lesson in WA §35 — *two documents claiming the same job, and whichever gets updated becomes the truth while the other rots.* |

---

## PART 3 — STANDING CONSTRAINTS REGISTER

**WICKS ARE TESTS, CLOSES ARE ACCEPTANCE** — operator's doctrine, 2026-09-03,
applied repo-wide. A wick through a level TESTS it; a CLOSE beyond ACCEPTS it.
Audited at r221: 17 candidate sites across `liquidity_mapper` and `orb_engine`,
and both already honour it — sweep detection is wick-based **correctly** (a
sweep IS a wick through liquidity), the ORB retest requires a wick in with the
body outside, and the break latch is close-only. The 50% TP was the only place
with NO test either way, which is what r221 adds.

**A RETEST IS NOT A RE-ENTRY.** RETEST = wick into the range, close back
OUTSIDE — a test, fires a trade, leaves the impulsive candle intact. RE-ENTRY =
a CLOSE back inside — acceptance, terminates the thesis, a fresh break must set
a new impulsive candle.


Facts that are not tasks. They bound future work and are recorded so they are
not rediscovered the expensive way.

| ID | constraint | established |
|---|---|---|
| **C.1** | **19 of 27 tables reach S3.** Missing: `fork_series`, `indicator_series`, `surface_series`, `character_axis_sample` (candidates) and `chain_marks`, `chain_subs`, `chain_subs_aux`, `feed_meta` (plumbing, not candidates). | 2026-08-29, measured against `docs/WRITE_MAP.md` + `warehouse/s3_push.py` |
| **C.2** | `push_series()` is bound to `FEED_DB`. Any derived-store series needs its own call and its own namespaced ledger key — two shapes in one ledger dict is the r82 failure class. | 2026-08-29 |
| **C.3** | `excursion_report.py --since` is **refused** without per-box DBs. Cumulative windows from S3 require `reports/warehouse/` populated per date. | 2026-08-29, read from source |
| **C.4** | The land gate globs `tests/check_*.py` only. `gen_file_map.py` and `gen_write_map.py` are run by the land command but **their rc is not part of that glob** — which is how DOC.1 survived six days of red runs. | 2026-08-29 |
| **C.5** | A version-bumping script **cannot distinguish a file's own header from a header quoted as an example**, and this repo's docs are full of quoted headers by design. Anchor on position or an explicit marker, never on a `vX.Y` pattern found anywhere in the file. | r182 (DOC.1) |
| **C.6** | `docs/GENESIS.md` is never in a tarball (WA §35) and `docs/BACKLOG.md` is in **every** tarball (WA §18). The two rules point opposite ways on purpose: Genesis is append-only on the box, the backlog is authored here. | WA, restated r182 |

| **C.18** | 🔴 **THE PURGE JUSTIFICATION FOR THE DERIVED SERIES WAS PARTLY FALSE AND IS RETIRED.** It read *"pure functions of the candles, so trimming them costs a recomputation and nothing more"*. Two objections: a recomputation says what TODAY'S CODE would have produced, not what the bot ACTUALLY SAW — and those differ exactly when there is a bug, the only time anyone looks (the operator's own ORB-state argument); and **`surface_series` is not a function of the candles at all**, it comes off the options chain and `greeks_series`, and chain snapshots are explicitly not reconstructible after the session. The purge stands because the disk cost is real; it is now safe because the data is warehoused first. | r191 |
| **C.19** | ⚠️ **`check_purge_pushed`'s COVERAGE IS BOUNDED BY WHAT THE POLICY EXPOSES AS A CONSTANT.** It proves its invariant by IMPORTING the purge lists. Any future purge written as a literal inside a function is invisible to it and will pass green while deleting unwarehoused data — which is exactly what happened here, for as long as the purge has been armed. | r191 |
| **C.20** | `gen_write_map` cannot see a table read through a DYNAMIC name. `push_series` builds its query with `%s` from a variable, so `WRITE_MAP.md` does not list it as a reader of the ten series tables. Not a defect in this change; a limit on what the map can claim. | r191, observed |
| **C.39** | 🔴 **A REPORT THAT READS DEFAULTS LOOKS EXACTLY LIKE A FLEET THAT IS UNCONFIGURED.** Fifteen rows of `QQQ / 200 / (DEFAULT)` is a plausible finding, not an obvious error — and the on-disk columns beside it were correct, which made the table read as trustworthy. **An environment-derived figure must name the layer it came from, or it cannot be distinguished from a real reading.** The script now reports `unit unreadable (figures would be DEFAULTS)` per box rather than silently falling back. | r206 |
| **C.37** | 🔴 **A VALUE COMPUTED INTO A LOCAL IS A VALUE THROWN AWAY.** `atm_iv` was calculated correctly, twice, in two dispatch branches — and both bound it to `_atm_iv` and passed it to one caller. Everything else downstream got the `setdefault(None)`. **Computing a quantity is not the same as recording it**, and the fleet ran for weeks with a field that was present, named and empty. Two computations of one quantity in one tick can also disagree, which is the bug nobody would ever find — so there is now ONE conversion and both branches read it. | r205 |
| **C.38** | 🔑 **A CHECK THAT CANNOT RUN IS NOT A GATE.** The first cut of `check_atm_iv_stored` called `run_analysis`, which needs live market data and raises in a sandbox — so it reported "could not execute" and gated nothing, the same weak-gate shape that let r201 ship. The conversion was EXTRACTED so the check could actually exercise it. **If a thing cannot be tested where the tests run, make it testable rather than asserting it from source.** | r205 |
| **C.34** | 🔴 **A TEST BUILT AROUND YOUR OWN ASSUMPTION CANNOT FAIL.** I verified the r201 hint by creating a fixture directory that MATCHED MY GUESS, watched it pass, and reported it verified. It proved only that the guess was self-consistent. **The fixture must be built from the source of truth** — here, from `config.py`'s own constants — never from the same belief the code under test encodes. It happened TWICE: the r203 re-verification also read `$HOME/options-trader` instead of the fixture, because `DB_PATH` uses `expanduser`, and returned a stale row for all three cases before I caught it. | r203 |
| **C.35** | 🔑 **PRESENCE AND A CLEAN PARSE ARE NOT EVIDENCE THAT A DISPLAY DISPLAYS.** r201's land gate asserted `change_orb_budget` existed and that `configure.sh` parsed. Both were true of the broken version. A feature whose output IS the deliverable must be gated on that output. | r203 |
| **C.36** | ⚠️ **A CHECK THAT FAILS FOR A REASON UNRELATED TO WHAT IT CHECKS IS WORSE THAN NO CHECK.** The first r203 gate had a literal newline where `\\n` belonged — built through a Python string — so its regex never matched and it reported "no output" regardless. It would have gone red forever, been distrusted, and been disabled. Rewritten with plain string finds. | r203 |
| **C.32** | 🔴 **THE 08-28 CAP EXEMPTION IS REVERSED (C.24 SUPERSEDED).** It was ruled on RISK APPETITE — *"I'm actually good, even with the worst case"* — which is not the same question as ACCOUNT CAPACITY, and the code had neither. `check_orb_geometry_size` G3c pinned the exemption and was REWRITTEN rather than deleted: geometry is still exempt from the risk-per-trade rule and is now bound by its own budget. **Two ceilings, and conflating them is how a reversal gets half-applied.** | r201 |
| **C.33** | ⚠️ **FIFTEEN BOXES, ONE BROKERAGE ACCOUNT, NO COORDINATION** — every box reads the same `TT_ACCOUNT_NUMBER` and sizes as if it were alone. A local per-box budget bounds each one but does NOT bound the fleet: 15 x the budget is the real exposure, and r195's standing offers hold it for the session rather than for 20 seconds. Not a defect while paper; a live question with no answer yet. Whether tastytrade rejects an over-BP order outright or reduces to fit is **still unverified** — the local budget means we never find out. | r201, open |
| **C.31** | 🔑 **A RULE OUTLIVING ITS REASON IS A RULE THAT WILL BE LOOSENED BY THE NEXT PERSON WHO READS IT.** The noon floor's stated premise was falsified the same day it was hardened. The VALUE was still right — for two entirely different reasons — but leaving the dead sentence in place would have left the constant defended by a claim the record contradicts, and the honest response to that is to distrust the whole file. **When evidence kills a justification, replace the justification or drop the rule; do not keep both.** | r200 |
| **C.30** | 🔑 **WHEN A RULE CHANGES, SWEEP ITS READERS.** r161 made a box able to hold more than one position and three consumers went unswept: `has_blocking_position` (r197), `status.py` and `query.py` (r199). Each was invisible until a box actually held two. **A change to what is POSSIBLE is a change to every place that assumed it was not.** | r199 |
| **C.29** | 🔑 **A GLOBAL CONSTANT STANDING IN FOR A PER-SYMBOL FACT IS A BUG WAITING FOR THE RIGHT SYMBOL.** `STRIKE_INCREMENT` was correct for the $1-ladder symbols the strategy was developed on and silently wrong for every $2.50 and $5 one. It failed as a *refusal*, which is the most expensive kind of wrong: the gate reported honestly for 240+ minutes a day and nobody read it as arithmetic. **Ask the chain, not the config, for facts the chain owns.** | r198 |
| **BFLY.4** | ⬜ **STUDY: does a stretched wing trade as well as an intended one?** | ⬜ | Enabled by r198's recorded `wing_stretch`. The operator accepted the wide fly on the condition it bears out. Needs a disposition, not a shrug: if stretched flies underperform, the answer may be to refuse them on wide-ladder symbols rather than widen. |
| **C.27** | 🔑 **AN EXEMPTION BUILT IN ONE DIRECTION IS HALF AN EXEMPTION.** r161 said the butterfly takes "no position slot" and implemented it only for ENTRY. That it occupies no slot once open was never written, and the gap stayed invisible because it only shows when a butterfly is open AND another setup qualifies. **When a rule says a thing does not participate in a constraint, check BOTH directions.** | r197 |
| **C.28** | `set_open_position()` REPLACES `_open_records`. Before r197 an entry could never land on a box already holding a butterfly, so the wipe was unreachable; r197 makes it reachable. `additive` is no longer a caller's opinion — `main.py` appends whenever anything is open. A dropped butterfly has no trail and no stop. | r197 |
| **C.25** | 🔑 **RELAX DIALS, NEVER STRUCTURAL GATES — AND THINK TWICE ON A CAPPED STRATEGY.** Relaxation only informs a gate that is a DIAL ALONG A CONTINUUM: widen it and you collect the near-misses, whose outcomes say whether the line sits right. `PIN_CONC_MIN` and `EM_MAX_FRAC` are dials and are relaxed correctly. A time floor is not — the operator's rule (*"any sooner than noon to reach a pin is unlikely to hold all the way to the closing bell"*) is about TIME TO EXPIRY, so a 09:45 butterfly is not a marginally worse butterfly, it is a different trade whose outcome says nothing about whether noon is right. ⚠️ AND THE WIDENING CAME FROM UNRELATED REASONING: `relaxed.window`'s 09:45 floor is documented as avoiding the OPENING AUCTION'S RESIDUE, a quote-quality argument that silently overrode a time-to-pin one. 🔴 WORST ON A CAPPED STRATEGY: the butterfly is ONE PER SESSION, so relaxing this did not collect a sample, it SPENT the sample three hours before the thesis was valid. | r196 |
| **C.26** | 🔴 **`sqlite3` IS NOT ON THE BOXES**, so a fan-out query piping stderr to /dev/null returns EMPTY and reads as "no rows". I concluded "there are no butterfly trades anywhere" from exactly that, while Telegram was showing the fills. Use the repo venv's python for box-side DB reads, and never let a diagnostic hide its own failure. | r196, self-inflicted |
| **C.22** | 🔴 **A SIZING RULE APPLIED BY THE CALLER IS THE ONLY KIND THAT CAN COMPUTE A NUMBER THE ORDER NEVER SEES.** r181 lived in `_execute_entry_signal` and wrote `signal.contracts` — written 4x, read 0x tree-wide. Every size must come from `size_for()` and arrive in `SizingResult.contracts`. A rule that cannot return a `SizingResult` is not a sizing rule. | r192 |
| **C.23** | 🔴 **`tests/check_orb_geometry_size.py` v1.0 PINNED THE BUG RATHER THAN MISSING IT.** G1-G3 re-implemented the geometry inside the test and asserted against that copy; G5 read `main.py` as source text and asserted the PRESENCE of `signal.contracts = _geo`. Green for two days, and any correct repair turned it red. **A test that re-implements the thing it measures tests itself.** v2.0 executes and asserts the quantity handed to `_place_single_leg`. | r192 |
| **C.24** | ORB geometry has **no `insufficient_capital` rung**, by the 08-28 cap-exemption ruling. A setup the budget rule refused outright (premium > risk budget) now trades at >=1 lot. Verified: $2.40 premium sizes 10 lots / $2,400 notional where the budget rule returns `allowed=False`. Only a non-positive premium still refuses. | r192 |
| **C.17** | **THERE IS NOW EXACTLY ONE DEDUP RULE IN THE SYSTEM: `warehouse_reader.latest_per_trade()`, newest `pushed_at_utc` wins.** Nothing downstream may add a second. A tool that finds itself needing to "pick between two rows" of the same `trade_id` has found a DEFECT upstream, not a tie to break. | r190 |
| **C.15** | **MENU NUMBERS MOVED AT r188 AND WILL MOVE AGAIN.** They are assigned from a render-time loop counter and stored nowhere, so a reorder cannot desynchronise code — that property was bought by the v1.35 conversion after the July 22 incident. **What it cannot protect is PROSE.** Any doc, changelog or note naming an item by number is now wrong. **Cite items by LABEL.** | r188 |
| **C.16** | ~~The **S3 WAREHOUSE** section still reads *"(read-only; runs ALONGSIDE the local reports)"*. After r184–r187 there is barely a local report left to run alongside. Same stale framing MENU.1 removed from R SUITE.~~ **RESOLVED r189** — now `S3 WAREHOUSE (inventory, hygiene, rebuilds and parity)`, which is what those nine items actually are. | r188, closed r189 |
| **C.13** | **`setup_grade` IS `UNGRADED` ON EVERY v4 ROW AND `setup_score` IS NEVER WRITTEN.** The columns survive deliberately (`check_conviction_removed` S6). Any report grouping on either has exactly one bucket, and any study treating them as data is measuring a constant. | r187, read from entry_engine:212 / main:2135 / condor_roll:789 / base_strategy:127 |
| **C.14** | **NO REPORT HAS AN ENGINE-EPOCH FLOOR BY DEFAULT EXCEPT REPORT 41.** `trade_report` v1.9 floors at 2026-08-25; `excursion_report`, `fit_readiness` and the R suite do not. Every one of them can pool v3 and v4 records in a single table. Worth a sweep once S3.4 is ruled. | r187 |
| **C.12** | **`trades/<date>/` IS NO LONGER POPULATED ON CONTROL.** `install_eod_v2.sh` disables `dtp-harvest.timer` deliberately — the conductor drains to S3 and a second copy has no consumer. Consequence for every report: **the per-box-DB path is dead**, and anything still taking it reads nothing. `excursion_report --since` is the one capability genuinely lost with it (a bundle holds one session), and it refuses rather than lying. | r186, read from `install_eod_v2.sh` |
| **C.11** | **A FACT WRITTEN IN THREE DOCUMENTS ROTS IN THE ONE NOBODY SWEEPS.** The fleet count lived in `README.md`, `ROADMAP.md` S.4 and WA §30; r74 fixed two. Prefer ONE authority plus pointers: the panel is `selector.PANEL`, the module graph is the generated `FILE_MAP.md`, the table ownership is the generated `WRITE_MAP.md`. Where a fact must appear twice, the second copy says which one outranks it. | r185 |
| **C.9** | 🔴 **A DERIVED `dt=` PARTITION IS THE PUSH DAY, NOT THE ROW'S DAY.** `push_derived` files every CHANGED row under `datetime.now(ET).date()` at push time, so a plan created Monday and updated Wednesday lands in **Wednesday's** partition, and the first push after any gap files a whole table's history under one day. Reading one partition per requested date under-reports **silently** — it returns a smaller, entirely plausible number. `load_derived()` scans a forward window (`DTP_DERIVED_FORWARD_DAYS`, default 3) and then files each row by ITS OWN timestamp converted to the ET trading day. **Partition selection and row attribution are different questions.** | r184, read from `s3_push.push_derived` |
| **C.10** | Timestamp columns differ by table and the difference is meaningful: `plan_ledger` is dated by **`created_ts`** (when the plan was FORMED), everything else by `ts_epoch`. Dating a plan by `updated_ts` would move it to whichever session it last transitioned in. | r184 |
| **C.7** | **GATE.1 proves the bookkeeping, not the edit.** It asserts the version MOVED and that a dated entry names it; it cannot tell whether the entry is TRUE. The land command's own content gate — a positive grep for a distinctive line from the real change plus a negative grep that the superseded code is gone — is what proves the edit happened. Running GATE.1 and calling a delivery verified is the laundered green WA §18 names. | r183 |
| **C.8** | The otv4 checkout on control is **`~/options-trader-v4`** (hyphens), not `options_trader_v4`. Confirmed by r182's land output. | 2026-08-29, observed |

---

## PART 4 — CHANGELOG

**v1.88 — 2026-09-05 — r272 — THREE ROWS CLOSED BY READING THEM. DOCS ONLY.**

None of the three needed work. All three needed checking, and two were wrong
about the repo as it stands.

🔴 **SNS.4 NAMED THE WRONG FUNCTION.** It required every S3-sourced reader to
use `warehouse_reader.load_derived()` — which carries the natural-key collapse,
the forward scan and the ET-day filter, and **has no production callers**
(S3.11). A standing rule pointing at the correct-but-unused path would have
sent the next reader down the road with no traffic, **which is exactly how
S3.11 and S3.21 happened**. It is now WA **§36a** and names
`WarehouseCache.load`, which every report actually uses and which carries all
three behaviours since dtp r286/r290. ⚠️ It moved to the working agreement
because it is a STANDING RULE: a backlog row is a task, and this is a
constraint.

**S3.7 WAS STALE TWICE.** *"Menu 54 → retire, or repoint to
`warehouse_reader.build()`"* — 54 is now the LAND item (C.15, on a row written
before the menu shifted), and the item it meant, `Rebuild a day's bundle FROM S3
→ reports/warehouse/`, **already shells `warehouse_reader.py`**. The repoint it
asked for exists. A row citing a menu number is wrong the moment the next item
lands, which is why C.15 says cite by label — and why this one could not be
evaluated without opening the registry.

**RPT.3 CONFLATED A MENU ITEM WITH A SCRIPT.** `excursion_report.py` is retired
from the menu and has **two live callers** — `tools/report_parity.py` and the
nightly `_excursion` phase, which shelled it in tonight's run. `menu_registry
.sh:55` already documents exactly this. ⚠️ And `report_parity.py`'s fate is not
open either: it is **WH.11's gate**, its own output reads *"OT_EOD_PULL=0 is now
defensible"*, and `OT_EOD_PULL` still defaults to 1 — dual-write is live, so the
tool that decides when to sever it stays until it is severed.

**v1.87 — 2026-09-05 — dtp r293 — LAND.3: THE ROLLBACK'S RECOVERY RESTORED WHAT
IT CLAIMED TO DISCARD.**

r279's all-or-none rollback uses `reset --soft` on purpose, so an unrelated file
the operator had mid-edit survives. The consequence went unstated: **the payload
stays staged in the index.** The message said *"the files are still in the tree,
uncommitted"* — true, and the natural reading is that a `git checkout -- .`
clears them. It does not. That command copies the INDEX into the working tree,
so it **restores precisely the changes it was run to remove.**

📊 **OBSERVED ON A REAL RETRY, NOT REASONED.** The tree read clean, the files
were still present, and the next land appended a **second GENESIS row for the
same revision**. `check_land_discipline`'s duplicate-row check refused it —
which is the only reason this surfaced at all rather than landing a ledger with
two authoritative rows for r270.

The message now names the state (`the payload is STAGED, not discarded`) and
prints a command that unstages before it restores. ⚠️ **The rollback mechanism
is untouched and stays `--soft`** — §35's reason still holds. The defect was in
what the operator was told, and in there being nothing to act on.

⚠️ **TWO WRONG DRAFTS OF THE CHECK ARE WORTH RECORDING**, because both passed
against the broken code. The first drove a CONTENT-GATE refusal, where nothing
has been committed and nothing is staged — so the old command worked and the
case went green at HEAD. The second read `die()`'s recovery line, which belongs
to the half that FAILED and likewise never staged anything. **Only the
rolled-back half reaches the defect.** A case that does not take the exact
failing path is a case that certifies the bug.

`tests/check_land_sh.py` v1.5, born red 2. R1d runs the printed command and
asserts the repo is clean afterwards — grepping the message for `reset` would
have passed against any sentence containing the word.

**v1.86 — 2026-09-05 — otv4 r270 / dtp r292 — ASK.1: THE CHARACTER ENGINE'S ONLY
OUTPUT REACHES THE WAREHOUSE.**

Operator ruled: push it.

🔑 **AND IT IS NOT A MINOR TABLE.** r85 set `BANDS_SET=False`, so
`character_ledger` records no transitions and pushed **0 boxes** in the
2026-09-05 stream census. `character_engine`'s own comment says what that
leaves: *"the sample IS the deliverable right now — one session of real
efficiency values is what the bands get derived from."* **Holding the bands back
was the entire reason for collecting this**, and until now the corpus they are
to be derived from lived only on the boxes.

Per row: `efficiency`, `vol_ratio`, `close_capture`, `realised_vol_cc`,
`realised_vol_parkinson`, `adx`, `atr_normalized`, `price`, keyed
`(symbol, ts_epoch)`. Two realised-volatility estimators side by side — a
feature vector rather than a status field. It is **strided**
(`BASELINE_STRIDE_S`) on purpose, because *"a 15s cadence would write ~1,560
rows per symbol-day to answer a question a few hundred answers just as well."*

⚠️ **THREE PLACES, ONE REVISION.** Append-only and ts-keyed, so it takes the
HIGH-WATER path with `fork_series` and friends, not CDC. It gets a
`retention_purge` entry at 20 days **in the same revision that pushes it** —
it was in no list at all, neither purged nor protected, the exact by-absence
exposure that let `shadow`, `plan_tick` and `plan_check` grow unbounded
(S3.15), and adding the push alone would have left it that way. And it gets a
`STREAM_POLICY` row, because an undeclared stream renders **UNDECLARED** and
fails the coverage board on night one — a new alarm that cries wolf immediately
is how an operator learns to stop reading it.

⚠️ **`CONDITIONAL`, NOT `EVERY`.** The engine writes only when an axis value is
computable, and the write is strided, so a thin session legitimately produces
none. Grading it `EVERY` would flag quiet boxes as gaps — the mistake r280
corrected for `trades` and `prints`.

⚠️ **20 days is the sibling default and a RE-PUSH WINDOW, not a fit decision.**
S3 is the durable home; how much history the bands need is answered from the
warehouse, by whoever fits them.

**v1.85 — 2026-09-05 — r269 — ASK.3 RESOLVED AND CND.1 SETTLED: EIGHT SPENT
CONTRACTS DELETED, TWO THINGS LIFTED OUT OF THEM FIRST.**

Eight documents, ~89 KB, ~1,700 lines. Read before ruling rather than sorted by
filename.

**`AUDIT.md`** is a DELIVERY CONTRACT — how to package work so it survives the
pipeline. Every constraint in it is now enforced by `land.sh`, the `land.spec`
format and §15, so it describes a rule you can no longer follow wrongly.
**Five `HANDOFF_*` docs are REQUESTS whose work landed**, and each says so in
its own opening lines — *"RESOLVED — r146"*, *"Ships with the fix this document
asked for"*, *"read with PLAN_SPEC §10"*.

🔑 **TWO THINGS HAD TO SURVIVE, AND THEY GO TO DIFFERENT PLACES.**

The v3 direction-skill measurement — 715 closed directional trades, 16 sessions,
**44.9% correct side, CI [41.3%, 48.6%] entirely below a coin flip**, puts
34.2%, and the P&L attribution behind the v4 thesis — went to `config.py`'s
**INHERITED DOCTRINE** block. ⚠️ **Not the backlog**: the operator's own
distinction, *"backlog is deferred work"*, and this is a settled measurement.
Not an archive either — an archive is where documents go to stop being read.
The doctrine block is what WA §32 requires be read before that file is edited.

**CND.1** went to the code. `HANDOFF_CONDOR_STOP_20260824.md` held the only
statement of an OPEN operator decision — whether a formed condor has any loss
boundary beyond the 15:45 close, the nickel close and the roll — cited twice
from `exit_engine.py` and **absent from the backlog entirely**. The operator
settled it: it has none, deliberately. That answer now lives at the site that
would otherwise invent one.

⚠️ **DELETION WAS NOT FREE, AND CHECKING FIRST IS WHAT FOUND THAT.** Six live
citations pointed into these files, including two in live code and one in a
ninth document (`docs/HANDOFF.md`) that was not in the original list. All were
redirected to what survives — `PLAN_SPEC` §8 and §10, WA §0.6, the backlog —
before a single file was removed.

**v1.84 — 2026-09-05 — r268 — SHD.2: VELOCITY SURVIVES A RESTART, AND A NULL
STOPS READING AS A QUIET TAPE.**

Operator's parameters, given plainly after I circled the question twice:
*"I want it collecting from the open and recoverable from a reboot or crash
loops. The boxes come up at 09:15 sharp."*

🔴 **THE DEFECT.** `TickAccumulator` is live-only — `add()` runs from inside
`one_tick` — so a reboot at 10:00, or the fourth pass of a `Restart=always`
crash loop, entered RTH with an empty deque and emitted `typical_roc: null` for
the next five minutes. **And a null velocity is indistinguishable from a quiet
tape**, in exactly the corpus the operator intends to fit triggers on. Same
silent-empty shape that let seven weeks of stage-1 shadow data look like data.

🔑 **RECOVERY IS FROM THE CANDLES, NOT FROM A CLOCK.** The 1m closes are
backfilled from the session open and `one_tick` already holds them, so
`seed_from_closes()` costs a loop over data in hand. **The first tick of the
day, a 10:00 reboot and the fourth restart of a crash loop all take the same
path** — nothing depends on when the process started, and no timer is
load-bearing. The 09:15 wake is a convenience rather than a dependency, which
is what makes it robust to the case the operator asked about.

⚠️ **AND THE RECORD STATES ITS OWN PROVENANCE.** `velocity_state` is
`warming`, `seeded` or `live` on every line. A seeded baseline is a median of
MINUTE-to-minute moves while live samples are poll-interval moves — different
scales — so the fit is told which it has rather than being handed a number on
the wrong footing. It stays `seeded` while any seeded sample is still inside
`TYPICAL_LOOKBACK_S`, because the median is taken over that window and one
seeded sample in it still moves the denominator.

⚠️ **TWO EARLIER PROPOSALS OF MINE WERE WITHDRAWN AND THAT IS WORTH RECORDING.**
A clock-based pre-open warm-up fails the restart case entirely. A pre-open
seed puts a thin-tape median under the denominator, and `TYPICAL_LOOKBACK_S =
1800` would drag it through the whole ORB window — the case
`TYPICAL_ROC_FLOOR` was already built to bound. ⚠️ **I ALSO ASSERTED THE
PRE-OPEN DISTRIBUTION WITHOUT MEASURING IT**, on a fleet of fourteen mega-caps.
Recovery from the session's own candles avoids the question rather than
answering it.

`tests/check_shadow_velocity.py` v1.0, **10 checks**, born red. ⚠️ V3b was
re-derived mid-build: it asked for `seeded` at a moment when the seeded samples
had already aged out of the lookback, where `warming` is the truthful answer —
the code was right and the case was wrong. V5 drives zero, `None` and garbage
closes, because the observer logs a failed tick at WARNING and continues, so an
exception in the seed would cost the whole record and look like a quiet tape
again.

**v1.83 — 2026-09-05 — dtp r290 — S3.21: THE READ WINDOW WAS WRONG IN BOTH
DIRECTIONS, AND THE CONTROL THAT WOULD HAVE CAUGHT IT COULD NOT RUN.**

`WarehouseCache.load` listed exactly the requested `dt=` partitions and applied
no filter afterwards. **A derived partition carries the PUSH day, not the row's
ET day** — C.9, and the reason the coverage board grades those streams `pusher`
grain. So the method was wrong twice over: a row whose session fell in range but
which pushed the next morning **was never read**, and a row pushed inside the
range whose own day fell before it **was read anyway**. Neither consumer
compensated.

🔑 **AND `load_derived` HAS DONE IT CORRECTLY SINCE r184** — scan a forward
window, then keep rows whose own timestamp lands in range. It has no production
callers (S3.11). The correct behaviour sat on the road with no traffic while
every real report used the wrong one, which is the same finding as S3.11 one
layer down and the second time today it has cost something.

⚠️ **THE CONTROL EXISTED AND COULD NOT EXECUTE.** `tests/test_fit_readiness_s3.py`
case C is a forward-scan **positive control**, and that file has been raising a
TypeError before its first assertion since the streaming rewrite (RPT.14). **A
positive control that cannot run is not a control** — so
`tests/test_cache_window.py` rebuilds it on the path production takes, and every
case drives `cache.load` and counts rows in sqlite rather than touching
`load_derived`.

⚠️ **THE ET FILTER IS PER ROW IN PYTHON, NOT AN SQL OFFSET.** `_et_offset()`
applies TODAY's UTC offset to every row — right for eight months and an hour
wrong for four, the exact DST trap its own docstring warns about. W3 pins a row
at 00:30 UTC on 2026-11-03 landing on 2026-11-02 ET, which a September offset
would have placed on the wrong day.

🔴 **AND MY FIRST CUT DID NOTHING, WHICH THE CHECKER SHOWED IMMEDIATELY.** I
changed the FETCH loop to walk the widened scan and left the key LISTING on
`dates`, so the forward partitions were never listed. The checker failed
identically before and after — which is precisely what a fix applied to the
wrong half looks like, and why every case here drives the real method.

⚠️ **`test_cache_collapse` fixtures corrected too**: they used `ts_epoch: 1000.0`
— 1970 — on rows filed under a 2026 partition. Internally inconsistent from the
start, invisible until something filtered on the row's own day.

`tests/test_cache_window.py` v1.0, **8 checks, born red 3**. Ten control suites
green.

**v1.82 — 2026-09-05 — dtp r289 — DEP.2: THE CONTENT GATE WAS MATCHING
PATTERNS, NOT CONTENT.**

`land.sh` compared POS/NEG assertions with `grep -q` — a **basic regular
expression** — against strings that are ordinary text. It graded two deliveries
wrongly in a single day, in **opposite directions**.

🔴 **FAILED OPEN.** `POS docs/GENESIS.md|**r247**`. In a BRE that reads as `r24`
followed by *zero or more* `7`s and *zero or more* `*`s, so it matched a GENESIS
containing `r24` and no `r247` at all. The gate reported PASS on an assertion
that was false, which is the failure this whole mechanism exists to prevent.

🔴 **FAILED CLOSED.** `NEG menu_functions.sh|[ "$GO" = "y" ]`. The brackets are
a character class, so the NEG matched a file that did not contain the string,
and a correct delivery was refused. That one cost a re-cut of the archive.

🔑 **A GATE THAT CAN FAIL BOTH WAYS IS NOT A WEAK GATE. IT IS UNRELATED TO THE
THING IT CLAIMS TO CHECK** — and it had been that way since r235, silently, on
every delivery that happened not to contain a metacharacter.

⚠️ **AND THE REGEX BOUGHT NOTHING BY DESIGN.** The operator's supersession rule
is that an assertion names *a distinctive LINE from the real change*, so
`**bold**`, `[brackets]`, `$vars`, `(parens)` and `.` are the CONTENT being
asserted. A pattern engine can only misread them. `grep -qF`.

`tests/check_land_sh.py` v1.3, **born red 2**. ⚠️ F1 and F2 drive a **real
land** — a source check for `-qF` would pass against the flag sitting in a
comment and prove nothing, which is the same defect one level up. F3 exists
because loosening a check that misfires is the easy wrong fix: the literal form
must still refuse a delivery whose asserted content is genuinely absent, and it
does.

**v1.81 — 2026-09-05 — r265 — SEC.1: I LEAKED THE FLEET'S CREDENTIALS. AND
SHADOW WAS ONLY HALF COLLECTING.**

🔴🔴 **SEC.1 FIRST, BECAUSE IT COST HIM HIS EVENING.** To confirm one variable I
ran `systemctl show shadow-observer -p Environment --value` on all fifteen
boxes. That flag prints the entire block: `TT_REFRESH_TOKEN` — a live JWT with
`read trade` scope on the funded account — `TT_CLIENT_SECRET`, `GITHUB_TOKEN`
with write access to both repos, and `TELEGRAM_TOKEN`. Four rotations, fifteen
boxes, Saturday evening. ⚠️ **I had written the safe filtered form earlier in
the same session and reached for the unsafe one anyway**, which is exactly why
this is a section and a checker rather than a resolution.

🔑 **AND THE CHECKER'S OWN FALSE POSITIVES CORRECTED THE RULE.** Its first cut
flagged three install scripts that do
`EL=$(systemctl show "$BOTUNIT" -p Environment --value)` and then filter with
`grep "^$1="`. Those **capture** into a variable and emit nothing — the correct
idiom, and it predates me. **The offence is EMITTING the block, not reading
it.** A rule banning the read would have flagged three working files and taught
the next reader to disable the check.

🔑 **ASK.2 IS SETTLED, AND ITS PREMISE WAS WRONG TWICE OVER.** It began as *cut
a dead stage or leave it*; r280 established shadow is live; and today's
measurement establishes it has been **collecting only half of itself since
July** — `"stage": 1` on all fifteen boxes, `scores: []`, zero scorer entries.
`OT_SHADOW_STAGE=1` is the build-order de-risk meant to hold "for a few
sessions", and nothing ever forced step two. **Same shape as the retention purge
logging "WOULD remove" for two months.**

⚠️ **WHAT THE SEVEN WEEKS DO HOLD IS REAL** and answers the operator's first
question: per tick, `current_roc` against `typical_roc`, `atr_normalized`,
`bb_width_pct`, `price_vs_bb`, and nearest-level distance in both pct and ATR —
enough to walk backwards from a real move and see which primitive crossed
first. **What it cannot hold** is `stages`, `conviction`, `invalidated` and
`would_fire` across ten thresholds. That tape is gone and cannot be rebuilt.

**Armed by drop-in on all fifteen boxes the same day**, `active=active`; r265
moves the unit's own default 1 → 2 so a re-install cannot silently restore the
state that cost seven weeks.

**SHD.1 opened** for the divergence join itself. Both sides are
warehouse-readable, but `plan_tick` keys on UTC epoch floats and shadow on ET
strings from an independent process, so the join must be **nearest preceding
shadow tick with the gap reported** — never minute-bucketed, because averaging
destroys the lead-time signal the whole exercise is after.

**v1.80 — 2026-09-05 — dtp r288 — TZ.2: THE BOUNDARY HAD A SHELL-SHAPED HOLE.**

The operator asked a precise question — *"Monday at 19:30, when it's already
Tuesday in UTC, it will know I mean Monday, right?"* — and checking it found the
gap rather than confirming the fix.

🔴 **THREE MENU PROMPTS FELL BACK TO `$(date +%F)`, WHICH IS UTC.**
`menu_functions.sh:220`, `:395` and `:577` hand a date to the script BEFORE any
Python default can apply, so r287's nine corrected sites were invisible behind
three ENTER keys. Three sibling prompts in the very same file already used
`TZ=America/New_York date +%F` — the identical five-right/nine-wrong split TZ.1
found in Python, repeated one language over.

⚠️ **THE MISS WAS THE GUARD'S SCOPE, AND THAT IS THE LESSON.** r287's T4 swept
`*.py` and I called it the repo. **The gap was hiding in the language the
checker did not read — the same shape as the defect the checker exists to
catch.** So r288 extends the sweep to `.sh` rather than editing three lines: T6
was proven RED against the three real sites before they were fixed, and T6b
plants a fault to show it can fail, because a guard never seen red is a guard
nobody has tested — which is exactly how v1.0 shipped blind to these.

⚠️ **AND THE TIMING IN THE QUESTION WAS OFF, WHICH IS WORTH KEEPING.** At 19:30
ET in summer it is 23:30 UTC — still the same day. The roll is **20:00 EDT /
19:00 EST**, so this is a winter-hours failure. It would have presented as
intermittent and seasonal, which is the hardest kind to chase from a symptom.

`tests/test_ettime.py` v1.1, **15 checks**.

**v1.79 — 2026-09-05 — dtp r287 — TZ.1: ONE ET/UTC BOUNDARY, AND A SWEEP THAT
KEEPS IT.**

Operator: *"Store everything as UTC, but when a report prompt asks me for a
date, convert my choice assuming I mean ET. It's incredibly annoying when I run
a report for 'today' at 6pm and it says nothing to report, because UTC has
already started the next day."*

📊 **SURVEYED FIRST, AND THE SURVEY CHANGED THE JOB.** NINE sites handed out a
naive "today"; FIVE more had it right and each carried its own private
three-line copy. **So there was never one missing translator — there were five,
and nine places that never got one**, which is how the count grows every time
somebody adds a report. The worst of the nine was **`market_calendar`, the
module that decides what a trading day IS**, asking a UTC box: after the roll it
answered Friday's question about Saturday, returned False, and was
indistinguishable from a real holiday.

⚠️ **THE ROLL IS 20:00 ET IN SUMMER, 19:00 IN WINTER** — the instant UTC
midnight lands. Past it every naive default asks for TOMORROW, finds nothing,
and **reports nothing rather than erroring**: a defect in the clock reading as a
finding about the market, which is the worst shape of bug this project has.

🔑 **`ettime.py` IS THE BOUNDARY AND IMPORTS NOTHING FROM THIS REPO.** A first
cut had it re-export `et_day`/`et_bounds` from `warehouse_reader` and closed a
cycle immediately — `warehouse_reader` imports `market_calendar`, which now asks
this module what today is. **The boundary cannot depend on one of its own
consumers**, so the two functions moved here and `warehouse_reader` re-exports
them for its existing callers. The cycle was the architecture telling me which
way the dependency goes.

⚠️ **`operator_date()` RAISES ON A TYPO** rather than defaulting. A prompt that
silently reinterprets an unparseable answer produces a clean report about the
wrong day, which is the same failure one level up. And `days_back()` builds
ranges in ET DAYS rather than by subtracting 86400 — that is not a day across a
DST boundary, and T3 spans the November change to prove it.

🔴 **T4 IS THE DURABLE HALF OF THE DELIVERY.** It walks the whole repo for
`datetime.now()`, `date.today()` and `utcnow()` outside the boundary and fails
on a new one, with `ettime` and `auto_label` exempt for stated reasons. Fixing
nine sites without that guard buys a year at most. T4b plants a fault to prove
the sweep can go red, and T5 asserts the module has real callers — a boundary
nobody imports is r230's defect wearing a new hat.

`tests/test_ettime.py` v1.0, **13 checks**, born red. Fourteen existing control
suites re-run green after the move.

**v1.78 — 2026-09-05 — dtp r286 — S3.11 CLOSED, AND THE ROW'S OWN DIAGNOSIS WAS
WRONG.**

S3.11 was filed as *three collapse rules on one dataset, C.17 says exactly one*.
Checking before building says otherwise: **there was one, and it ran where
nothing goes.**

🔴 **`load_derived` HAS NO PRODUCTION CALLERS.** It has carried the natural-key
collapse since r276, and its only references outside its own definition are
three test files and a `fit_readiness` docstring naming an architecture that had
already changed. Every report reaches the warehouse through
`WarehouseCache.load`, which streams objects into sqlite and **collapsed
nothing**. That is r230's shape exactly — a correct fix on a road nobody drives
— and `test_natural_key` stayed green the entire time because it calls the dead
function directly. **A test that exercises the wrong entrypoint cannot fail for
the right reason**, which is why `tests/test_cache_collapse.py` exists as a
separate file rather than as more cases in the old one.

🔑 **THE COLLAPSE MOVED TO WHERE THE DATA IS.** `WarehouseCache.load` now
dedupes at insert through a UNIQUE index on the natural key — O(one object)
preserved, sqlite doing the work on disk, which is this class's whole reason for
existing after r242's OOM. The winner rule is `load_derived`'s rather than a new
one: a later push replaces an earlier one, because these are CDC rows.

🔴 **AND IT REFUSES A PARTIAL KEY.** `load()` keeps only the columns a caller
asks for, and collapsing on a SUBSET of a primary key folds genuinely distinct
rows together — silently, and in the direction that makes a report look tidier.
Measured: `fit_readiness` requested `plan_ledger` without `plan_id`, which is
that table's entire key. It now requests it; any table whose key does not
survive its projection loads uncollapsed and the banner says so.

🔴 **RPT.13 — THE BANNER DESCRIBED A COLLAPSE ITS DATA NEVER GOT.** *"N after
collapse by (_rid, ts)"*, computed over an uncollapsed cache, under a docstring
claiming the work happened upstream. The number was real and the sentence was
false. ⚠️ **And my first cut reproduced the same defect one layer down** —
`load()` returned the INSERT count, so a caller would have printed *"4 row(s),
collapsed on …"* for two logical rows. The new checker's own detail line caught
it: 2 in the table, 4 in the ticker.

⚠️ **RPT.14 OPENED AND DELIBERATELY NOT FIXED HERE.**
`tests/test_fit_readiness_s3.py` has been dead — a TypeError before any
assertion runs, verified at HEAD. Repairing the call exposed a second staleness
two API generations deep, so the half-repair was **reverted rather than
shipped**: a test that runs and asserts the wrong shape is worse than one that
visibly fails.

`tests/test_cache_collapse.py` v1.0, **12 checks**, born red. Every case drives
`cache.load` and counts rows in the sqlite table — never the reader, never a
return value a refactor could satisfy without touching the data. W3c is the one
that matters: two distinct plans identical in every projected column are BOTH
kept.

**v1.77 — 2026-09-05 — dtp r285 — S3.12: THE COVERAGE BOARD JOINS THE NIGHTLY
CHAIN, LAST RATHER THAN FIRST.**

`eod_analysis` v1.3 gains a **STREAMS** phase between COVERAGE and the R suite.

🔑 **THE DELAY WAS THE DESIGN.** r277 built `--streams` and refused to wire it,
because every CONDITIONAL and DEAD classification in the policy table was a
declaration read out of `s3_push`'s stage list and never checked against a real
bucket. The first hand-run raised **nine flags and seven were mine** — `prints`
graded EVERY when SPX is a cash index that publishes none, `trades` graded EVERY
when `push_trades` is CDC, `shadow` graded DEAD when fifteen boxes push it every
session. r280 corrected all three; r284 closed the two genuine absences as
ACCEPTED_LOSS. **Wired on the day it was built, this alarm would have cried wolf
on its first night and been ignored by its second** — the CV.1 failure, arrived
at from the other direction.

⚠️ **A SEPARATE PHASE, NOT AN ARGUMENT TO `COVERAGE`.** The VIX report answers
*did the single-writer stream land*; this answers *did every box push every
stream it owes*. Different questions with different exit codes, and two of them
behind one green is how a passing check stops meaning anything.

⚠️ **IT CARRIES THE ROWS.** dtp r282 is one phase over in the same chain, where
`head -3` ate the cause of every purge failure for weeks. The phase logs each
flagged line — 🔴 gap, ❗ stale exemption, ❓ undeclared — and **▪ accepted-loss
rows print on a clean night as well**, because r284's contract is that a closed
absence stays visible rather than vanishing from the board.

⚠️ **WARN, NEVER STOP.** A coverage gap is a fact about yesterday; the rest of
the chain still has work to do, and a phase that aborted would cost the R
baseline over a missing OHLC file.

`tests/test_streams_phase.py` v1.0, **12 checks**, born red. P1 asserts the
phase is in the list that actually RUNS rather than merely defined — a function
nobody calls is the r230 defect. P3 is the one that matters: the flagged rows
must survive the phase, including the accepted-loss ones.

**v1.76 — 2026-09-05 — r260 — S3.16 ANSWERED AND CLOSED; MEM.1's BANDING HALF
RULED OUT AND SETTLED. DOCS ONLY.**

📊 **THE MEASUREMENT.** Fleet-wide, post-purge: `quote_series` is the store.
QQQ **11,476,862** rows against greeks 431k, prints 394k, candles 17k. MU/CVX on
that table is **13.8x** where the whole store spread was 9x — so it is both the
largest table and the one carrying the variance.

🔑 **AND THE DECOMPOSITION IS THE FINDING, NOT THE HEADLINE.** `greeks_series`
and `quote_series` ride the same per-contract chunked subscribe, which makes
greeks a clean proxy for chain width. Greeks vary **4.2x** across the fleet;
quotes vary **15.0x**; quotes-per-greek varies another **4.1x** — CVX and UNH
sit near 6.7 while QQQ and TSLA run 25-27. **Chain width and per-contract quote
ACTIVITY contribute roughly equally**, 4.2 x 4.1 = 17 against 15 observed.
⚠️ **THAT CORRECTS SOMETHING I SAID EARLIER TODAY** — that the disk story and
the 09-02 OOM were one root cause. They share a contributor; they are not the
same number, and the stronger claim was mine.

🔴 **OPERATOR'S RULING: THE CHAIN STAYS UNBANDED. DECIDED, NOT DEFERRED.**
*"I like #1 the best and it will let us know soon if the checkpoint ever fails to
run again. Let's close it out as decided — leave it."*
🔑 **THE UNBANDED CHAIN IS A CANARY**, and that is the argument rather than a
shrug: store growth is the fastest visible signal that the nightly reclaim has
stopped, and a banded chain would hide a silent failure behind a smaller
footprint for weeks. The same shape as §17's rule that detection stays on while
only the alerting is gated.

⚠️ **TWO SUPPORTING FACTS, BOTH OF WHICH WOULD HAVE SURVIVED A DIFFERENT
RULING.** The lever is smaller than the contract count suggests, because the
strikes a band removes are the deep-OTM ones that barely quote. And it carried a
real cost: `compute_gex` walks the WHOLE chain for `call_wall` and `put_wall`,
and r215 deliberately left the walls unbounded — *"a wall IS allowed to be far
away, that is what makes it a wall"* — so a band would have truncated the gamma
surface and quietly weakened a signal the sweep reads for confluence.

⚠️ **ONE CORROBORATION FROM A DIFFERENT INSTRUMENT:** SPX reported `prints 0`,
independently confirming the `EVERY_EXCEPT:SPX` classification shipped at r280
from a measurement that had nothing to do with coverage.

**The disk is solved by the nightly reclaim (S3.15 / S3.17). Nothing further is
owed on chain width, and this row exists so it is not re-opened from scratch.**

**v1.75 — 2026-09-05 — r259 — DOC.15: TWO SPENT REVISION NUMBERS GET THEIR ROWS,
IN SEQUENCE.**

r247 and r248 were the otv4 halves of the natural-key and coverage deliveries,
cut against BACKLOG v1.64/v1.65. Before either landed, r278 shipped the
universal deploy and took v1.65, so both would have overwritten newer entries
with an older file. They were re-cut as `_r2` and landed as **r250** and
**r251**. 🔑 **Their content gates are why that was caught rather than
clobbered** — r248's half asserted a GENESIS row written by its predecessor, so
landing the pair out of order was REFUSED rather than quietly overwriting a
backlog. The `ORDER` directive in the re-issues exists for the same reason.

**The ledger could report the gap but not explain it.** `check_ledger_parity`
listed them inside *"15 unused revision number(s)"*, which is true and leaves a
reader unable to distinguish a MISSING revision from a number that was never
used without going through git. §26 says numbering is sequential and never
resets, so a spent number is a fact about the ledger and belongs in it.

⚠️ **SHIPPED AS A FILE RATHER THAN AN APPEND, AT THE OPERATOR'S DIRECTION, AND
HE WAS RIGHT.** I argued against it on §35 — GENESIS is append-only on the box
and a shipped copy clobbers. That rule holds for the ordinary case and this is
the r194 exception: a REPAIR to existing rows, which r194 also had to make and
made in place. But an append can only reach the BOTTOM of the table, and a row
for r247 sitting after r258 would break the newest-row-is-last property the
land command's own ordering contract depends on. **In-sequence placement is only
possible by shipping the file.** ⚠️ It is safe here for one reason worth stating:
the copy was taken from HEAD immediately before packaging, so the lander's
append lands on a current file. That condition is the whole of §35's concern.

**v1.74 — 2026-09-05 — dtp r284 — S3.20: THE RE-BASELINE, AS A LEDGER RATHER
THAN AS A LIE.**

The last thread from the coverage report's first run. QQQ ran out of disk on
2026-09-03 and lost two streams for that day; both were chased to a conclusion —
`eod` overwritten by the next session's fixed-filename write, `ohlc` unwritten
and unrecoverable because DXFeed history is same-evening only and the backfill
came back STILL MISSING. Without a record of that, `--streams` flags both as GAP
forever, and **a permanent red is the one thing that stops a board being read** —
the CV.1 lesson this file has now learned three times, on a Sunday, on `shadow`,
and here.

🔴 **THE OPERATOR ASKED WHETHER TO UPLOAD PLACEHOLDER OBJECTS INSTEAD, AND THE
ANSWER IS NO.** `raw/` is the durable record and never deletes by design; an
object in it is a claim to every future reader that a box wrote something that
day. A synthetic `eod` would be indistinguishable from a real one, and
`WAREHOUSE_MAP.md` is generated FROM THE BUCKET precisely so it states what is
actually stored rather than what was intended. Satisfying a check by lying to it
is the named enemy here — output that renders cleanly while meaning something
other than it appears.

🔑 **SO IT IS A FOURTH CATEGORY, NOT A SUPPRESSION.** `ACCEPTED_LOSS` sits
beside `NOT_A_SESSION`, `PARTIAL_BY_DESIGN` and `DEAD`, and **it prints every
run** with the box, the reason and the date it was accepted. An absence quietly
removed from the board is as bad as one that cries wolf: nobody would ever learn
the fleet had a hole.

⚠️ **AND IT AUDITS ITSELF, WHICH IS THE PART THAT MATTERS.** If an entry's data
ever appears, the row renders **RESOLVED and the run FAILS**, telling the reader
to delete the entry — because an exemption nobody removes is exactly what would
suppress the next real gap on that stream. That is this category's own failure
mode, one level up, and A4 pins it. A2 and A3 pin that the ledger excuses only
the named box on the named day: a wildcard would have hidden the next outage.

`tests/test_stream_coverage.py` v1.2, **38 checks, born red 6**. ⚠️ A1c was
re-derived mid-build: it asserted the whole run exits 0, which is a claim about
the fixture rather than the feature — the fixture declares four streams while
the policy grades thirty, so every unlisted one legitimately gaps. The claim
that belongs there is that the accepted streams contribute nothing to the
failure count. ⚠️ And a first cut read the excused list out of `locals()`, which
persists across loop iterations — one accepted stream would have stamped its
exemption onto every stream after it.

**v1.73 — 2026-09-05 — dtp r283 — TWO SILENT REFUSALS, BOTH FOUND BY ASKING FOR
ONE ORDINARY THING.**

The whole finding came out of a single request — backfill one box's OHLC for one
date — which was refused twice in a row without ever saying so.

🔴 **RPT.12 — THE CAP.** `--stream-cap` defaults to 10, the fleet runs 15, so a
**one-box** batch exceeded it and the run stopped. And it is a hard stop
(`return 2`), not the warn-never-stop the file's header describes for a
neighbouring check. 🔑 **r53 already retired the fleet-wide copy of this guard**,
after the 2026-08-20 pare, in these words: *"it existed so a maintenance wake
could not put 29 boxes on the wire at once; the fleet is 15 and a normal session
already carried ~20 without strain."* This copy was never swept — the same shape
as the README fleet count that read 29 for nine days. The default is now 20,
**r53's own recorded number rather than one I invented**, env-overridable, and
labelled a prior.

🔴 **RPT.11 — THE CONFIRM.** With the cap raised by hand, the operator typed
**`Y`** at the LIVE backfill prompt and nothing happened. `[ "$GO" = "y" ]`
matches lowercase only, there is no else branch, and the run simply did not
occur. ⚠️ **That is worse than a refusal**: *declined* and *ran and did nothing*
are indistinguishable to the person watching. Six sites carried it; all six now
route through `_yes`, and the destructive ones state what they declined. ⚠️ **A
flag toggle must stay quiet**, which is why `_yes` is a pure predicate — one
helper that printed for both would be wrong at half its callers.

⚠️ **AND IT STILL REFUSES EVERYTHING ELSE.** C1b drives `n`, `N`, `no`, `sure`,
`ye` and empty. These prompts wake boxes, stop trading and delete rows;
loosening the check to *anything non-empty* would be a worse defect than the one
it replaces. **C3 is the check that matters most** — no lowercase-only
comparison survives anywhere in the menu, because repairing the site that bit
and leaving five others is exactly how this comes back (C.30).

`tests/test_confirm_and_cap.py` v1.0, **17 checks**, born red at HEAD. ⚠️ It
EXTRACTS `_yes` from `devtools.sh` and runs it in a subshell rather than sourcing
the file — `devtools.sh` ends in an interactive menu loop, and a fixture that
launched the menu would be a test with a side effect on the operator's terminal.
And the cap is read from the real `add_argument` default, not from the constant,
because a constant nobody wired is the r230 defect exactly.

**v1.72 — 2026-09-05 — otv4 r256 / dtp r282 — THE NIGHTLY RECLAIM WORKS. IT HAD
NO MUTUAL EXCLUSION, AND ITS FAILURES WERE INVISIBLE.**

🔑 **FIRST, WHAT THE FLEET PROVED, BECAUSE IT IS THE PART THAT SURVIVES.** The
r255 reclaim ran for real: **fleet `feed_store` + WAL went 23.2 GB -> 9.8 GB.**
MU 3.90 -> 1.40, META 2.60 -> 0.73, AMD 2.24 -> 0.70, SPX 2.30 -> 0.98. Thirteen
of fifteen WALs went to zero, and on a clean re-run with nobody else touching
the box, QQQ went **1.7 GB -> 260 KB** and TSLA **1.1 GB -> 268 KB**. No box
reported BUSY where the reclaim reached it, so **`stop_services` releases the
stores exactly as designed.** The checkpoint, the gated vacuum and the ordering
are all confirmed against real data. What was missing was a lock.

🔴 **THREE DEFECTS, ALL MINE, AND THE FIRST ONE HAD A WORKING PRECEDENT ONE FILE
OVER.** `s3_push.acquire_lock()` has guarded *every* invocation path since WH.6,
written because *"the timer and the conductor's `--verify` are different
entrypoints to the same work, and nothing else was stopping them overlapping"* —
and `retention_purge`, which **deletes**, had none. `_open()` then connected at
SQLite's five-second default, shorter than a single 2 GB delete. And the COUNT
was wrapped while the DELETE was not, so one locked table took `main()` down and
**the reclaim never executed** on the four boxes that lost the race.

🔴 **`head -3` IS WHY IT TOOK THREE ROUND TRIPS.** A traceback puts its cause
last; the phase read the first three lines. The operator saw an outermost frame
and a truncated path. ⚠️ **And the same truncation hid the reclaim verdict on
every box on every run** — the single line that says whether a 1.6 GB WAL came
back. Redirected to a file now, exit code captured before the pipe, `tail -12`.

⚠️ **S3.19 OPENED, AND IT IS THE ROOT CAUSE RATHER THAN THE SYMPTOM.** An ssh
timeout kills the local client and leaves the remote `python3` running. Two
option-14 fan-outs timed out on QQQ; their abandoned purges held the store open
and the conductor's checkpoint found it busy. The lock makes that harmless. It
does not make it visible, and that is the concrete case for SSM.

`tests/check_purge_lock.py` v1.0, **11 checks**, born red — L1 takes the lock in
a **second process**, because `flock` is per open-file-description and a
same-process check would pass against code that locks nothing (C.23). D1 holds a
**real exclusive transaction** rather than stubbing an exception, because the
finding is about a timeout and a stub would pin the handler and miss it. L3 pins
the SHIPPED defaults, since the cases shorten them to stay quick and a fixture
that agrees with itself proves nothing. `dtp check_conductor_purge` v1.2, born
red 2.

**v1.71 — 2026-09-05 — otv4 r255 / dtp r281 — TRANSFER, DELETE, **RECLAIM** —
AND THE WAL NOBODY HAD LOOKED AT.**

Operator, 2026-09-05: *"Transfer to s3, then delete, then vacuum. We need a
nightly hygiene program that aggressively scrubs the boxes after the session &
leaves only the required tenors."*

🔴 **DELETING ROWS RETURNED NO DISK, AND THIS PROJECT WROTE THAT DOWN ITSELF.**
`purge_verified`'s docstring read *"SQLite reuses freed pages and the store
reaches steady state."* Steady state is a PLATEAU AT THE HIGH-WATER MARK, not a
shrink. Measured fleet-wide: **18-34% of every `feed_store.db` is free pages**,
330-690 MB per box, inside files the purge has trimmed nightly since r162. That
stale note is replaced rather than left standing.

🔴 **AND THE WAL WAS LARGER THAN ANYTHING THE PURGE COULD REACH.** MU held a
**1.6 GB `feed_store.db-wal`**; META 1.1 GB, AMD 963 MB, AVGO 596 MB, CRM
500 MB. A WAL is reclaimed by a CHECKPOINT — seconds, no temp space — so it
runs first and unconditionally. ⚠️ **IT WAS INVISIBLE FOR AN HOUR BECAUSE THE
MEASUREMENT GLOBBED `*.db`.** WA §0.3 lists that exact incident: the WAL files
are `.db-wal`, and the biggest files on the box were excluded by the pattern
whose job was to find them. Same mistake, same week, mine.

🔴 **AND THE CHECKPOINT COULD NOT WORK WHERE IT WAS PLACED (DEP.6).** The
checker found this rather than confirming it: `wal_checkpoint(TRUNCATE)` returns
**busy** while another connection holds a read mark — 7.1MB fell to 4.4MB with
a reader open and to 0 with none. Both close paths purged with `optionsbot` and
`candle-feed` still running. Conductor **v2.2** releases the writers between the
verdict and the purge; `self_close` **v1.3** does the same after verification
succeeds. On the VERIFIED list only, stop and never disable.

🔴 **VACUUM IS GATED, NOT ATTEMPTED.** It writes a complete second copy, so it
needs free disk above the live size — and the four boxes that needed it most
(MU, NVDA, TSLA, META, all under 900 MB free) are exactly the four where it
would have failed. It refuses with the arithmetic printed, and `SQLITE_TMPDIR`
points at the data directory because `/tmp` is a 476 MB tmpfs.

🔑 **FOUR STORES GREW BY ABSENCE FROM EVERY LIST RATHER THAN BY POLICY.**
`plan_tick`, `plan_check`, `shadow` and `chain_snapshots` were in none of
`RETENTION_DAYS`, `ARTIFACT_DAYS`, `DERIVED_ARTIFACT_DAYS` or `NEVER_PURGE` —
nothing deleted them and nothing protected them either. ⚠️ They got their OWN
lists: `check_purge_pushed` C9 proves a `DERIVED_ARTIFACT_DAYS` table ships via
`push_series`, and these do not, so folding them in would have turned C9 red for
a TRUE reason — the fastest way to get a real check loosened. ⚠️
`chain_snapshots` closes a divergence rather than opening a policy: config has
declared 3 days since v4.4 and nothing ever read it.

🔴 **`shadow` IS DECLARED AND NOT ENFORCED, AND THAT IS WHY IT SHIPS AT ALL.**
The boxes hold the only copy of every date before 2026-08-26; arming it before
the re-push destroys exactly what S3.13 confirmed is recoverable. R6b pins that
an inert policy reports `-1`, never `0` — *not armed* and *found nothing* are
different facts.

**S3.14 REFUTED AND CLOSED.** Shadow is 21-40 MB, a third of one percent of the
volume. I raised it from a directory count without measuring a size; the
measurement kills it, and it is marked DEAD rather than quietly dropped.
**S3.16 opened:** MU holds 1.8 GB live against CVX's 0.20 GB on identical
policy, and r255's remaining-rows report answers it on the first armed run.

`tests/check_purge_reclaim.py` v1.0, **16 checks**, born red at HEAD, driving
real SQLite stores — the WAL, the free pages, the refusal and the inert policy
are all arithmetic about bytes and none of it is provable by reading source.
`dtp tests/check_conductor_purge.py` v1.1, born red 4. ⚠️ **C7 IS RE-DERIVED,
NOT PATCHED:** it asserted *"no VACUUM at takedown"*, which stopped being true,
and it would have passed forever because the conductor's own text never mentions
vacuum either way. What survives is the real invariant — one implementation of
the reclaim, and the conductor is not a second one.

**v1.70 — 2026-09-05 — dtp r280 — THE COVERAGE REPORT'S FIRST REAL RUN FOUND
NINE FLAGS AND SEVEN WERE MINE.**

Run by hand over 2026-09-01..09-04, which is exactly what S3.12 said had to
happen before the phase was wired. 🔑 **THE REPORT EARNED ITS PLACE AND NOT IN
THE WAY INTENDED:** it was built to find gaps in the bucket and what it found
first was three wrong declarations in its own policy table. That is the whole
argument for running a new alarm by hand before automating it, and the argument
holds whichever way the next run goes.

🔴 **(1) `prints` — SPX IS A CASH INDEX AND PUBLISHES NO TimeAndSale.** r95
already recorded that `prints` on a cash index renders n/a; I declared the
stream `EVERY` anyway, so it flagged SPX on all four days. Fixed with a
**per-symbol exception**, not by loosening the stream — a box that *cannot*
write a stream is a different fact from a stream nobody is graded on, and
collapsing them would stop the report noticing the day the other fourteen go
quiet. S12b pins exactly that.

🔴 **(2) `trades` IS CONDITIONAL.** `push_trades` is CDC, so a box with no
changed rows pushes nothing and absence means that box took no trades — a
market outcome. ⚠️ **CORROBORATED RATHER THAN REASONED FROM THE CODE:**
`derived_fire_snapshot` and `derived_plan_ledger` matched the trades count
**box-for-box on all four days** — 15/13/10/12 against trades missing 0/2/5/3 —
three independent streams agreeing on which boxes had no fills.

🔴 **(3) `shadow` IS LIVE, AND "NEVER INSTALLED ON THE v4 FLEET" IS FALSE.**
Measured on QQQ 2026-09-05: **32 date directories, newest 2026-09-04, and a
shadow systemd unit present.** The bucket said the same thing from the other
side the whole time — 15 boxes pushing every session, and `WAREHOUSE_MAP.md`
generated 09-01 showing `raw/shadow` at 160,978 objects over 7 days. Two
instruments already disagreed with the finding and nobody read them together.

⚠️ **AND THE COST IS FILED, NOT SOFTENED. S3.13:** the 2026-08-25 purge deleted
**492,945 `raw/shadow` objects** as a dead stream, on this belief. `raw/` is the
durable copy and never deletes by design; that one went through the console
grant. **What is actually lost is not established and must be measured before
it is described** — the boxes never purge shadow, so some of it may still be
box-side and re-pushable. **S3.14** records the other half: shadow is unbounded
on disk by *absence* from every purge list rather than by policy, QQQ holds 32
date dirs of high-frequency jsonl, and QQQ ran out of space on 09-03 — which is
what cost that day's `eod` and `ohlc`. ⚠️ **That link is plausible and NOT
measured**, and it is filed as a question rather than a cause.

**ASK.2's premise is falsified** and the row is rewritten: the ruling is no
longer *cut a dead stage or leave it* but **keep collecting a live stream or
stop it deliberately** — a different question with a different cost.

**THE TWO REMAINING FLAGS WERE REAL AND ARE EXPLAINED.** QQQ missing `eod` and
`ohlc` on 09-03 only, with its candles, series, journal and all seven derived
streams present — the box ran out of disk. `eod` is unrecoverable: `pnl_today
.json` is a fixed filename overwritten once per session and 09-04 landed for all
15 boxes, so it has already been replaced. `ohlc` is date-partitioned and may
survive on the box; `push_whole_files` keys on content hash per path, so a
normal pusher run would ship it. ⚠️ **A zero-byte file is the case to watch** —
`if not raw: continue` skips an empty file **silently**, which is an absence
that never announces itself.

`tests/test_stream_coverage.py` v1.1, **29 checks, born red 5 against v1.2** —
and the cases assert VERDICTS from `check_streams`, never that `STREAM_POLICY`
contains a string, because a test that reads the map back is the map agreeing
with itself (C.23). ⚠️ **S4 IS RE-DERIVED, NOT PATCHED:** it used `shadow` as
its DEAD example, so leaving it would have gone on certifying the exact
classification this revision corrects — the r233/r234 trap. It now uses
`theo_series`, which is genuinely dead.

**v1.69 — 2026-09-05 — otv4 r253 — DEP.5: THE WORKING AGREEMENT CATCHES UP TO
THE DEPLOY. DOCS ONLY.**

Operator, 2026-09-05: *"I no longer need you to print the landing/commit
commands going forward... now we use [the LAND item] in devtools. Maybe update
the working agreement that this is the preferred way we stage and commit files
now."*

**`WORKING_AGREEMENT.md` v4.3.** §15 is rewritten: the deploy is the devtools
item **`LAND a tarball from /home/ubuntu`**, with its dry run beside it. Its
archive rules — the `tar czf` build, the `.gz` strip that is not an invariant,
`tar xf` never `xzf`, unique names per delivery, no scaffolding — are unchanged
and survive as **§15a, struck rather than deleted** per r240's precedent,
because a row a later entry contradicts is a wrong answer and not history, and
that reasoning is still why the tarball looks the way it does.

🔑 **WHAT THE ASSISTANT STILL OWES IS THE PART NO GENERIC TOOL CAN SUPPLY.** The
archive, and a `land.spec` per half: `REPO` markers so the lander finds the
checkout rather than guessing a path (§3), `REV` and `DESC` as the one string
that becomes both the GENESIS row and the commit subject (§35), `ORDER` when a
second half depends on its first, `POS`/`NEG` content assertions, and `CHECK`
lines naming what must be EXECUTED. **The mechanics are generic; the gate is
specific, and only the author of the change can write it.** §15 says so
explicitly, so a future reader does not mistake "there is a menu item" for
"there is nothing left to do."

⚠️ **THE ITEM IS CITED BY LABEL AND THE NUMBER IS NAMED ONCE, AS OF A DATE.**
It is 54 today. Menu numbers come from a render-time loop counter, are never
stored or compared, and have moved twice in a week — **C.15** records that any
document naming an item by number is wrong the moment the next item lands, and
a rule file that rots inside a year is worse than one that says less.

🔴 **§33's LAND-ORDER SKETCH IS CORRECTED, AND THE DISAGREEMENT IS THE FINDING.**
It read `extract → verify → REGENERATE MAP → APPEND GENESIS → git add -A`, while
the operator's own standing rule is *"NEVER `git add -A`; stage shipped files by
name"*, written after a stray `fit_report.py` was pushed off main. **Two
documents disagreed and the looser one was the one the code followed**, for four
months, until dtp r278 measured it. The sketch now shows named staging and the
`RUN THE CHECKS` stage — before r278 this command GREPPED and never executed
anything, which is §0.6's own shape: the r201 gate asserted a function existed
and the file parsed, and both were true of the broken version.

§19's scope is narrowed rather than deleted: it still governs every other
command the operator runs — fleet fan-outs, queries, studies — and now says
plainly that it does not cover the land.

**v1.68 — 2026-09-05 — dtp r279 — DEP.4: ALL HALVES LAND, OR NONE REACHES
ORIGIN.**

Operator, 2026-09-05: *"make sure all will land or none."*

🔴 **THE FAILURE IS OBSERVED, NOT HYPOTHETICAL.** Landing `r277_r2` before
`r276_r2` in the sandbox: the dtp half passed its gate, committed **and
pushed**, and only then did the otv4 half correctly refuse on a GENESIS row
`r276` had not yet written. Origin ended up holding the code with no backlog
entry, and a re-run then died at `git commit` with nothing left to stage. v1.1
landed halves sequentially and stopped at the first failure — one-at-a-time,
not all-or-nothing.

🔑 **A PRE-FLIGHT OF EVERY GATE WOULD NOT HAVE WORKED, AND THAT IS THE WHOLE
DESIGN.** The obvious fix is *"verify every half before landing any"* — and it
is wrong here, because a half is ALLOWED to gate on an artifact an earlier half
produces. `r277_r2`'s otv4 half asserts a GENESIS row that `r276_r2`'s otv4 land
appends. Pre-flighting it before r276 landed would fail a gate that is not
actually failing; the dependency is real and the ordering exists to serve it.

🔑 **SO THE SPLIT IS COMMIT vs PUSH, WHICH IS WHERE THE IRREVERSIBILITY SITS.**
Phase 1 verifies and commits each half LOCALLY, in order, so a later half still
sees an earlier half's landed files. Nothing is pushed. Phase 2 pushes every
repo and only runs if every half reached a commit. A phase-1 failure rolls every
repo this run committed to back to the SHA it was on before the run started —
**origin never sees a partial delivery**, which is the property that matters
when fifteen boxes pull from it.

⚠️ **THE ROLLBACK IS `reset --soft`, NOT `--hard`.** A hard reset would also
revert an unrelated tracked file the operator had edited — the exact reason §35
already refuses a blind `git checkout -- .` on a failed gate. Soft moves HEAD
back and leaves the tree, so a rolled-back half looks EXACTLY like a half that
failed its gate today: files present, uncommitted, recovery printed. Nothing of
his is destroyed to tidy up after a delivery of mine. ⚠️ A rollback that itself
fails is NAMED, never swallowed — a silent one would leave him believing his
checkout and origin agree when they do not.

⚠️ **AND THE HONEST LIMIT IS STATED RATHER THAN PAPERED OVER.** Phase 2 pushes
to two independent remotes; that is not a transaction and cannot be made one.
What it CAN be is ordered last, back to back, with nothing between them but
network — and if one fails, the report names which repo is ahead of its remote
and the one command that fixes it. A pushed half is **not** auto-reverted:
undoing something already on origin is a decision for a human, not a cleanup
step.

`tests/check_land_sh.py` v1.2, **35 checks, born red 4 against v1.1** — and A1b
is the one that carries the weight because it asserts on the **BARE REPO**, not
on the checkout: *"the local HEAD moved back"* is a weaker claim than *"origin
never saw it"*, and origin is what the fleet pulls from. Against v1.1 it reports
exactly the observed defect, `r999` on remote one while remote two sat at base.
⚠️ **A1c IS THE CASE THAT CATCHES A LAZY ROLLBACK:** `--hard` would pass every
other case here and silently revert a file the operator had mid-edit. ⚠️ **AND
MY FIRST DRAFT OF A1c WAS WRONG AND THE CODE WAS RIGHT** — it edited a file the
delivery legitimately overwrites, asserting a property no lander could have, and
went red against correct code. Re-derived onto a file the payload does not ship.

**v1.67 — 2026-09-05 — dtp r277 — S3.10: PER-STREAM, PER-DAY, PER-BOX COVERAGE
— AND THE FOUR WAYS IT COULD CRY WOLF.**

🔑 **THE TOOL ALREADY EXISTED AND WAS EXTENDED, NOT DUPLICATED.**
`warehouse_coverage.py` v1.1 is LIST-only, trading-day aware via
`market_calendar.is_trading_day`, and already carries `NOT_A_SESSION` and
`PARTIAL_BY_DESIGN`. A second coverage tool would have been the WA §35 rot.
**ADDITIVE:** `--streams` is its own report with its own exit code, and the v1.1
verdict suite is byte-identically green before and after.

🔑 **COVERAGE MEANS TWO DIFFERENT THINGS AND EVERY ROW SAYS WHICH.** Read from
`s3_push.py`: `push_derived` writes ONE OBJECT PER TABLE PER RUN (line 959),
`push_series` batches at 50,000 — while `push_jsonl_tree` and `push_trades`
write one object per RECORD. So a count on `raw/signal_journal` is volume and
the same count on `raw/derived_plan_check` is push RUNS, which is how 5,389
objects sat beside 2.38M rows with nothing reconciling them. 🔴 **A DERIVED ROW
IS LABELLED `pusher`, because its `dt=` is the PUSH day (C.9)** — it can say
whether that box's pusher ran and CANNOT say whether that day's rows are
complete.

⚠️ **"ABSENT" IS NOT ONE FACT, AND THE NEGATIVE CASES ARE THE ONES THAT MATTER.**
`chain_snapshots` is written only by a box that TRADED; `shadow` was NEVER
INSTALLED on the v4 fleet; `theo_series` and `underlying_series` were
unsubscribed at r118/r125b. Grading any of those as a gap puts a permanent red
on the board — v1.1 learned this on a Sunday.

🔴 **A SILENT BOX IS ONE DIAGNOSIS, NOT TWENTY.** A box that pushed nothing at
all reports as `BOX_SILENT` and its absences are attributed there rather than
counted against every EVERY-stream — v1.0's own `PUSH_DEFECT` vs `OWNER_DOWN`
split generalised. Without it the first fleet-wide outage produces twenty red
lines for one cause and drowns the single-stream gap on another box, which S2c
pins by keeping exactly that gap visible underneath.

⚠️ **THE PANEL IS `selector.PANEL`, IMPORTED** — r185 records what one fact
living in three documents cost. An empty `PANEL` means discretionary selection
is on, so the mode REFUSES rather than grading against a guess (dtp r250).
⚠️ **AN UNDECLARED STREAM IS REPORTED, NEVER SKIPPED** — a tool that quietly
shrinks its own scope is as misleading as one that over-reports (v1.1's finding).
⚠️ **`NVDA_EXT` NORMALISES TO `NVDA`** — r194's guard matched a name FORMAT
rather than an IDENTITY and proposed deleting the extended tape of every panel
symbol.
⚠️ **COST:** presence is ONE delimited LIST per stream-day; counts page and are
opt-in, **pinned by COUNTING PAGINATOR CALLS** rather than by reading code
(dtp r253).

`tests/test_stream_coverage.py` v1.0, **24 checks**, born red at `bb27458`.
⚠️ **THE BORN-RED IS WEAK HERE AND THAT IS WORTH SAYING:** unlike r276, where
`load_derived` existed and misbehaved, this is a NEW capability, so at HEAD
there is nothing to be wrong. The proof that carries weight is S2b-S7b, plus
S11 which measures the REAL rendered line (C.23) and S11b which reads the VALUES
back, because r216 is the other half of that lesson.

**S3.10 closed. S3.12 opened:** the phase is NOT wired into `eod_analysis` yet —
the `CONDITIONAL` and `DEAD` classifications have never been checked against the
bucket, and Monday is the first tape for six sweep revisions. ⚠️ **RE-ISSUED AS
`_r2`:** the code half is byte-identical; only this file and the specs moved.
dtp red set unchanged: 6 before, 6 after.

**v1.66 — 2026-09-05 — dtp r276 — 🔴 THE CDC COLLAPSE KEYS ON THE TABLE'S OWN
PRIMARY KEY. `_rid` WAS NEVER AN IDENTITY.**

🔴 **r266 FIXED AN UNDER-COUNT AND OPENED AN OVER-COUNT IN THE SAME MOTION.**
Scoping `_rid` to the `dt=` partition stopped two sessions' rowids colliding —
measured, real, and correct as far as it went. But `push_derived` files every
CHANGED row under the **push** day, so one CDC row touched on two days lands in
two partitions, and a partition-scoped key keeps both copies.

🔑 **THE IDENTITY WAS IN THE SCHEMA THE WHOLE TIME.** Eight of the nine derived
tables declare a `PRIMARY KEY` the box already enforces — `plan_check` is
`(ts_epoch, symbol, strategy, direction, check_name)`, `strategy/plan.py:313`.
`screen_plan_gates` has grouped its per-tick panel on exactly that key since dtp
r271, so this is not a new idea; it is the one already working in the consumer
that had to be right, applied to the reader. `DERIVED_NATURAL_KEY` is **diffed
against otv4's own `CREATE TABLE` statements** (N4b), so it cannot drift into a
second definition of identity.

⚠️ **r266's STATED MECHANISM IS NOT ESTABLISHED, AND THIS DOES NOT REST ON IT.**
Its comment says rowids restart because *"boxes purge and rebuild their derived
stores."* `warehouse/retention_purge.py` at HEAD touches the derived store ONLY
for `DERIVED_ARTIFACT_DAYS` — `indicator_series`, `fork_series`,
`surface_series` — and **`plan_check` and `plan_tick` are in neither that list
nor `NEVER_PURGE`**: nothing deletes them and nothing protects them by name. A
box REBUILD restarts rowids; the nightly purge does not. Recorded rather than
quietly corrected, because a landed comment naming the wrong cause is what the
next reader will reason from.

🔑 **THE COUNT IS NOW SELF-VERIFYING** — distinct primary keys per ET day IS the
row population, which is what made *"a 5-day range returned 2.38M `plan_check`
rows and there is no way to know whether that is complete"* unanswerable.
⚠️ **THE FALLBACK IS COUNTED OUT LOUD.** `character_ledger`'s key is
`id INTEGER PRIMARY KEY AUTOINCREMENT`, which in sqlite IS the rowid, so it
keeps r266's partition-scoped key; any row missing a component falls back the
same way and the banner names the rule that ran and counts the fallbacks.
⚠️ **ABSENT IS TESTED AS `is None`, NEVER FALSINESS** — `direction` is
`NOT NULL DEFAULT ''` and `ts_epoch` can be `0.0` (**C.45**).

`tests/test_natural_key.py` v1.0, **17 checks, born red 10/17 at `bb27458`** —
N5 goes red on the BEHAVIOUR (*"one row pushed on two days loaded as 2"*) rather
than on the absence of the helper, because a born-red that only says *"the fix
is not installed"* proves installation and never correctness.
`tests/test_cdc_partition_key.py` **re-derived to v1.1, not patched**: its C2
asserted the 3-part key, the exact shape being replaced, so leaving it would
have certified the defect on every run — the r233/r234 trap.

**BFLY.12 and BFLY.13 closed by dtp r275**, struck in place per r240's
precedent. **S3.10** and **S3.11** filed. ⚠️ **RE-ISSUED AS `_r2`:** the first
cut was built against BACKLOG v1.64 and would have overwritten r278's DEP
entries; the code halves are byte-identical, only this file and the specs moved.
dtp red set unchanged: 6 before, 6 after.

**v1.65 — 2026-09-05 — dtp r278 — DEP.1: THE UNIVERSAL DEPLOY, AS A MENU ITEM
— AND NINE OF ITS TEN STAGES ALREADY EXISTED.**

Operator's spec, 2026-09-05: a devtools option that finds a tar in
`/home/ubuntu`, unpacks and stages it, verifies the write map, the file map,
the file versions, the changelog and the GENESIS append, *"any smoke tests or
canaries are verified"*, commits, and cleans up.

🔑 **`tools/land.sh` (r235) ALREADY DID NINE OF THOSE TEN**, and has done all
four of today's lands end to end. Rebuilding it would have been the WA §35 rot
— two implementations of one job, and whichever gets updated becomes the truth
while the other rots. So r278 adds the missing stage and fixes what the
hand-run was hiding.

🔴 **(1) IT RAN NO CHECKERS.** The content gate greps for a distinctive line and
never EXECUTES anything — which is precisely the r201 shape §0.6 names: the gate
asserted a function existed and that the file parsed, and both were true of the
broken version. `CHECK <path>` directives now run in the repo and must exit 0.
⚠️ **AND A HALF THAT SHIPS CODE AND DECLARES NO CHECK IS REFUSED**, detected
from the payload rather than trusted to the author, because the realistic
failure is a FORGOTTEN check and *nothing was executed* must not read like
*everything passed*. A docs-only half legitimately has nothing to run and says
so out loud — "not applicable" and "passed" must never look alike (r183).

🔴 **(2) `git add -A`.** The operator's standing rule is the opposite — *"NEVER
`git add -A`; stage shipped files by name"*, written after a stray
`fit_report.py` was pushed off main — while WA §33's sketch of the land order
says `git add -A`. Two documents disagreed and **the looser one was the one in
the code.** Every path is now named: the payload's own file list plus the two
regenerated maps and the GENESIS row. C3 plants an unrelated dirty file and
requires it out of the delivery commit; only a dirty-tree fixture can tell the
two versions apart.

🔴 **(3) THE ARCHIVE IT DELETED WAS A GUESS.** `ls "$HOME"/*_r*.tar* | head -1`
takes the first glob match and the cleanup `rm -f`s it — and on 2026-09-05 he
had r276 and r277 in `/home/ubuntu` at once. `LAND_ARCHIVE` names the file
`deploy.sh` actually extracted; without it an ambiguous glob deletes NOTHING and
says so. Untidy is recoverable; deleting the wrong tarball is not.

**NEW `tools/deploy.sh`** is only the three things standing between the lander
and a menu item, each a real gap: FINDING the archive (prompting on ambiguity
rather than picking), DISCOVERING the halves from their own specs (the operator
should not have to know a tarball is *"dtp otv4"*), and ORDERING them via a new
optional `ORDER n` directive — because a two-repo delivery whose second half
cites the first must not land backwards, which is exactly r277's otv4 half
gating on r247's GENESIS row. 🔑 **IT EXECS THE LANDER FROM THE ARCHIVE**, repo
copy as fallback: a delivery that improves the lander has to be landed by the
improved copy or the improvement is never exercised on the one delivery that
could prove it — and the fallback is what keeps archives cut before r278
landing through the item unchanged.

`tests/check_land_sh.py` v1.1, **27 checks, born red 8/19 against v1.0** — C1b
lands a delivery whose declared check exits 1 (proving v1.0 executed nothing),
C3 finds `STRAY.txt` in the commit (proving `git add -A`), C4b finds the guessed
archive deleted. **D1-D5 drive `deploy.sh` itself end to end** against a real
two-half tarball in a real `$HOME`, and **D2c requires the backwards order to be
REFUSED**, because an ordering never tested against the wrong order is one
nobody knows works (§17). `docs/MENU_INVENTORY.tsv` regenerated **after reading
the diff** — 2 labels added, 0 removed, 0 commands changed — never reflexively,
which turns the proof tool into a rubber stamp.

**DEP.2 opened, and it is the sharper finding.** `land.sh`'s gate uses bare
`grep -q`, so `POS docs/GENESIS.md|**r247**` PASSED against a GENESIS with no
`r247` in it: BRE reads the trailing `**` as *zero or more 7s* and the pattern
degenerates to `r24`. **`**rNNN**` is this repo's own GENESIS idiom.** Not fixed
here, deliberately — the lander that changes the lander is verified by the old
lander, and that change deserves its own born-red rather than riding in.
**DEP.3** records that LAND.1 is reversed at the operator's own request, so the
ledger does not contradict `menu_registry.sh` v1.10.

⚠️ **AND r276/r277 ARE SUPERSEDED ON THIS LINE ONLY.** Their otv4 halves were
cut against v1.64 and would overwrite this entry. They are re-issued as `_r2`
against v1.65/v1.66 and land AFTER r278 — through the new menu item, which is
the proof run.

**v1.64 — 2026-09-04 — r246 — FIT.2 AND TCS.9 CLOSED — AND FIT.2 WAS FILED
WRONG.**
🔴 **r239'S SPLIT WAS IN A THIRD PLACE.** `gate_report` kept its own
`DISPATCH_ALIAS` and was **missing `ORB` and `SweepForLeg2`**, so the ORB's
`fired()` arrived as `"ORB"` and never resolved. r239 fixed the notes writer;
the plan board had it right since r147; this one was never told.
⚠️ **BUT IT IS NOT A DUPLICATE, AND FIT.2 SAID IT WAS.** I filed it as *"two
copies of one map"*. `plan.DISPATCH_ALIAS` maps a dispatch label to the **class
name**; `gate_report`'s maps it to **the reporter's own internal name**, and
`GexPinButterfly` (lowercase x) is live — `gex_pin_butterfly:271` calls
`blocked("GexPinButterfly", …)` while dispatch fires under `"GEXPinButterfly"`.
**Merging them would have broken that reconciliation.** Composed instead, with
the local layer last so a reporter name always wins, and the import degrading to
local names on failure because this file never raises.
🔑 **TCS.9 — THE COPY IS FINE; THE MISSING COMPARISON WASN'T.** The cascade
harnesses keep local constants deliberately, so the cascade can be reasoned
about without importing config. But r238 parked `TCS_ENTRY_END_ET` at (0,0) and
both still read (14,0) — **for a day they modelled a TCS that traded** — and
r241 restored (14,0), making them correct **by accident**, which is not the same
as correct. `check_cascade_constants.py` now compares every mirrored constant
and **was verified to go red against config parked at (0,0)**, the exact drift
it was written for. Same treatment `ORB_NO_ENTRY_AFTER_ET` already had.
⚠️ **AND IT REFUSES TO PASS ON NOTHING** — C2 fails if the parse stops finding
the constants, so a rename cannot produce a cheerful green having verified
nothing.
`check_cascade_constants.py` v1.0, 8 checks. `check_note_label` → 9. **87/87.**

| id | question | state |
|---|---|---|
| **FIT.2** | Not a duplicate — a missing composition. Closed by r246. | ✅ **CLOSED r246** |
| **TCS.9** | Local copies now compared against config. | ✅ **CLOSED r246** |

**v1.63 — 2026-09-04 — r245 / dtp r275 — 🔴 THREE INSTRUMENTS MISLED IN ONE
EVENING. ALL THREE READ A PROXY INSTEAD OF THE THING ITSELF.**

🔴 **BFLY.12 — the stop-forensics screen reported 419 trades where there are
20.** ~399 unclosed rows with `pnl 0` and `exit_reason None` sat in the SURVIVED
group. `RP.COLS` has carried `status` the whole time and the screen never used
it. Now keyed on a **closing fact** — a non-empty `exit_reason` — rather than a
status spelling, because this project has twice this week been bitten by a value
renamed underneath a name check. The count is labelled **CLOSED** so 419 cannot
recur silently.
🔴 **BFLY.13 — the verdict line read the MFE ratio and ignored `mfe_bars`.** It
printed *"the stop is taking trades that were working"* when the column beside it
said the opposite: **winners peak at bar 141–305, the stopped trades at a median
of bar 5.5.** The operator was one step from removing a stop on the strength of
that line.
🔑 **THE BAR FLOOR NOW COMES FROM THE WINNERS, NOT FROM ME.** A trade "was
working" if it traded above entry **and** peaked no earlier than the earliest
winner in that sample. Hard-coding a threshold would be a number I chose.
⚠️ **AND THE STRICTER TEST CORRECTS MY OWN CHAT NUMBER.** I said *"2 of 13 share
the winners' signature"* using a loose bar>15 cut. Against the winners' own floor
of **bar 141**, only CVX at 144 qualifies — **1 of 12**, against a break-even
needing 9 of 13. The case against removing the stop is stronger than I stated.
🔴 **AND `check_ledger_parity`'s OWN OPEN LIST WAS WRONG.** It asked whether
"OPEN" appeared anywhere in the state cell; the older rows carry a long
`◐ PUSHED…` narrative there containing "OPENED" and "opening", so **CLOSED items
read as open — ten false positives out of 25.** I recommended work on BFLY.2 as
though it were live and then argued from a defect r197 had already fixed. **The
true open list is 23.** L6 pins the five markers against a fixture.

⚠️ **THE COMMON FAULT: a proxy for the thing.** A status inferred from a row's
presence, a "was working" inferred from a ratio without its timing, an open
state inferred from a word inside a paragraph. Each was cheap to write and each
produced a confident wrong answer about a live trading decision.
`test_bfly_stop.py` → 21 checks; `check_ledger_parity` → 8. **86/86 otv4 green,
no new dtp reds.**

**v1.62 — 2026-09-04 — r244 — 🔑 ALL THREE PIN MEASURES REACH THE SNAPSHOT.
NO MEASURE OF PIN STRENGTH HAS EVER BEEN VALIDATED.**
🔴 **THE STATE OF THE EVIDENCE, STATED PLAINLY.** The butterfly gates on
`pin_concentration` (29% fail), `pinning` (53% fail) and `pin_em_fraction` (58%
fail). **None of the three has ever been tested against an outcome.** They live
in `plan_check`, which has no `trade_id`, so nothing can join them to a P&L.
The thresholds are priors somebody chose, not fits — consistent with r152
deleting the scorer for selecting losers, and with every v4 row being UNGRADED
by construction.
⚠️ **AND THE ONE VECTOR SCREEN THAT HAS RUN FOUND NOTHING.**
`screen_entry_vectors` scored **sixteen** point-in-time vectors over 152 runaway
trades; the best separation was **AUC 0.54** against a **0.19 noise floor in its
own fixture**, and `adx` came in at 0.47 — *below* chance. It never covered the
pin fields.
🔴 **INSTRUMENTING ONLY THE EM FRACTION WOULD HAVE BEEN WORSE THAN USELESS.** A
study three weeks from now could have concluded *"EM predicts nothing"* while
the real signal sat in a field nobody recorded — and that negative would have
been believed. r243 + r244 record all three.
⚠️ **RAW, NOT THRESHOLDED.** The gate's pass/fail is already in `plan_check`;
what was missing is the VALUE. A study cannot fit a boundary it can only see one
side of.
⚠️ **SEPARATELY, NOT COMPOSITED** — r224: *a composite that separates tells you
nothing about which part did the work.*
⚠️ **NOTHING ACCRUES RETROACTIVELY.** The 20 banked butterflies stay
unmeasurable on all three.
`check_snapshot_pin.py` → 11 checks. **86/86 green.**

| id | question | state |
|---|---|---|
| **BFLY.14** | With ~3 weeks of snapshots, score `pin_concentration`, `gex_environment` and `pin_em_fraction` **separately** against outcome. The precedent says expect nothing: 16 vectors, best AUC 0.54, noise floor 0.19. A null result here is a real finding — it would mean the fly's three gates are priors with no evidence, and the win rate has to come from somewhere else entirely. | 🔲 OPEN |

**v1.61 — 2026-09-04 — r243 — 🔴 THE PIN AND ITS EM FRACTION REACH THE
SNAPSHOT — AND THREE BUTTERFLY LEVERS DIED ON EVIDENCE FIRST.**

## WHAT THE EVENING ACTUALLY FOUND

🔴 **EVERY butterfly loss is a premium stop.** 13 losses, all `stop_24/25/26%`,
**−$2,393.50**, matching the 13 losers to the dollar. It has never lost to the
market — only to its own stop, at a 16–26 minute hold, while its 7 winners run
to `hard_close` at 289 minutes for **+$2,714**.
🔴 **BUT THE MFE STUDY REFUTED REMOVING THE STOP.** 10 of 13 traded above entry
before being cut — and the column beside it says why that is not the finding it
looks like: **winners peak at bar 141–305; the stopped trades peak at a median
of bar 5.5**, ten of twelve within 15 bars at 1.03–1.49× and then fade. That is
a pop on entry noise, not a trade working toward the pin. **Only 2 of 13 share
the winners' late-peak signature, against a break-even of 9 of 13** (average win
+0.72× the debit; a stop costs 25% of it, no stop costs 100%). Operator, after
seeing it: *"I'm already convinced not to change the window or remove the stop."*
⚠️ **MY OWN SCREEN'S VERDICT LINE WAS TOO CRUDE** — it printed *"the stop is
taking trades that were working"* off the MFE ratio alone while ignoring
`mfe_bars`, which is the column that decides it.
⚠️ **AND THE 09:45 FIRES WERE THE DEFECT, NOT THE DESIGN.** I read r196's
comment describing the fault as current behaviour and told the operator his own
correction had not happened. `EARLIEST_ET` is 12:00, FOUNDATIONAL, passed as its
own relaxed value so it cannot widen. **Second time in one hour I read a
historical entry as a live state** (the first was BFLY.2's blocking, closed at
r197).

## THE FIX THAT SURVIVED

🔑 **`pin_strike` and `pin_em_fraction` now ride the fire snapshot.** The EM band
is 0.30–1.00 and hard-capped, and the live question — *do the winners sit lower
in the band?* — was **unanswerable**: `plan_check` carries the value on every
tick with **no `trade_id`**, and `fire_snapshot` is keyed **by `trade_id`** and
carried no pin and no EM.
🔑 **SAME SHAPE AS r240** — computed, used for a decision, never written where
the outcome could be joined to it. The bridge existed; it did not carry the
field.
⚠️ **DERIVED FROM ctx, NOT PLUMBED**, using the strategy's own
`expected_move()` — so it is the fraction **the gate used**, not a second
definition of it. Emitted for **every** strategy, because a field present only
where someone expected to need it is a field no study can ask a new question of.
⚠️ `None` when unmeasurable, `0.0` for a pin at the money — opposite facts. And
it cannot raise: `capture()` runs on every fill, so S4 drives four degenerate
contexts.
⚠️ **NOTHING ACCRUES RETROACTIVELY.** The 20 butterflies already banked stay
unmeasurable.
`tests/check_snapshot_pin.py` v1.0, 7 checks, born red. **86/86 green.**

| id | question | state |
|---|---|---|
| **BFLY.11** | **Do the winners sit lower in the EM band?** Answerable once ~3 weeks of snapshots carry `pin_em_fraction`. If they do, the lever is **lowering** `EM_MAX_FRAC`, not raising it — a pin a full EM away is the loosest end of the band and the least likely to convert. | 🔲 OPEN |
| **BFLY.12** | `screen_bfly_stop` reported **419 trades** where there are 20 — ~399 rows with `exit_premium 0.00`, `pnl 0`, `reason None` are unclosed/non-terminal. `RP.COLS` carries `status` and the screen never filtered on it. The quantiles are computed off real rows so the finding stands, but the counts are junk. | ✅ **CLOSED dtp-r275** — keyed on a CLOSING FACT (a non-empty `exit_reason`) rather than on a `status` spelling, because a value renamed under a name check has bitten this project twice in one week; the count is labelled CLOSED so 419 cannot recur silently. `test_bfly_stop.py` B6. |
| **BFLY.13** | The verdict line should read `mfe_bars`, not just the MFE ratio. As written it would call a 1-bar pop "a trade that was working". | ✅ **CLOSED dtp-r275** — 🔑 **AND IT CORRECTED THE NUMBER IN THE OPERATOR'S FAVOUR.** The bar floor now comes from the WINNERS in that sample, not from a threshold anyone chose. Against the winners' own floor of bar 141, only CVX at 144 qualifies — **1 of 12, against a break-even needing 9 of 13** — so the case against removing the butterfly's stop is STRONGER than it was stated in chat. B5 pins that the ratio alone says 10 of 12 while `mfe_bars` says 1: opposite conclusions from the same rows. |

**v1.60 — 2026-09-04 — r242 — 📌 DOCS ONLY. DISP.1: THE REGIME QUESTION IS
ASKED ONCE FOR DEBITS AND N TIMES FOR CREDITS.** Operator, 2026-09-04: *"why
are the credit trades even polling during that time at all… could we move the
window further upstream in the decision layer so it doesn't start asking until
it's time?"*

🔑 **THE MORNING HALF ALREADY WORKS THAT WAY.** `_afternoon_debit_blocked()` is
evaluated **once at the top of the tick** (`main.py:3371-3372`), before any plan
is polled, and it is **keyed on STRUCTURE, not on a name list** — the cutoff
reads `_STRUCTURE_BY_NAME`, which records what each strategy BUILDS. Its own
comment records why: v3 held a name list, **two of the three names were deleted**
while `RunawayContinuation` was never added, and it *"would have been silently
EXEMPT from the cutoff. An allow-list of names rots."*
🔴 **THE AFTERNOON HALF HAS NO MIRROR.** There is no `_morning_credit_blocked`.
`CREDIT_ENTRY_START_ET` is enforced **only inside each strategy**, as a declared
`entry_window` condition. So every credit strategy is polled every tick from the
open, and each one checks its own clock on the way in.
⚠️ **AND THE RECORD HIDES IT.** `t.dormant()` deduplicates — the first tick
outside the window writes a row and every identical tick after is silent. That is
why `entry_window` shows **410 failures against 61,641 passes**: the 410 are
*transitions*, not ticks. The morning polling is real and nearly invisible.

## THE SHAPE

🔑 **A mirror gate reading the SAME map, at the SAME point in the tick.** Not a
schedule in `main.py` and not a per-strategy declaration read by dispatch — the
authority already exists and is already structure-keyed.
⚠️ **IT DISSOLVES THE MUTE RISK I RAISED.** I first proposed each strategy
exposing `ENTRY_WINDOW` for dispatch to read, and warned that a wrong
declaration would **silently mute a strategy** with a plausible NOT ASKED
reason. That does not apply to the mirror: the map is already the authority for
the debit half, its default is already defined and restrictive (`long_debit`),
and a credit strategy skipped before 11:31 **would have refused itself anyway.**
Same map, same answer, asked once instead of thousands of times — **behaviour
identical by construction; only the record changes.**
🔑 **THE RECORD CHANGE IS THE GAIN:** `NOT ASKED — before the credit window`
instead of morning polling deduped into nothing.
⚠️ **AND IT ENDS SINGLE-POINT ENFORCEMENT.** The strategy's own `entry_window`
check is currently the ONLY thing between a credit spread and a morning fill.
Two constant faults this week were exactly that class: `TCS_ENTRY_END_ET` was a
placeholder nobody chose (r238), and `SWEEP_CS_MAX_AGE_BARS` was a name that did
not exist (r230). The strategy check STAYS — the same declaration read twice is
not duplication, and the second read is what catches a disagreement.

⚠️ **NOT BUILT TONIGHT, DELIBERATELY.** It touches the dispatch path on the eve
of the first observation of five sweep revisions (r230, r231, r233, r234, r241),
none of which has seen a tick. A zero result on Monday must be attributable.

| id | question | state |
|---|---|---|
| **DISP.1** | Mirror `_afternoon_debit_blocked` with a credit-side gate reading `_STRUCTURE_BY_NAME` at the same point in the tick. `vertical` before `CREDIT_ENTRY_START_ET` → `_plan_skip`. Behaviour-neutral by construction; the gain is a truthful record and enforcement above the plans. **Build after Monday's observation.** | 🔲 OPEN |
| **DISP.2** | A checker pinning that every credit strategy's window starts at or after `DEBIT_DIRECTIONAL_CUTOFF_ET`, so the two regimes cannot silently overlap. Would have caught both of this week's constant faults. | 🔲 OPEN |
| **DISP.3** | ORB and RunawayContinuation declare **no window constants at all** — their eligibility is entirely the cutoff. Fine today; worth naming because a future strategy with neither a declared window nor a structure entry is invisible to both gates. | 🔲 OPEN |

**v1.59 — 2026-09-04 — r241 / dtp r272 — 🔴 THE AGE GATE IS REMOVED, NOT
RAISED — AND THE MEASUREMENT THAT SHOWS WHETHER r234 LANDED.**
🔴 Operator, 2026-09-04: *"I don't give a rat's ass how old the level is, it's
still a level. Why are we still measuring the age of them?"* **Because I only
half-shipped his 2026-08-11 ruling.** SWP.5 said *"LIVENESS REPLACES THE
CLOCK"*; r230 found it had never reached the code and **raised the ceiling 6 →
48 instead of deleting the gate.** That was my call, not his.
🔑 **AGE MEASURES THE RAID, NOT THE LEVEL.** A level swept at 09:45 that has
held since is the *same level* at 13:00 — arguably better for having held
longer. And levels are swept all day; the morning's is not the only one on the
board, which is the operator's point and it kills the "morning event, afternoon
window" chain I had built on top of it.
🔴 **MEASURED FLEET-WIDE, 08-31..09-04:** `age` failed **46,791 of 61,641
(76%)**, and on **333 ticks — 26% of every tick that was ONE gate short — it
was the only thing refusing.** Complete setups, declined for being old.
⚠️ `invalidated` already answers this correctly and fails 73% — price accepting
through a level is a market fact, not a defect. `age` was a second, worse proxy
for a question that gate settles.
⚠️ **THE MEASUREMENT SURVIVES** — `sig.sweep_age_bars` still reaches the row.
The gate goes, the number stays, because age is useful for FITTING.
⚠️ **AND UNMEASURABLE IS NOT OLD.** The 999 sentinel refuses under its own name
(`sweep_unmeasurable`): a data fault, not a staleness judgement.

## THE MEASUREMENT — dtp r272

🔑 **A MIN/MAX CANNOT ANSWER WHETHER r234 WORKED.** `wing_r_best` failed 58,205
times over `0.0000 .. 0.9841`, and r234's bar sits at the equivalent of **0.15**
on that scale. A median of 0.60 and a median of 0.02 report **identically** as a
range and mean opposite things: the first says most of those 509 sole-blocker
ticks now fire, the second says r234 barely touched the sweep and the anchor
distance is still the problem. The screen now prints p10/p25/median/p75/p90 per
rung.

## THREE FRAMINGS I GOT WRONG, IN ORDER

⚠️ I claimed the window and the debit block were **redundant**. Then that they
**overlapped**. Both wrong: `DEBIT_DIRECTIONAL_CUTOFF_ET` 11:30 ends debit
entries and `CREDIT_ENTRY_START_ET` 11:31 begins credit entries — **they never
compete**, and the debit block is a backstop for a position still running, not
a gate on entry. The window is the design and was never the problem.
⚠️ And I built a "sweeps happen in the morning, the window opens in the
afternoon" causal chain **on top of the age gate that shouldn't exist**.

`tests/check_age_gate_gone.py` v1.0, 9 checks, born red 7. `check_sweep_liveness`
**re-derived** — it pinned the ceiling. `check_ledger_parity` gains r226 to its
known-rowless set: **r240's own GENESIS row cites it**, so the checker caught
its own new case the day it was written. **85/85 green.**

| id | question | state |
|---|---|---|
| **SWEEP.12** | Read the `wing_r_best` quantiles. Median **above 0.15** → r234 cleared it and the sweep should fire Monday. Median near **0.02** → r234 barely touched it and SWEEP.2's anchor distance is the real blocker. | 🔲 OPEN |

**v1.58 — 2026-09-04 — r240 — 🔴 r226 WAS CUT AND NEVER LANDED, AND THE CHANGE
IT DESCRIBED IS THE ONE BLOCKING MOM.1. PLUS: THE BACKLOG COULD NO LONGER
ANSWER "WHAT IS OPEN".**

## THE r226 FORENSICS

🔑 **No commit for r226 exists on any branch** — `git log --all --grep=r226` is
empty and the sequence runs r225 → r227. Its BACKLOG entry (v1.44) reached git
inside the **r227** commit, because `docs/BACKLOG.md` ships in every archive: the
r226 archive was cut, its entry written, and then the operator's *"you didn't
brick my ORB trade with bad follow-up retest logic, did you?"* made r227 urgent.
r227 shipped on top and **carried r226's already-written paperwork with it.**
Operator, 2026-09-04, guessing correctly before the check: *"that might be an
occasion where you told me not to land."*
🔴 **AND THE CHANGE IS STILL MISSING AND STILL COSTLY.** `entry_engine` wrote
`orb_range_high/low` only `if signal.is_orb` — literally
`strategy_name == "ORBStrategy"`. The **runaway populates those fields**
(`runaway_continuation:581`) because it is a continuation of the same break, and
the name check discarded them on every runaway fill. Measured:
`calibrate_trend_strength` reported **"no ORB boundary on the row : 182"** — all
182 runaway trades unmeasurable, on the largest strategy in the book by count
and by net.
🔑 **IT BLOCKS MOM.1 STAGE 1**, which r225 filed as the stage every other stage
anchors on — *"strength calibrated… which if it cannot discriminate makes 2
through 9 moot."* Stage 1 calibrates against the break-to-50 path, and the
boundary is exactly what was thrown away.
⚠️ **AND IT EXPLAINS ORB.7 ON THE RUNAWAY.** `exit_engine`'s structure stop
needs a bound on the record and skips silently without one, so *"the −25% floor
fires before the structure stop"* is, for the runaway, *"the structure stop had
nothing to fire against."*
⚠️ **A NAME CHECK IS A LIST** (r35's allow-list rot). The next strategy that
computes an ORB boundary is covered by **having** one. Both bounds required —
one bound is not geometry.
⚠️ **r235's CONFIRMATION LATCH KEEPS `is_orb`, deliberately** — only the ORB
engine has a confirmation to spend, so that one IS an identity question. B3 pins
it, because removing `is_orb` wholesale would have broken the fix that stopped
one retest firing three orders.

## THE LEDGER AUDIT

🔴 **25 rows read `🔲 OPEN` and 7 of them were already done.** Entries are
prepended per revision, so closing an item leaves its earlier OPEN row in place:
`SWEEP.2` sat on **four** rows, and SWEEP.3, SWEEP.4, TCS.8, ORB.6 and ORB.7 all
carried a stale OPEN alongside a later CLOSED. **The true open list is 19.**
⚠️ **STRUCK IN PLACE, NOT DELETED.** The superseded rows now read
`⬛ superseded — see rNNN`. The entries are a per-revision record and rewriting
them rewrites history; a row whose state a later entry contradicts is not
history, it is a wrong answer.
⚠️ **AND I MADE THE SAME ERROR WHILE CATCHING IT** — `open_items` took the
*last* row per id, but the file is newest-first, so the first row is
authoritative. It reported SWEEP.2/3/4 as open when they had been closed at
r231/r234.
`tests/check_ledger_parity.py` v1.0, 5 checks, prints the computed open list on
every run. `tests/check_orb_bounds_capability.py` v1.0, 5 checks, born red 2.
**84/84 green.**

| id | question | state |
|---|---|---|
| **DOC.13** | **r110, r141 and r159 are cited in GENESIS prose by later revisions and have no row of their own.** Either three rows were lost or three citations point at revisions that never existed; the ledger cannot say which. Allowed by name in `check_ledger_parity` L3 (DOC.13) — a **fourth** such citation fails, because that would be a new loss rather than an old one. | 🔲 OPEN |
| **DOC.14** | Nine revision numbers are absent everywhere (r42, 49, 89, 97, 109, 111, 117, 123, 151) — allocated and abandoned. Reported by L4, not failed: §26 says numbering never resets, not that it is contiguous. | 📌 RECORDED |
| **MOM.1** | **Stage 1 is now unblocked.** `calibrate_trend_strength` can see the boundary on runaway rows from the next session that banks. Nothing is calibrated yet. | 🔲 OPEN |

**v1.57 — 2026-09-04 — r239 / dtp r267 — 🔴 THE FIT REPORT WAS READING TWO
WRONG POPULATIONS, AND NEITHER WAS A DATA PROBLEM.** Both surfaced only once
dtp r266 stopped the CDC collapse from hiding them.
🔴 **ONE STRATEGY, TWO ROWS.** `_note_evaluation` is the only writer of
`strategy_note` and it stamped the raw `_safe_strategy` label, while the plan
ledger and gate rows use the class name. Result over 08-31..09-04:
**`ORB` — 78 fired, ZERO declined. `ORBStrategy` — zero fired, 4,260 declined.**
Neither arm could ever be fittable, and the report said NOT READY for both, for
opposite reasons.
🔑 **`DISPATCH_ALIAS` HAS EXISTED SINCE r147** and was already applied by the
plan board (`plan.py:791`, `:833`) and by `gate_report` (`:118`). This was the
one writer that never consulted it. **The fix is a lookup, not a rename** — a
rename fixes tomorrow and leaves five sessions of history split. `SweepForLeg2
→ SweepCreditSpread` comes along with it (r160's ruling, already true of the
plan board and silently untrue of the notes).
🔴 **`manage` IS NOT AN ENTRY RUNG.** It is the management path declining to act
on an **open** position, and it held **70%** of the butterfly's refusals, **89%**
of the runaway's, and **100%** of `IronCondorStrategy`'s and `ORBStrategy`'s. The
verdict then read *"one rung dominates, so there is no surface to fit"* — a true
sentence about the wrong population. The butterfly's real entry story was
underneath it: `wing_search` 461, `entry_window` 296, `legs` 152.
⚠️ **SPLIT, NOT DROPPED.** A management decline is a real event; its count still
prints, on its own line, where it cannot share a denominator with an entry gate.
The readiness verdict now computes its dominance share over entry rungs only.
⚠️ **AND THE REPORT CANONICALISES ON READ** (`STRATEGY_ALIAS`), because r239 only
helps rows written from now on, and a report that cannot read its own history is
not a fix.
`tests/check_note_label.py` v1.0, 5 checks — N3 pins the general invariant that
no dispatch label may resolve both to itself and to something else, so the next
strategy with a mismatched label is caught rather than silently splitting its own
arms. `dtp tests/test_fit_rungs.py` v1.0, 8 checks. Both born red. **82/82 otv4,
no new dtp reds** (7 were already red at HEAD).

| id | question | state |
|---|---|---|
| **FIT.1** | `RunawayContinuation declined 37,412` prints next to a rung distribution summing to **1,650**. They come from different streams — declines from `strategy_note`, rungs from `gate_disposition` — and were never comparable, but printing them adjacently invites the misread. | 🔲 OPEN |
| **FIT.2** | `analysis/gate_report.py:58` keeps its **own copy** of `DISPATCH_ALIAS`. Two copies of one map is how the first rots; r239 did not merge them. | ⬛ superseded — see r246 |

**v1.56 — 2026-09-04 — r238 — 🔴 TCS REBUILT: THE CREDIT VERSION OF THE RUNAWAY,
ANCHORED TO THE 50.** Operator's spec, 2026-09-04, six parameters, all quoted in
the code beside what they replace.

| | |
|---|---|
| **Window** | 11:31 → 14:00 for entries. *"No new positions after 1400, but condor management is allowed until the flatten."* Same number as the old placeholder, **chosen** this time. |
| **Precondition** | no open debit, butterfly exempt — `has_blocking_position` (r197, already built) |
| **Trigger** | `fifty_accepted` — 1m close beyond `target_50pct`, **held** at the next tick |
| **Live condition** | `holds_fifty` — price still on the traded side of the 50 |
| **Short** | nearest OTM strike from **current price**, floor side |
| **Wing** | **widest** clearing 1:1 on the **expiry** basis |
| **Stop** | 15% of credit, floored by `2 × short-leg spread` |
| **Exits** | 15% stop first · nickel · 15:45 flatten |
| **Size** | `_size_vertical`, full grade budget (already built) |
| **Re-entry** | permitted; strictness is the limiter, no latch |

🔑 **THE TRIGGER IS REUSED, NOT REBUILT.** `fifty_accepted` is a dated, latched,
falsifiable event with a pending-then-hold test that discards a close which
reverses. TCS has never had one — its old conditions were a per-tick set, which
is why it churned. **TCS.8 is closed by reuse.**
🔴 **THE WING RULE IS INVERTED AND DOES NOT CALL `search_wing`.** That helper
maximises R, which drives the wing **narrow**; the spec wants the **widest**
clearing 1:1 — more credit and more absolute stop room. And 1:1 must be the
**expiry** basis: with the stop at 15% of credit, `credit/stop` is 1/0.15 = 6.67
for every wing, a **constant**, so "set the wing accordingly" would have nothing
to solve for. `TCS_R_FLOOR_EXPIRY` is deliberately separate from the sweep's
`R_FLOOR_STOP` (r234) — one constant with two bases is the rot §35 names.
🔑 **THE TWO RULES PULL THE SAME WAY.** A thin far-OTM sale fails 1:1 *and* its
stop cannot clear 2× the quote; a rich near-money sale clears both. Realized
shape: **$0.375 risked against $2.45 to the nickel — 6.5:1, breakeven near 13%.**
Operator: *"available, not expected."*
⚠️ **`adx`, `trend_vote`, `outside_range`, `pop`, `drift_bar` — all GONE.**
Inherited for a continuation trade this is not.
⚠️ **THE EXIT BRANCH HAD NO PREMIUM STOP AT ALL.** `is_trend_participation`
checked the breach and returned. The 15%-of-credit stop now runs first; the
breach survives as a backstop, expected inert. **`stop_survivable` at ENTRY is
load-bearing for this EXIT** — without it this is the r155-inverted stop.
🔴 **THREE FAULTS THE SUITE CAUGHT IN MY OWN WORK, each a first-tick crash:** a
ghost `chain.contracts` (OptionsChain has `.calls`/`.puts`) — `check_attr_fidelity`;
`safe_float` used six times and never imported — `check_singletons`, *"a global
declared but never bound raises only when the line RUNS"*; and an **invented**
`cv.fill_credit`, the §0.1 failure this repo is named after.
⚠️ **AND MY FIRST FIXTURE WAS REFUSED AT R 0.85 — THE CODE WAS RIGHT.** 1:1 on
the expiry basis genuinely needs credit ≥ 50% of width, so a near-ATM short is
not a nicety, it is the only way the floor is reachable. Recorded because it is
the single most surprising consequence of the spec.
`tests/check_tcs_fifty.py` v1.0, 7 checks, drives the operator's own 947/945
example. Five checkers re-derived; C1–C5/T7/T8 **retired** because they pinned
conditions the rewrite deleted. **81/81 green.**
⚠️ **STILL HELD BY `OT_TCS_ACTIVE=0`** on all 15 boxes. Landing this does not
unpark it; clearing that flag is a separate, deliberate act.

| id | question | state |
|---|---|---|
| **TCS.8** | Re-entry latch — closed by reuse of `fifty_accepted`; operator ruled no latch, strictness is the limiter. | ✅ **CLOSED r238** |
| **TCS.10** | C1–C5/T7/T8 covered the POP fault and the structural-vs-condition split. `check_tcs_fifty` does not. Owed. | 🔲 OPEN |
| **TCS.11** | Never run against a tick. First live session needs `fifty_accepted` counts, `holds_fifty` refusals, and how often 1:1 is reachable — the 0.85 fixture says it may be rare. | 🔲 OPEN |
| **TCS.9** | `cascade_harness`/`cascade_real` still hardcode their own `(14, 0)`. Now correct by accident. | ⬛ superseded — see r246 |

**v1.55 — 2026-09-04 — r237 — 🔴 TCS PARKED AT ITS FIRST GATE.** Operator, mid-session:
*"I don't know how TCS has cleared the bar to fire... set the impossible variable and
comment it in the changelog. We're doing a rewrite tomorrow anyways."*
🔑 **WHY IT CLEARED, so the rewrite does not re-derive it:** r234 moved R to the stop
basis and **TCS passed honestly** — UNH sold 398/402 for $0.84, `credit/width 21.0%`
against the 13.04% bar, `r_stop 1.77`. **My "TCS still fails" note was measured on SPX
and QQQ at 0.04–0.09 and I let it stand for the fleet.** UNH is a different chain and
sails through. The gate was right; the trade behind it should not have been taking the
offer.
🔴 **AND IT CHURNED:** 11:40, 11:42, 11:42 on identical strikes, closing −$2.00, −$2.00,
−$0.00. **TCS has no re-entry latch of any kind** — no `order_placed`, no confirmation
sequence — the exact shape r235 fixed for the ORB, which TCS never had. And
`exit=breach@397.07` is the **ORB low**, the same bound it anchors its short strike to,
so price sitting ON the boundary makes it enter and exit on alternating ticks.
🔑 **THE LEVER: `TCS_ENTRY_END_ET = (0, 0)`.** `(now.hour, now.minute) >= (0,0)` is true
at every tick, so TCS is DORMANT before a chain is read.
⚠️ **WHY THIS CONSTANT AND NOT A QUALITY BAR.** Raising `R_FLOOR_STOP` or `TCS_MIN_POP`
would also stop it and would **lie about why** — the plan board would read `wing_r_best
FAIL` forever and the next reader would spend a session working out why UNH never clears
R. A closed window is the truth: parked, not out-priced. And it is **TCS-only** —
`TCS_START_ET` is pinned equal to `CREDIT_ENTRY_START_ET` by `check_entry_windows`, so
touching that would have moved the **sweep**. P3/P4 pin both.
⚠️ **BELT AND BRACES:** `OT_TCS_ACTIVE=0` is in a systemd drop-in on all 15 boxes
(verified 11:47, 15/15). The env flag dies with the file; this survives in the repo.
⚠️ **THE DORMANT MESSAGE NAMES THE PARK** rather than reading "past 00:00 — dormant until
tomorrow", which describes the wrong thing: tomorrow never arrives.
⚠️ **`check_plan_prepares` C1–C5 RESTORE THE WINDOW for their duration** — they exercise
the internals tomorrow's rewrite starts from, and losing that coverage the day before a
rewrite is the wrong trade. Patches the module, restores after, and the production value
is pinned in `check_tcs_parked` so this file can never be what claims TCS is parked.
`tests/check_tcs_parked.py` v1.0, 6 checks, born red 3 at `88bac2c`. **80/80 green.**

| id | question | state |
|---|---|---|
| **TCS.8** | The rewrite must add a re-entry latch. r235's `confirmation_seq`/`order_placed_seq` is the pattern; TCS has no confirmation concept at all to hang it on. | ⬛ superseded — see r238 |
| **TCS.9** | `cascade_harness.py:49` and `cascade_real.py:56` hardcode their own `TCS_ENTRY_END_ET = (14, 0)`, so they now model a TCS that still trades. Not in the `check_*` glob, so nothing went red. Pre-existing drift, named not fixed. | ⬛ superseded — see r246 |

**v1.54 — 2026-09-04 — r236 — 📌 DOCS ONLY. THE TCS's ACTUAL INTENT, THE VOL
SENSORS NOBODY READS, AND THREE DISPOSITIONS.** No code. Recorded because all
of it existed only in one chat, and a weekend TCS rebuild that starts from a
spec is a different project from one that starts by re-deriving a conversation.

## TCS.7 — WHAT THE TREND CREDIT SPREAD IS ACTUALLY FOR

🔑 **OPERATOR, 2026-09-04, first statement of intent on the record:** *"The
intent of the TCS was to capture a big afternoon move... an afternoon
characterized by expanding IV in some macro catalyst... without buying rapidly
evaporating premium."* The credit structure is the point — it is the way to be
positioned for a catalyst **without paying theta on a 0DTE debit**, which is
also why the window opens at 11:31, the moment `DEBIT_DIRECTIONAL_CUTOFF_ET`
closes the debit door.

🔴 **THE CODE IMPLEMENTS A DIFFERENT TRADE, AND SAYS SO.** `trend_credit_spread`
sells the **ORB boundary strike, frozen at 09:35**, gated on `trend_vote` and
`adx >= 25` — trend continuation off the morning range. A 14:00 catalyst has no
relationship to the 09:30–09:35 range. Four inherited pieces, none of them
chosen for this trade:

| piece | is | should be |
|---|---|---|
| anchor | ORB boundary, fixed 09:35 | something the MOVE creates |
| window | 11:31 → **14:00** | spec'd for the event |
| trigger | `adx >= 25` | a pre-catalyst tape is COILED, not trending |
| side | direction of the vote | where premium actually is |

🔴 **`TCS_ENTRY_END_ET = (14, 0)` IS A PLACEHOLDER THAT IS ENFORCED.** config's
own comment calls it *"PROVISIONAL, INERT — inherited verbatim from the deleted
global cutoff... Operator specs TC.6's real v4 window before any activation"* —
and `trend_credit_spread:287` enforces it. That stopped being inert when TCS was
unparked. **The strategy shuts at 14:00, which is when an FOMC statement drops.**
Same class as r230's `getattr` default: a live gate nobody chose.

🔴 **AND IT IS HANDED THE FED CALENDAR AND NEVER OPENS IT.** `macro` appears in
`trend_credit_spread` **three times — all signatures or pass-throughs, never a
read.** Meanwhile `macro_data` pulls high-impact Fed events from a live
calendar, `orb_strategy:359` reads `macro.is_fed_day` for confluence, and the
butterfly disables itself on Fed days. The fleet knows when FOMC is; the one
strategy built for it is the one that does not look. Same shape as r205's
`atm_iv` — computed, passed, discarded.

🔴 **THE MEASURED VERDICT, FROM THE OPERATOR:** *"The ORB range is so far OTM
when we sell it, there's no juice to squeeze."* `plan_check` 2026-09-03 agrees
from both ends: `pop` **PASSED 596/596** at 0.87–1.00 while `wing_r_best`
**FAILED 596/596** at 0.0–0.09. Safe and worthless on the same rows. And the gap
between boundary and price **IS** the move — SPX ran 27–40 points past its ORB
low on an ordinary day — so **the credit shrinks as the opportunity grows**,
which is backwards for a trade whose purpose is the big day.
⚠️ **AND IT SELLS THE CHEAP SIDE.** On a violent drop TCS sells CALLS, where
skew steepens toward puts and premium collapses. Expanding IV does not rescue
it: a parallel lift raises the long leg too. **A credit spread needs steep SKEW,
not high IV.**

⚠️ **PARKED, NOT DISABLED.** Operator: *"live but rarely fires and it's not
hurting anything. I will disable it prior to live trading if we don't end up
remastering it."* `TREND_CREDIT_ACTIVE` defaults on; `OT_TCS_ACTIVE=0` parks it
per box with no deploy.
⚠️ **AND DISABLING IS NOT NEUTRAL:** TCS is the only **leg-one** trigger for a
trend-shaped condor (Rule 4 — a trend CS may never FOLLOW anything). Turning it
off removes that path on a book where no condor has yet formed.
⚠️ **CORRECTION ON THE RECORD:** I claimed a TCS fill competes with the sweep
for a slot. Wrong twice. Rule 4 names the operator's exact sequence — *"TREND CS
first → ONLY a SWEEP completes it"* — so a bearish TCS taking the call side is
what LETS a put-side sweep form the condor. And the residual I retreated to (an
open TCS call spread blocking a later HIGH sweep) cannot occur: **price must
travel through the short call to reach that high, and the 15% stop resolves the
position first.** TCS costs the sweep nothing.

## IV.2 — EVERY VOLATILITY-EXPANSION SENSOR IS READ BY NOTHING

🔴 Traced 2026-09-04. Each is computed and recorded; **none gates any decision.**

| measure | computed | read by a strategy |
|---|---|---|
| `variance_risk_premium` | ✓ | **nothing** |
| `expected_move_iv` | ✓ | **nothing** |
| `iv_slope` | ✓ `second_order.py` → `greeks_series` | **nothing** |
| `is_expanding` | ✓ `volatility_engine:172` | **logged only** (`:248`) |
| `atm_iv` | ✓ since r205 | butterfly sizing only |

🔴 **AND THE TWO IMPLIED MEASURES WERE NULL UNTIL 2026-08-31.** Both derive from
`atm_iv`, which r205 found computed into a local and never stored — *"31/31 rows
across 13 symbols carried a null."* So VRP and `expected_move_iv` have been
computed from `None` for the life of the project and have **three sessions** of
real history. Operator: *"we had nothing available to exploit it."* Literally
true — the sensor existed, was wired to nothing, and the IV half returned nulls.
⚠️ **SAMPLE ASYMMETRY FOR ANY FUTURE STUDY:** realized expansion
(`is_expanding`, ATR, `bb_width_pct`) has **full history** in `indicator_series`,
warehoused since r191. Implied has three days. A screen can answer the realized
question now and only find a mechanism on the implied one (§12).

## SWAN.1 — THE BLACK-SWAN WATCHER IS AN OBSERVER, NOT A STRATEGY

🔑 Operator: *"I would love to have a black swan type trade there, watching just
in case we ever caught such a move."* A rare event cannot be fitted after the
fact — you cannot build the trade and then wait for a sample. `shadow/` is the
existing home and §34 carves it out by name: *"Observers are the exception and
DO ship — `shadow/` collects in-session, which is the data a future scorer is
earned from."* `install.sh:49` already ships it; `primitives.py` already carries
`is_expanding`.
🔑 **AND IT SEPARATES TWO FACTS THAT LOOK IDENTICAL FROM OUTSIDE** — *never
fired* vs *never would have fired*. The same distinction r217 draws for the
condor. r208's butterfly is the precedent: it went its whole life without a
survivability check because nothing was watching it.
⚠️ **TWO OPEN QUESTIONS, BOTH UNANSWERED ON PURPOSE.** (1) What counts as the
event? `atm_iv` rising, VRP widening, realized `is_expanding`, range compression
breaking — they disagree, and an observer recording all of them is honest while
one picking a definition now is a guess wearing a sensor's clothing. (2)
Continuous or latched? Continuous is many rows for something rare; a latch needs
a threshold nobody has yet.
⚠️ **AND I WITHDREW AN ARGUMENT HERE.** I argued armed-and-instrumented was the
conservative default for a rare-event trade. That holds for a trade that would
CAPTURE the move. TCS would fire and collect pennies, so leaving it on is not
insurance — it only looks like insurance from the flag's point of view.

## ORB.6 / ORB.7 — CLOSED

⚠️ **ORB.6a — `_place_butterfly` needs no latch.** `is_orb` is
`strategy_name == "ORBStrategy"`; reaching that placer requires
`signal.is_butterfly`, a separate field the ORB never sets. Unreachable.
⚠️ **ORB.6b — the double-notify is real and now benign.** `resting_orders:571`
and `position_manager:719` can both fire for one setup. Post-r235 the latch and
seqs are untouched and the rest is idempotent; the only effect is
`attempt_number` incrementing twice, so *"attempt #4"* can mean two attempts.
Cosmetic — **filed, not fixed**, rather than touch the exit path with five
revisions already in flight.
🔑 **AND IT WAS A SECOND PATH TO THE r235 BUG.** Before r235 a double-notify
cleared `order_placed` twice, which on the standing-offer path (where the latch
WAS set) bought a free second entry off one confirmation. r235 closed it as a
side effect, not by design.
⚠️ **A WORRY I CHECKED AND DISPROVED, recorded so nobody re-checks it:** I
expected the ordinary close never to notify, which would have made r235's latch
a **one-trade-per-session** regression — r227's quiet failure reintroduced. It
does notify: `position_manager:719` sits in `_execute_exit` gated on the
strategy name, not on the offer. Paper included.
✅ **ORB.7 — CLOSED, WORKING AS INTENDED.** Operator: *"we don't need to wait for
a structure stop if the position has already turned on us."* The −25% floor and
the structure stop answer different questions — is the money gone, is the thesis
dead — and there is no reason to keep paying for an answer already in hand.
🔑 **THE FLOOR WAS NEVER THE EXPENSE.** META 2026-09-04 lost **$332 across four
entries**; the first was **−$49**. The floor was firing three times for one
setup, and r235 stops the multiplication.

**v1.53 — 2026-09-04 — r235 — 🔴 ONE RETEST FIRED THREE ORDERS, AND THE LATCH
THAT SHOULD HAVE STOPPED IT WAS NEVER SET.** Operator, from the tape: META
entered **09:39, 09:40 and 09:43** off a SINGLE 09:38 retest, with only one
further qualifying retest all session (09:54). *"It would need a qualifying
retest to enter again."*
🔴 **THE CALL SITE, NOT THE FLAG.** r207 installed
`_mark_orb_confirmation_spent()` inside `_place_standing_offer` — twice — and
its own note says the latch is *"a property of the CONFIRMATION, so it is
mode-independent."* True of the flag; **false of the call site.**
`_place_single_leg` is the DEFAULT placer and never called it, so
`order_placed` was **False for the life of every session**, the engine sat in
`OPEN_*` after the retest, and both fire gates passed on every tick.
⚠️ **C.40 A THIRD TIME.** r195's `_orb_offer_working()` read a table paper never
writes; r207 replaced it with a flag set on one of two placement paths. A guard
in the order plumbing cannot protect a path that does not run that plumbing.
⚠️ **AND IT EXPLAINS WHY r221 AND r227 BOTH MISSED IT.** Both reasoned at length
about whether `order_placed` survived a close or went quiet — about a flag that
had never been set on this path. r227's hazard (*"decline EVERY retest for the
rest of the session"*) could not occur, and its fix was inert.
🔑 **THE LATCH IS NOW PER-CONFIRMATION.** A bare boolean can only say "an order
happened", which is why the armed path had to clear it globally — and a global
clear is indistinguishable from never having been set. `confirmation_seq` bumps
at each qualifying retest, `order_placed_seq` records which one fired, and
`notify_position_closed` now clears **neither**. `confirmation_spent()` is
extracted to module level so the checker drives it and not a copy (C.23); `>=`
not `==` so an out-of-order restore fails **shut**.
⚠️ **RESTORE FAILS SHUT.** A pre-r235 snapshot carries `order_placed` and no
seqs, so a naive restore would let a spent confirmation fire on the first tick
after a restart. A legacy True with no seq reads as *confirmation 1, already
spent*. Both seqs persist.
⚠️ **CLOSE-INSIDE IS UNTOUCHED** — operator: *"a close inside the range during
the retest hunt kills the thesis and it starts back at square 1 waiting for a
break."* Still `_rearm(reentered=True)`. No expiry on a live confirmation, per
the same ruling; only geometry invalidates.
⚠️ **AND THE STOPS WERE THE OTHER HALF.** `exit_engine`'s own comment: the −25%
premium floor *"is independent and still fires first... the two are an AND, not
an OR"*, so the structure stop the operator expected (a 1m close beyond the
impulsive candle's origin) never got the chance. The three META losers exited at
−28.5%, −28.2% and −19.3% of premium. **Recorded, not fixed — the ordering of
those two stops is the operator's call and is filed as ORB.7.**
`tests/check_orb_one_order.py` v1.0, 14 checks, born red with a named failure.
`check_orb_rearm_zone` Z1d **re-derived** — it asserted the global clear, which
is the behaviour r235 removes. `check_orb_sequence` fixtures re-derived to the
seqs. **79/79 green.**

| id | question | state |
|---|---|---|
| **ORB.6** | Does the same missing latch affect `_place_butterfly`, and can `resting_orders` double-notify a close? Named at r235, deliberately not touched. | 🔲 OPEN |
| **ORB.7** | The −25% premium floor fires **before** the structure stop, so the ORB rarely reaches its own invalidation level. Operator's intended exit was the 1m close beyond the impulsive candle. Ordering is a what-gets-traded call. | 🔲 OPEN |

**v1.52 — 2026-09-03 — r234 — 🔴 R WAS JUDGED AGAINST A LOSS THE STOP EXISTS
TO PREVENT. SWEEP.2 and SWEEP.3 CLOSED.** Operator, 2026-09-03: *"are we
calculating R with the stop placement at 15% of credit received?"* No — against
**max loss at expiry**, while `exit_engine:1818` fires at 15% of that same
number. **6.67× apart.** On the measured median (credit $0.97 on $5.00 width,
08-25..09-03): R **0.241** as gated, **1.605** against the risk actually taken.
🔑 **THE THRESHOLD, EXACTLY: `R_stop ≥ 1 ⟺ credit/width ≥ 13.04%`**, against a
measured richness median of **19.4%** (min 10.8%, max 24.2%). Most of the book
already cleared 1:1 on the risk it was taking.
🔴 **AND A SECOND DENOMINATOR ERROR IN THE SAME PATH.** `sweep_credit_spread`
computed `credit * MAX_LOSS_PCT` — **15% of CREDIT** — and fed it to
`stop_survivable`, while the engine uses 15% of RISK. **0.1455 against 0.6045,
4.15×**, and the forensics' own *"risk-anchored room: median $0.605"* matches
the ENGINE. Survivability was judged against a stop four times tighter than the
one that exists. The credit-anchored form is the rule **r155 deleted** —
exit_engine's own fallback warns *"the trade will stop on noise."* One
definition now: `criteria.stop_distance`, reading the engine's own constant.
⚠️ **THE BASIS SPLITS BY THE OPERATOR'S OWN EXIT RULINGS, not by taste.** A
credit vertical's stop **is** the designed exit (*"the only 2 ways I want out is
a 15% loss or a session hard close"*), so the risk accepted is the stop. The
**GEX pin butterfly** is a debit paid up front and **held to the close** for the
pin — its 25% floor is a disaster backstop, not the plan — so
`R = (width−debit)/debit` already had the right denominator and keeps `R_FLOOR`.
The **managed roll** never opted in: `condor_roll` judges on
`banked_credit + roll_credit − close_cost`, a risk-free-roll test, which is the
right question for a position you are already in. Both constants carry their
basis in the name so they cannot collapse into one (§35).
🔑 **SWEEP.3 CLOSED — r208's C.43 carried to the verticals.** R rises as the wing
narrows while the **stop narrows with it**, so a selector that only maximises R
*optimises into* the least survivable structure. `search_wing` is now bracketed
by `R_FLOOR_STOP` on the wide side and `stop_survivable` on the narrow side, the
same shape r208 built for the butterfly.
🔴 **AND THE r219 ARITY BUG IS RETIRED BY CONSTRUCTION.** r219 added a fifth
return value and **missed two guard returns still returning four**; both callers
unpacked five, so a short leg with `bid <= 0` raised `ValueError` into
`_safe_strategy`, read as a clean DECLINE, and never recorded the strategy as
asked. `WingResult` is a NamedTuple with defaults read by name — adding a field
can never again change what a return path unpacks to. `why_key` names the
refusing rung as a **field**, not prose a caller would sniff (§20 one layer up),
so a bracket refusal reports `stop_vs_spread` instead of blaming the chain.
⚠️ **NARRATION NAMES BOTH BASES** — *"R 7.22 on the stop (min 1.00; 1.08 at
expiry)"* — r219's lesson one layer over: printing one and labelling it the other
is how it stays invisible.
⚠️ **THREE CHECKERS RE-DERIVED, EACH CERTIFYING THE DEFECT IT PINNED.**
`check_plan_prepares` S2 asserted `stop_premium == credit * 1.15`, the
r155-inverted stop — the **third** time a fixture in that file has certified the
thing it was meant to catch. `check_fill_basis` F0 asserted "five values", the
exact invariant r219 broke, and could not see it because it only drove the
success path. `check_wing_search` W2 matched source text a correct refactor
removed (§21).
⚠️ **AND r219's OWN FIXTURE IS NOW REFUSED** — its 0.60-wide legs give 0.69 of
stop room against a 0.60 spread, needing 1.20 to clear 2×. That is r219's own
verdict (*"the position was born at its stop"*) enforced at selection instead of
discovered at the exit. F1c pins it.
`tests/check_r_basis.py` v1.0, 15 checks, born red with a **named** failure.
78/78 checkers green.

| id | question | state |
|---|---|---|
| **SWEEP.2** | R basis — closed. Whether fills actually arrive is the live test. | ✅ **CLOSED r234** |
| **SWEEP.3** | Narrow-side bracket — closed, r208's pattern ported. | ✅ **CLOSED r234** |
| **SWEEP.11** | **Watch the first session.** 13.04% is the bar and 19.4% was the median — if fills cluster below 13% the median was flattering us. `r_expiry` rides every row beside `r_stop`, so the basis change is auditable from the tape. | 🔲 OPEN |
| **ROLL.1** | The managed roll has **never run live** (no condor has formed). Its `new_maxloss = (new_width − roll_credit) × qty × 100` is untested arithmetic for a deliberately INVERTED structure. Operator, 2026-09-03: the condor is a **permissive plan, not a required one** — two contested levels must be traversed in one session with one leg already open — so non-formation is rarity, not defect. | 🔲 OPEN |

**v1.51 — 2026-09-03 — r233 — 🔴 THE STRIKE MUST CLEAR THE TESTED RANGE, AND
THE NEAREST LIVE LEVEL WINS.** Operator, 2026-09-03: *"the strike cannot sit at
any level that is part of the testing range... I don't want to get stopped out
by another retest. It has to be just beyond that, if only a little bit"*, and
*"the level in question needs to be the closest to the current price."*
🔴 **THE HOLE, AND r107's DOCSTRING STATES BOTH SIDES OF IT** three paragraphs
apart — *"it sits FURTHER from spot than anything price reached"* (the intent)
and *"nearest is 7635 — the strike price traded THROUGH"* (the deep-pierce case,
documented without noticing the contradiction). **Proven at `bd6f25e` on the
header's own example:** pool 7639.01, wick 7633 → **7635, which sits between
them.** Price traded clean through it on the way down, so a second test of the
same size takes the position out. The candidate bound was the POOL when it
needed to be the WICK EXTREME — r107's intent was right, its bound was not.
⚠️ And it is **the nearest of what is beyond** — `min(cand)`/`max(cand)`, never
`min(abs(k - sweep_price))`, which is exactly what let an inside strike win.
⚠️ The pool bound is **kept and now implied**; P4 pins it never binds, so it is
known inert rather than assumed so.
🔑 **SELECTION MOVES FROM RECENCY TO DISTANCE.** Both branches took the freshest
raid — this one `min(bars_ago)`, the fallback the map's `recent_sweep` — so a
level three points out beat one 0.6 points out if it landed a bar sooner.
Freshness survives as the **tie-break**, the one question distance cannot
answer. `level_rank` **extracted to module level so the checker drives it and
not a copy** (C.23). The `recent_sweep` fallback survives only when no candidate
carries a usable pool price, and says so at INFO — leaving it in place would
have put leg two on distance and the primary entry on recency, one rule with
two answers.
⚠️ **RETIRES SWEEP.6 AT THIS SITE RATHER THAN FIXING IT** — distance carries no
units problem. SWEEP.6 stays OPEN for the other selector and `liquidity_mapper`.
⚠️ **SCOPE, MEASURED:** `pierce_depth` ran a **0.0032 median against a 0.5685
max**, so shallow pierces dominate and only the deep tail re-prices. `pierce_pts`,
`level_dist_pts` and `level_dist_pct` ride the plan **record-only** so how often
it fires is a query rather than an argument (WA §31, same shape as r198's
`wing_stretch`).
🔴 **AND IT DOES NOT FIX THE MEASURED LOSSES.** Forensics 08-25..09-03: price
never reached the strike on **22 of 22**, and the stops were mark-driven (r219).
A real hole, correctly closed, on a failure mode this sample never showed.
⚠️ **"EVER HELD" IS DEPRIORITISED** by operator ruling — a level is a point, not
a range, so the prior-hold requirement matters less. `level_ledger.touch_count`
stays recorded and ungated (SWEEP.8).
`tests/check_strike_beyond.py` v1.0, 12 checks, **born red 3 + a named
capability failure** at `bd6f25e`. `check_sweep_spread` v1.1 **re-derived**:
its S7c asserted PARITY with the pre-r107 rule, which now certifies the defect
— the same shape as the old `check_plan_prepares` S2 certifying the r219 fill
basis. 77/77 checkers green.

| id | question | state |
|---|---|---|
| **SWEEP.10** | Does the deep-pierce case fire often enough to matter, and does clearing the wick cost more credit than it saves in stop-outs? Answerable from `pierce_pts` + `level_dist_pts` once a session banks. | 🔲 OPEN |
| **SWEEP.2** | Still the blocker. Moving the strike further out on deep pierces pushes credit **down**, against `R_FLOOR` 1.00. Consistent with §2 doctrine (*"a deep pierce means a WEAK level"*) but it does not help R. | ⬛ superseded — see r234 |
| **SWEEP.6** | Cross-timeframe `bars_ago` — retired at the primary selector, still live in `_sweep_at_level` and `liquidity_mapper:~1057`. | 🔲 OPEN |

**v1.50 — 2026-09-03 — r232 / dtp r265 — SWEEP.8 OPENED AND INSTRUMENTED: DOES
A LEVEL'S DEFENDED COUNT PREDICT WHETHER IT HOLDS?** Operator, 2026-09-03:
*"I'd rather have a handful of rare firing high quality reversals than a stack
of lottery tickets"*, and **signal quality is the primary outcome, P&L second.**
🔑 **THE COUNT THE STRATEGY USES IS NOT REAL AND THE REAL ONE IS UNUSED.**
`LiquidityPool.touch_count` is `len(cluster)` from a map `analyze()` rebuilds
every tick, and `_add_named_pool` hardcodes it to **1** — 44,450 of 44,890 ticks
read exactly 1, which is why `level_strength` came back **94% ties on two
values**. Consumers: `sweep_reversal`'s `level_strength` collapses to 0.7/0.3, a
boolean wearing a float; and `trade_readiness` LEVEL QUALITY computes
`ramp(1, TR_SWEEP_TOUCH_MIN=1.0, TR_SWEEP_TOUCH_FULL=4.0)` = **exactly 0.0**,
which *multiplies* the proximity term, so that whole term has been zero on every
tick (LOG-ONLY, so no trade was affected).
⚠️ **AND r231 MADE IT STRUCTURAL.** The only pools that ever carried
`touch_count >= 2` were the unnamed equal-high/low clusters r231 deleted at the
operator's ruling. Post-r231 it is 1 for named pools and 0 for tines,
universally. Nothing that worked stopped working; the last path to a non-zero
value is gone. Recorded because it was not flagged when r231 shipped.
🔑 **THE REAL COUNT EXISTS AND IS THE OPERATOR'S OWN MODEL.**
`derived/levels.py` → `LevelEngine.walk(price, limit=3)` returns levels ordered
by DISTANCE from spot, `WHERE retired_ts IS NULL`, carrying `touches`,
`provenance` and `is_live_session` — *"the session is a label on the answer, not
the query"*. Touch = HOLD per his 2026-08-22 ruling, a run that TERMINATES at the
break. Its own docstring states the criterion: *"the nearest level may be a
one-touch artifact while the one 0.4% beyond has held five times — that is the
whole distinction between trading into something and trading into noise."*
🔴 **AND ITS ONLY CONSUMERS ARE RECORDERS.** `ctx["levels"]` is read by
`plan_ledger`, `notes`, `snapshot` and `liquidity_ledger`. **No strategy reads it
for a decision.** Two level systems: the one with memory records, the one without
memory trades.
⚠️ **THE COUNTERWEIGHT, STATED SO IT IS NOT RE-LITIGATED.** The sweep's own
header records that grading by level TYPE is **measured null** — *"POOL TYPE DID
NOTHING: PDH 32%, PDL 28%, both at base"* — so wiring `level_grade.py` would not
help. Grading by DEFENDED COUNT has never been tested, because the number was
never available to the strategy. That is the one quality signal still standing.
**INSTRUMENTED, NOT GATED (WA §31).** dtp r265 extends
`tests/screen_sweep_forensics.py` to v1.6 with **panel 8** rather than building a
second lineage (§7/§25) — it already owns the join, the outcome, and the
corrections (`entry_time` is UTC; `plan_check` keys on `direction`). It costs **no
extra S3 objects**: panel 6 already loads `fire_snapshot`, whose
`payload["levels"]` is the walk AT THE FILL.
🔴 **THE OUTCOME IS PANEL 1'S, DELIBERATELY** — `pen` (did price trade beyond the
short anchor) and `acc` (longest run of closes beyond it). A stop cannot
manufacture either, and both are unaffected by the r219 fill-basis artefact. P&L
prints beside them and is **not** the split key; grading levels on this book's
P&L would fit the artefact.
🔴 **A DEGENERATE DISTRIBUTION IS REPORTED AS DEGENERATE.** If every joined level
reads one touch the panel says the sample **CANNOT test** the hypothesis, rather
than printing a flat table that would read as *"defended count does not matter"*.
And a pool outside the 3-rung walk is **UNMEASURED, not one-touch** — coverage is
printed with its three causes kept distinct. Both are the plausible-silence class.
`tests/test_level_quality.py` v1.0, 8 checks, born red at HEAD with a **named**
failure via a capability probe. `_level_join` / `_level_report` are EXTRACTED so
the selftest drives the real code (C.23).

| id | question | state |
|---|---|---|
| **SWEEP.8** | Does defended count separate held levels from broken ones? Instrumented at dtp r265; **no dial moves on it** until read against a real range. n≈41 finds a mechanism, not a conclusion (§12). | ◐ **INSTRUMENTED** |
| **SWEEP.9** | If it separates: wire `LevelEngine.walk()` into the sweep's candidate selection **LOG-ONLY** first, then gate. Alters what gets traded — operator's call. | 🔲 OPEN |
| **LVL.1** | `level_strength` and `trade_readiness` LEVEL QUALITY both read the dead `LiquidityPool.touch_count`. Repoint at `level_ledger` or delete — two dead consumers is worse than one. | 🔲 OPEN |

**v1.49 — 2026-09-03 — r231 — 🔴 THE LEVEL MODEL, CORRECTED TO THE OPERATOR'S
INTENT. SWEEP.4 CLOSED; SWEEP.6/7 OPENED.** Five rulings, 2026-09-03. **Two were
already built and are reported rather than rebuilt:** named precedence (v3.1),
and *"nothing inside the ORB range is actionable"* — `session_map.classify()`
has refused those since it was written, in almost his words, and SPX failed it
88 times today.
🔴 **THE `or 999`.** `age = int(getattr(sweep, "bars_ago", 999) or 999)`.
`bars_ago` is an int field defaulting to 0 and SWP.10 counts it from the
**reclaim** bar, so a sweep that reclaimed on the current bar is `0` — and
**`0 or 999` is 999.** Twenty-six lines above, the selection loop takes
`min(bars_ago)`: it hunts the freshest sweep on the board, and this line turned
exactly that winner into the stale sentinel and refused it. One function
contradicting itself, and invisibly — 999 reads as missing data, not as the best
setup available. Absent stays 999; **zero stays zero.**
🔴 **GEOMETRY NOW ASKS ROLE-vs-PRICE.** Operator: *"an upper tine below the
current price cannot be resistance, and a lower tine above price can never be
support — invalidated by geometry."* The range tests did **not** cover this: a
ceiling between `orb_high` and spot passed every one of them while price had
already traded through it. `spot` is a **required keyword** — an optional one is
r230's getattr default wearing a signature. Missing spot → None (unmeasured),
never a pass. Threaded through `PlanTick.level`, `check_geometry` and
`build_session_map`; no production caller outside `session_map.py`.
🔴 **EQUAL HIGHS/LOWS ARE NOT IDENTIFIED AT ALL** — *"not reliable enough."*
`_find_pools` **deleted**, not left uncalled (r190). Verified before removal
(§23): every external reader of `lmap.pools` already filtered them —
`orb_strategy:499`, `main.py:1267`, `shadow/primitives.py:167`. **One external
reader in the tree and it already ignored them.** And they could cost a trade:
an unnamed sweep can WIN the freshest-sweep selection (that loop does not filter
on name) then FAIL the `named` condition on the next line — taking the slot and
declining while a valid named sweep sat unselected. v3.1's named-precedence
filter comes out with them: every remaining producer names its pool, so the
`else` branch was unreachable.
🔴 **`_flag_nearby_pools` WAS LAST-MATCH-WINS.** Every pool inside the buffer
overwrote the field, so it held whichever came **last in list order** — ordered
by producer, not distance. **Measured at HEAD on a farthest-first fixture: 115.00
and 85.00 where the nearest were 112.00 and 88.00.** Distance is now the only
key; the timeframe that produced a level is never consulted, matching
`level_ledger`, whose id is `symbol:provenance:price` with no timeframe in it.
⚠️ **CONSEQUENCE UP FRONT:** a box whose only nearby structure was an unnamed
cluster now produces **no sweep candidate at all** rather than a bad one. Fewer
plans, and the DECISIONS panel will say so.
⚠️ **LANDS AFTER r230, NOT INSTEAD OF IT.** `sweep_credit_spread.py` v5.0
carries r230's changes as well, so landing this first would put r230's code in
the tree with no r230 GENESIS row.
`tests/check_pool_geometry.py` v1.0, 16 checks, **born red 13 of 16** at
`d680949` with **named** failures — a capability probe degrades a missing `spot`
kwarg to a named FAIL rather than one TypeError killing every G-check (r206/r212).
`check_plan_wiring` v1.4 **re-derived**, not patched, with W6g pinning the new
rule where the range tests cannot reach it. **Two faults caught in my own
checker, both C.23:** P1 first read the `.append()` call's keywords instead of
the `LiquidityPool(...)` being appended, so every site looked unnamed; and G7
went red against *correct* code because the degrade-wrapper swallowed the very
TypeError G7 asserts. 76/76 checkers green before and after.

| id | question | state |
|---|---|---|
| **SWEEP.4** | `0 or 999` scored the freshest sweep as maximally stale. | ✅ **CLOSED r231** |
| **SWEEP.6** | `bars_ago` is compared **across timeframes**: `min(bars_ago)` at two selection sites, and `liquidity_mapper:~1057` compares a **1m** tine touch against a possibly-**15m** sweep — a 15x unit error that can overwrite the correctly-computed `recent_sweep` without updating `sweep_age_bars`. The mapper already computes the 5m-equivalent and says why: *"so the downstream thresholds stay consistent across timeframes."* Fix shape: an `age_5m` property on `SweepEvent` so no consumer can get it wrong. **Alters selection — unruled.** | 🔲 OPEN |
| **SWEEP.7** | With geometry enforcing role-vs-spot, `side_of_pool` now tests the same fact a second time as a soft condition. Two rules for one thing is the rot §35 names. **Remove or keep — unruled.** | 🔲 OPEN |
| **SWEEP.2** | Unchanged and still the blocker: `wing_r_best` 761/761 at 0.0–0.06 against `R_FLOOR` 1.00. | ⬛ superseded — see r234 |
| **SWEEP.3** | `search_wing` is a bare argmax on R with no narrow-side bound; `stop_vs_spread` checked after. r208's C.43, never carried to the verticals. | ⬛ superseded — see r234 |
| **C.45** | THE GENERAL LESSON. **`x or DEFAULT` is not a null check.** Zero, empty string and empty list are all falsy, so the idiom silently rewrites the most extreme *valid* reading into the sentinel for "absent" — and the sentinel is exactly the value a staleness gate refuses. Sibling of C.44: both are fallbacks standing in for a value nobody chose. Use an explicit `is None`. | 📌 RECORDED |

**v1.48 — 2026-09-03 — r230 — 🔴 SWP.5 WAS RULED ON 2026-08-11 AND NEVER
REACHED THE CODE. SWEEP.1 CLOSED.** `sweep_credit_spread` read
`SWEEP_CS_MAX_AGE_BARS`, **a name defined nowhere in the tree**, so
`getattr(config, ..., 6)` made the ceiling its own hardcoded default — a
quarter of the old `SWEEP_MAX_AGE_BARS` (8) and an **eighth** of SWP.5's ruled
`SWEEP_STALE_HARD_BARS` (48). Three age constants exist in config; **the
strategy read none of them.** SWP.5's measurement, unread for three weeks: over
90 symbol-days, **32.9% of the stale sweeps the clock refused still had a LIVE
thesis** — ~9.5 valid setups discarded per symbol-day.
🔑 MEASURED 2026-09-03 from `plan_check`, not reasoned: `age` FAILED **761/761**
on QQQ (33–48 bars) and **934/934** on SPX. Every QQQ evaluation clears at 48.
⚠️ **THE OPERATIVE CEILING WAS 18, NOT 6.** The fleet is running RELAXED by
operator decision to observe tick-by-tick progression, so `widen(6, 3.0)` gave
18 — and 33–48 refused anyway. **Net effect on a relaxed fleet is 18 → 48, a
LOOSENING of 2.7x**, even though relaxed no longer reaches this gate. Keeping
×3 on 48 would give 144 bars against a 78-bar RTH session: unreachable, and an
unreachable ceiling is not a backstop.
⚠️ R IS NOT CONTAMINATED BY RELAXED, verified in source: `search_wing` reads
`R_FLOOR` directly and never through `r_hurdle()`, which returns None under
relaxed — *"relaxed widens EVIDENCE; it does not waive economics."* So the
0.0–0.06 in SWEEP.2 is the real number, not a relaxed artefact.
⚠️ OPERATOR RULING 2026-09-03: eliminate `relaxed` from the age question. The
widen call is **removed, not pinned to factor 1.0** — `check_gates`'
pinned-value idiom (r196) is implemented for `window()` ONLY and would have
gone red on a pinned `widen()`. Removing the call and declaring the gate
FOUNDATIONAL is **stronger**: the checker now refuses any future relax call on
it. Verified by re-adding one — `check_gates` exits 1 and names it.
⚠️ THE LIVENESS TEST IS `invalidated`, already wired and already correct (934/934
on SPX today). Age becomes the backstop SWP.5 intended, not the primary filter.
⚠️ **THIS UNBLOCKS ONE RUNG OF TWO AND DOES NOT MAKE THE SWEEP TRADE.** QQQ still
fails `wing_r_best` 761/761 at 0.0–0.06 — SWEEP.2.
`tests/check_sweep_liveness.py` v1.0, 8 checks, **born red 5 of 8 at `d680949`**
with the resolved value reading 6. L2b/L4 parse the AST and L3 reads the
resolved value, never the source text — the changelog above names both removed
tokens, and a string canary would trip on the prose §5 requires (§20).
75/75 checkers green before and after.

## OPEN — SWEEP

| id | question | state |
|---|---|---|
| **SWEEP.2** | `wing_r_best` FAILS 761/761 on QQQ at 0.0–0.06 against `R_FLOOR` 1.00. R ≥ 1.00 needs credit ≥ 50% of width; the short anchor sat 11 points OTM (705 vs 716 spot). **Liveness and richness pull opposite ways** — a pool still live and old is one price walked away from. Operator's intent: *"sell high volume, rich in premium, at a level we believe is just out of reach."* Requires separating the level's two jobs — confirmation/defence vs strike location. **Alters what gets traded: operator decides.** | ⬛ superseded — see r234 |
| **SWEEP.3** | `search_wing` is a bare argmax on R with **no narrow-side bound**; `stop_vs_spread` is checked separately afterward. That is r208's C.43 — the selector optimises into the least survivable structure and a later gate refuses it. Measured 2026-09-03 on SPX: 5 rows cleared R at 1.00, then `stop_vs_spread` failed 2 of those 5. r208 fixed this shape for the butterfly and it was never carried to the verticals. | ⬛ superseded — see r234 |
| **SWEEP.4** | `age = int(getattr(sweep, "bars_ago", 999) or 999)` — **999 is an ABSENT sentinel scored as maximally stale.** SPX's range topped out at exactly 999 today, so unmeasured is being counted as too old. Unreadable is not empty (C.26). | ⬛ superseded — see r231 |
| **SWEEP.5** | `SWEEP_MAX_AGE_BARS = 8` (config:1032) has **zero readers tree-wide**, as does `SWEEP_LIVENESS_GATE`. r190's precedent: an orphaned constant is what the next person rewires. Delete or keep — **not folded into r230, operator has not ruled.** | 🔲 OPEN |
| **C.44** | THE GENERAL LESSON. A `getattr(config, NAME, default)` is a policy the config cannot see and the checker cannot import — C.19 in a new costume, where a purge list hardcoded inside a function passed green while deleting unwarehoused data. **A constant read by fallback is a constant nobody chose.** Any ruling that lands a value in `config.py` without a reader is a ruling that did not ship. | 📌 RECORDED |
| **LEDGER** | **r226 has a BACKLOG entry (v1.44) but NO GENESIS row and NO commit.** Either it never landed or §35 was skipped. Unresolved. | 🔲 OPEN |

**v1.47 — 2026-09-03 — r229 — TWO NEW COMPONENT FAMILIES; MOM.1 STAGE 1's
FIRST RUN WAS NEGATIVE AND THE DIAGNOSIS IS THE OUTCOME.** Best AUC 0.63 under
a 0.65 floor, on a 74% base rate — predicting a near-universal event. Acceptance
was strongest at every window and the MEAN is blind to direction, so
`acc_slope` / `acc_delta` / `acc_run` are recorded; the same measure read
backward is stage 5's exhaustion signal. `fvg_respect` measures WHY a pullback
ended — mechanical fill and continuation vs distribution — detected from the
window's own bars to keep `measure()` pure, and BACKWARD-LOOKING because the
post-entry version would calibrate beautifully and be unusable as a gate.
**Nothing new is weighted**: the calibration decides.

**v1.46 — 2026-09-03 — r228 — r221 ARMED UNCONDITIONALLY.** It never consulted
where price was — three branches, none of them the zone test the operator's rule
requires. `last_close_inside` is recorded per tick from the last CLOSED bar; a
close back inside is a RE-ENTRY and ends the thesis. Without it, ARMED would
have overwritten a `close_inside` invalidation already applied. **And
`fifty_accepted` was only read at trade close**, so an already-ARMED engine
stayed armed through acceptance and would fire on a boundary the move had left;
it stands down at acceptance now, from ARMED only — a live position belongs to
the exit engine. Verified on both sides.

**v1.45 — 2026-09-03 — r227 — r221 WOULD HAVE MADE THE ORB GO QUIET.**
`order_placed` is the one-confirmation-one-order latch, cleared by `_rearm()`
building a fresh ORBData — and r221 deliberately stopped calling `_rearm()` on
the armed path to keep the impulsive candle. The flag survived, and
`orb_strategy` refuses on it ("this confirmation is SPENT"), so the engine would
sit ARMED and decline every retest for the session. **Quiet, not wrong** — an
armed engine that never fires looks like a market with no setups.
🔑 Rule recorded: not rebuilding ORBData means every ONE-CONFIRMATION field must
be cleared BY NAME. Caught by the operator asking before the bake.

**v1.44 — 2026-09-03 — r226 — 🔴 A NAME CHECK THREW AWAY THE RUNAWAY'S ORB
BOUNDS, AND IT BLOCKED MOM.1 STAGE 1.** `entry_engine` wrote
`orb_range_high/low` only `if signal.is_orb`, which is literally
`strategy_name == "ORBStrategy"`. The runaway populates those fields and the
name check discarded them on every fill. Measured: `calibrate_trend_strength`
reported **"no ORB boundary on the row : 182"** — all 182 runaway trades
unmeasurable. It is also why r223's guard still could not key: the boundary
half was empty regardless. **r223's header claim is corrected** — `direction`
IS written (`runaway_continuation:574`), the guard failed on the boundary alone.
Now a capability check, not an identity check.
⚠️ `check_orb_rearm_zone` was WALL-CLOCK DEPENDENT and would have gone red
every afternoon; the clock is frozen in the engine's namespace.

**v1.43 — 2026-09-03 — r225 — MOM.1 FILED: THE MOMENTUM PARTICIPATION BUILD.**
Nine stages in strict dependency order, from the QQQ 2026-09-03 finding that
four entries and four exits captured one move that wanted one position.
Strength sets entry, strike and initial stop; a SEPARATE exhaustion meter
contracts the stop while open. Strength selects the delta, gamma follows, theta
is what exhaustion pays for. Built inside the runaway for now — carryover
deferred deliberately.

**v1.42 — 2026-09-03 — r224 — A TREND STRENGTH METER, AS A RECORDER.**
`analysis/trend_strength.py`: four path components — efficiency, acceptance,
shallowness, pace — chosen because every point-in-time vector failed the screen
(adx AUC 0.47 over 152 runaway trades, strongest of sixteen 0.07 from chance,
pure-noise floor 0.19). **It gates nothing**: the weights are a declared prior
and `calibrate_trend_strength` (dtp r257) scores each component against the
5%-green outcome over the existing sample before any threshold is set. Refuses
rather than guessing — a degenerate window returns `score=None` with a reason,
because a 0.0 on missing data reads as "flaccid" and vetoes good trades.
⚠️ `MIN_BARS = 8` while `character.py` holds that an efficiency ratio is noise
below 20 — pragmatic for the runaway's break-to-50% window, and the calibration
is what will show whether 8-bar readings are stable.

**v1.41 — 2026-09-03 — r223 — THE ONE-RUNAWAY-PER-BREAK GUARD HAS NEVER
FIRED.** `trades.direction` is a declared column nothing writes, so the
losing-exit hook keyed `("", orb_low)` while `prepare()` checks
`("long", orb_high)` — never a match, since r174. Direction is derived from
`option_side` now, and an unkeyable exit is logged instead of swallowed by
`except Exception: pass`. QQQ 2026-09-03: five runaway entries in 29 minutes,
net −$530. **RUN.1 opened** for the part that is a decision rather than a
defect: whether a WINNING exit should also finish the break, and whether the
50%-held condition should be an event rather than a standing state.

**v1.40 — 2026-09-03 — r221 — THE BAND BETWEEN THE ORB BOUNDARY AND THE 50%
HAD NO OWNER.** `notify_position_closed` always called `_rearm()`, wiping the
impulsive candle and parking the engine in AWAITING_RANGE_REENTRY where a
retest from outside armed nothing; the runaway needs a held close beyond the
50%. NVDA 2026-09-03: 227.43 -> 228.77 owned by nobody. A resolved trade with
price still outside now stays ARMED with the original break candle and fires on
each qualifying retest. The 50% handoff uses the runaway's own close-and-hold
test, so there is no dead window between them.

**v1.39 — 2026-09-02 — r220 — EVERY FILL PATH AUDITED: MARK ON PAPER, LADDER
ON LIVE EXCEPT ORB.** Two gaps found by walking all six strategies.
**TrendCreditSpread** still booked `short.bid − long.ask` — r219 fixed the
prepare layer and `_build_signal` recomputed it at the signal layer, so the fix
looked complete from either end. **Credit verticals posted a static limit** and
never walked it; every other live entry prices through `ladder_registry`, and
only ORB's standing offer is exempt by design. The spread walk runs from the
best credit down to mark (operator: *"from the top. Best price that will
fill."*), built from the four leg quotes — whose midpoint is exactly what paper
books, so live and paper share a floor. `refuse` on a non-fill, `clear` only on
a complete fill. check_fill_basis F5/F6/F7 keep the audit as checks.

**v1.38 — 2026-09-02 — r219 — 🔴 THE ENTRY AND THE MARK WERE ON DIFFERENT
SIDES OF THE QUOTE.** Credit verticals were booked at `short.BID − long.ASK`
and marked at `short.MARK − long.MARK` — a gap of both half-spreads, charged as
a loss at the instant of fill, on a lone stop with 60.5 cents of room. Measured
$0.37 judged vs $0.97 booked on the fleet's shape. Sweep forensics 08-25..09-02:
38 of 41 stopped while price NEVER reached the short strike on 22 measurable
trades. Operator ruling: paper fills at mark. R stays judged on bid/ask.
**RPT.A's sweep result is void** — 3 GREEN of 41 measured a bookkeeping
artefact, not the strategy. **And check_plan_prepares S2 asserted the old basis
throughout**, so the suite certified the mismatch.

**v1.37 — 2026-09-02 — r218 — MEM.1 AND OI.1 OPENED FROM A LIVE OOM.** MU was
OOM-killed at 14:20 ET. MEM.1: the primary expiry publishes every listed strike
while the aux tenors are banded at ~9 — MU carries 356 contracts spanning
±45% of spot and its `candle_feed` is 4.2x CVX's at the same uptime. Measured,
and two theories of mine were refuted along the way: it is NOT a runaway leak
(12 samples, 0.53 MB/min drift) and NOT a spike (peak-to-trough 1.45 MB).
Operator ruled to upgrade MU. OI.1: `_await` calls `asyncio.run`, creating a
new event loop per call, against a long-lived SDK session holding loop-bound
primitives — so open interest has never worked in v4, and GEX is a
gamma-squared surface wherever the batches fail.

**v1.36 — 2026-09-02 — r217 — RPT.A / RPT.B / RPT.C OPENED: THE THREE REPORTS.**
The operator's stated end state for the reporting side, recorded before any of
it is built. RPT.A (entries) turns on an outcome variable the STOP CANNOT
MANUFACTURE — was the entry directionally correct long enough to start out in
profit — because judging entries by P&L measures the exit too. Its vectors are
NOT chosen and must not be assumed; the candidate hunt against the bucket is
the next piece of work. RPT.B (MFE/MAE) is per stop TYPE and needs values that
move WHILE THE TRADE IS OPEN, which `fire_snapshot` does not carry. RPT.C
(management) is scoped to the condor, which has never formed — and whether that
is protection or over-strictness is the study, since the two are
indistinguishable from the outside.

**v1.35 — 2026-09-02 — r216 — THE P&L PERCENT COLUMN WAS OFF BY 100x SINCE
r210.** `pnl_pct` is a FRACTION (`(exit - entry)/entry`), so a doubling is 1.07.
r210 replaced `pct_str` — `f"{val:+.1%}"`, where the `%` spec multiplies by
100 — with a bare `:.0f` while narrowing rows for the phone. SPX on 2026-09-02
rendered a 9.15 -> 18.95 runaway as "+1%". The dollars were right throughout,
which is why it survived a night: "+$1,960  +1%" reads as a strange percentage
rather than a broken one. Q11 measured the row's WIDTH and never its VALUES —
width and meaning are different properties and a row check needs both, which
Q12/Q12b now do.

**v1.34 — 2026-09-01 — r215 — THE PIN STRIKE IS BOUNDED TO SPOT; BFLY.11-13
OPENED.** `pin_strike` was an unbounded argmax over the whole chain and
wandered: GOOGL published 20 distinct pins spanning 245-450 in one session
against a ~345 price. Now bounded to 3% of spot (a PRIOR), with the raw argmax
and its distance recorded so it can be fitted. Out of range = NO pin, never an
ATM substitute. **BFLY.11: EM_MAX_FRAC has been filtering mis-located pins by
accident** — a wandering pin inflates `pin_em_fraction` — so loosening it on
reachability grounds would also remove the pin's sanity check. **BFLY.12: the
charm question is NOT RESOLVED** — pooled correlations flip sign within a
single day (charm vs crossings +0.27 pooled, -0.07 on 08-31 alone) because
09-01 has ZERO crossing variance; `pin_concentration` held up better
(crossings +0.40, |end-pin| -0.55 within 08-31). **BFLY.13: is
`pin_concentration` computed off the same unbounded argmax?** If so the one
signal that survived was measured at a possibly-wrong strike. UNEXAMINED.

**v1.33 — 2026-09-01 — r214 — RPT.6 CLOSED; RPT.10 OPENED.**
`query.py`'s unrealized line is signed by structure. Confirmed display-only:
all eight `(current - entry)` sites in exit_engine.py are debit evaluators
where the sign is right, and `_evaluate_condor_leg` already used the credit
sign — so no exit decision was ever taken on it. RPT.10: **menu 55 (fit
readiness) is OOM-KILLED on a multi-day range** — `fit_readiness.py` over
2026-08-24..09-01 was killed by the OOM reaper on control, so any S3 read
spanning a range is currently unusable. That blocks BFLY.9, which needs the
same reader over the chain history.

**v1.32 — 2026-09-01 — r213 (chunk E) — RPT.7 CLOSED. THE FIVE-CHUNK DASHBOARD
PASS IS DONE.** Every skip now names itself: `CondorManagement`, `CreditRoll`
and every `<Strategy>/manage` row are driven only from the position-open branch
and nothing named them, so a flat session printed "dispatch gave no reason" on
every tick. The membership list lives with the registry, not in main.py, so a
new management plan is covered by registering (r35's allow-list rot). The
fallback now reads as a dispatch gap rather than a market condition, because it
fires only where main.py named nothing.
Chunks A-E: r209 subtractions, r210 today-scoping and width, r211 status.py,
r212 the plan-ledger writer, r213 the skip reasons. RPT.8 remains open on
`eod_summary.py` alone; RPT.6 (query.py's sign-inverted unrealized on credit
verticals) and RPT.9 are open.

**v1.31 — 2026-09-01 — r212 (chunk D) — RPT.5 CLOSED, AND r199's DIAGNOSIS
WAS WRONG.** Plans opened by `PlanTick.take()` were never closed by anything,
so every fired plan stayed live for the session — QQQ showed seven runaway
plans flagged LIVE while six of those trades had closed. r199 read that as
duplicate rows and collapsed them for display; they were distinct plans, and
the collapse was merging trades with different outcomes. Fixed at the writer:
`close_for_trade` on the `log_exit` choke point, `close_unfilled` on
supersession, and `CLOSED` added to `TERMINAL` (without it the state said
closed while the query still returned the row as live). The status.py collapse
is removed with its premise. Only chunk E — the "NOT ASKED" reasons in main.py
dispatch — remains under RPT.7.

**v1.30 — 2026-09-01 — r211 (chunk C) — status.py; RPT.9 FILED.**
Open positions to a bare count (the cards and the summed exposure stay in
query.py, which runs beside it), the duplicate-plan warning removed with the
collapse kept until chunk D fixes the writer, EXPIRED stated plainly, and the
CHARACTER line made unconditional at `inactive`. RPT.9: the EXPIRED label was
stale in TWO places — both the live branch and `ORB_STATE_LABELS` still named
the 11:00 cutoff r193 moved to 11:30 on 2026-08-30. Chunks D and E remain.

**v1.29 — 2026-09-01 — r210 (chunk B) — RPT.8 CLOSED IN otv4.**
PLANS, GATES and the closed-trade table scoped to today's session on the one
shared 09:30 cut; rows abbreviated to a single line (59 chars). The `-4 hours`
EDT hardcode is gone from `query.py` — `eod_summary.py` remains UNEXAMINED and
RPT.8 stays open on that file alone. LAST 10 CLOSED merged into TODAY'S TRADES.
Chunks C (status.py), D (the duplicate plan writer) and E (the "NOT ASKED"
reasons) remain under RPT.7.

**v1.28 — 2026-09-01 — r209 (chunk A) — RPT.7 OPENED; RPT.6 AND RPT.8 FILED.**
The box dashboard loses four per-symbol performance rollups and the Live Levels
panel; CHARACTER moves toward status.py. RPT.7 tracks the remaining chunks
(B today-scoping and width, C status.py, D the duplicate plan writer, E the
"NOT ASKED" reasons). RPT.6: otv4 `query.py:268` computes unrealized as
(current − entry) for EVERY structure, which is sign-inverted on credit
verticals — their `current_premium` is the spread's value and they profit as it
falls. dtp r236 got the sign right and deliberately did NOT copy this, because
making two reports agree on a wrong number is worse than having them differ.
RPT.8: `standings.py` carried a hardcoded `-4 hours` session offset (EDT, wrong
for four months of the year) and its own comment says it mirrors
`eod_summary.py` — so that file almost certainly carries it too. Fixed in
standings at dtp r236; eod_summary UNEXAMINED.

**v1.27 — 2026-09-01 — r208 — BFLY.7 AND BFLY.8 SHIPPED.**
The butterfly wing is searched over listed strikes, bracketed by R_FLOOR and
stop survivability, narrowest wins; relaxed is removed from that strategy
entirely. Three existing checkers were re-derived rather than patched — each
had a fixture encoding the rule being replaced, and `check_plan_prepares`'
`calls_good` WAS the 2026-09-01 trade. BFLY.9 (fit STOP_VS_SPREAD_MIN for a
four-leg structure, from S3) and BFLY.10 (charm, already recorded) stay open.

**v1.26 — 2026-09-01 — BFLY.7-BFLY.10 OPENED; LAND.1 RULED.**
LAND.1: a devtools menu item for the lander is NOT wanted — operator,
2026-09-01: *"a manual land command in devtools can wait indefinitely. Your
installer scripts should call it — not me manually running it."* So
`day_trader_pro/tools/land.sh` (dtp r235) is called by install/deploy scripts,
never typed. Closed by ruling before it was built.

**v1.25 — 2026-09-01 — r207 — ORB.8 CLOSED; ORB.9 OPENED; ORB.10 RULED; C.40 AND C.41.**
C.41: **fix the defect, then stop.** The sizing change in the first cut of this
revision was aimed at a symptom the latch had already deleted, and it traded a
true measure (entry-to-stop) for a determinate one (boundary-to-wick). Two
repairs for one defect is how the second becomes the next defect, and the
operator caught it in review rather than in the tape.


The firing sequence becomes the gate. C.40 is the lesson worth more than the
fix: **a guard installed in the ORDER PLUMBING cannot protect a mode that has
no plumbing.** r195 removed ORB's only mode-independent suppressor
(`mark_triggered()`) and replaced it with one that reads a table paper never
writes, and every check went green because they exercised `resting_orders`
directly and never drove `_place_single_leg` in paper. When a guard is
replaced, the new one must be proven in EVERY mode the old one covered.

**v1.24 — 2026-09-01 — r206 / dtp r234 — ORB.7 CLOSED; C.39 RECORDED.**
Staged as a standalone script and proven against the live fleet before it
became a menu item — which is how the wrong-env-layer bug was caught. The two
warehouse inventory rows also merge into one that prompts (MEN.1).

**v1.23 — 2026-08-31 — r205 — IV.1 CLOSED; IV.2 OPENED; C.37 AND C.38.**
Found by probing the bucket for a budget survey and discovering the field was
null on every row. The survey can wait; a silently starved vol layer cannot.

**v1.22 — 2026-08-31 — r204 — WA.1: §0 ADDED TO THE WORKING AGREEMENT.**
Ordered once before and never written; the assistant then asserted it existed.
It is the floor the rest of the file rests on.

**v1.21 — 2026-08-31 — r203 — CFG.1 CLOSED; C.34, C.35, C.36 RECORDED.**
Cut as a NEW revision rather than a re-cut of r201, deliberately: r201 is
landed and baked, and repairing it in place would have left GENESIS reading as
though it had shipped correct. The failure is the record.

**v1.20 — 2026-08-31 — r202 / dtp r233 — RPT.6 CLOSED.**
The suite could tell you how every dimension performed and not what it traded.

**v1.19 — 2026-08-31 — r201 — ORB.5 CLOSED; ORB.6 OPENED; C.32 AND C.33.**
The SPX trade that made $2,500 today deployed $34,750 to do it. ORB now has a
budget, set per underlying, and the operator's scaling rule falls out of two
clamps meeting rather than needing a curve.

**v1.18 — 2026-08-31 — r200 — BFLY.5 AND BFLY.6 OPENED; C.31 RECORDED.**
Docs only, and the point is honesty about WHY. The noon floor survives the day
that falsified its premise, on two better reasons — one of which is itself
unmeasured and now has a backlog entry rather than a free pass.

**v1.17 — 2026-08-31 — r199 — RPT.4 CLOSED; RPT.5 AND C.30 OPENED.**
The third consumer of r161's rule change found unswept in one day. The
dashboards were under-reporting the capital at risk on any box holding more
than one position — which, after r197, is most of them.

**v1.16 — 2026-08-31 — r198 — BFLY.3 CLOSED; C.29 AND BFLY.4 OPENED.**
The third butterfly finding of the day, and the only one that was pure
arithmetic: AMD and PLTR sat unable to form a fly all session because the wings
were computed on a grid neither symbol lists.

**v1.15 — 2026-08-31 — r197 — BFLY.2 CLOSED; C.27 AND C.28 OPENED.**
The 09:45 butterflies cost more than the day's butterfly slot — they cost three
boxes their whole credit session, because an exemption written for entry was
never written for occupancy.

**v1.14 — 2026-08-31 — r196 — BFLY.1 CLOSED; C.25 AND C.26 OPENED.**
First live-fleet open. The butterfly's noon floor was categorised SELECTION,
so relaxed mode widened it to 09:45 and the one-per-session butterfly was spent
before the thesis was valid. The general rule is C.25.

**v1.13 — 2026-08-30 — r195 — ORB.2 CLOSED. The ORB catalog is complete.**
r192 sizing, r193 window + pool, r195 the standing offer. All three need a
bake. The two checks that carry the weight are S5 (a partial then a full fill
grow ONE record) and S6 (an order reporting fills books NOTHING when the
broker's positions do not list the contract) — the operator's ruling made
literal.

**v1.12 — 2026-08-30 — r194 / dtp r232 — DOC.11 CLOSED; ORB.2 DESIGN SETTLED.**
The ledger has rendered wrong since r184 and the cause was a placeholder that
happens to be an HTML element name. ORB.2 stopped being an order-lifecycle
problem once the operator named the right source of truth: the broker already
knows what we own and already averages the basis, so there is no remaining
quantity to persist.

**v1.11 — 2026-08-30 — r193 — ORB.3 AND ORB.4 CLOSED.**
The two small ones, both fully testable without a live tape. ORB.2 (the resting
offer) is the only entry item left and it is blocked on one design ruling, not
on work: whether an order state exists before the first fill.

**v1.10 — 2026-08-30 — r192 — ORB.1 CLOSED; ORB.2-ORB.4 AND C.22-C.24 OPENED.**
The fleet has been sizing one lot since 08-28 while logging that it was not.
The repair is a refactor rather than a patch because the patch shape is what
failed: policy in the caller can write a field the order never reads. Splitting
the entry work out (ORB.2) was the operator's call, and reading the live path
properly shrank it — the mark-limit offer already exists and already sits; only
its 20-second fuse and the re-offer behind it are wrong.

**v1.9 — 2026-08-29 — r191 — S3.1 CLOSED (pending bake); C.18, C.19, C.20 OPENED.**
The last item standing between the operator and querying trades against what
the feed was doing. It was filed as a plumbing change and was not one: all
three tables are being DELETED at 20 days by an armed purge with no push
stage, and the invariant checker built to prevent exactly that could not see
the policy because it was a literal rather than a constant (C.19). SNS.3 — the
three sensor twins — is now unblocked once this has baked and collected a
session.

**v1.8 — 2026-08-29 — r190 / dtp r231 — S3.6 CLOSED; C.17 OPENED.**
The last of the trades-side repoint, and the only one of them that was a
correctness bug rather than a plumbing change. The two-rules-agreeing-by-luck
problem has been on this list since the warehouse work began; what closed it
was not deleting the second rule but making the condition it silently absorbed
impossible to absorb. C.17 states the invariant so the next tool does not
quietly re-create it.

**v1.7 — 2026-08-29 — r189 / dtp r230 — S3.4, RPT.2 AND C.16 CLOSED; RPT.3 OPENED.**
The operator concurred with the r188 recommendation, so the excursion report is
retired and the never-favourable split now lives in `r_ledger` — intent kept,
code not. RPT.3 is what the retirement did NOT settle: the file stays on disk
because two callers still use it, and one of those callers (report_parity) now
has half its job retired out from under it. `menu_extract --diff` reports ❌ on
this change and that is CORRECT — it is not a pure reorder, two labels really
did go, and a tool that said otherwise would be useless.

**v1.6 — 2026-08-29 — r188 / dtp r229 — MENU.1 CLOSED; S3.4 RESOLVED TO A
RECOMMENDATION; RPT.1, RPT.2, C.15 AND C.16 OPENED.**
Looking properly at what the v4 R suite already covers changed the S3.4 answer:
`r_ledger` computes capture and giveback per strategy, side and exit reason, so
the excursion report's descriptive core is already rebuilt — and the only thing
left that nothing else measures is the never-favourable split, which is one
addition to a tool that already holds the population. RPT.1 records the
operator's frame for the rest: judge the QUESTION, not the code.

**v1.5 — 2026-08-29 — r187 / dtp r228 — S3.5 CLOSED; S3.4 RE-FILED AS A RULING,
S3.8, C.13 AND C.14 OPENED.**
Operator asked whether reports 40 and 41 are even relevant to v4 or are running
on v3 benchmarks. Measured: **41 is fine** (nine of ten dimensions are
engine-agnostic; the tenth was dead and is gone), **40 is half fine** — its
measurement is engine-agnostic and its verdict layer is v3, and `stop_sweep.py`
may already supersede it. That is a ruling, not a task, so S3.4 now says so
instead of sitting in a work queue. C.14 is the generalisation nobody had
written down: the epoch contamination is not report 41's problem, it is
everything's.

**v1.4 — 2026-08-29 — r186 / dtp r227 — S3.3, DOC.5 AND DOC.10 CLOSED; C.12 OPENED.**
S3.3 was filed as a one-line fix and was not one: the phase had been failing
nightly since the v2 EOD install, because the same rebuild that pointed
CONSOLIDATE at S3 also disabled the harvest that fed the phase behind it (C.12).
DOC.10 was not on any list — the fixture written to prove S3.3 rendered a report
that said `source: warehouse]` and `SOURCE DEGRADED`, which is what a test is
for.

**v1.3 — 2026-08-29 — r185 — DOC.4 CLOSED; DOC.9 AND C.11 OPENED.**
The front page had been wrong for nine days about how many boxes exist, and the
reason it survived r74's sweep is the reason DOC.9 exists: the file carried no
version in either place, so no gate and no reviewer had anything to compare.
Fixing the sentence took one line; the four other stale claims found while
reading the file are the actual yield.

**v1.2 — 2026-08-29 — r184 / dtp r226 — S3.2 CLOSED; SNS.4, C.9 AND C.10 OPENED.**
The first item in the S3-repoint queue landed, and building it turned up C.9 —
a property of the warehouse nobody had written down, and one that would have
quietly under-reported every derived reader built after it. That is why SNS.4
exists as a condition rather than a task: the next three sensor twins inherit
the trap, and the loader is the place it is already solved.

**v1.1 — 2026-08-29 — r183 / dtp r225 — GATE.1 CLOSED; DOC.6–DOC.8 AND C.7–C.8 OPENED.**
The land-discipline checker landed, and measuring history with it is what
produced DOC.6: **9 of the last 18 revisions shipped a file whose header did
not move.** That number is the justification for the gate and it is also a
debt — the gate stops the next one and repairs none of the previous ones.
C.7 records what the gate does NOT prove, because a checker whose limits are
not written down gets cited for things it never established.

**v1.0 — 2026-08-29 — r182 — FILE CREATED.**
WORKING_AGREEMENT §18 has required `docs/BACKLOG.md` in every archive since
2026-08-04 and the file did not exist in this repo; `analysis/trade_readiness.py`
already referenced it. Seeded with the 2026-08-29 review of the reporting
apparatus: the open S3-repoint queue (S3.1–S3.7), the sensor twins
(SNS.1–SNS.3), the end-state joins (END.1–END.2), four rulings awaiting the
operator (ASK.1–ASK.4), the r183 ORB candidate (ORB.1), and the three items
closed by r182 itself (DOC.1–DOC.3).
⚠️ **No CPI or CV is reported and none will be** until a real cost baseline
exists. Schedule status and the BUILT/PUSHED/BAKED completion split are the
honest measures available; an index computed off an invented baseline is
decoration wearing the clothes of measurement.
