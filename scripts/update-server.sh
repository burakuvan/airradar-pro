#!/usr/bin/env bash
set -euo pipefail
APP_DIR="/opt/airradar-pro"

git -C "$APP_DIR" pull --ff-only
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"
cd "$APP_DIR/frontend"
npm install
npm run build
systemctl restart airradar
nginx -t
systemctl reload nginx
curl -fsS https://radar.kuvan.dev/health
