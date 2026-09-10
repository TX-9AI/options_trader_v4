#!/usr/bin/env python3
"""
tests/check_entry_records_contract.py  v1.0
v1.0  2026-09-10  r340 / RPT.24 — a single-leg entry must record its CONTRACT.

🔴 THE DEFECT THIS CLOSES. `_record_kwargs` wrote `symbol = INSTRUMENT` — the
underlying — and nothing naming the option. So every ORB and Runaway trade in
the book is unreplayable: `exit_replay` refused 301 of 337 rows with "no leg
symbols on row", and that is not a lookup failure, it is an ABSENCE. No join,
no symbol-format fix and no permission change can recover a field that was
never written.

  K1  the factory returns a non-empty `option_symbol` from signal.contract
  K2  it does not raise when there is no contract (butterfly / degraded
      signal) — an empty string, never an exception on the entry path
  K3  the underlying still lands in `symbol`, unchanged
  K4  ONE construction site: every `make_record` for a single-leg entry goes
      through `_record_kwargs`, so the two lineages cannot drift (§7)

⚠️ K4 IS A SOURCE CHECK AND THAT IS DELIBERATE — the failure it guards is a
SECOND factory appearing, which no runtime assertion on the first one can see.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


class _C:
    symbol = "QQQ   260910C00715000"


class _Sig:
    contract = _C()
    strategy_name = "ORBStrategy"
    setup_type = "orb"
    direction = "LONG"
    underlying_entry = 715.0
    underlying_stop = 713.0
    underlying_target = 719.0
    vix_at_signal = 14.0
    is_fed_day = False
    option_side = "call"
    strike = 715.0
    expiry = "2026-09-10"


def main():
    src_path = os.path.join(REPO, "execution", "entry_engine.py")
    src = open(src_path, encoding="utf-8").read()
    # 🔴 THE FUNCTION IS COMPILED FROM SOURCE, NOT IMPORTED. `entry_engine`
    # pulls in the broker SDK and a timezone library that live on the BOXES;
    # this gate runs on CONTROL at land time. Importing would make it fail for
    # the machine rather than the code — a red that means "wrong host" is a
    # red the reader learns to skip. Stubbing the chain was tried first and
    # grew a new missing module each time, which is itself the signal.
    # 🔑 IT IS STILL THE REAL FUNCTION: the source is lifted verbatim out of
    # the file by AST and compiled, so a change to that code changes what runs
    # here. Only its module's IMPORTS are absent, and the factory uses none of
    # them beyond INSTRUMENT.
    import ast
    tree = ast.parse(src)
    fn_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_record_kwargs":
            fn_src = ast.get_source_segment(src, node)
    if fn_src is None:
        print("  FAIL  _record_kwargs not found in execution/entry_engine.py")
        return 1
    ns = {"INSTRUMENT": "QQQ"}
    exec(compile(ast.parse(fn_src.lstrip()), "<factory>", "exec"), ns)
    fn = ns["_record_kwargs"]

    try:
        rec = fn(None, _Sig())
    except Exception as exc:                                    # noqa: BLE001
        print("  FAIL  _record_kwargs raised: {}".format(exc))
        return 1

    check("K1", rec.get("option_symbol") == _C.symbol,
          "option_symbol={!r}".format(rec.get("option_symbol")))

    class _Bare:
        strategy_name = setup_type = direction = ""
        underlying_entry = underlying_stop = underlying_target = 0.0
        vix_at_signal = 0.0
        is_fed_day = False
    try:
        bare = fn(None, _Bare())
        ok2 = bare.get("option_symbol") == ""
        why = "no contract -> {!r}".format(bare.get("option_symbol"))
    except Exception as exc:                                    # noqa: BLE001
        ok2, why = False, "raised: {}".format(exc)
    check("K2", ok2, why)

    check("K3", "symbol" in rec and rec["symbol"] and
          rec["symbol"] != _C.symbol,
          "symbol={!r} (underlying, not the contract)".format(rec.get("symbol")))

    # K4 — one lineage. Every make_record( in this file must be fed by the
    # shared factory on the very next line.
    bad = []
    lines = src.splitlines()
    for i, ln in enumerate(lines):
        if "make_record(" in ln and "def " not in ln:
            window = " ".join(lines[i:i + 3])
            if "_record_kwargs" not in window:
                bad.append(i + 1)
    check("K4", not bad,
          "make_record without the shared factory at line(s) {}".format(bad)
          if bad else "every make_record uses _record_kwargs")

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
