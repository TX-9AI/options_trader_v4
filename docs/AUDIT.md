# AUDIT.md — the delivery contract

**Read `docs/AUDIT_HANDOFF.md` first: that is WHAT to audit. This is HOW to
deliver it.**

Your output is not landed as you ship it. It is **stripped, validated and
re-shipped** under this repo's conventions by the operator's other agent, and
then landed by the operator. **Anything that does not survive that pipeline is
work you did for nothing** — so the constraints below are not ceremony, they are
the shape of the pipe.

---

## 1. Two deliverables, and they are separate

### 1.1 `FINDINGS.md` — always, even if you fix everything

One entry per finding. **A finding without a mechanism is a suspicion**, and a
suspicion costs a day to chase. Required fields:

```
### F<n>  <one-line claim>
SEVERITY : P0 stops the fleet | P1 trades wrong | P2 measures wrong | P3 rot
FILE     : path:line
MECHANISM: why it is wrong, in terms of what executes in what order
EVIDENCE : the command that demonstrates it, and its output
FIX      : shipped in the tarball | proposed, not shipped | not fixable here
BLAST    : what else touches this
```

⚠️ **`MEASURES WRONG` IS ITS OWN SEVERITY AND IT IS NOT COSMETIC.** This
project's most expensive defects were instruments, not trades: a proxy that made
GEX a gamma-squared surface for years, a grouping key that hid 107 trades as
nothing, a measure that contained its own predictor. **A wrong number is worse
than a crash, because a crash announces itself.**

⚠️ **REPORT WHAT YOU COULD NOT DETERMINE.** An unexamined path named as
unexamined is worth more than silence. Absence reported as absence is the house
rule.

### 1.2 The fix tarball — only if you have fixes

`otv4_audit_fixes_<date>.tar.gz`, containing **only changed files**, at their
real repo paths, rooted at `otv4/`. Not the whole tree.

---

## 2. What the tarball may NOT contain

**These get stripped, and a stripped file is a fix that did not land.**

- ❌ **`docs/GENESIS.md`** — append-only on the box. A shipped copy is stale by
  every revision landed since, and `cp -r` runs BEFORE the gate, so it clobbers
  the good file **even when the gate then fails.** This happened twice on
  2026-08-20; rows went 32 → 28 and the recovery was `git checkout`.
- ❌ **`MANIFEST.txt`, `README_FIXES.txt`, or any scaffolding.** WA §27: an
  archive must not include install scaffolding, because it is *supposed* to be
  deleted after install and routinely is not. Stray MANIFESTs are still tracked
  in v3 repos from tarballs shipped weeks ago.
- ❌ **`trades.db`, `*.log`, `__pycache__`, `.pyc`, venvs.**
- ❌ **Reformatting of untouched code.** Whitespace, import reordering, quote
  style. **It buries the real diff**, and the real diff is the only thing being
  validated.
- ❌ **New third-party dependencies.** The fleet installs from a pinned set. If
  a fix needs one, that is a FINDING, not a fix.
- ❌ **Deletions of anything you did not also explain.** Especially the standing
  checks in `tests/` — if one is wrong, say so and say why; do not remove it.

---

## 3. What every changed file MUST carry

- ✅ **The `INHERITED DOCTRINE` block preserved.** WA §32. Those blocks are the
  measured findings and design constraints carried from v3 — 280 KB of them, and
  they are the reason a future reader does not re-make a solved mistake.
  **Add to them; never trim them.**
- ✅ **A version bump in the header AND a dated entry** saying what changed and
  **why**. Both places — this repo has had headers drift stale while changelogs
  advanced, and vice versa.
- ✅ **The reasoning, not the conclusion.** *"Reordered X before Y"* is a diff.
  *"Y consumed X fourteen lines before it was assigned, so the first tick raised
  and `_safe_strategy` logged it as 'no signal'"* is a doctrine block.
- ✅ **A test, where the fix is behavioural.** Extend `tests/stress_entry_path.py`
  or add a plain script with an exit code. **Not pytest** — the first
  gate-checker was a pytest file and it broke the land command on a box whose
  venv had no pytest. **A red that means "environment" teaches an operator to
  ignore reds.**

---

## 4. The bar your tarball is validated against

All six must pass, as plain scripts, before anything is re-shipped:

```
python3 tests/check_imports.py
python3 tests/check_gates.py
python3 tests/check_no_regime.py
python3 tests/check_condor_spec.py
python3 tests/check_dispatch.py
python3 tests/stress_entry_path.py
python3 tests/gen_file_map.py --check
```

⚠️ **IF A FIX REQUIRES CHANGING A CHECK, SAY SO EXPLICITLY IN `FINDINGS.md`.**
A check that was loosened to let a fix through is the single most dangerous
artifact you could produce here, and it would look like a green board.

⚠️ **AND `import` IS NOT `execute`.** Three defects this month were invisible to
`import main`: the `ctx` NameError that stopped every box, a call to a function
that no longer existed, and `_rc_bar` consumed before assignment. **Run the
path.**

---

## 5. Rules for the fixes themselves

**5.1 Do not fix a measurement by changing the threshold.** If a gate is wrong,
the finding is the gate. Every threshold in this repo is supposed to be
traceable to a number — `ATR floor 0.05%` because 0 of 5,517 bars reached the
required move; `13:00–15:00` because 39% survival vs 26%; `0.25% pierce ceiling`
because 33–34% vs 19–21%. **If you move one, cite what replaces the number.**

**5.2 Fail closed.** Unknown structure → `long_debit` (blocked). Unreadable
paper flag → live (relaxed refused). Unknown tick class → non-penny (coarser is
always postable). **If your fix introduces a default, state which direction it
fails and why that is the safe one.**

**5.3 Never let telemetry reach the trading loop.** A journal write, a log, an
excursion tracker — all must be guarded. **But a bare `except: pass` makes
"deliberate" and "accidental" indistinguishable to the next audit**, which was
`v-audibleabandon`'s finding. Guard *and* name it.

**5.4 A column, a producer and a persist — all three or none.** `open_interest`
had a column and no producer. `peak_close` had a producer and no column.
**Either alone is the bug.** Any new field must exist in the `CREATE TABLE`, in
the migration list, be written by something, and survive `log_exit`.

**5.5 Keep the diff small enough to reason about.** If a fix touches more than a
few files, split it: the P0s in one tarball, the rest in a second. **A large
diff gets landed on trust, and trust is what this pipeline exists to replace.**

---

## 6. What happens after you ship

1. **Strip** — everything in §2 removed, unrequested reformatting reverted.
2. **Validate** — the six checks, plus execution of every changed path, plus a
   read of each diff against its stated mechanism. **A fix whose diff does not
   match its `FINDINGS.md` entry is rejected, not reconciled.**
3. **Re-ship** — repackaged under this repo's naming, with a `GENESIS.md` line
   written on the box and a land command carrying its own verification.
4. **Land** — by the operator, one revision at a time.

⚠️ **A DISAGREEMENT IS A FINDING, NOT A DEFEAT.** If a fix is rejected you get
told why, and if the rejection is wrong you should say so. **Two of this repo's
better decisions came from the operator overruling an analysis** — the panel
correlation argument and the condor's tine-order question both changed the
design.

---

## 7. Go hard

The repo is 100 modules and roughly 30 hours old. **It has already found 18 of
its own bugs in one stress run, six revisions that exist only to correct earlier
ones, and two checkers of mine that could not fail.**

**Assume there are more. Assume the next one is an instrument, not a trade.**
