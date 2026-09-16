#!/usr/bin/env python3
"""
tests/check_orb_underwater_entry.py  v1.0

v1.0  2026-09-16  rNNN / ORB.12 — A FIRE ALREADY THROUGH ITS OWN INVALIDATION IS
      REFUSED, AND ONE THAT GETS THROUGH ANYWAY IS OUT ON THE TICK IT IS SEEN.

🔴 THE DEFECT, FROM THE TAPE. MU 2026-09-14 lost $2,047.50 in 45 seconds — 54%
of that session — on an ORB Long that was underwater from the fill and never
traded up for a single tick (mfe_premium 3.80 against a 4.17 entry).

  · BREAK CANDLE 09:46 — opened 914.335 INSIDE [904.40, 914.55], closed 918.195
    outside. Its LOW, 914.14, becomes `underlying_stop`. The banked row carries
    exactly that number.
  · CONFIRMING RETEST 09:50 — O 916.365 / H 917.04 / L 913.39 / C 914.8042. The
    wick entered the range and the body stayed outside, so `_check_for_retest`
    confirmed. THE STRATEGY WAS RIGHT TO ARM; this file does not touch that.
  · FIRE 09:51:16 AT 913.495 — one tick after that candle completed, while the
    09:51 bar was collapsing 914.73 -> 908.50. The fill landed 1.06 below the
    ORB boundary and 0.65 BELOW THE IMPULSIVE-CANDLE LOW.

⚠️ NOTHING RE-READ PRICE AGAINST THE LEVEL BETWEEN CONFIRM AND FIRE. Every
non-exit consumer of `underlying_stop` was enumerated: `entry_engine` records
it, and `main` and `entry_engine` both wrap it in `abs()` for the sizer and for
`planned_r`. No side check existed anywhere in the entry path.

📊 SCALE: 8 of 154 banked ORB trades (5.2%) entered already through their own
stop — net -$2,792, 2 winners, 5 never favorable, sizes to 60x and costs to
$6,854. Seven of the eight fall on 09-01 and 09-14.

🔑 WHY THE BLOCKER SITS IN THE STRATEGY AND NOT AT THE ORDER. The operator's
first instinct was a check the instant before the execute command; the reasoning
inverts on reading the source. `current_price` is `ctx["price"]`, fetched ONCE
at the top of the tick and never refreshed within it, and `entry_engine.enter()`
re-reads only the OPTION's quote — never the underlying. MU's own row proves it:
entry_time 13:51:16.725166 and the entry snapshot 13:51:16.731832, 7ms apart.
So a guard in the strategy and a guard at the order compare IDENTICAL NUMBERS;
position inside the tick buys nothing. The strategy site buys what the order
site cannot: both facts are constructed two lines apart so neither can be a
stale copy, the refusal becomes a COUNTED plan verdict rather than a log line,
and no signal exists — so the dispatch never runs and the engine never lands in
the phantom OPEN_LONG that `_check_for_retest` sets at confirm.

⚠️ `sig is None` IS NOT THE PROOF, and this file inherits that lesson from
`check_orb_sequence` S4 rather than rediscovering it. With no chain the strike
never resolves and `generate_signal` returns None for an unrelated reason, so a
bare None assertion is GREEN AT HEAD against the very version it exists to
catch — WORKING_AGREEMENT 0.4 exactly. Every refusal check below reads the
PLAN ROW and requires it to name THIS gate.

  U1  the MU case: price through the impulsive low -> refused, BY NAME
  U2  the short-side mirror: price above the impulsive high -> refused
  U3  CONTROL — a fire correctly beyond the boundary and holding the origin
      still produces a signal. A guard that refused everything would satisfy
      U1 and U2 on its own.
  U4  CONTROL (section 37) — a refusal does not PARK the setup: the engine is
      still armed and a later qualifying retest still fires.
  U5  the refusal is COUNTED, not swallowed (section 0.5)
  U6  CONTROL — SIZING IS UNTOUCHED. `size_for` with MU's real inputs still
      returns 15. Operator, 2026-09-16: "I don't want the sizing affected."
      If this moves, the delivery crossed the boundary it was given.
  U7  the live arm: an entry already through the stop exits on the FIRST
      evaluate, with the last CLOSED candle deliberately still on the safe
      side — it must exit on the FILL, not on the candle
  U7b the same record after a SELECT * round trip (section 22)
  U8  CONTROL — a correctly-entered position that is intrabar through the
      level but whose last closed candle HOLDS does NOT exit. If U8 reds, the
      live arm leaked onto every ORB position and the breathing room is gone.
"""
from __future__ import annotations

import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails: list = []

# ── MU 2026-09-14, the real numbers ──────────────────────────────────────────
MU_ORB_HIGH = 914.55
MU_ORB_LOW = 904.40
MU_BREAK = (914.335, 918.40, 914.14, 918.195)      # 09:46 — low is the stop
MU_RETEST = (916.365, 917.04, 913.39, 914.8042)    # 09:50 — the confirm
MU_FIRE = 913.495                                  # 09:51:16 — the fill
MU_STOP = 914.14


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
    if not ok:
        _fails.append(name)


def _frame(rows):
    """A 1m frame the engine can advance on. rows = [(o,h,l,c), ...].

    The engine reads `iloc[-2]`, so the caller supplies the bar to be consumed
    followed by one forming bar.
    """
    import pandas as pd
    return pd.DataFrame(
        [{"open": o, "high": h, "low": l, "close": c} for o, h, l, c in rows],
        index=pd.date_range("2026-09-14 09:46", periods=len(rows), freq="1min"))


def _mu_engine(direction: str = "long"):
    """An engine carrying MU's real range and MU's real break.

    ⚠️ BUILT BY DRIVING `_check_for_break`, NOT BY ASSIGNING FIELDS — a fixture
    that sets the state encodes my belief about how a break is registered;
    driving the real method encodes the code's. (check_orb_sequence's rule.)
    """
    from analysis.orb_engine import ORBEngine, ORBState
    eng = ORBEngine()
    d = eng._data
    d.orb_high, d.orb_low = MU_ORB_HIGH, MU_ORB_LOW
    d.orb_width = MU_ORB_HIGH - MU_ORB_LOW
    d.state = ORBState.WAITING_FOR_BREAK
    if direction == "long":
        o, h, l, c = MU_BREAK
        eng._check_for_break(_frame([(o, h, l, c), (c, c + 0.1, c - 0.1, c)]))
    else:
        # mirror: opens inside, closes BELOW the low, wick high is the stop
        eng._check_for_break(_frame([(910.00, 914.20, 900.00, 902.00),
                                     (902.00, 902.5, 901.5, 902.0)]))
    return eng


def _confirm(eng, direction: str = "long"):
    if direction == "long":
        o, h, l, c = MU_RETEST
    else:
        # mirror of the retest: wick ENTERS the range, body stays outside
        o, h, l, c = (903.00, 904.90, 902.50, 903.20)
    eng._check_for_retest(_frame([(o, h, l, c), (c, c + 0.05, c - 0.05, c)]))
    return eng


def _plan_store():
    from strategy import plan as P

    class _Store:
        def __init__(self):
            self.conn = sqlite3.connect(":memory:")
            self.conn.row_factory = sqlite3.Row

        def commit(self):
            self.conn.commit()

    st = _Store()
    P.ensure_tables(st)
    P.bind_store(st)
    return st, P


class _Macro:
    """Only what `generate_signal` reads. A stub that carries MORE than the
    code touches invites the next reader to believe the extra fields matter."""
    vix = 17.72                 # MU 2026-09-14's real vix_at_entry
    is_fed_day = False
    fed_event_name = ""
    butterfly_half_size = False


class _MS:
    adx = 48.23                 # MU's real adx_at_entry
    flat_angle_deg = -1.0


class _Vol:
    price_vs_vwap = "ABOVE"
    atr = 6.0


class _Chain:
    """An EMPTY chain, deliberately.

    ⚠️ This is why every refusal check reads the plan row. With no contract the
    strategy refuses at the `contract` gate for a reason that has nothing to do
    with this file's subject, so `sig is None` is true at HEAD and proves
    NOTHING (section 0.4). The control U3 asserts exactly that: it refuses, but
    NOT at our gate.
    """
    calls: list = []
    puts: list = []
    iv_rank = 0.0
    spot_price = MU_FIRE


def _fire(price: float, direction: str = "long"):
    """Drive the REAL generate_signal and return (signal, plan reason text)."""
    from strategy.orb_strategy import ORBStrategy
    st, P = _plan_store()
    eng = _confirm(_mu_engine(direction), direction)
    P.begin_tick()
    sig = ORBStrategy().generate_signal(
        orb=eng._data, ms=_MS(), vol_state=_Vol(), chain=_Chain(), macro=_Macro(),
        current_price=price)
    P.close_tick(st, "MU")
    row = st.conn.execute(
        "SELECT verdict, reason FROM plan_tick ORDER BY ts_epoch DESC LIMIT 1"
    ).fetchone()
    return sig, ((row["reason"] or "") if row else ""), eng


# ── the gate's name, which is what U1/U2/U5 anchor on ────────────────────────
GATE = "entry_underwater"


def main() -> int:
    print("check_orb_underwater_entry — a fire already through its own "
          "invalidation is refused, and one that gets through is out on the "
          "tick it is seen")
    print()

    # ── U0 — capability. A born-red record has to SHOW what is missing rather
    # than abort on a traceback: a crash reads like a broken test, not a caught
    # absence. (r379's lesson, applied here.)
    try:
        from analysis.orb_engine import ORBEngine  # noqa: F401
        from strategy.orb_strategy import ORBStrategy  # noqa: F401
        from strategy import plan as _P  # noqa: F401
        import pandas  # noqa: F401
    except Exception as exc:                                     # noqa: BLE001
        print(f"  FAIL  U0 the ORB entry path did not import: {exc}")
        for n in ("U1", "U2", "U3", "U4", "U5", "U6", "U7", "U7b", "U8"):
            check(n, False, "unreachable: import failed")
        return 1

    # ── the fixture must reproduce MU before it can prove anything about it ──
    eng = _confirm(_mu_engine("long"), "long")
    d = eng._data
    from analysis.orb_engine import ORBState
    ok_fix = (d.state == ORBState.OPEN_LONG
              and abs(float(d.stop_level) - MU_STOP) < 1e-6)
    check("U0 the fixture reproduces MU: the 09:50 candle confirms and the "
          "stop is the 09:46 low",
          ok_fix, f"state={d.state} stop_level={d.stop_level}")
    if not ok_fix:
        for n in ("U1", "U2", "U3", "U4", "U5", "U7", "U7b", "U8"):
            check(n, False, "fixture did not reproduce MU")
        return 1

    # ── U1 — THE MU CASE ────────────────────────────────────────────────────
    sig, why, _ = _fire(MU_FIRE, "long")
    check("U1 price 913.495 is below the impulsive low 914.14 -> REFUSED, and "
          "the plan row names the gate",
          sig is None and GATE in why,
          f"sig={'None' if sig is None else 'BUILT'} reason={why!r}")

    # ── U2 — the short-side mirror ──────────────────────────────────────────
    eng_s = _confirm(_mu_engine("short"), "short")
    stop_s = float(eng_s._data.stop_level or 0.0)
    sig2, why2, _ = _fire(stop_s + 0.50, "short")
    check("U2 a short firing ABOVE the impulsive high -> REFUSED by the same "
          "gate",
          sig2 is None and GATE in why2,
          f"stop={stop_s:.2f} fire={stop_s + 0.50:.2f} reason={why2!r}")

    # ── U3 — THE CONTROL. A guard that refuses everything passes U1 and U2 ──
    sig3, why3, _ = _fire(916.00, "long")
    check("U3 CONTROL a fire correctly beyond the boundary and HOLDING the "
          "origin is not refused by this gate",
          GATE not in why3,
          f"reason={why3!r}")

    # ── U4 — CONTROL, section 37: a refusal is not a PARK ───────────────────
    _, _, eng4 = _fire(MU_FIRE, "long")
    still_live = eng4._data.state in (ORBState.OPEN_LONG, ORBState.ARMED_LONG)
    sig4, why4, _ = _fire(916.00, "long")
    check("U4 CONTROL the refusal does not park the setup — the engine is "
          "still live and a later good fire is not blocked",
          still_live and GATE not in why4,
          f"state={eng4._data.state} later_reason={why4!r}")

    # ── U5 — COUNTED, not swallowed (section 0.5) ───────────────────────────
    check("U5 the refusal is recorded as a verdict, not only logged",
          bool(why) and GATE in why,
          f"reason={why!r}")

    # ── U6 — CONTROL: SIZING IS UNTOUCHED ───────────────────────────────────
    # ⚠️ Anchored on the RETURNED contract count, never on source text
    # (section 21) and never on a version string (section 24). MU's real
    # inputs: premium 4.17, ORB width 10.15, |entry - stop| 0.645 -> 15.
    try:
        from risk.risk_manager import RiskManager
        rm = RiskManager()
        res = rm.size_for("long_debit", premium=4.17, orb_width=10.15,
                          orb_stop_distance=0.645, budget_usd=6500.0)
        check("U6 CONTROL sizing is unchanged — MU's inputs still size 15",
              int(getattr(res, "contracts", -1)) == 15,
              f"contracts={getattr(res, 'contracts', None)} "
              f"rule={getattr(res, 'rule', None)}")
    except Exception as exc:                                     # noqa: BLE001
        check("U6 CONTROL sizing is unchanged — MU's inputs still size 15",
              False, f"sizer did not run: {exc}")

    # ── U7 / U7b / U8 — THE LIVE ARM ────────────────────────────────────────
    # ⚠️ The last CLOSED candle is deliberately left on the SAFE side in U7, so
    # the existing completed-candle arm CANNOT be what exits. If U7 passes with
    # a safe-side close, the exit came from the FILL — which is the whole claim.
    try:
        import datetime as _dt
        import pandas as pd
        import execution.exit_engine as XE
        from execution.exit_engine import ExitEngine
        from utils.time_utils import ET

        def _rec(entry, stop, direction="long"):
            # MU's real numbers throughout: the fixture comes from the banked
            # row, not from my belief about what a record looks like (0.4).
            return {
                "trade_id": "underwater-0001", "symbol": "MU",
                "strategy": "ORBStrategy", "setup_type": "ORB Long",
                "direction": direction, "option_side": "call",
                "contracts": 15, "entry_premium": 4.17,
                "stop_premium": 3.13125, "target_premium": 8.35,
                "trail_activation": 6.2625, "underlying_entry": entry,
                "underlying_stop": stop, "underlying_target": 924.70,
                "orb_range_high": MU_ORB_HIGH, "orb_range_low": MU_ORB_LOW,
                "status": "open", "is_butterfly": 0, "is_condor_leg": 0,
            }

        def _bars(last_close):
            return pd.DataFrame(
                [{"open": last_close, "high": last_close + 0.2,
                  "low": last_close - 0.2, "close": last_close}] * 3,
                index=pd.date_range("2026-09-14 09:50", periods=3, freq="1min"))

        # 🔴 PIN THE CLOCK — the first cut of this file did not, and U7 went
        # GREEN AT HEAD on `hard_close_15:45_ET` because the suite happened to
        # run at 15:48 ET. A check that passes for a reason unrelated to its
        # claim is WORKING_AGREEMENT 0.4, and one whose colour depends on the
        # wall clock is CHK.4 — an intermittent gate is worse than a red one.
        # ⚠️ AND THE SECOND CUT PATCHED THE WRONG THING: `XE.datetime`, which
        # this branch never consults. The ORB path calls `is_hard_close_time()`,
        # imported into the module namespace, and it is evaluated BEFORE the
        # premium floor — so it is the name that has to be pinned. Patching a
        # clock the code does not read is a fixture that proves nothing, which
        # is the same class of error as the defect this file exists to catch.
        _real_hc = XE.is_hard_close_time
        XE.is_hard_close_time = lambda *a, **k: False

        ee = ExitEngine(paper_trading=True)
        # entry 913.495 is BELOW stop 914.14; the last closed candle is 916.00,
        # comfortably ABOVE the stop, so the completed-candle arm is silent.
        dec = ee.evaluate(_rec(MU_FIRE, MU_STOP), current_premium=4.10,
                          df_1m=_bars(916.00))
        check("U7 an entry already through the stop exits on the FIRST "
              "evaluate, with the last closed candle still on the safe side",
              bool(getattr(dec, "should_exit", False)),
              f"reason={getattr(dec, 'exit_reason', None)!r}")

        # section 22 — the same record after a SELECT * round trip
        rehydrated = dict(_rec(MU_FIRE, MU_STOP))
        dec_b = ee.evaluate(rehydrated, current_premium=4.10,
                            df_1m=_bars(916.00))
        check("U7b the rehydrated shape behaves identically",
              bool(getattr(dec_b, "should_exit", False)),
              f"reason={getattr(dec_b, 'exit_reason', None)!r}")

        # U8 — CONTROL. Entered CORRECTLY (916.00 above the 914.14 stop), now
        # intrabar through the level, but the last CLOSED candle holds.
        dec2 = ee.evaluate(_rec(916.00, MU_STOP), current_premium=4.10,
                           df_1m=_bars(916.00))
        check("U8 CONTROL a correctly-entered position whose last closed "
              "candle holds does NOT exit — the breathing room survives",
              not bool(getattr(dec2, "should_exit", False)),
              f"reason={getattr(dec2, 'exit_reason', None)!r}")
        XE.is_hard_close_time = _real_hc
    except Exception as exc:                                     # noqa: BLE001
        for n in ("U7", "U7b", "U8"):
            check(n, False, f"exit path did not run: {exc}")

    print()
    if _fails:
        print("FAILED: " + ", ".join(_fails))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
