#!/usr/bin/env python3
"""
tests/check_manifold_cost.py  v1.0
v1.0  2026-09-20  r405 / OPS.32 — THE BOARD MUST NOT BUY A NUMBER NOBODY
      DECIDES ON WITH A FULL TABLE SCAN.

🔴 WHAT IT PROTECTS, MEASURED ON TSLA 2026-09-20 RATHER THAN REASONED:
`tools/manifold_health.py` ran `rc=0 elapsed=38s` while `fleet.py`'s fan-out
is bounded at 22s and `status.py:491` allows it 10 — so the board timed out on
the menu and the rollup bulb rendered `⚪ Manifold: unavailable` on every box
with a large store. **28.75 of those 38 seconds were one `COUNT(*)` over
13,241,241 rows**, and `_bulb` reads that count as a truthiness test and
nothing else.

  M1  the default path runs NO COUNT(*) over a stream table  (the defect)
  M1b and `counts` DECLARES False — the default is what the fleet runs
  M2  --counts still returns EXACT figures                   (the opt-in works)
  M3  🔴 THE BULBS ARE IDENTICAL IN BOTH MODES                (the control)
  M4  the candles GROUP BY executes exactly ONCE             (the dead twin)
  M5  an EMPTY stream is still RED without a count           (fail-closed)
  M6  an uncounted row never renders as `0`                  (§0.5)
  M7  status.py names a TIMEOUT distinctly from a failure

🔑 M1 AND M4 READ THE SQL THE CODE ACTUALLY EXECUTES, not its source text.
A grep for `COUNT(*)` would be satisfied or broken by this file's own
changelog and by the `--counts` branch that is SUPPOSED to contain one (§20,
§21). A `set_trace_callback` on the real connection cannot be fooled by
either.

⚠️ EVERY FIXTURE IS BUILT FROM THE MODULE'S OWN `STREAMS` AND `DERIVED`
TABLES, never from this author's list of them (§0.4) — so a table added to the
board is covered here the day it is added, not the day somebody remembers.

Plain script with an exit code, stdlib only: the land gate runs every CHECK
under bare `python3` and pytest is not guaranteed ([[CHK.9]], §36).
"""
from __future__ import annotations
import ast
import importlib.util
import os
import re
import sqlite3
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOL = os.path.join(ROOT, "tools", "manifold_health.py")
STATUS = os.path.join(ROOT, "status.py")

_res = []


def ck(name, ok, why=""):
    _res.append((name, bool(ok), why))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}  {'' if ok else why}")


def _unrun(names, reason):
    done = {n for n, _, _ in _res}
    for n in names:
        if n not in done:
            ck(n, False, reason)


_TOOLCHECKS = ["M1", "M1b", "M2", "M3", "M4", "M5", "M6"]

# ⚠️ FAILS RATHER THAN RAISES if the tool is absent. A gate that cannot report
# on the broken version is not a gate — the crash-instead-of-fail defect
# [[DOC.25]]'s R1c and [[OPS.27]]'s first cut both shipped, and r404's B14b
# made it three.
mh = None
if not os.path.exists(TOOL):
    _unrun(_TOOLCHECKS, f"{TOOL} does not exist")
else:
    try:
        _spec = importlib.util.spec_from_file_location("_mh", TOOL)
        mh = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(mh)
    except Exception as exc:                                    # noqa: BLE001
        mh = None
        _unrun(_TOOLCHECKS, f"module did not load: {exc!r}")


class _Spy:
    """A sqlite3 stand-in that records every statement the tool executes."""

    Error = sqlite3.Error

    def __init__(self):
        self.sql = []

    def connect(self, *a, **k):
        conn = sqlite3.connect(*a, **k)
        conn.set_trace_callback(self.sql.append)
        return conn


def _fixture(tmp, stream_rows=3, derived_rows=2, empty_tables=()):
    """Build the two stores FROM THE MODULE'S OWN TABLE LISTS."""
    feed = os.path.join(tmp, "feed_store.db")
    derived = os.path.join(tmp, "derived_store.db")
    now = 1789900000
    fc = sqlite3.connect(feed)
    for tbl, tscol, _b, _l, _c, _ah in mh.STREAMS:
        fc.execute(f"CREATE TABLE {tbl} ({tscol} REAL)")
        if tbl not in empty_tables:
            fc.executemany(f"INSERT INTO {tbl} ({tscol}) VALUES (?)",
                           [(now - i,) for i in range(stream_rows)])
    fc.execute("CREATE TABLE candles (symbol TEXT, interval TEXT,"
               " ts_epoch_ms INTEGER)")
    fc.executemany("INSERT INTO candles VALUES (?,?,?)",
                   [("AMD", "1m", now * 1000 - i * 1000) for i in range(4)])
    fc.commit(); fc.close()
    dc = sqlite3.connect(derived)
    for tbl, tscol, _b, _l in mh.DERIVED:
        dc.execute(f"CREATE TABLE {tbl} ({tscol} REAL)")
        dc.executemany(f"INSERT INTO {tbl} ({tscol}) VALUES (?)",
                       [(now - i,) for i in range(derived_rows)])
    dc.commit(); dc.close()
    return feed, derived


def _has_counts() -> bool:
    """Does `collect` even offer the opt-in? Read from the SIGNATURE."""
    try:
        import inspect
        return "counts" in inspect.signature(mh.collect).parameters
    except Exception:                                           # noqa: BLE001
        return False


def _run(feed, derived, counts, spy):
    """Drive `collect`, ADAPTING to a tree that has no `counts` yet.

    🔴 `counts=None` MEANS *DO NOT PASS THE ARGUMENT AT ALL*, AND THAT
    DISTINCTION IS LOAD-BEARING. M1's first cut passed `counts=False`
    explicitly and a mutation flipping the DECLARED DEFAULT to True **survived
    green** — because the check was exercising the path it asked for rather
    than the path `main()`, the menu and `status.py` actually get. The gate was
    asserting something narrower than it claimed, which is [[C.23]]'s shape:
    a test that arranges its own subject proves only that the arrangement
    works. M1 now drives the real default and M1b pins the declared value.

    🔑 WHY THIS ADAPTS RATHER THAN RAISING. At the born-red commit `collect`
    takes no `counts` keyword, and calling it with one raises a TypeError that
    would take EVERY check in this file down with it — so the gate would
    report one signature error instead of six findings, which is the
    crash-versus-failure defect this repo has now shipped three times. With
    the fallback, M1, M4, M5 and M6 each go red for THEIR OWN reason against
    the old code, and M2/M3 report the honest one: the opt-in does not exist.
    """
    real = mh.sqlite3
    mh.sqlite3 = spy
    try:
        if counts is None or not _has_counts():
            return mh.collect(feed, derived, in_rth=True, is_index=False)
        return mh.collect(feed, derived, in_rth=True, is_index=False,
                          counts=counts)
    finally:
        mh.sqlite3 = real


if mh is not None:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            feed, derived = _fixture(tmp)
            spy_off, spy_on = _Spy(), _Spy()
            # ⚠️ `None` — the DEFAULT path, the one production takes.
            rep_off = _run(feed, derived, None, spy_off)
            rep_on = _run(feed, derived, True, spy_on)

            # ── M1 · NO COUNT(*) OVER A STREAM TABLE ON THE DEFAULT PATH ────
            stream_tbls = [t[0] for t in mh.STREAMS] + [t[0] for t in mh.DERIVED]
            offenders = []
            for stmt in spy_off.sql:
                flat = " ".join(stmt.split()).upper()
                if "COUNT(*)" not in flat:
                    continue
                for t in stream_tbls:
                    if re.search(r"\bFROM\s+%s\b" % re.escape(t.upper()), flat):
                        offenders.append((t, " ".join(stmt.split())[:70]))
            ck("M1", not offenders,
               f"the default path runs COUNT(*) over stream table(s): "
               f"{offenders} — that is a FULL SCAN, measured at 28.75s on "
               f"13.2M rows, for a number `_bulb` only tests for truthiness")

            # ── M1b · AND THE DECLARED DEFAULT IS `False` ───────────────────
            # M1 proves the default path does not scan; this proves the default
            # IS the cheap one, read off the signature. Together they close the
            # mutation that survived M1's first cut.
            _dflt = None
            try:
                import inspect as _ins
                _pm = _ins.signature(mh.collect).parameters.get("counts")
                _dflt = _pm.default if _pm is not None else "<absent>"
            except Exception as _e:                             # noqa: BLE001
                _dflt = "<unreadable: %r>" % (_e,)
            ck("M1b", _dflt is False,
               f"collect()'s `counts` must DEFAULT to False — the menu and "
               f"status.py call it with no keyword at all, so the declared "
               f"default is what the fleet runs. got {_dflt!r}")

            # ── M2 · THE OPT-IN STILL ANSWERS EXACTLY ───────────────────────
            if not _has_counts():
                ck("M2", False,
                   "collect() has no `counts` parameter — there is no opt-in, "
                   "so the exact figures cannot be asked for at all")
            else:
                exact = {s["label"]: s["rows"] for s in rep_on["streams"]}
                ck("M2", exact and all(v == 3 for v in exact.values()),
                   f"--counts must still return the true figures: {exact}")

            # ── M3 · 🔴 THE VERDICT DOES NOT MOVE. The control on the whole
            # revision: if a bulb differs between the two modes then the
            # cheap path is not answering the same question, and every
            # measurement of "it is now fast" would be about a different board.
            b_off = [(s["label"], s["bulb"]) for s in rep_off["streams"]] + \
                    [(d["label"], d["bulb"]) for d in rep_off["derived"]]
            b_on = [(s["label"], s["bulb"]) for s in rep_on["streams"]] + \
                   [(d["label"], d["bulb"]) for d in rep_on["derived"]]
            if not _has_counts():
                # ⚠️ WITHOUT THE OPT-IN THE TWO RUNS ARE THE SAME RUN, so an
                # equality test would pass VACUOUSLY and report parity between
                # a mode and itself. Refused by name instead.
                ck("M3", False,
                   "there is only one mode, so `identical in both modes` "
                   "cannot be tested — it would compare a run with itself")
            else:
                ck("M3", b_off == b_on,
               f"the bulbs differ between counted and uncounted modes — the "
                   f"the bulbs differ between counted and uncounted modes — "
                   f"the cheap path must be observationally identical for the "
                   f"DECISION.\n        off={b_off}\n        on ={b_on}")

            # ── M4 · THE CANDLES GROUP BY RUNS ONCE ─────────────────────────
            grp = [x for x in spy_off.sql
                   if "GROUP BY" in x.upper() and "CANDLES" in x.upper()]
            ck("M4", len(grp) == 1,
               f"the candles GROUP BY executed {len(grp)} time(s); v4.1 ran it "
               f"twice and discarded the first result")

            # ── M5 · AN EMPTY STREAM IS STILL RED (fail-closed) ─────────────
            with tempfile.TemporaryDirectory() as t2:
                first = mh.STREAMS[0][0]
                f2, d2 = _fixture(t2, empty_tables=(first,))
                rep_e = _run(f2, d2, False, _Spy())
                row = [s for s in rep_e["streams"] if s["table"] == first][0]
                ck("M5", row["bulb"] == mh.RED and row.get("present") is False,
                   f"an EMPTY stream must still be RED without a count — the "
                   f"presence probe must not manufacture presence: {row}")

            # ── M6 · AN UNCOUNTED ROW NEVER RENDERS AS `0` (§0.5) ───────────
            _rt = getattr(mh, "_rows_txt", None)
            txt = ([_rt(s) for s in rep_off["streams"]] if _rt
                   else ["<no _rows_txt>"])
            ck("M6", all(t == "present" for t in txt) and "0" not in txt,
               f"an uncounted populated stream must render `present`, never "
               f"`0` — zero is a measurement and it means MISSING: {txt}")
    except Exception as exc:                                    # noqa: BLE001
        _unrun(_TOOLCHECKS, f"check block raised: {exc!r}")

# ── M7 · status.py TELLS A TIMEOUT FROM A FAILURE ──────────────────────────
# 🔑 ON THE AST, NOT ON THE WORDS. The property is that a distinct handler for
# `TimeoutExpired` EXISTS — a grep for the string would match this comment and
# the changelog paragraph that explains the defect, which is §20 exactly.
try:
    _st = ast.parse(open(STATUS, encoding="utf-8").read())
    _handlers = []
    for node in ast.walk(_st):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            _handlers.append(ast.dump(node.type))
    _has_timeout = any("TimeoutExpired" in h for h in _handlers)
    ck("M7", _has_timeout,
       "status.py must handle subprocess.TimeoutExpired on its own branch — "
       "v4.5 printed `Manifold: unavailable` for a 10s timeout, an "
       "ImportError and a crash alike, and the one that was firing across the "
       "fleet was the timeout")
except Exception as exc:                                        # noqa: BLE001
    ck("M7", False, f"status.py did not parse: {exc!r}")

bad = [n for n, ok, _ in _res if not ok]
print(f"\n  {len(_res) - len(bad)}/{len(_res)} passed")
if bad:
    print(f"  FAILED: {', '.join(bad)}")
sys.exit(1 if bad else 0)
