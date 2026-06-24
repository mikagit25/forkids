#!/usr/bin/env python3
"""
Re-authenticate YouTube OAuth token for AR/ID channels.

Usage:
    python3 scripts/reauth_local.py --channel ar
    python3 scripts/reauth_local.py --channel id

Flow:
    1. Script prints auth URL
    2. Open URL in browser, log in as the correct Google account, click Allow
    3. Browser will show an error page (can't reach localhost) — that's OK
    4. Copy the FULL URL from the browser address bar and paste it here
    5. Token is saved automatically
"""
import argparse, json, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHANNEL_CFG = {
    "en": {"client": ROOT/"credentials"/"youtube_client.json",
           "token":  ROOT/"credentials"/"youtube_token.json",
           "account": "lapidainvest@gmail.com"},
    "ar": {"client": ROOT/"credentials"/"youtube_client_ar.json",
           "token":  ROOT/"credentials"/"youtube_token_ar.json",
           "account": "kidsar6945071@gmail.com"},
    "id": {"client": ROOT/"credentials"/"youtube_client_id.json",
           "token":  ROOT/"credentials"/"youtube_token_id.json",
           "account": "kidain6945071@gmail.com"},
}

SCOPES = " ".join([
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
])
REDIRECT_URI = "http://localhost:8090"


def build_auth_url(client_id: str, account: str) -> str:
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
        "login_hint":    account,
    })


def exchange_code(client_id, client_secret, code) -> dict:
    payload = urllib.parse.urlencode({
        "code": code, "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST",
    )
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", choices=["en", "ar", "id"], required=True)
    args = parser.parse_args()

    cfg = CHANNEL_CFG[args.channel]
    c = json.loads(cfg["client"].read_text())
    creds = c.get("installed") or c.get("web") or {}
    client_id, client_secret = creds["client_id"], creds["client_secret"]

    auth_url = build_auth_url(client_id, cfg["account"])

    print(f"\n{'='*60}")
    print(f"  Reauth: {args.channel.upper()} — {cfg['account']}")
    print(f"{'='*60}")
    print(f"\n1. Open this URL in your browser:\n\n{auth_url}\n")
    print(f"2. Log in as: {cfg['account']}")
    print(f"3. Click Allow")
    print(f"4. Browser will show an error — that's OK")
    print(f"5. Copy the FULL URL from the browser address bar\n")

    callback_url = input("Paste the full URL here: ").strip()

    params = urllib.parse.parse_qs(urllib.parse.urlparse(callback_url).query)
    code = params.get("code", [None])[0]
    if not code:
        print("ERROR: no 'code' found in the URL")
        return

    print(f"\nExchanging code for token...")
    tokens = exchange_code(client_id, client_secret, code)
    if "error" in tokens:
        print(f"ERROR: {tokens}")
        return

    out = {
        "access_token":  tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "token_uri":     "https://oauth2.googleapis.com/token",
        "client_id":     client_id,
        "client_secret": client_secret,
        "scopes":        tokens.get("scope", "").split(),
        "expires_at":    time.time() + tokens.get("expires_in", 3600),
    }
    cfg["token"].write_text(json.dumps(out, indent=2))
    cfg["token"].chmod(0o600)
    print(f"✓ Token saved: {cfg['token'].name}")
    print(f"  refresh_token: {'YES' if out['refresh_token'] else 'NO'}")


if __name__ == "__main__":
    main()
