#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(id -un)" != octavius || "$PWD" != /home/octavius/pi ]]; then
  echo "Run as octavius from /home/octavius/pi."; exit 1
fi
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python setup_local.py
sudo systemctl stop octavius.service 2>/dev/null || true
if ss -ltnH 'sport = :5000' | grep -q .; then
  echo "Port 5000 is occupied. Stop your old manual app.py (Ctrl+C), then rerun this installer."; exit 1
fi
sudo install -m 644 octavius.service /etc/systemd/system/octavius.service
sudo install -m 644 octavius-setup.service /etc/systemd/system/octavius-setup.service
sudo systemctl daemon-reload
sudo systemctl enable --now octavius.service octavius-setup.service
sleep 2
if ! curl --fail --silent --cacert certs/ca.crt https://127.0.0.1:5000/health; then
  sudo journalctl -u octavius.service -n 30 --no-pager
  exit 1
fi
echo
echo "Ready. Open http://10.42.0.1:8080 on your phone for certificate setup."
