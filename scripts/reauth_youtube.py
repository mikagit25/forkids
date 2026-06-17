#!/usr/bin/env python3
"""
Re-authenticate YouTube OAuth token for any channel.

Flow (web, no copy-paste):
  1. Script generates OAuth URL using the web client (client_secret_kids_web.json)
  2. URL is sent to Telegram as a clickable link
  3. Admin taps the link → Google consent screen → clicks Allow
  4. Google redirects to https://medmind.pro/api/v1/auth/youtube/callback
  5. medmind backend exchanges code and saves token automatically
  6. Done — no terminal paste needed

Usage:
    python3 scripts/reauth_youtube.py              # EN channel
    python3 scripts/reauth_youtube.py --channel ar # AR channel
    python3 scripts/reauth_youtube.py --channel id # Indonesian channel
"""
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BOT_TOKEN    = "8657721269:AAEkhJ92vHR4K1CkA14nFcy0_bA95c38QZk"
CHAT_ID      = "209381269"
WEB_SECRET   = ROOT / "credentials" / "client_secret_kids_web.json"
CALLBACK_URL = "https://medmind.pro/api/v1/auth/youtube/callback"

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CHANNEL_CFG = {
    "en": {"name": "Happy Bear Kids 🐻 EN", "state": "kids"},
    "ar": {"name": "Happy Bear Kids 🐻 AR", "state": "kids_ar"},
    "id": {"name": "Happy Bear Kids 🐻 ID", "state": "kids_id"},
}


def send_telegram(text: str) -> None:
    try:
        payload = json.dumps({
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
        print("✓ Ссылка отправлена в Telegram")
    except Exception as e:
        print(f"  (Telegram не отвечает: {e})")


def build_auth_url(client_id: str, state: str) -> str:
    params = {
        "client_id":     client_id,
        "redirect_uri":  CALLBACK_URL,
        "response_type": "code",
        "scope":         " ".join(SCOPES),
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", choices=["en", "ar", "id"], default="en")
    args = parser.parse_args()

    cfg = CHANNEL_CFG[args.channel]

    if not WEB_SECRET.exists():
        print(f"ERROR: {WEB_SECRET} not found")
        return

    with open(WEB_SECRET) as f:
        secret = json.load(f)
    client_id = (secret.get("web") or secret.get("installed") or {})["client_id"]

    auth_url = build_auth_url(client_id, cfg["state"])

    print(f"\n{'='*60}")
    print(f"  Reauth: {cfg['name']}")
    print(f"  State:  {cfg['state']}")
    print(f"{'='*60}")
    print(f"\nОткрой ссылку в браузере (войди под нужным Google аккаунтом):\n")
    print(auth_url)
    print(f"\nИли жди ссылку в Telegram.\n")

    send_telegram(
        f"🔑 <b>YouTube reauth — {cfg['name']}</b>\n\n"
        f"Войди в нужный Google аккаунт и нажми:\n"
        f'<a href="{auth_url}">👉 Авторизовать {cfg["name"]}</a>\n\n'
        f"После нажатия «Разрешить» токен сохранится автоматически."
    )

    print("После авторизации в браузере токен сохранится автоматически.")
    print("Скрипт завершён.")


if __name__ == "__main__":
    main()
