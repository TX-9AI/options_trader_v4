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

---

## UPDATE — 2026-08-19, Phase 0.3 part 1: the repo imports

**`analysis/market_state.py` replaces `analysis/regime_classifier.py`.**
**68 of 69 runtime modules import.** The one failure is `debug_status.py`,
which shells out to `sudo` at import time — a diagnostic script, not a runtime
path.

**The cut was KEEP THE TYPES, DROP THE SCORING**, and the file map is what
showed it was possible: `regime_classifier` had **fan-in 12**, third highest in
the codebase, but **eight of its nine importers wanted only `RegimeState` and
`Regime`** — the dataclass and the enum. Two called the classifier.

**What `MarketState` carries** is what `RegimeState` always really was: a
CARRIER for structural facts computed elsewhere — adx, atr_normalized,
bb_width_pct, trend_direction, structure_sequence, sweep_recent, flat_angle_deg,
sweep_age_bars, vix_regime, timeframe_alignment. Those pass through untouched.

**`Regime` — the six-label vocabulary — survives deliberately**, and the names
are unchanged so historical journals, trade rows and replay logs stay readable
against v4 code. **The names survive; the way they were COMPUTED does not.**

⚠️ **`conviction` IS STILL PRESENT AND IS ON ITS WAY OUT. 49 live reads across 8
files.** Removing the field outright would be one large blind edit with nothing
importable until every site was fixed — and nothing testable until all of it
compiled. It stays defaulted and unread by `market_state` itself so the call
sites can be removed **file by file with tests passing at each step**.
**It must not be reintroduced as a gate.**

⚠️ `RegimeState` remains as a temporary alias for `MarketState` for the same
reason. Remove when the last importer reads `MarketState` directly.

### STILL TO DO IN PHASE 0.3
- Remove the 49 `conviction` reads, file by file.
- Split `trend_engine`: ADX and the EMA stack are primitives v4 wants; the
  `direction` vote measured **34.2% on puts** and must stay DESCRIPTIVE.
- `main.py` deep clean — the regime gates in the dispatch path.

---

## UPDATE — 2026-08-19, Phase 0.3 part 2: the L2 stack is out of `main.py`

**`run_regime_classification` → `assemble_market_state`.** 17,177 characters of
classification and Layer-2 override replaced by a ~60-line assembler that
**classifies nothing**: it gathers adx, atr, bb width, trend direction,
structure sequence, sweep age, vix regime and flat angle into one `MarketState`.
**Those facts were always the useful part; the label was the part that failed.**

⚠️ **`main.py` IMPORTED CLEANLY WHILE BEING RUNTIME-BROKEN.** After the
`regime_classifier` cut, line 757 imported the types from `market_state` while
line 1167 still called `get_regime_classifier()` — a function that no longer
existed anywhere. `import main` passed the entire time. **That is the `ctx`
NameError of 2026-08-18 in a different costume**, and it is why WA §21 exists:
tests must EXECUTE the path. `assemble_market_state` is now executed against a
synthetic ctx, not merely imported.

⚠️ **AND THE L2 BLOCK WAS ALREADY DEAD BEFORE IT WAS REMOVED.** The v3 import sat
in a `try/except` setting `_L2_OK`; at the split the except branch became
permanent, so `_l1_scorer` and `_l2_integ` were always `None` and every block
gated on them was unreachable code that still had to be read and reasoned about.
Four such sites are now cut: the entry stale-book guard, the `_rgm_stale`
computation, the startup book reload, and the engine-announce line.

**The five remaining mentions in `main.py` are comments explaining the removal.**
No live code.

**`primary_regime` is now honestly `UNKNOWN`** until a structure-first label
exists (Phase 4.1). An honest UNKNOWN beats a number nobody should trust.

### STILL TO DO IN PHASE 0.3
- The remaining `conviction` reads outside `main.py` — strategies, setup_scorer,
  shadow/observer.
- Split `trend_engine`: ADX and the EMA stack stay; the `direction` vote
  measured **34.2% on puts** and must remain DESCRIPTIVE.
- `tests/check_imports.py` is now a tool the land gate can call by name (§19).
