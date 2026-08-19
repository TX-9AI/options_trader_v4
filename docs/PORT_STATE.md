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
