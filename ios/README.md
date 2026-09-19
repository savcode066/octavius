# iPhone controls

Join the iPhone to the Pi-hosted Wi-Fi network named `Octavius`, then open `http://10.42.0.1:5000` in Safari for the button controller.

## Voice command Shortcut

This avoids browser microphone permissions and works entirely on the local Octavius network.

1. Open **Shortcuts** and create a new shortcut named `Octavius Wave`.
2. Add **Get Contents of URL**.
3. Set the URL to `http://10.42.0.1:5000/command?cmd=WAVE`.
4. Set Method to `GET`.
5. Say “Hey Siri, Octavius Wave.”

Create copies for `CLAW_OPEN`, `CLAW_CLOSE`, and `HOME` by changing the `cmd=` value.

## Photo upload Shortcut

1. Create a new shortcut named `Octavius Photo`.
2. Add **Take Photo** and disable “Show Camera Preview” if desired.
3. Add **Get Contents of URL** after it.
4. Set URL to `http://10.42.0.1:5000/photo` and Method to `POST`.
5. Set Request Body to **Form**.
6. Add a field named `photo`, set its type to **File**, and use the image from **Take Photo** as its value.

The Pi saves the most recent photo at `pi/uploads/latest.jpg`. The first version only saves it; use that stable upload path before adding object recognition.
