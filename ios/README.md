# iPhone controller

1. Join Octavius Wi-Fi.
2. In Safari open http://10.42.0.1:8080.
3. Download the Pi's certificate and install the profile under Settings → General
   → VPN & Device Management.
4. Enable full trust for Octavius Local CA under Settings → General → About →
   Certificate Trust Settings.
5. Open https://10.42.0.1:5000 and enter the pairing code from the installer.
6. Enable the camera. Tap Record voice, speak, then stop. Listen back if desired.
7. Tap Send request. Practice mode is free and does not interpret media.
8. Once enabled on the Pi, turn on live OMNI to interpret speech and camera
   together. Review the suggested action, then tap to run it.

The microphone stops after ten seconds. Hiding the page releases camera and mic.
Manual controls remain available without OMNI. The web app uses POST requests
and pairing; old unauthenticated Siri GET-command shortcuts are no longer used.

Apple explains the trust step here:
https://support.apple.com/102390

Only install the certificate from your own Pi. Remove the profile when finished.
