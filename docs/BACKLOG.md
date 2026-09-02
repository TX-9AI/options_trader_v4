# BACKLOG.md — v1.35

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

### S3 repoint — the reporting apparatus

The governing measurement, taken 2026-08-29 against `docs/WRITE_MAP.md` and
`warehouse/s3_push.py`: **19 of 27 tables already reach S3.** Not pushed:
`fork_series`, `indicator_series`, `surface_series`, `character_axis_sample`,
`chain_marks`, `chain_subs`, `chain_subs_aux`, `feed_meta`. The last four are
feed plumbing and are not warehouse candidates.

| ID | item | status | notes |
|---|---|---|---|
| **RPT.3** | **`excursion_report.py` is retired from the menu but NOT deleted, and `report_parity.py`'s own fate is now open.** | ⬜ | The script still has two callers: the nightly `eod_analysis` EXCURSION phase (r186 repointed it) and `tools/report_parity.py`, which runs report 40 three ways. **A retired MENU ITEM and a deleted FILE are different decisions** and collapsing them breaks a working caller. Two things to rule on, in order: (1) drop the nightly EXCURSION phase — R_LEDGER already runs in the same chain — but **not before the never-favourable numbers have been read once against a real session and seen to reproduce what the excursion report was saying.** That is a parity argument, not caution. (2) parity itself compared LOCAL vs WAREHOUSE, and after r184-r188 there is barely a local pipeline to compare against; half its job (report 40) is now retired. |
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
| **S3.7** | Menu 54 → retire, or repoint to `warehouse_reader.build()`. | ⬜ | Duplicates what `eod_analysis._consolidate()` already does from S3. |

### Sensor twins — control-side, read S3, boxes untouched

The whole SENSORS block (menu 19–30) is an SSH fan-out running `sqlite3`
against each box. That is right **during** a session and wrong after it.

| ID | item | status | notes |
|---|---|---|---|
| **SNS.1** | Control-side twin for sensor 30 (Order flow). | ⬜ | `prints` and `quote_series` are already in S3. **Portable today**, no dependency on S3.1. |
| **SNS.2** | Control-side twins for sensors 20, 21, 23, 24, 25, 29. | ⬜ | All six tables already in S3 via `DERIVED_TABLES`. |
| **SNS.4** | Every future S3-sourced derived reader must use `warehouse_reader.load_derived()`, not a bare partition read. | ⬜ | Not a task on its own — a **condition on SNS.1–SNS.3 and END.1**. See C.9: a derived `dt=` is the PUSH day, so reading one partition per date under-reports silently. The loader already handles it; hand-rolling a `read_prefix` loop would reintroduce it. |
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
| **ASK.1** | `character_axis_sample` — include in S3.1's push, or leave it on the box? | ⬜ |
| **ASK.2** | `shadow/` still ships to the boxes and `s3_push` still runs a shadow stage, but shadow was never installed on the v4 fleet. Cut both, or leave? | ⬜ |
| **ASK.3** | Disposition of `AUDIT.md`, `AUDIT_HANDOFF.md`, `AUDIT_FINDINGS.md` and the four `HANDOFF_*` docs — spent thread contracts. Keep, archive, or delete? | ⬜ |
| **ASK.4** | `debug_status.py` and `stress_theta_bleed.py` sit at repo root. Move to `tests/` per WA §28, or are they entry points? | ⬜ |

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
