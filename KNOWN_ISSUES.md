# Octavius: what is broken and what still needs testing

Reviewed on September 19, 2026, against commit `103c68c` and the team's latest reports. This is a documentation-only review. No Pi, Nano, or servos were operated during it, and no paid API calls were made.

## Current blocker

The team reports that the phone's manual controls do not move the arm even though the Nano appears connected and the main sketch is uploaded. The exact cause is still unconfirmed. A connection badge, successful web request, or serial acknowledgement does not measure servo movement.

The code problems below are confirmed, but none has been established as the cause of every button doing nothing.

## Confirmed code problems

### 1. STOP can be rejected while another serial request is pending

- Location: [pi/control.py](pi/control.py), `Arm.send()`.
- All commands, including `STOP`, must acquire the same nonblocking lock. If another request is opening the port or waiting for a reply, STOP fails with `Nano is busy; try again in a moment.` It is never sent to the Nano in that case.
- Reproduced with a fake serial connection and the lock held: calling `send("STOP")` produced the error and wrote zero bytes.
- The firmware handles STOP during movement when it receives it, but the web-to-serial path does not guarantee delivery. STOP also holds positional servos; it is not a power cut.
- Needed fix: prioritize STOP through a single serial owner and test it during connection setup and delayed acknowledgements without interleaving serial messages.

### 2. A normal busy reply closes the serial connection

- Location: [pi/control.py](pi/control.py), `Arm.send()` exception handling; [main sketch](arduino/octavius_arm/octavius_arm.ino), `handle()`.
- The Nano acknowledges a movement when it accepts it. It may still be moving when the user taps again, so the next command can legitimately return `ERR busy`.
- The Pi treats that reply as a connection failure, closes the port, and clears the connection. The next request must reopen the port and wait through the two-second connection delay.
- Reproduced with a fake `ERR busy` response: the port was closed and the saved connection became `None`.
- Needed fix: keep the connection open for normal firmware rejections and distinguish them from transport failures. Show that the arm is busy without treating it as disconnected.

### 3. The connected labels overstate what has been checked

- Locations: [pi/control.py](pi/control.py), `Arm.status()`; [pi/web/app.js](pi/web/app.js), `refresh()`.
- The page's top `Connected` label means the browser is paired. `Nano connected` only checks that the saved serial object reports an open port.
- There is no heartbeat or servo feedback. The status can remain stale after disconnection until a command detects an error, and it cannot verify power, wiring, movement, or completion.
- Needed fix: distinguish paired browser, open serial port, last verified Nano response, and current command state. Physical movement would require feedback beyond the present hardware.

### 4. Any OK reply is accepted as success for the current command

- Location: [pi/control.py](pi/control.py), the serial reply loop in `Arm.send()`.
- The code accepts any line starting with `OK ` without matching the command that was sent. A delayed reply can therefore be attributed to the wrong request.
- Reproduced by sending `YAW_LEFT` and returning `OK CLAW_CLOSE` from a fake Nano: the Pi accepted it.
- Needed fix: match the expected command acknowledgement. Request IDs would also distinguish repeated commands. Acceptance and completed motion should remain separate states.

### 5. Practice mode's media wording is misleading

- Locations: [pi/web/app.js](pi/web/app.js), the request form handler; [pi/omni.py](pi/omni.py), the practice response.
- `Send request` attaches the camera frame and saved audio even when live mode is off. The files go from the phone to the Pi, where practice mode ignores them.
- There is no provider call in practice mode, but the response says the camera and microphone stay local without explaining that they were uploaded to the Pi.
- Needed fix: skip media uploads in practice mode, or explicitly describe the phone-to-Pi transfer. Recording and preview can still work without a paid request.

## Hardware and calibration still need verification

| Pin | Current behavior | What remains unverified |
| --- | --- | --- |
| D2 | Continuous rotation; left `87`, right `93`, stop `90`; each movement lasts 110 ms | Whether these speed values overcome the servo's deadband and the arm's load, and whether `90` actually stops it |
| D3 | Positional; up reduces the target by 3 degrees, down increases it by 3; range 60 to 140 | Physical direction and visible movement under load; pressing farther at a limit deliberately does nothing |
| D4 | Positional; requested open `75`, closed `120`; reversed linkage sends servo commands 125 and 80 | Whether those positions actually open and close the mounted tongs without binding |

Only D4 was reversed in the latest code. D2 and D3 directions were left as requested. The team has not yet confirmed successful operation after uploading that revision. The requested claw positions are mapped through the reversed linkage, but this does not establish correct physical endpoints.

The normal requested claw targets are 45 degrees apart, but this is not a universal movement limit. Startup immediately commands the open position from an unknown physical position. Typed `CLAW_ANGLE` commands accept 60 through 140, and the reversed linkage maps those requests before sending them to D4. Calibrate endpoints with the linkage disconnected.

Servo supply voltage/current, common ground, signal wiring, and mechanical binding have not been measured in this review. They remain possible causes of no movement, not diagnosed faults.

## Features that are limited or intentionally disabled

- Voice interpretation is off by default at the team's request. Recording audio does not itself move the arm. Live interpretation needs the server setting enabled, a working API key, internet access from the Pi, and the phone's live toggle. A suggested command still requires confirmation.
- Live OMNI audio/image interpretation has not been verified with a real provider response in this review. Existing integration tests mock the provider. Camera and microphone access alone do not prove voice control works end to end.
- The implementation sends a voice clip and an optional still frame per request. Continuous realtime audio/video and autonomous object pickup are not implemented.
- With continuous rotation enabled, `HOME` does not return D2 to its original orientation. It sets an internal angle target that continuous yaw does not use. `WAVE` uses balanced timed pulses, which cannot establish an exact physical return position without feedback.

## Previously reported issues that are resolved or corrected in code

- Website access: an old Python process occupied port 5000 and the old service repeatedly failed. After switching to the supplied Gunicorn service, the team obtained HTTP 200 health responses and confirmed the site loaded. A hotspot firewall block was not established by the earlier evidence.
- Camera and microphone permission: the team explicitly confirmed both now work. They should not be treated as current blockers.
- D4 direction and calibration: the repository now requests open `75` and closed `120`, reverses them for the D4 linkage, and allows 60 through 140. Physical verification is still pending.

## Next diagnostic steps

1. With the arm supported and motion kept clear, press STOP once and record the exact message below the controls. `OK STOP` verifies that the Nano accepted that command; it does not test servo movement.
2. Press one small movement once, then wait. Record both the exact reply and which joint physically moved. An OK reply with no movement calls for calibration, power, wiring, and mechanical checks. A timeout or ERR reply calls for serial-path diagnosis.
3. Confirm D4's open and closed endpoints with the linkage unloaded before relying on the website's claw buttons. Keep those values consistent with the main sketch's allowed range.
4. Address the STOP, busy-response, and acknowledgement bugs before testing repeated commands. Verify manual movement before enabling paid voice interpretation.

## Verification for this report

- Existing Python suite: 18 tests passed using `tests/test_app.py`.
- Separate fake-serial checks reproduced STOP rejection, connection closure on `ERR busy`, and acceptance of an unrelated OK reply. These checks did not connect to hardware.
- Pin mappings, motion limits, HOME behavior, connection labels, and practice uploads were checked in the source.
- No new firmware compilation or physical motion test was performed for this documentation change. The passing software tests do not resolve the reported hardware symptom.
