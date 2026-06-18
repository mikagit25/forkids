/**
 * TransformLong — 20-min "transformation" visual series.
 * Four distinct modes covering: growth, kaleidoscope, rain, day/night.
 * No text — universal (EN + AR + ID channels).
 *
 * Modes:
 *   "grow"         — seed → sprout → tree → fruit → fall cycle (repeated)
 *   "kaleidoscope" — sprites in rotating symmetric mandala pattern
 *   "rain"         — rainfall + sprites in a garden scene
 *   "day_night"    — sky gradient cycle: dawn → day → dusk → night
 */
import React, { useMemo } from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// ── Types ─────────────────────────────────────────────────────────────────────

export type TransformMode =
  | "grow"
  | "kaleidoscope"
  | "rain"
  | "day_night";

export interface TransformLongProps {
  mode: TransformMode;
  bgColor: string;               // base / dominant background
  accentColor: string;           // primary accent (fruit color, sun, etc.)
  altColor?: string;             // secondary accent (leaf color, sky tones)
  musicFile: string;
  volume?: number;
  cycleDuration?: number;        // seconds per animation cycle (default by mode)
  spritePaths?: string[];        // for kaleidoscope + rain modes (relative to public/sprites/)
  spriteSize?: number;           // px for sprites (default 200)
  seed?: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function sr(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
}

function hexToRgb(hex: string): [number, number, number] {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
}

function lerpHex(a: string, b: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(a);
  const [r2, g2, b2] = hexToRgb(b);
  return `rgb(${Math.round(lerp(r1, r2, t))},${Math.round(lerp(g1, g2, t))},${Math.round(lerp(b1, b2, t))})`;
}

// ── GROW mode ─────────────────────────────────────────────────────────────────

const Grow: React.FC<{
  fSec: number; cycleDur: number;
  width: number; height: number;
  accentColor: string; altColor: string;
}> = ({ fSec, cycleDur, width, height, accentColor, altColor }) => {
  const cx   = width  * 0.50;
  const gndY = height * 0.80;
  const maxH = height * 0.56;

  const cycleT = ((fSec % cycleDur) + cycleDur) % cycleDur / cycleDur; // 0–1
  const ct     = easeInOut(cycleT);

  // Phases (fractions of cycle)
  const seedEnd    = 0.08;
  const sproutEnd  = 0.22;
  const treeEnd    = 0.48;
  const fruitEnd   = 0.70;
  const fallEnd    = 0.86;

  const seedP    = clamp01(cycleT / seedEnd);
  const sproutP  = clamp01((cycleT - seedEnd)   / (sproutEnd - seedEnd));
  const treeP    = clamp01((cycleT - sproutEnd) / (treeEnd   - sproutEnd));
  const fruitP   = clamp01((cycleT - treeEnd)   / (fruitEnd  - treeEnd));
  const fallP    = clamp01((cycleT - fruitEnd)  / (fallEnd   - fruitEnd));
  const fadeOutP = clamp01((cycleT - fallEnd)   / (1 - fallEnd));

  const overallOp = cycleT < fallEnd ? 1 : (1 - easeInOut(fadeOutP));

  // Stem
  const stemH   = easeInOut(sproutP) * maxH;
  const trunkW  = lerp(2, 9, easeInOut(Math.min(1, treeP * 2)));

  // Branches: appear at treeP > 0.25
  const branchP = clamp01((treeP - 0.25) / 0.75);
  const bLen    = easeInOut(branchP) * maxH * 0.30;
  const bAngle  = 0.55; // radians from vertical

  // Left/right branch endpoints
  const bx = bLen * Math.sin(bAngle);
  const by = bLen * Math.cos(bAngle);
  const branchY = gndY - stemH * 0.62;

  // Leaves: at treeP > 0.55
  const leafP = clamp01((treeP - 0.55) / 0.45);
  const leafR = easeInOut(leafP) * 22;

  // Sub-branches: at treeP > 0.70
  const subP  = clamp01((treeP - 0.70) / 0.30);
  const subLen = easeInOut(subP) * bLen * 0.50;

  // Fruit
  const fruitR = easeInOut(fruitP) * 26;
  const fruitX_L = cx - bx - subLen * Math.sin(bAngle * 0.7);
  const fruitY_L = branchY - by - subLen * Math.cos(bAngle * 0.7);
  const fruitX_R = cx + bx + subLen * Math.sin(bAngle * 0.7);
  const fruitY_R = fruitY_L;

  // Fall (quadratic gravity)
  const fallDist = easeInOut(fallP) * (gndY - fruitY_L) * 1.05;
  const fruitFallY_L = fruitY_L + fallDist;
  const fruitFallY_R = fruitY_R + fallDist;

  const leafColor = altColor;
  const fruitColor = accentColor;
  const trunkColor = "#7B4F2A";
  const groundColor = "#3D6B35";

  return (
    <g opacity={overallOp}>
      {/* Ground line */}
      <line x1={0} y1={gndY} x2={width} y2={gndY} stroke={groundColor} strokeWidth={6} />

      {/* Trunk / stem */}
      {stemH > 2 && (
        <line
          x1={cx} y1={gndY}
          x2={cx} y2={gndY - stemH}
          stroke={trunkColor}
          strokeWidth={trunkW}
          strokeLinecap="round"
        />
      )}

      {/* Left branch */}
      {branchP > 0.01 && (
        <line x1={cx} y1={branchY} x2={cx - bx} y2={branchY - by}
          stroke={trunkColor} strokeWidth={4} strokeLinecap="round" />
      )}
      {/* Right branch */}
      {branchP > 0.01 && (
        <line x1={cx} y1={branchY} x2={cx + bx} y2={branchY - by}
          stroke={trunkColor} strokeWidth={4} strokeLinecap="round" />
      )}

      {/* Sub-branches */}
      {subP > 0.01 && (
        <>
          <line x1={cx - bx} y1={branchY - by}
            x2={cx - bx - subLen * Math.sin(bAngle * 0.7)}
            y2={branchY - by - subLen * Math.cos(bAngle * 0.7)}
            stroke={trunkColor} strokeWidth={2.5} strokeLinecap="round" />
          <line x1={cx + bx} y1={branchY - by}
            x2={cx + bx + subLen * Math.sin(bAngle * 0.7)}
            y2={branchY - by - subLen * Math.cos(bAngle * 0.7)}
            stroke={trunkColor} strokeWidth={2.5} strokeLinecap="round" />
        </>
      )}

      {/* Leaves */}
      {leafR > 1 && (
        <>
          <circle cx={cx - bx} cy={branchY - by} r={leafR} fill={leafColor} opacity={0.85} />
          <circle cx={cx + bx} cy={branchY - by} r={leafR} fill={leafColor} opacity={0.85} />
          {/* Top leaf cluster */}
          <circle cx={cx} cy={gndY - stemH} r={leafR * 0.85} fill={leafColor} opacity={0.80} />
          {subP > 0.2 && (
            <>
              <circle cx={fruitX_L} cy={fruitY_L - fruitR * 1.2} r={leafR * 0.65}
                fill={leafColor} opacity={0.75} />
              <circle cx={fruitX_R} cy={fruitY_R - fruitR * 1.2} r={leafR * 0.65}
                fill={leafColor} opacity={0.75} />
            </>
          )}
        </>
      )}

      {/* Fruit (before fall) */}
      {fruitR > 1 && fallP < 0.02 && (
        <>
          <circle cx={fruitX_L} cy={fruitY_L} r={fruitR} fill={fruitColor} />
          <circle cx={fruitX_R} cy={fruitY_R} r={fruitR} fill={fruitColor} />
          {/* Highlight */}
          <circle cx={fruitX_L - fruitR * 0.28} cy={fruitY_L - fruitR * 0.28}
            r={fruitR * 0.22} fill="rgba(255,255,255,0.45)" />
          <circle cx={fruitX_R - fruitR * 0.28} cy={fruitY_R - fruitR * 0.28}
            r={fruitR * 0.22} fill="rgba(255,255,255,0.45)" />
        </>
      )}

      {/* Fruit (falling) */}
      {fallP > 0.02 && fruitR > 1 && (
        <>
          <circle cx={fruitX_L} cy={fruitFallY_L} r={fruitR} fill={fruitColor} />
          <circle cx={fruitX_R} cy={fruitFallY_R} r={fruitR} fill={fruitColor} />
        </>
      )}

      {/* Seed (beginning) */}
      {seedP < 1 && cycleT < seedEnd + 0.02 && (
        <circle cx={cx} cy={gndY - 8}
          r={lerp(4, 10, seedP)}
          fill={trunkColor} />
      )}
    </g>
  );
};

// ── KALEIDOSCOPE mode ─────────────────────────────────────────────────────────

const Kaleidoscope: React.FC<{
  fSec: number; width: number; height: number;
  spritePaths: string[]; spriteSize: number; seed: number;
}> = ({ fSec, width, height, spritePaths, spriteSize, seed }) => {
  const cx   = width  * 0.50;
  const cy   = height * 0.50;
  const arms = Math.min(6, Math.max(4, spritePaths.length));  // 4–6 arms
  const orbitR = Math.min(width, height) * 0.28;
  const rot  = fSec * 6;  // degrees/sec — slow rotation
  const sz   = spriteSize;

  return (
    <>
      {Array.from({ length: arms }, (_, i) => {
        const angle = (i / arms) * 360 + rot;
        const rad   = (angle * Math.PI) / 180;
        const x     = cx + Math.cos(rad) * orbitR - sz / 2;
        const y     = cy + Math.sin(rad) * orbitR * 0.70 - sz / 2;
        const path  = spritePaths[i % spritePaths.length];
        const selfRot = rot * 0.40 + i * (360 / arms);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x, top: y,
              width: sz, height: sz,
              transform: `rotate(${selfRot}deg)`,
              transformOrigin: "center center",
            }}
          >
            <Img src={staticFile(`sprites/${path}`)} style={{ width: sz, height: sz }} />
          </div>
        );
      })}
      {/* Inner ring (half size, counter-rotate) */}
      {Array.from({ length: arms }, (_, i) => {
        const angle = (i / arms) * 360 - rot * 0.65 + 30;
        const rad   = (angle * Math.PI) / 180;
        const r2    = orbitR * 0.48;
        const s2    = sz * 0.55;
        const x     = cx + Math.cos(rad) * r2 - s2 / 2;
        const y     = cy + Math.sin(rad) * r2 * 0.70 - s2 / 2;
        const path  = spritePaths[(i + 1) % spritePaths.length];
        return (
          <div
            key={`i${i}`}
            style={{
              position: "absolute",
              left: x, top: y,
              width: s2, height: s2,
              opacity: 0.75,
            }}
          >
            <Img src={staticFile(`sprites/${path}`)} style={{ width: s2, height: s2 }} />
          </div>
        );
      })}
    </>
  );
};

// ── RAIN mode ─────────────────────────────────────────────────────────────────

const Rain: React.FC<{
  fSec: number; width: number; height: number;
  spritePaths: string[]; spriteSize: number;
  accentColor: string; seed: number;
}> = ({ fSec, width, height, spritePaths, spriteSize, accentColor, seed }) => {
  const gndY    = height * 0.72;
  const nDrops  = 60;
  const dropH   = 24;
  const dropW   = 2;
  const dropColor = "rgba(180,210,240,0.70)";

  const drops = useMemo(() => Array.from({ length: nDrops }, (_, i) => ({
    x:     sr(seed * 17 + i * 499) * width,
    speed: 5.5 + sr(seed * 31 + i * 113) * 3.5,
    offset: sr(seed * 23 + i * 211) * 100,
    opacity: 0.4 + sr(seed * 41 + i * 307) * 0.5,
  })), [seed, width]);

  return (
    <>
      {/* Rain drops */}
      {drops.map((d, i) => {
        const y = ((d.offset + fSec * d.speed * 50) % (gndY + dropH)) - dropH;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: d.x - dropW / 2,
              top:  y,
              width: dropW,
              height: dropH,
              background: dropColor,
              borderRadius: dropW,
              opacity: d.opacity,
            }}
          />
        );
      })}

      {/* Sprites in garden */}
      {spritePaths.slice(0, 4).map((path, i) => {
        const n   = Math.min(spritePaths.length, 4);
        const xPos = (0.15 + (i / (n - 1 || 1)) * 0.70) * width;
        const sz  = spriteSize;
        const bob = Math.sin(fSec * 1.5 + i * 0.8) * 8;
        return (
          <div
            key={`sp${i}`}
            style={{
              position: "absolute",
              left:   xPos - sz / 2,
              top:    gndY - sz + bob,
              width:  sz,
              height: sz,
            }}
          >
            <Img src={staticFile(`sprites/${path}`)} style={{ width: sz, height: sz }} />
          </div>
        );
      })}

      {/* Ground */}
      <div style={{
        position: "absolute",
        left: 0, top: gndY,
        width: "100%", height: height - gndY,
        background: "linear-gradient(to bottom, #3D6B35 0%, #2D5228 100%)",
      }} />

      {/* Puddle splashes (every ~3s) */}
      {Array.from({ length: 5 }, (_, i) => {
        const phaseSec = (fSec + sr(seed * 71 + i * 199) * 3) % 3;
        const px = (0.1 + sr(seed * 89 + i * 131) * 0.80) * width;
        if (phaseSec > 0.6) return null;
        const pr = phaseSec * 30;
        const op = (0.6 - phaseSec) / 0.6;
        return (
          <div key={`sp${i}`} style={{
            position: "absolute",
            left: px - pr, top: gndY - pr * 0.25,
            width: pr * 2, height: pr * 0.5,
            borderRadius: "50%",
            border: `1.5px solid rgba(180,210,240,${op * 0.6})`,
          }} />
        );
      })}
    </>
  );
};

// ── DAY_NIGHT mode ────────────────────────────────────────────────────────────

const DayNight: React.FC<{
  fSec: number; cycleDur: number;
  width: number; height: number;
  accentColor: string; seed: number;
}> = ({ fSec, cycleDur, width, height, seed }) => {
  const horY  = height * 0.60;
  const t     = ((fSec % cycleDur) + cycleDur) % cycleDur / cycleDur; // 0–1

  // Sky color: dawn(0)→day(0.15)→midday(0.30)→afternoon(0.45)→dusk(0.55)→night(0.70)→midnight(0.85)→dawn(1)
  const colorStops: [number, string][] = [
    [0.00, "#FF8C00"], [0.12, "#87CEEB"], [0.35, "#4A9FD4"],
    [0.50, "#E07A30"], [0.62, "#1A104A"], [0.80, "#020C28"], [1.00, "#FF8C00"],
  ];

  let skyColor: string = colorStops[0][1];
  for (let i = 0; i < colorStops.length - 1; i++) {
    const [t0, c0] = colorStops[i];
    const [t1, c1] = colorStops[i + 1];
    if (t >= t0 && t <= t1) {
      skyColor = lerpHex(c0, c1, (t - t0) / (t1 - t0));
      break;
    }
  }

  // Sun/Moon arc: 0→1 = full arc left-to-right
  const isDay  = t < 0.50 || t > 0.92;
  const arcT   = isDay ? (t > 0.92 ? t - 0.92 + 0 : t) / 0.50 : (t - 0.50) / 0.42;
  const arcX   = lerp(width * 0.05, width * 0.95, arcT);
  const arcY   = horY - Math.sin(arcT * Math.PI) * horY * 0.75;
  const bodyR  = isDay ? 52 : 42;
  const bodyColor = isDay ? "#FFD700" : "#F0F0D0";
  const glowR  = bodyR * 2.2;
  const glowOp = isDay ? 0.25 : 0.15;

  // Stars visible at night
  const nightOp = clamp01(
    t > 0.60 ? (t - 0.60) / 0.15 :
    t > 0.85 && t < 0.95 ? (0.95 - t) / 0.10 : 0,
  );
  const stars = useMemo(() => Array.from({ length: 20 }, (_, i) => ({
    x: sr(seed * 11 + i * 377) * width,
    y: sr(seed * 13 + i * 211) * horY * 0.85,
    r: 2 + sr(seed * 17 + i * 137) * 4,
    phase: sr(seed * 19 + i * 97) * Math.PI * 2,
  })), [seed, width, horY]);

  return (
    <>
      {/* Sky */}
      <div style={{
        position: "absolute", left: 0, top: 0,
        width: "100%", height: horY,
        background: skyColor,
        transition: "background 0.1s",
      }} />

      {/* Ground */}
      <div style={{
        position: "absolute", left: 0, top: horY,
        width: "100%", height: height - horY,
        background: isDay
          ? "linear-gradient(to bottom, #4A7C40 0%, #3A6230 100%)"
          : "linear-gradient(to bottom, #1A2E18 0%, #111E10 100%)",
      }} />

      {/* Stars (night only) */}
      {nightOp > 0.01 && (
        <svg style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%" }}
          viewBox={`0 0 ${width} ${horY}`}
        >
          {stars.map((s, i) => {
            const tw = 0.5 + 0.5 * Math.sin(fSec * 2 + s.phase);
            return <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="#FFFFFF" opacity={tw * nightOp} />;
          })}
        </svg>
      )}

      {/* Sun / Moon glow */}
      <div style={{
        position: "absolute",
        left:   arcX - glowR,
        top:    arcY - glowR,
        width:  glowR * 2,
        height: glowR * 2,
        borderRadius: "50%",
        background: `radial-gradient(circle, ${bodyColor}${Math.round(glowOp * 255).toString(16).padStart(2, "0")} 0%, transparent 70%)`,
      }} />

      {/* Sun / Moon body */}
      <div style={{
        position: "absolute",
        left:   arcX - bodyR,
        top:    arcY - bodyR,
        width:  bodyR * 2,
        height: bodyR * 2,
        borderRadius: "50%",
        background: bodyColor,
        boxShadow: isDay
          ? `0 0 ${bodyR}px ${bodyColor}`
          : `0 0 ${bodyR * 0.5}px rgba(240,240,200,0.4)`,
      }} />

      {/* Moon crescent highlight */}
      {!isDay && (
        <div style={{
          position: "absolute",
          left:   arcX - bodyR + bodyR * 0.35,
          top:    arcY - bodyR * 0.55,
          width:  bodyR * 1.0,
          height: bodyR * 1.0,
          borderRadius: "50%",
          background: skyColor,
          opacity: 0.75,
        }} />
      )}
    </>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────

const DEFAULT_CYCLE: Record<TransformMode, number> = {
  grow: 150, kaleidoscope: 60, rain: 80, day_night: 240,
};

export const TransformLong: React.FC<TransformLongProps> = ({
  mode,
  bgColor,
  accentColor,
  altColor = "#4CAF50",
  musicFile,
  volume = 0.18,
  cycleDuration,
  spritePaths = [],
  spriteSize = 200,
  seed = 42,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const fSec = frame / fps;
  const cycle = cycleDuration ?? DEFAULT_CYCLE[mode];

  const fadeIn  = interpolate(fSec, [0, 2.5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [durationInFrames - fps * 4, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const globalOp = fadeIn * fadeOut;

  // Background: for most modes use bgColor; day_night uses its own sky
  const showStaticBg = mode !== "day_night";

  return (
    <AbsoluteFill style={{ backgroundColor: showStaticBg ? bgColor : "#87CEEB", overflow: "hidden" }}>
      <Audio src={staticFile(`music/${musicFile}`)} volume={volume} loop />

      <AbsoluteFill style={{ opacity: globalOp }}>
        {/* ── DAY_NIGHT ── */}
        {mode === "day_night" && (
          <DayNight
            fSec={fSec} cycleDur={cycle}
            width={width} height={height}
            accentColor={accentColor} seed={seed}
          />
        )}

        {/* ── GROW ── */}
        {mode === "grow" && (
          <svg
            style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%" }}
            viewBox={`0 0 ${width} ${height}`}
          >
            {/* Slow color-shift background circles (decorative) */}
            {Array.from({ length: 4 }, (_, i) => {
              const bx = (0.2 + i * 0.22) * width;
              const by = height * (0.88 + Math.sin(fSec * 0.3 + i) * 0.04);
              const br = 30 + i * 12;
              return (
                <circle key={i} cx={bx} cy={by} r={br}
                  fill={altColor} opacity={0.18} />
              );
            })}
            <Grow
              fSec={fSec} cycleDur={cycle}
              width={width} height={height}
              accentColor={accentColor} altColor={altColor}
            />
          </svg>
        )}

        {/* ── KALEIDOSCOPE ── */}
        {mode === "kaleidoscope" && spritePaths.length > 0 && (
          <Kaleidoscope
            fSec={fSec} width={width} height={height}
            spritePaths={spritePaths} spriteSize={spriteSize} seed={seed}
          />
        )}

        {/* ── RAIN ── */}
        {mode === "rain" && (
          <Rain
            fSec={fSec} width={width} height={height}
            spritePaths={spritePaths} spriteSize={spriteSize}
            accentColor={accentColor} seed={seed}
          />
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
