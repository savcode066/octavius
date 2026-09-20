"""Generate a private local CA and a server certificate for the Pi hotspot."""
import ipaddress
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

ROOT = Path(__file__).resolve().parent

def setup(root=ROOT):
    root = Path(root)
    certs = root / "certs"
    certs.mkdir(mode=0o700, exist_ok=True)
    now = datetime.now(timezone.utc)
    ca_key_path, ca_path = certs / "ca.key", certs / "ca.crt"
    if ca_key_path.exists() and ca_path.exists():
        ca_key = serialization.load_pem_private_key(ca_key_path.read_bytes(), None)
        ca = x509.load_pem_x509_certificate(ca_path.read_bytes())
    elif ca_key_path.exists() or ca_path.exists():
        raise RuntimeError("Incomplete certificate authority. Restore the matching ca.key and ca.crt.")
    else:
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Octavius Local CA")])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
              .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
              .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=1825))
              .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
              .add_extension(x509.KeyUsage(False,False,False,False,False,True,True,None,None), critical=True)
              .sign(ca_key, hashes.SHA256()))
        ca_key_path.write_bytes(ca_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        ca_key_path.chmod(0o600)
        ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "octavius.local")])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(ca.subject)
            .public_key(server_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=90))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("10.42.0.1")),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),x509.DNSName("octavius.local"),
                x509.DNSName("localhost")]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.KeyUsage(True,False,True,False,False,False,False,None,None), critical=True)
            .sign(ca_key, hashes.SHA256()))
    (certs/"server.key").write_bytes(server_key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    (certs/"server.key").chmod(0o600)
    (certs/"server.crt").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    # Only this public certificate is ever served by the setup page.
    (certs/"octavius-ca.cer").write_bytes(ca.public_bytes(serialization.Encoding.DER))
    env = root / ".env"
    existing = env.read_text() if env.exists() else ""
    defaults = {"YIBU_API_KEY":"",
                "OCTAVIUS_OMNI_MODEL":"qwen3.5-omni-flash","OCTAVIUS_SERIAL_PORT":"auto",
                "OCTAVIUS_PAIR_CODE":str(secrets.randbelow(900000)+100000),
                "OCTAVIUS_SESSION_SECRET":secrets.token_hex(32),"OCTAVIUS_SIMULATE":"0"}
    keys = {line.split("=",1)[0].strip() for line in existing.splitlines() if "=" in line}
    with env.open("a") as handle:
        handle.write("\n")
        for key,value in defaults.items():
            if key not in keys: handle.write(f"{key}={value}\n")
    env.chmod(0o600)
    code = next(line.split("=",1)[1] for line in env.read_text().splitlines() if line.startswith("OCTAVIUS_PAIR_CODE="))
    print("Phone setup: http://10.42.0.1:8080")
    print("Control page: https://10.42.0.1:5000")
    print("Pairing code:",code)
    print("Certificate SHA-256:", ca.fingerprint(hashes.SHA256()).hex())

if __name__ == "__main__":
    setup()
