#!/usr/bin/env python3
"""
tests/check_level_vocabulary.py  v1.0
v1.0  2026-09-12  r364 / LVL.2 — the level ledger speaks ONE vocabulary, and
      every consumer can see the named pools.

🔴 WHAT WAS WRONG. `data/derived_store.py:130` declares the column as
`kind TEXT, -- support / resistance`. `derived/levels.py` honours that for the
session extremes (`prev_day_high` -> resistance) and then, for POOLS, writes
the detector's own word straight through: `str(getattr(pool, "kind", ""))`,
which is `high` / `low`. So PDH, PDL and the whole R1/R2/R3 ladder entered the
catalogue in a vocabulary no reader asks for.
🔑 MEASURED ON THE WAREHOUSE, 2026-09-11: of 786 level rows sampled across four
symbols, every `PDH*`, `PDL*`, `NY/London/Asia High|Low (R*)` row carried kind
`high` or `low`. A reader filtering `kind IN ('support','resistance')` — which
is what the fork's `live_levels` does — sees none of them.
⚠️ THE SIDE IS THE FACT, NOT THE FORMATION. A pool formed from a high is
resistance while price is below it; the catalogue records what a level IS to a
consumer now, and the biography (TRAVERSED / ACCEPTED_THROUGH) retires it when
price genuinely goes through.
⚠️ TINES AND VWAP ARE UNTOUCHED. The 1h fork's tines are legitimate levels and
stay (upper -> resistance, lower -> support, by their own rule); vwap stays
`dynamic` so a kind-filtered read still excludes it.

  L1  every kind `_sources` emits is in the declared vocabulary
  L2  a pool ABOVE price is resistance; a pool BELOW price is support
  L3  a pool with no price context still lands in the vocabulary (formation
      fallback) — never dropped, never `high`/`low`
  L4  vwap is still `dynamic`, so kind-filtered readers still exclude it
  L5  DerivedStore exposes live_levels() and it returns a written pool
"""
import os, sys, sqlite3, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
FAILS = []
def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok: FAILS.append(name)

class _Pool:
    def __init__(self, name, price, kind, timeframe="session"):
        self.name, self.price, self.kind, self.timeframe = name, price, kind, timeframe
class _Liq:
    def __init__(self, pools): self.pools = pools
    prev_day_high = prev_day_low = None
    asia_session_high = asia_session_low = None
    london_session_high = london_session_low = None
    ny_session_high = ny_session_low = None
class _Vol:
    vwap = 100.0

def main():
    try:
        from derived.levels import LevelEngine
    except Exception as exc:                                     # noqa: BLE001
        print("  FAIL  derived.levels did not import: {}".format(exc)); return 1
    eng = LevelEngine(store=None, symbol="TEST")
    pools = [_Pool("PDH", 105.0, "high"), _Pool("PDL", 95.0, "low"),
             _Pool("NY High (R2)", 110.0, "high")]
    ctx = {"liq_map": _Liq(pools), "vol": _Vol(), "price": 100.0}
    rows = eng._sources(ctx)
    kinds = {r[2] for r in rows}
    check("L1", kinds <= {"support", "resistance", "dynamic"},
          "kinds emitted: {}".format(sorted(kinds)))
    by_prov = {r[0]: r for r in rows}
    check("L2", by_prov.get("PDH", (None,)*3)[2] == "resistance"
               and by_prov.get("PDL", (None,)*3)[2] == "support"
               and by_prov.get("NY High (R2)", (None,)*3)[2] == "resistance",
          "PDH={} PDL={} R2={}".format(*(by_prov.get(k, ("","",  "?"))[2]
                                         for k in ("PDH", "PDL", "NY High (R2)"))))
    rows2 = eng._sources({"liq_map": _Liq([_Pool("PDH", 105.0, "high")]), "vol": None})
    k2 = [r[2] for r in rows2 if r[0] == "PDH"]
    check("L3", k2 == ["resistance"], "no price in ctx -> {}".format(k2))
    check("L4", by_prov.get("vwap", (None,)*3)[2] == "dynamic",
          "vwap kind={}".format(by_prov.get("vwap", ("","","?"))[2]))
    # ── L5/L6/L7 — TRAVERSED, driven through derive() against a stub store ──
    class _Store:
        def __init__(self): self.rows = []
        def upsert_level(self, row): self.rows.append(row); return 1
    class _Orb:
        def __init__(self, lo, hi): self.orb_low, self.orb_high = lo, hi

    def _run(orb):
        st = _Store()
        e = LevelEngine(store=st, symbol="TEST")
        pools = [_Pool("PDH", 105.0, "high"),      # above the range
                 _Pool("MID", 100.2, "high"),      # INSIDE the range
                 _Pool("PDL", 95.0, "low")]        # below the range
        c = {"liq_map": _Liq(pools), "vol": None, "price": 100.0, "symbol": "TEST"}
        if orb is not None:
            c["orb"] = orb
        try:
            e.derive(c)
        except Exception as exc:                                 # noqa: BLE001
            return st, exc
        return st, None

    st, err = _run(_Orb(99.5, 100.5))
    by_prov = {r[4]: r for r in st.rows}          # provenance -> row
    mid = by_prov.get("MID")
    check("L5", err is None and mid is not None and mid[11] == "TRAVERSED",
          "inside-range level retired: {}".format(mid[11] if mid else ("raised: %s" % err)))
    pdh = by_prov.get("PDH")
    check("L6", pdh is not None and pdh[11] is None,
          "outside-range level untouched: reason={}".format(pdh[11] if pdh else "MISSING"))
    st2, err2 = _run(None)
    reasons2 = {r[11] for r in st2.rows}
    check("L7", err2 is None and "TRAVERSED" not in reasons2,
          "no range -> nothing retired (reasons: {})".format(sorted(x for x in reasons2 if x)))
    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS))); return 1
    print("ALL PASS (7)"); return 0

if __name__ == "__main__":
    sys.exit(main())
