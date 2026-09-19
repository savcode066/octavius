# Raspberry Pi control server

The Pi hosts the iPhone control page on the `Octavius` Wi-Fi network and forwards named commands to the Arduino Nano over USB.

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

## API

- `GET /health` - server status.
- `GET /command?cmd=WAVE` - send a named arm command.
- `POST /command` with JSON `{ "command": "CLAW_CLOSE" }` - send a command.
- `POST /photo` with multipart field `photo` - save the latest iPhone photo for later vision processing.

The camera upload endpoint intentionally stores photos only. Add vision after the arm mechanics and manual controls work reliably.
