"""Step 2: narration. One WAV per scene + sentence timings (used for subtitles).

Backends:
  kokoro  - free, runs locally, Apache-2.0 model (commercial use OK). English/Spanish/French/etc, no Arabic.
  openai  - paid API (OPENAI_API_KEY), many languages incl. Arabic.
Sentences are cached, so editing one sentence only re-voices that sentence.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
SENT_PAUSE = 0.30
SCENE_TAIL = 0.75
ROOT = Path(__file__).resolve().parent.parent

_kokoro = None


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“(])", text)
    return [p.strip() for p in parts if p.strip()]


def _kokoro_say(text, voice):
    global _kokoro
    from kokoro_onnx import Kokoro
    if _kokoro is None:
        _kokoro = Kokoro(str(ROOT / "models/kokoro-v1.0.onnx"), str(ROOT / "models/voices-v1.0.bin"))
    samples, sr = _kokoro.create(text, voice=voice["name"], speed=voice.get("speed", 1.0), lang=voice.get("lang", "en-us"))
    assert sr == SR
    return np.asarray(samples, dtype=np.float32)


def _openai_say(text, voice):
    import requests
    r = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={"model": voice.get("model", "gpt-4o-mini-tts"), "voice": voice["name"], "input": text,
              "response_format": "wav", "speed": voice.get("speed", 1.0),
              **({"instructions": voice["instructions"]} if voice.get("instructions") else {})},
        timeout=120,
    )
    r.raise_for_status()
    data, sr = sf.read(io.BytesIO(r.content), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != SR:
        x = np.linspace(0, len(data), int(len(data) * SR / sr), endpoint=False)
        data = np.interp(x, np.arange(len(data)), data).astype(np.float32)
    return data


BACKENDS = {"kokoro": _kokoro_say, "openai": _openai_say}


def _trim(a: np.ndarray, thr=0.004):
    idx = np.where(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a
    s, e = max(idx[0] - int(0.02 * SR), 0), min(idx[-1] + int(0.06 * SR), len(a))
    return a[s:e]


def voice_episode(ep_dir: Path, episode: dict):
    voice = episode["voice"]
    say = BACKENDS[voice.get("backend", "kokoro")]
    out = ep_dir / "audio"
    cache = out / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    timings = {}
    for scene in episode["scenes"]:
        sid = scene["id"]
        chunks, sents, t = [], [], 0.0
        for s in split_sentences(scene["narration"]):
            key = hashlib.md5(json.dumps([s, voice], sort_keys=True).encode()).hexdigest()[:16]
            cp = cache / f"{key}.wav"
            if cp.exists():
                a, _ = sf.read(cp, dtype="float32")
            else:
                a = _trim(say(s, voice))
                sf.write(cp, a, SR)
            dur = len(a) / SR
            sents.append({"text": s, "start": round(t, 3), "end": round(t + dur, 3)})
            chunks += [a, np.zeros(int(SENT_PAUSE * SR), np.float32)]
            t += dur + SENT_PAUSE
        chunks.append(np.zeros(int((SCENE_TAIL - SENT_PAUSE) * SR), np.float32))
        audio = np.concatenate(chunks)
        sf.write(out / f"{sid}.wav", audio, SR)
        timings[sid] = {"duration": round(len(audio) / SR, 3), "sentences": sents}
        print(f"[{sid}] {timings[sid]['duration']:.1f}s, {len(sents)} sentences")
    (out / "timings.json").write_text(json.dumps(timings, indent=2))
    total = sum(v["duration"] for v in timings.values())
    print(f"narration total: {total / 60:.1f} min")
    return timings
