"""Authenticated terminal controller using the same HTTPS server as the phone."""
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/".env")

def main():
    import ssl
    context=ssl.create_default_context(cafile=str(ROOT/"certs/ca.crt"))
    with httpx.Client(base_url=os.getenv("OCTAVIUS_SERVER_URL","https://127.0.0.1:5000"),
                      verify=context,timeout=8,trust_env=False,headers={"X-Octavius":"1"}) as client:
        response=client.post("/pair",json={"code":os.getenv("OCTAVIUS_PAIR_CODE","")})
        response.raise_for_status()
        print("Octavius connected. HELP for commands, QUIT to exit.")
        while True:
            try: command=input("octavius> ").strip().upper()
            except (EOFError,KeyboardInterrupt): break
            if command in {"QUIT","EXIT"}: break
            if command=="HELP":
                print("YAW_LEFT YAW_RIGHT PITCH_UP PITCH_DOWN CLAW_INC CLAW_DEC WAVE HOME STOP")
                print("PITCH_ANGLE 95 | CLAW_ANGLE 100");continue
            if command:
                try: print(client.post("/command",json={"command":command}).json())
                except httpx.RequestError: print("Could not reach the control server.")

if __name__=="__main__": main()
