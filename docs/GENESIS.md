# GENESIS — every revision shipped to options_trader_v4

**One line per tarball, in order, from r1.**
**Appended as part of the land command (WORKING_AGREEMENT §33), never after.**

This is not `git log`. Git records what changed; this records **why**, and it
keeps the corrections — several revisions below exist because an earlier one was
wrong, and those are the entries worth reading.

---

## Why this repo exists

OTV3 was closed on 2026-08-19 after its central premise was **measured false**,
not abandoned on a hunch. `tests/direction_skill.py`, 715 closed directional
trades over 16 sessions with ORB and neutral structures excluded: the regime
classifier picked the correct **side** on **44.9%**, 95% CI **[41.3%, 48.6%]** —
the interval sits entirely below a coin flip. Puts were **34.2%**. The strategy
most dependent on it lost **$5,872** across 660 trades.

What made money was already regime-independent: `orb_trail_stop` 95% win / 107
trades / **+$37,848**, `theta_bleed` 100% / 107. Operator: *"every day where P&L
was green or very green is nearly entirely based on the ORB trade and the
quality of our stops."*

**v4 keeps the collection, the execution and the exits. It replaces the layer in
between.** Full evidence in `docs/INHERITED_FINDINGS.md`.

---

---

## What the corrections say

Six of these twenty-five exist because an earlier one was wrong, and the pattern
is consistent enough to name: **the measuring instrument failed before the code
did.**

· r3 — a manifest built from a description list, missing 20 files silently
· r4 — an orphan report that flagged 12 modules, of which **only 2 were real**;
  three were live code the resolver could not see, and one had traded four
  times the day before
· r10 — a measure that contained its own predictor
· r16 — a grouping key carrying a per-trade value, hiding 107 trades as nothing
· r19 — a proxy that was never labelled as unavailable, so it became
  indistinguishable from data for the life of a project
· r24 — a threshold set before the measurement that contradicted it

**Every one of them printed something plausible.** That is why WA §33 fails the
land command on drift rather than warning, and why an absent measurement is
reported as absent rather than as zero.

---

## Revisions

⚠️ **THIS TABLE IS THE LAST THING IN THE FILE, DELIBERATELY.** The land command
appends with `>>`, so the append point must BE the end of the document. When the
prose sat below the table, r26 and r27 landed underneath it and the two sections
interleaved. Nothing after this table.

| rev | what it did |
|---|---|
| **r1** | Skeleton. Directory structure, `WORKING_AGREEMENT.md` carried verbatim, plus README, VISION and INHERITED_FINDINGS written fresh. No code. |
| **r2** | The port — exits, collection, structure/levels, risk, warehouse, tooling, strategies as shells. Headers reset to 4.0 with the **inherited doctrine preserved**: 280 KB of measured findings and design guarantees, kept on the condition that WA §32 requires reading them before editing a file. |
| **r3** | Completed the port — `main.py`, `config.py`, `shadow/`, `notifications/`, tooling. **The first manifest silently omitted 20 files**, including the entry point and every constant, because it was built from a hand-written description list rather than the source tree. |
| **r4** | `tests/gen_file_map.py` — the file map generated from the real import graph, with drift, orphan and broken-import checks. **Restored `volatility_engine` and `trend_engine`**, dropped at the split on location and name rather than on what they compute: they produce VWAP and ADX, both on the successor list. |
| **r5** | `analysis/market_state.py` replaces `regime_classifier`. **Keep the types, drop the scoring** — the file map showed eight of its nine importers wanted only the dataclass and the enum. Repo imports 68/69. |
| **r6** | `assemble_market_state` replaces `run_regime_classification`: 17,177 characters of classification and Layer-2 override become a ~60-line structural assembler that classifies nothing. **`main.py` had been importing cleanly while runtime-broken** — a call to a function that no longer existed anywhere. |
| **r7** | `tests/entry_profile.py` — what made a good entry good, per strategy, labelled on **directional correctness** rather than P&L, because P&L conflates entry quality with exit management. |
| **r8** | Recorded-column features with **coverage reporting**. An empty column read as "no signal" when it was "no data" — `gap_pct` and `level_strength` were 0% populated, `vix_at_entry` 2%. |
| **r9** | `tests/opening_bias.py` — does the session opening expose direction, asked of the tape rather than the trade book (797 session-symbol observations, none chosen by a broken engine). |
| **r10** | **Forward-only measurement.** r9's inclusive numbers were partly tautological: the opening candle's own range sits inside "the day's excursion", which is why they rose monotonically with window length (5m 67% → 30m 82%). Measured from the window close instead: **every cell 49–53%, a coin.** |
| **r11** | `tests/chain_feasibility.py` — how big a move a contract needs to pay, against what the tape delivers. 110,162 contract observations. |
| **r12** | `tests/tape_harness.py` — what precedes a payable move, mined across ~300,000 bars with a **date-split holdout**, against a bar the chain sets rather than one chosen. |
| **r13** | `tests/magnitude_estimator.py` — can the underlying **reach** the target. Tests ADX beside ATR rather than assuming. |
| **r14** | Strike reachability by **ATR** band. **ADX measured FLAT** — every band from 0-15 to 40-100 produced the same median excursion, so ADX 45 reaches no further than ADX 12. ATR is monotone across the same bars, a 5.6× spread. The ADX table is kept in the output, labelled flat, so nobody re-proposes it. |
| **r15** | `tests/exit_record.py` — net dollars and the **loss tail** per exit reason, not just win rate. |
| **r16** | Normalise the exit reason before grouping. v3 writes the trade's own P&L into the reason string, so every distinct percentage became its own reason — **ORB's entire 107-trade record was invisible under an n<5 floor and printed as nothing.** |
| **r17** | `RunawayContinuation` — the first v4 entry rule. No regime label. ATR gates the trade and picks the strike; **ADX is unused and that is a measurement, not an omission.** |
| **r18** | Expose `pin_concentration` on `GEXSnapshot` — it was computed, used to decide a boolean, and discarded as a local. Plus the test of whether it predicts the pin holding. |
| **r19** | Fetch real **open interest** over REST. `open_interest` was a declared field with **no producer** — 0 on every contract — so `gex_data` fell through to `oi_proxy = 1000 × gamma` and multiplied by gamma again. **GEX has been a gamma-squared surface, not dealer positioning, since it shipped.** |
| **r20** | `GEXPinButterfly` — complete and **PARKED**. Every gate works; it is off because its input is not yet trustworthy. Parked ~2 weeks for real GEX to accumulate. |
| **r21** | `SweepCreditSpread` — sell the boundary a swept pool just became. High sweep → ceiling → call credit; low sweep → floor → put credit. Reads no age-decay, no damper chain, no regime label. |
| **r22** | Its exits: **15% stop and 15:45 hold, no trail, no TP.** It had been falling through to `DIRECTIONAL` in `structure.py` and would have been laddered out at 15:40 with the debit positions, giving away the theta it was opened to collect. |
| **r23** | `tests/sweep_discriminator.py` — which swept pools **held**, from the tape (2,169 events) rather than 34 trades chosen by a gate that could not fire. |
| **r24** | Adopted the measured conditions: window **13:00–15:00** (39% survival vs 26% before 10:30) and a **0.25% pierce ceiling** (33–34% vs 19–21% deeper). ⚠️ **A deep pierce means a WEAK level, not a strong rejection** — 1.28% median adverse against 0.46%. Also corrected a pre-measurement floor that had excluded the best-measuring bucket. |
| **r25** | Sell the **nearest pierced strike**, not the pool. Entry ladder rebuilt: 25% start, **one venue increment per rung**, ratcheting so a refused price never returns, and never worse than mark. |
| **r26** | GENESIS.md: one line per revision from r1, with the corrections kept. WA 35 appends it inside the land command, because no checker can tell whether a line is missing. |
| **r27** | Canonical land header: REV and DESC set once, the same string becomes both the Genesis line and the commit subject, appended before git add so it ships inside the commit it describes. |
| **r28** | GENESIS restructured so the revisions table is the LAST thing in the file - the land command appends with `>>`, so r26 and r27 had landed underneath the closing prose and the sections interleaved. |
| **r29** | Universal relaxed-entry toggle: `configure.sh` option 7, paper-only and guarded, loosens SELECTION gates but never a feasibility veto, and tags every trade `relaxed_entry=1` so the population stays separable. The live guard required an explicit `OT_PAPER_TRADING` assertion after a first draft was satisfied by a config default. |
| **r30** | GEX pin butterfly v4.1 - apex OTM on the pin with DISTANCE AS THE EDGE, gated on a 30-100% expected-move band from the chain's ATM IV rather than VIX. v4.0 had built an ATM butterfly requiring price NEAR the pin and vetoed high ATR - both backwards. |
| **r31** | Gate categories as DATA - each strategy declares a GATES dict and tests/check_gates.py reads the code, refusing any relaxed.widen() on a non-SELECTION gate. Replaces a docstring check that only proved somebody wrote the right words, and that broke the land command because the active venv had no pytest. |
| **r32** | GENESIS repair: r29 and r30 were never appended and r31 was appended twice, because the land command's checks verify the REPO STATE rather than that this tarball was applied - a re-run after a successful land looks identical to a fresh one. Row count now guards it. |
| **r33** | TRADES.md with all five specs and the condor's management ladder (leg 1 at 15% while unhedged, then roll, then invert to a butterfly, then stop and page). Deletes butterfly_strategy, continuation_strategy and sweep_reversal_strategy - superseded, not shelved - with their imports and dispatch. ORB made purely mechanical: no regime, no conviction. |
| **r34** | All three v4 strategies wired into dispatch - runaway first (it reads ORB's own state and firing disarms the retest), then sweep credit spread, then the parked butterfly so its plumbing is audited now rather than on the day it unparks. check_dispatch.py verifies order, scope and that each generate_signal EXECUTES. Deletes docs/SHIPPING_LOG.md, a duplicate shipping record drafted in the same session as GENESIS and abandoned at r26. |
| **r35** | Long-debit cutoff extended to 11:30 and keyed on STRUCTURE rather than a strategy name list. v3's allow-list held three names, two of which had been deleted, while RunawayContinuation was absent and would have been silently EXEMPT - an allow-list rots permissively. Verticals and butterflies run all day; an undeclared strategy fails closed. |
| **r36** | ORB cleanup: confluence gate stripped (it could never fail - two factors were added unconditionally), reachability replaces premium>0 as a FEASIBILITY veto, telemetry on the liquidity block, and GATES declared. Also closes a scope hole in check_gates that skipped any strategy not importing relaxed - which was hiding ORB, the condor and TC.6. |
| **r37** | Two studies: tine_order_study asks whether a channel's slope predicts which rail is tapped first and whether a WRONG-tine tap predicts trouble (traverse and breach rates); orb_bleed_study measures how fast ORB winners declare themselves, on the UNDERLYING rather than the option, to define the sideways-grinder stop. |
| **r38** | Record MFE/MAE and the bar each occurred: exit_engine tracks it every tick, position_manager passes it, trade_logger persists it. The data already existed as TrailState.peak_close and was discarded at close - the same defect as pin_concentration and flat_angle_deg. Also documents that max_profit is NOT MFE: it is written once at entry from the structure's THEORETICAL maximum, and this project nearly built a study on it. |
| **r39** | Fix both studies. tine_order rebuilt on a DAILY channel over prior sessions - the intraday version extrapolated a 60-bar slope across 330 and manufactured its own 81% result, with breached=100% on BOTH arms as the tell. orb_bleed's join now reports every drop by cause and REFUSES when under half the rows join, instead of scanning from the session open when a timestamp format disagrees. |
| **r40** | fork_respect_study: does price respect an hourly CONTAINED fork's extended boundaries? Span is an output not a parameter, rails held flat forward to avoid the extrapolation that fabricated the daily study's result. |
| **r41** | fork_respect_study fixes: an off-by-one made contained_channel return None on EVERY call, so the study reported "no qualifying forks" against the whole archive - a tool-caused absence wearing the costume of a null. And the fork now spans SESSIONS: the first version fitted 3 hourly bars inside one day, while pitchfork.py records measured hourly spans of 12, 32 and 139 bars. |
| **r43** | stress_entry_path: hostile inputs against every entry path, and the 18 bugs it found. Worst: a NaN ATR INVERTED the feasibility veto - every comparison against NaN is False, so target_delta(nan) returned a strike in exactly the tape where 0 of 5,517 bars reached the required move. Same in the sweep ceiling. Plus NaN/-inf prices firing signals, math.floor(nan) raising inside pierced_strike, and a NaN mark recorded as the MFE peak. |
| **r44** | AUDIT_HANDOFF.md - the adversarial brief. Covers both entry modes, every exit path, ladder and ratchet claims to be broken rather than believed, management/restart/orphan/journal integrity, crash loops and circular logic. Names where the ground is soft and tells the auditor to attack the checkers first, because two of mine could not fail. |
| **r45** | AUDIT.md - the delivery contract for the audit. FINDINGS.md always, fix tarball only if there are fixes, changed files only, no GENESIS, no scaffolding, no reformatting, no new deps. Doctrine blocks preserved, headers and changelogs bumped, tests as plain scripts not pytest. Every fix validated against the six checks before re-shipping. |
| **r46** | AUDIT FIXES. F0: my r38 inserted _track_excursion at column 0 above `def evaluate`, which sat INSIDE the class - Python read the class as ending there and the ~2,000 lines below became nested locals of a telemetry helper. ExitEngine had ONE attribute and no evaluate. EVERY intraday exit was dead code for seven revisions behind a green board, because none of my six checkers executes an exit. F2: TC.6 was live on default=1 while I had written NOT DISPATCHED into its own doctrine block without grepping for the dispatch. Plus 8 more, all verified. |
| **r47** | FEED.2 ported to v4 - the body below the header was BYTE-IDENTICAL across all three repos, so one defect, one fix, three places. symbol_map keyed on (dx_symbol, interval) while FEED.2 subscribes the same symbol+interval TWICE, so the RTH 1h route was destroyed at construction and every 1h bar landed under *_EXT. Six days fleet-wide, nothing raised. Also rewrote C5 in the ported test: it grepped for a variable name the code does not use, so re-planting the exact defect left it reporting ALL PASS. |
| **r48** | RTH guard ported from the SMC thread v3.17. The FEED.2 fix corrected STREAMING routes; the restart backfill then wrote 24-HOUR bars into the plain series anyway - plain 1h carried hours 00-23 on equities from 08-05, ~12/hour overnight vs 38-39 in RTH, while SPX stayed clean because an index has no overnight session. Worse than the hole it replaced: a gap announces itself, a series that changes character mid-stream does not. Bars are SEGREGATED to SYM_EXT, never dropped - EXT_INTERVAL is 1h only so an overnight 5m has no other home and DXFeed history is use-it-or-lose-it. |
| **r50** | chmod +x on all 16 root shell scripts. Git does not preserve the executable bit unless it is set in the index, so a repointed box got Permission denied on configure.sh. Found on the LLY throwaway repoint before it could hit all 15 tomorrow - and the same test proved the sync is clean, all eight checkers pass in a box venv, the env survives a hard reset against a different repo, and the gitignore boundary holds. |
| **r51** | Thread close-out: PORT_STATE rewritten as the current-state document, ROADMAP given numbered next-actions for Friday and beyond, FILE_MAP orientation moved INTO the generator (a hand-edit to a generated file vanishes on the next run), and docs/HANDOFF.md written for the next thread. |
