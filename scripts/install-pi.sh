#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-https://radar.kuvan.dev/api/update}"
REPO="https://github.com/burakuvan/airradar-pro.git"
APP_DIR="/home/pi-star/airradar-pro"
SERVICE="/etc/systemd/system/airradar-pi.service"

if [[ $EUID -ne 0 ]]; then
  echo "Bu script sudo ile çalıştırılmalı." >&2
  exit 1
fi

command -v git >/dev/null || apt-get update && apt-get install -y git python3-venv

if [[ -d "$APP_DIR/.git" ]]; then
  sudo -u pi-star git -C "$APP_DIR" pull --ff-only
else
  rm -rf "$APP_DIR"
  sudo -u pi-star git clone "$REPO" "$APP_DIR"
fi

sudo -u pi-star python3 -m venv "$APP_DIR/venv"
sudo -u pi-star "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u pi-star "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/pi-agent/requirements.txt"

cp "$APP_DIR/deploy/systemd/airradar-pi.service" "$SERVICE"
sed -i "s#https://radar\.kuvan\.dev/api/update#${API_URL}#g" "$SERVICE"

systemctl daemon-reload
systemctl enable --now airradar-pi
sleep 2
systemctl --no-pager --full status airradar-pi
