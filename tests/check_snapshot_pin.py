#!/usr/bin/env python3
"""
tests/check_snapshot_pin.py  v1.2
v1.2  2026-09-19  CHK.4 CORRECTED — S2 WAS RED AS A FUNCTION OF THE WALL CLOCK.
      S2 compares `pin_em_fraction` from `build_payload()` against its own
      recomputation at a 1e-9 tolerance. Both sides call
      `gex_pin_butterfly.expected_move`, which reads `datetime.now(ET)` ITSELF
      and scales by sqrt(hours-to-close) -- so the two reads land at different
      instants and the values differ continuously through the session.
      MEASURED 2026-09-19: six consecutive runs drifted 2.208372 -> 2.208879,
      ~1e-4 per run at ~1s intervals, against a predicted want*0.5/hours =
      9.4e-5/s at 3.25h remaining. The arithmetic matches the tape.
      🔑 AND THE CLAMP IS WHY IT WAS EVER GREEN. `hours = max(..., 0.25)` binds
      from 15:45 ET, after which EM is FROZEN and both reads agree. So this gate
      was GREEN ONLY WHEN THE SUITE RAN AFTER 15:45 ET and red at every other
      hour -- its colour encoded the hour of the run, not the state of the code.
      Every green it ever reported was a late-day sweep.
      ⚠️ CONSEQUENCE BEYOND THIS FILE: a full-sweep baseline is only comparable
      to a build sweep taken on the SAME SIDE of 15:45 ET, and nothing has ever
      recorded a sweep's start time. Until that changes, a sweep must record it.
      🔴 BACKLOG CHK.4 NAMES THE WRONG FUNCTION. It says `expected_move_iv`
      resolves `frac_remaining` via `session_fraction_remaining()` and proposes
      feeding both sides one fraction. S2 CALLS NEITHER. A fix written to that
      row would patch a function this check cannot reach. The SHAPE is right --
      pin the time -- and the parameter is `now=`, which `expected_move` has
      always accepted.
      FIX: freeze the clock around S2 at a MID-SESSION instant, so the check
      exercises the REAL unclamped arithmetic rather than passing vacuously on
      the 0.25 floor. S2c pins that the freeze holds; S2d pins that the
      underlying hazard is real, using two EXPLICIT `now` values so the proof
      does not itself depend on when the suite runs.
      ⚠️ THE 1e-9 TOLERANCE IS NOT LOOSENED. Widening it would hide exactly the
      second-definition drift S2 exists to catch (this file's own v1.0 note).
      Reproduced independently on OTV4TEST at their r60: same function, same
      0.25 floor, same 15:45 boundary to the minute.
v1.1  2026-09-04  r244 — S6 extends to `pin_concentration` and
      `gex_environment` — recorded RAW, kept as distinct keys, and None rather
      than 0.0 or "" when the gex object carries neither.
v1.0  2026-09-04  r243 — THE PIN AND ITS EM FRACTION REACH THE SNAPSHOT.

🔴 WHY. Operator, 2026-09-04, after the stop-removal and window cases both
failed on evidence: *"then that leaves the EM variable as our last hope of
raising our win rate. What is the furthest EM that this trade will fire on?"*
The band is 0.30–1.00 and hard-capped — but whether the SEVEN winners sat lower
in it than the THIRTEEN losers was UNANSWERABLE: `plan_check` carries
`pin_em_fraction` on every tick and has NO trade_id, and `fire_snapshot` is
keyed BY trade_id and carried no pin and no EM.

🔑 SAME SHAPE AS r240 — a field computed, used for a DECISION, and never
written where the OUTCOME could be joined to it. The bridge existed; it just
did not carry the field.

⚠️ NOTHING ACCRUES RETROACTIVELY. The 20 butterflies already banked stay
unmeasurable. This starts the collection.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


class _Gex:
    def __init__(self, pin, conc=None, env=None):
        self.pin_strike = pin
        if conc is not None:
            self.pin_concentration = conc
        if env is not None:
            self.gex_environment = env


class _FrozenClock:
    """Pin `datetime.now()` inside a module's namespace.

    🔴 WHY A FREEZE AND NOT A TOLERANCE. `expected_move` reads the clock itself
    and scales by sqrt(hours-to-close), so two calls a millisecond apart return
    different numbers. S2's whole purpose is that the recomputation uses the
    GATE'S OWN function rather than a second definition -- so the fix cannot be
    to reimplement it with a fixed `now`, and must not be to widen 1e-9, which
    would hide the drift S2 exists to detect.

    ⚠️ MID-SESSION ON PURPOSE. `hours` is floored at 0.25, which binds from
    15:45 ET and freezes EM all by itself. A freeze set after 15:45 would make
    S2 pass for the WRONG REASON -- the clamp, not the fix -- which is the
    failure this whole revision is correcting.
    """

    def __init__(self, mod, hh, mm):
        self.mod, self.hh, self.mm = mod, hh, mm
        self.real = None

    def __enter__(self):
        from utils.time_utils import ET
        real = self.mod.datetime
        fixed = real(2026, 9, 17, self.hh, self.mm, 0, 0, tzinfo=ET)

        class _DT(real):
            @classmethod
            def now(cls, tz=None):
                return fixed

        self.real = real
        self.mod.datetime = _DT
        return fixed

    def __exit__(self, *exc):
        self.mod.datetime = self.real
        return False


def main():
    from derived.snapshot import SnapshotEngine
    from strategy.gex_pin_butterfly import expected_move, EM_MIN_FRAC, EM_MAX_FRAC

    e = SnapshotEngine.__new__(SnapshotEngine)
    e.symbol = "TEST"

    # ══ S1 — THE KEYS ARE ALWAYS PRESENT ══════════════════════════════════
    # ⚠️ This file's own contract: every key is emitted even when null, so a
    # study can tell "measured as absent" from "did not exist in that era".
    p = e.build_payload({"price": 100.0, "atm_iv": 0.30})
    check("S1 pin_strike and pin_em_fraction are always emitted",
          "pin_strike" in p and "pin_em_fraction" in p)
    check("S1b unmeasurable reads None, NEVER 0.0",
          p["pin_strike"] is None and p["pin_em_fraction"] is None,
          f"{p['pin_strike']!r} {p['pin_em_fraction']!r}")

    # ══ S2 — THE FRACTION MATCHES THE GATE'S OWN ARITHMETIC ═══════════════
    # 🔴 THE POINT OF THE WHOLE REVISION. If this reproduced the fraction with
    # a second definition, the study would compare a number the gate never saw
    # against an outcome the gate decided — worse than no field at all.
    price, iv, pin = 100.0, 0.30, 103.0
    import strategy.gex_pin_butterfly as _gpb
    # 12:00 ET — mid-session, so `hours` is ~4.0 and the 0.25 floor does NOT
    # bind. A freeze after 15:45 would pass on the clamp and prove nothing.
    with _FrozenClock(_gpb, 12, 0) as _frozen_at:
        got = e.build_payload({"price": price, "atm_iv": iv, "gex": _Gex(pin)})
        want = abs(pin - price) / expected_move(price, iv)
        check("S2 the fraction equals |pin - spot| / expected_move()",
              abs(got["pin_em_fraction"] - want) < 1e-9,
              f"{got['pin_em_fraction']:.6f} vs {want:.6f}")
        # S2c — THE FREEZE ITSELF IS PINNED. If it ever stops holding, this
        # goes red BY NAME instead of S2 going red mysteriously once a day.
        _a = expected_move(price, iv)
        _b = expected_move(price, iv)
        check("S2c the clock is frozen — two reads are identical",
              _a == _b, f"{_a!r} vs {_b!r}")
        # 🔴 S2d IS LOAD-BEARING. IT IS NOT REDUNDANT WITH S2c. DO NOT DELETE IT.
        # THERE ARE **TWO** WAYS EM CAN GO CONSTANT FOR A REASON THAT IS NOT
        # THE FIX WORKING, AND S2c CANNOT SEE EITHER:
        #   (1) THE CLAMP. `hours = max(..., 0.25)` binds from 15:45 ET, so a
        #       freeze set inside that window makes EM constant by the FLOOR.
        #       Proven: moving the freeze to 16:30 turned all eleven checks
        #       green on a fix that was no longer doing anything.
        #   (2) THE BARE `except Exception: hours = 3.0` IN `expected_move`
        #       (gex_pin_butterfly.py:403). If this harness's `datetime`
        #       subclass mishandles the tz-aware `now(ET)` call in ANY way, the
        #       exception is SWALLOWED, `hours` becomes the constant 3.0, and
        #       EM freezes **for a reason the test harness itself introduced**.
        #       S2 then passes with the arithmetic entirely bypassed.
        #       ⚠️ Raised by the OTV4TEST session's review, and it is the case
        #       my own mutation testing MISSED — I mutated the freeze TIME and
        #       never the function's FAILURE PATH.
        # S2d catches both, because a constant EM cannot move between two
        # instants however it became constant.
        #
        # S2d — THE FREEZE SITS WHERE THE ARITHMETIC IS LIVE.
        # 🔴 S2c ALONE IS NOT ENOUGH. `hours` is floored at 0.25, so a freeze
        # set after 15:45 ET makes EM constant BY THE CLAMP and S2/S2c both pass
        # for the wrong reason — proven by moving the freeze to 16:30, where all
        # eleven checks went green on a fix that was no longer doing anything.
        # ⚠️ SO THE INSTANT IS TAKEN FROM THE FREEZE ITSELF (`_frozen_at`) and
        # never written twice. Move the freeze into the clamped window and EM
        # stops moving, these two values become equal, and THIS check goes red
        # BY NAME rather than the suite going quietly vacuous.
        from datetime import timedelta as _td
        _e0 = expected_move(price, iv, now=_frozen_at)
        _e1 = expected_move(price, iv, now=_frozen_at + _td(milliseconds=1))
        check("S2d the frozen instant is MID-SESSION — EM still moves there",
              _e0 != _e1, f"{_e0!r} vs {_e1!r}")
        # 🔴 S2e — THE FROZEN CLOCK ACTUALLY REACHES THE PRODUCTION PATH.
        # S2d passes `now=` EXPLICITLY, so it never calls `datetime.now()` and
        # therefore CANNOT see the bare-except case: if the harness's clock
        # raises, `expected_move` swallows it, `hours` becomes the constant
        # 3.0, and BOTH sides of S2 get 3.0 and agree. Verified by mutation —
        # making `now()` raise left S2, S2c AND S2d all green on a fix that had
        # stopped working entirely.
        # ⚠️ THIS IS THE CHECK THAT CLOSES IT: `build_payload` computes its
        # fraction through the FROZEN clock, and here it is compared against
        # the fraction computed from the frozen instant passed EXPLICITLY. They
        # agree only if the freeze genuinely reached the production path. If
        # the clock raises, build_payload gets hours=3.0 while the explicit
        # call gets the real remaining hours, and this goes RED by name.
        # 🔑 S2d and S2e catch DIFFERENT failures — the clamp and the swallowed
        # exception — and neither is redundant. Raised by the OTV4TEST review.
        _want_explicit = abs(pin - price) / expected_move(price, iv,
                                                          now=_frozen_at)
        check("S2e the frozen clock REACHES build_payload's own computation",
              abs(got["pin_em_fraction"] - _want_explicit) < 1e-9,
              f"{got['pin_em_fraction']:.6f} vs explicit {_want_explicit:.6f}")
    check("S2b and the pin itself round-trips", got["pin_strike"] == pin)

    # ══ S3 — A PIN AT THE MONEY IS 0.0, NOT None ══════════════════════════
    # ⚠️ The opposite fact from S1b and it must not collapse into it: a pin
    # exactly at spot is a MEASURED zero and belongs in the sample.
    atm = e.build_payload({"price": price, "atm_iv": iv, "gex": _Gex(price)})
    check("S3 a pin AT spot reads 0.0, distinct from unmeasurable",
          atm["pin_em_fraction"] == 0.0, repr(atm["pin_em_fraction"]))

    # ══ S4 — IT NEVER RAISES INTO THE FIRE PATH ═══════════════════════════
    # 🔴 `capture()` runs on every fill. A study field that can throw would
    # cost a trade its snapshot — or worse — for a number nobody needs live.
    for bad in ({"price": None, "atm_iv": 0.3, "gex": _Gex(100.0)},
                {"price": 100.0, "atm_iv": None, "gex": _Gex(100.0)},
                {"price": 100.0, "atm_iv": 0.3, "gex": object()},
                {}):
        try:
            e.build_payload(bad)
        except Exception as exc:                               # noqa: BLE001
            check("S4 build_payload never raises on a degenerate ctx", False,
                  f"{type(exc).__name__}: {exc}")
            break
    else:
        check("S4 build_payload never raises on a degenerate ctx", True)

    # ══ S5 — THE BAND IS STILL HARD-CAPPED ════════════════════════════════
    # ⚠️ r208: `cap=EM_MAX_FRAC` makes the relaxed value equal the base, so the
    # ceiling cannot widen. Recording the fraction must not become a reason to
    # loosen the gate that made it worth recording.
    check("S5 the EM band is unchanged at 0.30-1.00",
          EM_MIN_FRAC == 0.30 and EM_MAX_FRAC == 1.00,
          f"{EM_MIN_FRAC}-{EM_MAX_FRAC}")

    # ══ S6 — ALL THREE PIN MEASURES, NOT JUST THE EM FRACTION ════════════
    # 🔴 r244. `pin_concentration` (29% fail) and the GEX environment behind
    # `pinning` (53% fail) GATE every butterfly fire and NEITHER has ever been
    # tested against an outcome. Instrumenting only the EM fraction would let a
    # study conclude "EM predicts nothing" while the real signal sat in a field
    # nobody recorded.
    full = e.build_payload({"price": price, "atm_iv": iv,
                            "gex": _Gex(pin, conc=0.31, env="PINNING")})
    check("S6 pin_concentration is recorded RAW, not as a pass/fail",
          full["pin_concentration"] == 0.31, repr(full["pin_concentration"]))
    check("S6b the GEX environment is recorded",
          full["gex_environment"] == "PINNING", repr(full["gex_environment"]))
    # ⚠️ THE GATE'S ANSWER IS ALREADY IN plan_check. What was missing is the
    # VALUE — a study cannot fit a boundary it can only see one side of.
    check("S6c a gex object carrying neither yields None, not 0.0 or ''",
          got["pin_concentration"] is None and got["gex_environment"] is None,
          f"{got['pin_concentration']!r} {got['gex_environment']!r}")
    # 🔑 SEPARATELY, NOT COMPOSITED — r224: a composite that separates tells you
    # nothing about WHICH PART did the work.
    check("S6d all four pin fields are distinct keys",
          len({"pin_strike", "pin_em_fraction", "pin_concentration",
               "gex_environment"} & set(full)) == 4)

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 11 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
