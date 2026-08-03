#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-radar.kuvan.dev}"
REPO="https://github.com/burakuvan/airradar-pro.git"
APP_DIR="/opt/airradar-pro"
PYTHON="${PYTHON:-python3.9}"

if [[ $EUID -ne 0 ]]; then
  echo "Bu script root olarak çalıştırılmalı." >&2
  exit 1
fi

command -v git >/dev/null || dnf install -y git
command -v nginx >/dev/null || dnf install -y nginx
command -v "$PYTHON" >/dev/null || dnf install -y python39
command -v node >/dev/null || { echo "Node.js 20+ gerekli." >&2; exit 1; }

if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" pull --ff-only
else
  rm -rf "$APP_DIR"
  git clone "$REPO" "$APP_DIR"
fi

"$PYTHON" -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

cd "$APP_DIR/frontend"
npm install
npm run build

cp "$APP_DIR/deploy/systemd/airradar.service" /etc/systemd/system/airradar.service
sed "s/radar\.kuvan\.dev/${DOMAIN}/g" "$APP_DIR/deploy/nginx/airradar.conf" > "/etc/nginx/sites-enabled/${DOMAIN}"

systemctl daemon-reload
systemctl enable --now airradar nginx
nginx -t
systemctl reload nginx

curl -fsS http://127.0.0.1:8090/health >/dev/null
echo "AirRadar Pro kuruldu: https://${DOMAIN}"
