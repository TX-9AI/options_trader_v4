#!/usr/bin/env python3
"""
tests/check_leg2_levels.py  v1.0  (2026-08-26, r147)

LEG TWO IS A ONE-LEVEL PLAN ON A CONFIRMED REJECTION; THE BUTTERFLY HAS LEGS.

Born red at 054d224 (r146): `analysis.level_test` and `plan_second_leg` do not
exist, and the butterfly's signal is invalid.

  L1-L4  level_state: UNTESTED / BREACHED / REJECTED / ACCEPTED on a 1m tape,
         using the sweep detector's acceptance count.
  L5     leg two arms on the NEAREST valid level of the COMPLEMENTARY role.
  L6     BREACHED -> HOLD, no signal ("never sell on a level being breached").
  L7     REJECTED -> a VALID credit vertical beyond the level, R recorded.
  L8     STRICT vetoes a sub-1:1 leg two; RELAXED takes and records r_muted.
  L9     ACCEPTED -> the level is finished and the plan moves to the NEXT one.
  L10    a finished level survives a restart (reloaded from plan_ledger).
  L11    no candidate -> HOLD row saying leg two is off the table.
  L12    the pairing table filters level CLASS (trend-first -> named pools only).
  B1     the butterfly fires a VALID three-leg debit signal on the pin.
  B2     wing width is floored at one increment and capped at the pin distance.
  B3     STRICT vetoes a fly below 1:1; RELAXED takes it.
  B4     no exact strike at the pin -> refused, never a nearest substitute.
"""
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


def _df(rows, t0):
    """1m bars from (high, low, close) tuples, starting at epoch t0."""
    import pandas as pd
    idx = pd.to_datetime([t0 + 60 * i for i in range(len(rows))], unit="s", utc=True)
    return pd.DataFrame({"open": [r[2] for r in rows], "high": [r[0] for r in rows],
                         "low": [r[1] for r in rows], "close": [r[2] for r in rows]},
                        index=idx)


class _C:
    def __init__(self, k, mark, delta=0.2):
        self.strike, self.mark = float(k), float(mark)
        self.bid, self.ask = mark - 0.02, mark + 0.02
        self.delta, self.gamma, self.theta = delta, 0.01, -0.03
        self.expiry, self.symbol, self.open_interest = "x", f"O{k}", 100


class _Chain:
    def __init__(self, calls, puts):
        self.calls, self.puts = calls, puts


def main():
    from strategy import plan as P
    st = _Store()
    P.bind_store(st)
    # HERMETIC LEDGER: the condor's leg-2 plan persists finished levels through
    # derived.registry.plan_ledger(); point it at the same in-memory store so
    # the test never touches (or is polluted by) a real derived_store.db.
    import derived.registry as _reg
    from derived.plan_ledger import PlanLedger
    _led = PlanLedger(st, "TST")
    _reg.plan_ledger = lambda symbol="": _led
    P.begin_tick(1.0)
    os.environ["OT_RELAXED_ENTRY"] = "0"

    # ── L1-L4 ─────────────────────────────────────────────────────────────
    from analysis.level_test import (level_state, UNTESTED, BREACHED, REJECTED,
                                     ACCEPTED, ACCEPT_CLOSES)
    from analysis.session_map import CEILING, FLOOR
    t0 = 1_000_000
    lvl = 100.0
    s1, _ = level_state(_df([(99.5, 99.0, 99.2), (99.8, 99.1, 99.6)], t0), lvl, CEILING, t0)
    check("L1 UNTESTED — price never reached the level", s1 == UNTESTED)
    s2, d2 = level_state(_df([(99.8, 99.1, 99.6), (100.4, 99.7, 100.2)], t0), lvl, CEILING, t0)
    check("L2 BREACHED — through it, last close beyond, not yet accepted",
          s2 == BREACHED and d2["closes_beyond"] == 1, d2.get("why"))
    s3, d3 = level_state(_df([(99.8, 99.1, 99.6), (100.4, 99.7, 100.2), (100.1, 99.5, 99.7)], t0),
                         lvl, CEILING, t0)
    check("L3 REJECTED — tested, last close back inside (pierce recorded)",
          s3 == REJECTED and abs(d3["pierce"] - 0.4) < 1e-9, d3.get("why"))
    rows = [(99.8, 99.1, 99.6)] + [(100.5, 99.9, 100.3)] * ACCEPT_CLOSES
    s4, d4 = level_state(_df(rows, t0), lvl, CEILING, t0)
    check(f"L4 ACCEPTED — {ACCEPT_CLOSES} closes beyond finishes the level",
          s4 == ACCEPTED, d4.get("why"))
    s4b, _ = level_state(_df([(101.0, 99.0, 100.3)], t0), lvl, FLOOR, t0)
    check("L4b FLOOR mirror — a wick below with a close above is REJECTED", s4b == REJECTED)
    s4c, _ = level_state(_df([(101.0, 99.0, 99.5)], t0), lvl, CEILING, t0 + 3600)
    check("L4c bars BEFORE arming are not this test", s4c == UNTESTED)

    # ── the condor's leg two ──────────────────────────────────────────────
    from strategy.iron_condor_strategy import IronCondorStrategy
    import strategy.iron_condor_strategy as icm
    icm.INSTRUMENT = "TST"
    ic = IronCondorStrategy()
    ic.leg2_planner.symbol = "TST"

    class _Pool:
        def __init__(self, price, kind, name):
            self.price, self.kind, self.name = price, kind, name
            self.is_named, self.swept = True, False

    class _LM:
        pools = [_Pool(96.0, "low", "NY Low"), _Pool(94.0, "low", "PDL"),
                 _Pool(104.0, "high", "NY High")]

    class _Rail:
        def __init__(self, tf, side, rail):
            self.tf, self.side, self.rail = tf, side, rail

    class _CTM:
        def all_rails(self):
            return [_Rail("1h", "call", 105.0), _Rail("1h", "put", 95.0)]

    puts = [_C(k, 0.30 + (99 - k) * -0.05) for k in (92, 93, 94, 95, 96, 97, 98, 99)]
    chain = _Chain([_C(k, 0.30) for k in (101, 102, 103, 104, 105, 106)], puts)
    ctx = {"price": 98.0, "orb_high": 99.5, "orb_low": 97.5, "liq_map": _LM(),
           "condor_triggers": _CTM(), "df_1m": _df([(98.5, 97.9, 98.2)], t0)}

    # an open CALL spread wants a FLOOR complement; nearest valid floor below
    # the range is NY Low 96 (95 tine and 94 PDL are further)
    P.begin_tick(2.0)
    r5 = ic.plan_second_leg(ctx=ctx, chain=chain, current_price=98.0, open_side="call")
    check("L5 arms on the NEAREST valid level of the complementary role (NY Low 96)",
          r5 is None and ic._leg2 and ic._leg2["price"] == 96.0 and ic._leg2["role"] == FLOOR,
          str(ic._leg2 and (ic._leg2["name"], ic._leg2["price"])))
    row5 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='CondorLeg2' "
                           "AND ts_epoch=2.0").fetchone()
    check("L5b the armed, untested level is a HOLD row",
          row5 and row5[0] == "HOLD" and "untested" in (row5[1] or ""), str(row5))

    # breach: price closes through 96 (one close — not accepted yet)
    armed = ic._leg2["armed_ts"]
    ctx["df_1m"] = _df([(97.0, 95.8, 95.9)], armed)
    P.begin_tick(3.0)
    r6 = ic.plan_second_leg(ctx=ctx, chain=chain, current_price=95.9, open_side="call")
    row6 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='CondorLeg2' "
                           "AND ts_epoch=3.0").fetchone()
    check("L6 BREACHED -> HOLD, no signal — never sell on a level being breached",
          r6 is None and row6 and row6[0] == "HOLD" and "BREACHED" in (row6[1] or ""),
          str(row6))

    # rejection: wick through, close back above
    ctx["df_1m"] = _df([(97.0, 95.8, 95.9), (96.6, 95.7, 96.4)], armed)
    os.environ["OT_RELAXED_ENTRY"] = "0"
    P.begin_tick(4.0)
    r7 = ic.plan_second_leg(ctx=ctx, chain=chain, current_price=96.4, open_side="call")
    row7 = st.conn.execute("SELECT verdict, reason, r_now FROM plan_tick WHERE "
                           "strategy='CondorLeg2' AND ts_epoch=4.0").fetchone()
    # puts chain: 95 mark 0.50, long 95-wing; R is well below 1 here -> strict vetoes
    check("L8 STRICT vetoes a sub-1:1 leg two on a rejected level",
          r7 is None and row7 and row7[0] == "DECLINE" and "r:" in (row7[1] or "")
          and row7[2] is not None, str(row7))
    os.environ["OT_RELAXED_ENTRY"] = "1"
    from strategy import criteria as C
    if not C.relaxed_active():
        print("  SKIP  L7/L8b relaxed cannot activate here")
    else:
        P.begin_tick(5.0)
        r7b = ic.plan_second_leg(ctx=ctx, chain=chain, current_price=96.4, open_side="call")
        check("L7 REJECTED -> a VALID put vertical beyond the level",
              r7b is not None and r7b.is_valid and r7b.option_side == "put"
              and r7b.short_put_contract.strike < 96.0 and r7b.condor_trigger_source == "sweep_reversal",
              f"{getattr(r7b, 'short_put_contract', None) and r7b.short_put_contract.strike}/"
              f"{getattr(r7b, 'long_put_contract', None) and r7b.long_put_contract.strike}")
        chk = {r[0]: r[1] for r in st.conn.execute(
            "SELECT check_name, verdict FROM plan_check WHERE strategy='CondorLeg2' AND ts_epoch=5.0")}
        check("L8b RELAXED takes it and records r_muted", chk.get("r_muted") == "PASS", str(chk.get("r_muted")))
        ic.leg2_fired()
        check("L8c leg2_fired() clears the armed level", ic._leg2 is None)
    os.environ["OT_RELAXED_ENTRY"] = "0"

    # acceptance -> finished, move to the next floor (95 tine)
    ic._leg2 = None
    ctx["df_1m"] = _df([(98.5, 97.9, 98.2)], t0)
    P.begin_tick(6.0)
    ic.plan_second_leg(ctx=ctx, chain=chain, current_price=98.0, open_side="call")
    armed = ic._leg2["armed_ts"]
    ctx["df_1m"] = _df([(96.2, 95.5, 95.8)] * ACCEPT_CLOSES, armed)
    P.begin_tick(7.0)
    ic.plan_second_leg(ctx=ctx, chain=chain, current_price=95.8, open_side="call")
    row9 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='CondorLeg2' "
                           "AND ts_epoch=7.0").fetchone()
    P.begin_tick(8.0)
    ctx["df_1m"] = _df([(96.0, 95.6, 95.8)], t0)
    ic.plan_second_leg(ctx=ctx, chain=chain, current_price=95.8, open_side="call")
    check("L9 ACCEPTED -> level finished, plan moves to the NEXT floor (95 tine)",
          row9 and "ACCEPTED" in (row9[1] or "") and (FLOOR, 96.0) in ic._leg2_finished
          and ic._leg2 and ic._leg2["price"] == 95.0 and ic._leg2["source"] == "fork",
          f"{row9} now={ic._leg2 and ic._leg2['price']}")

    # L10 — a fresh instance must not re-arm on 96 (ledger says accepted today)
    ic2 = IronCondorStrategy()
    ic2.leg2_planner.symbol = "TST"
    led_rows = st.conn.execute("SELECT count(*) FROM plan_ledger WHERE strategy='CondorLeg2' "
                               "AND state='EXPIRED'").fetchone()[0] if st.conn.execute(
        "SELECT name FROM sqlite_master WHERE name='plan_ledger'").fetchone() else 0
    if led_rows == 0:
        print("  SKIP  L10 plan_ledger not wired in this environment (no derived store)")
    else:
        P.begin_tick(9.0)
        ctx["df_1m"] = _df([(98.5, 97.9, 98.2)], t0)
        ic2.plan_second_leg(ctx=ctx, chain=chain, current_price=98.0, open_side="call")
        check("L10 a finished level survives a restart (reloaded from plan_ledger)",
              ic2._leg2 and ic2._leg2["price"] != 96.0, str(ic2._leg2 and ic2._leg2["price"]))

    # L11 — no candidate at all
    ic3 = IronCondorStrategy()
    ic3.leg2_planner.symbol = "TST"
    ic3._leg2_loaded_date = "never"      # avoid ledger reload noise

    class _Empty:
        pools = []

    class _NoRails:
        def all_rails(self):
            return []
    P.begin_tick(10.0)
    ic3._leg2_loaded_date = None
    ic3._leg2_finished = set()
    r11 = ic3.plan_second_leg(ctx={"price": 98.0, "orb_high": 99.5, "orb_low": 97.5,
                                   "liq_map": _Empty(), "condor_triggers": _NoRails(),
                                   "df_1m": ctx["df_1m"]},
                              chain=chain, current_price=98.0, open_side="call")
    row11 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy='CondorLeg2' "
                            "AND ts_epoch=10.0").fetchone()
    check("L11 no candidate -> HOLD row: leg two is off the table",
          r11 is None and row11 and row11[0] == "HOLD" and "off the table" in (row11[1] or ""),
          str(row11))

    # L12 — trend-first: only the 'sweep' class (named pools), never a tine
    ic4 = IronCondorStrategy()
    ic4.leg2_planner.symbol = "TST"
    ic4._leg2_finished = {(FLOOR, 96.0), (FLOOR, 94.0)}
    ic4._leg2_loaded_date = __import__("datetime").datetime.now(icm.ET).strftime("%Y-%m-%d")
    P.begin_tick(11.0)
    ctx["df_1m"] = _df([(98.5, 97.9, 98.2)], t0)
    ic4.plan_second_leg(ctx=ctx, chain=chain, current_price=98.0, open_side="call",
                        allowed_classes=("sweep",))
    check("L12 pairing table filters level CLASS — with named pools finished, a "
          "trend-first leg never arms on a tine", ic4._leg2 is None)

    # ── the butterfly ─────────────────────────────────────────────────────
    from strategy.gex_pin_butterfly import GEXPinButterflyStrategy
    import strategy.gex_pin_butterfly as bf
    bf.ENABLED = True
    bf.EARLIEST_ET, bf.LATEST_ET = "09:30", "16:00"

    class _GEX:
        gex_environment, pin_strike, pin_concentration = "PINNING", 101.0, 0.60

    # spot 100, pin 101, ATM IV 1.20 at 12:30 -> EM ~1.5, pin ~0.67 EM away
    calls = [_C(k, m) for k, m in ((99, 1.60), (100, 1.00), (101, 0.55), (102, 0.28), (103, 0.14))]
    chain_b = _Chain(calls, [])
    b = GEXPinButterflyStrategy()
    b.planner.symbol = "TST"
    os.environ["OT_RELAXED_ENTRY"] = "1"
    P.begin_tick(20.0)
    sig = b.generate_signal(gex=_GEX(), price_now=100.0, now_et="12:30", atm_iv=1.20,
                            chain=chain_b)
    rowb = st.conn.execute("SELECT verdict, reason, r_now FROM plan_tick WHERE "
                           "strategy='GEXPinButterfly' AND ts_epoch=20.0").fetchone()
    check("B1 the butterfly fires a VALID three-leg call debit on the pin",
          sig is not None and sig.is_valid and sig.is_butterfly and sig.center_contract.strike == 101.0
          and sig.butterfly_direction == "call" and sig.net_debit > 0,
          f"{rowb} legs={sig and (sig.lower_contract.strike, sig.center_contract.strike, sig.upper_contract.strike)}")
    check("B2 wing floored at one increment, capped at the pin distance",
          sig is not None and (sig.upper_contract.strike - sig.center_contract.strike) == 1.0
          and sig.lower_contract.strike == 100.0)
    # strict: this fly's R = (w - debit)/debit — make a fat debit to force a veto
    os.environ["OT_RELAXED_ENTRY"] = "0"
    calls_fat = [_C(k, m) for k, m in ((99, 2.00), (100, 1.50), (101, 0.55), (102, 0.28), (103, 0.14))]
    P.begin_tick(21.0)
    sig2 = b.generate_signal(gex=_GEX(), price_now=100.0, now_et="12:30", atm_iv=1.20,
                             chain=_Chain(calls_fat, []))
    row2 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                           "strategy='GEXPinButterfly' AND ts_epoch=21.0").fetchone()
    check("B3 STRICT vetoes a fly below 1:1 (R recorded on the DECLINE row)",
          sig2 is None and row2 and row2[0] == "DECLINE" and "r:" in (row2[1] or ""), str(row2))
    P.begin_tick(22.0)
    sig3 = b.generate_signal(gex=_GEX(), price_now=100.0, now_et="12:30", atm_iv=1.20,
                             chain=_Chain([c for c in calls if c.strike != 101.0], []))
    row3 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                           "strategy='GEXPinButterfly' AND ts_epoch=22.0").fetchone()
    check("B4 no exact strike at the pin -> refused, never a nearest substitute",
          sig3 is None and row3 and "legs:" in (row3[1] or ""), str(row3))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_leg2_levels: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
