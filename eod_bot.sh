#!/usr/bin/env bash
# ==========================================================================
# eod_bot.sh  v4.0
# End-of-day bot wrapper.
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
# options_trader_v3/eod_bot.sh — v1.0
# Unified bot-side EOD winddown. ONE script, ONE timer (~16:01 ET), run AFTER the
# in-process 15:45 flatten and the 16:00 close. Replaces the separate ot-eod (15:50
# P&L) + candle-logger (16:05 OHLC) timers, so every box produces the exact set the
# control conductor gates on: ~/eod/pnl_today.json + trades_today.json, and the
# full-session OHLC CSV. Sequential; each step logged; runs under systemd (no ceiling).
# ==========================================================================
set -uo pipefail
DIR=/home/ubuntu/options-trader
PY="$DIR/venv/bin/python"; [ -x "$PY" ] || PY=/usr/bin/python3
cd "$DIR" || { echo "🚨 $DIR not found"; exit 9; }
echo "=== $(date '+%F %T %Z') eod_bot start ==="
echo "[1/2] P&L writer (eod_summary.py)"
"$PY" eod_summary.py || echo "🚨 eod_summary failed"
echo "[2/2] full-session OHLC (pull_today_ohlc.sh __work)"
bash "$DIR/pull_today_ohlc.sh" __work || echo "🚨 pull_today_ohlc failed"
echo "=== $(date '+%F %T %Z') eod_bot done ==="
