# docs/ROADMAP.md — v4.0 — options_trader v4

**Opened 2026-08-19. This is the governing plan.**

**Success is `docs/VISION.md`: dollars, and an edge that survives a measurable
period. Everything below is in service of that and nothing below is a goal in
itself.**

---

## PHASE 0 — SKELETON AND SALVAGE  ⏳ IN PROGRESS

**0.1** Repo skeleton, `WORKING_AGREEMENT.md` carried verbatim, README, VISION,
INHERITED_FINDINGS. ⬜
**0.2** Port the verbatim set — exits, collection, structure/levels, risk,
warehouse, utils, tooling. **Every header reset to 4.0, every changelog fresh.** ⬜
**0.3** Port the shells — all strategies, `main.py`, `entry_engine` — with
**every regime gate and conviction read stripped.** They will not fire until
Phase 2 gives them triggers. ⬜
**0.4** `check_versions.sh` rebuilt for v4 with **behavioural canaries only** —
never version-string pins (a canary that reddens on a legitimate bump teaches
the operator to ignore a red run). ⬜

⚠️ **PHASE 0 ENDS WITH A REPO THAT COLLECTS AND MANAGES BUT DOES NOT ENTER.**
That is deliberate: exits and collection are the proven parts and can run while
entries are still being mined.

---

## PHASE 1 — MINE THE ENTRY CONDITIONS

> **The triggers are MINED, not theorised.**

**1.1** Derive structural features retroactively from banked OHLC at every
historical entry — swing sequence, channel position, whether the last break
held, distance to prior-session extremes, impulse character of the entry bar.
**They need not have been journaled.** ⬜
**1.2** Split favourable vs never-favourable and find where the structure
separates. Same machinery as `separation_probe.py`, pointed at entry conditions
instead of primitives. ⬜
**1.3** ⚠️ **CALLS AND PUTS SEPARATELY.** At 34.2% put accuracy the bearish
entries are close to ANTI-selected — trades taken short when structure said
otherwise. **The never-favourable puts are the sharpest "do not fire" signature
in the data**, and pooling them with calls would blunt it. ⬜
**1.4** Write the cutoff where the distributions actually part. ⬜

**🔵 WHY THE BROKEN CLASSIFIER MAKES THIS SAMPLE GOOD** (operator's point, and
it is the better framing): a 44.9% engine is close to a **random sampler** of
entry conditions. The favourable trades are therefore not "cases where the
engine was right" — they are **cases where the structure was good enough to work
despite it.** The never-favourable set is an equally broad sample of what does
not work.

⚠️ **THE RESIDUAL BIAS, STATED.** The engine still chose WHEN AND WHERE to look,
so coverage is biased even though direction was noise. **A mined bar needs
forward validation before it sizes anything.**

---

## PHASE 2 — WIRE THE TRIGGERS, LOG-ONLY

**2.1** Each strategy gets a structural trigger from Phase 1. ⬜
**2.2** **LOG-ONLY first.** Journal what would have fired and what was refused;
gate nothing. ⬜
**2.3** ⚠️ **THE REFUSALS ARE HALF THE DATA.** `rejection_ledger` carries over
for exactly this — *a bar that only shrinks the book is not confidence, it is
fear.* A trigger is judged on what it declined as much as what it took. ⬜
**2.4** Compare the log-only book against the real one. **Dollars.** ⬜

---

## PHASE 3 — ADVERSARIAL AUDIT, THEN LIVE

**3.1** Once entry criteria exist on paper, request an adversarial audit before
anything trades on them. ⬜
**3.2** Enable entries on the panel. Exits and sizing unchanged. ⬜
**3.3** Measure dollars over a period long enough that variance cannot explain
it. ⬜

---

## PHASE 4 — EARNED LAYERS (not before)

**4.1 Structure-first regime labels.** Vocabulary — in-channel, breakout,
compression, ranging, breakout-volatile, trending — **rebuilt from structure**,
shaped by derived cues. ⚠️ **INFORMS, NEVER AUTHORISES.** Any setup may read
one; no setup may require one. ⬜
**4.2 A scorer, if earned.** From a shadow observer grading entries
post-mortem — **never built ahead of the evidence.** OTV3's was, and A-grade
lost $8,244 at 1.5× size while B made +$1,893. ⬜
**4.3 Sizing on the scorer, if it clears.** Separation with direction ·
selection-clean measurement · window stability · marginal fee-adjusted-ROI
placement. ⬜

---

## STANDING OPERATIONAL WORK

**S.1 Conductor becomes a VERIFIER, not a collector.** Completing the S3 move is
**high priority**. Control remains 1-REPORTER. ⬜
**S.2 All tests and tools live in `/tests`.** Nothing new at repo root; the
existing root sprawl on control migrates. ⬜
**S.3 Bot independence is a FEATURE.** No box may require control to be
reachable in order to trade. ⬜
**S.4 Fleet: 15 traders, 29 collectors.** ⚠️ Collection is fleet-wide, trading is
panel-only. **A box that stops collecting because it is not trading is a box
whose pitchfork and ADX depth quietly dies**, and DXFeed history is
same-evening only. ⬜

---

## ⚠️ MIGRATION HAZARD — READ BEFORE ANY RE-FLASH

*"Overwrite execution and regime engines; historical data must not be deleted."*
**On the boxes those live in the same tree.** `~/options-trader/data/feed_store.db`
holds the candle and chain-mark depth that pitchfork and ADX warm-up depend on,
and a re-flash that replaces the repo directory wholesale takes it with it.

**Pruning was disabled (OTV3 FEED.3) specifically so that depth accumulates, and
DXFeed history is same-evening only.** Verify per box **BEFORE** the flash, not
after — the 2026-08-03 loss was 38-byte files nobody noticed for days.

**QQQ is out of scope** — it runs SMC exploration and must not be repointed with
the rest.
