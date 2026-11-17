#!/usr/bin/env python3
"""YouTube token for the Archive Tales channel (Google account mailmarkwood, same OAuth client as MedMind AR).

The MedMind backend callback (medmind.pro/api/v1/auth/youtube/callback) only knows its own channels, so it
answers "Unknown account: archive_tales" WITHOUT using the code. The code stays valid for a few minutes:
copy the whole address of that error page and pass it here. MedMind tokens are never touched.

    python auth_archive_tales.py link                 # prints the link (and sends it to the Telegram bot)
    python auth_archive_tales.py code "<address of the error page>"   # exchanges the code, checks the channel

Result: history_channel/youtube_token.json (google-auth "authorized user" format, used by run.py upload).
"""
import json
import sys
import urllib.parse
from pathlib import Path

import requests

SECRET = Path("/opt/medmind/client_secret_account3_web.json")   # mailmarkwood@gmail.com project
REDIRECT = "https://medmind.pro/api/v1/auth/youtube/callback"    # the only redirect registered for this client
STATE = "archive_tales"
SCOPES = ["https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
OUT = Path(__file__).resolve().parent / "youtube_token.json"


def client():
    raw = json.loads(SECRET.read_text())
    c = raw.get("web") or raw.get("installed")
    return c["client_id"], c["client_secret"]


def link():
    cid, _ = client()
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": REDIRECT, "response_type": "code", "scope": " ".join(SCOPES),
        "access_type": "offline", "prompt": "consent select_account", "state": STATE})
    print(url)
    try:   # same Telegram bot as MedMind reauth
        sys.path.insert(0, "/opt/medmind/backend/scripts")
        from reauth_youtube import send_telegram
        ok = send_telegram("🔑 <b>Archive Tales — YouTube токен</b>\n\nВойди как mailmarkwood, выбери канал "
                      "<b>Archive Tales</b> (не MedMind Arabic) и нажми «Разрешить».\nСтраница покажет ошибку "
                      "«Unknown account» — это нормально: скопируй адрес этой страницы целиком и пришли его Claude.\n\n"
                      f'<a href="{url}">👉 Авторизовать Archive Tales</a>')
        print("sent to Telegram" if ok else "Telegram did not answer - use the link above")
    except Exception as e:
        print(f"Telegram not sent: {e}")


def code(arg: str):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(arg).query) if "://" in arg else {"code": [arg]}
    if q.get("state", [STATE])[0] != STATE:
        sys.exit("this address is not from the Archive Tales link (state differs)")
    cid, sec = client()
    r = requests.post("https://oauth2.googleapis.com/token", timeout=20, data={
        "code": q["code"][0], "client_id": cid, "client_secret": sec,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code"})
    if r.status_code != 200:
        sys.exit(f"token exchange failed: {r.text[:300]}")
    t = r.json()
    if not t.get("refresh_token"):
        sys.exit("no refresh_token in the answer - run 'link' again (consent screen must be shown)")
    me = requests.get("https://www.googleapis.com/youtube/v3/channels", timeout=20,
                      params={"part": "snippet", "mine": "true"},
                      headers={"Authorization": f"Bearer {t['access_token']}"}).json().get("items", [])
    if not me:
        sys.exit("token has no YouTube channel")
    cid_ch, title = me[0]["id"], me[0]["snippet"]["title"]
    print(f"channel: {title}  ({cid_ch})")
    if "archive" not in title.lower():
        sys.exit("NOT saved: this is not Archive Tales - open the link again and pick the Archive Tales channel")
    OUT.write_text(json.dumps({"token": t["access_token"], "refresh_token": t["refresh_token"],
                               "token_uri": "https://oauth2.googleapis.com/token", "client_id": cid,
                               "client_secret": sec, "scopes": SCOPES}, indent=1))
    OUT.chmod(0o600)
    print(f"saved {OUT}")
    print(f"youtube_channel_id: {cid_ch}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "link":
        link()
    elif len(sys.argv) >= 3 and sys.argv[1] == "code":
        code(sys.argv[2])
    else:
        sys.exit(__doc__)
