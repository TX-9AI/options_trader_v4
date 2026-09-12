#!/usr/bin/env python3
"""
tests/check_level_board.py  v1.0
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
"""
import ast, os, sys, time
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
    def __init__(self, rows): self.conn = _Conn(rows)
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
    eng2 = LevelEngine(store=_Store(rows), symbol="TEST", forks=_FE(_Fork()))
    b2 = eng2.board(100.0, orb_high=101.0, orb_low=99.0, limit=3)
    t = {x["provenance"]: x for x in b2["tines"]}
    up, lo = t.get("fork1h/upper"), t.get("fork1h/lower")
    check("M6", b2["fork"] == "built" and up and lo
               and up["bars_to_contact"] == 20.0        # 10 away, closing 0.5/bar
               and lo["bars_to_contact"] is None        # below and falling: diverging
               and up["slope_per_bar"] == -0.5,
          "upper bars={} lower bars={}".format(
              up.get("bars_to_contact") if up else "?", lo.get("bars_to_contact") if lo else "?"))
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
