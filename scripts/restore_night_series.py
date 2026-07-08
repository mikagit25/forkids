#!/usr/bin/env python3
"""
Restore the Classical Night Relax night-series videos:
  - Make them public again
  - Rename titles to English
  - Rewrite descriptions for adult sleep/relaxation audience
  - Update tags for the Classical Night Relax channel

These are ambient sleep videos (Moon Garden, Ocean Night, Sleepy Stars)
that were made before the rebranding and suit the new channel perfectly.

Usage:
  python3 scripts/restore_night_series.py --dry-run
  python3 scripts/restore_night_series.py
"""
import argparse, json, logging, sys, time, datetime
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
CREDS = ROOT / "credentials" / "youtube_token_id.json"

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Night series videos: video_id → new English metadata
# Original: Indonesian baby sleep videos — repurposed for adult ambient/sleep channel
NIGHT_SERIES = [
    {
        "video_id":    "tLuvCsN4Q9M",
        "title":       "🌙 Moon Garden — 1 Hour Ambient Sleep Music | Classical Night Relax",
        "description": """\
🌙 Let the tranquil beauty of a moonlit garden carry you into deep, restful sleep.

One hour of carefully chosen ambient music paired with soft, looping visuals of a night garden bathed in moonlight. Gentle and unhurried — perfect for drifting off.

🎵 Perfect for:
• Falling asleep quickly and naturally
• Late-night reading or winding down
• Meditation and mindfulness before bed
• Background music for yoga or stretching
• Relieving stress after a long day

✨ The visuals feature a peaceful moonlit garden — soft glowing light, slowly drifting elements, and a colour palette chosen to calm the nervous system and reduce screen fatigue.

No jarring transitions. No ads during playback. Just one uninterrupted hour of calm.

Subscribe for more sleep and relaxation programs ▶ @ClassicalNightRelax

#SleepMusic #AmbientMusic #MoonGarden #RelaxationMusic #ClassicalNightRelax #NightMusic #DeepSleep #MeditationMusic #ChillMusic #SleepAid
""",
        "tags": [
            "sleep music", "ambient music", "moon garden", "relaxation music",
            "night music", "deep sleep music", "sleep aid", "meditation music",
            "chill music", "calm music", "1 hour sleep music", "lofi sleep",
            "classical night relax", "sleep sounds", "peaceful music",
        ],
        "category_id": "10",   # Music
        "made_for_kids": False,
    },
    {
        "video_id":    "b-m9bxmZcEU",
        "title":       "🌊 Ocean Night — 2 Hours Ambient Sleep Music | Classical Night Relax",
        "description": """\
🌊 Two hours of gentle ocean night ambiance to guide you into deep, peaceful sleep.

The soft rhythm of waves beneath a starlit sky — this is pure rest. No words, no sudden changes. Just the ocean at night, with music that breathes at the same pace as sleep itself.

🎵 Perfect for:
• Deep, uninterrupted sleep through the night
• Anxiety relief and nervous system calming
• Study and concentration sessions
• Yoga, breathwork and evening meditation
• Blocking city noise or background sounds

The 2-hour format is ideal for a full sleep cycle — start it when you go to bed and let it carry you through to morning.

No ads. No interruptions. Subscribe for weekly sleep programs ▶ @ClassicalNightRelax

#OceanSleepMusic #AmbientMusic #SleepMusic #OceanWaves #NightAmbience #DeepSleep #RelaxationMusic #2HourSleepMusic #ClassicalNightRelax #CalmMusic #SleepSounds
""",
        "tags": [
            "ocean sleep music", "ambient music", "sleep music", "ocean waves",
            "night ambience", "deep sleep", "relaxation music", "2 hour sleep music",
            "classical night relax", "calm music", "sleep sounds", "water sounds",
            "sleep aid", "stress relief music", "peaceful night",
        ],
        "category_id": "10",
        "made_for_kids": False,
    },
    {
        "video_id":    "ZLgjYog70ZM",
        "title":       "✨ Sleepy Stars — 2 Hours Ambient Sleep Music | Classical Night Relax",
        "description": """\
✨ Drift away under a sky full of stars — two hours of ambient music designed for deep sleep.

Close your eyes and let the soft glow of a starlit night wash over you. The visuals are gentle, unhurried, and dark — crafted so your eyes can rest while the music slowly quiets your thoughts.

🎵 Perfect for:
• Full night's sleep from start to finish
• Insomnia relief and sleep onset
• Meditation, body scans and progressive relaxation
• Background ambiance for work-from-home evenings
• Winding down after screen time

Stars have guided travellers and dreamers for centuries. Let them guide you tonight.

No ads during the 2-hour program. New content every week. Subscribe ▶ @ClassicalNightRelax

#SleepyStars #NightSkyMusic #AmbientSleep #DeepSleep #SleepMusic #StarsSleepMusic #ClassicalNightRelax #RelaxationMusic #MeditationMusic #2HourSleep #CalmNight
""",
        "tags": [
            "sleepy stars", "night sky music", "ambient sleep", "deep sleep",
            "sleep music", "stars sleep music", "classical night relax",
            "relaxation music", "meditation music", "2 hour sleep", "calm night",
            "stress relief", "sleep aid", "peaceful music", "lofi sleep",
        ],
        "category_id": "10",
        "made_for_kids": False,
    },
    {
        "video_id":    "fIVuw7vWsmc",
        "title":       "🌙 Bedtime Calm — 30 Minutes Ambient Sleep Music | Classical Night Relax",
        "description": """\
🌙 A 30-minute ritual for winding down — gentle ambient music to transition your mind from busy to restful.

Sometimes you only need half an hour. This program is designed for the window between activity and sleep: the moment when screens go off, the lights dim, and your body starts letting go of the day.

🎵 Ideal for:
• Pre-sleep wind-down routine
• Power naps (set a gentle alarm)
• Evening yoga or light stretching
• Quiet reading or journaling
• Short meditation or breathing exercises

The visuals are calm and soft — no flickering, no sudden brightness. Just a gentle loop you can comfortably close your eyes to.

Subscribe for longer 1h, 2h and 8h sleep programs ▶ @ClassicalNightRelax

#BedtimeMusic #SleepMusic #AmbientMusic #ClassicalNightRelax #WindDown #RelaxationMusic #NightRoutine #30MinuteRelax #CalmMusic #SleepRoutine
""",
        "tags": [
            "bedtime music", "sleep music", "ambient music", "classical night relax",
            "wind down music", "relaxation music", "night routine", "30 minute relax",
            "calm music", "sleep routine", "pre-sleep music", "nap music",
            "stress relief", "evening music", "peaceful music",
        ],
        "category_id": "10",
        "made_for_kids": False,
    },
]


def get_youtube():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not CREDS.exists():
        log.error(f"Token not found: {CREDS}")
        log.error("Run: python3 scripts/reauth_youtube.py --channel id")
        sys.exit(1)

    t = json.loads(CREDS.read_text())
    creds = Credentials(
        token=t.get("access_token"),
        refresh_token=t["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=t["client_id"],
        client_secret=t["client_secret"],
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
    )
    creds.refresh(Request())
    t["access_token"] = creds.token
    CREDS.write_text(json.dumps(t, indent=2))
    return build("youtube", "v3", credentials=creds)


def restore_video(youtube, meta: dict, dry_run: bool) -> bool:
    vid_id = meta["video_id"]
    title  = meta["title"]
    desc   = meta["description"].strip()
    tags   = meta["tags"]

    log.info(f"\n  [{vid_id}] {title[:60]}")

    if dry_run:
        log.info(f"    [dry-run] Would restore: public + English title/desc")
        return True

    try:
        youtube.videos().update(
            part="snippet,status",
            body={
                "id": vid_id,
                "snippet": {
                    "title":       title,
                    "description": desc,
                    "tags":        tags,
                    "categoryId":  meta.get("category_id", "10"),
                },
                "status": {
                    "privacyStatus": "public",
                    "madeForKids":   meta.get("made_for_kids", False),
                    "selfDeclaredMadeForKids": meta.get("made_for_kids", False),
                },
            }
        ).execute()
        log.info(f"    ✓ Restored and updated")
        return True
    except Exception as e:
        log.error(f"    ✗ Failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    youtube = get_youtube()

    log.info(f"Restoring {len(NIGHT_SERIES)} night series videos on Classical Night Relax…")
    done = 0
    for meta in NIGHT_SERIES:
        ok = restore_video(youtube, meta, dry_run=args.dry_run)
        if ok:
            done += 1
        time.sleep(1.0)

    log.info(f"\n✓ Done: {done}/{len(NIGHT_SERIES)} videos restored.")
    if not args.dry_run:
        log.info("Videos are now public on @ClassicalNightRelax with English titles.")


if __name__ == "__main__":
    main()
