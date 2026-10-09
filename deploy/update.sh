#!/usr/bin/env bash
# Pulls main and restarts dlwikibot if it changed. Run every minute by dlwikibot-update.timer.
set -euo pipefail
cd "$HOME/dlwikibot"

git fetch -q origin main
if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ]; then
  exit 0
fi

git reset -q --hard origin/main
venv/bin/pip install -q -r requirements.txt
sudo systemctl restart dlwikibot
echo "Deployed $(git rev-parse --short HEAD)"
