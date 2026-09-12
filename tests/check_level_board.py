#!/usr/bin/env python3
"""
tests/check_level_board.py  v1.1
v1.1  2026-09-12  r376 / LVL.6 — M6 RE-DERIVED, M8-M11 ADDED. M6 fed a fake
      ForkEngine and asserted the board priced its tines from it, which
      CERTIFIED the builder the operator ruled out of the decision path — the
      same shape as the fixtures r234 records certifying the defects they were
      meant to catch. The arithmetic is unchanged; the source moved.
v1.0  2026-09-12  r364 / LVL.3 — ONE LEVEL MAP, READ FROM THE LEDGER.

🔴 THE OPERATOR'S SPECIFICATION, 2026-09-12: *"3 previously held levels above,
three previously held levels below and the one hour fork tines, if present...
Nothing in memory and all of them correctly organized by their geometry,
including the pitchfork and invalidating any level that sits within the opening
range."*
⚠️ AND THE TINE RULE THAT COMES WITH IT: *"if the fork stops emitting, then the
map has to go with it... out of sight, out of mind."* A tine is computed at read
time from the live fork, never stored, so a dead structure cannot be served as a
live rail one tick later.

  M1  a board exists and is referenced to the OPENING RANGE, not to spot
  M2  before the range exists the board says `no_range` — not an empty board,
      because silence must never read as clearance
  M3  three above the range high and three below the range low, ordered
      outward, and VWAP (`dynamic`) is not among them
  M4  fewer than three is REPORTED, never padded
  M5  no fork -> no tines, and the board says `fork: absent`
  M6  a fork -> each tine carries price, slope and bars_to_contact, and a tine
      that is diverging reports None rather than a negative time
  M7  main.py actually asks for the board every tick
  M8  the tines come from the OBSERVER, driven — the ForkEngine stub is left
      wired and returns different prices, so the two sources are told apart
  M9  the geometric role is ABSOLUTE: a top tine is resistance even with price
      above it, which is the one case a role-by-position rule would flip
  M10 a dead fork yields no tines through the new source too
  M11 the docstring no longer cites a lifecycle module nothing runs (PF.4)
"""
import ast, os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
FAILS = []
def check(n, ok, d=""):
    print("  {:<4} {}  {}".format(n, "PASS" if ok else "FAIL", d))
    if not ok: FAILS.append(n)

class _Row(tuple): pass
class _Conn:
    def __init__(self, rows): self.rows = rows
    def execute(self, sql, args): 
        assert "kind IN ('support','resistance')" in sql, "board must exclude dynamic in SQL"
        return self
    def fetchall(self): return self.rows
class _Store:
    def __init__(self, rows): self.conn = _Conn(rows); self.written = []
    def upsert_level(self, row): self.written.append(row)
class _Fork:
    slope = -0.5
    def upper_at(self, i): return 110.0
    def median_at(self, i): return 105.0
    def lower_at(self, i): return 95.0
class _FE:
    def __init__(self, fork): 
        self.last_forks = {"1h": fork} if fork else {}
        self.last_idx = {"1h": 10.0}

def main():
    try:
        from derived.levels import LevelEngine
    except Exception as exc:                                     # noqa: BLE001
        print("  FAIL  derived.levels did not import: {}".format(exc)); return 1
    if not hasattr(LevelEngine, "board"):
        print("  FAIL  LevelEngine.board() does not exist — there is no one map")
        return 1
    rows = [(112.0, "resistance", "PDH (R1)", 3, 0), (118.0, "resistance", "NY High (R2)", 1, 0),
            (125.0, "resistance", "PDH (R3)", 2, 0), (130.0, "resistance", "PDH (R4)", 1, 0),
            (95.0, "support", "PDL (R1)", 4, 0), (88.0, "support", "London Low (R1)", 2, 0)]
    eng = LevelEngine(store=_Store(rows), symbol="TEST", forks=_FE(None))
    b = eng.board(100.0, orb_high=101.0, orb_low=99.0, limit=3)
    check("M1", b.get("state") == "ok" and b["above"] and b["below"],
          "state={} above={} below={}".format(b.get("state"), len(b["above"]), len(b["below"])))
    nr = eng.board(100.0, orb_high=None, orb_low=None)
    check("M2", nr.get("state") == "no_range" and not nr["above"],
          "state={}".format(nr.get("state")))
    provs = [r["provenance"] for r in b["above"]]
    check("M3", provs == ["PDH (R1)", "NY High (R2)", "PDH (R3)"]
               and all(r["kind"] in ("support", "resistance") for r in b["above"] + b["below"]),
          "above (outward): {}".format(provs))
    check("M4", b["count"]["below"] == 2 and len(b["below"]) == 2,
          "only two levels exist below; board reports {}".format(b["count"]["below"]))
    check("M5", b["fork"] == "absent" and b["tines"] == [],
          "fork={} tines={}".format(b["fork"], len(b["tines"])))
    # 🔴 M6 RE-DERIVED ONTO THE OBSERVER (r376 / LVL.6). It used to feed a fake
    # ForkEngine and assert the board priced tines from it — which certified
    # the builder the operator ruled OUT of the decision path. The arithmetic
    # it checked is unchanged and still checked; only the source moved.
    eng2 = LevelEngine(store=_Store(rows), symbol="TEST", forks=_FE(_Fork()))
    eng2._obs_rails = {"upper": 110.0, "median": 105.0, "lower": 95.0,
                       "slope": -0.5, "tf": "1h"}
    b2 = eng2.board(100.0, orb_high=101.0, orb_low=99.0, limit=3)
    t = {x["provenance"]: x for x in b2["tines"]}
    up, lo = t.get("fork1h/upper"), t.get("fork1h/lower")
    check("M6", b2["fork"] == "built" and up and lo
               and up["bars_to_contact"] == 20.0        # 10 away, closing 0.5/bar
               and lo["bars_to_contact"] is None        # below and falling: diverging
               and up["slope_per_bar"] == -0.5,
          "upper bars={} lower bars={}".format(
              up.get("bars_to_contact") if up else "?", lo.get("bars_to_contact") if lo else "?"))

    # ══ M8 — THE SOURCE IS THE OBSERVER, AND IT IS DRIVEN ════════════════
    # §21: asserting the import appears would pass against an import that is
    # never reached. `derive()` is run for real with `rails_for` replaced, and
    # the board must then price its tines from what the OBSERVER returned.
    # ⚠️ THE FORKENGINE STUB IS DELIBERATELY LEFT WIRED AND RETURNS DIFFERENT
    # PRICES, so a board still reading it produces 110/95 and fails on value
    # rather than on absence — the two sources are told apart, not merely one
    # of them present.
    import analysis.pitchfork_observer as _obs
    _saved = _obs.rails_for
    _obs.rails_for = lambda ctx, sym, tf="1d": (
        {"upper": 210.0, "median": 205.0, "lower": 195.0, "slope": -0.5, "tf": tf}
        if tf == "1h" else None)
    try:
        eng3 = LevelEngine(store=_Store(rows), symbol="TEST", forks=_FE(_Fork()))
        eng3.derive({"symbol": "TEST", "price": 200.0})
        b3 = eng3.board(200.0, orb_high=101.0, orb_low=99.0, limit=3)
        t3 = {x["provenance"]: x for x in b3["tines"]}
        got = (t3.get("fork1h/upper") or {}).get("price")
        check("M8", got == 210.0,
              "tine priced from the observer (210.0), got {} "
              "— 110.0 would mean it is still reading ForkEngine".format(got))

        # M9 — THE GEOMETRIC ROLE IS ABSOLUTE. Operator, 2026-09-12: *"the
        # pitchfork tines have geometric restrictions on S/R — a top tine can
        # NEVER be support."* Price is ABOVE the upper rail here, the one case
        # where a role-by-position rule would flip it to support.
        _obs.rails_for = lambda ctx, sym, tf="1d": (
            {"upper": 100.0, "median": 95.0, "lower": 90.0, "slope": 0.1, "tf": tf}
            if tf == "1h" else None)
        eng4 = LevelEngine(store=_Store(rows), symbol="TEST", forks=_FE(None))
        eng4.derive({"symbol": "TEST", "price": 150.0})     # price ABOVE the top rail
        t4 = {x["provenance"]: x for x in eng4.tines_now(150.0)}
        check("M9", (t4.get("fork1h/upper") or {}).get("kind") == "resistance"
                   and (t4.get("fork1h/lower") or {}).get("kind") == "support",
              "price 150 above the 100 upper rail: upper={} lower={}".format(
                  (t4.get("fork1h/upper") or {}).get("kind"),
                  (t4.get("fork1h/lower") or {}).get("kind")))

        # M10 — A DEAD FORK YIELDS NOTHING, THROUGH THE NEW SOURCE TOO.
        _obs.rails_for = lambda ctx, sym, tf="1d": None
        eng5 = LevelEngine(store=_Store(rows), symbol="TEST", forks=_FE(_Fork()))
        eng5.derive({"symbol": "TEST", "price": 100.0})
        b5 = eng5.board(100.0, orb_high=101.0, orb_low=99.0, limit=3)
        check("M10", b5["fork"] == "absent" and b5["tines"] == [],
              "observer returns None -> fork={} tines={}".format(
                  b5["fork"], len(b5["tines"])))
    finally:
        _obs.rails_for = _saved

    # ══ M11 — PF.4, AND ITS FIRST CUT WAS §20 FOR THE FOURTH TIME TODAY ══
    # 🔴 It asserted the SENTENCE was absent — and r376's correction has to
    # QUOTE the false claim in order to retract it, so the canary tripped on
    # the retraction. Rule 5 requires the changelog name what it removed;
    # §20 says the canary is then wrong, never the prose.
    # 🔑 SO IT IS TWO DEFINITION-SHAPED ASSERTIONS INSTEAD OF A TEXT SEARCH:
    # the module is not IMPORTED (§20's own prescribed form for imports — an
    # import cannot be quoted into existence by a docstring), and the
    # correction is PRESENT, which is a positive check no amount of prose can
    # falsely satisfy. What was wrong was a claim of a live guarantee; what is
    # right is no import and an explicit acknowledgement that none exists.
    lv = open(os.path.join(REPO, "derived", "levels.py"), encoding="utf-8").read()
    imported = any(l.strip().startswith(("from analysis.pitchfork_lifecycle",
                                         "import analysis.pitchfork_lifecycle"))
                   for l in lv.splitlines())
    check("M11", not imported and "PF.4" in lv and "imported by NOTHING" in lv,
          "imported={} correction_present={}".format(imported, "PF.4" in lv))

    src = open(os.path.join(REPO, "main.py"), encoding="utf-8").read()
    called = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr == "board" for n in ast.walk(ast.parse(src)))
    check("M7", called, "main.py calls .board() on the levels engine")
    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS))); return 1
    print("ALL PASS (7)"); return 0

if __name__ == "__main__":
    sys.exit(main())
