#!/usr/bin/env python3
"""
tests/check_sweep_event.py  v1.0
v1.0  2026-09-12  r378 / LVL.14 — A TINE CONTACT IS AN EVENT WITH A CLOSE, AND
      ONE INTERACTION BUYS ONE ENTRY.

OPERATOR'S RULING, 2026-09-12: *"for the 1-hr fork, allow ANY contact with a tine
to trigger if it results in a 1-min candle close back inside the channel on the
1-min candle where the contact occurred."*

🔴 WHAT WAS WRONG, AND IT WAS NOT THE THRESHOLDS. The sweep had NO interaction
identity. `_spent_key` is `(symbol, side, round(pool, 2))` — THE LEVEL — and
`mark_spent` is called from one site, `trade_logger`, inside
`if float(pnl_usd or 0.0) < 0`. So the lock armed only on a LOSS and a WINNING
sweep left the same touch live for the next tick. That is RUN.1's shape on a
second strategy. And since r163 a tine event was born `reclaimed=True` — *"the
TOUCH is the trigger"* — so the condition §36 calls FOUNDATIONAL for this setup
was VACUOUS on the tine path for fourteen revisions.
⚠️ "ANY CONTACT" IS A TIGHTENING, NOT A LOOSENING. Every tine event must now
survive a close it never had to survive before. What goes is the DEPTH BAND, and
it goes because it was a SELECTION preference standing in for a missing reclaim.
⚠️ AND IT IS WHY THE EVENT IS COUNTABLE. The old scan answered *"is price near
the rail somewhere in the last 30 bars"* — a STATE, true every tick until the
window slid, with no instant to name. A p25 fit on 38,834 `plan_check` rows
collapsed to 637 distinct events once deduped, and was withdrawn. The population
was not badly sampled; the event did not exist.

  E1  contact + a SAME-BAR close back inside the channel IS an event, and
      `event_ts` is that bar's stamp
  E2  contact whose own bar closes OUTSIDE the channel is NOT an event
  E3  a reclaim on a LATER bar is NOT an event — the ruling says that bar
  E4  the FORMING bar can never be the event; it has no close to judge
  E5  no far rail -> no event. The channel question is unanswerable and an
      unanswerable test must never read as satisfied
  E6  the latch is PER INTERACTION: the same event fires once...
  E7  ...and a NEW interaction on the same level RE-ARMS
  E8  an unstamped event is NEVER latched — collapsing identity-less events onto
      one key would make the first lock out every later one, silently
  E9  the key is stable against the sub-cent drift the pool price has every tick
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
FAILS = []


def check(n, ok, d=""):
    print("  {:<4} {}  {}".format(n, "PASS" if ok else "FAIL", d))
    if not ok:
        FAILS.append(n)


class _TS:
    def __init__(self, t): self._t = t
    def timestamp(self): return self._t


class _Col(list):
    def astype(self, _): return self
    def tolist(self): return list(self)


class _DF:
    """The frame `_detect_touch` reads, and nothing more."""
    def __init__(self, rows, t0=1_700_000_000.0):
        self._d = {"high": _Col([r[0] for r in rows]),
                   "low": _Col([r[1] for r in rows]),
                   "close": _Col([r[2] for r in rows])}
        self.index = [_TS(t0 + 60.0 * i) for i in range(len(rows))]

    def __len__(self): return len(self.index)

    def __getitem__(self, k): return self._d[k]

    def tail(self, _n): return self


def main():
    print("check_sweep_event — one interaction, identified, and one entry for it")
    try:
        from analysis.liquidity_mapper import LiquidityPool, _detect_touch
        import strategy.sweep_credit_spread as SCS
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  import failed: {}".format(exc))
        return 1

    T0 = 1_700_000_000.0

    def tine(rows, opp=90.0):
        """An upper tine at 100.0, flat, with its far rail at `opp`."""
        df = _DF(rows, T0)
        p = LiquidityPool(price=100.0, kind="high", name="1h upper tine",
                          timeframe="1h")
        p.moving = True
        p.slope_per_min = 0.0
        p.as_of = T0 + 60.0 * (len(rows) - 1)
        try:
            p.opp_price = opp
            p.opp_slope_per_min = 0.0
        except Exception:                                       # noqa: BLE001
            pass          # the fields do not exist at HEAD; E5 reports that
        return p, df

    QUIET = (99.0, 98.0, 98.5)

    # ── E1 — the event. Bar 4 is the newest CLOSED bar (bar 5 is forming): it
    # reaches the rail at 100.5 and closes at 99.5, back between 90 and 100.
    rows = [QUIET] * 4 + [(100.5, 99.0, 99.5), QUIET]
    p, df = tine(rows)
    ev = _detect_touch(p, df, p.as_of)
    want_ts = T0 + 60.0 * 4
    check("E1", ev is not None and abs(float(getattr(ev, "event_ts", 0.0)) - want_ts) < 1e-6
          and ev.bar_index == 4 and ev.reclaim_bar_index == 4,
          "event_ts={} (want {}) bar={} reclaim_bar={}".format(
              getattr(ev, "event_ts", "MISSING"), want_ts,
              ev and ev.bar_index, ev and ev.reclaim_bar_index)
          if ev is not None else "NO EVENT on a tape built to contain one")

    # ── E2 — the same contact, taken NOWHERE. Bar 4 closes at 100.4, above the
    # rail: price did not come back inside on its own bar, so there is no
    # interaction. At HEAD this emitted an event on the contact alone.
    rows = [QUIET] * 4 + [(100.5, 99.0, 100.4), QUIET]
    p, df = tine(rows)
    check("E2", _detect_touch(p, df, p.as_of) is None,
          "a contact closing outside the channel yields no event")

    # ── E3 — THE SAME-BAR RULE. Bar 3 contacts and closes outside; bar 4 closes
    # back inside but never reaches the rail. Two halves of an interaction on two
    # different bars is not the interaction the operator described.
    rows = [QUIET] * 3 + [(100.5, 99.0, 100.4), (99.0, 98.0, 99.5), QUIET]
    p, df = tine(rows)
    check("E3", _detect_touch(p, df, p.as_of) is None,
          "a reclaim on a LATER bar is not the event")

    # ── E4 — the FORMING bar. The only contact is the last row, which has no
    # close yet. `liquidity_ledger.feed_frame` owns this rule for the project:
    # *"the LAST row is the forming bar and is never fed."*
    rows = [QUIET] * 5 + [(100.5, 99.0, 99.5)]
    p, df = tine(rows)
    check("E4", _detect_touch(p, df, p.as_of) is None,
          "the forming bar cannot be the event")

    # ── E5 — NO CHANNEL, NO EVENT. The E1 tape with no far rail.
    rows = [QUIET] * 4 + [(100.5, 99.0, 99.5), QUIET]
    p, df = tine(rows, opp=0.0)
    check("E5", _detect_touch(p, df, p.as_of) is None,
          "an unanswerable channel never fires")

    # ── E6/E7 — THE LATCH. Keyed on the interaction, not the level.
    for fn in ("event_key", "mark_event_fired_key", "is_event_fired"):
        if not hasattr(SCS, fn):
            check("E6", False, "sweep_credit_spread has no {}".format(fn))
            break
    else:
        SCS._FIRED.clear()
        SCS._FIRED_DAY = ""
        k1 = SCS.event_key("TST", "call", 100.0, want_ts)
        SCS.mark_event_fired_key(k1, "filled 1 @ 0.60")
        fired1, why1 = SCS.is_event_fired("TST", "call", 100.0, want_ts)
        check("E6", fired1 and why1, "same interaction latched: {}".format(why1))
        # a NEW bar on the SAME level is a NEW interaction and must re-arm. This
        # is the half that matters: before r378 only a LOSS armed anything, so a
        # winning exit left the same touch live — and a latch that never released
        # would be the opposite defect, refusing every later test of a level.
        fired2, _ = SCS.is_event_fired("TST", "call", 100.0, want_ts + 60.0)
        check("E7", not fired2, "a later interaction on the same level re-arms")
        # and the same interaction on the OTHER side is not this one
        fired3, _ = SCS.is_event_fired("TST", "put", 100.0, want_ts)
        check("E7b", not fired3, "the other side is a different interaction")

        # ── E8 — an unstamped event is never latched.
        SCS._FIRED.clear()
        k0 = SCS.event_key("TST", "call", 100.0, 0.0)
        SCS.mark_event_fired_key(k0, "no stamp")
        fired0, _ = SCS.is_event_fired("TST", "call", 100.0, 0.0)
        check("E8", not fired0 and k0 not in SCS._FIRED,
              "an event with no identity is not latched ({})".format(k0))

        # ── E9 — the key survives the sub-cent drift a recomputed pool has every
        # tick. `_spent_key` rounds to the cent for exactly this reason: an
        # exact float would never match itself and the latch would be dead,
        # which looks identical to a latch with nothing to catch.
        ka = SCS.event_key("TST", "call", 100.00000001, want_ts)
        kb = SCS.event_key("TST", "call", 100.00000009, want_ts)
        kc = SCS.event_key("TST", "call", 100.02, want_ts)
        check("E9", ka == kb and ka != kc,
              "cent-rounded: {} == {} != {}".format(ka, kb, kc))

    print()
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
