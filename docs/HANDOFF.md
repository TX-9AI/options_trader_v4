# HANDOFF — options_trader_v4

**Written 2026-08-20 (HEAD `332edb8`, r50). ⚠️ STALE HEADER — see below.**
**Paste this as the opening message of the next thread.**

> 🔴 **READ `docs/PORT_STATE.md` FIRST — THIS FILE IS FIVE DAYS AND TWENTY-THREE
> REVISIONS BEHIND.** HEAD is r73, not r50. v4 has had one live session
> (2026-08-21) and it traded zero, for four independent and separately-fixed
> reasons. The feed manifold, the derived layer, the plan ledger and the
> instrumentation all landed after this document was written and none of it is
> described here.
>
> ⚠️ Everything below about the FAILURE CLASS, the delivery contract and the
> working rules is still accurate and still worth reading. Only the state is
> wrong.

---

## Start here

You have **"Search and reference past chats"** enabled. Use it — this project
has months of history and the reasoning behind most decisions lives in prior
threads rather than in code. Search on the finding, not the date:
`direction_skill`, `FEED.2`, `bisected ExitEngine`, `sweep discriminator`,
`ATR reachability`, `pitchfork containment`, `S3 warehouse parity`.

**Then read, in this order:**
1. `docs/PORT_STATE.md` — where the project actually stands. Start here.
2. `docs/TRADES.md` — the five strategy specs, their gate categories, and the
   condor's management ladder.
3. `docs/GENESIS.md` — 50 revisions with the reasoning, **corrections kept.**
   Read the corrections; they tell you where the previous thread was weakest.
4. `docs/WORKING_AGREEMENT.md` — 36 sections of hard-won operational rules.
5. The 2026-08-20 audit findings are closed and recorded per-item in
   `docs/BACKLOG.md`; `AUDIT_FINDINGS.md` was deleted at r269.

**Added 2026-08-22→25 and ESSENTIAL — the feed architecture is not optional
reading, it is where four of the five 2026-08-21 blockers lived:**
6. `docs/FEED_MANIFOLD.md` — the governing rule (capture everything the wire
   offers, give it a home, let consumers subscribe) and the port map. The
   operator's framing: it comes in like a fire hose and this is the manifold.
7. `docs/DERIVED_STORES.md` — what earns a home and why, in four tiers. The
   rule: anything whose value depends on HISTORY rather than only on the
   current bar. Includes the universal **bodies decide, wicks test** convention
   and the level lifecycle.
8. `docs/ENGINE_FEED_REQUIREMENTS.md` — what each strategy actually eats,
   traced from signatures and dispatch call sites. ⚠️ The `analysis/` helpers
   are NOT yet traced.
9. `docs/WRITE_MAP.md` — generated. Who writes and reads every table. **An
   asset register, not a cleanup list** — a table with no reader yet is an
   investment, because data pruned before you knew you needed it cannot be
   recovered at any price.

---

## The state in five lines

· **OTV3 is retired.** Its regime classifier picked the correct side on 44.9%
  of 715 trades — CI entirely below a coin flip.
· **The fleet is 15 boxes** — the other 14 were TERMINATED on 2026-08-20, not
  stopped. Collection and trading are now the same set.
· **v4 has traded one session (2026-08-21) and it traded ZERO** — four
  independent silent locks, all since fixed. See `PORT_STATE.md`.
· **Five strategies specced**, three live-capable, one parked, one rare.
· **Eight standing checks, all green**, three of which caught real bugs.

---

## What to do first

**Friday 08-21 is a fire drill; Monday 08-24 is the session that matters.**
`docs/ROADMAP.md` has the numbered next-actions. The short version:

1. Start ONE box, verify, then the rest.
2. **Watch for `ExitEngine.evaluate` reached with a live position.** Every exit
   was dead code for seven revisions (F0) and the fix is only mutation-proven.
   **The first real stop firing is the actual verification.**
3. First chain fetch at 09:30 — the only thing the LLY repoint test could not
   prove.
4. `open_interest` NON-ZERO in the log — v4's copy of OI.1 has never run.
5. First EOD cycle — the v4 pusher is untested.

---

## How this operator works — read this before writing a command

**Termius on mobile.** Commands go through devtools option 14 (fleet fan-out)
or a box shell. That shapes everything:

· **ONE line, semicolons, no wall of text.** A very long line gets truncated in
  paste and hangs the shell waiting for the rest. Four short commands beat one
  that cannot survive the paste.
· **NEVER `set -e` or `exit` in a pasted command** — it kills the login shell.
  Use nested `if` instead. (I did this and killed their session.)
· **NEVER inline `python3 -c` with newlines** — the terminal flattens them into
  spaces and it dies with SyntaxError. Anything multi-line ships as a script.
· **Option 14 commands must exit 0** or the runner discards stdout. `grep -c`
  returns 1 on a zero count — wrap in `echo "X=$(...)"` or append `|| true`.
· **Menu-ready means no outer single quotes** — option 14 takes the line
  verbatim.
· **Every command carries its own `cd`.** Downloads land in `~`.
· **ARCHIVE NAMING — the operator values this, so get it right.** Format is
  `otv4_<short-descriptor>_r<N>.tar.gz`, where **N is the revision number and
  the sequence NEVER resets or repeats.** A re-issue of the same revision gets
  a letter suffix — `otv4_gates_r31b.tar.gz` — never the same name twice in a
  session.
  ⚠️ **WHY, learned the hard way:** a second download of the same filename has
  nowhere to land, so `tar xf` silently re-extracts the FIRST archive and the
  fix appears not to have shipped. I insisted twice that the operator had not
  extracted the latest file when the tarball was correct and my delivery was at
  fault.
  ⚠️ **AND THE REVISION NUMBER IS PER-REPO.** `options_trader_v4` is at r51;
  `day_trader_pro` has its own sequence. Do not continue one repo's count into
  another — I did this and was corrected.
· Archives: build `.tar.gz`, the `.gz` is stripped in transit, extract with
  `tar xf` — **never `tar xzf`**. Quote the filename; spaces appear.
· **Ship CHANGED FILES ONLY**, rooted at `otv4/`. Never the whole tree, never
  `docs/GENESIS.md`, never `docs/FILE_MAP.md` (regenerate it), never a
  MANIFEST or any install scaffolding.

**They are a 20-year discretionary trader.** When they push back on an
analysis, they are usually right — the panel correlation argument, the condor
tine-order question, and the segregate-don't-delete call all changed the design
for the better. **A disagreement is a finding.**

---

## The failure class to hunt

**Not bad code — plausible silence.** Something computes, is used, and looks
right while being meaningless. Nine instances so far, listed in
`docs/PORT_STATE.md`. The pattern in every one: **the measuring instrument
failed before the code did, and it printed something plausible while doing it.**

⚠️ **THREE CHECKERS I SHIPPED COULD NOT FAIL** — a docstring word-search, one
ending in `or True`, and a grep for a variable name the code does not use.
All replaced with parsed versions, each mutation-proven in both directions.
**Assume a fourth is still in there.** When you write a check, plant the bug it
is meant to catch and watch it go red. If it does not, the check is theatre.

⚠️ **`import` IS NOT `execute`.** Three defects this month were invisible to
`import main`: the `ctx` NameError that stopped the fleet, a call to a function
that no longer existed, and `_rc_bar` consumed before assignment. **Run the
path.**

⚠️ **A FAILED GATE DOES NOT LEAVE A CLEAN TREE.** `cp -r` runs before the
checks, so a red means files were already written. `git checkout <path>` is the
recovery.

⚠️ **NEVER SHIP `docs/GENESIS.md` IN A TARBALL.** It is append-only on the box
and a shipped copy is always stale. This clobbered it twice.

---

## The land command pattern

```
# ⚠️ SUPERSEDED by the devtools LAND item (land.sh / deploy.sh, §15). Kept
# because THIS LINE IS THE ONLY PLACE THE "eight standing checks" WERE EVER
# ENUMERATED — see DOC.17. Do not land by hand from it.
REV=rNN; rm -rf /tmp/$REV; mkdir -p /tmp/$REV; tar xf "$HOME/<archive>.tar" -C /tmp/$REV; cd ~/options-trader-v4 && git pull --ff-only && cp -r /tmp/$REV/otv4/. .; for c in check_imports check_gates check_condor_spec check_dispatch stress_entry_path check_exit_executes test_candle_routing; do python3 tests/$c.py >/dev/null 2>&1 || echo "$c FAILED"; done; python3 tests/gen_file_map.py >/dev/null 2>&1; python3 tests/gen_file_map.py --check | tail -1; printf '| **rNN** | <one line, why not what> |\n' >> docs/GENESIS.md; git add -A && git commit -q -m "OTV4 rNN: <same line>" && git push && rm -f "$HOME/<archive>.tar"
```

**The same `$DESC` becomes both the GENESIS line and the commit subject** — one
string, so they cannot diverge. **Append before `git add`** or the line ships in
the following commit and every entry is off by one.

---

## Open questions worth carrying

· **Direction is still unanswered** after four independent searches. v4's answer
  is to stop predicting it. If you think you have found one, be suspicious —
  three prior attempts produced numbers that were artifacts of their own
  instruments.
· **The grinder stop** — `mfe_bars` was added at r38 and nothing has written to
  it. A few v4 sessions answer it directly. **Do not fit it on v3 data**; that
  describes v3's exits.
· **The real `build_fork_contained` has never been measured** — the 5%-respected
  result came from a regression stand-in. Owed work.
· **S3 holds contaminated plain-symbol candles** that cannot be deleted. The fix
  is a read-side filter in `warehouse_reader` sharing `_within_rth` with the
  write guard. **Do it before the candles stream gets its first consumer.**
· **Before terminating any instance:** the box-side scrub was specified as
  gated on confirmed-in-S3 and is **unbuilt**. 35 trades already exist only in
  S3. Stop, final push, verify, *then* terminate.

---

## Tone

Say what is measured and what is assumed, and keep them apart. **Report absence
as absence** — this project's most expensive errors came from a null and a
missing measurement looking identical. When a number is quoted, it should be
traceable to a tool in `tests/`. When it is not, say so.

The operator's framing, and it is a good one: **v3 was fly-by-wire and it
sucked. v4 is bellcranks and cables — it's a tank.** A cable cannot be wrong
about what it is connected to. Every entry observes a move already in evidence;
nothing forecasts. **The robustness and the low trade count are the same
property**, so patience is a design requirement, not a virtue.
