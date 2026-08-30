# BACKLOG.md — v1.3

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
| **DOC.5** | WA §25 routes the reader to `docs/README.md` — *"read it first"* — and that file does not exist. | ⬜ | The rule that exists to stop docs going unread points at a missing doc. |
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
| **S3.1** | Push `fork_series`, `indicator_series`, `surface_series` from `derived_store.db`. | ⬜ | **The long pole; SNS.3 waits on it.** ⚠️ `push_series()` is called with `FEED_DB` and these live in `DERIVED_DB` — needs a **second call** with its own table tuple and a namespaced ledger key, NOT an append to `SERIES_TABLES`, which would silently find nothing. These three are exactly "what the feed was doing at the time". |
| **S3.3** | `eod_analysis._excursion()` → pass `--bundles-dir reports/warehouse`. | ⬜ | One line. The nightly builds an S3 bundle in `_consolidate()` and then, one phase later, reads the **local per-box DBs** anyway. |
| **S3.4** | Menu 55 (excursion) → default to `reports/warehouse`; DB path becomes an explicit flag. | ⬜ | ⚠️ `--since` is **refused** without per-box DBs, so cumulative windows need `reports/warehouse/` populated for every date first (menu 76 does that). |
| **S3.5** | Menu 56 (trade breakdown) → default to `reports/warehouse`. | ⬜ | `--bundles-dir` already exists; menu 81 is the warehouse twin. |
| **S3.6** | Remove `trade_report.py`'s dedup shim. | ⬜ | Dead code once S3.5 lands. It only ever existed to survive pre-07-28 cumulative bundles. **Do S3.5 first** — removing it before the glob is repointed under-counts. |
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

| **C.11** | **A FACT WRITTEN IN THREE DOCUMENTS ROTS IN THE ONE NOBODY SWEEPS.** The fleet count lived in `README.md`, `ROADMAP.md` S.4 and WA §30; r74 fixed two. Prefer ONE authority plus pointers: the panel is `selector.PANEL`, the module graph is the generated `FILE_MAP.md`, the table ownership is the generated `WRITE_MAP.md`. Where a fact must appear twice, the second copy says which one outranks it. | r185 |
| **C.9** | 🔴 **A DERIVED `dt=` PARTITION IS THE PUSH DAY, NOT THE ROW'S DAY.** `push_derived` files every CHANGED row under `datetime.now(ET).date()` at push time, so a plan created Monday and updated Wednesday lands in **Wednesday's** partition, and the first push after any gap files a whole table's history under one day. Reading one partition per requested date under-reports **silently** — it returns a smaller, entirely plausible number. `load_derived()` scans a forward window (`DTP_DERIVED_FORWARD_DAYS`, default 3) and then files each row by ITS OWN timestamp converted to the ET trading day. **Partition selection and row attribution are different questions.** | r184, read from `s3_push.push_derived` |
| **C.10** | Timestamp columns differ by table and the difference is meaningful: `plan_ledger` is dated by **`created_ts`** (when the plan was FORMED), everything else by `ts_epoch`. Dating a plan by `updated_ts` would move it to whichever session it last transitioned in. | r184 |
| **C.7** | **GATE.1 proves the bookkeeping, not the edit.** It asserts the version MOVED and that a dated entry names it; it cannot tell whether the entry is TRUE. The land command's own content gate — a positive grep for a distinctive line from the real change plus a negative grep that the superseded code is gone — is what proves the edit happened. Running GATE.1 and calling a delivery verified is the laundered green WA §18 names. | r183 |
| **C.8** | The otv4 checkout on control is **`~/options-trader-v4`** (hyphens), not `options_trader_v4`. Confirmed by r182's land output. | 2026-08-29, observed |

---

## PART 4 — CHANGELOG

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
