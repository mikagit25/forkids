/**
 * SleepClassicalLoop — seamless 4-minute visual loop for Calm Classics channel.
 * Rendered once per theme, then assembled into 1h/3h/8h via FFmpeg.
 * Format: 1920×1080, 30fps. NO text. Adult aesthetic.
 *
 * LOOP RULE: all Math.sin/cos frequencies must be k * (2π / LOOP_SECS)
 * where k is a positive integer → guaranteed seamless at LOOP_SECS.
 * LOOP_SECS default: 240 (4 min). night_bear uses 300 (5 min).
 *
 * Themes:
 *   moon_clouds  — night sky, large moon, drifting clouds, stars
 *   night_bear   — sleeping bear silhouette, fireflies, forest
 *   warm_waves   — ocean waves at sunset/dusk, amber glow
 *   rain_window  — rain on glass, warm interior, distant city lights
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { noise2D } from "@remotion/noise";

export type SleepTheme = "moon_clouds" | "night_bear" | "warm_waves" | "rain_window";

export interface SleepClassicalLoopProps {
  theme: SleepTheme;
  musicFile?: string;   // empty string or omit → no audio (for shared loop renders)
  loopSecs?: number;    // 240 for most themes, 300 for night_bear
  phaseOffset?: number; // 0..1 — vary visual for different programs using same theme
}

// ── Seeded pseudo-random (deterministic, no state) ───────────────────────────
function sr(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}

// ── Seamless sin: frequency = k * (2π / loopSecs), k integer ─────────────────
function ssin(t: number, k: number, loopSecs: number, phase = 0): number {
  return Math.sin(t * k * (Math.PI * 2 / loopSecs) + phase);
}
function scos(t: number, k: number, loopSecs: number, phase = 0): number {
  return Math.cos(t * k * (Math.PI * 2 / loopSecs) + phase);
}


// ══════════════════════════════════════════════════════════════════════════════
// THEME: moon_clouds
// ══════════════════════════════════════════════════════════════════════════════

const MoonClouds: React.FC<{
  w: number; h: number; t: number; ls: number; phase: number;
}> = ({ w, h, t, ls, phase }) => {
  // Moon breathe: 1 cycle per 60s (k=4 for 240s loop)
  const moonBreath = 1 + 0.018 * ssin(t, 4, ls, phase);
  const moonGlow   = 0.15 + 0.04 * ssin(t, 2, ls, phase * 0.7);
  const moonSize   = 130 * moonBreath;

  // Cloud positions: k=1 (very slow, 1 cycle per 240s = barely moves, perfect loop)
  const clouds = Array.from({ length: 7 }, (_, i) => {
    const baseX  = sr(i * 7 + 1) * w * 1.6 - w * 0.3;
    const speed  = 0.6 + sr(i * 11 + 1) * 0.5; // relative drift speed
    // Wrap X seamlessly: uses ssin to drift gently left-right over loop
    const dx     = ssin(t, 1, ls, sr(i * 13 + phase) * Math.PI * 2) * w * 0.12 * speed;
    const cx     = (baseX + dx + w) % (w * 1.4) - w * 0.2;
    const cy     = sr(i * 17 + 1) * h * 0.55 + h * 0.05;
    const cw     = 200 + sr(i * 19 + 1) * 350;
    const ch     = cw * (0.25 + sr(i * 23 + 1) * 0.20);
    const op     = (0.06 + sr(i * 29 + 1) * 0.10) * (1 + 0.15 * ssin(t, 2, ls, sr(i * 5) * 6));
    return { cx, cy, cw, ch, op };
  });

  // Stars: 120 static twinkling points
  const stars = Array.from({ length: 120 }, (_, i) => {
    const x  = sr(i * 7 + 100) * w;
    const y  = sr(i * 11 + 100) * h * 0.85;
    const sz = 0.8 + sr(i * 3 + 100) * 2.2;
    // Twinkle: k=3 to k=8 to give variety, all seamless
    const k  = 3 + (i % 6);
    const op = (0.3 + sr(i * 17 + 100) * 0.5) * (0.6 + 0.4 * ssin(t, k, ls, sr(i * 23) * 6));
    return { x, y, sz, op };
  });

  return (
    <>
      {/* Night sky gradient */}
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(180deg, #030612 0%, #060d1f 40%, #0a1228 70%, #060810 100%)",
      }} />

      {/* Stars */}
      {stars.map((s, i) => (
        <div key={i} style={{
          position: "absolute",
          left: s.x - s.sz / 2, top: s.y - s.sz / 2,
          width: s.sz, height: s.sz,
          borderRadius: "50%",
          backgroundColor: "#E8F0FF",
          opacity: s.op,
        }} />
      ))}

      {/* Moon halo */}
      <div style={{
        position: "absolute",
        right: w * (0.10 + phase * 0.08),
        top: h * (0.06 + phase * 0.03),
        width: moonSize * 3, height: moonSize * 3,
        borderRadius: "50%",
        background: `radial-gradient(circle, rgba(255,255,220,${moonGlow * 0.3}) 0%, transparent 70%)`,
      }} />

      {/* Moon */}
      <div style={{
        position: "absolute",
        right: w * (0.10 + phase * 0.08),
        top: h * (0.06 + phase * 0.03),
        width: moonSize, height: moonSize,
        borderRadius: "50%",
        backgroundColor: "#FFFCE8",
        opacity: 0.88,
        boxShadow: `0 0 ${60 + moonGlow * 40}px ${30 + moonGlow * 20}px rgba(255,252,200,${moonGlow}), 0 0 ${120 + moonGlow * 60}px rgba(255,250,180,${moonGlow * 0.4})`,
      }} />

      {/* Clouds */}
      {clouds.map((c, i) => (
        <div key={i} style={{
          position: "absolute",
          left: c.cx - c.cw / 2, top: c.cy - c.ch / 2,
          width: c.cw, height: c.ch,
          borderRadius: "50%",
          backgroundColor: `rgba(200,215,255,${c.op})`,
          filter: "blur(22px)",
        }} />
      ))}

      {/* Subtle horizon glow */}
      <div style={{
        position: "absolute",
        bottom: 0, left: 0, right: 0, height: "20%",
        background: "linear-gradient(0deg, rgba(8,14,30,0.8) 0%, transparent 100%)",
      }} />
    </>
  );
};


// ══════════════════════════════════════════════════════════════════════════════
// THEME: night_bear  (loopSecs = 300)
// ══════════════════════════════════════════════════════════════════════════════

const NightBear: React.FC<{
  w: number; h: number; t: number; ls: number; phase: number;
}> = ({ w, h, t, ls, phase }) => {
  // Bear breathing: very slow, k=1 per 300s
  const bearBreath = 1 + 0.022 * ssin(t, 1, ls, 0);
  const bearScale  = 0.85 + phase * 0.08; // bears different sizes for different programs

  // Fireflies: 16 gentle glowing orbs, each drifts on unique seamless path
  const fireflies = Array.from({ length: 16 }, (_, i) => {
    const bx  = sr(i * 7 + 200) * w * 0.78 + w * 0.11;
    const by  = h * 0.25 + sr(i * 11 + 200) * h * 0.48;
    const k1  = 1 + (i % 5);     // 1..5 — drift X frequency
    const k2  = 1 + ((i + 2) % 5); // offset — drift Y
    const dx  = ssin(t, k1, ls, sr(i * 13 + 200) * 6) * (40 + sr(i * 17) * 30);
    const dy  = scos(t, k2, ls, sr(i * 19 + 200) * 6) * (28 + sr(i * 23) * 22);
    const k3  = 2 + (i % 4);
    const glow = 0.50 + 0.50 * Math.abs(ssin(t, k3, ls, sr(i * 29 + 200) * 6));
    const sz  = 10 + sr(i * 3 + 200) * 12;
    const hue = 48 + sr(i * 41 + 200) * 22; // warm yellow-gold
    return { x: bx + dx, y: by + dy, sz, glow, hue };
  });

  // Stars
  const stars = Array.from({ length: 90 }, (_, i) => {
    const x  = sr(i * 7 + 300) * w;
    const y  = sr(i * 11 + 300) * h * 0.72;
    const sz = 0.7 + sr(i * 3 + 300) * 1.8;
    const k  = 2 + (i % 8);
    const op = (0.25 + sr(i * 17 + 300) * 0.45) * (0.65 + 0.35 * ssin(t, k, ls, sr(i * 23 + 300) * 6));
    return { x, y, sz, op };
  });

  return (
    <>
      {/* Night sky */}
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(180deg, #020409 0%, #050b14 35%, #080e18 60%, #040610 100%)",
      }} />

      {/* Stars */}
      {stars.map((s, i) => (
        <div key={i} style={{
          position: "absolute",
          left: s.x - s.sz / 2, top: s.y - s.sz / 2,
          width: s.sz, height: s.sz,
          borderRadius: "50%",
          backgroundColor: "#D0E0FF",
          opacity: s.op,
        }} />
      ))}

      {/* Moon */}
      {(() => {
        const mb = 1 + 0.012 * ssin(t, 2, ls, phase);
        const mg = 0.12 + 0.03 * ssin(t, 3, ls);
        const ms = 100 * mb;
        return (
          <div style={{
            position: "absolute",
            right: w * (0.08 + phase * 0.06), top: h * 0.05,
            width: ms, height: ms,
            borderRadius: "50%",
            backgroundColor: "#FFFDE0",
            opacity: 0.80,
            boxShadow: `0 0 ${50 + mg * 35}px ${25 + mg * 18}px rgba(255,250,180,${mg})`,
          }} />
        );
      })()}

      {/* Ground */}
      <div style={{
        position: "absolute",
        bottom: 0, left: 0, right: 0, height: "22%",
        background: "linear-gradient(0deg, #020408 0%, #060d12 100%)",
      }} />

      {/* Tree silhouettes */}
      {Array.from({ length: 6 }, (_, i) => {
        const tx = (sr(i * 7 + 400) * 0.88 + 0.06) * w;
        const tw = 45 + sr(i * 11 + 400) * 50;
        const th = h * (0.30 + sr(i * 13 + 400) * 0.25);
        const isPine = sr(i * 17 + 400) > 0.4;
        return (
          <React.Fragment key={i}>
            <div style={{
              position: "absolute",
              left: tx - tw * 0.07, bottom: h * 0.22,
              width: tw * 0.14, height: th * 0.45,
              backgroundColor: "#040810",
            }} />
            {isPine ? (
              <div style={{
                position: "absolute",
                left: tx - tw / 2, bottom: h * 0.22 + th * 0.36,
                width: tw, height: th * 0.72,
                backgroundColor: "#030709",
                clipPath: "polygon(50% 0%, 5% 100%, 95% 100%)",
              }} />
            ) : (
              <div style={{
                position: "absolute",
                left: tx - tw / 2, bottom: h * 0.22 + th * 0.28,
                width: tw, height: th * 0.85,
                borderRadius: "50%",
                backgroundColor: "#03080B",
              }} />
            )}
          </React.Fragment>
        );
      })}

      {/* Bear silhouette (SVG-style pure CSS) */}
      {(() => {
        const bw   = 280 * bearScale;
        const bh   = 220 * bearScale;
        const bx   = w * (0.42 + phase * 0.08);
        const by   = h * 0.78;
        // Body
        return (
          <>
            {/* Body */}
            <div style={{
              position: "absolute",
              left: bx - bw * 0.5, top: by - bh * bearBreath,
              width: bw, height: bh * bearBreath,
              borderRadius: "50% 50% 40% 40%",
              backgroundColor: "#080C10",
              transform: `scaleY(${bearBreath})`,
              transformOrigin: "bottom center",
            }} />
            {/* Head */}
            <div style={{
              position: "absolute",
              left: bx - bw * 0.22, top: by - bh * bearBreath - bw * 0.32,
              width: bw * 0.44, height: bw * 0.40,
              borderRadius: "50%",
              backgroundColor: "#07090E",
            }} />
            {/* Left ear */}
            <div style={{
              position: "absolute",
              left: bx - bw * 0.18, top: by - bh * bearBreath - bw * 0.52,
              width: bw * 0.14, height: bw * 0.13,
              borderRadius: "50%",
              backgroundColor: "#06080C",
            }} />
            {/* Right ear */}
            <div style={{
              position: "absolute",
              left: bx + bw * 0.04, top: by - bh * bearBreath - bw * 0.52,
              width: bw * 0.14, height: bw * 0.13,
              borderRadius: "50%",
              backgroundColor: "#06080C",
            }} />
            {/* Zzz indicator — tiny star pulses very gently */}
            {[0, 1, 2].map(j => {
              const zop = 0.35 + 0.30 * ssin(t, 1, ls, j * 2.1);
              const zsz = (3 - j) * 4 + 3;
              return (
                <div key={j} style={{
                  position: "absolute",
                  left: bx + bw * (0.18 + j * 0.07),
                  top: by - bh * bearBreath - bw * (0.35 + j * 0.08),
                  width: zsz, height: zsz,
                  borderRadius: "50%",
                  backgroundColor: "#B8D0F0",
                  opacity: zop,
                  boxShadow: `0 0 ${zsz * 2}px rgba(180,210,255,${zop * 0.6})`,
                }} />
              );
            })}
          </>
        );
      })()}

      {/* Fireflies */}
      {fireflies.map((f, i) => (
        <div key={i} style={{
          position: "absolute",
          left: f.x - f.sz / 2, top: f.y - f.sz / 2,
          width: f.sz, height: f.sz,
          borderRadius: "50%",
          backgroundColor: `hsl(${f.hue}, 90%, 72%)`,
          opacity: f.glow * 0.92,
          boxShadow: `0 0 ${f.sz * 1.6 * f.glow}px ${f.sz * 0.8}px hsl(${f.hue}, 90%, 72%)`,
        }} />
      ))}
    </>
  );
};


// ══════════════════════════════════════════════════════════════════════════════
// THEME: warm_waves
// ══════════════════════════════════════════════════════════════════════════════

const WarmWaves: React.FC<{
  w: number; h: number; t: number; ls: number; phase: number;
}> = ({ w, h, t, ls, phase }) => {
  // Horizon glow breathe: k=3 (every 80s) — very slow
  const horizonGlow = 0.18 + 0.06 * ssin(t, 3, ls, phase);

  // 5 wave layers with different speeds and opacities — all seamless
  const waveLayers = Array.from({ length: 5 }, (_, i) => {
    const k      = 1 + i;           // k=1..5
    const amp    = 18 + i * 8;      // wave amplitude px
    const yBase  = h * (0.52 + i * 0.065);
    const op     = 0.12 + (4 - i) * 0.07;
    const col    = i < 2
      ? `rgba(255,165,60,${op})`    // warm amber near surface
      : `rgba(40,90,140,${op * 1.3})`; // deep blue lower
    return { k, amp, yBase, col };
  });

  return (
    <>
      {/* Dusk sky */}
      <div style={{
        position: "absolute", inset: 0,
        background: `linear-gradient(180deg,
          #0A0510 0%, #1A0818 12%,
          #2B0D1C 25%, #3D1520 40%,
          #5C2218 52%, #7A3012 60%,
          #9B4008 68%, #C05A04 75%,
          #A04806 80%, #7A3210 88%, #1A0D18 100%)`,
      }} />

      {/* A few stars near top */}
      {Array.from({ length: 30 }, (_, i) => {
        const x  = sr(i * 7 + 500) * w;
        const y  = sr(i * 11 + 500) * h * 0.38;
        const sz = 0.6 + sr(i * 3 + 500) * 1.4;
        const k  = 2 + (i % 5);
        const op = (0.15 + sr(i * 17 + 500) * 0.35) * (0.5 + 0.5 * ssin(t, k, ls, sr(i * 23 + 500) * 6));
        return (
          <div key={i} style={{
            position: "absolute", left: x - sz / 2, top: y - sz / 2,
            width: sz, height: sz, borderRadius: "50%",
            backgroundColor: "#FFE8C8", opacity: op,
          }} />
        );
      })}

      {/* Sun/moon just below horizon */}
      <div style={{
        position: "absolute",
        left: w * (0.45 + phase * 0.08) - 55,
        top: h * 0.50 - 55,
        width: 110, height: 110,
        borderRadius: "50%",
        backgroundColor: "#FF9020",
        opacity: 0.60,
        boxShadow: `0 0 ${80 + horizonGlow * 60}px ${40 + horizonGlow * 30}px rgba(255,120,20,${horizonGlow}), 0 0 ${180 + horizonGlow * 100}px rgba(255,80,10,${horizonGlow * 0.35})`,
      }} />

      {/* Horizon reflection band */}
      <div style={{
        position: "absolute",
        left: 0, right: 0,
        top: h * 0.50,
        height: h * 0.12,
        background: `linear-gradient(180deg, rgba(200,80,10,${horizonGlow * 0.55}) 0%, transparent 100%)`,
      }} />

      {/* Ocean body */}
      <div style={{
        position: "absolute",
        left: 0, right: 0, bottom: 0,
        height: h * 0.50,
        background: "linear-gradient(180deg, #0D1E35 0%, #061220 60%, #030C18 100%)",
      }} />

      {/* Waves */}
      {waveLayers.map((wl, i) => {
        // Wave shape via multiple sin components — all use valid k values
        const wavePoints = Array.from({ length: 40 }, (_, j) => {
          const x = (j / 39) * w;
          const y = wl.yBase
            + ssin(t, wl.k, ls, j * 0.28 + phase * 1.4) * wl.amp
            + ssin(t, wl.k * 2, ls, j * 0.55 + phase * 0.8) * (wl.amp * 0.4);
          return `${x},${y}`;
        });
        return (
          <svg key={i} style={{
            position: "absolute", inset: 0, overflow: "visible",
            width: "100%", height: "100%",
            pointerEvents: "none",
          }}>
            <polyline
              points={wavePoints.join(" ")}
              fill="none"
              stroke={wl.col}
              strokeWidth={2 + (4 - i) * 0.8}
            />
          </svg>
        );
      })}

      {/* Moonlit water reflection shimmer */}
      <div style={{
        position: "absolute",
        left: w * (0.35 + phase * 0.08), bottom: 0,
        width: w * 0.30,
        height: h * 0.48,
        background: `linear-gradient(0deg, rgba(255,150,40,${horizonGlow * 0.22}) 0%, transparent 100%)`,
        clipPath: "polygon(25% 0%, 75% 0%, 100% 100%, 0% 100%)",
        filter: "blur(8px)",
      }} />
    </>
  );
};


// ══════════════════════════════════════════════════════════════════════════════
// THEME: rain_window
// ══════════════════════════════════════════════════════════════════════════════

const RainWindow: React.FC<{
  w: number; h: number; t: number; ls: number; phase: number;
}> = ({ w, h, t, ls, phase }) => {
  // Interior amber glow breathe: k=2 (every 120s)
  const amberPulse = 0.18 + 0.05 * ssin(t, 2, ls, phase);

  // Rain drops: 70 drops, each has seamless vertical cycle
  const drops = Array.from({ length: 70 }, (_, i) => {
    const cx    = sr(i * 7 + 600) * w;
    const speed = 220 + sr(i * 11 + 600) * 280;   // px/s
    const period = (h + 60) / speed;               // seconds per cycle
    // Use t directly (rain doesn't need perfect loop — continuous rain)
    const yNorm = ((t / period + sr(i * 13 + 600)) % 1 + 1) % 1;
    const cy    = yNorm * (h + 60) - 30;
    const dh    = 12 + sr(i * 5 + 600) * 18;
    const dw    = 1.8 + sr(i * 3 + 600) * 1.4;
    const op    = 0.25 + sr(i * 17 + 600) * 0.28;
    const angle = 8 + phase * 6;                   // rain angle varies per program
    return { cx, cy, dh, dw, op, angle };
  });

  // Water streaks on glass: 16 slow streaks
  const streaks = Array.from({ length: 16 }, (_, i) => {
    const cx    = sr(i * 7 + 700) * w * 0.82 + w * 0.09;
    const speed = 45 + sr(i * 11 + 700) * 70;
    const period = h / speed;
    const yNorm = ((t / period + sr(i * 13 + 700)) % 1 + 1) % 1;
    const cy    = yNorm * h;
    const sway  = ssin(t, 1, ls, sr(i * 17 + 700) * 6) * 10;
    const sh    = 38 + sr(i * 19 + 700) * 70;
    const op    = 0.10 + sr(i * 21 + 700) * 0.12;
    return { cx: cx + sway, cy, sh, op };
  });

  // Distant city lights: 12 flickering lights through wet glass
  const lights = Array.from({ length: 12 }, (_, i) => {
    const lx    = sr(i * 7 + 800) * w * 0.75 + w * 0.12;
    const ly    = h * 0.20 + sr(i * 11 + 800) * h * 0.32;
    const sz    = 3 + sr(i * 3 + 800) * 7;
    // Flicker: k=4 to k=10 so multiple beats visible in 4 min
    const k     = 4 + (i % 7);
    const flicker = 0.5 + 0.5 * Math.abs(ssin(t, k, ls, sr(i * 13 + 800) * 6));
    const isWarm = sr(i * 17 + 800) > 0.45;
    return { lx, ly, sz, flicker, isWarm };
  });

  return (
    <>
      {/* Rainy night exterior */}
      <div style={{
        position: "absolute", inset: 0,
        background: "linear-gradient(180deg, #020508 0%, #040810 50%, #030609 100%)",
      }} />

      {/* Blurry building silhouettes */}
      {Array.from({ length: 5 }, (_, i) => {
        const bw = 100 + sr(i * 7 + 900) * 140;
        const bh = h * (0.18 + sr(i * 11 + 900) * 0.25);
        const bx = (sr(i * 13 + 900) * 0.78 + 0.11) * w;
        return (
          <div key={i} style={{
            position: "absolute",
            left: bx - bw / 2, bottom: h * 0.14,
            width: bw, height: bh,
            backgroundColor: "rgba(6,10,18,0.80)",
            filter: "blur(5px)",
          }} />
        );
      })}

      {/* Distant city lights */}
      {lights.map((l, i) => (
        <div key={i} style={{
          position: "absolute",
          left: l.lx - l.sz / 2, top: l.ly - l.sz / 2,
          width: l.sz, height: l.sz * 0.65,
          borderRadius: "50%",
          backgroundColor: l.isWarm
            ? `rgba(255,185,55,${0.70 * l.flicker})`
            : `rgba(170,205,255,${0.55 * l.flicker})`,
          boxShadow: l.isWarm
            ? `0 0 ${l.sz * 2.5 * l.flicker}px rgba(255,150,40,${0.35 * l.flicker})`
            : `0 0 ${l.sz * 2 * l.flicker}px rgba(150,195,255,${0.3 * l.flicker})`,
          filter: "blur(1px)",
        }} />
      ))}

      {/* Rain drops */}
      {drops.map((d, i) => (
        <div key={i} style={{
          position: "absolute",
          left: d.cx, top: d.cy,
          width: d.dw, height: d.dh,
          background: `linear-gradient(180deg, transparent 0%, rgba(155,205,255,${d.op}) 40%, rgba(125,180,240,${d.op}) 100%)`,
          borderRadius: d.dw,
          transform: `rotate(${d.angle}deg)`,
        }} />
      ))}

      {/* Water streaks on glass */}
      {streaks.map((s, i) => (
        <div key={i} style={{
          position: "absolute",
          left: s.cx, top: s.cy,
          width: 2, height: s.sh,
          background: `linear-gradient(180deg, transparent 0%, rgba(145,195,250,${s.op}) 30%, rgba(115,175,235,${s.op}) 75%, transparent 100%)`,
          borderRadius: 2,
        }} />
      ))}

      {/* Window frame */}
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "12%",
        background: "linear-gradient(180deg, rgba(4,2,1,0.98) 0%, transparent 100%)" }} />
      <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "15%",
        background: "linear-gradient(0deg, rgba(4,2,1,0.98) 0%, transparent 100%)" }} />
      <div style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: "9%",
        background: "linear-gradient(90deg, rgba(3,1,1,0.97) 0%, transparent 100%)" }} />
      <div style={{ position: "absolute", top: 0, bottom: 0, right: 0, width: "9%",
        background: "linear-gradient(270deg, rgba(3,1,1,0.97) 0%, transparent 100%)" }} />

      {/* Cosy interior amber glow */}
      <div style={{
        position: "absolute",
        bottom: 0, left: "9%", right: "9%", height: "42%",
        background: `radial-gradient(ellipse 100% 100% at 50% 100%,
          rgba(255,145,30,${amberPulse}) 0%,
          rgba(220,100,15,${amberPulse * 0.45}) 45%,
          transparent 100%)`,
      }} />

      {/* Candle/lamp warm spot */}
      <div style={{
        position: "absolute",
        bottom: "15%",
        left: `${10 + phase * 16}%`,
        width: 90, height: 60,
        background: `radial-gradient(ellipse at center, rgba(255,195,70,${0.26 + 0.08 * ssin(t, 6, ls, 0)}) 0%, transparent 70%)`,
      }} />
    </>
  );
};


// ══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════════════════════════════════

export const SleepClassicalLoop: React.FC<SleepClassicalLoopProps> = ({
  theme,
  musicFile,
  loopSecs = 240,
  phaseOffset = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;

  const ls = theme === "night_bear" ? 300 : (loopSecs ?? 240);

  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#020408" }}>
      {musicFile && musicFile.length > 0 && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={0.85} loop />
      )}

      {theme === "moon_clouds" && (
        <MoonClouds w={width} h={height} t={t} ls={ls} phase={phaseOffset} />
      )}
      {theme === "night_bear" && (
        <NightBear w={width} h={height} t={t} ls={ls} phase={phaseOffset} />
      )}
      {theme === "warm_waves" && (
        <WarmWaves w={width} h={height} t={t} ls={ls} phase={phaseOffset} />
      )}
      {theme === "rain_window" && (
        <RainWindow w={width} h={height} t={t} ls={ls} phase={phaseOffset} />
      )}

      {/* Global subtle vignette */}
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(ellipse 90% 90% at 50% 50%, transparent 55%, rgba(0,0,0,0.45) 100%)",
        pointerEvents: "none",
      }} />
    </AbsoluteFill>
  );
};
