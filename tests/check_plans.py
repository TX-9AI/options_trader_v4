#!/usr/bin/env python3
"""
tests/check_plans.py  v1.0  (2026-08-25)

The plan engine declares, prices, and CANNOT AFFECT TRADING.

⚠️ THE LAST ASSERTION IS THE IMPORTANT ONE. r126 ships an engine that renders
verdicts — TAKE and DECLINE — on live setups. That is precisely the shape of
thing that gets wired into dispatch by a future edit "since it already knows".
This test fails if main.py ever reads it.
"""
import ast
import os
import sys

FAIL = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        FAIL.append(label)


class _C:
    def __init__(self, strike, bid, ask, gamma=0.0, oi=0.0):
        self.strike, self.bid, self.ask = strike, bid, ask
        self.gamma, self.oi = gamma, oi


class _Chain:
    def __init__(self, calls, puts):
        self.calls, self.puts = calls, puts


def main():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from derived.plans import PlanEngine

    e = PlanEngine(store=None, symbol="TSLA", ledger=None)

    # A chain with a deliberate gamma flip at 360, TSLA 2026-08-25 shape.
    calls = [_C(k, max(0.05, 8 - (k-350)*0.6), max(0.10, 8.4 - (k-350)*0.6),
                gamma=0.02 if k != 360 else 0.044,
                oi=800 if k != 360 else 7326) for k in range(345, 376, 5)]
    puts = [_C(k, max(0.05, 1.9 - (350-k)*0.22), max(0.10, 2.0 - (350-k)*0.22),
               gamma=0.02, oi=1500) for k in range(340, 361, 5)]
    ctx = {"price": 354.41, "chain": _Chain(calls, puts),
           "orb_high": 351.88, "orb_low": 349.20,
           "session_fraction_remaining": 0.60}

    per = e._gamma_by_strike(ctx["chain"], ctx["price"])
    check("P1 gamma surface is built from gamma x OI", bool(per), f"{len(per)} strikes")

    pin = e._pin(per)
    check("P2 the gamma flip is located", pin is not None, f"pin={pin}")

    conc, share = e._concentration(per, pin) if pin else (None, None)
    check("P3 concentration exceeds the neighbours", conc is not None and conc > 1.0,
          f"{conc:.2f}x" if conc else "none")

    b = e._butterfly(ctx)
    check("P4 the butterfly plan is PRICED, not just triggered",
          b is not None and (b.get("debit") is not None or b.get("verdict") == "NO PLAN"),
          f"debit={b.get('debit')} R={b.get('r')}" if b else "none")

    p = e._participation(ctx)
    check("P5 participation prices a real strike inside the range",
          p is not None and p.get("verdict") in ("TAKE", "DECLINE", "NO PLAN"),
          f"{p.get('verdict')} R={p.get('r')}" if p else "none")

    # ⚠️ A DECLINE MUST NAME ITS LEVELS. Operator's requirement: not "no
    # trade" but "R 0.29, target 350.00, stop 351.88, cannot clear 1:1".
    if p and p.get("verdict") == "DECLINE":
        w = p.get("why", "")
        check("P6 a decline names TARGET and STOP with numbers",
              "TARGET" in w and "STOP" in w, w[:70])

    # ── SWEEP: the CVX fix, as assertions ───────────────────────────────
    class _Sw:
        pool_price = 200.33; sweep_price = 200.29; kind = "low_sweep"
        swept_named_level = "London Low (R1)"; reclaimed = True
    class _Liq:
        recent_sweep = _Sw(); sweep_age_bars = 6; sweep_invalidated = False

    sputs = [_C(k, max(.05, 1.6-(200-k)*.18), max(.10, 1.7-(200-k)*.18))
             for k in range(190, 206, 5)]
    sctx = {"price": 201.2, "chain": _Chain([], sputs), "liq_map": _Liq(),
            "orb_high": 0, "orb_low": 0, "session_fraction_remaining": 0.5}
    sw = e._sweep(sctx)
    check("S1 the sweep plan prices a strike beyond the pool",
          sw and sw.get("credit") is not None, f"credit={sw.get('credit')}")

    # ⚠️ THE R GATE ALONE REFUSES TODAY'S CVX TRADE. Twelve of these sold at
    # R 0.19 needs an 84% win rate to break even; every one stopped out.
    check("S2 CVX's actual shape DECLINES on R",
          sw.get("verdict") == "DECLINE" and (sw.get("r") or 9) < 1.0,
          f"R={sw.get('r')}")

    # ⚠️ IDENTITY IS (pool, reclaim bar) — NOT (strategy, trigger). The pool
    # price is IDENTICAL across re-fires, so a generic key cannot express the
    # one-attempt rule. This is the CVX fix and it must not regress.
    check("S3 the plan's identity keys on the RECLAIM BAR, not just the pool",
          "200.33" in (sw.get("identity") or "") and
          (sw.get("identity") or "").count(":") >= 2, sw.get("identity"))

    # ⚠️ AN ABSENT LEVEL BOOK IS 'n/a', NEVER a passing 0.0.
    check("S4 an unreachable level book reads absent, not zero",
          sw["checks"].get("level_hold_rate") is None, "hold rate absent")

    check("S5 pierce depth is RECORDED and gates nothing",
          sw["checks"].get("pierce_depth") is not None and
          sw["checks"]["pierce_depth"][1] == "n/a",
          str(sw["checks"].get("pierce_depth")))

    # ── RUNAWAY: the debit R problem ────────────────────────────────────
    class _D:
        def __init__(self, k, ask, delta, gamma, theta):
            self.strike, self.ask, self.bid = k, ask, ask - 0.1
            self.delta, self.gamma, self.theta = delta, gamma, theta
    class _Orb:
        state = "INVALIDATED"; invalidation_reason = "runaway"

    dcalls = [_D(k, max(.20, 4.0-(k-350)*0.55), max(.05, .62-(k-350)*.07),
                 0.045, 0.28) for k in range(348, 362, 2)]
    dctx = {"price": 353.0, "chain": _Chain(dcalls, []), "orb": _Orb(),
            "orb_high": 351.88, "orb_low": 349.20, "atr": 1.20,
            "session_fraction_remaining": 0.55}
    rw = e._runaway(dctx)
    check("D1 the debit plan mirrors the stop distance into the target",
          rw and rw.get("invalidation") == 351.88, f"stop={rw.get('invalidation')}")

    # 🔴 D2 IS THE ONE THAT MATTERS. Under a LINEAR delta a symmetric spot
    # target gives R = 1.00 for every debit on every tape — the gate would be
    # decorative, passing everything at exactly the floor. GAMMA is the whole
    # asymmetry: a long option gains delta toward the target and loses it
    # toward the stop. If this ever reads 1.00 again, the convexity term has
    # been dropped and the R gate has stopped measuring anything.
    flat = [_D(c.strike, c.ask, c.delta, 0.0, c.theta) for c in dcalls]
    fctx = dict(dctx); fctx["chain"] = _Chain(flat, [])
    rf = e._runaway(fctx)
    check("D2 gamma is what makes debit R differ from exactly 1.00",
          abs(rf["r"] - 1.00) < 0.01 and rw["r"] > 1.00,
          f"delta-only={rf['r']}  with-gamma={rw['r']}")

    # ⚠️ THETA IS RECORDED IN DOLLARS AND NEVER NETTED INTO R — operator's
    # instruction. A theta-burn layer belongs in fitting, not in an entry gate.
    th = rw["checks"].get("theta_dollars")
    check("D3 theta is recorded in dollars and gates nothing",
          th is not None and th[1] == "n/a" and th[0] > 0, str(th))

    check("D4 a 1R target that the tape cannot reach is refused",
          e._runaway(dict(dctx, atr=0.20))["verdict"] == "DECLINE",
          "travel gate")

    # ── P7: THE TABLES — spine + long-format checks ─────────────────────
    import sqlite3, time as _t

    class _S:
        def __init__(self):
            self.conn = sqlite3.connect(":memory:")
        def commit(self):
            self.conn.commit()

    st = _S()
    e2 = PlanEngine(store=st, symbol="TSLA", ledger=None)
    e2._last_run = 0
    e2.derive(ctx)
    n_tick = st.conn.execute("select count(*) from plan_tick").fetchone()[0]
    n_chk = st.conn.execute("select count(*) from plan_check").fetchone()[0]
    check("P7 plan_tick records every plan, TAKE and DECLINE alike",
          n_tick >= 2, f"{n_tick} rows")
    check("P8 plan_check is LONG — one row per variable per plan",
          n_chk >= 6, f"{n_chk} rows")

    # ⚠️ NO PLAN MAY WRITE A CHECK IT DOES NOT OWN. The CHECKS map is the
    # contract that lets a reader tell "not applicable" from "not run"; if a
    # plan writes outside it, that distinction is gone and the table starts
    # lying about coverage.
    stray = []
    for sg, nm in st.conn.execute(
            "select distinct strategy, check_name from plan_check"):
        if nm not in PlanEngine.CHECKS.get(sg, ()):
            stray.append((sg, nm))
    check("P9 no plan writes a check outside its declared CHECKS map",
          not stray, str(stray))

    # ⚠️ ABSENT IS NOT ZERO. A check that could not be computed must land as
    # NULL/'n/a', never 0.0/PASS — the VW.1 failure, which second_order.py
    # already refuses for the same reason.
    bad = st.conn.execute(
        "select count(*) from plan_check where value is null "
        "and verdict in ('PASS','FAIL')").fetchone()[0]
    check("P10 an unmeasurable check is NULL/'n/a', never 0.0/PASS",
          bad == 0, f"{bad} violations")

    # ── P11: THE ONE THAT MATTERS ───────────────────────────────────────
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(root, "main.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    # strip docstrings — a canary that fires on documentation trains you to
    # loosen it (the 2026-08-07 lesson, and it recurred twice on 08-25).
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "PlanEngine":
            hits.append(node.lineno)
        if isinstance(node, ast.Attribute) and node.attr in (
                "_butterfly", "_participation", "_concentration"):
            hits.append(node.lineno)
    check("P11 main.py does NOT read the plan engine — OBSERVE-ONLY",
          not hits, f"lines {hits}" if hits else "no references")

    print()
    if FAIL:
        print(f"FAILED {len(FAIL)}: {', '.join(FAIL)}")
        return 1
    print("check_plans: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
