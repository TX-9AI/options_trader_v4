# docs/PORT_STATE.md — v4.0 — where the port actually stands

**2026-08-19, after r3.**

---

## THE REPO DOES NOT IMPORT CLEAN. THAT IS EXPECTED.

**85 files ported. 79 parse. Zero pre-4.0 headers. 86 doctrine blocks.**
**Three major modules fail to import**, and the reason is the work itself:

```
main.py                 ModuleNotFoundError: analysis.volatility_engine
strategy/orb_strategy   ModuleNotFoundError: analysis.regime_classifier
shadow/observer         ModuleNotFoundError: analysis.volatility_engine
```

⚠️ **THIS IS NOT A PACKAGING ERROR.** `regime_confluence`, `conviction_integrator`,
`regime_classifier`, `regime_axes`, `trend_engine`, `volatility_engine` and
`regime_labels` were dropped **deliberately** — their outputs were measured
anti-predictive on side (44.9% direction accuracy, CI [41.3%, 48.6%]).

**53 references across 12 files still reach for them:**

| file | refs |
|---|---|
| `main.py` | 17 |
| `strategy/continuation_strategy.py` | 7 |
| `config.py` | 7 |
| `shadow/observer.py` | 6 |
| `analysis/trade_readiness.py` | 6 |
| `analysis/signal_journal.py` | 4 |
| `strategy/{sweep_reversal,orb,iron_condor,butterfly}` | 2 each |
| `risk/setup_scorer.py` | 2 |
| `data/market_data.py` | 2 |

---

## ⚠️ WHY THIS IS NOT FIXED BY STUBBING

The obvious move — a stub module that returns neutral scores — would make every
import succeed **today** and leave the dependency intact. The next engineer
would find a working `analysis/volatility_engine.py` and reasonably assume the
regime layer is part of the design.

**The regime dependency is not a gate to delete.** It is woven through imports,
type hints, context assembly and journal payloads. Cutting it is a code change
per file, made deliberately, with the question asked each time: *does this
consumer need a regime, or does it need something the regime happened to
carry?*

⚠️ AND SOME OF IT IS LEGITIMATE. `signal_journal` stamps the label onto events —
that is DESCRIPTIVE and OTV4 keeps labels as description. `market_data` may only
need a type. **Blanket removal would be as wrong as blanket stubbing.**

---

## THE ORDER

**Phase 0.3** — cut the 53 references, file by file. A file is done when it
imports with no regime engine present **and** its tests pass.
**Phase 0.4** — rebuild `check_versions.sh` against what actually exists. The
inherited one carries 258 checks, many pointing at dropped modules; **a canary
that reddens on day one teaches the operator to ignore a red run** (CV.1).
**Phase 1** — mine the entry conditions.

⚠️ **NOTHING TRADES UNTIL PHASE 2.** Every strategy is a shell with its trigger
removed. Exits and collection are the proven parts and can run first.

---

## UPDATE — 2026-08-19, after the file-map work

**`volatility_engine` and `trend_engine` were RESTORED.** They were dropped on
LOCATION AND NAME — both live in `analysis/` with "engine" in the title — rather
than on what they compute. Neither is a regime engine:
· `volatility_engine` → ATR, Bollinger bands, **VWAP**, price-vs-band, compression
· `trend_engine` → **ADX**, the EMA stack, momentum

**The operator's successor list names ADX and VWAP explicitly.** Both were
sitting in modules I had cut. What actually failed is narrower:
`regime_confluence`, `conviction_integrator`, `regime_axes`, `regime_classifier`.

⚠️ **`trend_engine` still needs splitting, and that is Phase 0.3 work.** Its ADX
and EMAs are primitives v4 wants; its `direction` vote is the quantity measured
at **34.2% accuracy on puts**. Same module, opposite verdicts — the vote stays
DESCRIPTIVE and must not gate an entry.

**`regime_classifier` is the remaining blocker**, and the shape of the cut is now
clear: **eight of its nine importers want only `RegimeState` and `Regime` — the
dataclass and the enum, not the classifier.** `RegimeState` carries ADX, ATR,
BB width and trend direction as pass-throughs that v4 wants. `primary_regime`
and `conviction` are the parts measured dead. **Keep the types, drop the
scoring** — a far smaller change than deleting the module, and the file map is
what showed it (fan-in 12, third highest in the codebase).

**Harness relocation:** `rejection_ledger.py` and `eod_compare.py` moved to
`tests/` — control-only per WA §34.

### ⬜ BACKLOGGED — genuinely unwired in v3 as well as v4

| module | why it is not wired now |
|---|---|
| `execution/fill_model.py` | `would_fill` / `walk_ladder`. Nothing calls it — **find where paper fills actually happen before wiring**, or the wiring invents a second lineage. |
| `analysis/pitchfork_lifecycle.py` | 502 lines of `ForkTracker`, never wired in either repo. **Wiring it means deciding whether fork state is an entry input** — a Phase 1 question, not a plumbing one. |

⚠️ **DO NOT WIRE THESE TO SATISFY A CHECKER.** Three of the five modules first
reported as orphans were live code the checker could not see. Inventing a
consumer to clear a report is how a codebase grows call sites nobody wanted.
