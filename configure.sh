#!/usr/bin/env bash
# ==========================================================================
# configure.sh  v4.4
#
# v4.4  2026-08-31  r203 — THE r201 SPOT HINT WAS BROKEN AND BAKED. It read a
#   `data/` subdirectory that does not exist, and `2>/dev/null` made the
#   failure look like a deliberate blank. Paths now come from config.py;
#   stderr is visible; the land gate RUNS the function and requires output.
#   🔴 r201's gate checked that the function existed and that this file
#   parsed. Presence and a clean parse are not evidence that a display
#   displays.
#
# v4.3  2026-08-31  r201 — menu item 8: ORB BUDGET (OT_ORB_BUDGET_USD), set
#   PER UNDERLYING. Shows SPOT as the reference — live from orb_state.json,
#   or derived from the last trade's underlying_entry, labelled either way.
#   ⚠️ The default fails closed at one trade's risk, so an unconfigured box
#   trades SMALL; the menu labels it "(default)" so it does not read broken.
#   ⚠️ Fixed in passing: the prompt said "between 1 and 7" on an 8-item menu.
# Per-box configuration.
#
# v4.2  2026-08-20  change_relaxed now calls reload_daemon after set_env, like
#       every other change_*. set_env edits the UNIT FILE; without the reload
#       systemd restarts from its cached copy, so the bot runs the OLD value
#       while the menu reports the new one. Pinned by check_configure_relaxed
#       C6: any function that calls set_env must also call reload_daemon.
#
# v4.1  2026-08-20  Option 7 (relaxed entry) called an undefined `confirm`,
#       so it always took the else branch: it could never be switched ON, and
#       opening the item wrote OT_RELAXED_ENTRY=0. Now calls ask_yn, the
#       helper the rest of the file uses. Both branches are executed by
#       tests/check_configure_relaxed.py, which also traps
#       command-not-found so a future undefined helper cannot fail quietly.
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
#!/usr/bin/env bash
# repo-wide v3.0 bump: Yahoo-Finance purge & data stream
#         mapping optimization (single shared TastyTrade candle feed). No
#         logic change in this file.
#  options_trader v2.0  —  Live Configuration Manager
#  v1.0 — original release
#  replaced SMS/Twilio with Telegram
#  swapped menu order: Telegram now 4, TT credentials now 5
#  fixed menu display lines to match handler order
#  auto restart on exit if changes made, no prompt
#  wipe trades.db on instrument change (paper mode only);
#          ORB range auto-fetched for new instrument via get_orb_range.py
#  add Daily loss cap override menu (OT_DAILY_LOSS_LIMIT)
#  add single-name instruments (directional-only) to the
#          instrument menu for wider paper-trading coverage
#  archive trades.db (+WAL sidecars) on EVERY mode switch,
#          labeled by the outgoing mode (trades_paper_*.db / trades_live_*.db).
#          Paper and live histories never share a file (audit defect Q);
#          companion to trade_logger v3.7 mode-scoped queries.
#  going LIVE now reports that broker reconciliation
#          auto-enables with the mode (config.py v1.8 default follows
#          OT_PAPER_TRADING); show_config gains a "Broker reconcile" status
#          line; warns loudly if OT_BROKER_RECONCILE=False pins it off.
#  instrument picker now types the ticker (validated against
#          config.STRIKE_INCREMENTS) instead of a numbered menu — scales to the
#          full screener universe
#  Run this anytime to view or change bot settings.
#  Changes take effect on the NEXT bot start — the bot is
#  never restarted automatically to avoid mid-session surprises.
#  Usage:
#    ./configure.sh          — interactive menu
#    ./configure.sh --show   — print current config and exit
# ==========================================================================
SERVICE_NAME="optionsbot"
BOT_DIR="$HOME/options-trader"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# ── Colours ──────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

print_banner() {
    echo ""
    echo -e "${BOLD}${CYAN}============================================================${RESET}"
    echo -e "${BOLD}${CYAN}  options_trader  —  Configuration Manager${RESET}"
    echo -e "${BOLD}${CYAN}============================================================${RESET}"
    echo ""
}

print_ok()   { echo -e "  ${GREEN}✓${RESET}   $1"; }
print_warn() { echo -e "  ${YELLOW}⚠${RESET}   $1"; }
print_info() { echo -e "  ${CYAN}→${RESET}  $1"; }
ask()        { read -p "    $1: " "$2"; }
ask_secret() { read -s -p "    $1: " "$2"; echo ""; }
ask_yn()     {
    while true; do
        read -p "    $1 [y/n]: " yn
        case "$yn" in [Yy]) return 0;; [Nn]) return 1;; esac
    done
}

# ── Read a single Environment= value from the unit file ──────
get_env() {
    sudo grep -oP "(?<=Environment=${1}=).*" "$UNIT_FILE" 2>/dev/null | tail -1 || echo ""
}

# ── Update or add an Environment= line in the unit file ──────
set_env() {
    local key="$1" val="$2"
    if sudo grep -q "Environment=${key}=" "$UNIT_FILE" 2>/dev/null; then
        sudo sed -i "s|Environment=${key}=.*|Environment=${key}=${val}|" "$UNIT_FILE"
    else
        sudo sed -i "/ExecStartPre=/i Environment=${key}=${val}" "$UNIT_FILE"
    fi
}

reload_daemon() {
    sudo systemctl daemon-reload
}

# v2.0 (audit defect Q): archive the trade DB on EVERY mode switch so paper and
# live histories never share a file. mv on the same filesystem keeps the inode,
# so a still-running bot finishes its session writing into the archive; the
# restarted bot creates a fresh trades.db in the new mode. WAL sidecars move
# with the DB so no unflushed rows are lost.
archive_trades_db() {
    local from_mode="$1"   # outgoing mode: "paper" or "live"
    local db="$BOT_DIR/trades.db"
    if [[ ! -f "$db" ]]; then
        print_info "No trades.db to archive — starting the new mode fresh."
        return
    fi
    local stamp dest
    stamp=$(date +%Y%m%d_%H%M%S)
    dest="$BOT_DIR/trades_${from_mode}_${stamp}.db"
    mv "$db" "$dest"
    [[ -f "${db}-wal" ]] && mv "${db}-wal" "${dest}-wal"
    [[ -f "${db}-shm" ]] && mv "${db}-shm" "${dest}-shm"
    print_ok "Archived ${from_mode} trade history → $(basename "$dest")"
    print_info "A fresh trades.db is created on next start — ${from_mode} P&L can never leak into the new mode."
}

bot_is_running() {
    systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null
}

# ──────────────────────────────────────────────────────────────
# SHOW CURRENT CONFIG
# ──────────────────────────────────────────────────────────────
show_config() {
    local instrument risk paper account

    if [[ ! -f "$UNIT_FILE" ]]; then
        echo -e "  ${RED}Service unit not found.${RESET}"
        echo -e "  Run setup_ec2.sh first to install the bot."
        return 1
    fi

    instrument=$(get_env "OT_INSTRUMENT")
    risk=$(get_env "OT_RISK_USD")
    paper=$(get_env "OT_PAPER_TRADING")
    account=$(get_env "TT_ACCOUNT_NUMBER")
    telegram_token=$(get_env "TELEGRAM_TOKEN")
    telegram_chat=$(get_env "TELEGRAM_CHAT_ID")

    local mode_label
    if [[ "$paper" == "False" ]]; then
        mode_label="${RED}${BOLD}🔴 LIVE — real money${RESET}"
    else
        mode_label="${GREEN}📄 PAPER — simulated fills${RESET}"
    fi

    local status_label
    if bot_is_running; then
        status_label="${GREEN}● running${RESET}"
    else
        status_label="${YELLOW}○ stopped${RESET}"
    fi

    echo -e "  ${BOLD}Current Configuration${RESET}"
    echo -e "  ─────────────────────────────────────────"
    echo -e "  Bot status:     $(echo -e $status_label)"
    echo -e "  Instrument:     ${BOLD}${instrument:-not set}${RESET}"
    echo -e "  Risk per trade: ${BOLD}\$${risk:-not set}${RESET}"
    local dll=$(get_env "OT_DAILY_LOSS_LIMIT")
    echo -e "  Daily loss cap: ${BOLD}\$${dll:-${risk} (default)}${RESET}"
    echo -e "  Trading mode:   $(echo -e $mode_label)"
    local rec_pin rec_label
    rec_pin=$(get_env "OT_BROKER_RECONCILE")
    if [[ "$rec_pin" == "True" ]]; then rec_label="on (pinned)"
    elif [[ "$rec_pin" == "False" ]]; then rec_label="OFF (pinned)"
    elif [[ "$paper" == "False" ]]; then rec_label="on (auto, follows LIVE)"
    else rec_label="off (auto, follows PAPER)"; fi
    echo -e "  Broker reconcile: ${BOLD}${rec_label}${RESET}"
    echo -e "  TT Account:     ${BOLD}${account:-not set}${RESET}"
    local tg_status
    if [[ -n "$telegram_token" ]]; then
        tg_status="✓ enabled (chat ${telegram_chat})"
    else
        tg_status="— disabled"
    fi
    echo -e "  Telegram:       ${BOLD}${tg_status}${RESET}"
    echo -e "  ─────────────────────────────────────────"
    echo ""

    if bot_is_running; then
        print_warn "Bot is currently running. Changes take effect on next start."
    fi
}

# ──────────────────────────────────────────────────────────────
# MENU ACTIONS
# ──────────────────────────────────────────────────────────────

change_instrument() {
    local current allowed full choice
    current=$(get_env "OT_INSTRUMENT")
    # Pull the tradeable universe straight from config.py — single source of truth.
    allowed=$(cd "$BOT_DIR" && python3 -c "import config; print(' '.join(sorted(config.STRIKE_INCREMENTS)))" 2>/dev/null)
    full=$(cd "$BOT_DIR" && python3 -c "import config; print(' '.join(sorted(config.FULL_STRATEGY_INSTRUMENTS)))" 2>/dev/null)
    if [ -z "$allowed" ]; then
        print_warn "Could not read the symbol list from config.py."
        return
    fi
    echo ""
    echo -e "  Current instrument: ${BOLD}${current}${RESET}"
    echo ""
    echo -e "  ${BOLD}Full strategy${RESET} (condor/butterfly):  ${full}"
    echo -e "  ${BOLD}Directional only${RESET} (ORB + sweep):    everything else"
    echo ""
    echo -e "  Tradeable symbols:"
    echo "    ${allowed}"
    echo ""
    while true; do
        read -p "    Enter ticker [ENTER to keep ${current}]: " choice
        choice=$(echo "${choice:-$current}" | tr '[:lower:]' '[:upper:]')
        if [[ "$choice" == "$current" ]]; then
            print_info "Unchanged: ${current}"; return
        fi
        if echo "$allowed" | tr ' ' '\n' | grep -qxF "$choice"; then
            NEW_INST="$choice"; break
        fi
        print_warn "Unknown ticker '${choice}'. Pick one from the list above."
    done
    set_env "OT_INSTRUMENT"  "$NEW_INST"
    set_env "OT_BOT_NAME"    "OptionsTrader-${NEW_INST}"
    reload_daemon
    print_ok "Instrument updated to ${BOLD}${NEW_INST}${RESET}."
    # Wipe trades.db in paper mode — old trades from a different instrument
    # are meaningless and pollute the P&L dashboard
    local paper
    paper=$(get_env "OT_PAPER_TRADING")
    if [[ "$paper" != "False" ]]; then
        rm -f "$BOT_DIR/trades.db"
        print_ok "Paper trade history cleared (instrument changed)."
    fi
}

change_risk() {
    local current
    current=$(get_env "OT_RISK_USD")
    echo ""
    echo -e "  Current risk per trade: ${BOLD}\$${current}${RESET}"
    echo ""
    while true; do
        read -p "    New risk per trade in \$ [ENTER to keep \$${current}]: " input
        if [[ -z "$input" ]]; then
            print_info "Unchanged: \$${current}"
            return
        fi
        if [[ "$input" =~ ^[0-9]+(\.[0-9]+)?$ ]] && (( $(echo "$input > 0" | bc -l) )); then
            set_env "OT_RISK_USD" "$input"
            reload_daemon
            print_ok "Risk per trade updated to ${BOLD}\$$input${RESET}."
            return
        fi
        print_warn "Please enter a positive number (e.g. 200 or 150.50)."
    done
}

change_relaxed() {
    # ── RELAXED ENTRY CRITERIA (v4.0) ───────────────────────────────────────
    # Loosens SELECTION gates so trades actually fire: the sequence can be
    # watched, plumbing errors surfaced, and the stops exercised on deliberately
    # mediocre entries.
    #
    # ⚠️ IT DOES NOT LOOSEN FEASIBILITY VETOES. Below 0.05% ATR the required
    # move was reached on 0% of 5,517 measured bars - relaxing that would only
    # produce trades that cannot pay, which teaches nothing about stops and adds
    # noise to the very log this mode exists to read.
    # ⚠️ PAPER ONLY. strategy/relaxed.py refuses on a live box whatever this
    # says, and it requires OT_PAPER_TRADING to be asserted EXPLICITLY - a
    # config default is not an assertion.
    # ⚠️ EVERY relaxed trade is tagged `relaxed_entry=1` and its setup_type gets
    # a `_relaxed` suffix, so the population stays separable forever. **Data
    # collected here must never validate a tight threshold.**
    local current
    current=$(get_env "OT_RELAXED_ENTRY")
    echo ""
    echo "  Relaxed entry criteria: ${current:-0}  (1 = on, paper only)"
    echo ""
    echo "  ON  - trades fire on looser SELECTION gates so the sequence,"
    echo "        the logs and the stops can be watched. Every trade is"
    echo "        tagged relaxed_entry=1."
    echo "  OFF - measured criteria only. This is the trading setting."
    echo ""
    # v4.1 — `confirm` DOES NOT EXIST IN THIS REPO. The helper is `ask_yn`
    # (line ~69), and the only other yes/no caller in the file uses it. The
    # undefined name meant bash printed "confirm: command not found", returned
    # 127, and the `if` took the ELSE branch — so option 7 could never turn
    # relaxed entry ON, and MERELY OPENING IT WROTE `OT_RELAXED_ENTRY=0`.
    # ⚠️ IT FAILED IN THE SAFE DIRECTION, WHICH IS WHY IT SURVIVED. A
    # command-not-found in an `if` is indistinguishable from an honest "no":
    # the menu printed a plausible "Relaxed entry OFF." and carried on. Found
    # 2026-08-20 on the AMD box the night before the first v4 session.
    if ask_yn "Enable relaxed entry criteria?"; then
        set_env "OT_RELAXED_ENTRY" "1"
        reload_daemon
        echo "  RELAXED ENTRY ON - paper only, and every trade is tagged."
    else
        set_env "OT_RELAXED_ENTRY" "0"
        reload_daemon
        echo "  Relaxed entry OFF."
    fi
    # v4.2 — `set_env` EDITS THE UNIT FILE, so systemd must be told. Every
    # other change_* already reloads after writing (change_instrument,
    # change_risk, change_mode, change_daily_loss, change_telegram,
    # change_tt_credentials); this one never did, which is why the restart
    # printed "The unit file ... changed on disk. Run 'systemctl
    # daemon-reload'".
    # ⚠️ IT IS NOT COSMETIC. Without the reload systemd restarts from its
    # CACHED copy of the unit, so the bot comes back up on the OLD
    # OT_RELAXED_ENTRY while configure.sh and the menu both report the NEW
    # one. The setting appears applied and is not — this project's named
    # failure class, one layer below the code.
}



# ── r203 — SPOT, FOR SIZING THE ORB BUDGET AGAINST ────────────────────────
# 🔴 THIS FUNCTION SHIPPED BROKEN IN r201 AND THE FLEET BAKED IT. It read
# `<install>/data/orb_state.json` and `<install>/data/trades.db`. Neither
# exists: both files sit at the install root, and both paths were already in
# config.py — DB_PATH at 1604, LOG_FILE at 1613 — with orb_state.json written
# beside the log (main.py ~1358). I invented a subdirectory instead of reading
# two lines I had edited an hour earlier.
# 🔴 AND `2>/dev/null` TURNED THE FAILURE INTO A BLANK LINE. That was a
# deliberate choice, made to keep this screen tidy, on a feature whose entire
# job is to display a number. Silence over noise is the failure class this
# project exists to hunt, committed inside a display.
# 🔴 THE TEST COULD NOT FAIL. I built a fixture directory matching my own guess
# and verified against it. It passed, and it proved only that the guess was
# consistent with itself. The r201 land gate asserted the function EXISTED and
# that configure.sh PARSED — neither asks whether it produces output.
# 🔑 THE FIX, AND WHY IT IS SHAPED THIS WAY:
#   · paths are IMPORTED from config, never spelled here, so a future move of
#     either file cannot silently blank this display;
#   · stderr is NOT suppressed — every failure names itself and its path;
#   · the r203 land gate RUNS this body against a planted repo and REQUIRES a
#     Spot line back, and refuses both a literal `data/` path and any
#     re-suppression of stderr on this call.
orb_spot_hint() {
    local py="$HOME/options-trader/venv/bin/python"
    [[ -x "$py" ]] || py="python3"
    ( cd "$HOME/options-trader" 2>/dev/null || cd "$SCRIPT_DIR" 2>/dev/null || true
      "$py" - <<'PYEOF'
import json, os, sqlite3, sys
try:
    from config import DB_PATH, LOG_FILE
except Exception as exc:
    print("    Spot: unavailable (config import failed: %s)" % exc)
    sys.exit(0)
state = os.path.join(os.path.dirname(LOG_FILE), "orb_state.json")
try:
    with open(state) as f:
        price = json.load(f).get("price")
    if price:
        print("    Spot: %.2f  (live)" % float(price))
        sys.exit(0)
    print("    Spot: state file has no price yet (%s)" % state)
except FileNotFoundError:
    print("    Spot: no state file yet (%s)" % state)
except Exception as exc:
    print("    Spot: state unreadable (%s)" % exc)
# Fall back to the last trade's underlying_entry — spot when it fired.
try:
    c = sqlite3.connect(DB_PATH)
    r = c.execute("SELECT underlying_entry, entry_time FROM trades "
                  "WHERE underlying_entry > 0 ORDER BY entry_time DESC "
                  "LIMIT 1").fetchone()
    if r:
        print("    Spot: %.2f  (derived from the last trade, %s)"
              % (float(r[0]), str(r[1] or "")[:16]))
    else:
        print("    Spot: no trades on this box yet - read the chain")
except Exception as exc:
    print("    Spot: no trade history (%s)" % exc)
PYEOF
    )
}

change_orb_budget() {
    local current risk
    current=$(get_env "OT_ORB_BUDGET_USD")
    risk=$(get_env "OT_RISK_USD")
    echo ""
    echo -e "  ${BOLD}ORB budget${RESET} — the ceiling on what ONE ORB setup may"
    echo -e "  deploy. ORB sizes on GEOMETRY, not risk, so without this it grows"
    echo -e "  without bound as the impulsive stop tightens."
    echo ""
    echo -e "  contracts = min( floor(width / stop), floor(budget / cost) )"
    echo ""
    orb_spot_hint
    echo -e "  Current: ${BOLD}\$${current:-${risk} (default)}${RESET}"
    echo ""
    while true; do
        read -p "    New ORB budget in \$, 'r' to reset to default, ENTER to keep: " input
        if [[ -z "$input" ]]; then
            print_info "Unchanged."
            return
        fi
        if [[ "$input" == "r" ]]; then
            set_env "OT_ORB_BUDGET_USD" "$risk"
            reload_daemon
            print_ok "ORB budget reset to the per-trade risk default (\$${risk})."
            return
        fi
        if [[ "$input" =~ ^[0-9]+(\.[0-9]+)?$ ]] && (( $(echo "$input > 0" | bc -l) )); then
            set_env "OT_ORB_BUDGET_USD" "$input"
            reload_daemon
            print_ok "ORB budget updated to ${BOLD}\$$input${RESET}."
            # ⚠️ NAME THE CONSEQUENCE. A budget below one contract's cost
            # REFUSES the trade outright rather than flooring to a 1-lot.
            echo -e "  ${DIM}A setup whose single contract costs more than this"
            echo -e "  will be REFUSED, not reduced to 1 lot.${RESET}"
            return
        fi
        print_warn "Enter a positive number, 'r' to reset, or ENTER to keep."
    done
}

change_daily_loss() {
    local current risk
    current=$(get_env "OT_DAILY_LOSS_LIMIT")
    risk=$(get_env "OT_RISK_USD")
    echo ""
    echo -e "  ${BOLD}Daily loss cap${RESET} — halts NEW entries once the day's NET"
    echo -e "  P&L is down by this amount. Open trades still exit normally."
    echo -e "  Default is one trade's risk (\$${risk})."
    echo -e "  Current: ${BOLD}\$${current:-${risk} (default)}${RESET}"
    echo ""
    while true; do
        read -p "    New cap in \$, 'r' to reset to risk default, ENTER to keep: " input
        if [[ -z "$input" ]]; then
            print_info "Unchanged."
            return
        fi
        if [[ "$input" == "r" ]]; then
            set_env "OT_DAILY_LOSS_LIMIT" "$risk"
            reload_daemon
            print_ok "Daily loss cap reset to per-trade risk (\$${risk})."
            return
        fi
        if [[ "$input" =~ ^[0-9]+(\.[0-9]+)?$ ]] && (( $(echo "$input > 0" | bc -l) )); then
            set_env "OT_DAILY_LOSS_LIMIT" "$input"
            reload_daemon
            print_ok "Daily loss cap updated to ${BOLD}\$$input${RESET}."
            return
        fi
        print_warn "Enter a positive number, 'r' to reset, or ENTER to keep."
    done
}

change_mode() {
    local current
    current=$(get_env "OT_PAPER_TRADING")
    echo ""
    if [[ "$current" == "False" ]]; then
        echo -e "  Current mode: ${RED}${BOLD}🔴 LIVE${RESET}"
        echo ""
        if ask_yn "Switch to PAPER mode?"; then
            set_env "OT_PAPER_TRADING" "True"
            reload_daemon
            archive_trades_db "live"
            print_ok "Switched to ${BOLD}📄 PAPER mode${RESET}."
        else
            print_info "Unchanged: LIVE."
        fi
    else
        echo -e "  Current mode: ${GREEN}📄 PAPER${RESET}"
        echo ""
        print_warn "You are about to enable LIVE TRADING."
        print_warn "Real orders will be placed with real money."
        echo ""
        read -p "    Type  LIVE  to confirm: " confirm
        if [[ "$confirm" == "LIVE" ]]; then
            set_env "OT_PAPER_TRADING" "False"
            reload_daemon
            archive_trades_db "paper"
            print_ok "Switched to ${RED}${BOLD}🔴 LIVE mode${RESET}."
            # v1.9: broker reconciliation follows the mode (config.py default) —
            # LIVE turns it on automatically unless OT_BROKER_RECONCILE pins it.
            local rec_pin
            rec_pin=$(get_env "OT_BROKER_RECONCILE")
            if [[ "$rec_pin" == "False" ]]; then
                print_warn "Broker reconciliation is PINNED OFF (OT_BROKER_RECONCILE=False in the unit file) — phantoms and manual closes will NOT be reconciled."
            else
                print_ok "Broker reconciliation: auto-enabled with LIVE mode."
            fi
        else
            print_info "Confirmation not received — mode unchanged."
        fi
    fi
}

change_tt_credentials() {
    echo ""
    echo -e "  Update your TastyTrade OAuth credentials."
    echo -e "  ${CYAN}Leave blank and press ENTER to keep the current value.${RESET}"
    echo ""

    local current_secret current_token current_account
    current_secret=$(get_env "TT_CLIENT_SECRET")
    current_token=$(get_env "TT_REFRESH_TOKEN")
    current_account=$(get_env "TT_ACCOUNT_NUMBER")

    read -s -p "    New Client Secret  [ENTER to keep current]: " new_secret; echo ""
    read -s -p "    New Refresh Token  [ENTER to keep current]: " new_token;  echo ""
    read -p    "    Account Number     [ENTER to keep ${current_account}]: " new_account

    local changed=false
    if [[ -n "$new_secret" ]]; then
        set_env "TT_CLIENT_SECRET"  "$new_secret";  changed=true; fi
    if [[ -n "$new_token" ]]; then
        set_env "TT_REFRESH_TOKEN"  "$new_token";   changed=true; fi
    if [[ -n "$new_account" ]]; then
        set_env "TT_ACCOUNT_NUMBER" "$new_account"; changed=true; fi

    if [[ "$changed" == "true" ]]; then
        reload_daemon
        print_ok "TastyTrade credentials updated."
    else
        print_info "No credentials changed."
    fi
}

change_telegram() {
    local current_token current_chat
    current_token=$(get_env "TELEGRAM_TOKEN")
    current_chat=$(get_env "TELEGRAM_CHAT_ID")
    echo ""

    if [[ -n "$current_token" ]]; then
        echo -e "  Telegram alerts are currently ${GREEN}enabled${RESET}."
        echo -e "  Chat ID: ${BOLD}${current_chat}${RESET}"
    else
        echo -e "  Telegram alerts are currently ${YELLOW}disabled${RESET}."
    fi

    echo ""
    echo -e "  ${CYAN}Press ENTER on any field to keep the current value.${RESET}"
    echo ""

    read -p "    Bot Token [ENTER = no change]: " new_token
    read -p "    Chat ID   [ENTER = no change, current: ${current_chat}]: " new_chat

    local changed=false
    if [[ -n "$new_token" ]]; then
        set_env "TELEGRAM_TOKEN" "$new_token"
        changed=true
    fi
    if [[ -n "$new_chat" ]]; then
        set_env "TELEGRAM_CHAT_ID" "$new_chat"
        changed=true
    fi

    if [[ "$changed" == "true" ]]; then
        reload_daemon
        print_ok "Telegram settings updated."
    else
        print_info "No changes made."
    fi
}

auto_restart() {
    echo ""
    echo "  Applying changes and restarting bot..."
    sudo systemctl restart "$SERVICE_NAME"
    sleep 4
    if bot_is_running; then
        print_ok "Bot restarted successfully with new settings."
    else
        print_warn "Bot failed to start — check: journalctl -u ${SERVICE_NAME} -n 20"
    fi
}

# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--show" ]]; then
    print_banner
    show_config
    exit 0
fi

if [[ ! -f "$UNIT_FILE" ]]; then
    print_banner
    echo -e "  ${RED}No service unit found at ${UNIT_FILE}${RESET}"
    echo -e "  Run setup_ec2.sh first to install and configure the bot."
    echo ""
    exit 1
fi

print_banner
show_config

CHANGED=false
while true; do
    echo -e "  ${BOLD}What would you like to change?${RESET}"
    echo ""
    echo -e "  ${BOLD}1.${RESET}  Instrument          (currently: $(get_env OT_INSTRUMENT))"
    echo -e "  ${BOLD}2.${RESET}  Risk per trade      (currently: \$$(get_env OT_RISK_USD))"
    echo -e "  ${BOLD}3.${RESET}  Paper / Live mode   (currently: $([ "$(get_env OT_PAPER_TRADING)" = "False" ] && echo "🔴 LIVE" || echo "📄 PAPER"))"
    echo -e "  ${BOLD}4.${RESET}  Telegram alerts     (chat: $(get_env TELEGRAM_CHAT_ID))"
    echo -e "  ${BOLD}5.${RESET}  TastyTrade credentials"
    echo -e "  ${BOLD}6.${RESET}  Daily loss cap      (currently: \$$(dll=$(get_env OT_DAILY_LOSS_LIMIT); echo ${dll:-$(get_env OT_RISK_USD)}))"
    echo -e "  ${BOLD}7.${RESET}  Relaxed entry       (currently: $([ "$(get_env OT_RELAXED_ENTRY)" = "1" ] && echo "ON - paper only" || echo "off"))"
    echo -e "  ${BOLD}8.${RESET}  ORB budget          (currently: \$$(ob=$(get_env OT_ORB_BUDGET_USD); echo "${ob:-$(get_env OT_RISK_USD) (default)}"))"
    echo -e "  ${BOLD}9.${RESET}  Done"
    echo ""
    read -p "    Select [1-9]: " menu_choice

    case "$menu_choice" in
        1) change_instrument; CHANGED=true ;;
        2) change_risk;       CHANGED=true ;;
        3) change_mode;       CHANGED=true ;;
        4) change_telegram;       CHANGED=true ;;
        5) change_tt_credentials; CHANGED=true ;;
        6) change_daily_loss;     CHANGED=true ;;
        7) change_relaxed;        CHANGED=true ;;
        8) change_orb_budget;     CHANGED=true ;;
        9) break ;;
        *) print_warn "Please enter a number between 1 and 9." ;;
    esac
    echo ""
done

if [[ "$CHANGED" == "true" ]]; then
    echo ""
    show_config
    auto_restart
fi

echo ""
