# SHIPPING_LOG.md

**One entry per tarball shipped. Appended at ship time, never reconstructed.**

Per-file changelogs answer *"why is this line the way it is."* Git answers
*"what changed."* Neither answers **"what was r14, and why did we ship it"** —
which is the question actually asked weeks later, usually while trying to work
out whether something was already tried.

⚠️ **APPEND AT SHIP TIME.** WORKING_AGREEMENT §35. A log written from memory at
the end of a session is a log of what was remembered, not what was shipped.

Format: `rN — date — one line on what it did — files touched — bake needed?`

---

## OTV4

| r | date | what it did | bake |
|---|---|---|---|
| **r1** | 08-19 | Repo skeleton: directories, `WORKING_AGREEMENT.md` carried verbatim, plus new README / VISION / INHERITED_FINDINGS. Nothing executable. | no |
| **r2** | 08-19 | The port — 65 files from OTV3 with headers reset to 4.0 and inherited doctrine preserved. Exits, collection, structure, strategies as shells, provisioning, deploy units. | no |
| **r3** | 08-19 | The 20 files the first manifest silently omitted, including **`main.py` and `config.py`** — an entry point and every constant. Found by the canary rebuild, not by anything erroring. | no |
| **r4** | 08-19 | `gen_file_map.py` — generated dependency map with drift / orphan / broken-import checks. **Restored `volatility_engine` and `trend_engine`**, dropped in error on name rather than content (they produce VWAP and ADX). Harnesses moved to `tests/`. | no |
| **r5** | 08-19 | `analysis/market_state.py` replaces `regime_classifier` — **keep the types, drop the scoring.** The file map showed 8 of 9 importers wanted only the dataclass and the enum. | no |
| **r6** | 08-19 | `assemble_market_state` replaces `run_regime_classification`: **17,177 characters of classification and L2 override become a ~60-line structural assembler.** The L2 block was already dead code — `_L2_OK` was permanently False. | no |
| **r7** | 08-19 | `entry_profile.py` — what made a good entry good, per strategy, labelled on **directional correctness** rather than P&L. | no |
| **r8** | 08-19 | Recorded-column features plus **coverage reporting** — an empty column is not a null result. Found `gap_pct` and `level_strength` 0% populated. | no |
| **r9** | 08-19 | `opening_bias.py` — does the session opening expose direction, asked of the tape rather than the trade book. | no |
| **r10** | 08-19 | **Forward-only** measurement plus anchor/BB/ADX/slope state. The inclusive measure contained its own predictor: 82% inclusive against 51% forward, a +31% gap that was the opening candle counting itself. | no |
| **r11** | 08-19 | `chain_feasibility.py` — how big a move a contract needs to pay, against what the tape delivers. **Required 0.90% p50; delivered 0.50%.** | no |
| **r12** | 08-19 | `tape_harness.py` — what precedes a payable move, mined across ~300,000 bars with a **date-split holdout**. Every surviving condition helped UP *and* DOWN: they predict movement, not direction. | no |
| **r13** | 08-19 | `magnitude_estimator.py` — can the underlying REACH the target. **ADX measured FLAT across every band** (0.69–0.74% median excursion from ADX 12 to 45). | no |
| **r14** | 08-19 | Strike reachability by **ATR** band — monotone, 5.6× spread, and the map the runaway trade uses. ADX table kept beside it, labelled flat, so nobody re-proposes it. | no |
| **r15** | 08-19 | `exit_record.py` — net dollars and the **loss tail** per exit, not just win rate. | no |
| **r16** | 08-19 | Normalise exit reasons before grouping. v3 wrote per-trade P&L into the reason string, so **ORB's entire 107-trade record was invisible under n<5** and printed as nothing. | no |
| **r17** | 08-19 | **`RunawayContinuation`** — the first structure-only entry. ORB runs to 50% TP and holds; ATR gates the trade and picks the strike; no regime label anywhere. | bake |
| **r18** | 08-19 | Expose `pin_concentration` on `GEXSnapshot` — computed, used for a boolean, **discarded**. Plus the test of whether it predicts the pin holding. | no |
| **r19** | 08-19 | Real **open interest** over REST. `open_interest` was a declared field with **no producer**, so GEX has been a gamma-squared surface since it shipped. | bake |
| **r20** | 08-19 | **GEX pin butterfly — complete and PARKED.** Its input is an artifact until real OI accumulates (~2 weeks). | no |
| **r21** | 08-20 | **`SweepCreditSpread`** — sell the boundary a swept pool just became. High sweep → ceiling → call credit; low sweep → floor → put credit. | bake |
| **r22** | 08-20 | Sweep spread exits: **15% stop, hold to 15:45, no trail, no TP.** Recognised as a credit vertical by derivation from persisted columns — it was falling through to DIRECTIONAL and would have been laddered out at 15:40. | bake |
| **r23** | 08-20 | `sweep_discriminator.py` — which swept pools held, from **2,169 tape events** rather than 34 trades chosen by a broken gate. | no |
| **r24** | 08-20 | Adopt the measured conditions: window **13:00–15:00** (39% vs 26% survival) and a **0.25% pierce ceiling** (33–34% vs 19–21%). Also corrected a pre-measurement floor that excluded the best-measuring bucket. | bake |
| **r25** | 08-20 | Sell the **nearest pierced strike**, not the pool. Entry ladder rebuilt: 25% start, **one venue increment per rung**, ratcheting, never worse than mark. | bake |

---

## OTV3 (still the repo the fleet trades until the repoint)

| r | date | what it did | bake |
|---|---|---|---|
| **r195b** | 08-19 | **Open interest backported.** OTV4 collects nothing until the repoint, so the two-week GEX wait only starts when OTV3 collects. Also exposes `pin_concentration`. | bake |

---

## ⚠️ WHAT THIS LOG IS FOR

**Reading it back should answer "has this been tried?"** Three times in the week
before it existed, a defect was investigated that the repo had already
documented — `is_trend_credit` was recorded as "NOT A COLUMN" five days before
it crash-looped NFLX, and `_session_extremes` carried the exact caveat that
would have prevented TCS.3.

**A line here is cheap. Re-deriving a finding is not.**
