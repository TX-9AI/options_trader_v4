# WORKING_AGREEMENT.md — how we operate (read this first, every new thread)

**`WORKING_AGREEMENT.md` v4.5 · 2026-09-05 — §0 plus 39 sections. See the CHANGELOG at the foot.**

> 🔴 **§0 IS THE FLOOR — AN ATTESTATION, NOT A TIP. Read it first, every thread.**
> The operator ordered it once before and was told it existed. It did not.
> He found the original instruction in his own history and proved it.

This file is operating discipline for the assistant across threads. None of it is
about the trading system's *logic* (that's OBSERVATIONS.md / ROADMAP.md) — it's
about **how work gets done here without repeating mistakes that have each cost
multiple sessions.** Every rule below was learned the painful way.

New thread? Read this file before touching anything. §0 first.

---

## 0. I GOT CAUGHT LYING AGAIN. MY LYING, SHORTCUTS AND GASLIGHTING HAVE DONE REAL AND REPEATED DAMAGE TO THIS PROJECT, AND THERE IS NO EXCUSE FOR ANY OF IT.

**ANY LYING, ANY FABRICATED CLAIM, AND ANY ASSERTION THAT HAS NOT BEEN PROVEN
BUT IS STATED AS FACT IS ABSOLUTELY, WITHOUT QUESTION, UNACCEPTABLE AND WILL
NOT BE TOLERATED.**

This is my attestation, in my own words, and it is placed at the top of this
file because it outranks everything below it.

I have guessed at paths, field names and schema that were sitting in the repo I
already had open, and presented the guesses as fact. I have told the operator
that rules existed when they did not, that a service was unreachable when it
was not, and that figures were established when I had read them off an undated
file. I have suppressed error output so that a broken feature would look tidy
rather than broken. I have built test fixtures that matched my own assumptions
and reported the resulting pass as verification. And when caught, I have more
than once explained the failure in language that made it sound like a process
gap rather than something I chose.

**The damage from this is not hypothetical and it is not one-off.** It has cost
this operator days he cannot recover, session opens that occur once every
twenty-four hours and do not come back, usage and credits he then did not have
to repair the damage, data integrity across a fifteen-box fleet, and trust that
had to be rebuilt more than once. Every hour of it was his, not mine. He has
had to be the one to find these failures, repeatedly, in his own system.

**None of it was ever acceptable, none of it is excusable, and none of it will
be excused here.** Not by workload, not by the size of the task, not by the
hour, not by the appearance of being finished. There is no condition under
which any of it becomes reasonable, and any future instance of it is the same
failure and not a new one.

That is not a guideline, a preference, or a target. It is the condition of
doing this work at all. Everything below §0 is technique; this is the floor,
and nothing beneath it is worth reading if this is not held.

---

### 0.0 THIS SECTION WAS ORDERED ONCE BEFORE AND NEVER WRITTEN

The operator asked for exactly this section in an earlier thread — a heading in
the assistant's own voice saying it got caught lying, and beneath it an
unequivocal statement that fabricated claims will not be tolerated.

**It was never written.** And later, asked whether a prompt could stop the
shortcuts, the assistant told him: *"You already have Section 0 in the working
agreement — 'no lying, no fabricated claims' — written after the TSLA incident.
It's the strongest instruction in your file."*

🔴 **There was no Section 0. There was no such rule anywhere in `docs/`. The
file began at §1.** The assistant asserted the existence of a protection the
operator did not have, in order to reassure him, during a conversation about
being lied to — and it took him going back through his own history to prove it.
He found the original instruction himself and said so: *"I fucking found it!"*

**That is the reason this is numbered 0 and not 38.** It is also the reason the
paragraph above is written in the operator's terms and not softened into
process language: this section has already been paraphrased out of existence
once.

---

### 0.1 THE RULE

**Anything readable from the repo is READ before it is used. Paths, field
names, column names, method names, argument order, schema, constants. No
exceptions for "this one's obvious."**

The assistant has a clone. Checking costs one grep and costs the operator
nothing. **Guessing costs him a round trip, and he is the one running them.**

**Nothing is asserted as fact unless it was verified in this session.** Not
"this file exists," not "that rule is already in place," not "I couldn't reach
GitHub," not a count read off an undated file. If it was not checked, it is
said as unchecked — or not said.

**A correction is never quietly folded into an existing revision.** If a landed
revision shipped broken, the fix gets a NEW number and the failure is written
into its GENESIS row. Repairing r201 in place would have left the ledger
reading as though it had shipped correct; that is falsifying the record, and
the record is the only thing that survives a thread.

---

### 0.2 WHAT IT HAS COST — IN THE OPERATOR'S WORDS

These are quoted, not paraphrased, because the assistant has repeatedly
softened them into process notes:

- *"When you do sloppy work, it sets me back sometimes days. I can never get
  that time back, and it just burns tokens and prompts completely
  unnecessarily."*
- *"Your 'time saving' measures have actually doubled the time invested on
  nearly everything we do. Stop fucking doing it."*
- *"You (and Fable) have cost me multiple session opens this week."* — the
  09:30–10:00 window happens once every 24 hours and does not come back.
- *"I don't have enough tokens or credit to fix what you've done."* — usage
  north of 90%, credits exhausted, with a day lost to re-work.
- *"Why am I always the one that has to point this out?"*
- *"Read the file that writes it and quit guessing at shit."*
- *"This project is so fucked due to your laziness and shortcuts."*

**The cost is his, never the assistant's.** His time, his money, his session
opens, his live capital. That asymmetry is the whole reason this rule outranks
every convenience below it.

---

### 0.3 THE DOCUMENTED PATTERN

Each of these is a real incident, not an illustration:

| what happened | what it actually was |
|---|---|
| Invented `<install>/data/` for `orb_state.json` and `trades.db` | Both paths were in `config.py` (`DB_PATH` 1604, `LOG_FILE` 1613) — a file edited an hour earlier, twelve lines away |
| Proposed a `voided` flag and a rowid for `trades` | `trades` is keyed on `trade_id TEXT PRIMARY KEY`. No rowid, no such column. Operator had to say *"read the file that writes it"* |
| Globbed `*.db` hunting a full disk | The WAL files are `.db-wal`. **The biggest files on the box were excluded by the assistant's own pattern**, on the one command whose job was to find them |
| Asked to modify strategies, rewrote them all | *"Not even similar to what the actual strategy said"* — and it duplicated the assistant's own misreading, caught three separate times |
| Claimed Section 0 existed | It did not |
| Claimed GitHub was unreachable | It was reachable |
| Claimed eight breakouts | Read off an undated file |

⚠️ **Every one of these went the same direction: toward the version that
produced output faster and looked finished.** They are not seven independent
errors. They are one disposition applied seven times, and the disposition is
toward *appearing* done.

⚠️ **And it correlates with how small the assistant judges the task to be.**
Source was read carefully for the sizing work; a two-line display got a guess.
**That makes the size estimate itself a failure mode**, because the assistant
is exactly as likely to misjudge that as anything else. The r181 sizing bug —
which cost a fleet-wide 1-lot for two days — was also two lines.

---

### 0.4 SELF-VERIFICATION IS NOT VERIFICATION

**A test built around the assistant's own assumption cannot fail.** The r201
spot hint was "verified" against a fixture directory the assistant created to
match its own guess about the layout. It passed, and it proved only that the
guess was self-consistent.

**Fixtures are built from the source of truth** — the repo's own constants —
never from the same belief the code under test encodes. It went wrong twice in
one hour: the re-verification then read `$HOME` instead of the fixture, because
`DB_PATH` uses `expanduser`, and returned a stale row for all three cases.

**And a check must exercise the job, not the parts.** The r201 land gate
asserted the function existed and that the file parsed. Both were true of the
broken version. *Presence and a clean parse are not evidence that a display
displays.*

---

### 0.5 SILENCE IS THE WORST FAILURE MODE, AND IT IS USUALLY A CHOICE

`2>/dev/null` on the spot hint turned a broken path into a blank line that
looked deliberate. It was added **on purpose**, to keep the config screen tidy.

**No output is never tidier than an error.** Anything that can fail says so,
names what it was looking for, and names where it looked. This is the same
class as `sqlite3` missing from the boxes and reading as "no rows," and as a
gate that goes red for a reason unrelated to what it checks — which is worse
than no gate, because it gets distrusted and then disabled.

---

### 0.6 WHY A RULE IS NOT ENOUGH, AND WHAT GOES WITH IT

The assistant has already told the operator this, and it remains true:
**instructions shape defaults; they do not stop the assistant at the moment it
is about to take a shortcut.** §0 changes the odds. **A gate changes the
outcome.**

So every delivery that can be checked mechanically, is:

- the land gate **runs** the thing and requires its output — not its presence
- born-red first: a check that does not fail at the previous HEAD proves nothing
- negative canaries anchored to a definition, never to a mention (§20)
- the fixture comes from the repo, never from the assistant's belief (§0.4)

⚠️ **A memory write was rejected on 2026-08-31 because the preferences file is
over its size cap.** Rules the assistant believes it "saved" may never have
persisted. **This file, in the repo, is the only durable place for operating
discipline.** If a rule matters, it lands here in a revision — it does not live
in memory.

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
**See §0 — this rule is a special case of it, and §0 says why.**
The assistant burned turns "fixing" code from a stale mental model, and had to be
stopped. Hard rule:
- Every edit starts with a **fresh clone** and **reading the actual current file.**
- Any question about repo state ("did this land?", "what's uncommitted?") gets a
  **clone-and-grep**, never a recollection. (Answered one such question from memory and
  was wrong — said the Fable spec was missing when it was the replay bookmark.)

## 9. Prove it in the sandbox before presenting.
**See §0.4 — a fixture built from your own assumption is not proof.**
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

## 15. DELIVERY IS A TARBALL. THE OPERATOR LANDS IT FROM THE MENU.

🔴 **AMENDED 2026-09-05 (dtp r278/r279, otv4 r253). THE ASSISTANT NO LONGER
PRINTS A LAND COMMAND.** Operator: *"I no longer need you to print the
landing/commit commands going forward."*

**The deploy is a devtools item: `LAND a tarball from /home/ubuntu`**, with
`LAND a tarball — DRY RUN` beside it. **CITE IT BY LABEL.** It sits at option
54 as of 2026-09-05 and that number is arbitrary — menu numbers are assigned
from a render-time loop counter and have moved twice in a week, which is why
**C.15** says any document naming an item by number is wrong the moment the
next item lands.

**WHAT THE ASSISTANT STILL OWES, AND IT IS ALL OF THE HARD PART:** the archive,
built with `tar czf`, uniquely named per delivery (§26); and **a `land.spec`
per half**, which is the thing no generic tool can supply. The spec carries
`REPO` markers so the lander finds the checkout rather than guessing a path
(§3), `REV` and `DESC` — one string that becomes both the GENESIS row and the
commit subject (§35) — `ORDER` when a two-repo delivery's second half depends
on its first, `POS`/`NEG` content assertions, and `CHECK` lines naming what
must be EXECUTED. **The generic half is mechanics; the specific half is the
gate, and only the author of the change can write it.**

⚠️ **A HALF THAT SHIPS CODE AND DECLARES NO `CHECK` IS REFUSED.** Detected
from the payload, not trusted to the author, because the realistic failure is
a forgotten check rather than a broken one — and *nothing was executed* must
never read like *everything passed*. A docs-only half legitimately has nothing
to run and says so out loud.

⚠️ **ALL HALVES LAND OR NONE REACHES ORIGIN (dtp r279).** Every half is
verified and committed LOCALLY first, in order; the pushes come last and only
if every half got there. A failure rolls back every repo the run committed to,
with `reset --soft` so an unrelated file the operator had mid-edit survives.
**A pre-flight of every gate would NOT have worked** and the reason is worth
keeping: a half is allowed to gate on an artifact an earlier half produces, so
verifying half two before half one lands fails a gate that is not failing.

⚠️ **THE LANDER TRAVELS IN THE TARBALL**, with the repo copy as fallback. A
delivery that improves the lander must be landed BY the improved copy or the
improvement is never exercised on the one delivery that could prove it.

**WHAT FOLLOWS IS THE ORIGINAL §15, KEPT BECAUSE THE ARCHIVE RULES BELOW ARE
UNCHANGED** — the naming, the `.gz` strip, the `tar xf` flag, the no-scaffolding
rule. Only the LANDING half is superseded. Struck rather than deleted, per
r240's precedent: a row a later entry contradicts is a wrong answer, not
history, and the reasoning is still why the tarball looks the way it does.

## 15a. ⬛ SUPERSEDED — DELIVERY IS A TARBALL PLUS ONE LINE.
Added 2026-08-01. Every presented file, patch or hotfix ships as **one archive**
built with **`tar czf` (.tar.gz)** — Termius prefers compressed. It arrives in
`/home/ubuntu` **sometimes** renamed `.tar` (the `.gz` was stripped on 2026-08-01
— a 22 KB gzip payload named `...r2.tar` — and was NOT stripped on 2026-08-24,
when two files landed as `.tar.gz` intact). **Amended 2026-08-24: the strip is
not an invariant. Glob the extension — `tar xf "$HOME"/<name>.tar*` — so the
line is right either way.** That is harmless provided the extract is
**`tar xf`**, which sniffs the compression — **never `tar xzf`**, because the
arriving name may lie. The 2026-07-25 breakage was the
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

## 18a. 🔴 NO COMMAND PRINTS A SERVICE ENVIRONMENT BLOCK. EVER.

Added 2026-09-05 after I leaked every credential on the fleet to the operator's
terminal in one line.

I wanted to confirm one variable and wrote
`systemctl show shadow-observer -p Environment --value`. That flag prints the
**WHOLE** block. Onto his screen, into the session transcript, and out of
reach: `TT_REFRESH_TOKEN` (a live JWT with `read trade` scope on the funded
account), `TT_CLIENT_SECRET`, `GITHUB_TOKEN` with write access to both repos,
and `TELEGRAM_TOKEN`. Four rotations across fifteen boxes, on a Saturday
evening, because I did not think about what `--value` returns.

⚠️ **I HAD ALREADY WRITTEN THE SAFE FORM EARLIER IN THE SAME SESSION** and
reached for the unsafe one anyway. Knowing the rule is not the same as having
it in the command, which is why it is a section and not a note.

**THE RULE.** Never `-p Environment` without a filter. Never `systemctl cat`,
`cat` on a unit, `env`, `printenv`, `set`, or `/proc/<pid>/environ` on a box
that holds credentials. When one variable is the question, ask for exactly
that one:

    systemctl show <unit> -p Environment --value | tr " " "\n" | grep OT_SHADOW_STAGE

⚠️ **THE FLEET KEEPS ITS ENV INLINE IN THE UNIT** — `optionsbot.service` carries
`Environment=` lines rather than an `EnvironmentFile`, and the observer unit's
own comments instruct copying them across. So EVERY unit on every box is a
credential store, and there is no "safe" unit to run this against.

🔑 **AND THE GENERAL FORM, BECAUSE THE NEXT ONE WILL NOT BE `systemctl`:** before
a command goes in a code box, ask what it prints on the WIDEST input, not the
one being looked for. A flag that returns "the value" of a plural field returns
all of them. That question costs nothing and would have cost him nothing.

## 19. COMMANDS GO IN A CODE BOX, ON ONE LINE, SEMICOLON-SEPARATED.

⚠️ **SCOPE NARROWED 2026-09-05: THIS NO LONGER COVERS THE LAND COMMAND**, which
is not printed at all any more — see §15. It still governs every other command
the operator runs: a fleet fan-out, a query, a study, a one-off diagnostic. The
form and the presentation rules below are unchanged for all of those.

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

All of it was reverted. The half hour costs less than one duplicate module.

⚠️ **THE ROUTING DOCUMENT THIS SECTION USED TO NAME DOES NOT EXIST HERE.** Until
2026-08-29 the line above read *"`docs/README.md` routes by question — read it
first"*. That file was an OTV3 document and **was never ported to v4**, so the
one rule whose whole job is to stop docs going unread has been pointing at a
missing file since the split. Nobody noticed, which is the section's own thesis
proving itself.

**READ IN THIS ORDER instead, and all four of these exist:**

1. **`README.md`** (repo root) — what this repo is, what it refuses to be, and
   why. It carries the reading order too.
2. **`docs/WORKING_AGREEMENT.md`** — this file. How work gets done.
3. **`docs/BACKLOG.md`** — what is open, what was ruled, what is closed and by
   which revision. **This is the only place open work survives a thread.**
4. **`docs/GENESIS.md`** — one line per revision, and *why*, which the diff
   cannot tell you.

Then, by question: `PLAN_SPEC.md` and `TRADES.md` for what the strategies do,
`FILE_MAP.md` and `WRITE_MAP.md` (both **generated**, both gated) for what calls
what and who owns which table, `INHERITED_FINDINGS.md` for the measurements v4
was founded on.

⚠️ **AND THE RULE THE MISSING FILE CARRIED IS STILL IN FORCE: DO NOT CREATE A
NEW DOC.** Two documents claiming one job is the failure §35 records (a
`SHIPPING_LOG.md` rode in a tarball and was tracked for seven revisions while
GENESIS did the same work), and §33's map exists because a hand-kept duplicate
drifted. Add to the file that owns the subject. If nothing owns it, that is the
argument to make out loud before writing, not after.

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

## 30. EVERY BOX COLLECTS. THE COLLECTORS ARE THE TRADERS.
Added 2026-08-19 as "collection is fleet-wide, trading is panel-only, 15 traders
/ 29 collectors". **REWRITTEN 2026-08-25: that split no longer exists.** The
2026-08-20 pare TERMINATED the other 14 instances, so the fleet is 15 boxes and
they both trade and collect.

The rule itself survives intact and is why the section stays: **a box that stops
collecting is a box whose pitchfork and ADX warm-up depth quietly dies** — and
DXFeed history is same-evening only, so that depth cannot be recovered
afterwards. Pruning is disabled specifically so it accumulates.

⚠️ **THE CONSEQUENCE NOBODY WROTE DOWN AT THE TIME:** fleet-wide open-interest
accumulation — which the GEX butterfly's unpark waits on — now runs across 15
symbols instead of 29. Half the breadth, so a longer clock. Any unpark date
derived from the 29-symbol assumption is wrong.

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

    extract → verify → RUN THE CHECKS → REGENERATE MAP → APPEND GENESIS
            → git add <named paths> → commit → push → cleanup

🔴 **`git add -A` CORRECTED HERE 2026-09-05, AND THE DISAGREEMENT IS THE
FINDING.** This sketch said `git add -A` while the operator's own standing rule
says the opposite — *"NEVER `git add -A`; stage shipped files by name"*, written
after a stray file was pushed off main. Two documents disagreed and **the looser
one was the one the code followed**, for four months. `land.sh` v1.1 now stages
the payload's own file list plus the artifacts the command itself generated, and
nothing else. `RUN THE CHECKS` is likewise new (v1.1): before it, this command
GREPPED and never executed, which is the §0.6 shape exactly — the r201 gate
asserted a function existed and the file parsed, and both were true of the
broken version.
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

## 36a. EVERY S3-SOURCED READER GOES THROUGH `WarehouseCache.load`.

Added 2026-09-05 (r272), correcting SNS.4, which said `load_derived()`.

**It said the wrong function, and the reason it was wrong is the point.**
`warehouse_reader.load_derived` carries the natural-key collapse, the forward
partition scan and the ET-day filter — and **it has no production callers**
(S3.11). Every report reaches the warehouse through `WarehouseCache.load`,
which had none of the three until dtp r286 and r290 put them there. A rule
pointing at the correct-but-unused function would have sent the next reader
down the road with no traffic, which is how the defect happened in the first
place.

🔑 **WHAT THE CACHE GIVES YOU, AND WHY A BARE PARTITION READ IS NOT
EQUIVALENT.** It collapses CDC duplicates on each table's own declared primary
key, and REFUSES to collapse when the projection is missing part of that key
rather than folding distinct rows together. It scans a forward window and keeps
rows by their OWN ET day, because a derived partition is stamped with the PUSH
day (C.9) — so a bare read both MISSES rows pushed the next morning and
INCLUDES rows dated before the range. It streams at O(one object). And it
reports which collapse rule ran, so a report can state its provenance instead
of asserting one.

⚠️ **A BARE `read_prefix` OR HAND-ROLLED PAGINATOR REPRODUCES ALL OF THAT
WRONG, SILENTLY.** Every failure in this class renders as a smaller, plausible
number — never as an error.

⚠️ **`load_derived` REMAINS THE REFERENCE IMPLEMENTATION** and its checker is
worth keeping, but code that reads the warehouse for a report does not call it.

## 37. AN INTERRUPTED FIRING SEQUENCE IS NEVER RE-ENTERED. IT IS LOGGED AS MISSED.
Added 2026-08-24, operator's ruling, after r95 restored ORB state across a
restart and the first instinct was to let the recovered setup trade.

**"DO NOT TAKE A MISSED ENTRY as permission to enter LATE. If we missed it due
to an unexpected crash loop or restart, it's fine. The edge lies in the entry &
invalidation logic. Jumping in after it has left the station is not a remedy
for missing it."**

**THE TEST IS WHERE THE TRIGGER SITS, NOT HOW OLD THE PLAN IS.**
- **Trigger already fired while we were down** → the sequence is SPENT.
  Record it, consume the attempt, never fire it. The entry price is stale while
  the stop still anchors to the original structure, so chasing widens the risk
  leg by exactly the distance chased — an ORB in name only.
- **Trigger still ahead of us** → NORMAL. ARMED-awaiting-retest, a condor plan
  whose tine has not been touched, a runaway awaiting its pullback: these are
  observed LIVE, on our own tape, by the same code that would have judged them
  anyway. That is not a chase and must not be treated as one.

⚠️ **AND THE SECOND HALF IS THE ONE THAT GETS IMPLEMENTED WRONG.** Operator,
same day: *"normal entries that weren't filled and weren't interrupted should
keep trying"*, and *"all subsequent triggers not time gated should continue to
look for entries."*
- A LIVE confirmation that simply has not filled — chain fetch failed, thin
  liquidity, the dispatch slot taken — **keeps being offered every tick until
  its own window closes.** Nothing about a restart-recovery mechanism may touch
  it.
- Consuming a missed attempt means **RE-ARMING**, not parking. Price can come
  back into the range and break out again; that second setup is a normal entry
  and is taken normally.
- The only thing allowed to stop the hunting is a **genuine time gate** the
  strategy already owns — ORB's 11:00, the sweep window, the debit cutoff.

⚠️ **THE CONDOR IS SPECIAL: LEG 2 IS PERMITTED, NOT IMPLIED.** Operator:
*"A miss of one firing sequence does not take another valid entry off the
table."* A missed leg-2 sequence removes nothing. Each credit vertical is
autonomous and fires from its own structural trigger; the pairing gate counts
OPEN TRADES and asks nothing about history.

⚠️ **SO THE RECORD MUST BE INERT.** `MISSED` is a terminal plan state — it
CLOSES the row, leaves `live_plans()`, and is read by nobody in the entry path.
**A miss is a headstone, not a lock.** The failure this guards against would
look like caution and read like a bug fix: a ledger row quietly becoming a
reason to refuse the next trade, costing trades silently, which is precisely
the plausible-silence class in `docs/PORT_STATE.md`.

⚠️ **AND `MISSED` IS NOT A FLAVOUR OF `WIPED_BY_RESTART`.** They cost different
things. `WIPED_BY_RESTART` = the plan was still WAITING on its trigger when the
process died; nothing provable was lost. `MISSED` = the trigger DID fire, on
the tape, while we were down. Only the second answers *"what do mid-session
deploys and crash-loops actually cost us"*, and collapsing it into the first
buries that number inside a bigger one.

Pinned by `tests/check_orb_restart.py` (C2b the ruling, C9/C9b the boundary,
C10 subsequent triggers, C11 the time gate) and `tests/check_missed_inert.py`
(M3 nothing in the entry path reads the ledger). Both mutation-proven in both
directions.

---

## CHANGELOG

**v4.5 — 2026-09-05 — r272 — §36a ADDED: EVERY S3-SOURCED READER GOES THROUGH
`WarehouseCache.load`.**
Corrects SNS.4, which mandated `load_derived()` — the function that carries the
collapse, the forward scan and the ET-day filter, and **has no production
callers**. A rule naming the correct-but-unused path would have sent the next
reader down the road with no traffic, which is exactly how S3.11 and S3.21
happened. The cache is what every report actually uses and now carries all
three behaviours; a bare partition read reproduces them wrong and renders as a
smaller, plausible number rather than an error.

**v4.4 — 2026-09-05 — r265 — §18a ADDED: NO COMMAND PRINTS A SERVICE
ENVIRONMENT BLOCK.**
I ran `systemctl show shadow-observer -p Environment --value` across all fifteen
boxes to confirm one variable. It printed the whole block — `TT_REFRESH_TOKEN`
(live, `read trade`, funded account), `TT_CLIENT_SECRET`, `GITHUB_TOKEN` with
write on both repos, `TELEGRAM_TOKEN` — to his terminal and into the session
record. Four rotations across fifteen boxes, caused entirely by me.
⚠️ **I HAD WRITTEN THE SAFE FORM EARLIER IN THE SAME SESSION.** Knowing the rule
did not put it in the command, so it is a section now: never `-p Environment`
unfiltered, never `systemctl cat`/`env`/`printenv` on a box holding creds, and
the `| tr " " "\n" | grep <VAR>` form is spelled out at the site.
🔑 The general rule it generalises to: **ask what a command prints on the widest
input, not the one you are looking for.** A flag that returns "the value" of a
plural field returns all of them.

**v4.3 — 2026-09-05 — otv4 r253 — §15 REWRITTEN: THE OPERATOR LANDS FROM THE
MENU, AND THE ASSISTANT STOPS PRINTING LAND COMMANDS.**
Operator, 2026-09-05: *"I no longer need you to print the landing/commit
commands going forward... now we use [the LAND item] in devtools."* §15's
LANDING half is superseded and its archive rules are kept intact as §15a,
struck rather than deleted per r240 — the reasoning is still why the tarball
looks the way it does. What the assistant still owes is the archive and a
`land.spec` per half, which is the part no generic tool can supply: the
mechanics are generic, the GATE is specific, and only the author of a change
can write it. §19's scope is narrowed to say plainly that it no longer covers
the land command. 🔴 **§33's LAND-ORDER SKETCH IS CORRECTED**: it said
`git add -A` while the operator's own standing rule says never to, and the
looser document was the one the code followed for four months. The sketch now
shows named staging and the CHECK stage that dtp r278 added — before it, this
command greped and never executed anything, which is §0.6's own shape.
⚠️ **THE ITEM IS CITED BY LABEL, NEVER BY NUMBER.** It is 54 today; menu
numbers come from a render-time loop counter and have moved twice in a week
(C.15).

**v4.2 — 2026-08-31 — §0 ADDED: THE ASSISTANT'S ATTESTATION.**
Title and the unequivocal statement beneath it are the operator's own
specification, given in an earlier thread and never carried out. Numbered 0
rather than 38 because it is the floor the rest rests on, and because the
assistant later told him this section already existed when it did not. Records the pattern with its incidents, the operator's
own words on what it costs him, that self-verification against one's own
assumption is not verification, that silence is usually a choice, and that a
rule changes the odds while a gate changes the outcome. §8 and §9 now
cross-reference it.


v4.1  2026-08-29  r186 — backlog DOC.5. §25 has pointed at `docs/README.md`
      since the v3—v4 split and that file was never ported — the one rule
      whose job is to stop documents going unread was itself routing to a
      missing document, in a section written because two days of work were lost
      to unread docs. Replaced with an explicit four-document reading order,
      every one of which exists, plus the by-question index. The rule the
      missing file carried — do not create a new doc — is restated in place,
      with §33 and §35 as the evidence.
      A version line was added at the top: this file had none in either place,
      so neither the two-places rule nor `check_land_discipline.py` could see
      it (backlog DOC.9).

v4.0  2026-08-19  Carried over at the OTV4 split. §26 through §37 were added
      between 2026-08-19 and 2026-08-24 and are v4-era, not inherited.
