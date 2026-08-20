# WORKING_AGREEMENT.md — how we operate (read this first, every new thread)

This file is operating discipline for the assistant across threads. None of it is
about the trading system's *logic* (that's OBSERVATIONS.md / ROADMAP.md) — it's
about **how work gets done here without repeating mistakes that have each cost
multiple sessions.** Every rule below was learned the painful way.

New thread? Read this file before touching anything.

---

## 1. Commands must be SINGLE-LINE. No exceptions.
The user runs commands on mobile (Termius) through the fleet **service-menu
fan-out**, not direct SSH. Multi-line anything gets **truncated and butchered**
before it runs.
- **NO** heredocs (`<<'EOF'`), **NO** multi-line `python3 -c` blocks, **NO** line
  continuations, **NO** pasted scripts. One line, always.
- If logic needs more than one line, write it as a file, have the user download/stage
  it, and run it as `python3 script.py` — do not inline it.

## 2. Quoting must survive the menu's SSH wrapping.
The menu wraps the command and ships it over SSH, adding **an extra shell-quoting
layer** vs. a direct prompt. Nested quotes collide with that wrapping.
- Keep to **one consistent nesting level**. When a command needs both quote types
  (e.g. a `sqlite3 "SELECT ... '2026-07-24' ..."`), structure it so the menu's extra
  layer doesn't collide — and never go three deep.
- Give **menu-ready** commands, not direct-shell commands.

## 3. Know which box you're on. The paths differ — this bit us repeatedly.
- **Bot / fleet boxes:** the running bot's working directory is **`~/options-trader`**
  (NO suffix). Per-box `trades.db`, the live process, and per-box data live here.
  Fleet commands run via the menu fan-out (option 14) and execute in this dir.
- **Control / reporter box** (`ip-...-32-218`): has TWO relevant dirs —
  **`~/options-trader-v3`** = the clone of the GitHub repo (repo name is
  `options-trader-v3`), and **`~/day_trader_pro`** = the reporter + devtools service
  menu (`./dev*`), the replay harness, the diary, `reports/`, `fleet_trades_<date>.json`.
  The control box has NO running-bot `trades.db` of its own.
- **The trap:** `~/options-trader` exists on **bot boxes**, NOT on the control box.
  Sending `cd ~/options-trader` while the user is on the *control* box fails (this
  happened, repeatedly). Always resolve the path to the box the user is actually on:
  bot box → `~/options-trader`; control box → `~/options-trader-v3` (repo) or
  `~/day_trader_pro` (tooling).

## 4. Landed files go to /home/ubuntu, then get moved/extracted.
When the user uploads files to a box — TAR archives or loose files — assume they land
in **`/home/ubuntu/`**. We extract (TAR) or move (loose files) into the repo with
commands **before staging and committing**. This worked well when both sides assumed
the same thing; assume it by default.

## 5. Version-control & housekeeping discipline is NOT optional.
Stale headers, banners, and changelogs bit us repeatedly (a banner reading v3.5 while
the code was v3.7; two divergent `candle_feed.py` lineages). Every file the assistant
edits:
- **Bump the header/version** and add a **dated changelog line saying what changed.**
- **Update the banner/log-version string** if the file logs one, so it matches the header.
- Never leave a changelog describing behavior the code no longer has.
- If a doc references the changed code (README file-structure tables, etc.), update the
  reference in the same edit so the repo never self-contradicts.

## 6. Verify the deploy landed BEFORE restarting. Every time.
Pushes have silently failed or been clobbered more than once (a fix landing three
times and vanishing; parallel edits overwriting each other). The gate:
- After `git fetch && git reset --hard origin/main`, echo a **version + marker check**
  (`echo "v=$(grep ...) marker=$(grep -c ...)"`) and confirm the expected values
  **before** `systemctl restart`.
- Never restart on an unverified/unexpected version string. If it's wrong, the push
  didn't land — fix the push, don't restart.

## 7. One owner per file.
Two agents (assistant + Fable) editing the same file through the repo with no merge
created divergent lineages that cost days.
- The assistant **retains ownership of a file until it proves unable** to accomplish
  the task; only then does it go to Fable, via a tight spec.
- When editing a file another agent owns (e.g. Fable's `entry_engine.py`,
  `order_confirm.py`), **build from repo HEAD in that file's existing idiom** — do not
  create a second lineage. Preserve its conventions (signed-price, confirm machinery, etc.).

## 8. Clone HEAD and READ before editing. Memory is not evidence.
The assistant burned turns "fixing" code from a stale mental model, and had to be
stopped. Hard rule:
- Every edit starts with a **fresh clone** and **reading the actual current file.**
- Any question about repo state ("did this land?", "what's uncommitted?") gets a
  **clone-and-grep**, never a recollection. (Answered one such question from memory and
  was wrong — said the Fable spec was missing when it was the replay bookmark.)

## 9. Prove it in the sandbox before presenting.
Fixes that stuck were run against real data / a real repro first. Fixes asserted from
reasoning embarrassed us.
- Standard = **compiles + behavioral proof against real rows/tape**, shown, before the
  file is presented. "This should work" is not proof.

## 10. Live vs. replay vs. paper is a real distinction — always name it.
We nearly fixed *production* for what were **replay-only** artifacts (ADX cold-start
until 14:00 was the replay's single-day resample, not live), and nearly trusted
**paper** numbers that were optimistic vs. live ($0.00 hard-close fills; entry-only
slippage). Before diagnosing anything, ask: **is this the live path, the replay/diary
path, or the paper fill model?** They fail differently and get fixed differently.

## 11. Check the user's prior — don't just confirm it.
Twice the user held a strong belief and the valuable move was to **test it against
data**: once it confirmed (live regime_log proved ADX warm at the open), once it
retracted a wrong read (sweeps "fading a trend" was over-fit to one day; LOW-sweeps are
83% lifetime). Agreement is cheap; a checked answer is the job.

## 12. Thin samples find mechanisms, not conclusions.
n=7 (one session) tells you **what to look at**; n=99 (many sessions) tells you **what's
true.** No dial moves on one session. When the user says "understand it, don't fix it
yet," that is the correct discipline — capture it in OBSERVATIONS.md and let it stack.

---

## 13. The control box already has a devtools SERVICE MENU. Use it before building.
On the control box (`~/day_trader_pro`, run `./dev*`), the **devtools service menu**
(v1.22 as of 2026-07-24) already exposes most of what we reach for. Before writing a
query or script, check whether a menu option does it. Reference (numbers may drift —
re-read the menu if unsure):

- **Orchestration:** 1 full spool-up (mock) · 2 EOD aggregate (mock) · 3 reset mock ·
  4 dry-run spool-up (real reads) · 5 dry-run EOD aggregate (real reads)
- **Registry & master switch:** 6 instance map · 7 reconcile map · 8 swap/pin instance
  ID · 9 control status · 10 ENABLE control · 11 DISABLE control
- **Fleet (inspect & fan-out):** 12 fleet list · 13 fleet ping ·
  **14 Run command (all running)** ← the fan-out we use for fleet commands ·
  15 status.py+query.py (one/all/some) · **16 Pull trades.db (one/all/some)** ·
  17 Pull OHLC for a day (one/all/some)
- **Debug/logs (remote):** 18 service status (bot+candle-feed) · 19 journal tail ·
  20 feed health (store freshness) · 21 bot log tail
- **Maintenance (wake_and_bake):** 22 dry-run · 23 FULL (wake→bake→restart→STOP) ·
  24 wake · 25 bake only (sync, no restart — RTH-safe) · 26 leave on · 27 EMERGENCY STOP
- **Repoint (migrate fleet→new repo):** 28 check · 29 full · 30 full+wake · 31 no
  restart · 32 scoped · 33 mock preview
- **Snapshot & tests:** 34 snapshot dir→repo-ready tarball · 35 test selection (mock) ·
  36 test Telegram
- **Control repo ↔ GitHub (force sync):** **37 PUSH→GitHub (this server = source of
  truth)** · **38 PULL←GitHub (GitHub = source of truth)**
- **Trades data:** **39 re-run consolidation→`fleet_trades_<date>.json`(+.csv)** ·
  **40 excursion report (MFE/MAE)→`reports/excursions_<date>.txt`** ·
  **41 trade breakdown (cross-day: regime/strategy/grade + regime×strategy)**
- **Regime validation (L1 confluence, tape-only):** 42 run replay today · 43 replay a
  date · 44 view a day's report · **45 view the diary (all days)** · 46 backfill missing
  days · 47 A2 co-occurrence + HTF drift (auto-finds replay logs)
- **EOD/backfill/live P&L:** **48 live P&L standings (read-only)** · 49 backfill missing
  OHLC · 50 EOD conductor (dry-run→confirm→run)
- **Utilities:** 51 OHLC 21-day fetch (yfinance) · 52 rotate fleet tokens/secrets ·
  53 audit fleet credentials (read-only) · 54 verify fleet credentials WORK (TT SDK,
  Telegram, GitHub)

**Rule:** if the user needs trades pulled, a report, a replay, live P&L, or a deploy —
a menu option almost certainly exists. Point them at the number instead of writing a
one-off. The excursion/breakdown/diary reports (40/41/45) are already the analysis
surface we keep re-deriving by hand.

## 14. Data lives in SEPARATE folders — candles, trades, reports.
On the control box the data is split by kind, not co-mingled:
- **candles / OHLC** — its own folder (the replay/backfill tape; `data/OHLC/<date>/…`).
- **trades** — its own folder (`fleet_trades_<date>.json` / `.csv`, per-day consolidated).
- **reports** — its own folder (`reports/excursions_<date>.txt`,
  `reports/regime_replay_<date>.jsonl`, the diary, etc.).
When looking for a file, go to the folder for its *kind*; don't assume everything sits
together. (This is why "which file / which folder" questions get a `ls` of the right
subfolder, not a guess.)

---

## 15. DELIVERY IS A TARBALL PLUS ONE LINE. Nothing lands by hand.
Added 2026-08-01. Every presented file, patch or hotfix ships as **one archive**
built with **`tar czf` (.tar.gz)** — Termius prefers compressed. It arrives in
`/home/ubuntu` renamed `.tar` (the `.gz` is stripped in transit; verified by
screenshot 2026-08-01, a 22 KB gzip payload named `...r2.tar`). That is harmless
provided the extract is **`tar xf`**, which sniffs the compression — **never
`tar xzf`**, because the arriving name lies. The 2026-07-25 breakage was the
extract FLAG, not the compression.
- Underscores survive the Termius upload; do NOT build glob-resolution for
  spaces (that was a different transfer path, and predicting it here was wrong).
- Archive filenames are **unique per delivery** (`_r2`, `_r3`). A second download
  of a name already in `/home/ubuntu` has nowhere to land, so `tar xf` silently
  re-extracts the FIRST archive and the fix appears not to have shipped.
- The archive carries **no MANIFEST or scaffolding**, and the deploy line deletes
  the archive itself. Nothing operational is left loose in the home directory.

**The single line does the whole deploy**, semicolon-separated, cwd-independent,
quoted filenames: pull HEAD → extract into the nested directories → verify
supersession → stage → commit → push → clean up. Pull FIRST so the extract lands
on true HEAD and a dirty tree fails loudly instead of quietly merging.

**The supersession gate keys on CONTENT, not version strings.** Each file is
grepped for BOTH its header/changelog line AND a distinctive line from the actual
change, plus a NEGATIVE check that the superseded code is gone. A header bump
with no real edit must fail. On any flag: **fail loudly, stop, stage nothing,
keep the archive — never push.** This protects both sides and keeps the
assistant honest about version headers and changelogs.

## 16. LONG-RUNNING WORK GOES IN TMUX.
Added 2026-08-01. Suite runs, corpus replays and regenerations, backfills — open
them in a tmux session so a dropped mobile connection cannot kill the job. Give
the tmux-wrapped form in the command itself, not as an afterthought. Do not pipe
pytest through `tail`/`tee` inside an `&&` chain; redirect to a file and echo
`rc=$?`, or the exit code is swallowed and the check is decorative.

## 17. TELEGRAM IS AN EMERGENCY SERVICES CHANNEL.
Added 2026-08-01, operator's framing, and it governs everything that pages.
Nothing routine goes there — *"I just don't want to see it when I know it's down
for a reason."* A condition that is EXPECTED (outside RTH, a maintenance wake, a
box deliberately stopped) must never reach that channel, or it stops being read
and fails the one time it matters.
- **Gate the paging and the log level, not the detection.** Records stay accurate
  outside RTH so callers that legitimately run then (`get_orb_range`, `status.py`,
  the EOD chain) still get a true answer. Not fully dark — just not paging.
- **A per-tick warning is spam, not observability.** Emit once per episode and
  re-arm on recovery — the one-time-per-key idiom `candle_feed._log_backfill_depth()`
  already uses. A first attempt at the trend-vote starvation warning logged every
  tick and buried the log; an alarm that spams is an alarm that gets filtered,
  which is how three dead timeframes went unnoticed in the first place.
- **A drill must be unmistakably a drill.** Test alerts carry a `DRILL — NOT REAL`
  prefix and exercise the REAL code path (`tests/blind_alert_selftest.py`, devtools
  56). A test that looks real IS a false alarm, and a channel that has cried wolf
  once gets read more slowly forever.
- **An alarm that has never fired is one nobody knows works.** Alerts fire in
  PAPER too (tagged `[PAPER]`, without the manage-manually line) so the path is
  exercised daily before live capital depends on it.

## 18. EVERY DELIVERY CARRIES THE BACKLOG.
Added 2026-08-04, operator's instruction, when this thread became the primary and
only conversation for building, testing and deploying. One thread owning
build → test → deploy means this repo's docs are the only durable record it
leaves; a commit is the change, the backlog is what survives the thread.
- **`docs/BACKLOG.md` ships in every archive.** Not when it seems relevant —
  every time. It carries the progress of that delivery, the remaining
  deliverables, a **title-line version bump** and a matching **PART 4 changelog
  entry**. A delivery without it is incomplete, because **EV moves only when the
  backlog records it** — shipping, testing and pushing five artifacts changes EV
  by zero until the item is marked.
- **BUILT / PUSHED / BAKED are three different claims.** Written and proven on
  the desk; on origin with the checkout in parity; live on the fleet boxes. Only
  the third changes any of the data being collected, so a PUSHED item is ◐ and
  never ✅. Conflating them writes a green into the record that the tape does not
  support.
- **Record the gap, not just the win.** A verification that was planned and not
  actually read (a suite summary that scrolled past, a per-box line nobody
  opened) goes in the ledger as an open step. The recurring failure class here is
  output that renders cleanly while meaning something other than it appears —
  a laundered green is worse than a red.

## 19. COMMANDS GO IN A CODE BOX, ON ONE LINE, SEMICOLON-SEPARATED.
Added 2026-08-13, operator's instruction. Two halves of one failure: a command
the operator cannot copy cleanly is a command that runs wrong.

- **PRESENTATION — every command the operator will run goes in a fenced code
  box.** Not inline backticks, not prose-wrapped. A command sitting in a
  paragraph picks up soft line-wraps and typographic quote substitution on
  mobile, and the operator has to reconstruct it by eye before pasting. The code
  box is the delivery mechanism, not decoration.
- **FORM — one line, `;` separated.** §1 already forbids multi-line; this fixes
  the separator too. No heredocs, no continuations, no blank-line-separated
  steps the operator is expected to run in order — a sequence they have to
  perform is a sequence that gets performed halfway.
- **THE ONE THING `;` COSTS, AND HOW TO KEEP IT.** `;` does not short-circuit,
  so a failed verification would sail straight on into `git commit && git push`
  — the exact opposite of §15's requirement to fail loudly, stage nothing and
  keep the archive. So the destructive half lives inside a single-line
  conditional: `... ; if [ gate ]; then commit; push; rm archive; else echo
  "GATE FAILED"; fi`. Semicolons separate the STEPS; the `if` protects the ones
  that must not run on a red. Never let a bare `;` carry a chain whose later
  steps depend on an earlier step succeeding.
- **Corollary already learned the hard way (2026-08-13):** a tool that exits
  non-zero on an empty-but-valid result will cancel a trailing `&&` clause —
  that is how an `&& rm -f` failed to clean up three times running while the
  command looked like it had worked. Under `;` that specific trap disappears,
  which is part of why `;` is the default; the conditional above is what
  replaces the protection `&&` was providing.

## 20. AN ABSENCE CANARY TESTS FOR A DEFINITION, NEVER FOR A MENTION.
Added 2026-08-13, after the trap fired for the THIRD time in this repo. The
first two were `_orb_quality` and `main` v5.6's absence test. The third was
caught by a brand-new test on its first run: the check asserting a removed
config block had not come back matched the CHANGELOG ENTRY DESCRIBING ITS
REMOVAL.

**The mechanism, and it is unavoidable rather than careless.** Rule 5 requires
every edit to carry a dated changelog entry saying what changed. When what
changed is *"we removed `FOO`"*, the honest entry contains the token `FOO`. A
canary written as "`FOO` must not appear in this file" is then guaranteed to
trip on the very documentation the version discipline demands. **The two rules
collide by construction — good hygiene creates the false positive.**

**So scope the canary to the SHAPE OF A DEFINITION, not the presence of a
string:**
- config constants → `^FOO\s*=` (assignment at line start)
- functions → `^\s*def FOO\(`
- call sites → `FOO(` rather than `FOO`
- imports → `^from .* import .*FOO` rather than `FOO`

**Why this matters more than it looks.** A canary that fires on documentation
trains you to loosen it, and the loosened version is the one that misses the
real regression. A false positive on an absence check is not a minor annoyance;
it is the failure mode that disarms the check. The alternative — writing
changelog prose that avoids naming what it removed — is worse: it degrades the
record to protect the test, which inverts what each is for.

**Corollary for the writer.** If you find yourself carefully NOT spelling a name
in a changelog so a grep stays green, stop: the canary is wrong, not the prose.
Fix the pattern.

**Corollary for the reviewer.** A canary that has never gone red is one nobody
knows works. This one failed on its first run and that is the only reason its
scoping can be trusted — same principle as §17's "an alarm that has never fired
is one nobody knows works", and the same reason every fixture in this repo
carries a deliberate-failure check.

---

## 21. A TEST THAT READS SOURCE TEXT PROVES NOTHING ABOUT RUNTIME.

Added 2026-08-14, after **162 tests passed over a `NameError` that crash-looped
every box that opened a condor leg.**

`exit_engine` v4.20 called `is_trend_participation(record)` and **never imported
it.** Twelve tests covered that path. Every one asserted the *source text*
contained the string `is_trend_participation(record)` — which it did. **The bug
was that the name was never bound.** The tests asserted the MENTION of the thing
whose BINDING was missing. That is Rule 20 one level up: there, a canary matched
a changelog describing a removal; here, a chain test matched a call it could not
execute.

The cost was not theoretical. The exception escaped into the tick loop's error
counter — 30 errors at 15s ticks — so `sys.exit(1)` about **7.5 minutes after any
condor leg opened**, then a systemd crash-loop.

**THE RULE, in three parts:**

1. **At least one test per exit path must CALL `evaluate()`** with a realistic
   record and assert on the returned decision. Not the source, the decision.
2. **In BOTH shapes: fresh and rehydrated.** A record built by `make_record`
   carries in-memory keys; the same record after `SELECT *` carries only
   columns. **The two differ in exactly the fields that keep breaking.**
3. **A chain test must include HOP 0 — the dispatch.** "The exit gates on the key
   the record sets" is vacuous if the record never reaches that gate. It did not:
   `evaluate()` routed on `strategy == "IronCondorStrategy"`, and the fix three
   hours earlier had changed that field to `"TrendCreditSpread"`.

**The proof a test is real:** it FAILS against the broken version. Run it against
HEAD before the fix. If it passes there, it is testing something else.

---

## 22. A FIELD READ OFF `record` MUST BE A COLUMN, OR IT DIES ON RESTART.

Added 2026-08-14. `is_trend_credit` was written into the in-memory `TradeRecord`
and is **not one of the 69 columns**. `get_open_trades_live()` does `SELECT *`,
so **every restart rehydrated an open position without it** and the exit branch
gated on it silently stopped firing. **A restart happens on every bake.**

**Before adding any field that management or exit logic reads: check the
`CREATE TABLE trades` column list.** If it is not there, either add the column or
**derive the value from fields that are.**

⚠️ **PREFER DERIVING.** A new column fixes tomorrow and not today: every position
opened before the migration still rehydrates without it, `SELECT *` returns
`None`, and `None` reads as `False` — **the exact failure, silently.** Deriving
works on rows that already exist. See `strategy/structure.py`.

⚠️ **AND DERIVATION MUST FAIL CLOSED.** An unrecognised record gets the most
restrictive management, never the loosest. A misread must not hand a position a
looser exit than it earned.

The same applies to in-memory dicts on the engine: `self._condor_ratchet` held an
earned stop tier that **every bake reset to the base stop**. If state must
survive a restart, it rides a column.

---

## 23. FIX THE HOP UPSTREAM, NOT JUST THE ONE THAT BROKE.

Added 2026-08-14, after an adversarial audit found nine defects — **five of them
introduced the same day, each while fixing the previous one.** The pattern was
identical every time: **the defect was repaired where it was found, and the hop
that FEEDS it was never checked.**

- Changed the record's `strategy` field. Did not check what DISPATCHES on it.
  → every new record routed to the debit evaluator.
- Added a call. Did not check the IMPORT. → `NameError`.
- Stopped stamping `is_condor_leg` on one trade type. `position_manager` priced
  spreads by exactly that flag. → the fix would have broken pricing had the
  paired change not shipped in the same commit.

**Before shipping a change to any field, flag or name: `grep` for every READER,
not just the writer you are editing.** A patch that fixes the writer and not the
reader is the bug being fixed, moved one file over.

**And ship coupled changes in ONE commit.** If A breaks without B, they are one
change wearing two filenames.

---

## 24. VERIFY THE EDIT LANDED. A SILENT NO-OP LOOKS EXACTLY LIKE SUCCESS.

Added 2026-08-14. The `NameError` above came from a scripted `.replace()` whose
anchor string **appears zero times in the target file.** The replace succeeded,
changed nothing, reported nothing, and the call site landed without its import.

**Any scripted edit must assert its anchor matched** — `assert s.count(old) == 1`
before replacing — and **any edit must be verified by reading back the RESULT**,
not by the absence of an error. `python -c "import <module>"` catches an unbound
name in one second; it was not run.

⚠️ Related: **a canary pinned to a VERSION STRING rots on the next legitimate
bump.** Four canaries checking for `v6.1` and `v1.6` were failing at HEAD purely
because those files had advanced — training the reader to skim past failures
while a real one looks identical. **Canaries check BEHAVIOUR** — a dispatch
clause, a conditional — **never a version number.**

---

## 25. READ EVERY `.md` IN BOTH REPOS BEFORE WRITING CODE. NOT ON DEMAND.

Added 2026-08-14, at the operator's instruction, after the cost was paid.

The thread's opening instruction was *"read all available md files in both
repos."* `BACKLOG`, `WORKING_AGREEMENT` and `MECHANICS` were read on demand;
`ROADMAP`, `VALIDATION`, `HISTORY`, `FILE_MAP` and the whitepaper were not read
at all. Two days of work sat on that gap.

**What it cost:**
- A **774-line replay simulator** was built that duplicated
  `tests/replay_confluence.py`, which had done as-of replay with
  `--warm-sessions` **since 2026-07-21** — and the rebuild reintroduced the exact
  bug that file's v2.2 shipped to prevent (uncapped frames, so the replay sees
  more history than live). It reported *"100% of the trend vote live"* as an
  achievement. **By this repo's own standard that is the defect.**
- A **live module with 14 call sites across five files** was modified to serve
  that test artifact, without consulting `FILE_MAP.md` as Rule 7 requires.
- A **new doc file** was created against `docs/README.md`'s explicit rule.
- Priorities were ranked for two days **without `ROADMAP.md`**, the document that
  defines the critical path.

All of it was reverted. **`docs/README.md` routes by question — read it first,
then read the rest before writing anything.** The half hour costs less than one
duplicate module.

---

### Companion files
- **OBSERVATIONS.md** — evidenced findings about the *system*, deferred fixes.
- **ROADMAP.md** — the L1→L2→L3 build plan and where each piece stands.
- **README.md** — architecture + defect log.


---

## Operating notes migrated from the root README (2026-07-28)

### Bytecode cache

**Always purge the bytecode cache before restarting.** This is the single most common cause of "I
pushed the fix but it's still broken" — and it matters more than usual right now, because v3.4
renamed the `ORBState` strings.

### Monitoring and mode

Monitoring: `python status.py` · `python query.py` · `bash configure.sh` (risk, mode, daily-loss
cap override).

---

## 26. TARBALL NAMING IS SEQUENTIAL AND NEVER RESETS.
Added 2026-08-19, carried into v4. Revisions run `r1`, `r2`, ... `r101`, `r199`
and keep counting across the life of the project. A re-issue of the SAME
revision suffixes: `r185_r2`, `r185_r3`.

**Why it matters beyond tidiness:** on 2026-07-25 a corrected archive was
re-shared under a filename already used earlier in the same conversation. The
second download had nowhere to land, `tar xf` silently re-extracted the FIRST
archive, and the fix appeared not to have shipped. Two rounds were spent
insisting the operator had not extracted the file when the delivery was at
fault.

⚠️ AND THE OUTPUTS SLOT HOLDS ONE FILE. Building a new tarball overwrites the
previous one before the operator has necessarily fetched it — 2026-08-19, twice.
If a tarball is superseded before it lands, say so explicitly and re-cut it.

## 27. EVERY LANDED TARBALL CARRIES A CLEANUP LINE.
Mandatory, not optional. The extract directory and the archive both go, in the
same one-line command that landed them, guarded by the §19 conditional so a red
verification never reaches the `rm`.

**Learned the hard way:** stray `MANIFEST.txt` and `trades.db` files were found
tracked in the repos, left behind by delivery scaffolding from archives that
were supposed to clean up after themselves and routinely did not.

## 28. TESTS AND TOOLS LIVE IN `/tests`. NOTHING AT REPO ROOT.
Added 2026-08-19, operator's instruction. OTV3's control checkout accumulated
27 loose files at the root at an alarming pace. A tool at the root is a tool
nobody can find, nobody re-runs, and everybody rebuilds.

## 29. BOT INDEPENDENCE IS A FEATURE, NOT AN ACCIDENT.
Added 2026-08-19, operator's instruction. Each box trades standalone. Control
orchestrates, verifies and reports — **no box may require control to be
reachable in order to trade.** Any design that makes control load-bearing for
entry or exit is wrong, however convenient.

## 30. COLLECTION IS FLEET-WIDE. TRADING IS PANEL-ONLY.
Added 2026-08-19. 15 traders, 29 collectors. **A box that stops collecting
because it is not trading is a box whose pitchfork and ADX warm-up depth quietly
dies** — and DXFeed history is same-evening only, so that depth cannot be
recovered afterwards. Pruning is disabled specifically so it accumulates.

## 31. MEASURE DOLLARS BEFORE TRUSTING A NUMBER.
Added 2026-08-19, and it is the lesson OTV3 cost two months to learn. Every
acceptance row, ramp calibration and conviction integration measured the engine
against **its own outputs**. The first non-circular test — does the label predict
which side wins — was run on 2026-08-19 and returned **44.9% direction accuracy
on 715 trades, CI [41.3%, 48.6%]: worse than a coin.**

**A number that has never been tested against P&L does not size anything.**
Every gate ships LOG-ONLY and is judged on outcomes before it is allowed to
refuse a trade.

## 32. READ THE INHERITED DOCTRINE BLOCK BEFORE EDITING A FILE.
Added 2026-08-19, and it is the condition on which that block was kept.

Every ported file carries an `INHERITED DOCTRINE` header: the measurements that
justify its thresholds, the design guarantees, and the defects that recur when
forgotten. It is not a changelog. **Read it before you touch the file.**

⚠️ **THE REQUIREMENT EXISTS BECAUSE THE ALTERNATIVE WAS MEASURED.** Asked
directly whether these headers were actually read, the honest answer was no —
not reliably, and only when already investigating something. And the cost is on
the record:
· `structure.py` had said **"`is_trend_credit` IS NOT A COLUMN"** since
  2026-08-14. On 08-17 that exact field crash-looped NFLX every 15 seconds and
  an investigation rediscovered it from scratch.
· `_session_extremes` carried **"neither is guaranteed to reach 09:30"** in its
  own docstring — the precise caveat that would have prevented TCS.3, where the
  opening-range bound was dead for the entire credit window.

**Two days lost to knowledge the repo already held.** Keeping 280 KB of doctrine
is worth nothing without the habit; the habit is this section.

**What counts as reading it:** if a threshold, a veto, a bound or a default is
being changed, find the line that explains why it is what it is. If there is no
such line, that absence is itself worth noting in the commit — an unexplained
constant is a future investigation.

⚠️ **AND THE HEADER IS NOT THE ONLY PLACE.** Today's failures were as often
"did not run the test that already existed" as "did not read the header" —
`test_dispatch_slot_map` had a pin that caught a regression I would otherwise
have shipped. **Run the module's tests before editing it, not only after.**

## 33. THE FILE MAP IS GENERATED INSIDE THE LAND COMMAND, AND DRIFT FAILS.
Added 2026-08-19.

`docs/FILE_MAP.md` is produced by `tests/gen_file_map.py` from the real import
graph — parsed, never executed, so a module that crashes on import still maps.
**The generator runs INSIDE the land command**, between the verification gate
and `git add`, so the commit always carries a current map:

    extract → verify → REGENERATE MAP → APPEND GENESIS → git add -A
            → commit → push → cleanup

If regeneration reports broken imports, or `--check` reports drift, **the gate
fails and nothing stages.** Operator, 2026-08-19: *"I'm in favour of good
discipline as a backstop to sloppy execution."* A warning that fires on every
structural change gets ignored within a week — which is exactly how v3's map
came to be written from memory.

**WHY IT EARNS ITS PLACE.** v3's map was hand-maintained and its own header
admitted the consequence: *"it is a snapshot, and it will drift."* It did. At
the v4 split a module was nearly excised on a reading of its imports while the
map recorded its fan-in as **12 — third highest in the codebase.**

⚠️ **THE THREE FAILURES IT CATCHES WERE ALL SEEN FOR REAL DURING THE PORT:**
· **Broken local import** — eight files after the deliberate engine drop, found
  by running imports BY HAND because nothing checked.
· **Orphans** — twenty files silently omitted from the port manifest. Nothing
  errored, because an absent file breaks nothing until it is needed.
· **Drift** — the map disagreeing with the code.

⚠️ **AND AN ORPHAN REPORT MUST BE TRUSTWORTHY OR IT IS NOISE.** The first run
flagged 12; **only 2 were real.** Services and CLI helpers SHOULD have no
importers, and three modules were missed because the resolver did not handle
`from <package> import <module>` — the form used by
`from strategy import credit_vertical as cv`, a module that was live and had
traded four times the day before. **I was one step from "wiring in" working
code on the strength of a broken checker.** Entry points are listed explicitly;
the resolver handles both import forms.

## 34. TESTS ARE CONTROL-ONLY. OBSERVERS SHIP TO TRADERS.
Added 2026-08-19, operator's instruction.

    ships to a box   analysis/ data/ execution/ strategy/ risk/ database/
                     notifications/ utils/ warehouse/ shadow/ deploy/
                     main.py config.py + install scripts
    CONTROL ONLY     tests/ — every harness, probe and replay tool

**Harnesses read banked tape and trade databases. They never run on a box
mid-session**, and a t2.micro that has already been OOM-killed once (SPX, 419 MB)
should not carry code it cannot use. **Observers are the exception and DO
ship** — `shadow/` collects in-session, which is the data a future scorer is
earned from.

Enforced by **sparse checkout** in `install.sh`, not by a post-pull `rm`: the
setting persists in the clone's config, so a box configured once stays correct
through every later pull in a bake. **A cleanup step that must be remembered by
every future deploy path never happens.**

## 35. EVERY SHIPPED REVISION GETS A GENESIS LINE, IN THE SAME COMMAND.
Added 2026-08-20.

`docs/GENESIS.md` carries one line per tarball, in order, from r1. It is not
`git log`: git records WHAT changed, this records **WHY**, and the reasoning is
not derivable from the diff. *"ADX measured flat across every band, so strike
selection moved to ATR"* is the sentence that saves a future engineer a day; the
file list is not.

**It is appended INSIDE the land command**, between the map regeneration and
`git add`. ⚠️ **This one cannot be enforced mechanically and that is exactly why
the timing matters.** No checker can tell whether a line is truthful or whether
an entry is missing — the file map fails the gate on drift, Genesis cannot. It
stays honest only by being written before anyone has moved on to the next thing.

⚠️ **IF A REVISION EXISTS TO FIX A PROBLEM, SAY SO PLAINLY AND SAY WHAT THE
PROBLEM WAS.** Operator, 2026-08-20: *"if a package was created to fix a problem
absolutely state that."* **Six of the first twenty-five revisions exist because
an earlier one was wrong**, and the pattern across them is worth more than any
single entry: in every case **the measuring instrument failed before the code
did**, and every one of them printed something plausible while doing it —
· a manifest built from a description list, silently missing 20 files
· an orphan report flagging 12 modules of which only 2 were real, three of them
  live code the resolver could not see
· a measure that contained its own predictor
· a grouping key carrying a per-trade value, hiding 107 trades as nothing
· a proxy never labelled unavailable, indistinguishable from data for years
· a threshold set before the measurement that contradicted it

### THE CANONICAL LAND HEADER — one string, used twice

Every land command opens with two variables, and the SAME description becomes
both the Genesis line and the commit subject:

    REV="r27"; DESC="what it did and why, in a full sentence"
    ...
    printf '| **%s** | %s |\n' "$REV" "$DESC" >> docs/GENESIS.md
    ...
    git commit -m "OTV4 $REV: $DESC"

⚠️ **ONE SOURCE, SO THEY CANNOT DIVERGE.** Written by hand in two places they
drift, or one gets forgotten — and a Genesis line that disagrees with its own
commit is worse than a missing one, because it reads as authoritative.

⚠️ **AND THE APPEND MUST COME BEFORE `git add`**, or the line ships in the
commit AFTER the one it describes and every entry is permanently off by one.
That ordering is why the description cannot be derived FROM the commit message:
the message does not exist yet.

⚠️ **AND `GENESIS.md` IS NEVER IN A TARBALL.** It is append-only on the box, so
a shipped copy is always stale by however many revisions landed since the sandbox
last synced — and `cp -r` runs BEFORE the gate, so it clobbers the good file even
when the gate then fails. That happened twice on 2026-08-20: rows went 32 → 28,
the gate correctly refused, and the recovery was `git checkout docs/GENESIS.md`.
**A failed gate does not leave a clean working tree.**

⚠️ **ONE RECORD, NOT TWO.** A `docs/SHIPPING_LOG.md` was drafted in the same
session as GENESIS, abandoned at r26, and rode into the repo inside r26's
tarball — tracked for seven revisions while describing itself as *"one entry per
tarball shipped"*. **Two documents claiming the same job is the exact failure
this repo keeps finding in its own code**, and whichever gets updated becomes
the truth while the other rots. Deleted; its `date` and `bake` columns were
better and were adopted.

⚠️ **WRITE IT GENESIS-STYLE, NOT COMMIT-STYLE.** A terse subject loses exactly
the reasoning that makes this document worth keeping. A long commit subject is
the cheaper cost.

**A GENESIS THAT ONLY LISTS SUCCESSES IS A MARKETING PAGE.** The corrections are
the part with the knowledge in it, and they are the first thing that will
quietly stop being maintained. They do not get dropped.

## 36. EVERY STRATEGY DECLARES ITS GATES IN THREE CATEGORIES.
Added 2026-08-20, operator's instruction.

Every strategy header carries a **GATE CATEGORIES** block naming each of its
conditions as one of:

**SELECTION** — measured preferences. Window, depth band, age, distance.
Loosening one produces a WORSE example of the same trade, which is exactly what
a debug session wants. **Relaxable.**

**FOUNDATIONAL** — the conditions that define the setup's IDENTITY. *"Some of
the parts of the setups are requirements and cannot be relaxed because they are
foundational."* Relax the sweep's reclaim and you are selling into a level price
is still through — **not a loose version of the setup, a different and much
worse one.** **NEVER RELAXED.**

**FEASIBILITY** — the vetoes that make a trade unwinnable however good it looks.
Below 0.05% ATR the required move was reached on **0% of 5,517 measured bars**.
**NEVER RELAXED.**

⚠️ **FOUNDATIONAL IS NOT A SYNONYM FOR FEASIBILITY AND COLLAPSING THEM LOSES THE
POINT.** Feasibility says *"this cannot pay"*. Foundational says *"this is not
that trade"*. A gate can be perfectly winnable and still be foundational — the
runaway's held 50% TP would produce plenty of fills if relaxed, and every one of
them would be an ORB plus a guess.

⚠️ **THE DECLARATION IS FOR THE READER AND THE AUDIT, NOT FOR THE CODE.** Before
this rule the relaxed behaviour could only be inferred from which gates happened
to be wrapped in `relaxed.widen()` — scattered across three files with nothing
stating the intent. **A new strategy whose author never made the distinction is
a new strategy that will relax something foundational**, and it will look
reasonable in review.

**THE DECLARATION IS DATA, NOT PROSE.** Each strategy carries a module-level
`GATES` dict mapping every gate constant to its category, and
`tests/check_gates.py` reads the CODE: it refuses any `relaxed.widen()` or
`relaxed.window()` call on a constant not marked SELECTION. Verified by
deliberately relaxing a FEASIBILITY gate and watching it fail.

⚠️ **A DOCSTRING CHECK WAS THE FIRST VERSION AND IT WAS THEATRE.** It asserted
the WORDS appeared in a header — which proves somebody wrote the right words,
not that the code respects them. It also asserted on exact source strings, the
brittleness §21 warns about.

⚠️ **AND IT IS A PLAIN SCRIPT WITH AN EXIT CODE, NOT A PYTEST FILE.** The first
version broke the land command on the box — **not because the code was wrong but
because the active venv had no pytest.** A verification that goes red on
ENVIRONMENT rather than CONTENT teaches the operator to ignore reds, which is
precisely the CV.1 failure. `check_imports.py` and `gen_file_map.py` run
anywhere; this one was the odd one out and it was the one that broke.

⚠️ **THE BEST FOUNDATIONAL GATE HAS NO KNOB AT ALL.** In all three strategies
the foundational conditions — the named pool and its reclaim, the held 50% TP,
PINNING with the apex on the pin — are tested inline against no constant. There
is nothing to pass to `relaxed.widen()`, so they cannot be loosened even by
mistake.
