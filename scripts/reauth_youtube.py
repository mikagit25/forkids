#!/usr/bin/env python3
"""
Re-authenticate YouTube OAuth token (console flow — no browser needed on server).

Run this script locally via SSH tunnel, or directly on the server.
It prints an auth URL → you open it in your browser → paste the code back.

Usage:
    python3 scripts/reauth_youtube.py
"""
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

ROOT       = Path(__file__).resolve().parent.parent
CREDS_PATH = ROOT / "credentials" / "youtube_client.json"
TOKEN_PATH = ROOT / "credentials" / "token.pickle"

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def main():
    # Delete old token to force fresh auth
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        print(f"Deleted old token: {TOKEN_PATH}")

    print(f"\nStarting OAuth flow (console mode)...")
    print(f"Credentials: {CREDS_PATH}\n")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",          # force refresh_token even if already granted
        include_granted_scopes="true",
    )

    print("=" * 60)
    print("Open this URL in your browser:\n")
    print(auth_url)
    print("\n" + "=" * 60)
    code = input("Paste the authorization code here: ").strip()

    flow.fetch_token(code=code)
    creds = flow.credentials

    TOKEN_PATH.parent.mkdir(exist_ok=True)
    with open(TOKEN_PATH, "wb") as f:
        pickle.dump(creds, f)

    print(f"\n✓ Token saved: {TOKEN_PATH}")
    print("Scopes granted:")
    for s in creds.scopes or SCOPES:
        print(f"  {s}")


if __name__ == "__main__":
    main()
