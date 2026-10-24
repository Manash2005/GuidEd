import os
import sys
import urllib.parse
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
load_dotenv(ENV_FILE)

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8080"
SCOPE = "https://www.googleapis.com/auth/calendar"

def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("[ERROR] GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in backend/.env")
        sys.exit(1)

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    print("\n" + "=" * 70)
    print("GOOGLE OAUTH2 REFRESH TOKEN GENERATOR")
    print("=" * 70)
    print("\n1. Make sure your OAuth Client in Google Cloud Console has:")
    print(f"   Authorized redirect URI: {REDIRECT_URI}")
    print("\n2. Open this URL in your browser to authorize access:\n")
    print(auth_url)
    print("\n" + "-" * 70)
    print("3. After authorizing, your browser will redirect to a URL starting with:")
    print(f"   {REDIRECT_URI}/?code=YOUR_AUTHORIZATION_CODE...")
    print("   (Even if the page says 'This site can't be reached', copy the code from the address bar!)")
    print("-" * 70)

    auth_code = input("\nEnter the 'code' parameter value (or the full redirect URL): ").strip()
    if not auth_code:
        print("[ERROR] No code entered.")
        sys.exit(1)

    if "code=" in auth_code:
        parsed = urllib.parse.urlparse(auth_code)
        query_params = urllib.parse.parse_qs(parsed.query)
        auth_code = query_params.get("code", [auth_code])[0]

    print("\nExchanging authorization code for refresh token...")
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI
        }
    )

    if resp.status_code != 200:
        print(f"[ERROR] Failed to exchange code ({resp.status_code}): {resp.text}")
        sys.exit(1)

    data = resp.json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        print("[WARNING] No refresh token returned. Did you include prompt=consent? Response:")
        print(data)
        sys.exit(1)

    print("\n" + "=" * 70)
    print("SUCCESS! Your Refresh Token is:")
    print(refresh_token)
    print("=" * 70)

    # Automatically save to .env if present
    if ENV_FILE.exists():
        content = ENV_FILE.read_text(encoding="utf-8")
        if "GOOGLE_REFRESH_TOKEN=" in content:
            lines = content.splitlines()
            new_lines = []
            for line in lines:
                if line.startswith("GOOGLE_REFRESH_TOKEN="):
                    new_lines.append(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
                else:
                    new_lines.append(line)
            ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print(f"\n[INFO] Automatically updated GOOGLE_REFRESH_TOKEN in {ENV_FILE}")

if __name__ == "__main__":
    main()
