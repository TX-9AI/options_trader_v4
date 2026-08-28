#!/usr/bin/env python3
"""
tests/check_management_plan.py  v1.0  (2026-08-27, r166)

THE MANAGEMENT PLAN WATCHES; THE EXIT ENGINE EXECUTES.

Born red at 1b83ee0 (r165): strategy/management.py does not exist.

  M1  a runaway long, premium up 30%, trail not yet armed -> the row names
      the hard stop, the structure stop and the target with the record's
      OWN numbers, says the trail is not armed, carries MFE.
  M2  the same trade after the trail arms -> "premium <= trail -> out".
  M3  a sweep credit spread -> credit semantics: pnl positive when the
      spread's value FALLS; the premium stop reads ">=".
  M4  TCS -> breach of the ORB bound, no premium stop, nickel.
  M5  a butterfly -> stop and target, from the record.
  M6  an ADOPTED record -> no row (no declared conditions, no spec).
  M7  the r66 vector is written for the open position with outcome "manage"
      and the trade_id attached, once per record per tick.
  M8  the TCS vector exists now (vote, ADX, ORB width over EM).
  M9  every reading the plan writes comes from the record — the plan holds
      no threshold of its own (AST: no numeric literal compared to a premium).
  M10 main_loop calls the management plan AFTER manage_open_position and
      inside a try — narration can never reach an exit.
"""
import ast
import json
import os
import sqlite3
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.environ.setdefault("OT_PAPER_TRADING", "1")
_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


class _Store:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

    def commit(self):
        self.conn.commit()


def _row(st, strat, ts):
    return st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy=? "
                           "AND ts_epoch=?", (strat, ts)).fetchone()


def main():
    from strategy import plan as P
    from strategy.management import ManagementPlan, EXIT_CONDITIONS
    from derived.notes import NoteWriter
    st = _Store()
    P.bind_store(st)

    class _Notes:                       # what ctx["derived_engines"] holds
        name = "notes"
        writer = NoteWriter(st, "TST")

    class _Trend:
        overall_direction, primary_adx = "BULLISH", 27.0

    ctx = {"price": 101.9, "derived_engines": [_Notes()], "trend": _Trend(),
           "orb_high": 101.0, "orb_low": 100.0, "expected_move": 2.0}
    MP = ManagementPlan()

    run = {"trade_id": "rw1", "strategy": "RunawayContinuation", "option_side": "call",
           "direction": "long", "entry_premium": 1.00, "current_premium": 1.30,
           "stop_premium": 0.75, "target_premium": 2.00, "underlying_stop": 101.0,
           "trail_stop": None, "mfe_premium": 1.34, "mae_premium": 0.96, "excursion_ticks": 12}
    P.begin_tick(1.0)
    n = MP.tick(ctx, [run], 101.9)
    r1 = _row(st, "RunawayContinuation/manage", 1.0)
    check("M1 runaway +30%, trail not armed -> stop/structure/target from the record, trail not armed, MFE",
          n == 1 and r1 and r1[0] == "HOLD" and "premium <= 0.75 -> out (hard_stop)" in r1[1]
          and "1m close < 101.00 -> out (structure_stop)" in r1[1] and "trail not armed" in r1[1]
          and "premium >= 2.00 -> out (target)" in r1[1] and "(+30%)" in r1[1] and "MFE 1.34" in r1[1],
          str(r1))
    run["trail_stop"] = 1.12
    P.begin_tick(2.0)
    MP.tick(ctx, [run], 102.4)
    r2 = _row(st, "RunawayContinuation/manage", 2.0)
    check("M2 trail armed -> 'premium <= 1.12 -> out (trail armed)'",
          r2 and "premium <= 1.12 -> out (trail armed)" in r2[1], str(r2))

    short_run = dict(run, trade_id="rw2", option_side="put", direction="short",
                     underlying_stop=100.0, trail_stop=None)
    P.begin_tick(2.5)
    MP.tick(ctx, [short_run], 99.1)
    r2b = _row(st, "RunawayContinuation/manage", 2.5)
    check("M2b a SHORT runaway is hurt by a close ABOVE its stop — the row reads '>'",
          r2b and "1m close > 100.00 -> out (structure_stop)" in r2b[1], str(r2b))
    sweep = {"trade_id": "sw1", "strategy": "SweepCreditSpread", "option_side": "put",
             "is_credit_vertical": True, "entry_premium": 1.30, "current_premium": 0.90,
             "stop_premium": 1.495, "underlying_stop": 96.0, "excursion_ticks": 8}
    P.begin_tick(3.0)
    MP.tick(ctx, [sweep], 97.4)
    r3 = _row(st, "SweepCreditSpread/manage", 3.0)
    chk3 = st.conn.execute("SELECT value FROM plan_check WHERE strategy='SweepCreditSpread/manage' "
                           "AND ts_epoch=3.0 AND check_name='pnl_pct'").fetchone()
    check("M3 a credit spread: value fell 1.30 -> 0.90 reads as +31%, the premium stop reads '>='",
          r3 and "credit" in r3[1] and "premium >= 1.50 -> out (premium_stop)" in r3[1]
          and "1m close < 96.00 -> out (acceptance)" in r3[1] and chk3 and abs(chk3[0] - 0.3077) < 1e-3,
          f"{r3} pnl={chk3}")

    tcs = {"trade_id": "tc1", "strategy": "TrendCreditSpread", "option_side": "put",
           "is_credit_vertical": True, "is_trend_credit": True, "entry_premium": 1.30,
           "current_premium": 1.10, "underlying_stop": 351.88, "excursion_ticks": 3}
    P.begin_tick(4.0)
    MP.tick(ctx, [tcs], 353.2)
    r4 = _row(st, "TrendCreditSpread/manage", 4.0)
    check("M4 TCS -> breach of the bound and the nickel; no premium stop named",
          r4 and "1m close < 351.88 -> out (breach)" in r4[1] and "nickel" in r4[1]
          and "premium_stop" not in r4[1] and "hard_stop" not in r4[1], str(r4))

    fly = {"trade_id": "bf1", "strategy": "GEXPinButterfly", "option_side": "call",
           "is_butterfly": True, "entry_premium": 0.18, "current_premium": 0.22,
           "stop_premium": 0.135, "target_premium": 0.60, "excursion_ticks": 20}
    P.begin_tick(5.0)
    MP.tick(ctx, [fly], 100.6)
    r5 = _row(st, "GEXPinButterfly/manage", 5.0)
    check("M5 butterfly -> stop and target from the record",
          r5 and "premium <= 0.14 -> out (stop)" in r5[1] and "premium >= 0.60 -> out (target)" in r5[1],
          str(r5))

    P.begin_tick(6.0)
    n6 = MP.tick(ctx, [{"trade_id": "ad1", "strategy": "ADOPTED", "entry_premium": 1.0}], 100.0)
    check("M6 an ADOPTED record gets no row", n6 == 0)

    notes = st.conn.execute("SELECT strategy, outcome, trade_id, payload FROM strategy_note "
                            "WHERE outcome='manage' ORDER BY rowid").fetchall()
    check("M7 the r66 vector is written per open position with outcome 'manage' and the trade_id",
          len(notes) >= 5 and all(n[1] == "manage" for n in notes)
          and {n[2] for n in notes} >= {"rw1", "sw1", "tc1", "bf1"},
          f"{len(notes)} notes, ids {sorted({n[2] for n in notes})}")
    tcs_note = next((json.loads(n[3]) for n in notes if n[0] == "TrendCreditSpread"), None)
    spec = (tcs_note or {}).get("specific", {})
    check("M8 the TCS vector exists now — vote, ADX, ORB width over EM",
          spec.get("trend_dir") == "BULLISH" and spec.get("adx") == 27.0
          and abs((spec.get("orb_width_over_em") or 0) - 0.5) < 1e-9, str(spec))

    # M9 — the plan holds no threshold of its own
    src = open(os.path.join(_root, "strategy", "management.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            for c in n.comparators:
                if isinstance(c, ast.Constant) and isinstance(c.value, (int, float)) and c.value not in (0, 1):
                    bad.append(f"line {n.lineno}: compares to {c.value}")
    check("M9 the management plan compares premiums to the RECORD's fields, never to a literal of its own",
          not bad, "; ".join(bad) or "clean")

    # M10 — wired after manage_open_position, inside a try
    msrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    ml = next(n for n in ast.walk(ast.parse(msrc)) if isinstance(n, ast.FunctionDef) and n.name == "main_loop")
    body = ast.unparse(ml)
    i_m = body.find("pos_mgr.manage_open_position(chain=ctx.get('chain')")
    i_p = body.find("get_management_plan().tick(")
    in_try = any(isinstance(n, ast.Try) and "get_management_plan" in ast.unparse(n) for n in ast.walk(ml))
    check("M10 main_loop runs the management plan AFTER manage_open_position, inside a try",
          i_m != -1 and i_p != -1 and i_m < i_p and in_try, f"manage@{i_m} plan@{i_p} try={in_try}")

    check("M11 every strategy that opens a position declares its exit conditions",
          {"RunawayContinuation", "ORBStrategy", "SweepCreditSpread", "TrendCreditSpread",
           "IronCondorStrategy", "GEXPinButterfly"} <= set(EXIT_CONDITIONS))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_management_plan: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
