#!/bin/bash
# ==========================================================================
# bootstrap.example.sh  v4.2
# v4.2  2026-09-21  r408 / OPS.34 — THIS FILE SAID IT WAS SAFE TO COMMIT AND
#   GIT HAD NEVER LET ANYONE COMMIT IT.
#   🔴 `.gitignore` carried `!bootstrap.example.sh` at line 2 and
#   `bootstrap*.sh` at line 51. **git applies the LAST matching pattern**, so
#   the exception never took effect: `git check-ignore -v` named
#   `.gitignore:51` as the winner, and `git log --all -- bootstrap.example.sh`
#   is EMPTY — this template has never existed in otv4's history.
#   ⚠️ FOUND BY r407 FAILING TO STAGE IT: that revision repointed this file
#   from v3 to otv4 and the land printed "The following paths are ignored by
#   one of your .gitignore files", staging 4 payload files instead of 5 — so
#   `requirements.txt` and `install.sh` landed and THIS DID NOT.
#   🔑 THE CLAIM BELOW IS NOW TRUE AND IS KEPT RATHER THAN REWRITTEN, so the
#   next reader can see it was once false. `check_install_target` I7 drives
#   `git check-ignore` against this path and I8 asserts every negation in
#   `.gitignore` is actually in force.
# Worked example of an unattended box bootstrap.
#
# v4.1  2026-09-21  r407 / OPS.33 — THE UNATTENDED INSTALL FACES otv4.
#   🔴 IT FETCHED v3'S INSTALLER AND CLONED v3. A box deployed from this file
#   came up running options_trader_v3 and only became an otv4 box when REPOINT
#   rewrote its origin afterwards — so "the 5-minute unattended deploy" built
#   the PREVIOUS generation every time, by construction.
#   🔑 AND THAT IS THE WHOLE OF [[OPS.18]]. otv4's `install.sh` has applied
#   `_sparse_trader` since r4; **v3's installer has no sparse logic at all**
#   (2,025 bytes against otv4's 9,695), and neither REPOINT nor the bake ever
#   re-runs an installer. So `core.sparseCheckout` was never set on any box,
#   which is exactly what AMD measured: 168 test files and all of `docs/` on a
#   t2.micro WA §34 says must carry neither.
#   ⚠️ THE SAME CLASS ALREADY BIT ONCE, AT THE v2→v3 SPLIT, and `install.sh`'s
#   own header records it: *"the clone URL and the documented one-liner still
#   targeted options_trader_v2, so every fresh install from this repo silently
#   deployed v2 code — caught on the QQQ-TEST rebuild, whose banner printed
#   v2.5."* Same defect, one generation later, caught the same way: by reading
#   what a fresh box would actually run.
#   ⚠️ VERIFIED BEFORE REPOINTING, NOT ASSUMED: stripped of comments, v3's and
#   otv4's `setup_ec2.sh` are IDENTICAL in executable content and consume the
#   same nine environment variables into the same `$HOME/options-trader`. So
#   this changes WHICH REPO IS CLONED and nothing about how a box is
#   provisioned.
#
# v4.0  2026-08-19  Ported from options_trader_v3 at the OTV4 split.
#
# INHERITED DOCTRINE
# MEASUREMENTS AND CONSTRAINTS CARRIED FROM v3 - NOT A CHANGELOG.
# Dated release framing and trivia are stripped; what remains is the
# reasoning behind the thresholds, the design guarantees, and the
# defects that recur when forgotten. WORKING_AGREEMENT 32 requires
# this block be read before the file is edited.
#
#!/bin/bash
# repo-wide v3.0 bump: Yahoo-Finance purge & data stream
#         mapping optimization (single shared TastyTrade candle feed). No
#         logic change in this file.
# bootstrap.sh — one-shot unattended deploy for a fresh EC2 instance.
# This is a TEMPLATE (placeholders only) — safe to commit. Do NOT put real
# secrets in this file. Put them only in a copy named bootstrap.sh, which is
# gitignored (the .gitignore ignores every bootstrap*.sh except this .example).
# HOW TO USE:
#   1. cp bootstrap.example.sh bootstrap.sh   # your copy — gitignored
#   2. Fill in the REPLACE_ME values in bootstrap.sh.
#   3. scp bootstrap.sh ubuntu@IP:~
#   4. On the instance:  bash bootstrap.sh
#      (no chmod needed — `bash <file>` ignores the execute bit that SCP strips.
#       It re-launches itself in tmux; if SSH drops, reconnect and run
#       `tmux attach -t deploy` to watch it finish.)
#   Forked this repo? Point GITHUB_REPO and the install.sh URL below at YOUR fork.
# It exports every value setup_ec2.sh would otherwise prompt for, then runs the
# standard web installer hands-free. setup_ec2.sh securely SHREDS your
# bootstrap.sh during cleanup, once the credentials are in the systemd unit.
# On a failed install it remains so you can re-run — delete it by hand if you
# abandon the deploy.
# ── Run inside tmux ───────────────────────────────────────────────────────────
# Re-launch this script inside a tmux session so a dropped SSH connection can't
# kill a multi-minute install (and can't leave secrets un-shredded). If you get
# disconnected, reconnect and run:  tmux attach -t deploy
# ==========================================================================
if [ -z "$TMUX" ]; then
    command -v tmux >/dev/null 2>&1 || { sudo apt-get update -qq; sudo apt-get install -y -qq tmux; }
    if command -v tmux >/dev/null 2>&1; then
        exec tmux new-session -A -s deploy "bash '$(readlink -f "$0")'"
    else
        echo "  (tmux unavailable — running directly; keep this session connected)"
    fi
fi

# ── Instrument (optional; defaults to QQQ if omitted) ─────────────────────────
export OT_INSTRUMENT="QQQ"        # QQQ | SPY | SPX | any supported single name
# NOTE: installs are ALWAYS paper at $200/trade. There is deliberately no paper/
# live or risk knob here — set risk and switch to live later via configure.sh.

# ── TastyTrade OAuth ──────────────────────────────────────────────────────────
export TT_CLIENT_SECRET="REPLACE_ME"
export TT_REFRESH_TOKEN="REPLACE_ME"
export TT_ACCOUNT_NUMBER="REPLACE_ME"   # e.g. 5WT12345

# ── Telegram alerts ───────────────────────────────────────────────────────────
export TELEGRAM_TOKEN="REPLACE_ME"
export TELEGRAM_CHAT_ID="REPLACE_ME"

# ── GitHub (for push.sh; also sets commit author to the repo owner) ───────────
export GITHUB_REPO="TX-9AI/options_trader_v4"   # ENTER-to-skip equivalent: leave as ""
export GITHUB_TOKEN="REPLACE_ME"

# ── Run the standard installer (inherits every export above) ──────────────────
curl -fsSL https://raw.githubusercontent.com/TX-9AI/options_trader_v4/main/install.sh -o install.sh \
    && bash install.sh
