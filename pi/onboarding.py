"""HTTP certificate onboarding only. No control, credentials, or private files."""
from pathlib import Path
from flask import Flask, send_file
app = Flask(__name__)
ROOT = Path(__file__).resolve().parent

@app.get("/")
def index():
    return """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Octavius phone setup</title></head><body style="font:17px system-ui;max-width:600px;margin:32px auto;padding:20px">
    <h1>Connect to Octavius</h1><p>Complete this once on each device, while on your Octavius Wi-Fi.</p>
    <ol><li><a href="/octavius-ca.cer">Download your Pi's certificate</a> in Safari.</li>
    <li>Open Settings → General → VPN &amp; Device Management. Install the downloaded Octavius Local CA profile.</li>
    <li>Open Settings → General → About → Certificate Trust Settings. Enable full trust for Octavius Local CA.</li>
    <li><a href="https://10.42.0.1:5000">Open the control center</a> in Safari and enter the pairing code from your Pi.</li></ol>
    <p>Windows: import the downloaded certificate into Current User → Trusted Root Certification Authorities,
    then restart your browser.</p><p>This trusts certificates signed by your Pi's private certificate authority.
    Install only your own Pi's certificate. Remove this profile when the project is over.</p>
    <p>No private key is downloaded. Camera and mic permission will be requested separately.</p></body></html>"""

@app.get("/octavius-ca.cer")
def certificate():
    return send_file(ROOT/"certs/octavius-ca.cer", mimetype="application/x-x509-ca-cert")
