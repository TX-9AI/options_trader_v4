#!/usr/bin/env python3
"""
tests/check_butterfly_legs.py  v2.1  (2026-08-28, r170)
v2.1  r170: clock pinned at 12:30 and atm_iv 0.43 (see check_plan_prepares
      v1.6) — the B pins were time-of-day dependent.
v2.0  (2026-08-27, r160)
v2.0  r160: RENAMED from check_leg2_levels.py. The L1-L13 leg-two pins are
      gone with the code they pinned — the condor no longer selects a level;
      tests/check_plan_prepares.py holds the leg-two hypotheticals now. Only
      the butterfly pins (B1-B4, r147) remain.

THE BUTTERFLY HAS LEGS.

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
    # PIN THE CLOCK (see check_plan_prepares): expected_move reads wall time.
    _em_real = bf.expected_move
    from utils.time_utils import ET as _ET
    _fixed_now = bf.datetime(2026, 8, 27, 12, 30, tzinfo=_ET)
    bf.expected_move = lambda u, iv, now=None: _em_real(u, iv, now=_fixed_now)
    b = GEXPinButterflyStrategy()
    b.planner.symbol = "TST"
    os.environ["OT_RELAXED_ENTRY"] = "1"
    P.begin_tick(20.0)
    sig = b.generate_signal(gex=_GEX(), price_now=100.0, now_et="12:30", atm_iv=0.43,
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
    sig2 = b.generate_signal(gex=_GEX(), price_now=100.0, now_et="12:30", atm_iv=0.43,
                             chain=_Chain(calls_fat, []))
    row2 = st.conn.execute("SELECT verdict, reason FROM plan_tick WHERE "
                           "strategy='GEXPinButterfly' AND ts_epoch=21.0").fetchone()
    check("B3 STRICT vetoes a fly below 1:1 (R recorded on the DECLINE row)",
          sig2 is None and row2 and row2[0] == "DECLINE" and "r:" in (row2[1] or ""), str(row2))
    P.begin_tick(22.0)
    sig3 = b.generate_signal(gex=_GEX(), price_now=100.0, now_et="12:30", atm_iv=0.43,
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
