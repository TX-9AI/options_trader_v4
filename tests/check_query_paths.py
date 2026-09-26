#!/usr/bin/env python3
"""tests/check_query_paths.py — v1.0
QUERY.PY READS THE TREE IT LIVES IN, AND A FAILED CONFIG IMPORT IS NEVER SILENT.

v1.0  2026-09-26 — otv4 r449, MIRRORED FROM OTV4TEST r152 (fb34d10). Their file:
      112 lines, sha256 c0b0c571...; its body from `from __future__` to EOF,
      sha256 24b7500e..., is carried here BYTE-IDENTICAL (verified by hash, not by
      eye — r448 exists because a mirror once lost three lines). Only this header
      is ours (WA §38.11 criterion 2). BORN RED on otv4 5800e81 under the dtp venv
      at Q1, Q2, Q3 and Q4; under bare /usr/bin/python3 every case read "did not
      run" (ZoneInfoNotFoundError on "US/Eastern", an environment exit, not a
      verdict) until query.py's ET line took the canonical zone name. Their four
      mutants re-run HERE, both interpreters: ~ INSTALL_DIR -> Q1+Q3, per-call
      insert -> Q2, silent fallback -> Q4, live dir first -> Q1.

  Q1 (a) imported from THIS tree, with a decoy ~/options-trader/config.py present,
         query.INSTALL_DIR is this tree and the config that loaded is this tree's
  Q2 (b) two get_live_price() calls leave sys.path the same length
  Q3 (c) when config cannot import, DB_PATH falls back INSIDE this tree, not ~/options-trader
  Q4 (d) that fallback NAMES what it caught on stderr — and when config imports cleanly,
         nothing is printed and DB_PATH is config's own

🔴 NOTHING REAL IS TOUCHED: every case runs in a child whose HOME is a scratch directory
holding the decoy, and data.market_data is a stub, so no price is fetched and the live
tree is never on the path. Run:  python3 tests/check_query_paths.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBLEMS: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  - {detail}" if detail and not ok else ""))
    if not ok:
        PROBLEMS.append(name.split()[0])


def child(body: str, home: str) -> tuple:
    """Run `body` in a child that imports query from ROOT; its last stdout line is JSON."""
    code = ("import sys, json, types\n"
            f"sys.path.insert(0, {ROOT!r})\n" + body)
    env = dict(os.environ, HOME=home, OT_INSTRUMENT="QQQ")
    env.pop("PYTHONPATH", None)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       env=env, cwd=home, timeout=120)
    lines = [l for l in r.stdout.splitlines() if l.startswith("{")]
    if r.returncode != 0 or not lines:
        raise RuntimeError(f"child rc={r.returncode}: {(r.stderr or r.stdout)[-400:]}")
    return json.loads(lines[-1]), r.stderr


def main() -> int:
    print("query.py: its own tree, and no silent fallback")
    home = tempfile.mkdtemp(prefix="check_query_paths.")
    decoy = os.path.join(home, "options-trader")
    os.makedirs(decoy)
    with open(os.path.join(decoy, "config.py"), "w") as fh:
        fh.write("DB_PATH = '/DECOY/LIVE/trades.db'\nDECOY = True\n")
    root = os.path.realpath(ROOT)

    try:
        out, err = child("import query, config\n"
                         "print(json.dumps({'inst': query.INSTALL_DIR, 'cfg': config.__file__,"
                         " 'db': query.DB_PATH, 'cfgdb': getattr(config, 'DB_PATH', None),"
                         " 'decoy': getattr(config, 'DECOY', False)}))\n", home)
        check("Q1 (a) INSTALL_DIR and the loaded config are THIS tree, not the decoy ~/options-trader",
              os.path.realpath(out["inst"]) == root and os.path.realpath(out["cfg"]).startswith(root + os.sep)
              and not out["decoy"], f"INSTALL_DIR={out['inst']} config={out['cfg']}")
        check("Q4 (d) config imports cleanly -> no fallback notice, DB_PATH is config's own",
              "config did not load" not in err and out["db"] == out["cfgdb"],
              f"db={out['db']} cfgdb={out['cfgdb']} stderr={err[-200:]!r}")
    except Exception as exc:                                    # noqa: BLE001
        check("Q1 (did not run)", False, f"raised {type(exc).__name__}: {exc}")
        check("Q4 (did not run)", False, "")

    try:
        out, _ = child("import query\n"
                       "stub = types.ModuleType('data.market_data'); stub.fetch_quote = lambda s: 101.0\n"
                       "import data; sys.modules['data.market_data'] = stub\n"
                       "n0 = len(sys.path); p1 = query.get_live_price(); p2 = query.get_live_price()\n"
                       "print(json.dumps({'n0': n0, 'n2': len(sys.path), 'p': [p1, p2]}))\n", home)
        check("Q2 (b) two get_live_price() calls leave sys.path the same length",
              out["n2"] == out["n0"] and out["p"] == [101.0, 101.0], f"{out}")
    except Exception as exc:                                    # noqa: BLE001
        check("Q2 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    try:
        out, err = child("sys.modules['config'] = None\n"
                         "import query\n"
                         "print(json.dumps({'db': query.DB_PATH}))\n", home)
        check("Q3 (c) config unimportable -> DB_PATH falls back INSIDE this tree",
              os.path.realpath(out["db"]) == os.path.join(root, "trades.db"), f"db={out['db']}")
        import re
        named = re.search(r"config did not load \((\w+(?:Error|Exception)): ", err)
        check("Q4 (d) the fallback NAMES what it caught on stderr (the exception class and the fallback path)",
              bool(named) and out["db"] in err, f"stderr={err[-300:]!r}")
    except Exception as exc:                                    # noqa: BLE001
        check("Q3 (did not run)", False, f"raised {type(exc).__name__}: {exc}")

    import shutil
    shutil.rmtree(home, ignore_errors=True)
    print("GREEN" if not PROBLEMS else f"RED — {len(PROBLEMS)} failed: {', '.join(PROBLEMS)}")
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
