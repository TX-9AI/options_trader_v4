#!/usr/bin/env bash
# options_trader_v4/install_midnight_halt.sh — v1.0
# v1.0 (2026-09-06) — r289 / EOD.3. Installs the midnight ET backstop.
#
# Operator: *"I do sometimes work on them late & might forget. So I want another
# self shutdown at midnight eastern time to catch anything I accidentally left
# up. No drain, or anything else. Just stop, that's it."*
#
# 🔑 THIS SITS BELOW `optbot-self-close.timer`, NOT BESIDE IT. That one runs at
# 16:45, drains to S3, verifies, and deliberately STAYS UP IF SHORT. This one
# runs at 00:00 and only halts. Seven hours apart, so they cannot race, and the
# later one carries none of the earlier one's machinery — a backstop that can
# hang is not a backstop.
#
# ⚠️ EVERY DAY, NOT Mon-Fri. The 16:45 close is weekdays because that is when a
# session ends; this exists because a box was left up by hand, and that happens
# on a Saturday as easily as a Tuesday. A Sunday afternoon spent on the fleet is
# exactly the case the operator described.
#
# Run:  bash install_midnight_halt.sh
#       bash install_midnight_halt.sh --rollback
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

if [ "${1:-}" = "--rollback" ]; then
  sudo systemctl disable --now optbot-midnight-halt.timer 2>/dev/null || true
  sudo rm -f /etc/systemd/system/optbot-midnight-halt.{service,timer}
  sudo systemctl daemon-reload
  echo "rolled back."; systemctl list-timers 'optbot-*' --all --no-pager; exit 0
fi

sudo tee /etc/systemd/system/optbot-midnight-halt.service >/dev/null <<UNIT
[Unit]
Description=OPT_Trader midnight backstop — halt if this box is still up. No drain.
After=network-online.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=$DIR
ExecStart=$PY $DIR/warehouse/midnight_halt.py
StandardOutput=append:$DIR/logs/midnight_halt.log
StandardError=append:$DIR/logs/midnight_halt.log
# ⚠️ SHORT TIMEOUT. It reads one file and calls shutdown; anything slower is
# wedged, and a wedged backstop must give up rather than hold the boot.
TimeoutStartSec=120
UNIT

sudo tee /etc/systemd/system/optbot-midnight-halt.timer >/dev/null <<UNIT
[Unit]
Description=Halt at 00:00 ET if this box is somehow still up

[Timer]
OnCalendar=*-*-* 00:00:00 America/New_York
# ⚠️ Persistent=false, FOR THE SAME REASON AS THE 16:45 TIMER. A box woken at
# 09:15 must NOT immediately run a missed midnight halt and stop itself in the
# middle of the morning — which would be this backstop causing precisely the
# outage it exists to prevent.
Persistent=false

[Install]
WantedBy=timers.target
UNIT

mkdir -p "$DIR/logs"
sudo systemctl daemon-reload
sudo systemctl enable --now optbot-midnight-halt.timer
echo
echo "Installed. To keep a box up overnight deliberately:"
echo "  touch $DIR/data/NO_MIDNIGHT_HALT     # survives a bake; remove to re-arm"
echo
systemctl list-timers 'optbot-*' --all --no-pager | sed -n '1,4p'
