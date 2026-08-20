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

## Revisions

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
| **r26** | GENESIS.md: one line per revision from r1, with the corrections kept. WA 35 appends it inside the land command, because no checker can tell whether a line is missing. |
| **r27** | Canonical land header: REV and DESC set once, the same string becomes both the Genesis line and the commit subject, appended before git add so it ships inside the commit it describes. |
