#!/usr/bin/env python3
"""
tests/gen_write_map.py  v4.3
v4.3  2026-09-20  r400 / DOC.25 - THE MAP'S DEAD-WEIGHT LIST WAS NAMING EIGHT
LIVE STREAMS. This generator was PURE REGEX over source text and could not see
a table name that was not spelled out, so `warehouse/s3_push.py` - which reads
its tables as `"SELECT * FROM %s" % table` inside `for table in
SERIES_TABLES:` - was credited with the TWO it names literally against the
TWENTY it reads.
  🔴 THE CONSEQUENCE IS A DELETION LIST, NOT AN ATTRIBUTION ERROR. "No external
reader" went 9 -> 1 on this fix; the eight that left it are pushed to S3 every
session, and S3.13 records 492,945 `raw/shadow` objects already deleted once on
exactly that reasoning.
  🔑 THE THREE SHAPES ARE THE OTV4TEST FORK'S r67, PORTED WITH CREDIT: the
`%`-substitution with a single-`%s` refusal so an ambiguous path template
resolves to NOTHING; `_iter_members` as an explicit RECURSION so a CONDITIONAL
iterable contributes the branches that resolve; and `_param_consts`, which
resolves a loop over a PARAMETER from the module's own call sites.
  ⚠️ THE READ PASS TAKES THE RESOLVED TEXT TOO. Wiring it into the write pass
alone lands the writes and silently drops the reads, which would leave the
deletion list exactly as wrong as it was.
  ⚠️ AND EVERY ENTRY POINT IS DEFENSIVE BECAUSE THIS RUNS INSIDE THE LAND GATE
(section 33): any parse failure returns nothing and the regex pass stands
alone, so the worst case is the behaviour this file already had.
Generates docs/WRITE_MAP.md — what every box writes, and who writes it.

v4.2  2026-09-11  r358 — `handoffs` joins SKIP_DIRS. The operator's inbox on
the box is untracked by design and this walk reads the FILESYSTEM, so
.gitignore is invisible to it; a .py dropped there would drift WRITE_MAP.

v4.1  2026-08-26  r146 — THE MAP WAS ORDER-DEPENDENT AND FAILED THE GATE ON
      CONTROL WHILE PASSING IN THE SANDBOX. `scan()` recorded a READ only if
      the table's creator/writer had ALREADY been scanned, and `_files()`
      walked directories in FILESYSTEM order (os.walk, unsorted). So a reader
      that sat in a directory walked before its writer's directory was
      silently dropped — and which directory walks first differs between two
      machines. It surfaced the moment r146 moved plan_tick's creator from
      derived/ to strategy/. Fixed: directories are walked sorted, and reads
      are collected in a SECOND pass after every writer is known. The output
      is now a function of the tree alone.

v4.0  2026-08-25  Operator's ask: "a document that answers what does every box
write and who writes it — like a file map, but for journal writers."

WHY IT IS SEPARATE FROM FILE_MAP.md. That map answers "what calls what" from
the import graph. This answers a different question the import graph cannot:
**which module OWNS which table.** By r70 this repo had 22 tables across three
databases and NO SINGLE INDEX of who writes them — the ownership lived only in
scattered docstrings, which is the same shape as the sensor problem: a thing
that exists with no way to see it whole.

⚠️ GENERATED, NEVER HAND-MAINTAINED. A hand-kept write map drifts exactly the
way the version headers drifted across day_trader_pro — the changelogs advanced
while the title lines went stale for weeks. This is regenerated in the gate.

⚠️ IT REPORTS WHAT THE SOURCE SAYS, NOT WHAT A SCHEMA DUMP SAYS. A live
database shows tables that exist; this shows tables the CODE creates and
writes. The difference is the interesting part — a table in the db with no
writer in the tree is an orphan, and a writer whose table nobody reads is dead
weight. Both are visible here and in neither place alone.

Run:  python3 tests/gen_write_map.py           # regenerate
      python3 tests/gen_write_map.py --check   # fail if stale
"""

from __future__ import annotations

import os
import ast
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "WRITE_MAP.md")

# r358 — `handoffs` is the operator inbox: untracked by design, and this walk
# reads the FILESYSTEM, so .gitignore does not keep it out. A .py dropped there
# would enter WRITE_MAP and drift the next land.
SKIP_DIRS = {".git", "__pycache__", "venv", "docs", "node_modules",
             "handoffs"}

RE_CREATE = re.compile(r"CREATE TABLE IF NOT EXISTS\s+([a-z_]+)", re.I)
RE_INSERT = re.compile(r"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+([a-z_]+)", re.I)
RE_UPDATE = re.compile(r"UPDATE\s+([a-z_]+)\s+SET", re.I)
RE_DELETE = re.compile(r"DELETE\s+FROM\s+([a-z_]+)", re.I)
RE_SELECT = re.compile(r"FROM\s+([a-z_]+)", re.I)
RE_DBFILE = re.compile(r"([a-z_]+)\.db")


# ── DYNAMIC SQL: A LOOP OVER THIS MODULE'S OWN CONSTANTS (r400) ─────────────
# 🔴 THIS FILE WAS PURE REGEX OVER SOURCE TEXT AND COULD NOT SEE A TABLE NAME
# THAT WAS NOT SPELLED OUT. `warehouse/s3_push.py` reads its tables as
# `"SELECT * FROM %s" % table` inside `for table in SERIES_TABLES:`, so the map
# credited it with the TWO it names literally (`candles`, `trades`) against the
# TWENTY it actually reads.
#
# 🔴 AND THE CONSEQUENCE IS NOT AN ATTRIBUTION ERROR, IT IS A DELETION LIST.
# This document publishes "No external reader", and says of it in its own
# words: *"A table nobody reads is dead weight … this list is where that
# question gets asked."* Measured before the fix: **8 of its 9 entries were
# read by `s3_push` every session** — `character_axis_sample`,
# `character_ledger`, `exit_counterfactual`, `indicator_series`, `last_trade`,
# `session_summary`, `theo_series`, `underlying_series`. Only `resting_orders`
# was a true positive.
# ⚠️ **THIS PROJECT HAS ALREADY PAID THAT BILL ONCE.** [[S3.13]]: *"THE
# 2026-08-25 PURGE DELETED 492,945 `raw/shadow` OBJECTS AS A DEAD STREAM. IT
# WAS NOT DEAD."* Same reasoning, same kind of list. And `--check` was green
# throughout, because the generator and the map agreed with each other —
# self-consistent and wrong.
#
# 🔑 THE THREE SHAPES ARE THE OTV4TEST FORK'S (their r67), PORTED WITH CREDIT
# RATHER THAN RE-DERIVED. They paid for three attempts to get here.
# ⚠️ AND EVERY ENTRY POINT IS DEFENSIVE. This generator RUNS INSIDE THE LAND
# GATE (§33): if it raises, every future delivery fails on it. Any parse or
# resolution failure returns NOTHING and the regex pass stands alone, so the
# worst case is the behaviour this file had before.
_ITER_WRAPPERS = {"list", "tuple", "set", "sorted", "reversed", "frozenset"}
_ITER_METHODS = {"keys", "values", "items"}


def _string_members(node):
    """The strings of a collection literal written in place, else None."""
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        out = [e.value for e in node.elts
               if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        return out if len(out) == len(node.elts) else None
    return None


def _module_consts(tree):
    """{NAME: [strings]} for module-level string collections."""
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        members = _string_members(node.value)
        if not members:
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                out[tgt.id] = members
    return out


def _param_consts(tree, consts):
    """{function: {parameter: [tables]}} resolved from THIS module's calls.

    ⚠️ SCOPE IS DELIBERATELY TINY AND IS NOT GENERAL DATAFLOW: same module, a
    bare Name that is a module string-constant, nothing else. It exists for one
    real shape — `push_series(..., tables=DERIVED_SERIES_TABLES, ...)` called a
    few lines from its own loop. An imported name, a computed value or a call
    result resolves to NOTHING, which leaves the loop as invisible as it was
    rather than guessed at.
    """
    funcs = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = node.args
            funcs[node.name] = [pa.arg for pa in (a.posonlyargs + a.args)]
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in funcs:
            continue
        names = funcs[node.func.id]
        slot = out.setdefault(node.func.id, {})
        for i, arg in enumerate(node.args):
            if i < len(names) and isinstance(arg, ast.Name) and arg.id in consts:
                slot.setdefault(names[i], []).extend(consts[arg.id])
        for kw in node.keywords:
            if kw.arg and isinstance(kw.value, ast.Name) and kw.value.id in consts:
                slot.setdefault(kw.arg, []).extend(consts[kw.value.id])
    return out


def _iter_members(node, consts, params=None):
    """Members of a `for` iterable built from this module's own literals.

    -> list of strings, or None when ANYTHING in it is not resolvable.
    """
    m = _string_members(node)
    if m is not None:
        # ⚠️ `or None` keeps the contract single-valued: an EMPTY literal must
        # not read as "resolved, nothing to iterate".
        return m or None
    if isinstance(node, ast.Name):
        if node.id in consts:
            return list(consts[node.id])
        if params and node.id in params:
            return list(params[node.id]) or None
        return None
    if isinstance(node, ast.Call):
        if (isinstance(node.func, ast.Name)
                and node.func.id in _ITER_WRAPPERS and node.args):
            return _iter_members(node.args[0], consts, params)
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr in _ITER_METHODS):
            return _iter_members(node.func.value, consts, params)
        return None
    # 🔑 A CONDITIONAL ITERABLE CONTRIBUTES THE BRANCHES THAT RESOLVE. This is
    # the one that unlocks `for table in (SERIES_TABLES if tables is None else
    # tables)` — the old shape would have bounced off `IfExp` entirely.
    if isinstance(node, ast.IfExp):
        out = []
        for side in (node.body, node.orelse):
            got = _iter_members(side, consts, params)
            if got:
                out.extend(got)
        return sorted(set(out)) or None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        lhs = _iter_members(node.left, consts, params)
        rhs = _iter_members(node.right, consts, params)
        if lhs is None or rhs is None:
            return None
        return lhs + rhs
    return None


def _sql_template(sub, var):
    """SQL text with the loop variable replaced by \0, else None."""
    if isinstance(sub, ast.JoinedStr):
        parts, uses = [], False
        for v in sub.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            elif (isinstance(v, ast.FormattedValue)
                  and isinstance(v.value, ast.Name) and v.value.id == var):
                parts.append("\0")
                uses = True
            else:
                parts.append("?")
        return "".join(parts) if uses else None
    # ⚠️ ONLY A BARE Name ON THE RIGHT, AND EXACTLY ONE `%s`. `s3_push` also
    # has `"%s/derived_%s/dt=%s/..." % (PREFIX, table, day, ...)`; a TUPLE means
    # the table's POSITION is not knowable, so it must resolve to nothing
    # rather than to the first slot.
    if (isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Mod)
            and isinstance(sub.left, ast.Constant)
            and isinstance(sub.left.value, str)
            and isinstance(sub.right, ast.Name) and sub.right.id == var):
        text = sub.left.value
        if text.count("%s") != 1:
            return None
        return text.replace("%s", "\0")
    return None


def _loop_sql(src):
    """Every SQL string a `for` loop over this module's constants resolves to.

    ⚠️ NEVER RAISES. A syntax error, an unparseable file or any internal
    failure returns [] and the regex pass stands alone (§33 — this runs inside
    the land gate).
    """
    try:
        tree = ast.parse(src)
        consts = _module_consts(tree)
        params_of = _param_consts(tree, consts)
        # ⚠️ WITHOUT THIS MAP `_iter_members` NEVER RECEIVES `params` AND THE
        # PARAMETER SHAPE IS DEAD CODE THAT LOOKS INSTALLED. The fork named
        # this as the failure they would most expect on a port.
        fn_of = {}
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for sub in ast.walk(fn):
                    fn_of[id(sub)] = fn.name
        out = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            tgt = node.target
            if isinstance(tgt, ast.Tuple) and tgt.elts:
                tgt = tgt.elts[0]
            if not isinstance(tgt, ast.Name):
                continue
            members = _iter_members(node.iter, consts,
                                    params_of.get(fn_of.get(id(node), ""), {}))
            if not members:
                continue
            for sub in (n for st in node.body for n in ast.walk(st)):
                tmpl = _sql_template(sub, tgt.id)
                if tmpl is not None:
                    out.extend(tmpl.replace("\0", m) for m in members)
        return out
    except Exception:                                           # noqa: BLE001
        return []

# Which database each table lives in. Derived from the module that CREATEs it,
# so a table moving file moves here automatically.
DB_OF_DIR = {
    "data/candle_feed.py": "feed_store.db",
    "data/derived_store.py": "derived_store.db",
    "database/trade_logger.py": "trades.db",
}

# ⚠️ MODULES THAT CREATE THEIR OWN TABLE INSIDE ANOTHER STORE'S FILE.
# `derived/` engines call `self._store.conn.execute("CREATE TABLE ...")` so the
# table lives in derived_store.db while the DDL lives in the engine. That is
# deliberate — one engine per store, each owning its own schema — but it means
# the file that CREATEs is not the file that names the database, and the first
# run of this generator listed four tables as "(unattributed)". Reporting them
# as homeless would be wrong; guessing silently would be worse. This is the
# explicit mapping, and it is the ONE hand-maintained thing here.
DB_OF_PREFIX = {
    "derived/": "derived_store.db",
    "analysis/tenor_publish.py": "feed_store.db",
}


def _files():
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)   # v4.1: deterministic
        for f in sorted(fn):
            if f.endswith(".py"):
                yield os.path.relpath(os.path.join(dp, f), ROOT)


def scan():
    creates, writes, reads, dbs = {}, {}, {}, {}
    sources = {}
    for rel in _files():
        try:
            sources[rel] = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        except Exception:                                       # noqa: BLE001
            continue
    # r400 — RESOLVED ONCE PER FILE AND USED BY *BOTH* PASSES. The fork's
    # warning was explicit: if the loop-resolved texts feed the write pass and
    # not the read pass, the writes land and the reads silently do not — which
    # would leave the "No external reader" list exactly as wrong as it was.
    looped = {rel: "\n".join(_loop_sql(src)) for rel, src in sources.items()}
    for rel, src in sources.items():
        src = src + "\n" + looped.get(rel, "")
        for t in RE_CREATE.findall(src):
            creates.setdefault(t, set()).add(rel)
            if rel in DB_OF_DIR:
                dbs[t] = DB_OF_DIR[rel]
            else:
                for pref, db in DB_OF_PREFIX.items():
                    if rel.startswith(pref):
                        dbs[t] = db
                        break
        for rx, kind in ((RE_INSERT, "insert"), (RE_UPDATE, "update"),
                         (RE_DELETE, "delete")):
            for t in rx.findall(src):
                writes.setdefault(t, {}).setdefault(rel, set()).add(kind)
    # v4.1 — SECOND PASS, after every writer is known. A read is only a read
    # of a table this tree writes; deciding that mid-walk made the answer
    # depend on directory order.
    for rel, src in sources.items():
        src = src + "\n" + looped.get(rel, "")       # r400 — the read pass too
        for t in RE_SELECT.findall(src):
            # a module that only writes also names the table in its INSERT;
            # reads are recorded separately so "who consumes this" is answerable
            if t in creates or t in writes:
                reads.setdefault(t, set()).add(rel)
    return creates, writes, reads, dbs


def render() -> str:
    creates, writes, reads, dbs = scan()
    tables = sorted(set(creates) | set(writes))
    L = []
    L.append("# WRITE_MAP.md — what every box writes, and who writes it")
    L.append("")
    L.append("**GENERATED by `tests/gen_write_map.py` — do not edit by hand.**")
    L.append("Regenerated in the land gate; a stale map fails `--check`.")
    L.append("")
    L.append("`FILE_MAP.md` answers *what calls what*. This answers *who owns "
             "which table* — a question the import graph cannot.")
    L.append("")
    L.append("⚠️ **A table with no writer is an orphan. A table nobody reads "
             "is dead weight.** Both are visible here and in neither the "
             "schema nor the call graph alone.")
    L.append("")
    L.append(f"**{len(tables)} tables.**")
    L.append("")

    by_db = {}
    for t in tables:
        by_db.setdefault(dbs.get(t, "(unattributed)"), []).append(t)

    for db in sorted(by_db):
        L.append(f"## {db}")
        L.append("")
        L.append("| table | created by | written by | read by |")
        L.append("|---|---|---|---|")
        for t in sorted(by_db[db]):
            c = ", ".join(f"`{x}`" for x in sorted(creates.get(t, []))) or "—"
            w = writes.get(t, {})
            wparts = []
            for mod in sorted(w):
                kinds = "/".join(sorted(w[mod]))
                wparts.append(f"`{mod}` ({kinds})")
            wtxt = ", ".join(wparts) or "**— NO WRITER**"
            r = sorted(x for x in reads.get(t, set())
                       if x not in w and x not in creates.get(t, set()))
            rtxt = ", ".join(f"`{x}`" for x in r) or "—"
            L.append(f"| `{t}` | {c} | {wtxt} | {rtxt} |")
        L.append("")

    orphan_w = [t for t in tables if not writes.get(t)]
    orphan_r = [t for t in tables
                if not [x for x in reads.get(t, set())
                        if x not in writes.get(t, {})]]
    L.append("## Flags")
    L.append("")
    L.append(f"- **No writer** ({len(orphan_w)}): "
             + (", ".join(f"`{t}`" for t in orphan_w) or "none"))
    L.append(f"- **No external reader** ({len(orphan_r)}): "
             + (", ".join(f"`{t}`" for t in orphan_r) or "none"))
    L.append("")
    L.append("⚠️ *No external reader* is not automatically a defect — a table "
             "written today for a study run in a month is exactly the point of "
             "the derived layer. It IS a defect when nobody ever intends to "
             "read it, and this list is where that question gets asked.")
    L.append("")
    return "\n".join(L)


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        try:
            cur = open(OUT, encoding="utf-8").read()
        except FileNotFoundError:
            print("  WRITE_MAP.md missing — run gen_write_map.py")
            return 1
        if cur.strip() != text.strip():
            print("  WRITE_MAP.md is STALE — regenerate it")
            return 1
        print("  write map is current")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
