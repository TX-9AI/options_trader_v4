#!/usr/bin/env python3
"""
tests/check_plan_prepares.py  v1.0  (2026-08-27, r160)

HYPOTHETICALS. Operator: *"see if each one makes logical sense afterwards by
testing them on hypothetical conditions. if it doesn't it's probably not
written correctly."* Each scenario below is a market condition stated in
words, then what the PLAN must say and what the STRATEGY must do.

Born red at 379fdf1 (r158): `prepare()`, `authorize()` and `manage()` do not
exist.

THE SWEEP — the plan is anticipatory, the strategy is confirmatory
  S1  13:30, NY Low 96 swept 3 bars ago, NOT yet reclaimed, chain prices a
      wing to R>=1. -> PLAN: HOLD "PREPARED — sell 95P/buy .. Waiting on:
      reclaimed". STRATEGY: fires nothing. (The trade is fully selected
      before the trigger.)
  S2  same tick, the bar CLOSES back inside. -> STRATEGY fires, and the
      signal's strikes/credit/stop are the plan's numbers, not re-derived.
  S3  reclaimed, but every wing prices below R 1.00. -> PLAN: DECLINE
      wing_r_best (structural). STRATEGY: nothing, even though the trigger
      is true. Relaxed does NOT waive it.
  S4  reclaimed, but no chain this tick. -> PLAN: NO PLAN naming "chain".
  S5  10:15 — outside the slot. -> PLAN: DORMANT, one row; no selection.
  S6  a call vertical is open; the freshest sweep is a HIGH (call side).
      Authorized side is PUT. -> the plan prepares the freshest LOW sweep
      instead; a call sweep cannot fire under the authorization.
  S7  reclaimed at a pool that stopped us out earlier today. -> DECLINE
      spent_level (structural), trigger true or not.

THE CONDOR — authorizes, then manages
  A1  no vertical open -> no authorization, no restriction.
  A2  a call vertical open -> "put" authorized, and the reason says SWEEP.
  A3  both open -> "" and "nothing more may fire".
  M1  one leg open -> LONE row (15% stop, not a condor).
  M2  formed, price mid-range, neither short tested -> HOLD, no rung.
  M3  formed, put short tested, a roll of the call side makes it risk-free
      -> row verdict ROLL, rung 1, with roll credit / close cost /
      cumulative vs width, risk_free PASS.
  M4  formed, put short tested, NO roll reaches risk-free -> the row says
      NO RUNG in so many words (the ladder gap, named on the tick).
  M5  rolled structure, 1m close through the call short -> rung 2b TENT,
      the hedge named as the OPPOSITE type, the floor stated.
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


class _C:
    def __init__(self, k, bid, ask, delta=0.2, symbol=""):
        self.strike, self.bid, self.ask = float(k), float(bid), float(ask)
        self.mark = (bid + ask) / 2
        self.delta, self.gamma, self.theta = delta, 0.01, -0.03
        self.expiry, self.open_interest = "x", 100
        self.symbol = symbol or f"P{k}"


class _Chain:
    def __init__(self, puts, calls=()):
        self.puts, self.calls = list(puts), list(calls)


class _Sweep:
    def __init__(self, kind, pool, name, reclaimed, bars=3, rej=0.0018,
                 sweep_price=None, invalidated=False):
        self.kind, self.pool_price, self.swept_named_level = kind, pool, name
        self.reclaimed, self.invalidated, self.bars_ago = reclaimed, invalidated, bars
        self.rejection_pct = rej
        self.sweep_price = sweep_price if sweep_price is not None else (
            pool - 0.18 if kind == "low_sweep" else pool + 0.18)


class _LM:
    def __init__(self, *sweeps):
        self.sweeps = list(sweeps)
        self.recent_sweep = min(self.sweeps, key=lambda s: s.bars_ago) if self.sweeps else None


def _row(st, strat, ts):
    return st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE strategy=? "
                           "AND ts_epoch=?", (strat, ts)).fetchone()


def main():
    from strategy import plan as P
    st = _Store()
    P.bind_store(st)
    os.environ["OT_RELAXED_ENTRY"] = "0"
    import strategy.sweep_credit_spread as sw
    sw.EARLIEST_ET, sw.LATEST_ET = "13:00", "14:00"
    S = sw.SweepCreditSpreadStrategy()
    S.planner.symbol = "TST"

    # a put chain where 95/92.5 clears R>=1: short 95 bid 1.40, wing 92.5 ask
    # 0.10 -> credit 1.30 on a 2.5 width, risk 1.20, R 1.08. (A first draft
    # priced the wing at 0.30 -> R 0.79 and the plan correctly REFUSED it —
    # the hypothetical was wrong, not the plan.)
    good_puts = [_C(97.5, 2.40, 2.50), _C(95, 1.40, 1.44), _C(92.5, 0.08, 0.10),
                 _C(90, 0.03, 0.05), _C(87.5, 0.02, 0.03)]
    poor_puts = [_C(97.5, 2.40, 2.50), _C(95, 0.30, 0.34), _C(92.5, 0.20, 0.22),
                 _C(90, 0.12, 0.14), _C(87.5, 0.08, 0.10)]
    common = dict(price_now=96.6, now_et="13:30", atr_pct=0.08, orb_high=99.5, orb_low=97.5)

    # S1
    P.begin_tick(1.0)
    lm = _LM(_Sweep("low_sweep", 96.0, "NY Low", reclaimed=False))
    sig = S.generate_signal(liq_map=lm, chain=_Chain(good_puts), **common)
    r1 = _row(st, "SweepCreditSpread", 1.0)
    check("S1 not yet reclaimed -> PLAN holds with the trade PREPARED and names the wait",
          sig is None and r1 and r1[0] == "HOLD" and "PREPARED" in r1[1]
          and "sell 95P" in r1[1] and "reclaimed" in r1[1], str(r1))

    # S2
    P.begin_tick(2.0)
    lm = _LM(_Sweep("low_sweep", 96.0, "NY Low", reclaimed=True))
    sig = S.generate_signal(liq_map=lm, chain=_Chain(good_puts), **common)
    r2 = _row(st, "SweepCreditSpread", 2.0)
    check("S2 reclaimed -> STRATEGY fires with the plan's strikes, credit, stop",
          sig is not None and sig.is_valid and sig.short_put_contract.strike == 95.0
          and sig.long_put_contract.strike == 92.5 and abs(sig.net_credit - 1.30) < 1e-9
          and abs(sig.stop_premium - 1.30 * 1.15) < 1e-9 and r2 and r2[0] == "TAKE",
          f"{r2} sig={sig and (sig.strike, sig.net_credit)}")

    # S3
    P.begin_tick(3.0)
    sig = S.generate_signal(liq_map=lm, chain=_Chain(poor_puts), **common)
    r3 = _row(st, "SweepCreditSpread", 3.0)
    check("S3 trigger true but no wing clears R 1.00 -> DECLINE wing_r_best, no fire",
          sig is None and r3 and r3[0] == "DECLINE" and "wing_r_best" in r3[1], str(r3))
    os.environ["OT_RELAXED_ENTRY"] = "1"
    P.begin_tick(3.5)
    sig = S.generate_signal(liq_map=lm, chain=_Chain(poor_puts), **common)
    check("S3b relaxed does NOT waive the R floor (structure, not selection)", sig is None)
    os.environ["OT_RELAXED_ENTRY"] = "0"

    # S4
    P.begin_tick(4.0)
    sig = S.generate_signal(liq_map=lm, chain=None, **common)
    r4 = _row(st, "SweepCreditSpread", 4.0)
    check("S4 no chain -> NO PLAN naming chain", sig is None and r4 and r4[0] == "NO PLAN"
          and "chain" in r4[1], str(r4))

    # S5
    P.begin_tick(5.0)
    c5 = dict(common); c5["now_et"] = "10:15"
    sig = S.generate_signal(liq_map=lm, chain=_Chain(good_puts), **c5)
    r5 = _row(st, "SweepCreditSpread", 5.0)
    check("S5 outside the slot -> DORMANT, nothing selected",
          sig is None and r5 and r5[0] == "DORMANT", str(r5))

    # S6
    P.begin_tick(6.0)
    lm6 = _LM(_Sweep("high_sweep", 103.0, "NY High", reclaimed=True, bars=1),
              _Sweep("low_sweep", 96.0, "NY Low", reclaimed=True, bars=4))
    calls = [_C(103, 0.30, 0.34), _C(105, 0.10, 0.12)]
    sig = S.generate_signal(liq_map=lm6, chain=_Chain(good_puts, calls),
                            required_side="put", **common)
    check("S6 call vertical open (put authorized): the plan prepares the LOW sweep, "
          "not the fresher HIGH, and fires a put spread",
          sig is not None and sig.option_side == "put" and sig.swept_level_name == "NY Low",
          str(sig and (sig.option_side, sig.swept_level_name)))

    # S7
    P.begin_tick(7.0)
    sw.mark_spent(sw._symbol_of(), "put", 96.0, "stopped out 13:05")
    sig = S.generate_signal(liq_map=lm, chain=_Chain(good_puts), **common)
    r7 = _row(st, "SweepCreditSpread", 7.0)
    check("S7 a spent pool -> DECLINE spent_level even with the trigger true",
          sig is None and r7 and r7[0] == "DECLINE" and "spent_level" in r7[1], str(r7))
    sw._SPENT.clear()

    # ── the condor ────────────────────────────────────────────────────────
    from strategy.iron_condor_strategy import IronCondorStrategy
    IC = IronCondorStrategy()
    check("A1 nothing open -> no authorization, no restriction", IC.authorize([]) == ("", ""))
    a2 = IC.authorize(["call"])
    check("A2 call vertical open -> PUT authorized, and only as a SWEEP",
          a2[0] == "put" and "SWEEP" in a2[1], a2[1])
    a3 = IC.authorize(["call", "put"])
    check("A3 both open -> nothing more may fire", a3[0] == "" and "nothing more" in a3[1])

    class _PM:
        def __init__(self, recs): self.recs = recs
        def get_open_records(self): return self.recs

    def leg(side, short, long_, credit, bw=False):
        return {"is_condor_leg": True, "option_side": side, "short_strike": short,
                "long_strike": long_, "spread_width": abs(short - long_),
                "credit_received": credit, "contracts": 1, "is_broken_wing": bw}

    # M1
    P.begin_tick(10.0)
    IC.manage(_PM([leg("put", 95, 90, 1.10)]), _Chain(good_puts), 98.0)
    m1 = _row(st, "CondorManagement", 10.0)
    check("M1 one leg -> LONE row, 15% stop, not a condor",
          m1 and m1[0] == "HOLD" and "lone" in m1[1] and "15%" in m1[1], str(m1))

    # a chain for management, 1-point strikes (the roll walks STRIKE_INCREMENT).
    # Calls lose value further OTM; rolling the call side down from 105 toward
    # price 95.4 collects credit. 98/103 collects 3.8-0.8 = 3.0 -> cumulative
    # 5.15 >= tested width 5 -> risk-free.
    def _cv(k, base, slope, k0): return max(0.02, base - (k - k0) * slope)
    m_puts = [_C(k, _cv(100 - k, 5, 0.6, 0) - 0.02, _cv(100 - k, 5, 0.6, 0) + 0.02)
              for k in range(85, 101)]
    m_calls = [_C(k, _cv(k, 5, 0.6, 96) - 0.02, _cv(k, 5, 0.6, 96) + 0.02, symbol=f"C{k}")
               for k in range(96, 116)]
    formed = _PM([leg("put", 95, 90, 1.10), leg("call", 105, 110, 1.05)])

    # M2
    P.begin_tick(11.0)
    rung = IC.manage(formed, _Chain(m_puts, m_calls), 100.0)
    m2 = _row(st, "CondorManagement", 11.0)
    check("M2 formed, mid-range -> HOLD, neither short tested, no rung",
          rung == "HOLD" and m2 and "neither short tested" in m2[1], str(m2))

    # M3 — put short 95 tested (price 95.4); roll the call side down toward
    # price collects fat credit here -> risk-free reachable
    P.begin_tick(12.0)
    rung = IC.manage(formed, _Chain(m_puts, m_calls), 95.4)
    m3 = _row(st, "CondorManagement", 12.0)
    chk = {r[0]: (r[1], r[2]) for r in st.conn.execute(
        "SELECT check_name, value, verdict FROM plan_check WHERE strategy='CondorManagement' AND ts_epoch=12.0")}
    check("M3 put short tested, roll reaches risk-free -> ROLL verdict, rung 1, numbers stated",
          rung == "ROLL" and m3 and m3[0] == "ROLL" and "RUNG 1" in m3[1]
          and "cumulative" in m3[1] and chk.get("risk_free", (None, ""))[1] == "PASS",
          f"{m3} risk_free={chk.get('risk_free')}")

    # M4 — same tested short, but the call side is cheap: the best roll (98/103)
    # collects 0.8-0.3 = 0.5 -> cumulative 2.65, short of the 5-wide width
    cheap_calls = [_C(k, _cv(k, 1.0, 0.1, 96) - 0.01, _cv(k, 1.0, 0.1, 96) + 0.01, symbol=f"C{k}")
                   for k in range(96, 116)]
    P.begin_tick(13.0)
    rung = IC.manage(formed, _Chain(m_puts, cheap_calls), 95.4)
    m4 = _row(st, "CondorManagement", 13.0)
    check("M4 tested, NO roll reaches risk-free -> the row says NO RUNG (the ladder gap, named)",
          rung == "NO_RUNG" and m4 and m4[0] == "DECLINE" and "NO RUNG" in m4[1]
          and "never do nothing" in m4[1], str(m4))

    # M5 — already rolled, 1m close through the call short 105
    import pandas as pd
    idx = pd.to_datetime([1_000_000 + 60 * i for i in range(3)], unit="s", utc=True)
    df = pd.DataFrame({"open": [104, 104.8, 105.3], "high": [104.9, 105.6, 105.8],
                       "low": [103.9, 104.7, 105.1], "close": [104.6, 105.4, 105.5]}, index=idx)
    rolled = _PM([leg("put", 100, 95, 1.10 + 0.9, bw=True), leg("call", 105, 110, 1.05)])
    P.begin_tick(14.0)
    rung = IC.manage(rolled, _Chain(m_puts, m_calls), 105.5, df_1m=df)
    m5 = _row(st, "CondorManagement", 14.0)
    check("M5 rolled structure, close through the call short -> RUNG 2b TENT, opposite-type "
          "hedge, floor stated",
          rung == "TENT" and m5 and m5[0] == "ROLL" and "TENT" in m5[1]
          and "opposite-type" in m5[1] and "15%" in m5[1], str(m5))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_plan_prepares: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
