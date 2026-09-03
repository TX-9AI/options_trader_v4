#!/usr/bin/env python3
"""
tests/check_plan_prepares.py  v1.7
v1.7  2026-09-03  r234 — S2 RE-DERIVED. It asserted
      `stop_premium == credit * 1.15` — 15% OF CREDIT, the inverted rule r155
      deleted — so the suite was CERTIFYING a stop 4x tighter than the one the
      engine fires. Third time a fixture in this file has certified the defect
      it was meant to pin; r219 did it for the fill basis.  (2026-09-02, r219)
v1.6  r219 — 🔴 S2 ASSERTED THE BASIS MISMATCH AND SO CERTIFIED IT. It
      required `net_credit == 1.30`, the BID/ASK credit, while
      position_manager marks a credit vertical at MID — so this file passed on
      every run while every credit vertical was booked on one side of the
      quote and marked on the other, losing both half-spreads at fill. The
      fixture's 95P is 1.40/1.44 and the 92.5P is 0.08/0.10: judged 1.30, mark
      1.33. Re-derived to the MARK per the operator's ruling that paper fills
      at mark, with S2b requiring the plan line to NAME BOTH — it read
      "credit N (bid/ask)" and N is now the mark, so an unlabelled number
      would carry the same lie forward.
v1.5  r208 — THE BUTTERFLY HYPOTHETICALS ARE RE-DERIVED. `calls_good` WAS the
      2026-09-01 trade: penny legs on a 1-wide ladder, debit 0.18, R 4.6, and
      the old code took it. It is kept as `calls_unsurvivable` and B1b, the
      refusal case (r155 — a fixture encoding the replaced rule is re-derived,
      not deleted). B2 now pins the NARROWEST of two qualifying wings; B3
      pins the wing_search refusal with the best available R stated. B3b is
      inverted: it asserted relaxed does not waive feasibility and still
      PASSED for a reason that no longer exists, so it now drives BOTH
      postures over one chain and asserts the verdicts are identical.
      ⚠️ B12 needed a 104 strike, and its absence was informative: a migrated
      pin near the edge of the listed chain has fewer wings to choose from,
      so "the magnet moved" and "the magnet moved somewhere we can trade"
      are different facts.
v1.5  r168: R2b — the runaway carries no underlying stop; a 20% premium floor.
v1.4  r165: R1-R8 — the runaway: contract prepared before the TP confirms;
      the buy on confirmation; the gamma-leverage pick is the best strike
      REACHABLE within the run (102 on a 0.90 run, 103 on a 1.90 run); the
      invalidated-on-runaway handoff; unbroken ORB holds; unreachable ATR
      holds naming it; past the cutoff is dormant.
v1.3  r164: C1-C6 — TCS: a weak ADX holds with the put spread prepared; a
      strong vote fires the plan's 350/347.5; price back inside the range
      holds; a NEUTRAL vote has no side to prepare; no wing clears R declines;
      09:50 is dormant.
v1.2  r163: T1-T7 — the tine as a MOVING level: a touch is found against the
      rail where it WAS (slope x time), not where it is now; a falling rail
      the high never reached is no touch; acceptance invalidates; the sweep's
      plan fires leg one on the touch with the short beyond the move; as leg
      two the touch is never selected; the spent lock is keyed by name.
v1.1  r161: B1-B7 — the butterfly's plan (weak pin holds with the fly
      prepared; R<1 declined, relaxed included; no exact apex strike declined)
      and its exemption from the single-position rule (asked with a position
      open, record appended).
v1.0  r160

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
    # 🔴 RE-DERIVED AT r219. The fixture's 95P is 1.40/1.44 and the 92.5P is
    # 0.08/0.10, so the BID/ASK credit is 1.40 - 0.10 = 1.30 and the MARK
    # credit is 1.42 - 0.09 = 1.33. The signal now BOOKS the mark, per the
    # operator's ruling that paper fills at mark; R is still JUDGED on 1.30.
    # ⚠️ ASSERTING 1.30 HERE WAS ASSERTING THE BASIS MISMATCH ITSELF — the
    # entry was recorded at bid/ask while position_manager marks the position
    # at mid, and the difference (both half-spreads) was booked as an instant
    # loss on every credit vertical. This check passed throughout.
    check("S2 reclaimed -> STRATEGY fires, BOOKING the mark credit",
          sig is not None and sig.is_valid and sig.short_put_contract.strike == 95.0
          and sig.long_put_contract.strike == 92.5
          and abs(sig.net_credit - 1.33) < 1e-9
          # 🔴 RE-DERIVED AT r234. This asserted `1.33 * 1.15` — 15% OF CREDIT,
          # the inverted rule r155 deleted and exit_engine's own fallback
          # warns about ("the trade will stop on noise"). The engine fires at
          # 15% OF RISK, so the suite was CERTIFYING a stop four times tighter
          # than the real one — the third time a fixture in this file has
          # certified the defect it was meant to pin (r219 did it for the fill
          # basis). The stop is now `fill + 0.15*(width - fill)`.
          and abs(sig.stop_premium - (1.33 + 0.15 * (2.5 - 1.33))) < 1e-9
          and r2 and r2[0] == "TAKE",
          f"{r2} sig={sig and (sig.strike, sig.net_credit)}")

    # ⚠️ AND THE NARRATION MUST NAME BOTH. "credit N (bid/ask)" printing the
    # mark is how this stayed invisible.
    check("S2b the plan line names the mark AND the judged bid/ask credit",
          r2 and "1.33 (mark)" in r2[1] and "judged 1.30 bid/ask" in r2[1],
          str(r2)[:150])

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

    # ── THE BUTTERFLY (r161) — earns its entry; exempt from the slot rule ──
    from strategy.gex_pin_butterfly import GEXPinButterflyStrategy
    import strategy.gex_pin_butterfly as bf
    bf.ENABLED = True
    bf.EARLIEST_ET, bf.LATEST_ET = "09:30", "16:00"
    B = GEXPinButterflyStrategy()
    B.planner.symbol = "TST"
    # PIN THE CLOCK: expected_move() reads wall time for the remaining-session
    # scaling, so an unpinned test drifts with the hour it is run at (it broke
    # at 06:17 ET with EM 9.2 where a 12:30 run gives 2.1). Production behavior
    # unchanged; the hypothetical states its time of day like its prices.
    _em_real = bf.expected_move
    from utils.time_utils import ET as _ET_pin
    _fixed_now = bf.datetime(2026, 8, 27, 12, 30, tzinfo=_ET_pin)
    bf.expected_move = lambda u, iv, now=None: _em_real(u, iv, now=_fixed_now)

    class _GEX:
        def __init__(self, env="PINNING", pin=101.0, conc=0.60):
            self.gex_environment, self.pin_strike, self.pin_concentration = env, pin, conc

    # 🔴 r208 — THE OLD `calls_good` WAS THE 2026-09-01 TRADE. Penny legs on a
    # 1-wide ladder price a 0.18 debit at R 4.6, and the old code took it: that
    # is META/CRM/MU, stopped out inside the minute they opened on floors of
    # 4.3c to 7.0c. A fly's quote is FOUR leg-spreads wide, so on this ladder no
    # debit can both clear R 1.00 and hold its floor — width >= 64 x leg-spread
    # means 2c legs need $1.28 of wing. It is KEPT, as the refusal case.
    calls_unsurvivable = [_C(k, m - 0.01, m + 0.01) for k, m in
                          ((99, 1.60), (100, 1.00), (101, 0.55), (102, 0.28), (103, 0.14))]
    # A ladder where a fly IS constructible: half-cent legs, and TWO wings
    # clear both bounds — 1-wide at R 1.50 and 2-wide at R 1.00 — so "prefer
    # narrower" has something to prefer.
    # ⚠️ 104 IS HERE FOR B12, and its absence is a real lesson rather than a
    # fixture convenience: with the ladder ending at 103 the MIGRATED pin at
    # 102 had exactly one constructible wing (101/102/103, debit 0.05, R 19)
    # and the search refused it as unsurvivable — correctly. A pin near the
    # edge of the listed chain has fewer wings to choose from, so "the magnet
    # moved" and "the magnet moved somewhere we can trade" are different
    # facts. 104 gives pin 102 its 2-wide (100/102/104, debit 0.60, R 2.33).
    calls_good = [_C(k, m - 0.005, m + 0.005) for k, m in
                  ((99, 2.55), (100, 1.70), (101, 1.00), (102, 0.70),
                   (103, 0.45), (104, 0.30))]
    calls_fat = [_C(k, m - 0.005, m + 0.005) for k, m in
                 ((99, 2.00), (100, 1.50), (101, 0.55), (102, 0.28), (103, 0.14))]
    # debit 1.50 - 1.10 + 0.28 = 0.68 on width 1 -> R 0.47, nothing clears
    # atm_iv 0.90 -> EM ~4.1 at the pinned 12:30 clock, so a 2.00 pin distance
    # sits at 49% of it (inside the 30-100% band) with spot at 99.
    bcommon = dict(price_now=99.0, now_et="12:30", atm_iv=0.90)

    os.environ["OT_RELAXED_ENTRY"] = "0"
    P.begin_tick(20.0)
    sig = B.generate_signal(gex=_GEX(conc=0.15), chain=_Chain([], calls_good), **bcommon)
    rb1 = _row(st, "GEXPinButterfly", 20.0)
    check("B1 PINNING but the pin is weak -> HOLD with the fly PREPARED, waiting on pin_concentration",
          sig is None and rb1 and rb1[0] == "HOLD" and "PREPARED" in rb1[1]
          and "buy 100/101/102" in rb1[1] and "pin_concentration" in rb1[1], str(rb1))
    # ── B1b (r208) — the 2026-09-01 fly is refused, and the row names WHICH
    # bound refused it. "No fly" and "no fly that can hold its stop" are
    # different facts and the fit has to tell them apart.
    P.begin_tick(20.5)
    sig_bad = B.generate_signal(gex=_GEX(), chain=_Chain([], calls_unsurvivable), **bcommon)
    rb1b = _row(st, "GEXPinButterfly", 20.5)
    check("B1b the 2026-09-01 fly is REFUSED and the row names the bound",
          sig_bad is None and rb1b and rb1b[0] == "DECLINE"
          and "wing_search" in rb1b[1] and "clear their own spread" in rb1b[1],
          str(rb1b)[:120])
    P.begin_tick(21.0)
    sig = B.generate_signal(gex=_GEX(), chain=_Chain([], calls_good), **bcommon)
    rb2 = _row(st, "GEXPinButterfly", 21.0)
    check("B2 pinning, strong, reachable -> fires the NARROWEST qualifying wing",
          sig is not None and sig.is_valid and sig.is_butterfly
          and sig.center_contract.strike == 101.0
          and sig.lower_contract.strike == 100.0
          and sig.upper_contract.strike == 102.0
          and abs(sig.net_debit - 0.40) < 1e-9 and rb2 and rb2[0] == "TAKE", f"{rb2}")
    P.begin_tick(22.0)
    sig = B.generate_signal(gex=_GEX(), chain=_Chain([], calls_fat), **bcommon)
    rb3 = _row(st, "GEXPinButterfly", 22.0)
    check("B3 everything true but no wing clears R 1.00 -> DECLINE, best R stated",
          sig is None and rb3 and rb3[0] == "DECLINE"
          and rb3[1].startswith("wing_search:") and "too wide for R>=" in rb3[1],
          str(rb3))
    # ── B3b (r208) — RELAXED CANNOT REACH THIS STRATEGY AT ALL ────────────
    # 🔴 THE OLD B3b ASSERTED "relaxed does NOT waive economic feasibility" and
    # it still PASSES — for a reason that no longer exists. Operator, 2026-09-01:
    # "the relaxed is adding unnecessary complexity — get rid of relaxed
    # entirely", scoped to the butterfly (the sweep stays loose on purpose to
    # collect parameters). So the claim worth pinning is stronger and simpler:
    # the flag changes NOTHING here, verified by driving both postures over the
    # same chain and comparing the verdicts — not by reading the source.
    os.environ["OT_RELAXED_ENTRY"] = "1"
    P.begin_tick(22.5)
    sig_rx = B.generate_signal(gex=_GEX(), chain=_Chain([], calls_fat), **bcommon)
    rb3b = _row(st, "GEXPinButterfly", 22.5)
    check("B3b the relaxed flag changes nothing on the butterfly",
          sig_rx is None and rb3b and rb3b[0] == rb3[0] and rb3b[1] == rb3[1],
          f"strict={rb3} relaxed={rb3b}")
    os.environ["OT_RELAXED_ENTRY"] = "0"
    P.begin_tick(23.0)
    sig = B.generate_signal(gex=_GEX(env="NEUTRAL"), chain=_Chain([], calls_good), **bcommon)
    rb4 = _row(st, "GEXPinButterfly", 23.0)
    check("B4 not PINNING (pin strike still published) -> HOLD, fly prepared at the pin, waiting on pinning",
          sig is None and rb4 and rb4[0] == "HOLD" and "pinning" in rb4[1], str(rb4))
    P.begin_tick(24.0)
    sig = B.generate_signal(gex=_GEX(), chain=_Chain([], [c for c in calls_good if c.strike != 101.0]),
                            **bcommon)
    rb5 = _row(st, "GEXPinButterfly", 24.0)
    check("B5 no exact strike at the pin -> DECLINE legs, never a substitute apex",
          sig is None and rb5 and rb5[0] == "DECLINE" and rb5[1].startswith("legs:"), str(rb5))

    # B6 — wiring: main_loop asks the butterfly in the position-open branch and
    # appends its record; the authorization no longer skips it.
    import ast as _ast
    msrc = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    ml = next(n for n in _ast.walk(_ast.parse(msrc))
              if isinstance(n, _ast.FunctionDef) and n.name == "main_loop")
    mls = _ast.unparse(ml)
    check("B6 main_loop asks the butterfly with a position OPEN, additively",
          "_attempt_butterfly(ctx, ms, state, additive=True)" in mls
          and '_plan_skip("GEXPinButterfly", _auth_why)' not in mls)
    from execution.position_manager import PositionManager
    pm = PositionManager.__new__(PositionManager)
    pm._open_records = [{"trade_id": "v1", "is_condor_leg": True}]
    pm.add_open_position({"trade_id": "bf1", "is_butterfly": True})
    check("B7 add_open_position APPENDS — the vertical under management is not dropped",
          [r["trade_id"] for r in pm._open_records] == ["v1", "bf1"])

    # ── THE TINE AS A MOVING LEVEL (r163) — slope, time, touch ────────────
    from analysis.liquidity_mapper import (publish_tines, LiquidityMap,
                                           _ACCEPT_CLOSES as _AC)
    import pandas as pd

    class _Rail:
        def __init__(self, tf, side, rail, slope):
            self.tf, self.side, self.rail, self.slope = tf, side, rail, slope
            self.trigger, self.median, self.active = rail, rail, True

    class _CTM:
        def __init__(self, *rails): self._r = list(rails)
        def all_rails(self): return self._r

    def _bars(rows, t0=2_000_000):
        idx = pd.to_datetime([t0 + 60 * i for i in range(len(rows))], unit="s", utc=True)
        return pd.DataFrame({"open": [r[2] for r in rows], "high": [r[0] for r in rows],
                             "low": [r[1] for r in rows], "close": [r[2] for r in rows]}, index=idx)

    # a 1h upper tine at 100.00 NOW, rising 0.60/bar of 1h = 0.01/min; 10 bars
    # back it stood at 99.90. T1: a bar 10 minutes ago with high 99.95 touches
    # the rail AS IT WAS (99.90) even though it is below the rail NOW (100.00).
    rows = [(99.5, 99.0, 99.3)] * 5 + [(99.95, 99.4, 99.6)] + [(99.7, 99.2, 99.5)] * 4 + [(99.8, 99.3, 99.6)]
    lm = LiquidityMap()
    n = publish_tines(lm, _CTM(_Rail("1h", "call", 100.0, 0.60)), _bars(rows))
    ev = lm.recent_sweep
    check("T1 slope+time: a bar that reached the rail WHERE IT WAS is a touch (rail now 100.00, "
          "then 99.90, high 99.95)",
          n == 1 and ev is not None and ev.touch and ev.kind == "high_sweep"
          and ev.swept_named_level == "1h upper tine" and abs(ev.sweep_price - 99.95) < 1e-9
          and ev.reclaimed and not ev.invalidated,
          f"n={n} ev={ev and (ev.kind, ev.sweep_price, ev.bars_ago)}")
    pool = next(p for p in lm.pools if p.moving)
    check("T1b the tine is on the map as a MOVING named pool with price_at(t)",
          pool.is_named and abs(pool.price_at(pool.as_of - 600) - 99.90) < 1e-6,
          f"{pool.name} now {pool.price} 10m-ago {pool.price_at(pool.as_of - 600):.4f}")
    # T2: same tape, a FALLING rail (was 100.10 ten minutes ago): the 99.95
    # high never reached it -> NO touch. Today's value alone would say otherwise.
    lm2 = LiquidityMap()
    n2 = publish_tines(lm2, _CTM(_Rail("1h", "call", 100.0, -0.60)), _bars(rows))
    check("T2 a bar below the rail as it stood then is NOT a touch, whatever the rail reads now", n2 == 0)
    # T3: two closes above the rail(t) since the first touch -> ACCEPTED -> invalidated
    rows3 = [(99.5, 99.0, 99.3)] * 5 + [(100.3, 99.6, 100.2), (100.5, 99.9, 100.3)] * 1 + [(100.4, 100.0, 100.3)] * 4
    lm3 = LiquidityMap()
    publish_tines(lm3, _CTM(_Rail("1h", "call", 100.0, 0.0)), _bars(rows3))
    ev3 = lm3.recent_sweep
    check(f"T3 {_AC}+ closes beyond the rail since the touch -> the tine is INVALIDATED",
          ev3 is not None and ev3.touch and ev3.invalidated and ev3.closes_beyond_live >= _AC,
          str(ev3 and ev3.closes_beyond_live))

    # T4: the sweep's plan takes the TOUCH as leg one: short beyond the move's
    # extreme, no reclaim required. Price is back inside (99.6 < 100).
    S2 = sw.SweepCreditSpreadStrategy(); S2.planner.symbol = "TST"
    # short 100 (first strike beyond the 99.95 high) bid 1.28; wing 101 ask 0.72
    # -> credit 0.56 on width 1, risk 0.44, R 1.27. (R>=1 on a credit vertical
    # needs credit >= half the width — a first draft priced the wing at 0.80
    # and the plan refused it at R 0.85. The hypothetical was wrong.)
    calls_t = [_C(k, m - 0.02, m + 0.02) for k, m in
               ((100, 1.30), (101, 0.70), (102, 0.35), (103, 0.15), (104, 0.06), (105, 0.03))]
    P.begin_tick(30.0)
    sigt = S2.generate_signal(liq_map=lm, chain=_Chain([], calls_t), price_now=99.6,
                              now_et="13:30", atr_pct=0.08, orb_high=99.2, orb_low=98.4)
    rt4 = _row(st, "SweepCreditSpread", 30.0)
    check("T4 a tine TOUCH fires leg one: call spread with the short BEYOND the touching high, "
          "classed as a fork trigger",
          sigt is not None and sigt.option_side == "call" and sigt.short_call_contract.strike > 99.95
          and sigt.condor_trigger_source == "1h_fork" and getattr(sigt, "touch_of_tine", False)
          and rt4 and rt4[0] == "TAKE" and "TOUCH" in rt4[1],
          f"{rt4} short={sigt and sigt.short_call_contract.strike}")
    # T5: under the condor's authorization (leg two) the same touch is NOT selected
    P.begin_tick(31.0)
    sig5 = S2.generate_signal(liq_map=lm, chain=_Chain([], calls_t), price_now=99.6,
                              now_et="13:30", atr_pct=0.08, orb_high=99.2, orb_low=98.4,
                              required_side="call")
    rt5 = _row(st, "SweepCreditSpread", 31.0)
    check("T5 as LEG TWO the touch is never selected — a rejection is required",
          sig5 is None and rt5 and rt5[0] == "HOLD" and "waiting for a named pool" in rt5[1], str(rt5))
    # T6: an invalidated tine touch does not fire
    P.begin_tick(32.0)
    sig6 = S2.generate_signal(liq_map=lm3, chain=_Chain([], calls_t), price_now=100.3,
                              now_et="13:30", atr_pct=0.08, orb_high=99.2, orb_low=98.4)
    rt6 = _row(st, "SweepCreditSpread", 32.0)
    check("T6 an ACCEPTED (invalidated) tine does not fire; the row names invalidated",
          sig6 is None and rt6 and "invalidated" in rt6[1], str(rt6))
    # T7: spent by NAME survives the rail drifting
    sw.mark_spent(sw._symbol_of(), "call", sw._name_key("1h upper tine"), "stopped out 13:40")
    lm7 = LiquidityMap()
    publish_tines(lm7, _CTM(_Rail("1h", "call", 99.98, 0.60)), _bars(rows))    # rail has drifted
    P.begin_tick(33.0)
    sig7 = S2.generate_signal(liq_map=lm7, chain=_Chain([], calls_t), price_now=99.6,
                              now_et="13:30", atr_pct=0.08, orb_high=99.2, orb_low=98.4)
    rt7 = _row(st, "SweepCreditSpread", 33.0)
    check("T7 a stopped-out tine stays SPENT by name although its price has moved",
          sig7 is None and rt7 and rt7[0] == "DECLINE" and "spent_level" in rt7[1], str(rt7))
    sw._SPENT.clear()

    # ── TCS (r164) — the plan prepares off the ORB bound; the vote fires it ──
    import strategy.trend_credit_spread as tcs
    tcs.TREND_CREDIT_ACTIVE = True
    TC = tcs.TrendCreditSpread(); TC.planner.symbol = "TST"
    from datetime import datetime as _dt
    _noon = tcs.ET.localize(_dt(2026, 8, 27, 12, 0))

    class _Trend:
        def __init__(self, d, adx=30.0): self.overall_direction, self.primary_adx = d, adx

    class _Vol:
        atr_current = 0.8
        df_5m = None

    # opening range 349.20-351.88; a BULLISH vote sells a PUT spread off the
    # ORB high with the short at the first strike INSIDE the range from the top
    # (350) — a fat 350 put vs a cheap 347.5 wing clears R.
    puts_tcs = [_C(k, m - 0.02, m + 0.02) for k, m in
                ((352.5, 4.20), (350, 1.60), (347.5, 0.30), (345, 0.10), (342.5, 0.04))]
    tcommon = dict(ms=None, vol_state=_Vol(), macro=None, orb_high=351.88, orb_low=349.20,
                   now_et=_noon)
    P.begin_tick(40.0)
    sig = TC.generate_signal(chain=_Chain(puts_tcs), current_price=354.0,
                             trend=_Trend("BULLISH", adx=18.0), **tcommon)
    r40 = _row(st, "TrendCreditSpread", 40.0)
    check("C1 BULLISH but ADX 18 < floor -> HOLD with the put spread PREPARED, waiting on adx",
          sig is None and r40 and r40[0] == "HOLD" and "PREPARED" in r40[1]
          and "sell 350P" in r40[1] and "adx=18" in r40[1], str(r40))
    P.begin_tick(41.0)
    sig = TC.generate_signal(chain=_Chain(puts_tcs), current_price=354.0,
                             trend=_Trend("BULLISH", adx=30.0), **tcommon)
    r41 = _row(st, "TrendCreditSpread", 41.0)
    check("C2 BULLISH, ADX 30, price above the range -> fires the plan's 350/347.5 put spread",
          sig is not None and sig.is_valid and sig.option_side == "put"
          and sig.short_put_contract.strike == 350.0 and sig.long_put_contract.strike == 347.5
          and sig.is_trend_credit and r41 and r41[0] == "TAKE", f"{r41}")
    P.begin_tick(42.0)
    sig = TC.generate_signal(chain=_Chain(puts_tcs), current_price=350.9,
                             trend=_Trend("BULLISH", adx=30.0), **tcommon)
    r42 = _row(st, "TrendCreditSpread", 42.0)
    c42 = st.conn.execute("SELECT value, verdict FROM plan_check WHERE strategy='TrendCreditSpread' "
                          "AND ts_epoch=42.0 AND check_name='outside_range'").fetchone()
    # price 0.9 above the short also sinks POP below its floor, and the plan
    # reports the STRUCTURAL fault first (a trade it could not build outranks
    # a trigger that has not fired) — but the condition is still evaluated
    # and recorded as FAIL on the same tick.
    check("C3 price back INSIDE the range -> no fire; outside_range recorded FAIL; the "
          "structural POP fault is reported first",
          sig is None and r42 and r42[0] == "DECLINE" and "pop" in r42[1]
          and c42 and c42[1] == "FAIL" and c42[0] < 0, f"{r42} outside_range={c42}")
    P.begin_tick(43.0)
    sig = TC.generate_signal(chain=_Chain(puts_tcs), current_price=354.0,
                             trend=_Trend("NEUTRAL", adx=30.0), **tcommon)
    r43 = _row(st, "TrendCreditSpread", 43.0)
    check("C4 NEUTRAL vote -> HOLD, no side to prepare, waiting on a directional vote",
          sig is None and r43 and r43[0] == "HOLD" and "no side to prepare" in r43[1], str(r43))
    puts_poor = [_C(k, m - 0.02, m + 0.02) for k, m in
                 ((352.5, 4.20), (350, 0.60), (347.5, 0.30), (345, 0.20), (342.5, 0.12))]
    P.begin_tick(44.0)
    sig = TC.generate_signal(chain=_Chain(puts_poor), current_price=354.0,
                             trend=_Trend("BULLISH", adx=30.0), **tcommon)
    r44 = _row(st, "TrendCreditSpread", 44.0)
    check("C5 vote true but no wing clears R -> DECLINE wing_r_best (structural)",
          sig is None and r44 and r44[0] == "DECLINE" and "wing_r_best" in r44[1], str(r44))
    P.begin_tick(45.0)
    sig = TC.generate_signal(chain=_Chain(puts_tcs), current_price=354.0,
                             trend=_Trend("BULLISH", adx=30.0),
                             **{**tcommon, "now_et": tcs.ET.localize(_dt(2026, 8, 27, 9, 50))})
    r45 = _row(st, "TrendCreditSpread", 45.0)
    check("C6 09:50 -> DORMANT", sig is None and r45 and r45[0] == "DORMANT", str(r45))

    # ── THE RUNAWAY (r165) — gamma does the heavy lifting ────────────────
    import strategy.runaway_continuation as rw
    RW = rw.RunawayContinuationStrategy(); RW.planner.symbol = "TST"

    class _ORB:
        def __init__(self, state="OPEN_LONG", hi=101.0, lo=100.0, tp=101.5, inval="", bd=""):
            self.state, self.orb_high, self.orb_low, self.target_50pct = state, hi, lo, tp
            self.invalidation_reason, self.break_direction = inval, bd

    class _G:
        def __init__(self, k, prem, delta, gamma):
            self.strike, self.mark, self.ask, self.bid = float(k), prem, prem + 0.02, prem - 0.02
            self.delta, self.gamma, self.theta = delta, gamma, -0.04
            self.expiry, self.open_interest, self.symbol = "x", 100, f"C{k}"

    # spot 101.9 after a 0.90 run from the ORB high 101.0. A realistic OTM
    # ladder: premium and delta fall with distance, gamma peaks near the money.
    calls_rw = [_G(102, 0.95, 0.46, 0.050), _G(103, 0.48, 0.30, 0.058), _G(104, 0.20, 0.17, 0.040),
                _G(105, 0.08, 0.09, 0.022), _G(106, 0.03, 0.04, 0.010)]

    def _lev(c, run=0.9):
        return (abs(c.delta) * run + 0.5 * c.gamma * run * run) / c.ask
    _by_lev = sorted(calls_rw, key=lambda c: -_lev(c))
    os.environ["OT_RELAXED_ENTRY"] = "1"      # R muteable here; the pick is the point
    P.begin_tick(50.0)
    sig = RW.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.9, prev_close=101.4,
                             now_et="10:15", chain=_Chain([], calls_rw))
    r50 = _row(st, "RunawayContinuation", 50.0)
    check("R1 broke and ran, TP not yet closed beyond -> HOLD with the contract PREPARED, "
          "waiting on runaway_confirmed",
          sig is None and r50 and r50[0] == "HOLD" and "PREPARED" in r50[1]
          and "runaway_confirmed" in r50[1] and "leverage" in r50[1], str(r50))
    P.begin_tick(51.0)
    sig = RW.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.9, prev_close=101.6,
                             now_et="10:15", chain=_Chain([], calls_rw))
    r51 = _row(st, "RunawayContinuation", 51.0)
    check("R2 close beyond the 50% TP and holding -> BUYS the plan's contract, valid",
          sig is not None and sig.is_valid and sig.option_side == "call"
          and getattr(sig, "disarms_retest", False) and r51 and r51[0] == "TAKE", str(r51))
    check("R2b (r168) the runaway carries NO underlying stop and a 20% premium floor — "
          "the ORB boundary is not its stop",
          sig is not None and not getattr(sig, "underlying_stop", 0)
          and abs(sig.stop_loss_pct - 0.20) < 1e-9
          and abs(sig.stop_premium() - sig.entry_premium * 0.80) < 1e-9
          and "no price stop" in (r51[1] or ""),
          f"underlying_stop={getattr(sig, 'underlying_stop', None)} floor={sig and sig.stop_premium():.2f}")
    # Raw leverage-per-dollar always crowns the cheapest far-OTM ticket (here
    # the 105/106). "Just enough OTM" is the reachability band — strikes
    # within the run — and inside it the 102 wins. The band is the discipline.
    check("R3 the pick is the highest gamma-leverage strike REACHABLE within the 0.90 run "
          "(the 102); the raw ranking's winner sits beyond the run and is not taken",
          sig is not None and sig.strike == 102.0 and abs(sig.run_at_entry - 0.9) < 1e-9
          and _by_lev[0].strike > 101.9 + 0.9,
          f"picked {sig and sig.strike}; raw ranking {[c.strike for c in _by_lev][:3]}")
    P.begin_tick(52.0)
    sig = RW.generate_signal(orb=_ORB(hi=100.0, tp=100.8), atr_pct=0.14, price_now=101.9,
                             prev_close=101.6, now_et="10:15", chain=_Chain([], calls_rw))
    check("R4 a bigger run (1.90) reaches further and gamma picks the 103 — 'just enough OTM' "
          "scales with the intensity of the move",
          sig is not None and sig.strike == 103.0, str(sig and sig.strike))
    P.begin_tick(53.0)
    sig = RW.generate_signal(orb=_ORB(state="INVALIDATED", inval="runaway", bd="long"),
                             atr_pct=0.14, price_now=101.9, prev_close=101.6, now_et="10:15",
                             chain=_Chain([], calls_rw))
    check("R5 the engine has invalidated on 'runaway' — direction taken from break_direction, "
          "the handoff fires", sig is not None and sig.direction == "long")
    P.begin_tick(54.0)
    sig = RW.generate_signal(orb=_ORB(state="WATCHING"), atr_pct=0.14, price_now=100.5,
                             prev_close=100.4, now_et="10:15", chain=_Chain([], calls_rw))
    r54 = _row(st, "RunawayContinuation", 54.0)
    check("R6 ORB not broken -> HOLD, nothing to prepare until it breaks",
          sig is None and r54 and r54[0] == "HOLD" and "nothing to prepare" in r54[1], str(r54))
    P.begin_tick(55.0)
    sig = RW.generate_signal(orb=_ORB(), atr_pct=0.03, price_now=101.9, prev_close=101.6,
                             now_et="10:15", chain=_Chain([], calls_rw))
    r55 = _row(st, "RunawayContinuation", 55.0)
    check("R7 ATR 0.03% (unreachable tape) -> HOLD prepared, waiting on atr_pct — recorded, not silent",
          sig is None and r55 and r55[0] == "HOLD" and "atr_pct" in r55[1], str(r55))
    # ── r174 — the two structural gates from 2026-08-28's tape ───────────
    import strategy.runaway_continuation as rwmod
    # the teenie: floor 20% of 0.17 = 3.4c, spread ask-bid = 4c -> refused
    teenie = _G(107, 0.15, 0.09, 0.022); teenie.ask, teenie.bid = 0.17, 0.13
    P.begin_tick(57.0)
    sig = RW.generate_signal(orb=_ORB(hi=100.0, tp=100.8), atr_pct=0.14, price_now=105.9,
                             prev_close=105.6, now_et="10:15",
                             chain=_Chain([], [teenie]))
    r57 = _row(st, "RunawayContinuation", 57.0)
    check("R9 (r174) the only candidate is a teenie whose 20% floor sits INSIDE its own "
          "bid/ask -> structural DECLINE naming the spread, even on relaxed",
          sig is None and r57 and r57[0] == "DECLINE" and "clears its own bid/ask" in r57[1]
          and "1 rejected for spread" in r57[1], str(r57))
    # same chain plus a real-premium strike: the pick lands there, not the teenie
    real = _G(102, 0.95, 0.46, 0.050)          # floor 19c >> ~4c spread
    P.begin_tick(58.0)
    sig = RW.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.9, prev_close=101.6,
                             now_et="10:15", chain=_Chain([], [real, teenie]))
    check("R10 (r174) with a real-premium strike on the chain the pick lands there — the "
          "spread gate is what keeps the leverage score off the teenies",
          sig is not None and sig.strike == 102.0, str(sig and sig.strike))
    # one runaway per break: a floor stop-out finishes (long, 101.0)
    rwmod.finish_break("long", 101.0)
    P.begin_tick(59.0)
    sig = RW.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.9, prev_close=101.6,
                             now_et="10:15", chain=_Chain([], [real]))
    r59 = _row(st, "RunawayContinuation", 59.0)
    check("R11 (r174) this break already stopped out at its floor -> structural DECLINE: "
          "one runaway per break", sig is None and r59 and r59[0] == "DECLINE"
          and "already stopped out" in r59[1], str(r59))
    P.begin_tick(59.5)
    sig = RW.generate_signal(orb=_ORB(hi=103.0, tp=103.8), atr_pct=0.14, price_now=104.9,
                             prev_close=104.6, now_et="10:15",
                             chain=_Chain([], [_G(106, 0.95, 0.46, 0.050)]))
    check("R12 (r174) a NEW break at a new boundary is a new trade",
          sig is not None, str(sig and sig.strike))
    rwmod.FINISHED_BREAKS.clear()
    src_tl = open(os.path.join(_root, "database", "trade_logger.py"), encoding="utf-8").read()
    check("R13 (r174) the losing-exit hook finishes the break (source pin)",
          "finish_break(_dir, _bnd)" in src_tl and '"Runaway" in _strat' in src_tl)

    os.environ["OT_RELAXED_ENTRY"] = "0"
    P.begin_tick(56.0)
    sig = RW.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.9, prev_close=101.6,
                             now_et="11:45", chain=_Chain([], calls_rw))
    r56 = _row(st, "RunawayContinuation", 56.0)
    check("R8 past the 11:30 cutoff (strict) -> DORMANT", sig is None and r56 and r56[0] == "DORMANT", str(r56))
    # ── r176 — THE DEBIT CUTOFF DOES NOT RELAX (operator, 2026-08-29:
    # "Debit entries are finished at 1130, period … We are burning theta").
    # Dormant rows DEDUPE, so the pin is behavioural: relaxed at 11:45
    # produces no signal and no new TAKE/HOLD row.
    os.environ["OT_RELAXED_ENTRY"] = "1"
    P.begin_tick(56.5)
    sig = RW.generate_signal(orb=_ORB(), atr_pct=0.14, price_now=101.9, prev_close=101.6,
                             now_et="11:45", chain=_Chain([], [_G(102, 0.95, 0.46, 0.050)]))
    r565 = _row(st, "RunawayContinuation", 56.5)
    check("R14 (r176) 11:45 UNDER RELAXED -> still dormant: no signal, no TAKE/HOLD row",
          sig is None and (r565 is None or r565[0] == "DORMANT"), str(r565))
    src_rw = open(os.path.join(_root, "strategy", "runaway_continuation.py"), encoding="utf-8").read()
    check("R14b (r176) the relaxed 14:00 extension is gone from the source",
          'relaxed.window("00:00", CUTOFF_ET' not in src_rw and "_cut = CUTOFF_ET" in src_rw)
    os.environ["OT_RELAXED_ENTRY"] = "0"

    # ── r175 — TCS POP WITH THE SESSION'S MEASURED DRIFT ─────────────────
    # Operator: "You have to get it firing in ESPECIALLY this type of day …
    # A trend day we should be killing it & on chop we stay out."
    import strategy.credit_vertical as cvm
    # today's MU shape at 12:15: strike 3.2 under spot, 5m ATR 2.7, 45 bars to
    # the 15:45 flatten. Driftless read 0.57 and refused the trend all session.
    _p0 = cvm.pop(3.2, 2.7, 45)
    check("T1 (r175) driftless on the MU shape reads ~0.57 — the refusal that held TCS out",
          abs(_p0 - 0.57) < 0.02, f"{_p0:.3f}")
    # the session's measured drift: MU opened ~909, printed ~943 at bar 58 ->
    # ~0.59/5m bar. Two-hour horizon (24 bars).
    _p1 = cvm.pop_drift(3.2, 2.7, 45, 0.59, 24)
    check("T2 (r175) the SAME shape with the session's measured drift fires: POP > 0.80",
          _p1 > 0.80, f"{_p1:.3f}")
    _p2 = cvm.pop_drift(3.2, 2.7, 45, 0.02, 24)
    check("T3 (r175) chop (mu ~ 0) reduces to the driftless read — stays out",
          abs(_p2 - _p0) < 0.03, f"{_p2:.3f} vs {_p0:.3f}")
    _p3 = cvm.pop_drift(3.2, 2.7, 45, -0.40, 24)
    check("T4 (r175) drift TOWARD the short strike reads WORSE than driftless — a "
          "reversal day is harder, not easier", _p3 < _p0 - 0.10, f"{_p3:.3f}")
    check("T5 (r175) degenerate inputs still read 0.0 — a missing ATR is never safe",
          cvm.pop_drift(3.2, 0.0, 45, 0.59, 24) == 0.0
          and cvm.pop_drift(0.0, 2.7, 45, 0.59, 24) == 0.0)
    _p4 = cvm.pop_drift(3.2, 2.7, 45, 0.59, 0)
    check("T6 (r175) horizon 0 credits no drift at all — the prior is the only lever",
          abs(_p4 - _p0) < 1e-9, f"{_p4:.3f}")
    src_t = open(os.path.join(_root, "strategy", "trend_credit_spread.py"), encoding="utf-8").read()
    check("T7 (r175) TCS measures mu from vol_state's OWN df_5m and signs it by side "
          "(put: +drift, call: -drift)",
          "state.df_5m" in open(os.path.join(_root, "analysis", "volatility_engine.py"),
                                encoding="utf-8").read()
          and 'drift_bar if side == "put" else -drift_bar' in src_t
          and "cv.pop_drift(" in src_t and "TCS_DRIFT_HORIZON_BARS" in src_t)

    # T8 (r176) — mu reads the vote's clock: a V-shape session. Since the
    # open the tape is net FLAT (open 354 -> 354) but the last two hours fell
    # hard; a BULLISH-side put spread must see NEGATIVE drift (worse than
    # driftless), not the flat since-open zero.
    import pandas as pd_t8
    _vshape = [354 + 0.5 * i for i in range(24)] + [365.5 - 0.5 * i for i in range(24)]
    _vfix = _Vol(); _vfix.df_5m = pd_t8.DataFrame({
        "open": _vshape, "close": _vshape,
        "high": [c + 0.1 for c in _vshape], "low": [c - 0.1 for c in _vshape]})
    P.begin_tick(44.0)
    TC.prepare(chain=_Chain(puts_tcs), current_price=354.0,
               trend=_Trend("BULLISH", adx=30.0), ms=None, vol_state=_vfix, macro=None,
               orb_high=351.88, orb_low=349.20, now_et=_noon)
    c44 = st.conn.execute("SELECT value FROM plan_check WHERE strategy='TrendCreditSpread' "
                          "AND ts_epoch=44.0 AND check_name='drift_bar'").fetchone()
    check("T8 (r176) V-shape: net-flat since open but falling for two hours -> drift_bar "
          "NEGATIVE (~-0.5/bar), read over the horizon window, not since the open",
          c44 is not None and c44[0] is not None and -0.6 < c44[0] < -0.35, str(c44))

    # ── r178 — THE TICK AFTER THE TAKE (the 08-28 15:00 stack) ───────────
    import strategy.gex_pin_butterfly as bfmod
    bfmod.GEXPinButterflyStrategy.PLAYED_PINS.clear()
    P.begin_tick(60.0)
    sigB = B.generate_signal(gex=_GEX(), chain=_Chain([], calls_good), **bcommon)
    check("B10 (r178) the pin fires once — the baseline TAKE",
          sigB is not None and getattr(sigB, "pin_strike", None) == 101.0,
          f"pin={sigB and getattr(sigB, 'pin_strike', None)}")
    bfmod.GEXPinButterflyStrategy.mark_pin_played(sigB.pin_strike)
    P.begin_tick(61.0)
    sigB2 = B.generate_signal(gex=_GEX(), chain=_Chain([], calls_good), **bcommon)
    r61b = _row(st, "GEXPinButterfly", 61.0)
    check("B11 (r178) the NEXT TICK with identical conditions -> structural DECLINE "
          "pin_played; no second fly on the same magnet, relaxed does not waive it",
          sigB2 is None and r61b and r61b[0] == "DECLINE" and "already has a butterfly" in r61b[1],
          str(r61b))
    P.begin_tick(62.0)
    sigB3 = B.generate_signal(gex=_GEX(pin=102.0), chain=_Chain([], calls_good), **bcommon)
    check("B12 (r178) the magnet migrates to a NEW pin -> a new trade is allowed to prepare",
          (sigB3 is not None) or (_row(st, "GEXPinButterfly", 62.0)
                                  and _row(st, "GEXPinButterfly", 62.0)[0] in ("HOLD", "TAKE")),
          str(_row(st, "GEXPinButterfly", 62.0)))
    msrc2 = open(os.path.join(_root, "main.py"), encoding="utf-8").read()
    check("B13 (r178) the fire site marks the pin played AFTER execution",
          "mark_pin_played" in msrc2
          and msrc2.index("_execute_entry_signal(bf_sig") < msrc2.index("mark_pin_played"))
    bfmod.GEXPinButterflyStrategy.PLAYED_PINS.clear()

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_plan_prepares: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
