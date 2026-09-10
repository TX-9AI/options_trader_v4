#!/usr/bin/env python3
"""
tests/check_reconcile_lock.py  v1.0
v1.0  2026-09-10  r349 / S3.27 — an operator-initiated repair may not lose a
      race in silence.

🔴 WHAT HAPPENED. `main()` did `acquire_lock(LOCK_WAIT if do_verify else 0)`.
`--reconcile` is not `--verify`, so it waited ZERO seconds, took the normal-run
branch on failure — `return 0`, no output, exit 0 — and a repair the operator
asked for became indistinguishable from a box with nothing to say.

Measured 2026-09-10: a fleet reconcile at 19:16 collided with `s3-push.timer`
(re-armed by the conductor's own REARM step) and box after box reported
`NO ANSWER — counters NOT proven reset. (no output)`. The reconcile never ran;
the July prefixes the epoch strip emptied kept their counts; `--verify` kept
reporting `got=0`; r180's heal kept correctly refusing; the fleet was held for
THREE NIGHTS over a race that exits silently.

  L1  --reconcile asks for the full LOCK_WAIT, not 0
  L2  --verify still does (no regression on the path that already worked)
  L3  a plain push still passes 0 — a scheduled run SHOULD skip, because the
      run in flight is doing the same work
  L4  when the wait times out, --reconcile PRINTS and returns non-zero; it
      never exits 0 in silence
"""
import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "warehouse", "s3_push.py")
FAILS = []


def check(name, ok, detail=""):
    print("  {:<4} {}  {}".format(name, "PASS" if ok else "FAIL", detail))
    if not ok:
        FAILS.append(name)


def main():
    src = open(SRC, encoding="utf-8").read()
    tree = ast.parse(src)

    # the acquire_lock call inside main(), read from the AST — a grep would
    # match the comment block that explains the bug.
    call = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "id", "") == "acquire_lock"
                and node.args):
            call = node.args[0]
    if call is None:
        print("  FAIL  no acquire_lock(...) call found in s3_push")
        return 1
    arg = ast.get_source_segment(src, call) or ""

    # L1/L2/L3 — evaluate the real expression under each flag combination.
    # ⚠️ THE ARGUMENT MAY REFERENCE A LOCAL SET JUST ABOVE IT. Evaluating the
    # expression alone is not enough — pull any `_x = ...` assignments that
    # precede the call inside main() and run them first, so the test measures
    # the real logic rather than a fragment of it.
    pre = src.split("def main(", 1)[-1].split("lock = acquire_lock", 1)[0]
    setup = [l.strip() for l in pre.splitlines()
             if "=" in l and l.strip().startswith("_")
             and not l.strip().startswith("#")]

    def wait_for(verify, recon):
        ns = {"do_verify": verify, "do_reconcile": recon, "LOCK_WAIT": 120}
        for line in setup:
            try:
                exec(line, ns)
            except Exception:                                   # noqa: BLE001
                pass
        try:
            return eval(compile(ast.Expression(ast.parse(arg, mode="eval").body),
                                "<arg>", "eval"), ns)
        except NameError as exc:                                # noqa: BLE001
            return "NAMEERROR:{}".format(exc)

    r = wait_for(False, True)
    check("L1", r == 120, "--reconcile waits {} (expr: {})".format(r, arg))
    v = wait_for(True, False)
    check("L2", v == 120, "--verify waits {}".format(v))
    p = wait_for(False, False)
    check("L3", p == 0, "plain push waits {}".format(p))

    # L4 — the failure branch must print and return non-zero.
    body = src.split("lock = acquire_lock", 1)[-1][:1400]
    code = "\n".join(l for l in body.splitlines()
                     if not l.lstrip().startswith("#"))
    speaks = "COULD NOT ACQUIRE THE PUSH LOCK" in code
    nonzero = "return 3" in code
    silent = "if lock is None and not _wants_lock" in code
    check("L4", speaks and nonzero and silent,
          "prints={} rc!=0={} scoped-silent-skip={}".format(
              speaks, nonzero, silent))

    print("")
    if FAILS:
        print("FAILED: {}".format(", ".join(FAILS)))
        return 1
    print("ALL PASS (4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
