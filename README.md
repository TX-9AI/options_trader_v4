# options_trader_v4

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

**Fleet: 15 traders, 29 collectors.** ⚠️ Collection is fleet-wide; trading is
panel-only. A box that stops collecting because it is not trading is a box whose
pitchfork and ADX warm-up depth quietly dies — and DXFeed history is
same-evening only, so that depth cannot be recovered.

---

## WHAT THIS IS NOT, AND WHY

OTV4 exists because OTV3's central premise was **measured false**, not because it
was abandoned. The evidence is in `docs/INHERITED_FINDINGS.md` and it is the
reason for every structural choice here.

**There is no regime-conviction gate.** OTV3's classifier picked the correct
side on **44.9% of 715 directional trades** — 95% CI [41.3%, 48.6%], **entirely
below a coin flip**. Puts were **34.2%**. The strategy most dependent on it lost
**$5,872** across 660 trades.

**There is no setup scorer at launch.** OTV3's was built before it was earned and
inverted: **A-grade lost $8,244** at 1.5× size while **B-grade made +$1,893**.
A scorer here must be earned from a shadow observer grading entries post-mortem.

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
analysis/     structure, levels, pitchfork, ORB geometry, chain-derived inputs
data/         feed, candle store, options chain, GEX, macro
execution/    entry dispatch, exits, ladders, fills, reconciliation
strategy/     the trade constructions
risk/         loss caps, session gating, sizing
database/     trade logger and schema
warehouse/    S3 push and verification
utils/        time, math, latches
tests/        ⚠️ EVERY test and tool lives here. Nothing at repo root.
docs/         working agreement, roadmap, vision, inherited findings
```

---

## DOCTRINE

`docs/WORKING_AGREEMENT.md` carries over **verbatim** from OTV3. It was earned —
most of its sections exist because something broke in a way that cost a session.
Read it before writing code.

**The measurement tooling carries over too, and that is deliberate.** The probes
in `tests/` are what proved OTV3's model broken. **They will judge this one
identically.**
