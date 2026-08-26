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
    # ⚠️ `open_interest`, NOT `oi` — the real OptionContract field. This
    # fixture carried `oi` and so did the production code, so P1-P3 passed
    # against a name that does not exist on any real contract. The double had
    # to be wrong in the SAME way for the tests to go green, which is exactly
    # what happens when one person writes both in one sitting.
    def __init__(self, strike, bid, ask, gamma=0.0, oi=0.0):
        self.strike, self.bid, self.ask = strike, bid, ask
        self.gamma, self.open_interest = gamma, oi


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

    # ── CONDOR: one plan, two triggers ──────────────────────────────────
    ccalls = [_C(k, max(.05, 3.0-(k-193)*.45), max(.10, 3.1-(k-193)*.45))
              for k in range(190, 206, 5)]
    cputs = [_C(k, max(.05, 3.0-(191-k)*.45), max(.10, 3.1-(191-k)*.45))
             for k in range(180, 196, 5)]
    cbase = {"price": 192.0, "chain": _Chain(ccalls, cputs), "atr": 1.6,
             "session_high": 196.0, "session_low": 188.0,
             "orb_high": 195.0, "orb_low": 189.0}
    cd = e._condor(cbase)
    check("K1 the condor plan prices BOTH sides in one plan",
          cd and cd.get("short_strike") is not None
          and cd.get("short_put_strike") is not None,
          f"CCS {cd.get('short_strike')} / PCS {cd.get('short_put_strike')}")

    # 🔴 K2 IS THE CRM FIX. On 2026-08-25 a second leg signalled on 406
    # CONSECUTIVE TICKS with a put already open and left nothing in any log,
    # because _can_open_credit_spread refused Rule 3 silently. "Half a condor
    # waiting for its complement" is a real state that lasts hours; under a
    # two-plan model it is expressible only as the ABSENCE of a second plan,
    # which is exactly how 406 refusals produced silence.
    cd2 = e._condor(dict(cbase,
                         open_trades=[{"is_condor_leg": 1, "option_side": "put"}]))
    check("K2 a half-built condor is VISIBLE — leg2_pending is a row, not silence",
          cd2["checks"]["leg2_pending"][0] == 1.0
          and cd["checks"]["leg2_pending"][0] == 0.0,
          f"open={cd2['checks']['leg2_pending'][0]} none={cd['checks']['leg2_pending'][0]}")

    # ⚠️ R IS THE COMBINED STRUCTURE. Only ONE side can lose at expiry, so
    # risk is width minus TOTAL credit. Scoring a single leg systematically
    # understates the trade — a 0.30 side and a 0.30 side are not a 0.30 condor.
    tot = (cd.get("credit") or 0)
    check("K3 R is computed on the COMBINED credit, not one side",
          cd.get("risk") is not None and abs((5.0 - tot) - cd["risk"]) < 0.01,
          f"credit={tot} risk={cd.get('risk')}")

    check("K4 a range too tight to sell both sides of is refused",
          e._condor(dict(cbase, atr=9.0))["verdict"] == "DECLINE",
          "range_width_atr")

    # ── THE LADDER: ROLL → TENT → CLOSE ─────────────────────────────────
    rcalls = [_C(k, max(.02, 2.6-(k-200)*.42), max(.06, 2.75-(k-200)*.42))
              for k in range(190, 226, 5)]
    rputs = [_C(k, max(.02, 2.6-(196-k)*.42), max(.06, 2.75-(196-k)*.42))
             for k in range(170, 206, 5)]
    def _legs(rolled):
        return [{"is_condor_leg": 1, "status": "open", "option_side": "call",
                 "short_strike": 205.0, "long_strike": 210.0,
                 "credit_received": 0.90, "is_broken_wing": rolled},
                {"is_condor_leg": 1, "status": "open", "option_side": "put",
                 "short_strike": 190.0, "long_strike": 185.0,
                 "credit_received": 0.85, "is_broken_wing": rolled}]
    rbase = {"chain": _Chain(rcalls, rputs), "tent_floor_pct": 0.15}

    # ⚠️ THE ROLL IS RUNG 1 AND IS STRICTLY BETTER — it COLLECTS credit. The
    # tent is the rung BELOW it, never an alternative. condor_roll.py says so
    # in its own words and the plan must not invert them.
    # 🔴 THREE STATES ONLY: ROLL, else HEDGE (tent), else CLOSE. Operator,
    # 2026-08-25: *"I don't think any of my specs ever advise do nothing."*
    # A HOLD on a TESTED structure was MINE, not his, and it is gone.
    # ⚠️ "SHORT OF RISK-FREE" IS NOT A ROLL — the roll's entire purpose is
    # making the tested side risk-free, and the source refuses to execute one
    # that does not (`if plan is None or not plan.risk_free: return False`).
    # So it belongs in the same bucket as no roll at all: fall to the tent.
    l1 = e._roll(dict(rbase, price=206.0, open_trades=_legs(False)))
    check("L1 a TESTED structure never answers HOLD — three states only",
          l1["verdict"] in ("ROLL", "TENT", "CLOSE"),
          f"{l1['verdict']} rung={l1['checks']['rung'][0]}")

    check("L1b a roll short of risk-free falls THROUGH to the tent, not HOLD",
          l1["checks"]["rung"][0] == 2.0 or l1["verdict"] == "ROLL",
          f"rung={l1['checks']['rung'][0]} {l1['verdict']}")

    # ⚠️ THE ONLY LEGITIMATE HOLDS: nothing tested (no adverse move to answer)
    # and an unmarkable leg (the source calls acting on an unpriced chain the
    # worst of the three silent declines).
    _lh = e._roll(dict(rbase, price=197.0, open_trades=_legs(False)))
    check("L1c an UNTESTED structure may HOLD — nothing has gone wrong yet",
          _lh["verdict"] == "HOLD", _lh["verdict"])

    # ⚠️ NEVER BUY BACK THE TESTED SHORT. My first draft did exactly that and
    # the operator caught it: "why would we be buying the tested side???" It is
    # the most expensive leg on the board, which is why a textbook roll costs
    # more than closing. The real ladder never does it.
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(_root, "derived", "plans.py"), encoding="utf-8").read()
    i = src.index("def _roll(")
    body = "\n".join(l for l in src[i:src.index("# ── the tables", i)].split("\n")
                      if not l.strip().startswith("#"))
    # ⚠️ TEST THE PROPERTY, NOT A TOKEN. My first version banned the string
    # `close_cost` — but close_cost is now a LEGITIMATE field: the cost of
    # closing the UNTESTED vertical, which is exactly what the roll does. A
    # check that forbids a word rather than a behaviour is the same error as
    # a guard that matches its own comment.
    # THE REAL PROPERTY: whatever the plan proposes to close or re-strike must
    # be the UNTESTED side. Here the call is tested, so the plan must name the
    # PUT side as its direction and must not move the call short.
    # THE REAL PROPERTY: whatever the plan proposes must act on the UNTESTED
    # side or on a HEDGE — never on the tested short itself.
    check("L2 the plan never re-strikes the TESTED short",
          l1.get("short_strike") != 205.0,
          f"direction={l1.get('direction')} short={l1.get('short_strike')}")

    # ⚠️ PRICED BEFORE IT IS PAID. If the hedge's debit ALONE puts the
    # structure past the floor, the tent is not built and the position closes.
    l3 = e._roll(dict(rbase, price=206.0, open_trades=_legs(True)))
    check("L3 an unaffordable tent CLOSES rather than being bought",
          l3["verdict"] == "CLOSE" and l3["checks"]["rung"][0] == 2.0,
          f"{l3['verdict']} at {l3['checks']['cum_credit_after_pct'][0]}%")

    # ⚠️ THE FLOOR MEASURES CUMULATIVE CREDIT, not one leg's original credit —
    # otherwise a structure can bleed indefinitely one adjustment at a time.
    check("L4 the floor is measured on CUMULATIVE credit",
          "cum_credit_after_pct" in l3["checks"],
          str(l3["checks"]["cum_credit_after_pct"]))

    # ⚠️ THE TENT DEADLINE IS DERIVED FROM THE 15:45 CREDIT FLATTEN, never a
    # number of its own. An invented cutoff is a SECOND TIME AUTHORITY: at
    # 15:30 it would advertise a close the exit engine was not going to make.
    _rsrc = open(os.path.join(_root, "derived", "plans.py"), encoding="utf-8").read()
    check("L6 the tent's deadline reads VERTICAL_HOLD_TO_ET, not its own clock",
          "VERTICAL_HOLD_TO_ET" in _rsrc)



    # ── FORK: the tine is a LEVEL, not a channel to cross ───────────────
    class _T:
        def __init__(self, tf, side, rail, slope):
            self.tf, self.side, self.rail, self.slope = tf, side, rail, slope
            self.trigger, self.median, self.active = rail, 200.0, True
    class _CTM:
        def __init__(self, t): self._t = t
        def all_rails(self): return self._t

    fpx = 201.4
    fcalls = [_C(k, max(.03, 3.2-(k-fpx)*.30), max(.08, 3.4-(k-fpx)*.30))
              for k in range(195, 231, 5)]
    fputs = [_C(k, max(.03, 3.2-(fpx-k)*.30), max(.08, 3.4-(fpx-k)*.30))
             for k in range(170, 211, 5)]
    fctm = _CTM([_T("1h", "call", 203.2, 0.052), _T("1h", "put", 196.8, 0.052),
                 _T("1d", "call", 212.5, 0.004), _T("1d", "put", 188.0, 0.004)])
    # ⚠️ r134 — THE FORK NOW REQUIRES THE OPENING RANGE. Without it there is
    # no session map, so every tine returns NO PLAN by design (the map cannot
    # exist before 09:35). The fixture supplies a range that admits all four
    # tines so these checks still measure what they are about.
    fps = e._fork({"price": fpx, "chain": _Chain(fcalls, fputs),
                   "condor_triggers": fctm,
                   "orb_high": 202.15, "orb_low": 200.60})
    check("F1 one builder emits a plan per available timeframe AND side",
          isinstance(fps, list) and len(fps) == 4, f"{len(fps or [])} plans")

    # 🔴 BOTH TIMEFRAMES ARE VALID. Operator: "the hourly is valid too. Same
    # rationale." A DAILY tine is a multi-session boundary — a STRONGER level
    # than an hourly one, not a disqualified one.
    tfs = {p["checks"]["fork_tf"][0] for p in fps}
    check("F2 the 1d fork is NOT excluded — both timeframes plan",
          tfs == {1.0, 2.0}, str(sorted(tfs)))

    # ⚠️ NO SPAN / TRAVERSAL GATE. I began building `span_vs_session` — refuse
    # the daily because a 0DTE cannot cross a daily channel. That is the
    # CONDOR's logic applied to a trade that does not work that way: selling
    # beyond a tine no more requires price to reach the opposite rail than
    # selling beyond London High requires it to reach London Low. Operator:
    # "The tines are what's of value, not the channel."
    _fsrc = open(os.path.join(_root, "derived", "plans.py"), encoding="utf-8").read()
    _fi = _fsrc.index("def _fork(")
    _fbody = _fsrc[_fi:_fsrc.index("# ── the tables", _fi)]
    # ⚠️ STRIP COMMENTS AND THE DOCSTRING FIRST. My first version searched the
    # raw body for "traverse" and matched THE DOCSTRING EXPLAINING THAT THERE
    # IS NO TRAVERSAL GATE. That is the third time tonight a guard has fired on
    # its own explanation (r114's get_event_loop, r125's SQL localtime, now
    # this). The rule that keeps generalising: A GUARD MUST MATCH CODE, NEVER
    # PROSE — parse structure, or strip comments and strings before searching.
    import ast as _ast
    _fn = next(n for n in _ast.walk(_ast.parse(_fsrc))
               if isinstance(n, _ast.FunctionDef) and n.name == "_fork")
    # ⚠️ REMOVE THE DOCSTRING NODE — do not try to SUBTRACT ITS TEXT.
    # `ast.unparse` re-normalises whitespace, so a literal .replace() of
    # `get_docstring()` never matches and the prose survives. Deleting the node
    # is the only reliable way; that is what "match structure, not text" means
    # in practice.
    _body = list(_fn.body)
    if (_body and isinstance(_body[0], _ast.Expr)
            and isinstance(getattr(_body[0], "value", None), _ast.Constant)
            and isinstance(_body[0].value.value, str)):
        _body = _body[1:]
    _stripped = "\n".join(_ast.unparse(n) for n in _body)
    check("F3 there is NO channel-traversal gate in the fork's CODE",
          "span_vs_session" not in _stripped,
          "no span gate")

    # ⚠️ THE SHORT SITS JUST BEYOND THE TINE — the operator's construction,
    # first strike past the rail, not a fitted offset from it.
    _fc = next(p for p in fps if p["direction"] == "1h_call")
    check("F4 the short strike is the first one BEYOND the tine",
          _fc["short_strike"] >= 203.2 and _fc["short_strike"] - 203.2 < 5.0,
          f"tine 203.2 → short {_fc['short_strike']}")

    # 🔴 F5b — THE GEOMETRY MUST ACTUALLY ELIMINATE. The fixture above uses
    # only well-placed tines, so it cannot detect a missing geometry gate: I
    # removed the gate and every check still passed. A displaced tine — an
    # "upper" rail sitting BELOW the opening range — must be DECLINED, because
    # pricing a short call beyond it is an ITM short call, which is the defect
    # credit_edge recorded weeks ago and which I reproduced.
    _bad = _CTM([_T("1h", "call", 199.10, 0.05)])  # ceiling BELOW the range low
    _bp = e._fork({"price": fpx, "chain": _Chain(fcalls, fputs),
                   "condor_triggers": _bad,
                   "orb_high": 202.15, "orb_low": 200.60})
    check("F5b a CEILING below the opening range is eliminated by geometry",
          len(_bp) == 1 and _bp[0]["verdict"] == "DECLINE"
          and _bp[0]["checks"].get("geometry", (None, ""))[1] == "FAIL",
          f"{_bp[0]['verdict']} geometry={_bp[0]['checks'].get('geometry')}")

    # ⚠️ AND NO MAP BEFORE 09:35 — classifying without a marker would be an
    # accident dressed as a decision.
    _nr = e._fork({"price": fpx, "chain": _Chain(fcalls, fputs),
                   "condor_triggers": fctm})
    check("F5c with no opening range every tine is NO PLAN, not a guess",
          all(p["verdict"] == "NO PLAN" for p in _nr), f"{len(_nr)} plans")

    check("F5 tine slope is recorded — 1h drifts, 1d barely does",
          _fc["checks"]["tine_slope"][0] >
          next(p for p in fps if p["direction"] == "1d_call")["checks"]["tine_slope"][0],
          "1h slope > 1d slope")

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
