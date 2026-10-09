#!/usr/bin/env bash
# One-time setup for dlwikibot on a Debian VM. Expects the bot's .env at ~/dlwikibot.env
set -euo pipefail
APP_DIR="$HOME/dlwikibot"
SERVICE=dlwikibot

sudo apt-get update -y
sudo apt-get install -y git python3 python3-venv

if ! sudo swapon --show | grep -q /swapfile; then
  sudo fallocate -l 1G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

if [ ! -d "$APP_DIR/.git" ]; then
  git clone https://github.com/kai8484/dlwikibot.git "$APP_DIR"
fi
cd "$APP_DIR"

python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

if [ -f "$HOME/dlwikibot.env" ]; then
  mv "$HOME/dlwikibot.env" "$APP_DIR/.env"
fi
if [ ! -f "$APP_DIR/.env" ]; then
  echo "ERROR: no .env found" >&2
  exit 1
fi
chmod 600 "$APP_DIR/.env"

sudo tee /etc/systemd/system/$SERVICE.service >/dev/null <<UNIT
[Unit]
Description=dlwikibot Discord bot
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python -u src/lookup.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now $SERVICE

sudo tee /etc/systemd/system/$SERVICE-update.service >/dev/null <<UNIT
[Unit]
Description=Pull dlwikibot from GitHub and restart it if main changed
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$USER
ExecStart=$APP_DIR/deploy/update.sh
UNIT

sudo tee /etc/systemd/system/$SERVICE-update.timer >/dev/null <<UNIT
[Unit]
Description=Check GitHub for dlwikibot updates every minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min

[Install]
WantedBy=timers.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now $SERVICE-update.timer

echo "SETUP_OK user=$USER"
