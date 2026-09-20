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

### 2. A joint limit wider than the linkage parks the target past the stop

- Location: [main sketch](arduino/octavius_arm/octavius_arm.ino), the range constants.
- Commit `f77bcff` widened pitch from its calibrated `60..140` to `0..180` and gave yaw the same `0..180`. Presses accumulate onto the target, so a burst of taps drives the target to a limit the arm cannot reach. The servo stalls against its mechanical stop while the target keeps counting past it, and the joint then ignores every further press in that direction until the opposite direction has unwound the gap.
- Reproduced by replaying the 2026-09-20 log through [tests/test_firmware.py](tests/test_firmware.py): 117 `PITCH_UP` presses drove the servo to angle `0`, a full 90 degrees past home.
- Matches the reported symptom that up and right do nothing from rest but move a long way after the arm has first been brought down or left.
- Fixed by restoring `60..140` for pitch and yaw. The values are conservative and still unverified against the physical arm.

### 3. The connected labels overstate what has been checked

- Locations: [pi/control.py](pi/control.py), `Arm.status()`; [pi/web/app.js](pi/web/app.js), `refresh()`.
- The page's top `Connected` label means the browser is paired. `Nano connected` only checks that the saved serial object reports an open port.
- There is no heartbeat or servo feedback. The status can remain stale after disconnection until a command detects an error, and it cannot verify power, wiring, movement, or completion.
- Needed fix: distinguish paired browser, open serial port, last verified Nano response, and current command state. Physical movement would require feedback beyond the present hardware.

### 4. Any OK reply is accepted as success for the current command

- Location: [pi/control.py](pi/control.py), the serial reply loop in `Arm.send()`.
- The code accepts any line starting with `OK ` without matching the command that was sent. A delayed reply can therefore be attributed to the wrong request.
- Reproduced by sending `YAW_LEFT` and returning `OK CLAW_DEC` from a fake Nano: the Pi accepted it.
- Fixed: `Arm.send()` now requires the reply to name the command it sent. Request IDs would also distinguish repeated commands. Acceptance and completed motion remain separate states.

### 5. Every request now spends credits

- Locations: [pi/omni.py](pi/omni.py), `interpret()`; [pi/web/index.html](pi/web/index.html).
- Practice mode, the `live` flag, the `OCTAVIUS_OMNI_ENABLED` gate and the three-second throttle were all removed at the team's request. A present `YIBU_API_KEY` is now the only thing deciding whether voice works.
- The consequence is that there is no free way to exercise the voice path. Every attempt to debug it costs money, including the first one, which has still never succeeded.
- The confirm tap before any movement is unchanged, and `/interpret` still never touches hardware.

## Hardware and calibration still need verification

| Pin | Current behavior | What remains unverified |
| --- | --- | --- |
| D2 | Positional yaw; 3 degrees per press; range 60 to 140 | Whether 60 and 140 are inside the real travel, and which way is left |
| D3 | Positional pitch; 3 degrees per press; range 60 to 140 | Whether 60 and 140 are inside the real travel, and visible movement under load |
| D4 | Positional claw; 2 degrees per press; range 80 to 125 | Whether 80 and 125 are the true closed and open endpoints without binding |

Every limit above is a guess carried over from earlier commits, not a measured endpoint. A limit that is too narrow only costs reach; one that is too wide stalls the servo against its stop, which draws stall current and can strip gears. Widen them only after checking each endpoint with the linkage disconnected.

The claw spans 45 degrees, so at 2 degrees per press it takes 22 presses to cross. Startup and `HOME` command the midpoint, 102, from an unknown physical position. Typed `CLAW_ANGLE` commands accept 80 through 125 on both the Pi and the Nano.

Servo supply voltage/current, common ground, signal wiring, and mechanical binding have not been measured in this review. They remain possible causes of no movement, not diagnosed faults.

## Features that are limited or intentionally disabled

- Voice interpretation is off by default at the team's request. Recording audio does not itself move the arm. Live interpretation needs the server setting enabled, a working API key, internet access from the Pi, and the phone's live toggle. A suggested command still requires confirmation.
- Live OMNI audio/image interpretation has not been verified with a real provider response in this review. Existing integration tests mock the provider. Camera and microphone access alone do not prove voice control works end to end.
- The implementation sends a voice clip and an optional still frame per request. Continuous realtime audio/video and autonomous object pickup are not implemented.

## Previously reported issues that are resolved or corrected in code

- Website access: an old Python process occupied port 5000 and the old service repeatedly failed. After switching to the supplied Gunicorn service, the team obtained HTTP 200 health responses and confirmed the site loaded. A hotspot firewall block was not established by the earlier evidence.
- Camera and microphone permission: the team explicitly confirmed both now work. They should not be treated as current blockers.
- Claw open and close: the claw is now incremental like pitch and yaw. `CLAW_INC` and `CLAW_DEC` step 2 degrees inside 80 to 125; the fixed open and closed positions are gone.
- A firmware rejection no longer closes the serial port, so an `ERR` reply no longer costs a two-second reconnect on the next press.

## Next diagnostic steps

1. With the arm supported and motion kept clear, press STOP once and record the exact message below the controls. `OK STOP` verifies that the Nano accepted that command; it does not test servo movement.
2. Press one small movement once, then wait. Record both the exact reply and which joint physically moved. An OK reply with no movement calls for calibration, power, wiring, and mechanical checks. A timeout or ERR reply calls for serial-path diagnosis.
3. Calibrate each endpoint with the linkage unloaded, then widen `YAW_LOW`/`YAW_HIGH`, `PITCH_LOW`/`PITCH_HIGH` and `CLAW_MIN`/`CLAW_MAX` to what you measured. Keep `ranges` in [pi/control.py](pi/control.py) in step with them.
4. Address the remaining STOP bug before testing repeated commands. Verify manual movement before enabling paid voice interpretation.

## Verification for this report

- Python suite: 27 tests pass, including [tests/test_firmware.py](tests/test_firmware.py), which compiles the sketch for the desktop with g++ and replays recorded click bursts through it. A simulated servo always reaches its target, so those tests cover stepping and limits only, never physical movement.
- Separate fake-serial checks reproduced STOP rejection, connection closure on `ERR busy`, and acceptance of an unrelated OK reply. These checks did not connect to hardware.
- Pin mappings, motion limits, HOME behavior, connection labels, and practice uploads were checked in the source.
- No new firmware compilation or physical motion test was performed for this documentation change. The passing software tests do not resolve the reported hardware symptom.
