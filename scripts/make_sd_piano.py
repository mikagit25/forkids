#!/usr/bin/env python3
"""Sacred Drift — "Classical Piano for Sleep": our own piano performances of public-domain scores in one long video.

  1. pieces      render_midi_piano.py (Mutopia scores PD / CC BY, Salamander Grand Piano, mood=sleep)
  2. one track   pieces in programme order, short silence between them, chapters with timestamps
  3. video       render_sd_video.py, calm night scene (moon / stars), reacts to the music
  4. thumbnail   frame + "CLASSICAL PIANO FOR SLEEP"
  5. meta        tracklist as YouTube chapters, credits (scores, piano samples), stream_safe

Output goes to sacred_drift/output/piano/ — NOT the auto queue: this is a test format, published by hand
(upload_youtube.py --publish-at) to see how the audience reacts.

    python3 scripts/make_sd_piano.py --program 1                 # full: audio + video + thumb + meta
    python3 scripts/make_sd_piano.py --program 1 --audio-only    # just render pieces, print the length
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import render_midi_piano as rmp  # noqa: E402

OUT_DIR = ROOT / "sacred_drift" / "output" / "piano"
GAP = 2.0                                   # extra silence between pieces (render already adds 3 s tail)

COMPOSER = {"ChopinFF": "Frédéric Chopin", "BachJS": "J. S. Bach", "HandelGF": "G. F. Handel",
            "TarregaF": "Francisco Tárrega", "TchaikovskyPI": "Pyotr Tchaikovsky", "BeethovenLv": "Ludwig van Beethoven",
            "SchumannR": "Robert Schumann", "LisztF": "Franz Liszt", "BrahmsJ": "Johannes Brahms",
            "SchubertF": "Franz Schubert", "MozartWA": "W. A. Mozart", "GriegE": "Edvard Grieg"}
NICE_TITLE = {
    "bach_das_wohltemperierte_clavier_i_praeludium_i_wtk1_prelude1": "Prelude in C major, BWV 846",
    "handel_air_13_air": "Air",
    "schumann_kinderscenen_traumerei_schumannop15no07": "Träumerei (Kinderszenen, Op. 15 No. 7)",
    "schumann_kinderscenen_von_fremden_landern_und_menschen_schumannop15no01": "Of Foreign Lands and Peoples (Op. 15 No. 1)",
    "schumann_kinderscenen_bittendes_kind_schumannop15no04": "Pleading Child (Op. 15 No. 4)",
    "schumann_romanzen_romanze_op28_2": "Romance in F-sharp major, Op. 28 No. 2",
    "chopin_prelude_op_28_no_6_chop_28_6": "Prelude in B minor, Op. 28 No. 6",
    "chopin_prelude_op_28_no_7_chop_28_7": "Prelude in A major, Op. 28 No. 7",
    "chopin_prelude_chopin_prelude_op45": "Prelude in C-sharp minor, Op. 45",
    "beethoven_sonata_no_8_pathetique_2nd_movement_adagio_cantabi_pathetique_2": "Pathétique Sonata – Adagio cantabile",
    "beethoven_sonata_no_17_2nd_movement_adagio_lvb_sonate_31no2_2": "Sonata No. 17 – Adagio",
    "liszt_consolation_s_172_no_1_liszt_consolation_no": "Consolation No. 1",
    "liszt_consolation_s_172_no_4_liszt_consolation_no": "Consolation No. 4",
    "brahms_waltz_no_15_waltz_op39_15": "Waltz in A-flat major, Op. 39 No. 15",
    "tchaikovsky_morning_prayer_01morningprayer": "Morning Prayer (Children's Album)",
    "tchaikovsky_old_french_song_16oldfrenchsong": "Old French Song (Children's Album)",
    "mozart_piano_sonata_in_c_minor_kv_457_2nd_movement_sonata2": "Sonata in C minor, K. 457 – Adagio",
    "grieg_ases_tod_02_lamortdase": "Åse's Death (Peer Gynt)",
    "tarrega_lagrima_lagrima_duo": "Lágrima",
    "bach_schafe_konnen_sicher_weiden_sheep_will_safely_graz_sheep": "Sheep May Safely Graze, BWV 208",
    "schumann_kinderscenen_gluckes_genug_schumannop15no05": "Perfect Happiness (Op. 15 No. 5)",
    "mozart_ave_verum_corpus_aveverumm": "Ave verum corpus, K. 618",
    "schubert_ave_maria_ellens_dritter_gesang_schubertf_d839_avema": "Ave Maria, D. 839",
}

# programme 1: ~1 h, from gentle light pieces towards slower, darker ones (sleep arc)
PROGRAMS = {
    1: ["bach_das_wohltemperierte_clavier_i_praeludium_i_wtk1_prelude1",
        "schumann_kinderscenen_von_fremden_landern_und_menschen_schumannop15no01",
        "bach_schafe_konnen_sicher_weiden_sheep_will_safely_graz_sheep",
        "tchaikovsky_morning_prayer_01morningprayer",
        "chopin_prelude_op_28_no_7_chop_28_7",
        "brahms_waltz_no_15_waltz_op39_15",
        "handel_air_13_air",
        "schumann_kinderscenen_traumerei_schumannop15no07",
        "schumann_kinderscenen_gluckes_genug_schumannop15no05",
        "liszt_consolation_s_172_no_1_liszt_consolation_no",
        "beethoven_sonata_no_8_pathetique_2nd_movement_adagio_cantabi_pathetique_2",
        "tchaikovsky_old_french_song_16oldfrenchsong",
        "schubert_ave_maria_ellens_dritter_gesang_schubertf_d839_avema",
        "schumann_romanzen_romanze_op28_2",
        "chopin_prelude_op_28_no_6_chop_28_6",
        "tarrega_lagrima_lagrima_duo",
        "liszt_consolation_s_172_no_4_liszt_consolation_no",
        "mozart_piano_sonata_in_c_minor_kv_457_2nd_movement_sonata2",
        "schumann_kinderscenen_bittendes_kind_schumannop15no04",
        "mozart_ave_verum_corpus_aveverumm",
        "beethoven_sonata_no_17_2nd_movement_adagio_lvb_sonate_31no2_2",
        "chopin_prelude_chopin_prelude_op45",
        "grieg_ases_tod_02_lamortdase"],
}


def ts(sec: float) -> str:
    s = int(sec)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def duration(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)


def render_pieces(prog: int, seed: int):
    rows = {r["file_base"]: r for r in rmp.scores()}
    pieces = []
    for i, fb in enumerate(PROGRAMS[prog]):
        meta = rows.get(fb)
        if meta is None:
            sys.exit(f"{fb}: not in the PD / CC BY score list")
        name = f"{fb}_sleep_s{seed + i}"
        mp3 = rmp.OUT / f"{name}.mp3"
        if not mp3.exists():
            rmp.render(rmp.MUSIC / f"{fb}.mid", slow=1.06, mood="sleep", seed=seed + i, out_name=name, meta=meta)
        pieces.append((mp3, meta))
    return pieces


def join(pieces, out: Path):
    """Concatenate with GAP s of silence; returns chapter start times."""
    starts, t = [], 0.0
    with tempfile.TemporaryDirectory() as td:
        sil = Path(td) / "gap.mp3"           # same codec/rate as the pieces, or the concat demuxer chokes
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-t", str(GAP), "-c:a", "libmp3lame", "-b:a", "256k", str(sil)], check=True)
        lst = Path(td) / "list.txt"
        lines = []
        for mp3, _ in pieces:
            starts.append(t)
            lines += [f"file '{mp3}'", f"file '{sil}'"]
            t += duration(mp3) + GAP
        lst.write_text("\n".join(lines) + "\n")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-af", "aresample=44100", "-c:a", "libmp3lame", "-b:a", "256k", str(out)], check=True)
    return starts


def thumbnail(video: Path, out: Path, hours: int | None):
    from PIL import Image, ImageEnhance
    import thumb_text as tt
    frame = out.with_suffix(".frame.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "40", "-i", str(video), "-frames:v", "1",
                    "-vf", "scale=1280:720", str(frame)], check=True)
    img = Image.open(frame).convert("RGB")
    img = ImageEnhance.Brightness(img).enhance(1.35)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = tt.add_thumb_text(img, "CLASSICAL PIANO FOR SLEEP", duration_hours=hours, channel_tag="Sacred Drift")
    img.save(out, "PNG", optimize=True)
    frame.unlink(missing_ok=True)


def build_meta(pieces, starts, total: float, scene: str, seed: int) -> dict:
    mins = total / 60
    dur = f"{round(mins / 60)} Hour" + ("s" if round(mins / 60) > 1 else "") if mins >= 55 else f"{round(mins)} Minutes"
    names = []
    fame = ["ChopinFF", "BeethovenLv", "SchumannR", "LisztF", "MozartWA", "BachJS", "TchaikovskyPI", "BrahmsJ"]
    for _, m in sorted(pieces, key=lambda x: fame.index(x[1]["composer"]) if x[1]["composer"] in fame else 99):
        c = COMPOSER.get(m["composer"], m["composer"]).split()[-1]
        if c not in names:
            names.append(c)
    title = f"Classical Piano for Sleep 🌙 {', '.join(names[:3])} • {dur}"
    chapters = "\n".join(f"{ts(s)} {COMPOSER.get(m['composer'], m['composer'])} — {NICE_TITLE.get(m['file_base'], m['title'])}"
                         for s, (_, m) in zip(starts, pieces))
    cc_by = [m for _, m in pieces if m["license"].startswith("CC")]
    score_credit = ("Scores: The Mutopia Project (mutopiaproject.org) — public-domain editions"
                    + ("; these editions are licensed CC BY and credited here:\n" +
                       "\n".join(f"• {NICE_TITLE.get(m['file_base'], m['title'])} — {m['source']}" for m in cc_by)
                       if cc_by else "."))
    desc = "\n\n".join([
        f"Gentle classical piano for sleep — {len(pieces)} calm pieces by {', '.join(names[:-1])} and {names[-1]}, "
        "played slowly and softly, one after another, under a quiet night sky.",
        "Tracklist:\n" + chapters,
        "The programme moves from light, open pieces at the start towards slower and darker ones near the end, so the "
        "music settles as you fall asleep. Every piece is played softly with a warm sustain pedal and a natural hall, "
        "and there are a few seconds of silence between pieces. The volume stays low and even from start to finish, "
        "without sudden loud passages.",
        "About this recording:\nThese are our own performances, rendered note by note from public-domain scores — no "
        "existing recording is used. The phrasing, dynamics, pedalling and gentle rubato are shaped by our own "
        "performance code, and the sound comes from a sampled concert grand piano.",
        "How to listen:\n• Low volume, headphones or soft speakers\n• Start it as you go to bed — the pieces get "
        "calmer towards the end\n• Also good for reading, studying or a quiet evening",
        "About Sacred Drift:\nSacred Drift is a sanctuary of sound — singing bowls, solfeggio tones, cosmic ambient, "
        "rain, sleep music and now classical piano for deep rest and inner calm. Visuals are generated by code and "
        "move with the music. New sessions every week.\n\nSubscribe 🔮 @SacredDrift",
        "Credits:\n🎹 Piano samples: Salamander Grand Piano by Alexander Holm (CC BY 3.0)\n📜 " + score_credit
        + "\n🎶 Performance and video: Sacred Drift",
        "#classicalpiano #sleepmusic #pianoforsleep #chopin #sacreddrift #relaxingmusic",
    ])
    tags = ["classical piano for sleep", "piano sleep music", "classical music for sleep", "relaxing piano",
            "calm piano", "chopin", "schumann", "beethoven", "liszt", "bach", "brahms", "traumerei",
            "classical music", "sleep music", "study music", "soft piano", "sacred drift", dur.lower()]
    return {"title": title, "description": desc, "tags": tags, "video_type": "piano_classics",
            "language": "en", "is_short": False, "status": "public", "made_for_kids": False,
            "ai_generated": False, "music_source": "procedural_piano_pd_scores", "category": "classical_piano",
            "scene": scene, "seed": seed, "duration_sec": int(total), "stream_safe": True,
            "pieces": [{"start": round(s, 1), "file": p.name, "composer": m["composer"], "title": m["title"],
                        "license": m["license"], "source": m["source"]} for s, (p, m) in zip(starts, pieces)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--program", type=int, default=1, choices=sorted(PROGRAMS))
    ap.add_argument("--seed", type=int, default=101)
    ap.add_argument("--scene", default="night")
    ap.add_argument("--audio-only", action="store_true")
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"sd_piano_sleep_p{a.program}_s{a.seed}"
    print("① pieces …")
    pieces = render_pieces(a.program, a.seed)
    audio = OUT_DIR / f"{stem}.mp3"
    print("② joining …")
    starts = join(pieces, audio)
    total = duration(audio)
    print(f"   {len(pieces)} pieces, {total / 60:.1f} min → {audio}")
    meta = build_meta(pieces, starts, total, a.scene, a.seed)
    (OUT_DIR / f"meta_{stem}.yaml").write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    print(f"   title: {meta['title']}  ({len(meta['description'].split())} words)")
    if a.audio_only:
        return
    mp4 = OUT_DIR / f"{stem}.mp4"
    print(f"③ video ({a.scene}) …")
    subprocess.run([sys.executable, str(ROOT / "scripts/render_sd_video.py"), "--audio", str(audio),
                    "--scene", a.scene, "--seed", str(a.seed), "--out", str(mp4)], check=True)
    print("④ thumbnail …")
    thumbnail(mp4, OUT_DIR / f"thumb_{stem}.png", int(total // 3600) or None)
    print(f"✅ {mp4}")


if __name__ == "__main__":
    main()
