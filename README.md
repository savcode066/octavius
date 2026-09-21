# Octavius

1st Place - Huawei OMNI Live Challenge @ Hack the North '26

A backpack robotic arm controlled from an iPhone, with optional voice and camera
understanding through the Huawei OMNI Live challenge's Yibu API.

## Run it

1. Upload `arduino/octavius_arm/octavius_arm.ino` to the Nano.
2. Follow [Pi installation](pi/README.md). It includes the Windows-to-Pi copy commands.
3. Complete the one-time [iPhone certificate setup](ios/README.md).
4. Pair the phone, test manual movements, enable the camera and record a voice clip.
5. Practice is the default and costs no credits. Enable live OMNI only when ready.

## What works

- Lightweight phone UI with local camera preview, ten-second microphone recordings,
  compressed JPEG frames, and browser conversion to mono 16 kHz WAV.
- One explicit multimodal API call per submitted live request, with no retries.
- OMNI interprets speech, language and a camera frame together. Its suggested
  action requires a tap before it is sent to the Nano.
- Manual controls and serial console work without cloud AI.
- Boot services, local certificate onboarding, device pairing, private usage ledger
  and JSON/CSV reporting.
- Bounded servo movements with a responsive software STOP command.

## Limits

This is assisted arm control, not autonomous grasping or calibrated 3D vision.
There is no encoder on the continuous-rotation yaw servo, so timed yaw cannot
guarantee a return to the same position. A slow claw movement does not measure
grip force. Calibrate detached from the linkage before use.

The OMNI path uses the supplied HTTP Chat Completions format with audio and a
camera frame. It is push-to-talk, not a continuous realtime WebSocket session.
Practice mode explicitly does not recognize speech or images.
The Pi needs internet for live OMNI; its hotspot alone does not provide internet.

Camera/microphone access requires trusted HTTPS. The included local certificate
setup works without a public domain, but each phone/laptop must trust the Pi's CA
once. Accepting a browser warning alone is not the setup.

## Repository

- `pi/`: server, phone UI, certificate setup, API integration and usage reporting
- `arduino/`: main Nano firmware
- `tests/`: hardware sketches and offline Python integration tests
- `ios/`: phone setup

Run software checks with `python -m pytest tests/test_app.py` after installing
`pi/requirements.txt` and `pytest`. Tests mock the provider and never spend credits.
Hardware sketches replace the main controller when uploaded; upload the main
sketch again before using the web controller.

## Credits

Built by Dinesh Sinnathamby, Roy Lu, and Savio Joseph Benher.
Multimodal integration: Huawei OMNI Live challenge, using Qwen OMNI through Yibu.
Request format is based on the supplied Yibu examples dated 2026-09-18.
MIT licensed; see [LICENSE](LICENSE).

## Pick up / Put down

The "Take control" panel has **Pick up** and **Put down** buttons and an object width field (cm).

- **Pick up** turns the width into a claw angle, closes the claw to it, then writes pitch 0.
- **Put down** writes pitch 110, then opens the claw (angle 110).
- **STOP MOVEMENT** aborts either one part-way.

The claw is inverted (above 90 opens, below 90 closes). Width to angle is a straight line through two measured points, set in `pi/.env` (defaults: 7 cm = 80, 9 cm = 85). To recalibrate, put a known-width object in the claw, use the typed `CLAW_ANGLE n` command to find the angle that just grips it, do the same for a second object, then update the four `OCTAVIUS_CLAW_*` values. Widths outside the calibrated range are rejected. `OCTAVIUS_PICKUP_PITCH`, `OCTAVIUS_PUTDOWN_PITCH`, `OCTAVIUS_CLAW_OPEN_ANGLE` and `OCTAVIUS_GRIP_MARGIN_DEG` are also tunable there.
