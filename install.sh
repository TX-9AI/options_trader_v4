#!/bin/bash
# ==========================================================================
# install.sh  v4.0
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
#   curl -fsSL https://raw.githubusercontent.com/TX-9AI/options_trader_v3/main/install.sh -o install.sh && bash install.sh
# ==========================================================================
set -e

REPO="https://github.com/TX-9AI/options_trader_v3.git"
DEPLOY_DIR="$HOME/options-trader-deploy"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     options_trader v3.1  |  Web Installer           ║"
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
_sparse_trader() {
    git -C "$1" sparse-checkout init --no-cone 2>/dev/null || return 1
    git -C "$1" sparse-checkout set --no-cone '/*' '!/tests/' 2>/dev/null || return 1
    return 0
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
        echo "  Sparse checkout: tests/ excluded (trader role)."
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
