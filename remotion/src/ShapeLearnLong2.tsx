/**
 * ShapeLearnLong2 — 30-min "One Concept Deep" shape learning, v2.
 * 1920×1080 landscape. No text — universal (EN + AR + ID).
 *
 * Improvements over v1:
 * - 3D PNG sprites (FLUX-generated) instead of CSS flat shapes
 * - DVD screensaver bounce (shape travels entire screen) in SOLO section
 * - Fly-in from screen edges in COUNT section (1→2→3→4→5)
 * - Wobble (PIP/BWW) applied to every sprite
 * - CSS hue-rotate for COLOR section rainbow cycling
 * - All objects float independently (phase-offset per index)
 * - Large sprite sizes (600-660px main, 200-300px secondary)
 * - Idle animation always active (never conditional)
 *
 * Section timing (1800s total):
 *   INTRO      0–30s    : drop-in from top with spring, glow pulse
 *   SOLO       30–330s  : 1 shape, DVD screensaver bounce (5 min)
 *   DUO        330–570s : 2 shapes, opposite-phase DRIFT (4 min)
 *   TRIO       570–810s : 3 shapes, ORBIT around center (4 min)
 *   COLOR      810–1050s: 1 shape hue-rotating rainbow + 2 companions (4 min)
 *   COUNT      1050–1380s: fly-in from edges, 1→2→3→4→5 (5.5 min)
 *   COUNT_ALL  1380–1500s: all 5, varied independent motions (2 min)
 *   HYPNO      1500–1770s: 15 mini shapes, hue drift (4.5 min)
 *   OUTRO      1770–1800s: fade out (30s)
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ShapeLearnLong2Props {
  spritePath: string;    // e.g. "shapes_3d/circle.png" (relative to remotion/public/sprites/)
  shapeColor: string;    // canonical hex for backgrounds / watermark
  bgColor: string;       // main background colour
  bgColorEnd?: string;   // optional: lerp bg toward this over video
  musicFile: string;
  musicFile2?: string;   // second track — crossfades in at 15 min
  accentColor?: string;  // bubble colour (default white)
}

// ── Constants ─────────────────────────────────────────────────────────────────

const FPS = 30;
const W = 1920;
const H = 1080;

const S = {
  INTRO:     0,
  SOLO:      30,
  DUO:       330,
  TRIO:      570,
  COLOR:     810,
  COUNT:     1050,
  COUNT_ALL: 1380,
  HYPNO:     1500,
  OUTRO:     1770,
  END:       1800,
} as const;

// Stable target positions for the 5 shapes in COUNT section
const COUNT_TARGETS = [
  { x: 0.26, y: 0.36 },
  { x: 0.74, y: 0.36 },
  { x: 0.50, y: 0.60 },
  { x: 0.19, y: 0.74 },
  { x: 0.81, y: 0.74 },
] as const;

const COUNT_INTERVAL = 60;  // seconds between each new shape appearing
const FLY_DUR = 2.5;        // seconds to fly from edge to target

// ── Utilities ─────────────────────────────────────────────────────────────────

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// Triangle wave 0→1→0 (for DVD screensaver bounce)
function triWave(t: number): number {
  const p = ((t % 1) + 1) % 1;
  return p < 0.5 ? p * 2 : (1 - p) * 2;
}

// easeOutBack: slight overshoot, good for fly-in landing
function easeOutBack(t: number): number {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  const clamped = Math.min(1, Math.max(0, t));
  return 1 + c3 * Math.pow(clamped - 1, 3) + c1 * Math.pow(clamped - 1, 2);
}

// Linear interpolate between two hex colours
function lerpHex(a: string, b: string, t: number): string {
  const p = (h: string, s: number) => parseInt(h.slice(s, s + 2), 16);
  const mix = (ca: number, cb: number) =>
    Math.round(ca + (cb - ca) * t).toString(16).padStart(2, "0");
  return `#${mix(p(a,1),p(b,1))}${mix(p(a,3),p(b,3))}${mix(p(a,5),p(b,5))}`;
}

// Wobble (PIP/BWW): multi-frequency outline breathing per sprite seed
function applyWobble(
  t: number, s: number,
  cx: number, cy: number,
  scaleX: number, scaleY: number,
  rotation: number,
) {
  return {
    cx:       cx + Math.sin(t * (9.1 + s * 0.8)) * 2.8,
    cy:       cy + Math.cos(t * (7.3 + s * 0.6)) * 2.8,
    scaleX:   scaleX * (1 + Math.sin(t * (8.3 + s * 0.7)) * 0.038 + Math.sin(t * (5.1 + s * 0.4)) * 0.020),
    scaleY:   scaleY * (1 + Math.sin(t * (7.7 + s * 0.9)) * 0.038 + Math.cos(t * (4.2 + s * 1.1)) * 0.020),
    rotation: rotation + Math.sin(t * (6.5 + s * 0.5)) * 1.4,
  };
}

// ── Single sprite renderer ────────────────────────────────────────────────────

const Sprite: React.FC<{
  path: string;
  size: number;
  cx: number;
  cy: number;
  rotation?: number;
  scaleX?: number;
  scaleY?: number;
  opacity?: number;
  hueRotate?: number;
  seed?: number;
  fSec: number;
}> = ({
  path, size, cx, cy, rotation = 0, scaleX = 1, scaleY = 1,
  opacity = 1, hueRotate = 0, seed = 1, fSec,
}) => {
  const w = applyWobble(fSec, seed, cx, cy, scaleX, scaleY, rotation);
  return (
    <div style={{
      position: "absolute",
      left: w.cx - size / 2,
      top:  w.cy - size / 2,
      width: size,
      height: size,
      opacity,
      transform: `scaleX(${w.scaleX}) scaleY(${w.scaleY}) rotate(${w.rotation}deg)`,
      transformOrigin: "center center",
      filter: [
        `hue-rotate(${hueRotate}deg)`,
        "saturate(1.35)",
        "brightness(1.05)",
        "drop-shadow(0 10px 22px rgba(0,0,0,0.28))",
      ].join(" "),
    }}>
      <Img
        src={staticFile(`sprites/${path}`)}
        style={{ width: size, height: size, objectFit: "contain" }}
      />
    </div>
  );
};

// ── Background floating bubbles ───────────────────────────────────────────────

const Bubbles: React.FC<{ color: string; fSec: number }> = ({ color, fSec }) => (
  <>
    {Array.from({ length: 14 }, (_, i) => {
      const r = seededRand;
      const size  = 18 + r(i * 3 + 1) * 72;
      const baseX = r(i * 7 + 2) * (W - size);
      const baseY = r(i * 11 + 3) * (H - size);
      const spd   = 0.2 + r(i * 13 + 4) * 0.3;
      const op    = 0.05 + r(i * 5 + 5) * 0.07;
      return (
        <div key={i} style={{
          position: "absolute",
          left: baseX + Math.sin((fSec / 3) * spd + i) * 24,
          top:  baseY + Math.cos((fSec / 3.7) * spd + i * 2) * 18,
          width: size, height: size,
          borderRadius: "50%",
          backgroundColor: color,
          opacity: op,
        }} />
      );
    })}
  </>
);

// ── INTRO ─────────────────────────────────────────────────────────────────────

const IntroSection: React.FC<{
  path: string; bg: string; accent: string; frame: number; fSec: number;
}> = ({ path, bg, accent, frame, fSec }) => {
  const dropSpring = spring({
    frame: frame - S.INTRO * FPS,
    fps: FPS,
    config: { damping: 8, stiffness: 80 },
    durationInFrames: FPS * 2,
  });
  const cy = interpolate(dropSpring, [0, 1], [-400, H / 2]);
  const localF = frame - S.INTRO * FPS;
  const glowT = interpolate(localF, [FPS * 1.5, FPS * 2.5, FPS * 4.5], [0, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <Bubbles color={accent} fSec={fSec} />
      <Sprite
        path={path} size={640} cx={W / 2} cy={cy}
        hueRotate={0} seed={1} fSec={fSec}
        scaleX={1} scaleY={1} opacity={1}
      />
      {/* Glow ring */}
      {glowT > 0.01 && (
        <div style={{
          position: "absolute",
          left: W / 2 - 380, top: cy - 380,
          width: 760, height: 760,
          borderRadius: "50%",
          border: `12px solid rgba(255,255,255,${glowT * 0.6})`,
          boxShadow: `0 0 ${80 * glowT}px rgba(255,255,255,${glowT * 0.5})`,
          pointerEvents: "none",
        }} />
      )}
    </AbsoluteFill>
  );
};

// ── SOLO: DVD screensaver bounce ──────────────────────────────────────────────

const SoloSection: React.FC<{
  path: string; bg: string; accent: string; fSec: number;
}> = ({ path, bg, accent, fSec }) => {
  const t = fSec - S.SOLO;
  const SIZE = 640;
  const pad = SIZE / 2 + 30;

  // Two independent triangle waves → Lissajous-like coverage of whole screen
  const cx = pad + triWave(t / (7.3 * 2)) * (W - pad * 2);
  const cy = pad + triWave(t / (5.1 * 2)) * (H - pad * 2);

  // Continuous hue shift — full rainbow over section (5 min)
  const hue = (t / (S.DUO - S.SOLO)) * 720 % 360;

  // Idle pulse on top of position
  const pulse = 1 + Math.sin(fSec * 1.4) * 0.06;

  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <Bubbles color={accent} fSec={fSec} />
      <Sprite path={path} size={SIZE} cx={cx} cy={cy} hueRotate={hue}
        scaleX={pulse} scaleY={pulse} seed={2} fSec={fSec} />
    </AbsoluteFill>
  );
};

// ── DUO: 2 shapes, opposite DRIFT phases ─────────────────────────────────────

const DuoSection: React.FC<{
  path: string; bg: string; accent: string; fSec: number;
}> = ({ path, bg, accent, fSec }) => {
  const t = fSec - S.DUO;

  const items = [
    { cx: W * 0.28, cy: H * 0.40, size: 560, seed: 3, hueOff: 0   },
    { cx: W * 0.72, cy: H * 0.55, size: 420, seed: 4, hueOff: 180 },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <Bubbles color={accent} fSec={fSec} />
      {items.map((s, i) => {
        const phase = i * Math.PI;
        const cx = s.cx + Math.sin(t * 0.55 + phase) * 220;
        const cy = s.cy + Math.cos(t * 0.42 + phase + 1.3) * 140;
        const rot = Math.sin(t * 0.28 + i) * 14;
        const hue = (t * 7 + s.hueOff) % 360;
        return (
          <Sprite key={i} path={path} size={s.size} cx={cx} cy={cy}
            rotation={rot} hueRotate={hue} seed={s.seed} fSec={fSec} />
        );
      })}
    </AbsoluteFill>
  );
};

// ── TRIO: 3 shapes orbiting center ───────────────────────────────────────────

const TrioSection: React.FC<{
  path: string; bg: string; accent: string; fSec: number;
}> = ({ path, bg, accent, fSec }) => {
  const t = fSec - S.TRIO;
  const ocx = W * 0.5;
  const ocy = H * 0.46;

  const items = [
    { size: 480, orbitR: 300, period: 12.0, offsetAngle: 0,               seed: 5 },
    { size: 360, orbitR: 240, period: 10.0, offsetAngle: (Math.PI * 2/3), seed: 6 },
    { size: 280, orbitR: 180, period:  8.5, offsetAngle: (Math.PI * 4/3), seed: 7 },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <Bubbles color={accent} fSec={fSec} />
      {items.map((s, i) => {
        const angle = (t / s.period) * Math.PI * 2 + s.offsetAngle;
        const cx = ocx + Math.cos(angle) * s.orbitR;
        const cy = ocy + Math.sin(angle) * s.orbitR * 0.55;
        const hue = (t * 5 + i * 120) % 360;
        return (
          <Sprite key={i} path={path} size={s.size} cx={cx} cy={cy}
            hueRotate={hue} seed={s.seed} fSec={fSec} />
        );
      })}
    </AbsoluteFill>
  );
};

// ── COLOR: hue-rotate rainbow ─────────────────────────────────────────────────

const ColorSection: React.FC<{
  path: string; bg: string; accent: string; fSec: number;
}> = ({ path, bg, accent, fSec }) => {
  const t = fSec - S.COLOR;
  const dur = S.COUNT - S.COLOR;
  const progress = t / dur;

  // Main shape: 1.5 full rainbow rotations across section
  const hue = (progress * 540) % 360;

  // Complementary soft background
  const bgLum = 0.88 + 0.05 * Math.sin(progress * Math.PI * 4);
  const dynBg = `hsl(${(hue + 180) % 360}, 28%, ${Math.round(bgLum * 100)}%)`;

  // Main: slow breathing
  const pulse = 1 + Math.sin(t * 1.1) * 0.08;

  // Companions: smaller, offset hues, independent float
  const companions = [
    { cx: W * 0.20, cy: H * 0.33, size: 280, seed: 8,  hueOff: 60  },
    { cx: W * 0.80, cy: H * 0.64, size: 240, seed: 9,  hueOff: 120 },
    { cx: W * 0.50, cy: H * 0.82, size: 200, seed: 10, hueOff: 240 },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: dynBg }}>
      <Bubbles color={accent} fSec={fSec} />
      {/* Main large shape */}
      <Sprite path={path} size={640} cx={W / 2} cy={H / 2}
        hueRotate={hue} scaleX={pulse} scaleY={pulse} seed={11} fSec={fSec} />
      {/* Companions */}
      {companions.map((c, i) => {
        const cx = c.cx + Math.sin(t * 0.52 + i * 2.1) * 70;
        const cy = c.cy + Math.cos(t * 0.40 + i * 1.7) * 50;
        const sc = 1 + Math.sin(t * 0.9 + i * 0.8) * 0.07;
        return (
          <Sprite key={i} path={path} size={c.size} cx={cx} cy={cy}
            hueRotate={(hue + c.hueOff) % 360}
            scaleX={sc} scaleY={sc} opacity={0.75}
            seed={c.seed} fSec={fSec} />
        );
      })}
    </AbsoluteFill>
  );
};

// ── COUNT: fly-in 1→2→3→4→5 ──────────────────────────────────────────────────

function getCountPos(idx: number, fSec: number) {
  const appearSec = S.COUNT + idx * COUNT_INTERVAL;
  if (fSec < appearSec) return null;

  const elapsed = fSec - appearSec;
  const flyT = Math.min(1, elapsed / FLY_DUR);
  const eased = easeOutBack(flyT);

  // Entry edge (seed-deterministic): 0=top, 1=right, 2=bottom, 3=left
  const edge = Math.floor(seededRand(idx * 7 + 11) * 4);
  const edgePos = seededRand(idx * 13 + 17);
  let sx: number, sy: number;
  if      (edge === 0) { sx = edgePos * W; sy = -260; }
  else if (edge === 1) { sx = W + 260;    sy = edgePos * H; }
  else if (edge === 2) { sx = edgePos * W; sy = H + 260; }
  else                  { sx = -260;       sy = edgePos * H; }

  const tx = COUNT_TARGETS[idx].x * W;
  const ty = COUNT_TARGETS[idx].y * H;

  // After landing, gradually apply DRIFT
  const afterLand = Math.max(0, elapsed - FLY_DUR);
  const driftBlend = Math.min(1, afterLand / 2.5);
  const driftX = Math.sin(afterLand * 0.62 + idx * 2.1) * 60 * driftBlend;
  const driftY = Math.cos(afterLand * 0.48 + idx * 1.7) * 45 * driftBlend;

  return {
    cx: sx + (tx - sx) * eased + driftX,
    cy: sy + (ty - sy) * eased + driftY,
    opacity: Math.min(1, flyT * 4),
  };
}

const SHAPE_SIZES_5 = [560, 480, 420, 370, 320] as const;

const CountSection: React.FC<{
  path: string; bg: string; accent: string; fSec: number;
}> = ({ path, bg, accent, fSec }) => (
  <AbsoluteFill style={{ backgroundColor: bg }}>
    <Bubbles color={accent} fSec={fSec} />
    {COUNT_TARGETS.map((_, i) => {
      const pos = getCountPos(i, fSec);
      if (!pos) return null;
      const hue = i * 72;  // 5 shapes × 72° = evenly spread rainbow
      return (
        <Sprite key={i} path={path} size={SHAPE_SIZES_5[i]}
          cx={pos.cx} cy={pos.cy}
          hueRotate={hue} opacity={pos.opacity}
          seed={12 + i} fSec={fSec} />
      );
    })}
  </AbsoluteFill>
);

// ── COUNT_ALL: all 5 with varied independent motions ─────────────────────────

const CountAllSection: React.FC<{
  path: string; bg: string; accent: string; fSec: number;
}> = ({ path, bg, accent, fSec }) => {
  const t = fSec - S.COUNT_ALL;

  // Each shape has its own orbit / drift parameters
  const motions = [
    { bx: W * 0.26, by: H * 0.36, ax: 140, ay: 100, px: 1.25, py: 0.95, phX: 0,   phY: 0.5  },
    { bx: W * 0.74, by: H * 0.36, ax: 120, ay:  90, px: 1.05, py: 1.10, phX: 1.2, phY: 0.8  },
    { bx: W * 0.50, by: H * 0.60, ax: 160, ay:  80, px: 0.90, py: 1.20, phX: 2.4, phY: 1.6  },
    { bx: W * 0.19, by: H * 0.74, ax:  90, ay:  70, px: 1.40, py: 0.85, phX: 3.6, phY: 2.4  },
    { bx: W * 0.81, by: H * 0.74, ax: 100, ay:  75, px: 1.15, py: 1.05, phX: 4.8, phY: 3.2  },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: bg }}>
      <Bubbles color={accent} fSec={fSec} />
      {motions.map((m, i) => {
        const cx = m.bx + Math.sin(t * m.px + m.phX) * m.ax;
        const cy = m.by + Math.cos(t * m.py + m.phY) * m.ay;
        const hue = (t * 4 + i * 72) % 360;
        const sc  = 1 + Math.sin(t * 0.8 + i * 1.3) * 0.07;
        return (
          <Sprite key={i} path={path} size={SHAPE_SIZES_5[i]}
            cx={cx} cy={cy}
            hueRotate={hue} scaleX={sc} scaleY={sc}
            seed={17 + i} fSec={fSec} />
        );
      })}
    </AbsoluteFill>
  );
};

// ── HYPNO: 15 mini shapes floating, hue drift ─────────────────────────────────

const HypnoSection: React.FC<{
  path: string; bg: string; fSec: number; frame: number;
}> = ({ path, bg, fSec, frame }) => {
  const t = fSec - S.HYPNO;
  const fadeIn = interpolate(frame, [S.HYPNO * FPS, S.HYPNO * FPS + FPS * 3], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const COUNT = 15;
  return (
    <AbsoluteFill style={{ backgroundColor: bg, opacity: fadeIn }}>
      {Array.from({ length: COUNT }, (_, i) => {
        const r = seededRand;
        const size    = 80 + r(i * 7 + 30) * 220;
        const baseX   = r(i * 11 + 31) * (W - size) + size / 2;
        const baseY   = r(i * 13 + 32) * (H - size) + size / 2;
        const speed   = 60 + r(i * 17 + 33) * 130;
        const hueOff  = r(i * 19 + 34) * 360;
        const opacity = 0.30 + r(i * 5 + 35) * 0.55;

        const hue = ((t * 4) + hueOff) % 360;
        const cx  = baseX + Math.sin((t / speed * Math.PI * 2) + i) * 90;
        const cy  = baseY + Math.cos((t / speed * Math.PI * 2 * 0.8) + i * 2) * 65;
        const sc  = 1 + Math.sin(t * 0.55 + i) * 0.12;

        return (
          <Sprite key={i} path={path} size={size} cx={cx} cy={cy}
            hueRotate={hue} opacity={opacity}
            scaleX={sc} scaleY={sc}
            seed={22 + i} fSec={fSec} />
        );
      })}
    </AbsoluteFill>
  );
};

// ── OUTRO ─────────────────────────────────────────────────────────────────────

const OutroSection: React.FC<{
  path: string; bg: string; fSec: number;
}> = ({ path, bg, fSec }) => {
  const t = fSec - S.OUTRO;
  const dur = S.END - S.OUTRO;
  const fadeOut = interpolate(t, [0, dur * 0.6, dur], [1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const pulse = 1 + Math.sin(fSec * 1.3) * 0.06;

  return (
    <AbsoluteFill style={{ backgroundColor: bg, opacity: fadeOut }}>
      <Sprite path={path} size={640} cx={W / 2} cy={H / 2}
        scaleX={pulse} scaleY={pulse} seed={37} fSec={fSec} />
    </AbsoluteFill>
  );
};

// ── MAIN ─────────────────────────────────────────────────────────────────────

export const ShapeLearnLong2: React.FC<ShapeLearnLong2Props> = ({
  spritePath,
  shapeColor,
  bgColor,
  bgColorEnd,
  musicFile,
  musicFile2,
  accentColor = "#FFFFFF",
}) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const fSec = frame / fps;

  // Background fade
  const bgProgress = bgColorEnd
    ? interpolate(fSec, [0, S.END], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;
  const bg = bgColorEnd ? lerpHex(bgColor, bgColorEnd, bgProgress) : bgColor;

  // Global fade-out last 3s
  const fadeOut = interpolate(
    frame,
    [S.END * fps - fps * 3, S.END * fps],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // Music crossfade at 15 min
  const vol1 = musicFile2
    ? interpolate(fSec, [870, 900], [0.20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0.20;
  const vol2 = musicFile2
    ? interpolate(fSec, [870, 900], [0, 0.20], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;

  const section =
    fSec < S.SOLO      ? "intro"     :
    fSec < S.DUO       ? "solo"      :
    fSec < S.TRIO      ? "duo"       :
    fSec < S.COLOR     ? "trio"      :
    fSec < S.COUNT     ? "color"     :
    fSec < S.COUNT_ALL ? "count"     :
    fSec < S.HYPNO     ? "count_all" :
    fSec < S.OUTRO     ? "hypno"     : "outro";

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      <Audio src={staticFile(`music/${musicFile}`)} volume={vol1} loop />
      {musicFile2 && (
        <Audio src={staticFile(`music/${musicFile2}`)} volume={vol2} loop />
      )}

      {section === "intro"     && <IntroSection    path={spritePath} bg={bg} accent={accentColor} frame={frame} fSec={fSec} />}
      {section === "solo"      && <SoloSection     path={spritePath} bg={bg} accent={accentColor} fSec={fSec} />}
      {section === "duo"       && <DuoSection      path={spritePath} bg={bg} accent={accentColor} fSec={fSec} />}
      {section === "trio"      && <TrioSection     path={spritePath} bg={bg} accent={accentColor} fSec={fSec} />}
      {section === "color"     && <ColorSection    path={spritePath} bg={bg} accent={accentColor} fSec={fSec} />}
      {section === "count"     && <CountSection    path={spritePath} bg={bg} accent={accentColor} fSec={fSec} />}
      {section === "count_all" && <CountAllSection path={spritePath} bg={bg} accent={accentColor} fSec={fSec} />}
      {section === "hypno"     && <HypnoSection    path={spritePath} bg={bg} frame={frame} fSec={fSec} />}
      {section === "outro"     && <OutroSection    path={spritePath} bg={bg} fSec={fSec} />}

      {/* Subtle brand watermark */}
      <div style={{
        position: "absolute", bottom: "1.5%", right: "2%",
        opacity: 0.18, pointerEvents: "none",
        fontFamily: "Arial Black, Arial, sans-serif",
        fontSize: 30, color: shapeColor, fontWeight: 900,
        letterSpacing: 1,
      }}>
        Happy Bear Kids
      </div>
    </AbsoluteFill>
  );
};
