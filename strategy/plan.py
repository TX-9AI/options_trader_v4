"""
strategy/plan.py  v1.2
v1.2  2026-08-27  r160: DISPATCH_ALIAS — SweepForLeg2 -> SweepCreditSpread; the
      CondorLeg2 alias retires with the deleted level-selection.
v1.1  2026-08-26  r147: DISPATCH_ALIAS — the second-leg window now has one
      caller (CondorLeg2nd -> the condor's leg-2 plan, name `CondorLeg2`);
      the three retired second-leg aliases are removed.
v1.0  2026-08-26  r146 — THE PLAN, REBUILT AS THE OPERATOR SPECIFIED IT.
      Replaces the seven parallel strategy re-implementations that lived in
      `derived/plans.py` r126-r145 (1,200 lines, zero calls into strategy/).
      The recording layer from that file is carried over intact; the
      decision logic is not, because the STRATEGY is the decision.

════════════════════════════════════════════════════════════════════════════
WHAT A PLAN IS — operator, 2026-08-26, verbatim
════════════════════════════════════════════════════════════════════════════
*"The strategy is the spec, the specification. The plan is how it executes
according to the spec."* And: *"I don't need two strategies for every
strategy. I need a strategy, which is the specification, and the plan, that
plans on how to execute it and is verbose about every decision it's making
on each tick."*

And the purpose, in his words: the plan says *"if X happens on the next tick,
we are choosing strikes and calculating r-values (risk:reward) and gating on
1:1, but under relaxed entry rules the gate would still record the value but
not veto"* — and it *"deconflicts competing valid strategies by invalidating
levels or strikes on geometry or economics."* *"The spec is how the setup
functions, but the plan exists to account for other emergent factors that
are antagonistic to the strategies' execution."*

    STRATEGY  = the spec. Detects the setup, fixes the trigger and the
                invalidation, names the level, selects the contracts,
                EXECUTES. It is the only decision path.
    PLAN      = the informer the strategy consults. Prices the what-if
                (credit/debit, risk, R), runs the antagonistic checks
                (geometry against the session map, the R hurdle, the
                clock), RECORDS every check every tick, and hands back a
                verdict the strategy honours.

⚠️ THE PLAN NEVER DETECTS A SETUP AND NEVER SELECTS A STRIKE. If it did, it
would be a second implementation of the strategy — the thing that was
delivered by mistake and had to be torn out. The plan is told what the
strategy found and prices THAT.

⚠️ THE PLAN'S VERDICT IS CONSULTED, NOT DECORATIVE. Under STRICT criteria a
plan that cannot clear the R hurdle REFUSES, and the strategy returns None.
Under RELAXED the R value is recorded, the verdict reads MUTED, and the
strategy proceeds — `strategy/criteria.py` owns that switch and this file
only calls it. The old engine could not affect a trade by design and so
measured nothing that mattered.

════════════════════════════════════════════════════════════════════════════
THE SHAPE OF A STRATEGY'S TICK, and every strategy is written this way
════════════════════════════════════════════════════════════════════════════
    t = self.planner.tick(price_now, direction=...)
    if <spec gate fails>:            return t.refuse("gate_name", "why")
    if <input missing>:              return t.starved("chain")
    ok = t.level(level_price, role, name, orb_high, orb_low)   # geometry
    if not ok:                        return t.refuse("geometry", t.last_why)
    t.credit_spread(short_k, long_k, credit, invalidation=...)  # the what-if
    ok, why = t.executable()          # the R hurdle, strict/relaxed aware
    if not ok:                        return t.refuse("r_hurdle", why)
    return t.take(signal)

Every terminal — refuse / starved / take / hold — writes the row for this
strategy on this tick, feeds `analysis/gate_report` (edge-triggered log), and
returns what the strategy should return. So `return t.refuse(...)` IS the
refusal, and a strategy cannot refuse without saying why.

════════════════════════════════════════════════════════════════════════════
THE RECORD — carried over from r126b, the split is the whole design
════════════════════════════════════════════════════════════════════════════
  `plan_tick`   THE SPINE. One row per strategy per tick: verdict, reason,
                trigger, invalidation, spot, distance to trigger, R.
                Shared columns, because comparing R ACROSS strategies at one
                instant is the point.
  `plan_check`  LONG FORMAT. One row per variable per strategy per tick, with
                its own PASS/FAIL, so an elimination is a queryable row.
                A check that could not be measured is written NULL / n/a —
                NEVER 0.0/PASS (the VW.1 lesson; pinned by check_plan_wiring).

VERDICTS: TAKE · DECLINE · NO PLAN (input starved) · NOT ASKED (the
dispatch never called this strategy this tick — recorded by the board with
the dispatcher's reason) · HOLD / ROLL / CLOSE (management).
A TAKE under a muted R hurdle is still a TAKE — it was taken — and carries
the `r_muted` check PASS and a reason beginning "R hurdle MUTED (relaxed)",
so the relaxed population is separable by query, never by guess.

⚠️ ONE ROW PER STRATEGY PER TICK, ALWAYS. The board (`derived/plans.py`)
closes each tick: any registered strategy that wrote nothing gets a NOT ASKED
row carrying the reason main.py gave, or, if the strategy WAS asked and
still wrote nothing, a row saying so — that row is the canary for an
unwired `return None`.

⚠️ WRITES NEVER RAISE. A bookkeeping failure cannot change a verdict; the
verdict is computed first and the write is wrapped.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass       # r158 — the Permission carrier
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ── WA §36 GATE CATEGORIES ──────────────────────────────────────────────
# This file OWNS NO GATE CONSTANT. Every threshold a plan applies belongs to
# the strategy that calls it (its own GATES dict) or to strategy/criteria.py
# (R_FLOOR, FOUNDATIONAL). An empty declaration is the honest one, and
# tests/check_gates.py will refuse any relaxed.widen()/window() call here.
GATES = {}

# ── the tick clock, shared by every plan in the process ─────────────────
# One number per tick, set by the board at the assembly point, so every
# strategy's row for a tick carries the SAME ts and joins across strategies
# are exact rather than "within a second".
_TICK: Dict[str, Any] = {"n": 0, "ts": 0.0}

# strategy name -> Plan, so the board can close a tick for everyone
REGISTRY: Dict[str, "Plan"] = {}

# main.py's `_safe_strategy` labels -> the strategy name the plan writes under
DISPATCH_ALIAS = {
    "ORB": "ORBStrategy",
    "CondorPlan": "IronCondorStrategy",
    "CondorLeg": "IronCondorStrategy",
    "DailyForkPlan": "DailyForkCreditSpread",
    "DailyForkLeg": "DailyForkCreditSpread",
    # the second-leg window (main_loop, position open) — r160: the sweep is
    # asked under the condor's authorization and writes under its own name
    "SweepForLeg2": "SweepCreditSpread",
}


# ⚠️ LAST DORMANT (strategy, gate, reason) PER STRATEGY. Module-level because
# a strategy object is rebuilt per tick in some paths; keyed by strategy name so
# a genuine CHANGE of reason always writes.
_DORMANT: dict = {}


def clear_dormant(strategy: str = "") -> None:
    """Forget the dormant state so the next tick writes again. Called when a
    window OPENS, so the transition into tradeable is always recorded."""
    if strategy:
        _DORMANT.pop(strategy, None)
    else:
        _DORMANT.clear()


@dataclass
class Permission:
    """What an informing plan hands to an executing strategy. NOT a trade.

    ⚠️ NO CONTRACTS, NO STRIKES, NO PREMIUM. A side, a level, its provenance
    and the reason. The strategy asked to act on it does its own construction
    under its own rules — which is the whole point of the split.
    """
    side: str = ""
    level: float = 0.0
    source: str = ""
    plan_id: Any = None
    why: str = ""


def begin_tick(ts: Optional[float] = None) -> int:
    """Advance the tick clock. Called ONCE per tick by the board."""
    _TICK["n"] += 1
    _TICK["ts"] = float(ts or time.time())
    return _TICK["n"]


def tick_now() -> Tuple[int, float]:
    return _TICK["n"], _TICK["ts"]


def _n(v, spec: str = ".2f") -> str:
    """Format a value that may be None. None renders as 'n/a', never raises.

    🔴 THE 2026-08-26 CRASH, kept as doctrine: every `why` string formatted
    `r`, `credit` and the strikes with `{x:.2f}`. Under RELAXED entries
    `r_verdict(None)` returns MUTED — NOT FAIL — so execution fell into the
    f-string with r=None and raised on all 15 boxes every tick for a session.
    A value that can be absent must be absent-safe EVERYWHERE it is read.
    """
    if v is None:
        return "n/a"
    try:
        return format(v, spec)
    except Exception:                                          # noqa: BLE001
        return str(v)


_BOUND_STORE = {"store": None}


def bind_store(store) -> None:
    """The board (derived/plans.py) binds the box's derived store here at
    init, so every strategy's plan and the board write ONE store. Tests bind
    an in-memory store the same way."""
    _BOUND_STORE["store"] = store
    for p in REGISTRY.values():
        p._store = store


def _store():
    if _BOUND_STORE["store"] is not None:
        return _BOUND_STORE["store"]
    try:
        from data.derived_store import get_derived_store
        return get_derived_store()
    except Exception:                                          # noqa: BLE001
        return None


def _symbol() -> str:
    try:
        from config import INSTRUMENT
        return str(INSTRUMENT)
    except Exception:                                          # noqa: BLE001
        return ""


_TABLES_MADE = set()


def ensure_tables(store) -> bool:
    """CREATE IF NOT EXISTS, at first use — an empty table is a measurement,
    a missing table is a mystery (r133)."""
    if store is None:
        return False
    key = id(store)
    if key in _TABLES_MADE:
        return True
    try:
        store.conn.execute("""
            CREATE TABLE IF NOT EXISTS plan_tick (
                ts_epoch     REAL NOT NULL,
                symbol       TEXT NOT NULL,
                strategy     TEXT NOT NULL,
                verdict      TEXT NOT NULL,      -- TAKE / DECLINE / MUTED / NO PLAN / NOT ASKED / HOLD / ROLL / CLOSE
                reason       TEXT,
                trigger_price   REAL,            -- FROZEN by the strategy
                invalidation    REAL,            -- FROZEN by the strategy
                underlying      REAL,            -- LIVE
                dist_to_trigger REAL,            -- LIVE
                r_now           REAL,            -- LIVE, comparable ACROSS plans
                direction    TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (ts_epoch, symbol, strategy, direction)
            );""")
        store.conn.execute("""
            CREATE TABLE IF NOT EXISTS plan_check (
                ts_epoch  REAL NOT NULL,
                symbol    TEXT NOT NULL,
                strategy  TEXT NOT NULL,
                check_name TEXT NOT NULL,
                value     REAL,
                verdict   TEXT,                  -- PASS / FAIL / n/a
                direction TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (ts_epoch, symbol, strategy, direction, check_name)
            );""")
        store.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_plan_tick "
            "ON plan_tick(symbol, strategy, ts_epoch)")
        store.conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_plan_check "
            "ON plan_check(symbol, strategy, check_name, ts_epoch)")
        store.commit()
        _TABLES_MADE.add(key)
        return True
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("plan tables could not be created: %s", exc)
        return False


def write_row(store, symbol: str, ts: float, strategy: str, verdict: str,
              reason: str, direction: str = "", trigger=None,
              invalidation=None, underlying=None, r=None,
              checks: Optional[Dict[str, Tuple[Any, Optional[bool]]]] = None
              ) -> bool:
    """One spine row plus its check rows. Never raises; returns False on a
    failed spine write (and WARNS — a lost row is data lost, r133)."""
    if store is None or not ensure_tables(store):
        return False
    try:
        dist = None
        if trigger is not None and underlying is not None:
            try:
                dist = float(underlying) - float(trigger)
            except (TypeError, ValueError):
                dist = None
        store.conn.execute(
            "INSERT OR REPLACE INTO plan_tick (ts_epoch, symbol, strategy,"
            " verdict, reason, trigger_price, invalidation, underlying,"
            " dist_to_trigger, r_now, direction) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (ts, symbol, strategy, verdict, reason, trigger, invalidation,
             underlying, dist, r, direction or ""))
    except Exception as exc:                                    # noqa: BLE001
        logger.warning("plan_tick write FAILED for %s: %s: %s",
                       strategy, type(exc).__name__, exc)
        return False
    for name, (val, ok) in (checks or {}).items():
        # ⚠️ ABSENT, NOT ZERO. ok=None means unmeasured -> NULL / n/a.
        v = None
        if val is not None:
            try:
                v = float(val)
            except (TypeError, ValueError):
                v = None
        verdict_c = "n/a" if ok is None else ("PASS" if ok else "FAIL")
        try:
            store.conn.execute(
                "INSERT OR REPLACE INTO plan_check (ts_epoch, symbol,"
                " strategy, check_name, value, verdict, direction)"
                " VALUES (?,?,?,?,?,?,?)",
                (ts, symbol, strategy, name, v, verdict_c, direction or ""))
        except Exception as exc:                                # noqa: BLE001
            logger.debug("plan_check write failed %s/%s: %s", strategy, name, exc)
    try:
        store.commit()
    except Exception:                                           # noqa: BLE001
        pass
    return True


class PlanTick:
    """One strategy's narration for one tick. Built by `Plan.tick()`."""

    def __init__(self, plan: "Plan", spot: Optional[float], direction: str):
        self.plan = plan
        self.strategy = plan.strategy
        self.direction = direction or ""
        self.spot = spot
        self.n, self.ts = tick_now()
        self.checks: Dict[str, Tuple[Any, Optional[bool]]] = {}
        self.notes: list = []
        self.trigger: Optional[float] = None
        self.invalidation: Optional[float] = None
        self.r: Optional[float] = None
        self.credit: Optional[float] = None
        self.debit: Optional[float] = None
        self.risk: Optional[float] = None
        self.reward: Optional[float] = None
        self.short_strike: Optional[float] = None
        self.long_strike: Optional[float] = None
        self.last_why: str = ""
        self.closed = False
        self.verdict: str = ""

    # ── narration ──────────────────────────────────────────────────────
    def check(self, name: str, value=None, ok: Optional[bool] = None,
              note: str = "") -> "PlanTick":
        """Record one measured variable. ok=None means UNMEASURED (NULL/n/a)."""
        self.checks[name] = (value, ok)
        if note:
            self.notes.append(note)
        return self

    def note(self, text: str) -> "PlanTick":
        self.notes.append(text)
        return self

    def anchor(self, trigger=None, invalidation=None) -> "PlanTick":
        """The structural prices the STRATEGY fixed. Frozen — the plan never
        moves them. Recorded so `dist_to_trigger` is answerable."""
        if trigger is not None:
            self.trigger = float(trigger)
        if invalidation is not None:
            self.invalidation = float(invalidation)
        return self

    # ── geometry: the session-map deconfliction ────────────────────────
    def level(self, price, role_or_kind: str, name: str,
              orb_high, orb_low) -> Optional[bool]:
        """Is this level usable for the side its SOURCE says? Records the
        check. Returns True / False / None (unmeasured — no opening range).

        ⚠️ None IS NOT A PASS. The caller decides what an unmeasured map
        means for its trade; the default in every credit strategy is to
        proceed and say so, because refusing every trade before 09:35 on a
        missing marker would be a clock gate wearing geometry's name.
        """
        from analysis.session_map import classify, role_of, CEILING, FLOOR
        role = role_or_kind if role_or_kind in (CEILING, FLOOR) \
            else role_of(role_or_kind)
        ok, why = classify(price, role or "", orb_high, orb_low, name)
        self.last_why = why
        self.check("geometry", price, ok, why)
        return ok

    # ── economics: the what-if, priced off what the strategy chose ─────
    def credit_spread(self, short_strike, long_strike, credit,
                      invalidation=None, trigger=None) -> "PlanTick":
        """A credit vertical the strategy has already selected.
        R = credit / (width - credit). Real width — never an assumed $5."""
        try:
            self.short_strike = float(short_strike)
            self.long_strike = float(long_strike)
            width = abs(self.long_strike - self.short_strike)
            self.credit = float(credit) if credit is not None else None
        except (TypeError, ValueError):
            width, self.credit = 0.0, None
        self.anchor(trigger, invalidation)
        if self.credit is not None and width > 0:
            self.risk = round(width - self.credit, 4)
            self.reward = round(self.credit, 4)
            self.r = round(self.credit / self.risk, 4) if self.risk > 0 else None
        self.check("credit", self.credit, None if self.credit is None else self.credit > 0)
        self.check("width", width or None, None if not width else True)
        self.check("risk", self.risk, None if self.risk is None else self.risk > 0)
        self.check("r", self.r, None)      # verdict set by executable()
        return self

    def debit_directional(self, premium, delta, gamma, stop_distance,
                          target_distance=None, invalidation=None,
                          trigger=None) -> "PlanTick":
        """A long option. Reward/risk in premium terms from the greeks over
        the structural distances the strategy fixed:
            gain = δ·d_t + ½γ·d_t²      loss = δ·d_s − ½γ·d_s²   (gamma cushions)
        Target defaults to the stop distance MIRRORED — the structure sets
        both ends; no fitted multiple.
        """
        try:
            prem = float(premium)
            d = abs(float(delta or 0.0))
            g = float(gamma or 0.0)
            ds = abs(float(stop_distance))
            dt = abs(float(target_distance)) if target_distance is not None else ds
        except (TypeError, ValueError):
            prem, d, g, ds, dt = 0.0, 0.0, 0.0, 0.0, 0.0
        self.anchor(trigger, invalidation)
        self.debit = prem if prem > 0 else None
        if prem > 0 and d > 0 and ds > 0:
            gain = d * dt + 0.5 * g * dt * dt
            loss = max(0.01, d * ds - 0.5 * g * ds * ds)
            self.reward, self.risk = round(gain, 4), round(loss, 4)
            self.r = round(gain / loss, 4)
        self.check("debit", self.debit, None if self.debit is None else True)
        self.check("delta", d or None, None if not d else d > 0)
        self.check("stop_distance", ds or None, None if not ds else ds > 0)
        self.check("target_distance", dt or None, None if not dt else dt > 0)
        self.check("r", self.r, None)
        return self

    def butterfly(self, debit, width, invalidation=None, trigger=None) -> "PlanTick":
        """A debit fly: max profit = width - debit. R = (width - debit)/debit."""
        try:
            dbt, w = float(debit), float(width)
        except (TypeError, ValueError):
            dbt, w = 0.0, 0.0
        self.anchor(trigger, invalidation)
        self.debit = dbt if dbt > 0 else None
        if dbt > 0 and w > dbt:
            self.risk, self.reward = round(dbt, 4), round(w - dbt, 4)
            self.r = round((w - dbt) / dbt, 4)
        self.check("debit", self.debit, None if self.debit is None else True)
        self.check("width", w or None, None if not w else w > 0)
        self.check("r", self.r, None)
        return self

    # ── the antagonistic verdict ───────────────────────────────────────
    def executable(self) -> Tuple[bool, str]:
        """Apply the R hurdle. STRICT: r < floor (or unmeasurable) refuses.
        RELAXED: recorded, MUTED, proceeds. `strategy/criteria.py` decides.

        ⚠️ ONLY ECONOMICS LIVE HERE. Geometry is `level()` and the strategy
        acts on its answer; the clock is the strategy's own spec. Putting
        either inside this call would let a plan re-decide a setup.
        """
        from strategy.criteria import r_verdict
        v, why = r_verdict(self.r)
        self.last_why = why
        if v == "PASS":
            self.check("r", self.r, True)
            return True, why
        if v in ("MUTED", "MUTED_NO_R"):
            # recorded, not gating — the verdict of the tick becomes MUTED
            self.check("r", self.r, None)
            self.check("r_muted", 1.0, True, why)
            self.verdict = "MUTED"
            return True, why
        self.check("r", self.r, False)
        return False, why

    # ── terminals: each one WRITES and returns what the strategy returns ─
    def refuse(self, gate: str, reason: str = "", *, verdict: str = "DECLINE"):
        """The strategy is not trading this tick, at this gate, for this
        reason. Writes the row, reports the block edge-triggered, returns
        None so `return t.refuse(...)` is the whole refusal."""
        why = reason or self.last_why or gate
        prev = self.checks.get(gate, (None, None))[0]
        self.check(gate, prev, False)
        self._close(verdict, f"{gate}: {why}")
        self.plan._report_block(gate, why)
        return None

    def dormant(self, gate: str, reason: str = ""):
        """OUT OF WINDOW — write ONE row on the transition, then go quiet.

        🔴 OPERATOR, 2026-08-27: *"I don't want the 11:30-onwards credit
        strategies even looking at the chart before their window starts."*
        ⚠️ WHAT THIS REPLACES: three credit strategies calling `refuse()` on
        every tick from 09:35, each writing a plan row that said only "it is not
        11:31 yet". On UNH that was ~900 of roughly 1,300 rows for the morning —
        a per-minute transcript of a CLOCK, which nobody needs and which buried
        the ORB sequence the operator was actually looking for.
        ⚠️ THE RECORD IS NOT LOST, IT IS DEDUPLICATED. The first tick outside
        the window writes the row; every identical tick after it is silent; the
        next CHANGE writes again. "This strategy was dormant from 09:35" is the
        same information as 900 copies of it, and it is readable.
        ⚠️ THE GATE REPORTER IS UNAFFECTED — it was already edge-triggered, so
        the dashboard's GATES panel behaves exactly as before.
        """
        why = reason or self.last_why or gate
        key = (self.plan.strategy, gate, why)
        if _DORMANT.get(self.plan.strategy) == key:
            # ⚠️ MARK THE TICK AS HANDLED WITHOUT WRITING A ROW. `close_tick`
            # writes a NOT ASKED row for any strategy whose `_last` tick number
            # is stale — and for an ASKED strategy that wrote nothing it writes
            # the far louder "a return path is not wired through its plan".
            # Silently returning here would therefore produce a WORSE row than
            # the one being suppressed. Stamping `_last` with the current tick
            # is what makes the strategy genuinely quiet.
            n, _ts = tick_now()
            self.plan._last = (n, "DORMANT", f"{gate}: {why}")
            _ASKED.pop(self.plan.strategy, None)
            return None
        _DORMANT[self.plan.strategy] = key
        self.check(gate, None, False)
        self._close("DORMANT", f"{gate}: {why}")
        self.plan._report_block(gate, why)
        return None

    def permit(self, side: str, level: float, source: str = "",
               plan_id=None, why: str = ""):
        """A PERMISSION, not a signal. The plan's terminal for an informer.

        🔴 OPERATOR, 2026-08-27: *"nothing in the plan is executable. It's an
        information layer to feed the strategy and the strategy will execute."*
        And: *"The condor doesn't construct anything. The condor plan should
        just simply define whether a vertical spread is open and active and
        what's permitted afterwards."*

        ⚠️ THIS RETURNS NO SIGNAL AND NO CONTRACTS — deliberately. `take()`
        hands back an OptionsSignal because the strategy that called it BUILT
        one. A plan that is informing another strategy has nothing to hand over
        but the fact of permission: a side, a level, and why. If this ever
        starts returning something executable, the informer has become a second
        strategy again, which is the exact thing being removed here.

        The row is written as PERMIT so the per-tick account distinguishes
        "informed the strategy" from "took a trade" — they are different events
        and collapsing them is how the duplication hid.
        """
        self._close("PERMIT", why or f"{side} permitted at {level:g}")
        return Permission(side=side, level=float(level or 0.0),
                          source=source, plan_id=plan_id, why=why)

    def starved(self, *inputs: str):
        """An input the strategy needs is absent. NO PLAN row NAMING it —
        'could not evaluate' and 'does not exist' must never look alike."""
        names = ", ".join(inputs) or "unnamed input"
        for k in inputs:
            self.check(k, None, None)
        self._close("NO PLAN", f"input(s) absent: {names} — not evaluated this tick")
        self.plan._report_block("starved", names)
        return None

    def take(self, signal):
        """The strategy is firing. Writes TAKE (or MUTED if the R hurdle was
        muted), clears the gate block, opens the ledger row that
        `link_trade()` will join a fill to. Returns the signal unchanged."""
        v = self.verdict or "TAKE"
        if v == "MUTED":
            v = "TAKE"
            if not any("MUTED" in n for n in self.notes):
                self.notes.insert(0, "R hurdle MUTED (relaxed)")
        self._close(v, "; ".join(dict.fromkeys(self.notes)) or "spec satisfied")
        self.plan._report_fired()
        self.plan._ledger_open(self, signal)
        return signal

    def already(self):
        """The plan already wrote this tick's row (DORMANT / NO PLAN / DECLINE /
        HOLD) and the strategy has nothing to add. Returns None so
        `return prep.tick.already()` reads as what it is: the strategy
        declining to act on a tick the plan has fully accounted for."""
        return None

    def hold(self, reason: str, *, verdict: str = "HOLD"):
        """Management verdicts — HOLD / ROLL / CLOSE. Returns None."""
        self._close(verdict, reason)
        return None

    def _close(self, verdict: str, reason: str) -> None:
        if self.closed:
            return
        self.closed = True
        self.verdict = verdict
        self.plan._last = (self.n, verdict, reason)
        try:
            write_row(self.plan._store_ref(), self.plan.symbol, self.ts,
                      self.strategy, verdict, reason, self.direction,
                      self.trigger, self.invalidation, self.spot, self.r,
                      self.checks)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("[plan] %s row not written: %s", self.strategy, exc)
        lvl = logging.INFO if verdict in ("TAKE", "NO PLAN", "ROLL", "CLOSE") \
            else logging.DEBUG
        logger.log(lvl, "[plan] %-22s %-8s %s%s", self.strategy, verdict,
                   f"R {_n(self.r)} · " if self.r is not None else "", reason)


class Plan:
    """A strategy's informer. One per strategy instance; registered by name.

    `record_only=True` marks a plan whose verdict is never consulted (ORB —
    operator's ruling, *"leave orb alone"*). The strategy may still narrate
    through it; `executable()` is simply never called.
    """

    def __init__(self, strategy: str, checks: Tuple[str, ...] = (),
                 record_only: bool = False, self_ledgers: bool = False):
        self.strategy = strategy
        self.checks = tuple(checks)
        self.record_only = record_only
        # strategies that already open their own plan_ledger rows (the
        # condor, the daily fork) must not get a second one from take()
        self.self_ledgers = self_ledgers
        self.symbol = _symbol()
        self._store = _BOUND_STORE["store"]
        self._last: Tuple[int, str, str] = (0, "", "")   # (tick n, verdict, reason)
        REGISTRY[strategy] = self

    def _store_ref(self):
        if self._store is None:
            self._store = _store()
        return self._store

    def tick(self, spot=None, direction: str = "") -> PlanTick:
        """Open this tick's narration. Every strategy call starts here."""
        try:
            s = float(spot) if spot is not None else None
        except (TypeError, ValueError):
            s = None
        return PlanTick(self, s, direction)

    # ── did this plan write for the current tick? (the board asks) ─────
    def wrote_this_tick(self) -> bool:
        return self._last[0] == _TICK["n"]

    def last(self) -> Tuple[int, str, str]:
        return self._last

    # ── gate_report bridge — edge-triggered log, unchanged ─────────────
    def _report_block(self, gate: str, reason: str) -> None:
        try:
            from analysis.gate_report import get_gate_reporter
            r = get_gate_reporter(self.symbol)
            if r is not None:
                r.blocked(self.strategy, gate, reason)
        except Exception:                                       # noqa: BLE001
            pass

    def _report_fired(self) -> None:
        try:
            from analysis.gate_report import get_gate_reporter
            r = get_gate_reporter(self.symbol)
            if r is not None:
                r.cleared(self.strategy)
        except Exception:                                       # noqa: BLE001
            pass

    def _ledger_open(self, t: PlanTick, signal) -> None:
        """Open a plan_ledger row for a fired plan so `link_trade()` has a
        live row to attach the fill to. State TRIGGERED — the strategy has
        fired; the fill (or its absence) is what comes next."""
        if self.self_ledgers:
            return
        try:
            from derived.registry import plan_ledger as _pl
            led = _pl(self.symbol)
            if led is None:
                return
            ctx = {"price": t.spot}
            sp = getattr(signal, "short_put_contract", None)
            lp = getattr(signal, "long_put_contract", None)
            led.open_plan(
                self.strategy, "TRIGGERED", ctx,
                direction=t.direction or getattr(signal, "option_side", ""),
                short_strike=t.short_strike,
                long_strike=t.long_strike,
                short_put_strike=getattr(sp, "strike", None) if sp else None,
                long_put_strike=getattr(lp, "strike", None) if lp else None,
                trigger_price=t.trigger,
                underlying_at_decision=t.spot)
        except Exception as exc:                                # noqa: BLE001
            logger.debug("[plan] ledger open skipped for %s: %s", self.strategy, exc)


# ── the board's half: rows for strategies that never spoke this tick ────
_SKIPPED: Dict[str, str] = {}      # strategy -> reason main.py gave
_ASKED: Dict[str, Any] = {}        # strategy -> result summary


def skipped(strategy: str, reason: str) -> None:
    """main.py: this strategy is NOT being asked this tick, and here is why.
    Recorded at close_tick as NOT ASKED. Never raises."""
    try:
        _SKIPPED[DISPATCH_ALIAS.get(strategy, strategy)] = reason
    except Exception:                                           # noqa: BLE001
        pass


def skipped_all(reason: str) -> None:
    """main.py: NO strategy is being asked this tick (halted, outside the
    session, no chain, a position is open). Never raises."""
    try:
        for name in list(REGISTRY):
            _SKIPPED.setdefault(name, reason)
    except Exception:                                           # noqa: BLE001
        pass


def asked(label: str, result) -> None:
    """main.py's `_safe_strategy`: this strategy WAS called and returned
    `result`. Used at close_tick to catch a strategy that was asked and wrote
    no row — an unwired `return None` or a raise."""
    try:
        _ASKED[DISPATCH_ALIAS.get(label, label)] = (
            "signal" if result is not None else "None")
    except Exception:                                           # noqa: BLE001
        pass


def close_tick(store=None, symbol: str = "") -> int:
    """Write NOT ASKED rows for the tick just finished. Called by the board
    at the START of the next tick (so every dispatch return path is
    covered). Returns rows written."""
    n, ts = tick_now()
    if n == 0:
        return 0
    store = store or _store()
    symbol = symbol or _symbol()
    written = 0
    try:
        for name, plan in list(REGISTRY.items()):
            if plan.wrote_this_tick():
                continue
            if name in _ASKED:
                why = (f"ASKED and returned {_ASKED[name]} but wrote no plan "
                       f"row — a return path in this strategy is not wired "
                       f"through its plan (or it raised)")
                verdict = "NO PLAN"
                logger.warning("[plan] %s %s", name, why)
            else:
                why = _SKIPPED.get(name, "not asked this tick — dispatch gave no reason")
                verdict = "NOT ASKED"
            if write_row(store, symbol, ts, name, verdict, why):
                written += 1
            plan._last = (n, verdict, why)
    finally:
        _SKIPPED.clear()
        _ASKED.clear()
    return written


def board_line() -> str:
    """One line: every registered strategy's last verdict, for the log."""
    bits = []
    for name, plan in sorted(REGISTRY.items()):
        _, v, why = plan.last()
        short = (why or "")[:48].replace("\n", " ")
        bits.append(f"{name}={v or '-'}" + (f"({short})" if short else ""))
    return " · ".join(bits)
