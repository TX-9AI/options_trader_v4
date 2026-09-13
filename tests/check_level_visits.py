#!/usr/bin/env python3
"""
tests/check_level_visits.py  v1.0
v1.0  2026-09-12  r378 / LVL.13 — A TEST IS A VISIT, AND CONTACT IS CONTAINMENT.

🔴 THE DEFECT. `Level.on_closed_bar` decided contact with a HALF-PLANE:
`reached = low <= price + tol` for a low level, `high >= price - tol` for a high
one. Every bar on the FAR SIDE of a level therefore satisfied it, so once price
broke through, every subsequent bar re-counted as a fresh touch AND a fresh
breach — for the rest of the session.

📊 MEASURED ON THE BANKED BOOKS BEFORE IT WAS CHANGED. 45 books, 3 sessions, 15
symbols, 386 level-rows: 67.9% of levels showed ZERO touches and 19.4% showed
more than 100, median 209 for any level that saw one — in a 390-bar session.
Bimodal, because it recorded which SIDE of a line price sat on, not contact.
🔴 THE CASE THAT PROVES IT: AMZN 2026-09-09, PDL 254.75, session HIGH 254.62 —
price never reached the level. One bar came within the 0.51 band; 389 were
entirely below it. The book recorded **389 touches and 389 breaches**.
📊 AND IT WAS WRONG IN BOTH DIRECTIONS. Replaying 2026-09-09's tape through the
corrected counter: 41 level-rows INFLATED, **45 DEFLATED**, 61 equal. Tests fell
9,833 -> 596 (16.5x) and holds 3,353 -> 322, while `AMD Asia High (R1)` went from
a banked 0 to 24 real tests with 15 holds and 216 bars of contact. The deflation
is `reset_for_session`: it hydrates, then merges the caller's seeds, and every
BAKE restarts the process — so a level the mapper had not yet named at first
seeding joins with zero counts against an afternoon `last_bar_ts` that
`feed_frame` will never backfill.

OPERATOR'S RULINGS, 2026-09-12, and this file exists to pin them:
  *"Every 'touch' and retreat is a successful defense."*
  *"Leans on isn't the same as testing it."*

  V1  a level price NEVER REACHES records nothing at all
  V2  a multi-bar LEAN is ONE test, not one per bar
  V3  the outcome is the DEPARTING side — retreat = hold, through = breach
  V4  two visits separated by a departure are TWO tests
  V5  a visit still open at the bell is UNRESOLVED: neither outcome, and
      `last_result` stays EMPTY. Invariant: touches >= holds + breaches
  V6  the DURATION survives separately in `contact_bars`, so the two questions
      stop sharing one number
  V7  containment is SYMMETRIC — a high level and a low level answer the same
      question, so neither branch can drift back into a half-plane
  V8  a level admitted after bars were consumed is PARTIAL, because its session
      counters cannot include them
  V9  HISTORY SEEDS DURABILITY AND NEVER SEEDS AN EVENT — `prior_*` populated
      leaves `last_result`/`last_touch` empty, so a hold from three days ago can
      never fire a trade today
  V10 `defense_rate` is None with no history, NEVER 0.0 — a level with no
      record is not a level that has never held
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
FAILS = []


def check(n, ok, d=""):
    print("  {:<5} {}  {}".format(n, "PASS" if ok else "FAIL", d))
    if not ok:
        FAILS.append(n)


def g(obj, name, default=-1):
    """Read a field that may not exist yet.

    ⚠️ WHY THIS EXISTS RATHER THAN A BARE ATTRIBUTE ACCESS: at HEAD none of the
    r378 fields exist, and a bare access raises — which ABORTS THE RUN at the
    first check and reports a traceback instead of a verdict. A born-red record
    has to SHOW the wrong numbers, and a crash shows nothing and reads like a
    broken test rather than a caught defect. Same lesson as the M1/M1b siting in
    check_land_sh: a check that cannot run cannot report.
    """
    return getattr(obj, name, default)


def main():
    print("check_level_visits — a test is a VISIT and contact is CONTAINMENT")
    try:
        from analysis.liquidity_ledger import (LiquidityLedger, Level,
                                               SCHEMA_VERSION, TOUCH_TOL_PCT)
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  liquidity_ledger did not import: {}".format(exc))
        return 1

    def book(price, kind, name=""):
        led = LiquidityLedger("T")
        led.date = "2026-09-09"
        led.levels = [Level(price, kind, name or ("PDL" if kind == "low" else "PDH"),
                            True, "2026-09-09")]
        return led, led.levels[0]

    # ── V1 — the AMZN case. Ten bars five points BELOW a low level, never
    # within the 0.2 band. Under the half-plane this scored 10 touches and 10
    # breaches; under containment it is silence, which is the truth.
    led, lv = book(100.0, "low")
    for i in range(10):
        led.on_closed_bar(95.0, 94.0, 94.5, ts="t{:02d}".format(i))
    check("V1", (lv.touches, lv.holds, lv.breaches, g(lv, "contact_bars")) == (0, 0, 0, 0),
          "never reached: tests={} holds={} breaches={} bars={}".format(
              lv.touches, lv.holds, lv.breaches, g(lv, "contact_bars")))

    # ── V2/V3/V6 — ten consecutive bars in contact, then price leaves upward.
    # ONE test, ONE defense, and the ten bars survive as duration.
    led, lv = book(100.0, "low")
    for i in range(10):
        led.on_closed_bar(100.6, 99.9, 100.3, ts="l{:02d}".format(i))
    led.on_closed_bar(102.0, 101.0, 101.5, ts="l99")
    check("V2", lv.touches == 1,
          "a 10-bar lean is {} test(s)".format(lv.touches))
    check("V3", (lv.holds, lv.breaches) == (1, 0) and lv.last_result == "hold",
          "departed on the origin side: holds={} breaches={} last={!r}".format(
              lv.holds, lv.breaches, lv.last_result))
    check("V6", g(lv, "contact_bars") == 10 and g(lv, "last_visit_bars") == 10,
          "duration kept separately: contact_bars={} last_visit_bars={}".format(
              g(lv, "contact_bars"), g(lv, "last_visit_bars")))

    # ── V3b — the same shape failing: price leaves through the level.
    led, lv = book(100.0, "low")
    for i in range(3):
        led.on_closed_bar(100.6, 99.9, 100.3, ts="b{}".format(i))
    led.on_closed_bar(98.0, 97.0, 97.5, ts="b99")
    check("V3b", (lv.touches, lv.holds, lv.breaches) == (1, 0, 1)
          and lv.last_result == "breach",
          "departed through: tests={} holds={} breaches={} last={!r}".format(
              lv.touches, lv.holds, lv.breaches, lv.last_result))

    # ── V4 — leave and come back: two tests, two defenses.
    led, lv = book(100.0, "low")
    for i in range(3):
        led.on_closed_bar(100.6, 99.9, 100.3, ts="c{}".format(i))
    led.on_closed_bar(102.0, 101.0, 101.5, ts="c9")
    for i in range(2):
        led.on_closed_bar(100.6, 99.9, 100.3, ts="d{}".format(i))
    led.on_closed_bar(102.0, 101.0, 101.5, ts="d9")
    check("V4", (lv.touches, lv.holds) == (2, 2),
          "two visits: tests={} holds={}".format(lv.touches, lv.holds))

    # ── V5 — still in contact when the tape stops. A test with no outcome is
    # NOT a hold and NOT a breach, and `last_result` must not invent one.
    led, lv = book(100.0, "low")
    for i in range(5):
        led.on_closed_bar(100.6, 99.9, 100.3, ts="e{}".format(i))
    unres = lv.touches - (lv.holds + lv.breaches)
    check("V5", g(lv, "visit_open", False) and unres == 1 and lv.last_result == ""
          and lv.last_touch == "",
          "open at the bell: tests={} holds={} breaches={} unresolved={} "
          "last={!r}".format(lv.touches, lv.holds, lv.breaches, unres,
                             lv.last_result))

    # ── V7 — SYMMETRY. The mirrored tape against a HIGH level must produce the
    # mirrored answer. A half-plane reintroduced on either branch breaks this
    # while leaving the other branch's checks green, which is how the original
    # defect survived: only one direction was ever exercised.
    led_lo, lo = book(100.0, "low")
    led_hi, hi = book(100.0, "high")
    for i in range(4):                       # in contact from below / above
        led_lo.on_closed_bar(100.6, 99.9, 100.3, ts="f{}".format(i))
        led_hi.on_closed_bar(100.1, 99.4, 99.7, ts="f{}".format(i))
    led_lo.on_closed_bar(102.0, 101.0, 101.5, ts="f9")   # retreats up
    led_hi.on_closed_bar(99.0, 98.0, 98.5, ts="f9")      # retreats down
    check("V7", (lo.touches, lo.holds, lo.breaches) == (hi.touches, hi.holds, hi.breaches)
          == (1, 1, 0),
          "low {} vs high {}".format((lo.touches, lo.holds, lo.breaches),
                                     (hi.touches, hi.holds, hi.breaches)))
    # ...and the far-side case mirrors too: price never near the level, both silent
    led_lo2, lo2 = book(100.0, "low")
    led_hi2, hi2 = book(100.0, "high")
    for i in range(6):
        led_lo2.on_closed_bar(95.0, 94.0, 94.5, ts="g{}".format(i))   # far below
        led_hi2.on_closed_bar(106.0, 105.0, 105.5, ts="g{}".format(i))  # far above
    check("V7b", (lo2.touches, lo2.breaches) == (hi2.touches, hi2.breaches) == (0, 0),
          "far side silent both ways: low {} high {}".format(
              (lo2.touches, lo2.breaches), (hi2.touches, hi2.breaches)))

    # ── V8 — a level that joins after bars were consumed says so. Every bake
    # re-seeds, and the box cannot backfill from its own short frame.
    led, _ = book(100.0, "low")
    led.on_closed_bar(100.6, 99.9, 100.3, ts="2026-09-09 10:00:00-04:00")
    led.add_level(120.0, "high", "NY High (R1)", True)
    late = [x for x in led.levels if x.price == 120.0][0]
    early = led.levels[0]
    check("V8", g(late, "partial", None) is True and g(early, "partial", None) is False,
          "late level partial={} original partial={}".format(
              g(late, "partial", None), g(early, "partial", None)))

    # ── V9 — HISTORY IS NOT AN EVENT. A level carrying a full prior record must
    # still open the session with nothing to fire on.
    led, lv = book(100.0, "low")
    try:
        lv.prior_touches, lv.prior_holds, lv.prior_breaches = 31, 24, 7
        lv.prior_sessions = 18
    except AttributeError:
        pass            # the fields do not exist yet; V9/V10 report that
    check("V9", lv.last_result == "" and lv.last_touch == ""
          and lv.touches == 0 and lv.holds == 0,
          "prior tests={} holds={} sessions={} -> last_result={!r} touches={}".format(
              g(lv, "prior_touches"), g(lv, "prior_holds"), g(lv, "prior_sessions"),
              lv.last_result, lv.touches))

    # ── V10 — no history is not a failed history.
    _, fresh = book(100.0, "low")
    _dr_fresh = fresh.defense_rate() if hasattr(fresh, "defense_rate") else "NO METHOD"
    _dr_hist = lv.defense_rate() if hasattr(lv, "defense_rate") else None
    check("V10", _dr_fresh is None and _dr_hist is not None
          and abs(_dr_hist - 24.0 / 31.0) < 1e-9,
          "no history -> {!r}; with history -> {!r}".format(_dr_fresh, _dr_hist))

    # ── V11 — the schema refuses an old-semantics book. `touches` answered a
    # different question under v1, so hydrating one would import bar counts as
    # test counts. LIQ.7's precedent for a changed `touch_tol_pct`.
    check("V11", SCHEMA_VERSION >= 2,
          "SCHEMA_VERSION={} (must have moved off 1 with the meaning)".format(
              SCHEMA_VERSION))
    check("V11b", TOUCH_TOL_PCT > 0,
          "the tolerance band is real: {}".format(TOUCH_TOL_PCT))

    print()
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
