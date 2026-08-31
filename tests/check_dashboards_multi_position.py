#!/usr/bin/env python3
"""tests/check_dashboards_multi_position.py  v1.0
BOTH DASHBOARDS SHOW EVERY OPEN POSITION, AND THE EXPOSURE THEY PRINT IS THE
BOX'S — NOT ONE ROW'S.

v1.0  2026-08-31  r199 — born red at r198: both readers carry
      `ORDER BY entry_time DESC LIMIT 1`.

🔴 THE DEFECT WAS LATENT FOR FOUR DAYS AND BECOMES NORMAL TOMORROW. Before r161
made the butterfly additive, one position per box was TRUE and `LIMIT 1` was
correct. r161 changed the rule and nothing swept the readers. Measured
2026-08-31 on CRM, which held a runaway AND a butterfly and reported one — with
`Contracts: 2 × $100 = $1010.00 at risk` describing the runaway alone while the
butterfly's capital went unmentioned. r197 makes multi-position boxes the norm.

🔑 D3 IS THE CHECK THAT MATTERS, AND IT IS NOT ABOUT ROW COUNT. A dashboard
that lists two positions and still prints one position's exposure recreates
exactly the confusion r121 fixed ("How is 2 contracts at $96 costing me
$800???"), one level up. The summed figure is the number a person acts on.

⚠️ D5 PINS THE SORT. `DESC` put the newest on top and hid the position that had
been running longest — usually the one worth seeing. Oldest first is a
deliberate choice, not an accident of rewriting the query.

Run:  python3 tests/check_dashboards_multi_position.py
"""
import os
import re
import sqlite3
import sys
import tempfile

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

_fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))
    if not cond:
        _fails.append(label)


def main():
    st = open(os.path.join(_root, "status.py"), encoding="utf-8").read()
    qy = open(os.path.join(_root, "query.py"), encoding="utf-8").read()

    # ── D1: the LIMIT 1 is gone from the open-position reads ──────────────
    # ⚠️ Scoped to the OPEN query specifically. `LIMIT 1` is legitimate
    # elsewhere in both files (a single latest row of something else), so a
    # bare search would refuse correct code.
    pat = re.compile(r"status='open'[^\"]*LIMIT 1")
    check("D1 neither dashboard asks for one open position",
          not pat.search(st) and not pat.search(qy),
          "status.py and query.py both carried it")

    # ── D2: both actually fetch all of them ───────────────────────────────
    check("D2 both read every open row",
          "fetchall()" in st and "fetchall()" in qy)

    # ── D3: the exposure printed is the BOX's ─────────────────────────────
    check("D3 status sums total_cost across positions",
          'sum((t.get("total_cost") or 0) for t in _open)' in st,
          "one position's `at risk` line silently was the box's")
    check("D3b query sums deployed across positions",
          'sum((r.get("total_cost") or 0) for r in rows)' in qy)

    # ── D4: the count is visible ──────────────────────────────────────────
    check("D4 both name how many positions are open",
          "OPEN POSITIONS" in st and "OPEN POSITIONS" in qy)

    # ── D5: oldest first, deliberately ────────────────────────────────────
    check("D5 both sort oldest-first, so a long-running position is not hidden",
          "entry_time ASC" in st and "entry_time ASC" in qy)

    # ── D6: EXECUTED — two open rows, both rendered ───────────────────────
    # 🔑 The only check here that runs the code rather than reading it.
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "trades.db")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE trades (trade_id TEXT, strategy TEXT, "
                    "status TEXT, entry_time TEXT, is_butterfly INT, "
                    "total_cost REAL, contracts INT, entry_premium REAL, "
                    "stop_premium REAL, target_premium REAL, "
                    "trail_activation REAL, direction TEXT, option_side TEXT, "
                    "strike REAL, expiry TEXT, current_premium REAL, "
                    "setup_grade TEXT, net_debit REAL, max_profit REAL, "
                    "lower_strike REAL, center_strike REAL, upper_strike REAL)")
        con.execute("INSERT INTO trades VALUES ('bf1','GEXPinButterfly','open',"
                    "'2026-08-31 09:45:00',1,483.0,3,1.61,1.21,0,0,'long',"
                    "'call',950,'2026-09-04',1.71,'UNGRADED',1.61,10.0,"
                    "940,950,960)")
        con.execute("INSERT INTO trades VALUES ('rc1','RunawayContinuation',"
                    "'open','2026-08-31 10:19:00',0,1010.0,2,5.05,4.04,10.10,"
                    "7.58,'long','call',260,'2026-09-04',5.20,'UNGRADED',"
                    "0,0,0,0,0)")
        con.commit()
        con.close()

        import importlib.util as u
        sp = u.spec_from_file_location("_st", os.path.join(_root, "status.py"))
        m = u.module_from_spec(sp)
        try:
            sp.loader.exec_module(m)
            m.DB_PATH = db
            got = m.get_open_trades()
            ids = [r["trade_id"] for r in got]
            check("D6 status.get_open_trades() returns BOTH, oldest first",
                  ids == ["bf1", "rc1"], str(ids))
            check("D6b their summed exposure is $1,493, not $1,010",
                  abs(sum(r["total_cost"] for r in got) - 1493.0) < 1e-6,
                  "the butterfly's capital was the part going unmentioned")
        except Exception as exc:                                # noqa: BLE001
            check("D6 status.py is importable and returns both", False, str(exc))

    print()
    if _fails:
        print(f"FAILED {len(_fails)}: " + ", ".join(_fails))
        return 1
    print("check_dashboards_multi_position: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
