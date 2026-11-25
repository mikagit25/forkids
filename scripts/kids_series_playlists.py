#!/usr/bin/env python3
"""Happy Bear Kids EN: keep three series playlists filled (Studio analytics 25.11.2026 - playlists are the main way to keep
viewers on a made-for-kids channel: no end screens/cards).  Idempotent: creates missing playlists, adds public videos that match.

    python3 scripts/kids_series_playlists.py [--dry-run]
"""
import json, re, sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "kids_series_playlists.json"
SERIES = {
    "counting": ("🔢 Counting 1 to 10 with Fruit & Animal Friends | Happy Bear Kids",
                 "Learn to count from 1 to 10 with bouncing fruit, vegetable and animal friends - sensory counting videos for babies and toddlers.",
                 r"\bCount(ing)?\b"),
    "bedtime":  ("🌙 Bedtime & Lullabies for Babies | Happy Bear Kids",
                 "Calm sleepy lullabies for babies and toddlers - soft music and gentle sensory visuals for bedtime.",
                 r"Lullab|Sleepy|Bedtime|Goodnight|Sleep"),
    "dance":    ("🎉 Dance Party - Baby Sensory Dance Videos | Happy Bear Kids",
                 "Dancing fruit, vegetables and animals moving to the beat - high-contrast sensory dance videos for babies and toddlers.",
                 r"Danc|Parade|March|Bounce|High Contrast"),
}


def main():
    dry = "--dry-run" in sys.argv
    rebuild = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--rebuild=")]
    yt = build("youtube", "v3", credentials=Credentials.from_authorized_user_file(str(ROOT / "credentials/youtube_token.json")))
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    vids, tok = [], None
    while True:
        r = yt.playlistItems().list(part="snippet,status", playlistId=up, maxResults=50, pageToken=tok).execute()
        vids += [(i["snippet"]["resourceId"]["videoId"], i["snippet"]["title"], i["snippet"]["publishedAt"])
                 for i in r["items"] if i.get("status", {}).get("privacyStatus") == "public"]
        tok = r.get("nextPageToken")
        if not tok:
            break
    for key in rebuild:            # delete a playlist that was filled wrongly and start it again
        if key in state and not dry:
            yt.playlists().delete(id=state[key]["id"]).execute()
            print("deleted playlist", key, state.pop(key)["id"])
    for key, (title, desc, pat) in SERIES.items():
        pid = state.get(key, {}).get("id")
        if not pid:
            print("create playlist:", title)
            if dry:
                continue
            pl = yt.playlists().insert(part="snippet,status", body={"snippet": {"title": title, "description": desc},
                                                                   "status": {"privacyStatus": "public"}}).execute()
            pid = pl["id"]
            state[key] = {"id": pid, "videos": []}
        have = set(state[key]["videos"])
        todo = sorted([v for v in vids if re.search(pat, v[1], re.I) and not re.search(r"#shorts", v[1], re.I)
                       and v[0] not in have], key=lambda v: v[2], reverse=True)
        if key == "dance":   # only the sensory dance series (Oct 2026+), not the frozen v1 "Shapes Dance" / 30-min mixes
            todo = [v for v in todo if re.search(r"Sensory|Parade|Marching|Bounce", v[1], re.I) and v[2] >= "2026-10-01"
                    and not re.search(r"Disco|Lullab|Count|Shapes", v[1], re.I)]
        if key == "bedtime":
            todo = [v for v in todo if not re.search(r"Count", v[1], re.I)]
        for vid, t, _ in todo:
            print(f"  {key}: + {t[:70]}")
            if dry:
                continue
            yt.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": pid,
                                      "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
            state[key]["videos"].append(vid)
            STATE.write_text(json.dumps(state, indent=1))
    if not dry:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(state, indent=1))


if __name__ == "__main__":
    main()
