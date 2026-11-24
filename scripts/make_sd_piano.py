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
    # 24.11.2026 classical experiment on Sacred Drift (owner): 1 video a week for 4 weeks, each a different theme
    2: ["bach_das_wohltemperierte_clavier_i_praeludium_ii_bwv847a", "bach_invention_4_bach_invention_04",
        "bach_sinfonia_1_bwv787", "bach_das_wohltemperierte_clavier_i_praeludium_v_bwv850a",
        "bach_invention_8_bach_invention_08", "bach_sinfonia_2_bwv788",
        "bach_das_wohltemperierte_clavier_i_praeludium_vi_bwv851a", "bach_invention_13_bach_invention_13",
        "bach_sinfonia_5_bwv791", "bach_das_wohltemperierte_clavier_i_praeludium_x_bwv855a",
        "bach_invention_14_bach_invention_14", "bach_sinfonia_9_bwv795",
        "bach_das_wohltemperierte_clavier_i_praeludium_xv_bwv860_praeludium15", "bach_invention_10_bach_invention_10",
        "bach_sinfonia_11_bwv797", "bach_das_wohltemperierte_clavier_i_praeludium_xvii_bach_prelude17",
        "bach_invention_2_bach_invention_02", "bach_sinfonia_12_bwv798",
        "bach_das_wohltemperierte_clavier_ii_praeludium_i_wtk2prelude1", "bach_invention_15_bach_invention_15",
        "bach_sinfonia_15_bwv801", "bach_das_wohltemperierte_clavier_i_praeludium_xx_bwv865_praeludium20",
        "bach_invention_7_bach_invention_07", "bach_sinfonia_6_bwv792",
        "bach_das_wohltemperierte_clavier_ii_praeludium_ii_wtk2_prelude2", "bach_invention_11_bach_invention_11",
        "bach_sinfonia_14_bwv800", "bach_das_wohltemperierte_clavier_i_praeludium_xi_bwv856_praeludium11",
        "bach_invention_3_bach_invention_03", "bach_sinfonia_3_bwv789",
        "bach_das_wohltemperierte_clavier_i_praeludium_iii_bwv848a", "bach_invention_5_bach_invention_05",
        "bach_sinfonia_4_bwv790", "bach_das_wohltemperierte_clavier_i_praeludium_viii_bwv853a",
        "bach_sinfonia_7_bwv793", "bach_das_wohltemperierte_clavier_i_praeludium_xvi_bwv861_praeludium16",
        "bach_sinfonia_8_bwv794", "bach_sinfonia_10_bwv796", "bach_das_wohltemperierte_clavier_ii_praeludium_vi_bwv875a",
        "bach_sinfonia_13_bwv799"],
    3: ["mozart_sonate_opus_kv_331_variation_1_kv331_1_2_var1", "mozart_sonate_opus_kv_331_variation_2_kv331_1_3_var2",
        "mozart_sonate_opus_kv_331_variation_3_kv331_1_4_var3", "mozart_sonate_opus_kv_331_variation_4_kv331_1_5_var4",
        "mozart_sonate_opus_kv_331_variation_5_kv331_1_6_var5", "mozart_sonate_opus_kv_331_variation_6_kv331_1_7_var6",
        "mozart_sonate_opus_kv_331_menuetto_kv331_2_1_menuetto",
        "beethoven_sonata_no_23_appassionata_2nd_movement_andante_con_lvb_sonate_57_2",
        "mozart_piano_sonata_in_c_minor_kv_457_1st_movement_sonata1",
        "beethoven_sonata_no_17_1st_movement_largo_allegro_lvb_sonate_31no2_1",
        "schubert_moments_musicaux_no_3_in_f_minor_momentsno3",
        "beethoven_sonata_no_8_pathetique_3rd_movement_rondo_pathetique_3",
        "mozart_piano_sonata_in_c_minor_kv_457_3rd_movement_sonata3",
        "beethoven_symphony_no_7_in_a_major_2nd_movement_allegretto_symphony7_2",
        "mozart_eine_kleine_nachtmusik_1st_movement_eine_kleine_nachtmus",
        "beethoven_symphony_no_5_opus_67_2nd_movement_symphony5_2",
        "handel_air_16_airmitvar"],
    4: ["tchaikovsky_the_seasons_february_tschaikowsky_op37_2", "chopin_etude_ges_dur_chp_10_05",
        "schumann_kinderscenen_curiose_geschichte_schumannop15no02", "chopin_mazurka_op_6_no_1_mazurka_op6_no1",
        "tchaikovsky_doumka_dumka", "chopin_etude_c_dur_chp_10_01",
        "schumann_kinderscenen_wichtige_begebenheit_schumannop15no06", "chopin_mazurka_op_33_no_1_mazurka_op33_no1",
        "tchaikovsky_the_seasons_august_tschaikowsky_op37_8", "chopin_trois_nouvelles_etudes_no_1_f_minor_troisnouvellesetudes",
        "tchaikovsky_napolitan_dance_swan_lake_dansenapolitaine", "chopin_etude_f_moll_ps_chopin_25_02",
        "schumann_kinderscenen_hasche_mann_schumannop15no03", "tchaikovsky_march_of_the_wooden_soldiers_05marchofthewoodenso",
        "chopin_etude_a_moll_10_02_i", "beethoven_sonata_no_8_pathetique_1st_movement_grave_allegro__pathetique_1"],
}
# 24.11.2026 owner: classical titles lead with COMPOSER and WORK (people search by composer); purpose after "|"
TITLES = {
    2: "Bach — Inventions, Sinfonias & Well-Tempered Clavier Preludes | Piano for Study & Focus",
    3: "Mozart Sonata K. 331 & Beethoven Pathétique, Appassionata | Calm Piano for Reading",
    4: "Tchaikovsky The Seasons, Chopin Études & Schumann Kinderszenen | Romantic Winter Piano",
}
THUMBS = {2: "BACH • STUDY & FOCUS", 3: "MOZART & BEETHOVEN", 4: "TCHAIKOVSKY • CHOPIN"}
THEMES = {   # title prefix, thumbnail text, mood for the performance, scene, opening line, tags
    1: ("Classical Piano for Sleep 🌙", "CLASSICAL PIANO FOR SLEEP", "sleep", "night",
        "Gentle classical piano for sleep", ["classical piano for sleep", "piano sleep music", "sleep music"]),
    2: ("Bach Piano for Study & Focus 📚", "BACH FOR STUDY & FOCUS", "calm", "sunrise",
        "Bach for study and focus", ["bach for studying", "study music", "focus music", "classical music for studying", "bach piano"]),
    3: ("Mozart & Beethoven Piano for Reading and Calm ☕", "MOZART & BEETHOVEN PIANO", "calm", "lake",
        "Calm Mozart and Beethoven piano for reading, work and a quiet afternoon",
        ["mozart piano", "beethoven piano", "classical music for reading", "mozart for studying", "relaxing classical"]),
    4: ("Romantic Piano for a Winter Evening ❄️", "WINTER EVENING PIANO", "calm", "window",
        "Romantic piano for a winter evening",
        ["tchaikovsky the seasons", "chopin piano", "winter piano music", "romantic piano", "cozy classical music"]),
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
        name = f"{fb}_{THEMES[prog][2]}_s{seed + i}"
        mp3 = rmp.OUT / f"{name}.mp3"
        if not mp3.exists():
            rmp.render(rmp.MUSIC / f"{fb}.mid", slow=1.06 if THEMES[prog][2] == "sleep" else 1.0, mood=THEMES[prog][2], seed=seed + i, out_name=name, meta=meta)
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


def thumbnail(video: Path, out: Path, hours: int | None, text: str = "CLASSICAL PIANO FOR SLEEP"):
    from PIL import Image, ImageEnhance
    import thumb_text as tt
    frame = out.with_suffix(".frame.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "40", "-i", str(video), "-frames:v", "1",
                    "-vf", "scale=1280:720", str(frame)], check=True)
    img = Image.open(frame).convert("RGB")
    img = ImageEnhance.Brightness(img).enhance(1.35)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = tt.add_thumb_text(img, text, duration_hours=hours, channel_tag="Sacred Drift")
    img.save(out, "PNG", optimize=True)
    frame.unlink(missing_ok=True)


def build_meta(pieces, starts, total: float, scene: str, seed: int, prog: int = 1) -> dict:
    th = THEMES[prog]
    mins = total / 60
    dur = f"{round(mins / 60)} Hour" + ("s" if round(mins / 60) > 1 else "") if mins >= 55 else f"{round(mins)} Minutes"
    names = []
    fame = ["ChopinFF", "BeethovenLv", "SchumannR", "LisztF", "MozartWA", "BachJS", "TchaikovskyPI", "BrahmsJ"]
    for _, m in sorted(pieces, key=lambda x: fame.index(x[1]["composer"]) if x[1]["composer"] in fame else 99):
        c = COMPOSER.get(m["composer"], m["composer"]).split()[-1]
        if c not in names:
            names.append(c)
    title = (f"{TITLES[prog]} • {dur}" if prog in TITLES else f"{th[0]} {', '.join(names[:3])} • {dur}")[:100]
    chapters = "\n".join(f"{ts(s)} {COMPOSER.get(m['composer'], m['composer'])} — {NICE_TITLE.get(m['file_base'], m['title'])}"
                         for s, (_, m) in zip(starts, pieces))
    cc_by = [m for _, m in pieces if m["license"].startswith("CC")]
    score_credit = ("Scores: The Mutopia Project (mutopiaproject.org) — public-domain editions"
                    + ("; these editions are licensed CC BY and credited here:\n" +
                       "\n".join(f"• {NICE_TITLE.get(m['file_base'], m['title'])} — {m['source']}" for m in cc_by)
                       if cc_by else "."))
    desc = "\n\n".join([
        f"{th[4]} — {len(pieces)} pieces by {', '.join(names[:-1])} and {names[-1]}, "
        "played softly, one after another." + ("" if prog == 1 else " This is part of a short series of classical piano programmes on Sacred Drift — tell us in the comments which composers you would like next."),
        "Tracklist:\n" + chapters,
        ("The programme moves from light, open pieces at the start towards slower and darker ones near the end, so the "
         "music settles as you fall asleep. Every piece is played softly with a warm sustain pedal and a natural hall, "
         "and there are a few seconds of silence between pieces. The volume stays low and even from start to finish, "
         "without sudden loud passages.") if prog == 1 else
        ("Every piece is played at a calm, even pace with a natural concert-hall sound and a few seconds of silence "
         "between pieces, so the music stays in the background while you read, study or work. The volume is kept "
         "steady, without sudden loud passages, and the tracklist above lets you jump to any piece."),
        "About this recording:\nThese are our own performances, rendered note by note from public-domain scores — no "
        "existing recording is used. The phrasing, dynamics, pedalling and gentle rubato are shaped by our own "
        "performance code, and the sound comes from a sampled concert grand piano.",
        ("How to listen:\n• Low volume, headphones or soft speakers\n• Start it as you go to bed — the pieces get "
         "calmer towards the end\n• Also good for reading, studying or a quiet evening") if prog == 1 else
        ("How to listen:\n• Medium-low volume, headphones or speakers\n• Put it on at the start of a study or work "
         "session — one programme is about an hour\n• Also good for a quiet evening, reading or cooking"),
        "About Sacred Drift:\nSacred Drift is a sanctuary of sound — singing bowls, solfeggio tones, cosmic ambient, "
        "rain, sleep music and now classical piano for deep rest and inner calm. Visuals are generated by code and "
        "move with the music. New sessions every week.\n\nSubscribe 🔮 @SacredDrift",
        "Credits:\n🎹 Piano samples: Salamander Grand Piano by Alexander Holm (CC BY 3.0)\n📜 " + score_credit
        + "\n🎶 Performance and video: Sacred Drift",
        "#classicalpiano #sleepmusic #pianoforsleep #chopin #sacreddrift #relaxingmusic" if prog == 1 else "#classicalpiano #studymusic #relaxingmusic #pianomusic #sacreddrift",
    ])
    tags = th[5] + ["classical piano for sleep", "piano sleep music", "classical music for sleep", "relaxing piano",
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
    ap.add_argument("--scene", default=None)
    ap.add_argument("--audio-only", action="store_true")
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"sd_piano_{THEMES[a.program][2]}_p{a.program}_s{a.seed}"
    a.scene = a.scene or THEMES[a.program][3]
    print("① pieces …")
    pieces = render_pieces(a.program, a.seed)
    audio = OUT_DIR / f"{stem}.mp3"
    print("② joining …")
    starts = join(pieces, audio)
    total = duration(audio)
    print(f"   {len(pieces)} pieces, {total / 60:.1f} min → {audio}")
    meta = build_meta(pieces, starts, total, a.scene, a.seed, a.program)
    (OUT_DIR / f"meta_{stem}.yaml").write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    print(f"   title: {meta['title']}  ({len(meta['description'].split())} words)")
    if a.audio_only:
        return
    mp4 = OUT_DIR / f"{stem}.mp4"
    print(f"③ video ({a.scene}) …")
    subprocess.run([sys.executable, str(ROOT / "scripts/render_sd_video.py"), "--audio", str(audio),
                    "--scene", a.scene, "--seed", str(a.seed), "--out", str(mp4)], check=True)
    print("④ thumbnail …")
    thumbnail(mp4, OUT_DIR / f"thumb_{stem}.png", int(total // 3600) or None, THUMBS.get(a.program, THEMES[a.program][1]))
    print(f"✅ {mp4}")


if __name__ == "__main__":
    main()
