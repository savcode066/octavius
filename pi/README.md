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
