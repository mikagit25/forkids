#!/usr/bin/env python3
"""
Generate shape videos WITHOUT any text labels — universal content for both channels.
Produces both LONG (30-min, 1920×1080) and SHORT (55s, 1080×1920) versions.

Long videos replace the deleted ar_dance_shapes_* on YouTube and fill queue_ar.
Short videos go into queue_ar for scheduled publishing.

Usage:
  python3 scripts/generate_shape_notxt.py --long       # 8 long videos (30-min)
  python3 scripts/generate_shape_notxt.py --short      # 32 short videos (55s)
  python3 scripts/generate_shape_notxt.py --dance      # 4 dance combo shorts
  python3 scripts/generate_shape_notxt.py              # all of the above
  python3 scripts/generate_shape_notxt.py --upload     # upload longs to YouTube after render
  python3 scripts/generate_shape_notxt.py --force      # re-render existing
"""
import argparse
import base64
import json
import subprocess
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_AR  = ROOT / "output" / "queue_ar"
QUEUE_ID  = ROOT / "output" / "queue_id"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"

DATE_STR = datetime.now().strftime("%Y%m%d")

FPS       = 30
LONG_DUR  = 1800   # 30 min
SHORT_DUR = 55     # 55 sec

SHAPES = {
    "circle":   {"color": "#2980B9", "bg": "#E3F2FD"},
    "square":   {"color": "#E74C3C", "bg": "#FFEBEE"},
    "triangle": {"color": "#27AE60", "bg": "#F1F8E9"},
    "star":     {"color": "#F9A825", "bg": "#FFFDE7"},
    "heart":    {"color": "#E91E63", "bg": "#FCE4EC"},
    "diamond":  {"color": "#8E44AD", "bg": "#F3E5F5"},
    "oval":     {"color": "#16A085", "bg": "#E0F7FA"},
    "hexagon":  {"color": "#E67E22", "bg": "#FFF3E0"},
}

SHAPES_AR = {
    "circle": "دائرة", "square": "مربع", "triangle": "مثلث",
    "star": "نجمة", "heart": "قلب", "diamond": "معين",
    "oval": "بيضاوي", "hexagon": "سداسي",
}

SHAPES_ID = {
    "circle": "Lingkaran", "square": "Kotak", "triangle": "Segitiga",
    "star": "Bintang", "heart": "Hati", "diamond": "Belah Ketupat",
    "oval": "Oval", "hexagon": "Segi Enam",
}

DANCE_COMBOS = [
    {"shapes": ["circle", "square", "triangle"], "colors": ["#FF4444", "#27AE60", "#2980B9"], "bg": "#FFFDE7"},
    {"shapes": ["star", "heart", "circle"],      "colors": ["#F9A825", "#E91E63", "#2980B9"], "bg": "#FFF9E6"},
    {"shapes": ["diamond", "hexagon", "square"], "colors": ["#8E44AD", "#E67E22", "#E74C3C"], "bg": "#F3E5F5"},
    {"shapes": ["triangle", "star", "oval"],     "colors": ["#27AE60", "#F9A825", "#16A085"], "bg": "#E8F5E9"},
]

FLOAT_MODES = ["tb", "lr", "diag", "float"]
MUSIC_TRACKS = [
    "Carefree.mp3", "Wholesome.mp3", "Merry Go.mp3", "Pinball Spring.mp3",
    "Happy Happy Game Show.mp3", "Quirky Dog.mp3", "Life of Riley.mp3",
    "Hyperfun.mp3",
]


def render(composition: str, out_path: Path, props: dict,
           width: int = 1080, height: int = 1920, dur_frames: int = SHORT_DUR * FPS,
           timeout: int | None = 3600) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", composition,
        str(out_path),
        "--props", json.dumps(props),
        "--concurrency", "1",
        "--log", "error",
    ]
    result = subprocess.run(cmd, cwd=str(REMOTION),
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode == 0 and out_path.exists():
        return True
    print(f"    FAILED: {result.stderr[-200:]}")
    return False


def bilingual_meta_long(shape: str, is_uploaded: bool = False) -> dict:
    """Bilingual title/description for long shape video (no text = both channels)."""
    shape_ar = SHAPES_AR.get(shape, shape)
    title_en = f"Relaxing {shape.capitalize()} Shapes for Kids | 30 Minutes | Happy Bear Kids"
    title_ar = f"أشكال {shape_ar} للأطفال | 30 دقيقة | هابي بير كيدز"
    desc = (
        f"🔷 30 minutes of relaxing {shape} shape animation for babies and toddlers!\n\n"
        f"Colorful {shape}s float and dance to calm music. Perfect for:\n"
        f"• Tummy time and visual tracking\n"
        f"• Background play video\n"
        f"• Sensory stimulation for infants\n"
        f"• Calm wind-down before nap or bedtime\n\n"
        f"No language — suitable for all countries! الفيديو بدون كلام — مناسب لجميع الأطفال!\n\n"
        f"أشكال {shape_ar} ملونة تتحرك وترقص على موسيقى هادئة لمدة 30 دقيقة!\n"
        f"مثالي لـ: وقت الاسترخاء، الفيديو الخلفي أثناء اللعب، التحفيز البصري.\n\n"
        f"🔔 Subscribe → @HappyBearKids1 | اشتركوا → @HappyBearKids1\n\n"
        f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
        f"CC Attribution 4.0 — http://creativecommons.org/licenses/by/4.0/\n\n"
        f"#Shapes #Kids #HappyBearKids #BabyTV #ToddlerTV "
        f"#أشكال #أطفال #هابي_بير_كيدز\n\n"
        f"© Happy Bear Kids 2026"
    )
    return {
        "title":       title_ar,   # Arabic title for AR channel
        "title_en":    title_en,
        "description": desc,
        "tags": [shape, "shapes", "kids", "toddler", "baby", "relaxing",
                 "30 minutes", "Happy Bear Kids", shape_ar, "أشكال", "أطفال",
                 "هابي بير كيدز", "تعليمي", "رسوم متحركة"],
        "video_type": "shapes_long",
        "language":   "ar",
        "is_short":   False,
        "status":     "public",
        "uploaded":   is_uploaded,
    }


def bilingual_meta_short(shape: str) -> dict:
    shape_ar = SHAPES_AR.get(shape, shape)
    return {
        "title": f"أشكال {shape_ar} | هابي بير كيدز #Shorts",
        "description": (
            f"Colorful {shape}s dancing! 🎵 أشكال {shape_ar} ملونة ترقص!\n"
            f"#Shapes #Kids #HappyBearKids #أشكال #أطفال #هابي_بير_كيدز"
        ),
        "tags": [shape, "shapes", "kids", "shorts", shape_ar, "أشكال", "هابي بير كيدز"],
        "video_type": "short_shape_float",
        "language":   "ar",
        "is_short":   True,
        "status":     "public",
    }


def meta_long_id(shape: str) -> dict:
    shape_id = SHAPES_ID.get(shape, shape.capitalize())
    return {
        "title": f"Bentuk {shape_id} yang Rileks untuk Anak | 30 Menit | Happy Bear Kids",
        "description": (
            f"🔷 30 menit animasi bentuk {shape_id} yang menenangkan untuk bayi dan balita!\n\n"
            f"Bentuk {shape_id.lower()} berwarna-warni mengambang dan menari mengikuti musik yang tenang. "
            f"Sempurna untuk:\n"
            f"• Waktu tengkurap dan pelacakan visual\n"
            f"• Video latar belakang saat bermain\n"
            f"• Stimulasi sensorik untuk bayi\n"
            f"• Menenangkan sebelum tidur siang atau malam\n\n"
            f"Tanpa bahasa — cocok untuk semua negara! Tidak ada kata-kata.\n\n"
            f"🔔 Subscribe → @happybearkidsin\n\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
            f"CC Attribution 4.0 — http://creativecommons.org/licenses/by/4.0/\n\n"
            f"#Bentuk #{shape_id} #Anak #HappyBearKids #AnimasiBayi #ToddlerTV "
            f"#StimulasiVisual\n\n"
            f"© Happy Bear Kids Indonesia 2026"
        ),
        "tags": [shape, shape_id.lower(), "bentuk", "anak", "bayi", "rileks",
                 "30 menit", "Happy Bear Kids", "stimulasi visual", "animasi anak"],
        "video_type": "shapes_long",
        "language":   "id",
        "is_short":   False,
        "status":     "public",
    }


def meta_short_id(shape: str) -> dict:
    shape_id = SHAPES_ID.get(shape, shape.capitalize())
    return {
        "title": f"Bentuk {shape_id} | Happy Bear Kids #Shorts",
        "description": (
            f"Bentuk {shape_id.lower()} berwarna menari! 🎵\n"
            f"#Bentuk #Anak #HappyBearKids #{shape_id} #AnimasiAnak #Shorts"
        ),
        "tags": [shape, shape_id.lower(), "bentuk", "anak", "shorts", "happy bear kids"],
        "video_type": "short_shape_float",
        "language":   "id",
        "is_short":   True,
        "status":     "public",
    }


def meta_dance_short_id(shapes: list) -> dict:
    shapes_id = " + ".join(SHAPES_ID.get(s, s) for s in shapes)
    return {
        "title": f"Tari Bentuk | {shapes_id} | Happy Bear Kids #Shorts",
        "description": (
            f"Bentuk-bentuk berwarna menari! {shapes_id}\n"
            f"#TariBentuk #Anak #HappyBearKids #{shapes_id.replace(' + ','')} #Shorts"
        ),
        "tags": shapes + [s.lower() for s in shapes_id.split(" + ")] +
                ["tari bentuk", "anak", "shorts", "happy bear kids"],
        "video_type": "short_shape_dance",
        "language":   "id",
        "is_short":   True,
        "status":     "public",
    }


def write_meta(meta: dict, mp4_path: Path):
    p = mp4_path.parent / f"meta_{mp4_path.stem}.yaml"
    with open(p, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def generate_thumbnail(prompt: str, out_path: Path) -> bool:
    if out_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        return False
    try:
        import requests as _req
        key = TOGETHER_KEY_FILE.read_text().strip()
        r = _req.post(TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1280, "height": 720, "steps": 4, "n": 1,
                  "response_format": "b64_json"},
            timeout=90)
        if r.status_code == 200:
            data = r.json()["data"][0]
            b64 = data.get("b64_json")
            if b64:
                out_path.write_bytes(base64.b64decode(b64))
                return True
            url = data.get("url", "")
            if url:
                ir = _req.get(url, timeout=30)
                if ir.status_code == 200:
                    out_path.write_bytes(ir.content)
                    return True
    except Exception as e:
        print(f"    thumb error: {e}")
    return False


# ── Long videos (30-min, 1920×1080) ───────────────────────────────────────────

def gen_long(force: bool):
    print(f"\n[ShapeFloat LONG, no text] 8 shapes × 30-min → queue_ar/ + queue_id/\n")
    ok = 0
    for i, (shape, data) in enumerate(SHAPES.items()):
        fname    = f"shape_long_{shape}_{DATE_STR}.mp4"
        out_path = QUEUE_AR / fname
        if out_path.exists() and not force:
            sz = out_path.stat().st_size / 1024 / 1024
            print(f"  skip {fname} ({sz:.0f}MB)")
            ok += 1
            continue

        props = {
            "shapeName":  shape,
            "shapeColor": data["color"],
            "bgColor":    data["bg"],
            "mode":       "float",
            "count":      10,
            "showLabel":  False,
            "audioFile":  None,
            "musicFile":  MUSIC_TRACKS[i % len(MUSIC_TRACKS)],
            "speed":      "slow",
        }

        print(f"  Rendering {fname}...")
        start = time.time()
        if render("ShapeFloatLong", out_path, props,
                  width=1920, height=1080,
                  dur_frames=LONG_DUR * FPS,
                  timeout=21600):  # 6h max for 30-min video
            elapsed = (time.time() - start) / 60
            sz = out_path.stat().st_size / 1024 / 1024
            print(f"    ✓ {sz:.0f}MB in {elapsed:.0f}min")
            meta = bilingual_meta_long(shape)
            write_meta(meta, out_path)
            # Thumbnail
            thumb_path = QUEUE_AR / f"thumb_{out_path.stem}.png"
            STYLE = "children's YouTube thumbnail, no text, bright colors, 1280x720"
            thumb_prompt = (
                f"Big colorful cartoon {shape} shape character dancing and bouncing, "
                f"bright vivid background, kids educational video, {STYLE}"
            )
            if generate_thumbnail(thumb_prompt, thumb_path):
                print(f"    thumb → {thumb_path.name}")
            # Copy to queue_id/ with Indonesian meta
            dest_id = QUEUE_ID / fname
            if not dest_id.exists():
                import shutil as _sh
                _sh.copy2(str(out_path), str(dest_id))
            write_meta(meta_long_id(shape), dest_id)
            print(f"    → queue_id/{fname}")
            ok += 1
        else:
            print(f"    ✗ FAILED")
        time.sleep(2)

    print(f"\nLong videos: {ok}/8 done")
    return ok


# ── Short videos (55s, 1080×1920) ─────────────────────────────────────────────

def gen_shorts(force: bool):
    print(f"\n[ShapeFloat SHORT, no text] 8 shapes × 4 modes → queue_ar/ + queue_id/\n")
    ok = 0
    for i, (shape, data) in enumerate(SHAPES.items()):
        for j, mode in enumerate(FLOAT_MODES):
            fname    = f"shape_float_{shape}_{mode}_{DATE_STR}.mp4"
            out_path = QUEUE_AR / fname
            if out_path.exists() and not force:
                print(f"  skip {fname}"); ok += 1; continue

            props = {
                "shapeName":  shape,
                "shapeColor": data["color"],
                "bgColor":    data["bg"],
                "mode":       mode,
                "count":      {"tb": 6, "lr": 4, "diag": 5, "float": 7}[mode],
                "showLabel":  False,
                "audioFile":  None,
                "musicFile":  MUSIC_TRACKS[(i * 4 + j) % len(MUSIC_TRACKS)],
                "speed":      {"tb": "slow", "lr": "medium", "diag": "medium", "float": "slow"}[mode],
            }

            print(f"  {shape}/{mode}...", end=" ", flush=True)
            if render("ShapeFloatShort", out_path, props):
                sz = out_path.stat().st_size / 1024 / 1024
                print(f"✓ {sz:.1f}MB")
                write_meta(bilingual_meta_short(shape), out_path)
                # Copy to queue_id/ with Indonesian meta
                dest_id = QUEUE_ID / fname
                if not dest_id.exists():
                    import shutil as _sh
                    _sh.copy2(str(out_path), str(dest_id))
                write_meta(meta_short_id(shape), dest_id)
                ok += 1
            else:
                print("✗")

    print(f"\nFloat shorts: {ok}/32 done")
    return ok


def gen_dance_shorts(force: bool):
    print(f"\n[ShapeDance SHORT, no text] {len(DANCE_COMBOS)} combos → queue_ar/ + queue_id/\n")
    ok = 0
    for i, combo in enumerate(DANCE_COMBOS):
        label = "_".join(combo["shapes"])
        fname    = f"shape_dance_{label}_{DATE_STR}.mp4"
        out_path = QUEUE_AR / fname
        if out_path.exists() and not force:
            print(f"  skip {fname}"); ok += 1; continue

        props = {
            "shapes":     combo["shapes"],
            "colors":     combo["colors"],
            "bgColor":    combo["bg"],
            "bpm":        110,
            "showLabels": False,
            "audioFile":  None,
            "musicFile":  MUSIC_TRACKS[i % len(MUSIC_TRACKS)],
        }

        print(f"  {label}...", end=" ", flush=True)
        if render("ShapeDanceShort", out_path, props):
            sz = out_path.stat().st_size / 1024 / 1024
            print(f"✓ {sz:.1f}MB")
            shapes_ar = " + ".join(SHAPES_AR.get(s, s) for s in combo["shapes"])
            meta = {
                "title":       f"رقص الأشكال | {shapes_ar} | هابي بير كيدز #Shorts",
                "description": (
                    f"Colorful shapes dancing! أشكال ملونة ترقص!\n"
                    f"#Shapes #Dance #Kids #HappyBearKids #أشكال #رقص #أطفال"
                ),
                "tags": combo["shapes"] + ["shapes", "dance", "kids",
                        shapes_ar, "أشكال", "رقص", "هابي بير كيدز"],
                "video_type": "short_shape_dance",
                "language":   "ar",
                "is_short":   True,
                "status":     "public",
            }
            write_meta(meta, out_path)
            # Copy to queue_id/ with Indonesian meta
            dest_id = QUEUE_ID / fname
            if not dest_id.exists():
                import shutil as _sh
                _sh.copy2(str(out_path), str(dest_id))
            write_meta(meta_dance_short_id(combo["shapes"]), dest_id)
            ok += 1
        else:
            print("✗")

    print(f"\nDance shorts: {ok}/{len(DANCE_COMBOS)} done")
    return ok


def upload_to_youtube(mp4_paths: list[Path], dry_run: bool = False):
    """Upload rendered long videos directly to YouTube (bypass queue)."""
    import json as _j
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    import google.auth.transport.requests

    json_path = ROOT / "credentials" / "youtube_token.json"
    with open(json_path) as f:
        t = _j.load(f)
    creds = Credentials(
        token=t.get("access_token"), refresh_token=t.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=t.get("client_id"), client_secret=t.get("client_secret"),
    )
    if creds.expired or not creds.valid:
        creds.refresh(google.auth.transport.requests.Request())
    youtube = build("youtube", "v3", credentials=creds)

    print(f"\nUploading {len(mp4_paths)} long shape videos to YouTube...\n")
    ok = 0
    for mp4 in mp4_paths:
        if not mp4.exists():
            print(f"  skip (missing): {mp4.name}")
            continue
        meta_path  = mp4.parent / f"meta_{mp4.stem}.yaml"
        thumb_path = mp4.parent / f"thumb_{mp4.stem}.png"
        meta = yaml.safe_load(open(meta_path)) if meta_path.exists() else {}
        title = meta.get("title", mp4.stem)
        desc  = meta.get("description", "")
        tags  = meta.get("tags", [])

        print(f"  Uploading: {mp4.name}")
        print(f"  Title: {title[:70]}")

        if dry_run:
            print("  [DRY RUN]"); ok += 1; continue

        body = {
            "snippet": {
                "title": title, "description": desc,
                "tags": tags[:40], "categoryId": "22",
                "defaultLanguage": "ar",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": True},
        }
        media = MediaFileUpload(str(mp4), mimetype="video/mp4",
                                resumable=True, chunksize=4 * 1024 * 1024)
        req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        video_id = None
        while True:
            status, response = req.next_chunk()
            if status:
                print(f"    {int(status.progress()*100)}%", end="\r")
            if response:
                video_id = response["id"]
                print(f"\n  ✓ https://youtu.be/{video_id}")
                break

        if video_id:
            if thumb_path.exists():
                try:
                    m = MediaFileUpload(str(thumb_path), mimetype="image/png", resumable=False)
                    youtube.thumbnails().set(videoId=video_id, media_body=m).execute()
                    print(f"  ✓ thumbnail set")
                except Exception as e:
                    print(f"  ⚠ thumb: {e}")
            meta["youtube_id"] = video_id
            meta["uploaded"]   = True
            with open(meta_path, "w") as f:
                yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            # Move to uploaded/
            import shutil
            uploaded_dir = ROOT / "uploaded"
            uploaded_dir.mkdir(exist_ok=True)
            shutil.move(str(mp4), str(uploaded_dir / mp4.name))
            shutil.move(str(meta_path), str(uploaded_dir / meta_path.name))
            if thumb_path.exists():
                shutil.move(str(thumb_path), str(uploaded_dir / thumb_path.name))
            ok += 1

        time.sleep(3)

    print(f"\nUploaded: {ok}/{len(mp4_paths)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--long",    action="store_true", help="Generate long videos (30-min)")
    parser.add_argument("--short",   action="store_true", help="Generate short videos (55s)")
    parser.add_argument("--dance",   action="store_true", help="Generate dance combo shorts")
    parser.add_argument("--upload",  action="store_true", help="Upload long videos to YouTube after render")
    parser.add_argument("--force",   action="store_true", help="Re-render existing")
    parser.add_argument("--dry-run", action="store_true", help="Test upload without actually uploading")
    args = parser.parse_args()

    # Default: generate all
    do_long  = args.long or not (args.long or args.short or args.dance)
    do_short = args.short or not (args.long or args.short or args.dance)
    do_dance = args.dance or not (args.long or args.short or args.dance)

    QUEUE_AR.mkdir(parents=True, exist_ok=True)
    QUEUE_ID.mkdir(parents=True, exist_ok=True)

    if do_long:
        gen_long(args.force)
        if args.upload:
            longs = sorted(QUEUE_AR.glob(f"shape_long_*_{DATE_STR}.mp4"))
            upload_to_youtube(longs, dry_run=args.dry_run)

    if do_short:
        gen_shorts(args.force)

    if do_dance:
        gen_dance_shorts(args.force)

    if args.upload and not do_long:
        longs = sorted(QUEUE_AR.glob(f"shape_long_*_{DATE_STR}.mp4"))
        upload_to_youtube(longs, dry_run=args.dry_run)

    # Summary
    long_ready  = list(QUEUE_AR.glob("shape_long_*.mp4"))
    short_ready = list(QUEUE_AR.glob("shape_float_*.mp4")) + list(QUEUE_AR.glob("shape_dance_*.mp4"))
    print(f"\n=== Shape no-text videos in queue_ar ===")
    print(f"  Long  (30-min): {len(long_ready)}")
    print(f"  Short (55s):    {len(short_ready)}")


if __name__ == "__main__":
    main()
