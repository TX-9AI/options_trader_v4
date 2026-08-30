# options_trader_v4

**`README.md` v1.1 · 2026-08-29 — what this repo is, what it refuses to be, and where to read next.**

**Vertigo Capital · a structure-first options trading fleet.**
**Opened 2026-08-19. Successor to `options_trader_v3`.**

---

## WHAT THIS IS

A fleet of independent per-symbol trading bots that fire on **what price is
doing** — swing sequence, channel position, whether the last break held,
distance to prior-session extremes, the impulse character of the entry bar —
shaped by derived cues (delta, gamma, VWAP, pitchfork, ADX, volume, volatility,
GEX) and by the options chain.

**Each box trades standalone.** Control (`1-REPORTER`) orchestrates, verifies and
reports, but **no box requires control to be reachable in order to trade.** That
independence is a feature, not an accident of the architecture.

**Fleet: 15 boxes. Collection and trading are the SAME SET.** The panel is
`selector.PANEL` in `day_trader_pro` — named there and nowhere else, so this
file does not carry a symbol list that can go stale.

🔴 **THIS LINE READ "15 traders, 29 collectors, collection is fleet-wide"
UNTIL 2026-08-29, AND IT HAD BEEN FALSE SINCE 2026-08-20**, when the pare
TERMINATED the other 14 instances rather than stopping them. r74 corrected the
same sentence in `docs/ROADMAP.md` (S.4) and `WORKING_AGREEMENT.md` (§30) on
2026-08-22 and missed this copy — three documents carrying one fact, and the
one on the front page was the one that rotted.

The principle it carried is unchanged and still right: **a box that stops
collecting is a box whose pitchfork and ADX warm-up depth quietly dies.**
DXFeed history is same-evening only, so that depth cannot be recovered
afterwards; pruning stays disabled specifically so it accumulates.

⚠️ **AND THE CONSEQUENCE THAT OUTLIVES THE CORRECTION:** fleet-wide
open-interest accumulation — which the GEX butterfly's unpark waits on — now
runs across 15 symbols instead of 29. Half the breadth, so a longer clock. Any
unpark date derived from the 29-symbol assumption is wrong.

---

## WHAT THIS IS NOT, AND WHY

OTV4 exists because OTV3's central premise was **measured false**, not because it
was abandoned. The evidence is in `docs/INHERITED_FINDINGS.md` and it is the
reason for every structural choice here.

**There is no regime-conviction gate.** OTV3's classifier picked the correct
side on **44.9% of 715 directional trades** — 95% CI [41.3%, 48.6%], **entirely
below a coin flip**. Puts were **34.2%**. The strategy most dependent on it lost
**$5,872** across 660 trades.

**There is no setup scorer, and there is no longer one to delete.** OTV3's was
built before it was earned and inverted: over 619 trades **A-grade lost $8,244**
at 1.5× size while **B-grade made +$1,893** — it SELECTED LOSERS. It was ported
into v4 anyway and removed at **r152**: `risk/setup_scorer.py` is gone and
nothing imports it, pinned by `tests/check_conviction_removed.py` (S1—S4).

🔴 **WHY IT COULD NEVER HAVE WORKED, WHICH IS THE PART WORTH KEEPING:** about
90% of the grade was ONE COLUMN PRINTED TWICE — two of its four dimensions
had identical medians AND identical spreads over 619 trades — and the other
two measured 1.000 on every one of those trades. **The sum never measured
anything.** A scorer here has to be earned from evidence that a grade predicts
dollars, not assembled from dimensions that look reasonable.

**Regime labels inform; they never authorise.** The vocabulary survives —
in-channel, breakout, compression, ranging, breakout-volatile, trending — rebuilt
**from structure first**. Any setup may read one. **No setup may require one.**

---

## SUCCESS

**Dollars. P&L and return on risk.** A demonstrable edge, evidenced by **not
losing money over a measurable period** — long enough that variance cannot
explain it.

⚠️ **A HIGH WIN RATE IS NOT THE TARGET.** There will be bad trades and bad days;
the requirement is that they are overshadowed. The edge lives in **stop
discipline and management of winners**, and OTV3 proved that twice:
`orb_trail_stop` **95% win / 107 trades / +$37,848**, `theta_bleed` **100% /
107** — while grading entries harder made money *worse*.

See `docs/VISION.md`.

---

## LAYOUT

```
analysis/       structure, levels, pitchfork, ORB geometry, chain-derived inputs
data/           feed, candle store, options chain, GEX, macro, derived store
derived/        the derived layer - character, levels, plans, notes, counterfactual
strategy/       the trade constructions, and the PLAN each one declares
execution/      entry dispatch, exits, ladders, fills, reconciliation
risk/           loss caps, session gating, sizing
database/       trade logger and schema
warehouse/      S3 push, retention purge, box-side self close
notifications/  Telegram - an emergency-services channel, nothing routine
shadow/         the in-session observer (disposition open: docs/BACKLOG.md ASK.2)
utils/          time, math, latches
deploy/         systemd units and timers
tools/          on-box operator utilities (manifold health, status probes)
tests/          ⚠️ EVERY test and harness lives here. CONTROL ONLY - see §34.
docs/           working agreement, roadmap, backlog, genesis, the maps
```

⚠️ **THIS TABLE IS ORIENTATION, NOT AUTHORITY.** `docs/FILE_MAP.md` is
generated from the real import graph and the land gate fails on drift; this one
is written by hand and was missing five directories until 2026-08-29. When the
two disagree, the generated map is right.

---

## DOCTRINE

`docs/WORKING_AGREEMENT.md` carried over from OTV3 and **has been added to ever
since** — §26 through §37 are v4-era, written between 2026-08-19 and 08-24. It
was earned: most of its sections exist because something broke in a way that
cost a session. Read it before writing code.

Then `docs/BACKLOG.md` for what is open, `docs/GENESIS.md` for why each
revision exists, and `docs/PLAN_SPEC.md` + `docs/TRADES.md` for what the
strategies actually do.

**The measurement tooling carries over too, and that is deliberate.** The probes
in `tests/` are what proved OTV3's model broken. **They will judge this one
identically.**

---

## CHANGELOG

v1.1  2026-08-29  r185 — backlog DOC.4. THE FLEET COUNT WAS FALSE FOR NINE
      DAYS ON THE PAGE MOST LIKELY TO BE READ FIRST. Corrected, with the
      reason it survived r74's sweep recorded in place. Four further staleness
      fixes found reading the file end to end, which §5 requires of any edit:
      the setup scorer is DELETED (r152), not merely absent; the LAYOUT table
      was missing five of fifteen directories and now says plainly that
      `docs/FILE_MAP.md` outranks it; WORKING_AGREEMENT no longer "carries
      over verbatim" (§26-§37 are v4-era); and a reading order was added.
      A version line was added at the top so this file is visible to
      `check_land_discipline.py` at all — it carried no version in either
      place, which is why nothing ever flagged the drift.

v1.0  2026-08-19  Written at the v3 — v4 split.
