# Raspberry Pi installation

These instructions assume Pi username `octavius`, code at `/home/octavius/pi`,
and hotspot address `10.42.0.1`. Keep the servo power off until firmware is uploaded.

## 1. Copy from Windows

Connect the laptop to Octavius Wi-Fi. In Windows PowerShell (not SSH):

```powershell
cd C:\Users\dines\Downloads\repos\octavius
scp -r .\pi octavius@10.42.0.1:/home/octavius/
ssh octavius@10.42.0.1
```

The local ignored `.env`, if present, contains your private configuration.
Do not share it or copy it into a public repository.

## 2. Install on the Pi

The Pi needs internet for pip installation. Ethernet to an internet-connected
router is a straightforward way to keep its Octavius hotspot available too.
Otherwise install while on an internet-connected Wi-Fi, then restore the hotspot.

Run in the Pi SSH terminal:

```bash
cd ~/pi
bash install.sh
```

This installs dependencies, creates a local CA and server certificate, generates
a pairing code, and enables HTTPS and certificate-setup services at boot.
Rerunning preserves the CA (so phones remain trusted) and your settings, while
renewing the server certificate. Renew before its 90-day validity expires.

If port 5000 is already occupied, stop your old foreground server with Ctrl+C.
Use `sudo ss -ltnp 'sport = :5000'` to identify the process if needed.
The installer reports the conflict rather than terminating unknown processes.

If Python reports venv unavailable, install `python3-venv` through apt and rerun.
The service expects an existing `dialout` group, as on Raspberry Pi OS.

## 3. Open on the phone

Open `http://10.42.0.1:8080` in Safari and follow the certificate instructions.
Install the CA profile, then enable full trust under Settings → General → About
→ Certificate Trust Settings. Open `https://10.42.0.1:5000`.
Use the pairing code printed by the installer.

Windows: import `octavius-ca.cer` into Current User → Trusted Root Certification
Authorities and restart the browser. Only trust the CA created on your own Pi;
remove it from devices after the project. Never distribute `ca.key` or `server.key`.

## 4. Connect the Nano

Upload the main sketch using Arduino IDE; use the board model physically printed
on your board (classic Nano and Nano Every are different board selections).
Close Serial Monitor and connect Nano USB to Pi USB.
`OCTAVIUS_SERIAL_PORT=auto` selects a single USB serial device. If ambiguous,
set the actual port in `~/pi/.env`, for example:

```text
OCTAVIUS_SERIAL_PORT=/dev/ttyACM0
```

Check available devices with `ls /dev/serial/by-id/`. A stable by-id path is
preferable when several USB devices are attached.

## 5. OMNI stays off until you enable it

Edit `~/pi/.env` with `nano ~/pi/.env`:

```text
OCTAVIUS_OMNI_ENABLED=0
YIBU_API_KEY=your-private-key
OCTAVIUS_OMNI_MODEL=qwen3.5-omni-flash
```

Leave `0` for practice. When ready, change it to `1`, restart the service, and
enable “Use OMNI for this session” on the phone. Reloading the page resets the
phone's switch to off. Only Send request spends credits; opening the page,
recording, and camera preview do not. The key stays on the Pi.

This integration supports the supplied HTTP models `qwen3.5-omni-flash`,
`qwen3.5-omni-plus`, and `qwen3.8-omni-flash`. The realtime model IDs use a
different protocol and cannot be substituted into this HTTP implementation.

The Pi itself must have internet for API calls. A phone connected to a local-only
Pi hotspot does not automatically give the Pi cellular internet. Use Ethernet,
a properly configured second Wi-Fi adapter, or a shared internet-connected LAN.
When using a different IP, use `https://octavius.local:5000` if mDNS resolves;
the included certificate covers that hostname, not arbitrary new IP addresses.

Audio and camera frames are processed in memory and not saved by this app.
Live requests send them to Yibu; practice makes no provider calls.

## Controls and diagnostics

```bash
sudo systemctl restart octavius
sudo systemctl status octavius --no-pager
sudo journalctl -u octavius -n 50 --no-pager
curl --cacert ~/pi/certs/ca.crt https://127.0.0.1:5000/health

The service writes its application and Gunicorn logs to the Pi's system journal,
which avoids filling the SD card with a second log file. Follow live logs while
pressing a phone control:

```bash
sudo journalctl -u octavius.service -f -o cat
```

Useful messages include the detected serial devices, the selected Nano port,
the command sent, the Nano reply, serial timeouts, and OMNI request status.
Media bytes are counted for diagnosis, but audio, images, transcripts, and API
keys are not written to the journal. Press Ctrl+C to stop following the logs.

The server staying online does not itself ensure the hotspot stays enabled:
keep the NetworkManager Hotspot profile set to autoconnect.

Terminal controls use the same authenticated HTTPS server:

```bash
cd ~/pi
.venv/bin/python console.py
```

Commands: `YAW_LEFT`, `YAW_RIGHT`, `PITCH_UP`, `PITCH_DOWN`,
`CLAW_INC`, `CLAW_DEC`, `WAVE`, `HOME`, `STOP`,
`PITCH_ANGLE 95`, `CLAW_ANGLE 100`.
STOP cancels movement and holds positional servos; it does not cut servo power.

## Usage reporting

```bash
cd ~/pi
.venv/bin/python summarize_usage.py
```

Private ledger: `private/yibu_api_calls.jsonl`.
Reports: `private/summary/usage_summary.json` and
`private/summary/usage_by_model_key_purpose.csv`.
Missing usage is reported as unknown, not zero. No costs are estimated.
Review reports and submit them privately according to the organizers' instructions
by September 20, 2026, 11:59 PM EDT. The app does not email anyone.

## Local development

Install requirements, set `OCTAVIUS_DEV_HTTP=1`, `OCTAVIUS_SIMULATE=1`,
and `OCTAVIUS_PAIR_CODE=123456`, then run `python app.py`.
Use `http://localhost:5000` on the same computer. Localhost is permitted for
media development; a phone accessing the computer's LAN IP still needs HTTPS.
