# BACKLOG.md — v1.9

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
