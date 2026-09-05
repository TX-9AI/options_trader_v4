#!/usr/bin/env python3
"""tests/check_shadow_velocity.py — v1.0
v1.0  2026-09-05 — r268. VELOCITY SURVIVES A RESTART, AND SAYS WHERE IT CAME
FROM.

🔴 THE FAILURE THIS CLOSES. `TickAccumulator` is LIVE-ONLY: `add()` runs from
inside `one_tick`, so every tick before the process existed is gone. With
`Restart=always` and `RestartSec=30`, a reboot at 10:00 or the fourth pass of a
crash loop enters RTH with an empty deque and emits `typical_roc: null` for the
next five minutes — `MIN_TYPICAL_SAMPLES = 20` at the fleet's poll interval.

⚠️ AND A NULL VELOCITY IS INDISTINGUISHABLE FROM A QUIET TAPE. That is the same
silent-empty shape that let seven weeks of stage-1 shadow data look like data,
and it would land in the corpus the operator intends to FIT TRIGGERS ON.

🔑 TWO THINGS FIX IT AND BOTH ARE REQUIRED. Recovery — seed the ROC deque from
the 1m closes `one_tick` already holds, which are backfilled from the session
open, so recovery is independent of WHEN the process started. And provenance —
every record says `warming`, `seeded` or `live`, because a seeded baseline is
built from MINUTE-to-minute moves while live samples are poll-interval moves,
and the two are on different scales. The record states which; the fit decides.
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        FAILED.append(name)


def main():
    try:
        from shadow.primitives import (MIN_TYPICAL_SAMPLES, TYPICAL_LOOKBACK_S,
                                       TickAccumulator)
    except Exception as exc:                                    # noqa: BLE001
        check("V0 shadow.primitives imports", False, f"{exc}")
        print("\nRED — 1 failed: V0")
        return 1
    if not hasattr(TickAccumulator(), "seed_from_closes"):
        check("V0 TickAccumulator exposes the r268 recovery surface", False,
              "absent — r268 has not landed in this checkout")
        print("\nRED — 1 failed: V0")
        return 1
    check("V0 TickAccumulator exposes the r268 recovery surface", True)

    T0 = 1_757_000_000.0

    # ══ 🔴 V1 — A COLD ACCUMULATOR IS `warming`, NOT SILENT ═══════════════
    a = TickAccumulator()
    check("V1 a cold accumulator reports `warming`, not a null that reads as "
          "a quiet tape",
          a.velocity_state(T0) == "warming", a.velocity_state(T0))
    check("V1b ...and typical_roc really is null there",
          a.typical_roc(T0) is None)

    # ══ V2 — RECOVERY FROM THE 1m CLOSES ═════════════════════════════════
    # This is the reboot / crash-loop path. The bars are what `one_tick`
    # already holds; recovery must not depend on when the process started.
    bars = [(T0 - 60 * (30 - i), 100.0 + i * 0.05) for i in range(30)]
    n = a.seed_from_closes(bars)
    check("V2 seeding from 1m closes fills the ROC history",
          n >= MIN_TYPICAL_SAMPLES, f"{n} sample(s)")
    check("V2b ...so velocity is available immediately after a restart",
          a.typical_roc(T0) is not None, str(a.typical_roc(T0)))

    # ══ 🔴 V3 — AND IT SAYS THE BASELINE IS SEEDED ═══════════════════════
    # A seeded typical is a median of MINUTE moves; live samples are
    # poll-interval moves. Reporting `live` here would hand the fit a baseline
    # on the wrong scale with nothing to indicate it.
    check("V3 a seeded baseline reports `seeded`, never `live`",
          a.velocity_state(T0) == "seeded", a.velocity_state(T0))
    # ⚠️ AND IT STAYS SEEDED UNTIL THE LOOKBACK ROLLS CLEAR. `typical_roc` is a
    # median over TYPICAL_LOOKBACK_S, so one seeded sample still inside that
    # window still moves the denominator — it is not "live" the moment the
    # next live tick lands.
    # ⚠️ RE-DERIVED. The first cut asked at `T0 + LOOKBACK - 60`, by which
    # point the seeded bars have aged OUT of the window and the honest answer
    # is `warming` — too few samples, which the code got right and the case got
    # wrong. The property that matters is that it stays `seeded` while those
    # samples are still IN the window and still moving the median.
    check("V3b ...and stays seeded while the seeded samples are still inside "
          "the lookback window",
          a.velocity_state(T0 + 300) == "seeded", a.velocity_state(T0 + 300))
    # 🔑 AND ONCE THEY HAVE ROLLED CLEAR IT MUST NOT CLAIM `seeded` ANY MORE.
    # With nothing left in the window the truthful answer is `warming` — which
    # is the point: three states, and each one means exactly itself.
    check("V3c ...and never still claims `seeded` after they roll clear",
          a.velocity_state(T0 + TYPICAL_LOOKBACK_S + 120) != "seeded",
          a.velocity_state(T0 + TYPICAL_LOOKBACK_S + 120))

    # ══ V4 — A PURELY LIVE ACCUMULATOR IS NEVER MISLABELLED ══════════════
    b = TickAccumulator()
    t = T0
    for i in range(MIN_TYPICAL_SAMPLES + 6):
        t += 15
        b.add(t, 100.0 + (i % 3) * 0.02, "2026-09-08T09:31")
    check("V4 an accumulator fed only by ticks reports `live`",
          b.velocity_state(t) == "live", b.velocity_state(t))

    # ══ V5 — THE SEED IS ROBUST TO THE DATA IT WILL ACTUALLY MEET ════════
    # ⚠️ A zero or non-numeric close must not raise inside a tick: the handler
    # in the observer logs a failed tick at WARNING and continues, so an
    # exception here costs the whole record and looks like a quiet tape again.
    c = TickAccumulator()
    dirty = [(T0, 0.0), (T0 + 60, None), (T0 + 120, "x"), (T0 + 180, 101.0),
             (T0 + 240, 101.5)]
    try:
        c.seed_from_closes(dirty)
        check("V5 a seed containing zero/None/garbage closes does not raise",
              True)
    except Exception as exc:                                    # noqa: BLE001
        check("V5 a seed containing zero/None/garbage closes does not raise",
              False, f"{type(exc).__name__}: {exc}")

    print()
    if FAILED:
        print(f"RED — {len(FAILED)} failed: {', '.join(FAILED)}")
        return 1
    print("GREEN — 10 checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
