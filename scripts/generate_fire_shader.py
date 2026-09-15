#!/usr/bin/env python3
"""
Generate procedural fire video loops using moderngl GLSL shaders.
Runs headless via EGL (no GPU or display required — Mesa LLVMpipe).

Outputs 30s seamless loops to output/_ambient_loops/loop_{type}.mp4
These are drop-in replacements for Pexels footage in generate_ambient_video.py.

Usage:
  python3 scripts/generate_fire_shader.py --list
  python3 scripts/generate_fire_shader.py --type fireplace
  python3 scripts/generate_fire_shader.py --all
  python3 scripts/generate_fire_shader.py --type campfire --preview   # quick 3s test
  python3 scripts/generate_fire_shader.py --all --force               # overwrite existing
"""

import argparse, logging, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

import moderngl
import numpy as np
import yaml

# EGL backend — headless, no display needed
os.environ.setdefault('PYOPENGL_PLATFORM', 'egl')

ROOT      = Path(__file__).resolve().parent.parent
LOOPS_DIR = ROOT / 'output/_ambient_loops'
QUEUE_DIR = ROOT / 'sacred_drift/output/queue'
AUDIO_DIR = ROOT / 'sacred_drift/audio/ai_instrumental'
CONFIG    = ROOT / 'sacred_drift/config/channel_metadata_sd.yaml'
DATE_STR  = datetime.now().strftime('%Y%m%d')
TARGET_DUR = 3600

W, H  = 1280, 720
FPS   = 30
LOOP_DUR = 30  # seconds

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


# ── Shader source ─────────────────────────────────────────────────────────────

VERT = """\
#version 330
in vec2 in_vert;
out vec2 v_uv;
void main() {
    v_uv = in_vert * 0.5 + 0.5;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

FRAG = """\
#version 330

uniform float u_time;
uniform float u_speed;
uniform float u_turbulence;
uniform float u_scale;
uniform float u_height;
uniform float u_width;
uniform float u_brightness;
uniform float u_y_offset;   // shift flame base up from bottom (0=bottom, 0.3=center-ish)
uniform float u_teardrop;   // 0=bell-curve (fire/campfire), 1=teardrop (candle)
uniform vec3  u_col_base;   // deep red / ember
uniform vec3  u_col_mid;    // orange
uniform vec3  u_col_core;   // yellow / white-hot
uniform vec3  u_bg;         // background color

in  vec2 v_uv;
out vec4 fragColor;

// ── Hash & noise ──────────────────────────────────────────────────────────────
float hash2(vec2 p) {
    p  = fract(p * vec2(234.34, 435.345));
    p += dot(p, p + 34.23);
    return fract(p.x * p.y);
}
float hash3(vec3 p) {
    p  = fract(p * vec3(443.897, 397.297, 491.187));
    p += dot(p, p.yxz + 19.19);
    return fract(p.x * p.y * p.z);
}
float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
        mix(hash2(i), hash2(i + vec2(1,0)), u.x),
        mix(hash2(i + vec2(0,1)), hash2(i + vec2(1,1)), u.x),
        u.y
    );
}
float fbm(vec2 p) {
    float v = 0.0, a = 0.5;
    for (int i = 0; i < 6; i++) {
        v += a * vnoise(p);
        p  = p * 2.1 + vec2(1.31, 2.73);
        a *= 0.45;
    }
    return v;
}

// ── Fire color ramp ───────────────────────────────────────────────────────────
vec3 fire_color(float t) {
    t = clamp(t, 0.0, 1.0);
    vec3 c0 = vec3(0.0);
    vec3 c1 = vec3(0.12, 0.0, 0.0);
    if (t < 0.20) return mix(c0, c1,         smoothstep(0.00, 0.20, t));
    if (t < 0.45) return mix(c1, u_col_base,  smoothstep(0.20, 0.45, t));
    if (t < 0.72) return mix(u_col_base, u_col_mid,  smoothstep(0.45, 0.72, t));
    return             mix(u_col_mid,  u_col_core, smoothstep(0.72, 1.00, t));
}

void main() {
    // Coordinate system (with -vf vflip in FFmpeg correcting OpenGL's bottom-up storage):
    //   v_uv.y = 0 → video BOTTOM (ground / fire source)
    //   v_uv.y = 1 → video TOP (sky)
    float gy = v_uv.y;   // ground_y: 0 at bottom, increases upward
    float gx = v_uv.x;
    float t  = u_time * u_speed;

    // Local flame y (relative to the flame base, accounting for y_offset)
    float local_y = gy - u_y_offset;

    // Noise space — SUBTRACT t from y so patterns drift upward (fire rises)
    vec2 uv = vec2(gx, gy) * u_scale;
    vec2 q  = vec2(fbm(uv + vec2(0.10, -t * 0.55)),
                   fbm(uv + vec2(5.20, -t * 0.38)));
    vec2 r  = vec2(fbm(uv + u_turbulence * q + vec2(1.70, -t * 0.80)),
                   fbm(uv + u_turbulence * q + vec2(9.20, -t * 0.52)));
    float f = fbm(uv + u_turbulence * r + vec2(0.17, -t));

    // Height mask — full fire at base (local_y=0), fades to 0 at flame tip
    float h_norm = clamp(local_y / max(u_height, 0.001), 0.0, 1.0);
    float height_mask = (1.0 - pow(h_norm, 1.5)) * step(u_y_offset, gy);

    // Width mask — bell-curve (fire) or teardrop (candle)
    float dx = abs(gx - 0.5) * 2.0;
    // Bell curve: same width from base to tip
    float bell    = clamp(1.0 - pow(dx / u_width, 2.3), 0.0, 1.0);
    // Teardrop: narrow at base, widens at 1/3 height, tapers to point at tip
    //   profile: sin(π * h) gives 0 at base and tip, max at middle
    //   power 0.4 biases the peak downward (flame wider at lower third)
    float h_td    = pow(h_norm, 0.4);
    float td_w    = sin(clamp(h_td * 3.14159, 0.0, 3.14159)) * u_width * 1.4;
    float teardrop = clamp(1.0 - pow(dx / max(td_w, 0.001), 2.0), 0.0, 1.0);
    float width_mask = mix(bell, teardrop, u_teardrop);

    float intensity = clamp(f * height_mask * width_mask * 2.1 * u_brightness - 0.12, 0.0, 1.0);

    vec3 col = fire_color(intensity);

    // Ember glow at the flame base
    float ember = clamp(1.0 - local_y / 0.10, 0.0, 1.0) * width_mask * step(u_y_offset - 0.01, gy);
    col = max(col, u_col_base * ember * 0.65);

    // Background + halo (follows flame base, not video bottom)
    float halo = smoothstep(0.20, 0.0, local_y) * width_mask * step(u_y_offset - 0.01, gy) * 0.15;
    vec3 final_col = u_bg + u_col_mid * halo;
    final_col = max(final_col, col);

    // Sparks — rise above flame tip (skip for candle, u_teardrop=1 reduces sparks)
    float spark_count = mix(6.0, 1.0, u_teardrop);
    for (int i = 0; i < 6; i++) {
        if (float(i) >= spark_count) break;
        float si       = float(i);
        float tick     = floor(t * 18.0);
        float life_off = hash3(vec3(si, tick, 0.0));
        float life     = fract(t * (0.35 + hash3(vec3(si, tick, 1.0)) * 0.5) + life_off);
        float sx       = hash3(vec3(si, tick, 2.0));
        float sdx      = (hash3(vec3(si, tick, 3.0)) - 0.5) * 0.2 * life;
        // Sparks rise from tip upward
        float sy = u_y_offset + u_height + life * u_height * 0.9;
        float dist  = length(vec2(gx - sx - sdx, gy - sy));
        float spark = smoothstep(0.007, 0.001, dist);
        spark *= (1.0 - life);
        final_col = max(final_col, vec3(1.0, 0.85, 0.35) * spark);
    }

    fragColor = vec4(clamp(final_col, 0.0, 1.0), 1.0);
}
"""


# ── Fire presets ──────────────────────────────────────────────────────────────

PRESETS = {
    'fireplace': {
        'name':       'Cozy Fireplace',
        'speed':      0.75,
        'turbulence': 1.80,
        'scale':      3.20,
        'height':     0.72,
        'width':      1.30,
        'brightness': 1.00,
        'y_offset':   0.00,   # starts at the bottom
        'teardrop':   0.00,   # bell curve
        'col_base':   (0.90, 0.10, 0.00),
        'col_mid':    (0.98, 0.42, 0.02),
        'col_core':   (1.00, 0.92, 0.35),
        'bg':         (0.03, 0.01, 0.00),
    },
    'campfire': {
        'name':       'Campfire Night',
        'speed':      1.10,
        'turbulence': 2.40,
        'scale':      2.70,
        'height':     0.88,
        'width':      0.85,
        'brightness': 1.05,
        'y_offset':   0.00,
        'teardrop':   0.00,
        'col_base':   (0.85, 0.12, 0.00),
        'col_mid':    (1.00, 0.48, 0.04),
        'col_core':   (1.00, 0.95, 0.55),
        'bg':         (0.01, 0.01, 0.02),
    },
    'candle': {
        'name':       'Candlelight',
        'speed':      0.30,   # very gentle flicker
        'turbulence': 0.90,   # minimal turbulence
        'scale':      5.50,   # fine detail
        'height':     0.42,   # flame height: 42% of frame from base
        'width':      0.22,   # narrow teardrop width
        'brightness': 1.05,
        'y_offset':   0.08,   # flame base 8% up from bottom (above notional wick)
        'teardrop':   1.00,   # teardrop shape (classic candle flame)
        'col_base':   (0.80, 0.08, 0.00),   # deep red-orange
        'col_mid':    (1.00, 0.65, 0.12),   # warm golden orange
        'col_core':   (1.00, 0.97, 0.75),   # pale warm white at core
        'bg':         (0.015, 0.008, 0.008),
    },
    'fire_closeup': {
        'name':       'Sacred Fire — Close Up',
        'speed':      1.45,
        'turbulence': 3.20,
        'scale':      1.90,
        'height':     2.00,
        'width':      2.00,
        'brightness': 1.10,
        'y_offset':   0.00,
        'teardrop':   0.00,
        'col_base':   (0.65, 0.00, 0.00),
        'col_mid':    (1.00, 0.28, 0.00),
        'col_core':   (1.00, 0.78, 0.10),
        'bg':         (0.06, 0.00, 0.00),
    },
}


# ── Renderer ──────────────────────────────────────────────────────────────────

def render_fire(preset_key: str, out_path: Path,
                duration: float = LOOP_DUR, fps: int = FPS,
                width: int = W, height: int = H) -> bool:
    preset = PRESETS[preset_key]
    total_frames = int(duration * fps)
    log.info(f"  Rendering '{preset['name']}' — {total_frames} frames @ {fps}fps "
             f"({duration}s, {width}×{height})")

    try:
        ctx = moderngl.create_standalone_context(backend='egl')
    except Exception as e:
        log.error(f"  Failed to create OpenGL context: {e}")
        return False

    try:
        prog = ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
        fbo  = ctx.simple_framebuffer((width, height))
        fbo.use()

        verts = np.array([[-1.0,-1.0], [1.0,-1.0], [-1.0, 1.0], [1.0, 1.0]], dtype='f4')
        vao   = ctx.simple_vertex_array(prog, ctx.buffer(verts.tobytes()), 'in_vert')

        # Set static uniforms
        prog['u_speed'].value       = preset['speed']
        prog['u_turbulence'].value  = preset['turbulence']
        prog['u_scale'].value       = preset['scale']
        prog['u_height'].value      = preset['height']
        prog['u_width'].value       = preset['width']
        prog['u_brightness'].value  = preset['brightness']
        prog['u_y_offset'].value    = preset.get('y_offset', 0.0)
        prog['u_teardrop'].value    = preset.get('teardrop', 0.0)
        prog['u_col_base'].value    = preset['col_base']
        prog['u_col_mid'].value     = preset['col_mid']
        prog['u_col_core'].value    = preset['col_core']
        prog['u_bg'].value          = preset['bg']

        # Pipe raw RGB frames directly to FFmpeg
        ffcmd = [
            'ffmpeg', '-y',
            '-f', 'rawvideo', '-vcodec', 'rawvideo',
            '-s', f'{width}x{height}', '-pix_fmt', 'rgb24', '-r', str(fps),
            '-i', 'pipe:0',
            '-vf', f'vflip',          # OpenGL is bottom-up
            '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
            '-pix_fmt', 'yuv420p', '-an', str(out_path)
        ]
        ff = subprocess.Popen(ffcmd, stdin=subprocess.PIPE,
                              stderr=subprocess.DEVNULL)

        t_start = time.time()
        for i in range(total_frames):
            prog['u_time'].value = i / fps
            vao.render(moderngl.TRIANGLE_STRIP)
            frame_data = fbo.read(components=3)
            ff.stdin.write(frame_data)

            if i % 90 == 0 and i > 0:
                elapsed = time.time() - t_start
                remaining = (total_frames - i) * elapsed / i
                log.info(f"    frame {i}/{total_frames} "
                         f"({elapsed:.0f}s elapsed, ~{remaining:.0f}s left)")

        ff.stdin.close()
        ff.wait()
        ctx.release()

        if out_path.exists() and out_path.stat().st_size > 10_000:
            sz = out_path.stat().st_size // 1024
            elapsed = time.time() - t_start
            log.info(f"  Done: {out_path.name} ({sz}KB, {elapsed:.0f}s)")
            return True
        else:
            log.error(f"  Output missing or too small: {out_path}")
            return False

    except Exception as e:
        log.error(f"  Render error: {e}")
        try:
            ctx.release()
        except Exception:
            pass
        return False


# ── Build helpers (for --build mode) ─────────────────────────────────────────

def get_duration(path: Path) -> float:
    import json
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
        capture_output=True)
    try:
        return float(json.loads(r.stdout)['format']['duration'])
    except Exception:
        return 0.0


def find_audio(kw_list: list[str]) -> Path | None:
    if not AUDIO_DIR.exists():
        return None
    for kw in kw_list:
        matches = [f for f in AUDIO_DIR.glob('*.mp3') if kw.lower() in f.name.lower()]
        if matches:
            base = [m for m in matches if '(' not in m.name]
            return (base or matches)[0]
    return None


def build_long_video_silent(loop_path: Path, audio_path: Path | None,
                             out_mp4: Path, target_dur: int = TARGET_DUR) -> bool:
    """Build 1h video from a loop (shader loops have no natural audio)."""
    import shutil, json
    loop_dur = get_duration(loop_path)
    loops_needed = int(target_dur / loop_dur) + 2

    tmp = out_mp4.parent / '_shader_tmp'
    tmp.mkdir(exist_ok=True)
    concat_f = tmp / 'concat_v.txt'
    loop_mp4  = tmp / 'loop.mp4'

    try:
        concat_f.write_text(''.join(f"file '{loop_path.resolve()}'\n" for _ in range(loops_needed)))
        r = subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(concat_f), '-t', str(target_dur + 2), '-c', 'copy', str(loop_mp4)
        ], capture_output=True, timeout=300)
        if r.returncode != 0:
            log.error(f"  Loop concat failed: {r.stderr[-200:]}")
            return False

        fade_start = max(0, target_dur - 3)

        if audio_path and audio_path.exists():
            audio_dur = get_duration(audio_path)
            audio_loops = int(target_dur / audio_dur) + 2
            concat_a = tmp / 'concat_a.txt'
            concat_a.write_text(''.join(f"file '{audio_path.resolve()}'\n" for _ in range(audio_loops)))
            loop_audio = tmp / 'audio_loop.mp3'
            subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_a),
                '-t', str(target_dur + 2), '-ar', '44100', '-ac', '2',
                '-c:a', 'libmp3lame', '-b:a', '192k', str(loop_audio)
            ], capture_output=True, timeout=300)
            cmd = [
                'ffmpeg', '-y',
                '-i', str(loop_mp4), '-i', str(loop_audio),
                '-map', '0:v:0', '-map', '1:a:0',
                '-vf', f'fade=t=out:st={fade_start}:d=3',
                '-af', f'afade=t=out:st={fade_start}:d=3',
                '-t', str(target_dur),
                '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p', str(out_mp4)
            ]
        else:
            log.warning("  No audio — video will be silent")
            cmd = [
                'ffmpeg', '-y', '-i', str(loop_mp4), '-map', '0:v:0',
                '-vf', f'fade=t=out:st={fade_start}:d=3',
                '-t', str(target_dur),
                '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
                '-pix_fmt', 'yuv420p', '-an', str(out_mp4)
            ]

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if r.returncode != 0:
            log.error(f"  Final mix failed: {r.stderr[-300:]}")
            return False
        log.info(f"  Video: {out_mp4.name} ({out_mp4.stat().st_size//1024//1024}MB)")
        return True
    finally:
        import shutil as _s
        _s.rmtree(tmp, ignore_errors=True)


def make_thumbnail(loop_path: Path, out_path: Path) -> bool:
    dur = get_duration(loop_path)
    r = subprocess.run([
        'ffmpeg', '-y', '-ss', str(dur / 2), '-i', str(loop_path),
        '-vframes', '1', '-s', '1280x720', str(out_path)
    ], capture_output=True, timeout=30)
    return r.returncode == 0 and out_path.exists()


# Audio keywords per fire type (mirrors AMBIENT_TYPES in generate_ambient_video.py)
FIRE_AUDIO = {
    'fireplace':   ['amber fireplace', 'crackling fireplace', 'winter fireplace', 'candlelight hour'],
    'campfire':    ['sunset beach campfire', 'summer night crickets', 'crackling fireplace'],
    'candle':      ['candlelight hour', 'soft piano stillness', 'quiet library meditation'],
    'fire_closeup':['deep drone sanctuary', 'deep ambient drone', 'velvet bass wash'],
}

FIRE_TAGS = {
    'fireplace':    ['fireplace', 'crackling fire', 'cozy fireplace', 'fire sounds', 'fire meditation'],
    'campfire':     ['campfire', 'campfire sounds', 'outdoor fire', 'bonfire', 'fire crackling'],
    'candle':       ['candle meditation', 'candlelight', 'candle flame', 'meditation candle'],
    'fire_closeup': ['fire flames', 'burning fire', 'abstract fire', 'fire meditation', 'flames'],
}


def build_fire_video(key: str, loop_path: Path, force: bool = False) -> bool:
    preset = PRESETS[key]
    out_stem  = f"ambient_shader_{key}_{DATE_STR}"
    out_mp4   = QUEUE_DIR / f"{out_stem}.mp4"
    out_meta  = QUEUE_DIR / f"meta_{out_stem}.yaml"
    out_thumb = QUEUE_DIR / f"thumb_{out_stem}.png"

    if out_mp4.exists() and not force:
        log.info(f"  {out_mp4.name} exists — skip (--force to redo)")
        return True

    audio_kws  = FIRE_AUDIO.get(key, [])
    audio_path = find_audio(audio_kws)
    audio_name = audio_path.stem if audio_path else 'Silent'
    log.info(f"  Audio: {audio_name}")

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    log.info(f"  Building {TARGET_DUR//3600}h video...")
    if not build_long_video_silent(loop_path, audio_path, out_mp4, TARGET_DUR):
        return False

    make_thumbnail(loop_path, out_thumb)

    meta_cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    h = TARGET_DUR // 3600
    title = f"{preset['name']} — {h} Hour Procedural | Fire Ambience | Sacred Drift"
    footer = meta_cfg.get('video_defaults', {}).get('description_footer', '')
    description = f"""{preset['name']}

{h} hour of continuous procedural fire animation — generated through GLSL shader rendering for an organic, mathematically pure fire experience. Perfect for deep focus, meditation, sleep and relaxation.

✨ Best experienced on a large screen or TV for full immersion.
🎧 Pair with headphones for the ultimate ambient experience.
🔁 Animation loops seamlessly — ideal for all-night background ambience.

━━━━━━━━━━━━━━━━━━━━━━━
About Sacred Drift:
Sacred Drift is a sanctuary of sound and vision — ambient nature, fire, water and healing soundscapes for deep rest and inner peace.

Subscribe 🔮 @SacredDrift
━━━━━━━━━━━━━━━━━━━━━━━

🎨 Visuals: original procedural GLSL shader animation (© Sacred Drift 2026)
🎵 Audio: {audio_name} (AI-generated, © Sacred Drift 2026)

{footer}"""

    base_tags  = meta_cfg.get('video_defaults', {}).get('tags_base', [])
    type_tags  = FIRE_TAGS.get(key, [])
    all_tags   = type_tags + ['procedural fire', 'shader art', 'generative art',
                               'fire ambience', 'sacred drift'] + base_tags
    seen, tags, total = set(), [], 0
    for t in all_tags:
        if t and t not in seen and len(t) <= 30 and len(tags) < 30 and total + len(t) <= 500:
            seen.add(t); tags.append(t); total += len(t)

    meta_doc = {
        'title':         title,
        'description':   description,
        'tags':          tags,
        'video_type':    'ambient_video',
        'ambient_type':  f'shader_{key}',
        'ambient_group': 'fire_shader',
        'language':      'en',
        'is_short':      False,
        'status':        'public',
        'made_for_kids': False,
        'ai_generated':  True,
        'duration_sec':  TARGET_DUR,
    }
    out_meta.write_text(yaml.dump(meta_doc, allow_unicode=True, default_flow_style=False))
    log.info(f"  Meta: {out_meta.name}")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Generate procedural fire video loops via GLSL shader')
    parser.add_argument('--list',    action='store_true', help='Show available presets')
    parser.add_argument('--type',    choices=list(PRESETS.keys()), help='Render one preset')
    parser.add_argument('--all',     action='store_true', help='Render all presets')
    parser.add_argument('--preview', action='store_true', help='Render 3s preview only')
    parser.add_argument('--build',   action='store_true', help='After rendering loop, also build 1h video + meta')
    parser.add_argument('--force',   action='store_true', help='Overwrite existing loops and videos')
    args = parser.parse_args()

    if args.list:
        print(f"\n  {'Key':<16} {'Name':<28} Loop  Video")
        print('  ' + '-' * 65)
        for k, v in PRESETS.items():
            loop  = LOOPS_DIR / f'loop_shader_{k}.mp4'
            video = QUEUE_DIR  / f'ambient_shader_{k}_{DATE_STR}.mp4'
            lm = '✓' if loop.exists()  else ' '
            vm = '✓' if video.exists() else ' '
            print(f"  [{lm}] {k:<14} {v['name']:<28}  [{vm}]")
        print()
        return

    LOOPS_DIR.mkdir(parents=True, exist_ok=True)

    if args.type:
        keys = [args.type]
    elif args.all:
        keys = list(PRESETS.keys())
    else:
        parser.print_help()
        return

    duration = 3.0 if args.preview else float(LOOP_DUR)
    ok = fail = 0

    for key in keys:
        log.info(f"\n{'='*60}")
        log.info(f"Fire preset: {key}")

        suffix   = '_preview' if args.preview else ''
        loop_name = f'loop_shader_{key}{suffix}.mp4'
        loop_path = LOOPS_DIR / loop_name

        if loop_path.exists() and not args.force and not args.preview:
            log.info(f"  Loop exists — skip render (--force to redo)")
        else:
            if not render_fire(key, loop_path, duration=duration):
                fail += 1
                continue

        if args.build and not args.preview:
            if not build_fire_video(key, loop_path, force=args.force):
                fail += 1
                continue

        ok += 1

    log.info(f'\nDone: {ok} OK, {fail} failed')
    if ok and not args.preview:
        log.info(f'Shader loops → {LOOPS_DIR}/')
        if args.build:
            log.info(f'Videos → {QUEUE_DIR}/')


if __name__ == '__main__':
    main()
