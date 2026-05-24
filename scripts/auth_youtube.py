#!/usr/bin/env python3
"""
YouTube OAuth авторизация для headless-сервера.
Без SSH-туннелей — работает через copy-paste кода.

Запуск: python3 scripts/auth_youtube.py
"""

import os
import pickle
from pathlib import Path
from urllib.parse import urlparse, parse_qs

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # разрешаем http для localhost

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

ROOT   = Path(__file__).resolve().parent.parent
CREDS  = ROOT / "credentials" / "youtube_client.json"
TOKEN  = ROOT / "credentials" / "token.pickle"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

REDIRECT = "http://localhost:9876/"


def main():
    if not CREDS.exists():
        print(f"ERROR: файл не найден: {CREDS}")
        return

    flow = Flow.from_client_secrets_file(str(CREDS), SCOPES, redirect_uri=REDIRECT)

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    print("\n" + "=" * 60)
    print("YouTube OAuth авторизация")
    print("=" * 60)
    print("\n1. Открой эту ссылку в браузере:\n")
    print(f"   {auth_url}\n")
    print("2. Войди в аккаунт YouTube-канала и нажми 'Разрешить'")
    print()
    print("3. Браузер попытается открыть localhost:9876 — страница")
    print("   НЕ загрузится, это нормально!")
    print()
    print("4. Скопируй ПОЛНЫЙ URL из адресной строки браузера")
    print("   (начинается с http://localhost:9876/?code=...)")
    print()

    redirect_url = input("Вставь URL сюда и нажми Enter: ").strip()

    if not redirect_url:
        print("ERROR: пустой URL")
        return

    try:
        flow.fetch_token(authorization_response=redirect_url)
        creds = flow.credentials
    except Exception as e:
        print(f"\nERROR при обмене токена: {e}")
        print("Убедись что скопировал ВЕСЬ URL из адресной строки.")
        return

    TOKEN.parent.mkdir(exist_ok=True)
    with open(TOKEN, "wb") as f:
        pickle.dump(creds, f)

    # Проверка — запрашиваем данные канала
    try:
        youtube = build("youtube", "v3", credentials=creds)
        resp = youtube.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
    except Exception:
        items = []

    print("\n" + "=" * 60)
    if items:
        ch = items[0]["snippet"]
        print(f"✓ Авторизация успешна!")
        print(f"  Канал : {ch['title']}")
        print(f"  ID    : {items[0]['id']}")
    else:
        print("✓ Токен сохранён.")
        print("  Каналы не найдены — убедись что аккаунт имеет YouTube-канал.")
    print(f"  Токен : {TOKEN}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
