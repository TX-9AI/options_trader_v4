#!/bin/bash
# ==========================================================================
# install.sh  v4.2
# v4.2 (2026-09-21) - r407 / OPS.33. THE CLONE URL, THE DOCUMENTED ONE-LINER
#   AND THE BANNER ALL STILL SAID v3, SO THIS INSTALLER INSTALLED THE PREVIOUS
#   GENERATION - INCLUDING WHEN RUN FROM AN otv4 BOX.
#   🔴 `REPO` cloned options_trader_v3 and then ran THAT clone's setup_ec2.sh,
#   so otv4 could not install itself. The unattended bootstrap never even
#   reached this file: it curled v3's installer, which has NO SPARSE LOGIC,
#   which is the whole mechanism behind [[OPS.18]] - sparse is applied once at
#   install and neither REPOINT nor the bake re-runs an installer.
#   ⚠️ THE BANNER IS PART OF THE FIX, NOT DECORATION. The v2→v3 instance of
#   this exact defect (recorded below) was caught ONLY because a rebuild's
#   banner printed the wrong version. Leaving it reading v3.1 would remove the
#   one signal that has ever detected this.
#   ⚠️ AND otv4 GAINED ITS OWN `requirements.txt` IN THE SAME REVISION, because
#   without it `setup_ec2.sh:225` ABORTS - the reason the v3 pointer was
#   load-bearing rather than vestigial.
# v4.1 (2026-09-07) - r303 / DEP.8. WHAT SHIPS IS DECLARED, WHAT LANDED IS
#   VERIFIED. `docs/` joins `tests/` as control-only. New TRADER_DIRS and
#   _verify_trader: a SHORT checkout is fatal at install time rather than at
#   09:30, and DUPLICATE BASENAMES across levels are reported - the r288
#   signature, and the one thing a sparse allow-list cannot catch, since
#   `data/main.py` lives under a directory that must ship.
#   tools/ is on the list because status.py SHELLS OUT to
#   tools/manifold_health.py by path; no import graph would have found it.
# Installs the bot service on a box.
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
# install.sh — options_trader v3.0 Web Installer
# v1.0 — original release
# updated repo URL to options_trader_v2
# repo-wide v3.0 bump: Yahoo-Finance purge & data stream
#         mapping optimization (single shared TastyTrade candle feed). No
#         logic change in this file.
# REPO POINTER FIX: the clone URL and the documented
#         one-liner still targeted options_trader_v2, so every fresh install
#         from this repo silently deployed v2 code (caught on the QQQ-TEST
#         rebuild, whose banner printed v2.5 — v2's setup_ec2.sh). Now clones
#         options_trader_v3. Display banner v2.0 -> v3.1 (was never bumped).
# Run on a fresh EC2:
#   curl -fsSL https://raw.githubusercontent.com/TX-9AI/options_trader_v4/main/install.sh -o install.sh && bash install.sh
# ==========================================================================
set -e

REPO="https://github.com/TX-9AI/options_trader_v4.git"
DEPLOY_DIR="$HOME/options-trader-deploy"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     options_trader v4.2  |  Web Installer           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Install git if needed
sudo apt-get update -qq
sudo apt-get install -y -qq git

# ---------------------------------------------------------------------------
# DEPLOYMENT BOUNDARY: a TRADER carries only what it needs to trade and collect.
#
#   ships to a box   analysis/ data/ execution/ strategy/ risk/ database/
#                    notifications/ utils/ warehouse/ shadow/ deploy/ main.py
#                    config.py + the install scripts
#   CONTROL ONLY     tests/  - every harness, probe and replay tool
#
# WHY: harnesses read banked tape and trade databases. They never run on a box
# mid-session, and a t2.micro that has already been OOM-KILLED once (SPX, 419 MB)
# should not carry code it cannot use. Observers are the exception and DO ship:
# `shadow/` collects in-session, which is the data a future scorer is earned
# from.
#
# SPARSE CHECKOUT, not a post-pull `rm`. The setting persists in the clone's own
# config, so a box configured once stays correct through every later `git pull`
# in a bake. A cleanup step would have to be remembered by every future deploy
# path - and a manual step that must be remembered never happens.
# ---------------------------------------------------------------------------
# r303 / DEP.8 - WHAT SHIPS IS NOW DECLARED, AND WHAT LANDED IS VERIFIED.
#
# THE SPARSE RULE ALONE WOULD NOT HAVE PREVENTED r288, AND THAT IS THE WHOLE
# REASON THIS FUNCTION GAINED A SIBLING. r288 created TWO strays: a root
# `candle_feed.py` and a `data/main.py`. An allow-list refuses the first,
# because root files are enumerated - and ALLOWS the second, because `data/`
# has to ship. Tightening sparse catches one of two. So the protection that
# matters is `_verify_trader` below, which compares what is ON DISK against
# what is DECLARED.
#
# `docs/` joins `tests/` as control-only: 1.5 MB of prose no box reads, and
# `gen_file_map.py` runs on control.
_sparse_trader() {
    git -C "$1" sparse-checkout init --no-cone 2>/dev/null || return 1
    git -C "$1" sparse-checkout set --no-cone \
        '/*' '!/tests/' '!/docs/' 2>/dev/null || return 1
    return 0
}

# ── THE DECLARED SURFACE ────────────────────────────────────────────────────
# Directories a trader runs from. Derived from the ACTUAL import closure of the
# five box entry points (main.py, data/candle_feed.py, data/candle_logger.py,
# warehouse/s3_push.py, shadow/observer.py) plus the operator CLIs the fleet
# menu invokes (status.py, query.py, debug_status.py).
#
# 🔴 `tools/` IS ON THIS LIST AND NO IMPORT GRAPH WOULD HAVE PUT IT THERE.
# `status.py:491` SHELLS OUT to `tools/manifold_health.py` by path. A closure
# computed from imports alone omits it, and the manifold rollup breaks on every
# box - quietly, because the box still trades. Subprocess edges are invisible
# to the thing that would otherwise generate this list, which is exactly why it
# is written down rather than derived.
TRADER_DIRS="analysis data database deploy derived execution notifications risk shadow strategy tools utils warehouse"

# ── VERIFY WHAT LANDED, NOT WHAT WE ASKED FOR ───────────────────────────────
# ⚠️ THE FAILURE MODES ARE ASYMMETRIC AND ONLY ONE OF THEM IS LOUD. Shipping
# something extra wastes disk. Shipping something SHORT means a box cannot
# trade, and it does not surface until 09:30. So this refuses to be silent in
# either direction: a MISSING declared directory is fatal, and an UNEXPECTED
# top-level file or a DUPLICATE BASENAME is reported.
#
# 🔴 THE DUPLICATE-BASENAME TEST IS THE r288 DETECTOR. `data/main.py` beside
# `main.py` is the signature of an archive whose paths were built at the wrong
# level, and it is the one an allow-list cannot catch. It is also what the
# file map's orphan report missed, because `gen_file_map.py` falls back to
# matching a BASENAME against its entry-point list (DEP.10).
_verify_trader() {
    local d="$1" missing="" rc=0
    for p in $TRADER_DIRS; do
        [ -d "$d/$p" ] || missing="$missing $p"
    done
    [ -f "$d/main.py" ]   || missing="$missing main.py"
    [ -f "$d/config.py" ] || missing="$missing config.py"
    if [ -n "$missing" ]; then
        echo "  🔴 CHECKOUT IS SHORT - missing:$missing"
        echo "     This box CANNOT TRADE. Do not start it."
        rc=1
    fi
    # Duplicate basenames across levels - the r288 signature.
    # ⚠️ `__init__.py` IS EXCLUDED BY CONSTRUCTION, NOT BY TUNING. It is a
    # package marker - every package has one, so "duplicate basename" is
    # meaningless for it and a check that flags it fires on EVERY tree. These
    # markers have been in place since otv1 and are integral; nothing here
    # proposes touching them.
    # ⚠️ `registry.py` IS A DECLARED, LEGITIMATE DUPLICATE: `derived/registry.py`
    # and `shadow/registry.py` are two different modules that happen to share a
    # name. It is NAMED here rather than the check being loosened, so a THIRD
    # copy appearing still trips - and so the next reader can see which
    # duplicates were examined and accepted rather than guessing.
    # 🔑 A NEW ENTRY HERE IS A DECISION, NOT A CHORE. If this list grows without
    # anyone looking, the check has quietly become decorative - which is the
    # CV.1 failure it exists to avoid.
    local KNOWN_DUPES="registry.py"
    local dupes
    dupes="$(cd "$d" && find . -name '*.py' -not -path './.git/*' \
             -not -path './tests/*' -not -name '__init__.py' \
             -printf '%f\n' 2>/dev/null | sort | uniq -d \
             | grep -vxF "$KNOWN_DUPES" | tr '\n' ' ')"
    if [ -n "$dupes" ]; then
        echo "  ⚠️  DUPLICATE FILENAMES AT DIFFERENT LEVELS: $dupes"
        echo "     This is the r288 signature - an archive built at the wrong"
        echo "     level creates a copy beside the real file. Investigate"
        echo "     before baking; one of them is not the file being run."
    fi
    return $rc
}

if [ -d "$DEPLOY_DIR/.git" ]; then
    echo "  Updating existing repo..."
    cd "$DEPLOY_DIR" && git pull
else
    echo "  Cloning repository..."
    git clone "$REPO" "$DEPLOY_DIR"
fi

if [ "${OT_ROLE:-trader}" = "trader" ]; then
    if _sparse_trader "$DEPLOY_DIR"; then
        echo "  Sparse checkout: tests/ and docs/ excluded (trader role)."
        _verify_trader "$DEPLOY_DIR" || exit 1
    else
        # ⚠️ FAIL LOUD, NOT SILENT. A box that quietly keeps tests/ is only
        # wasting disk - but a box whose sparse config half-applied may be
        # MISSING RUNTIME PATHS, and that does not surface until it tries to
        # trade. Say so at install time rather than at 09:30.
        echo "  WARNING: sparse checkout FAILED - this box carries the full repo."
        echo "           Verify runtime paths are present before it trades."
    fi
else
    echo "  Role=${OT_ROLE}: full checkout (control keeps tests/)."
fi

echo "  Repository ready."
echo ""

# Run setup from the deploy dir
chmod +x "$DEPLOY_DIR/setup_ec2.sh"
bash "$DEPLOY_DIR/setup_ec2.sh"
