# Raspberry Pi control server

The Pi hosts the Octavius control page on the `Octavius` Wi-Fi network and
forwards validated commands to the Arduino Nano over USB.

## Install

From this folder on the Pi:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Connect the Nano to a Pi USB port, then find its device name:

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

The default is `/dev/ttyACM0`. If your Nano is on another port, set it before starting:

```bash
export OCTAVIUS_SERIAL_PORT=/dev/ttyUSB0
```

Start the server:

```bash
python app.py
```

With an iPhone or laptop connected to the Pi's `Octavius` hotspot, open:

```text
http://10.42.0.1:5000
```

Camera and microphone access require HTTPS. Create a local certificate on the
Pi once, then start the server with TLS enabled:

```bash
mkdir -p ~/pi/certs
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout ~/pi/certs/octavius.key \
  -out ~/pi/certs/octavius.crt \
  -subj "/CN=10.42.0.1" \
  -addext "subjectAltName=IP:10.42.0.1"

export OCTAVIUS_TLS_CERT=~/pi/certs/octavius.crt
export OCTAVIUS_TLS_KEY=~/pi/certs/octavius.key
python app.py
```

Then open this address instead:

```text
https://10.42.0.1:5000
```

The browser will warn that the certificate is self-signed. Continue to the
site for this local test, then tap “Enable camera + mic”.

## Start automatically at boot

After the certificate exists and the virtual environment has been installed,
copy the included service file into systemd:

```bash
sudo cp ~/pi/octavius.service /etc/systemd/system/octavius.service
sudo systemctl daemon-reload
sudo systemctl enable --now octavius.service
```

After that, the control center starts when the Pi powers on, even when no SSH
session is open. Check its status with:

```bash
sudo systemctl status octavius.service
```

View live server logs with:

```bash
journalctl -u octavius.service -f
```

The page has buttons and a command box. You can type commands such as
`YAW_LEFT`, `PITCH_UP`, `CLAW_OPEN`, or `PITCH_ANGLE 95`.

The media panel can request access to the iPhone camera and microphone. It can
save a still camera frame to `pi/uploads/latest.jpg` and a short microphone
recording to `pi/audio_uploads/`. Safari may require the page to be served over
HTTPS before it will grant camera and microphone access.

To use a terminal on the Pi instead, leave `app.py` running and open another
terminal:

```bash
python console.py
```

Type `HELP` for the command list, or `QUIT` to exit.

## API

- `GET /health` - server status.
- `GET /command?cmd=WAVE` - send a safe arm command.
- `POST /command` with JSON `{ "command": "CLAW_CLOSE" }` - send a command.
- `POST /command` also accepts bounded values such as `{ "command": "PITCH_ANGLE 95" }`.
- `POST /photo` with multipart field `photo` - save the latest iPhone camera frame.
- `POST /audio` with multipart field `audio` - save the latest iPhone microphone recording.

The media endpoints store the latest inputs for the Huawei OMNI integration.
