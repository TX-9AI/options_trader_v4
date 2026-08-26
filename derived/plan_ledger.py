"""
derived/plan_ledger.py  v4.0
Owns `plan_ledger`. INTENT as a first-class record.

v4.0  2026-08-25  See docs/DERIVED_STORES.md.

**A trade is what happened. A plan is what was INTENDED.** They are different
objects and they diverge in ways that matter:

  · A plan can produce NO TRADE AT ALL — the condor decides, sets strikes, and
    the leg trigger never comes. Nothing in `trades` records that a structure
    was designed and never fired. Today that intent evaporates with the
    process.
  · A plan can produce MORE THAN ONE trade — leg 1 and leg 2 are separate rows
    and nothing links them as halves of one structure except convention.
  · A plan HAS A LIFE: DECIDED -> LEG1_FILLED -> COMPLETE, or -> CANCELLED /
    EXPIRED. Same lifecycle shape as the level ledger, same argument for a
    home: recomputation cannot reconstruct a biography.

🔴 THE PROTECTION. `IronCondorStrategy._plan` lives ONLY in memory — zero
persistence in that file. A restart at LEG1_FILLED means ONE LEG IS LIVE AT THE
BROKER AND THE BOT HAS NO MEMORY THAT A SECOND WAS PLANNED. The position
exists; the intent does not. The repo already warns about orphan legs — but
that is detecting the wreckage, not preventing it.

🔴 THE BIGGER PRIZE — MINING THE PLANS THAT NEVER EXECUTED. An unfired plan
still has a KNOWABLE OUTCOME: the market went somewhere. Score it afterwards
and every unfired plan becomes a FREE BACKTEST ON LIVE DATA — no capital, no
slippage, and the strikes were chosen in real time rather than with hindsight.

⚠️ THAT MEASURES THE TRIGGER ITSELF. If unfired plans would have won at the
same rate as fired ones, the trigger is filtering noise. If they would have
done BETTER, the trigger is costing money. That is the question behind Friday
and behind every "why didn't it fire", and it is unanswerable today.

⚠️ THE LEDGER IS THE RECORD, NOT THE AUTHORITY. On reload a plan is restored as
INTENT and must be RE-QUALIFIED against current structure. A plan resumed blind
after a twenty-minute outage is trading a fork that may no longer exist. The
ledger says what we meant; the tape says whether it is still true.

⚠️ WRITES NEVER RAISE. Same rule as every derived home: a bookkeeping failure
must not be able to affect a live position.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

# ⚠️ `MISSED` IS ITS OWN STATE AND NOT A FLAVOUR OF `WIPED_BY_RESTART` (r95).
# They are different facts and they cost different things:
#   WIPED_BY_RESTART — the plan was still WAITING on its trigger when the
#       process died. Nothing was lost that the tape can prove; the setup may
#       simply not have happened.
#   MISSED           — the trigger DID fire, on the tape, while we were down.
#       This is a real setup the fleet did not take, and it is the number that
#       answers "what do mid-session deploys and crash-loops actually cost us".
# Collapsing the two would bury the second inside the first, which is exactly
# the plausible-silence class this repo keeps finding.
#
# ⚠️ RECORDED, NEVER RESUMED — operator's ruling, 2026-08-24: "An interrupted
# firing sequence should never attempt a late entry. Log it as missed. But
# normal entries that weren't filled and weren't interrupted should keep
# trying." A MISSED row is a headstone, not a queue.
#
# Terminal reasons. ⚠️ `WIPED_BY_RESTART` IS ITS OWN CATEGORY — on 2026-08-21
# four boxes held confirmed break+retest setups at 10:20-10:24 and the 10:39
# deploy erased them. Folding that into CANCELLED would hide the cost of
# deploying mid-session, which is exactly the number worth knowing.
TERMINAL = {"FIRED", "EXPIRED", "CANCELLED", "WIPED_BY_RESTART", "COMPLETE",
            "MISSED"}
LIVE = {"DECIDED", "LEG1_FILLED", "CONFIRMED", "ARMED"}


def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


class PlanLedger:
    """One row per plan. Never raises into a caller."""

    def __init__(self, store=None, symbol: str = ""):
        self._store = store
        self.symbol = symbol
        self._made = False

    def _ensure(self):
        if self._made or self._store is None:
            return
        try:
            self._store.conn.execute("""
                CREATE TABLE IF NOT EXISTS plan_ledger (
                    plan_id     TEXT NOT NULL PRIMARY KEY,
                    symbol      TEXT NOT NULL,
                    strategy    TEXT NOT NULL,
                    state       TEXT NOT NULL,
                    created_ts  REAL NOT NULL,
                    updated_ts  REAL NOT NULL,
                    closed_ts   REAL,
                    terminal_reason TEXT,
                    -- what was intended
                    direction   TEXT,
                    short_strike REAL, long_strike REAL,
                    short_put_strike REAL, long_put_strike REAL,
                    trigger_price REAL,
                    underlying_at_decision REAL,
                    expected_move REAL,
                    -- why it was intended: the derived vector at decision time
                    justification TEXT,
                    -- what happened to the tape afterwards (EOD scoring pass)
                    max_price_seen REAL, min_price_seen REAL,
                    counterfactual TEXT,
                    trade_ids   TEXT
                );""")
            self._store.conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_plan_live "
                "ON plan_ledger(symbol, state)")
            self._made = True
        except Exception as exc:                                # noqa: BLE001
            logger.debug("plan_ledger table: %s", exc)

    # ── writes ──────────────────────────────────────────────────────────
    def open_plan(self, strategy: str, state: str, ctx: dict,
                  **fields) -> Optional[str]:
        """Record a new intent. Returns plan_id, or None if unrecorded."""
        if self._store is None:
            return None
        pid = uuid.uuid4().hex[:16]
        now = time.time()
        try:
            self._ensure()
            just = {
                # ⚠️ THE JUSTIFICATION IS THE POINT OF THE STUDY. Scoring an
                # unfired plan tells you IF it would have worked; the
                # justification tells you WHY it was chosen, which is what a
                # fit actually needs.
                "price": _f(ctx.get("price")),
                "adx": _f(getattr(ctx.get("trend"), "primary_adx", None)),
                "atm_iv": _f(ctx.get("atm_iv")),
                "expected_move_iv": _f(ctx.get("expected_move_iv")),
                "variance_risk_premium": _f(ctx.get("variance_risk_premium")),
                "realised_vol_cc": _f(ctx.get("realised_vol_cc")),
                "charm": _f(ctx.get("charm")),
                "vanna": _f(ctx.get("vanna")),
                # ⚠️ ctx["gex"] is a GEXSnapshot OBJECT — _f() on it yields None,
            # which is why this column has been NULL on every row ever
            # written. The scalar is `net_gex`. See derived/surface.py r140.
            "gex": _f(getattr(ctx.get("gex"), "net_gex", None)),
                "session_fraction_remaining": _f(ctx.get("session_fraction_remaining")),
                "levels": ctx.get("levels"),
                "fork": ctx.get("fork_rails"),
            }
            self._store.conn.execute(
                "INSERT OR REPLACE INTO plan_ledger (plan_id, symbol, strategy,"
                " state, created_ts, updated_ts, direction, short_strike,"
                " long_strike, short_put_strike, long_put_strike,"
                " trigger_price, underlying_at_decision, expected_move,"
                " justification) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pid, self.symbol, strategy, state, now, now,
                 fields.get("direction"), _f(fields.get("short_strike")),
                 _f(fields.get("long_strike")), _f(fields.get("short_put_strike")),
                 _f(fields.get("long_put_strike")), _f(fields.get("trigger_price")),
                 _f(fields.get("underlying_at_decision")),
                 _f(fields.get("expected_move")),
                 json.dumps(just, default=str)))
            self._store.commit()
            logger.info("[plan] OPEN %s %s %s", pid[:8], strategy, state)
            return pid
        except Exception as exc:                                # noqa: BLE001
            logger.debug("open_plan: %s", exc)
            return None

    def transition(self, plan_id: str, state: str,
                   terminal_reason: str = "", trade_id: str = "",
                   max_price: Optional[float] = None,
                   min_price: Optional[float] = None) -> None:
        """Move a plan's state. Terminal states set closed_ts."""
        if self._store is None or not plan_id:
            return
        try:
            self._ensure()
            now = time.time()
            closed = now if state in TERMINAL else None
            row = self._store.conn.execute(
                "SELECT trade_ids FROM plan_ledger WHERE plan_id=?",
                (plan_id,)).fetchone()
            ids = json.loads(row[0]) if (row and row[0]) else []
            if trade_id and trade_id not in ids:
                ids.append(trade_id)
            self._store.conn.execute(
                "UPDATE plan_ledger SET state=?, updated_ts=?, closed_ts=?,"
                " terminal_reason=?, trade_ids=?,"
                " max_price_seen=COALESCE(?, max_price_seen),"
                " min_price_seen=COALESCE(?, min_price_seen)"
                " WHERE plan_id=?",
                (state, now, closed, terminal_reason or None,
                 json.dumps(ids), _f(max_price), _f(min_price), plan_id))
            self._store.commit()
            logger.info("[plan] %s -> %s%s", plan_id[:8], state,
                        f" ({terminal_reason})" if terminal_reason else "")
        except Exception as exc:                                # noqa: BLE001
            logger.debug("transition: %s", exc)

    # ── reads ───────────────────────────────────────────────────────────
    def live_plans(self) -> list:
        """Every plan still pending for this symbol. Survives restarts.

        🔴 THIS IS WHAT status.py READS. `orb_state.json` is written by a
        RUNNING bot, so after a restart it reflects whatever the new process
        has rebuilt — and a condor at LEG1_FILLED with a live leg at the broker
        would show as nothing at all. The ledger is on disk independent of who
        is running.
        """
        if self._store is None:
            return []
        try:
            self._ensure()
            cur = self._store.conn.execute(
                "SELECT plan_id, strategy, state, created_ts, direction,"
                " short_strike, trigger_price FROM plan_ledger"
                " WHERE symbol=? AND closed_ts IS NULL", (self.symbol,))
            return [{"plan_id": r[0], "strategy": r[1], "state": r[2],
                     "created_ts": r[3], "direction": r[4],
                     "short_strike": r[5], "trigger_price": r[6]}
                    for r in cur.fetchall()]
        except Exception:                                       # noqa: BLE001
            return []

    def mark_restart_wipe(self) -> int:
        """Called at boot: any plan left LIVE by a dead process is recorded.

        ⚠️ IT IS RECORDED, NOT RESUMED. The row keeps WIPED_BY_RESTART so the
        cost of deploying mid-session becomes a countable number — four boxes
        lost confirmed setups to the 10:39 deploy on 2026-08-21 and nothing
        wrote that down.
        ⚠️ CONDOR PLANS AT LEG1_FILLED ARE **NOT** WIPED — a leg is live at the
        broker, so the intent must survive for the reconciler to act on. Those
        are left open and re-qualified.
        """
        if self._store is None:
            return 0
        try:
            self._ensure()
            cur = self._store.conn.execute(
                "SELECT plan_id, state FROM plan_ledger"
                " WHERE symbol=? AND closed_ts IS NULL", (self.symbol,))
            n = 0
            for pid, state in cur.fetchall():
                if state == "LEG1_FILLED":
                    continue                     # real money on — keep it open
                self.transition(pid, "CANCELLED", "WIPED_BY_RESTART")
                n += 1
            if n:
                logger.warning("[plan] %d pending plan(s) lost to a restart — "
                               "recorded as WIPED_BY_RESTART", n)
            return n
        except Exception:                                       # noqa: BLE001
            return 0
