/**
 * LullabyLoop — 5-minute seamless sleep content loop.
 * Rendered once, then extended to 1-2h via FFmpeg in generate_lullaby.py.
 * Format: 1920×1080, 30fps, dark background, BPM 50-55.
 * No text, no faces after frame 900 — universal content.
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export interface LullabyLoopProps {
  theme: "stars" | "ocean" | "garden" | "train" | "rain" | "forest";
  bgColorTop: string;
  bgColorBottom: string;
  accentColor: string;
  musicFile?: string;
  bpm?: number;
  phaseOffset?: number; // 0..1 — offsets all star phases so EN/AR/ID have different visual rhythm
}

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ── Background star field (tiny CSS dots, 3 depth layers) ────────────────────
const StarField: React.FC<{
  w: number; h: number; frame: number; color: string;
}> = ({ w, h, frame, color }) => {
  const r = seededRand;
  const t = frame / 30;
  return (
    <>
      {Array.from({ length: 90 }, (_, i) => {
        const cx = r(i * 7) * w;
        const cy = r(i * 11) * h;
        const sz = 1 + r(i * 3) * 2.5;
        const tw = 0.6 + r(i * 5) * 0.8;
        const ph = r(i * 13) * Math.PI * 2;
        const op = (0.12 + r(i * 17) * 0.35) * (0.7 + 0.3 * Math.sin(t * tw + ph));
        return (
          <div key={i} style={{
            position: "absolute",
            left: cx - sz / 2, top: cy - sz / 2,
            width: sz, height: sz,
            borderRadius: "50%",
            backgroundColor: color,
            opacity: op,
          }} />
        );
      })}
    </>
  );
};

// ── Drifting star sprite (FLUX PNG, travels across screen) ───────────────────
const DriftingStar: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number;
  phaseOffset: number; yOffset?: number; sizeScale?: number;
}> = ({ seed, w, h, frame, fps, phaseOffset, yOffset = 0, sizeScale = 1 }) => {
  const r = seededRand;
  const t = frame / fps;

  // Size tier by seed range
  const rawSize = seed <= 3  ? 55  + r(seed * 3) * 35   // far: 55–90px
                : seed <= 7  ? 110 + r(seed * 3) * 55   // mid: 110–165px
                :              175 + r(seed * 3) * 95;  // near: 175–270px
  const size = rawSize * sizeScale;

  // Crossing period (seconds): far=slow, near=faster
  const period = seed <= 3  ? 75 + r(seed * 7) * 35
               : seed <= 7  ? 48 + r(seed * 7) * 22
               :              30 + r(seed * 7) * 16;

  const direction = r(seed * 17) > 0.5 ? 1 : -1;
  const phase     = ((r(seed * 23) + phaseOffset) % 1 + 1) % 1;

  // X: linear wrap
  const xNorm = ((t / period + phase) % 1 + 1) % 1;
  const rawX  = xNorm * (w + size * 2) - size;
  const cx    = direction > 0 ? rawX : w + size - rawX;

  // Y: base + gentle oscillation
  const yBase  = r(seed * 31) * h * 0.78 + h * 0.11;
  const yFreq  = 0.12 + r(seed * 37) * 0.14;
  const yAmp   = 22 + r(seed * 41) * 28;
  const yPh    = r(seed * 43) * Math.PI * 2;
  const cy     = yBase + yOffset + Math.sin(t * yFreq + yPh) * yAmp;

  // Wobble (PIP/BWW formula)
  const s = seed * 0.1;
  const scaleX = 1 + Math.sin(t * (8.3 + s * 0.7)) * 0.038 + Math.sin(t * (5.1 + s * 0.4)) * 0.020;
  const scaleY = 1 + Math.sin(t * (7.7 + s * 0.9)) * 0.038 + Math.cos(t * (4.2 + s * 1.1)) * 0.020;
  const rot    = Math.sin(t * (6.5 + s * 0.5)) * 1.4;

  // Twinkle + subtle hue shift
  const twFreq = 0.7 + r(seed * 53) * 0.7;
  const twPh   = r(seed * 59) * Math.PI * 2;
  const opacity = 0.50 + 0.38 * Math.sin(t * twFreq + twPh);
  const hue    = Math.sin(t * 0.07 + seed) * 22;

  return (
    <Img
      src={staticFile("sprites/objects/star_sleep.png")}
      style={{
        position: "absolute",
        left: cx - size / 2,
        top:  cy - size / 2,
        width: size, height: size,
        opacity,
        mixBlendMode: "screen" as const,
        transform: `scaleX(${scaleX}) scaleY(${scaleY}) rotate(${rot}deg)`,
        filter: `drop-shadow(0 0 ${size * 0.22}px rgba(255,215,70,0.65)) hue-rotate(${hue}deg)`,
        pointerEvents: "none",
      }}
    />
  );
};

// ── Ocean: drifting jellyfish (FLUX PNG) ─────────────────────────────────────
const DriftingJellyfish: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number; phaseOffset: number;
}> = ({ seed, w, h, frame, fps, phaseOffset }) => {
  const r = seededRand;
  const t = frame / fps;

  const size    = 100 + r(seed * 3) * 140;   // 100–240px
  const period  = 50  + r(seed * 7) * 40;    // 50–90s to cross screen
  const dir     = r(seed * 17) > 0.5 ? 1 : -1;
  const phase   = ((r(seed * 23) + phaseOffset) % 1 + 1) % 1;
  const xNorm   = ((t / period + phase) % 1 + 1) % 1;
  const rawX    = xNorm * (w + size * 2) - size;
  const cx      = dir > 0 ? rawX : w + size - rawX;

  // Y: mid-screen with gentle vertical drift
  const yBase   = h * 0.2 + r(seed * 31) * h * 0.55;
  const cy      = yBase + Math.sin(t * (0.18 + r(seed * 37) * 0.1) + r(seed * 43) * Math.PI * 2) * 35;

  // Pulse (jellyfish breathing)
  const pulse   = 1 + 0.12 * Math.sin(t * (1.2 + r(seed * 5) * 0.4) + r(seed * 11) * Math.PI * 2);

  // Wobble (PIP/BWW)
  const s       = seed * 0.1;
  const scaleX  = pulse * (1 + Math.sin(t * (8.3 + s * 0.7)) * 0.025);
  const scaleY  = pulse * (1 + Math.cos(t * (7.7 + s * 0.9)) * 0.025);
  const rot     = Math.sin(t * (4.5 + s * 0.5)) * 6;

  // Glow opacity — gentle breathe
  const opacity = 0.55 + 0.32 * Math.sin(t * (0.8 + r(seed * 53) * 0.5) + r(seed * 59) * Math.PI * 2);
  const hue     = Math.sin(t * 0.06 + seed) * 40; // shift between blue and purple

  return (
    <Img
      src={staticFile("sprites/objects/jellyfish_glow.png")}
      style={{
        position: "absolute",
        left: cx - (size * scaleX) / 2,
        top:  cy - (size * scaleY) / 2,
        width: size * scaleX, height: size * scaleY,
        opacity,
        mixBlendMode: "screen" as const,
        transform: `rotate(${rot}deg)`,
        filter: `drop-shadow(0 0 ${size * 0.18}px rgba(80,120,255,0.6)) hue-rotate(${hue}deg)`,
        pointerEvents: "none",
      }}
    />
  );
};

// ── Ocean: rising bubbles ────────────────────────────────────────────────────
const RisingBubble: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number;
}> = ({ seed, w, h, frame, fps }) => {
  const r  = seededRand;
  const t  = frame / fps;
  const sz = 8 + r(seed * 3) * 28;                // 8–36px
  const riseSpeed  = 20 + r(seed * 7) * 30;       // px/s
  const period     = (h + sz) / riseSpeed;
  const initPhase  = r(seed * 13);
  const yNorm      = ((t / period + initPhase) % 1 + 1) % 1;
  const cy         = h + sz - yNorm * (h + sz * 2); // bottom→top
  const cx         = r(seed * 23) * w * 0.9 + w * 0.05;
  const sway       = Math.sin(t * (0.9 + r(seed * 31) * 0.4) + r(seed * 37) * 6) * 18;
  const opacity    = (0.3 + r(seed * 41) * 0.4) * (0.7 + 0.3 * Math.sin(t * 1.5 + r(seed * 43) * 6));
  return (
    <div style={{
      position: "absolute",
      left: cx + sway - sz / 2, top: cy - sz / 2,
      width: sz, height: sz,
      borderRadius: "50%",
      border: `${sz * 0.06 + 0.5}px solid rgba(140,200,255,${opacity * 0.8})`,
      background: `radial-gradient(circle at 35% 35%, rgba(200,230,255,${opacity * 0.3}), rgba(80,140,220,${opacity * 0.08}))`,
      boxShadow: `0 0 ${sz * 0.5}px rgba(100,180,255,${opacity * 0.4})`,
    }} />
  );
};

// ── Ocean: drifting fish (FLUX PNG) ─────────────────────────────────────────
const DriftingFish: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number; phaseOffset: number;
}> = ({ seed, w, h, frame, fps, phaseOffset }) => {
  const r = seededRand;
  const t = frame / fps;
  const size   = 60 + r(seed * 3) * 80;
  const period = 40 + r(seed * 7) * 30;
  const dir    = r(seed * 17) > 0.5 ? 1 : -1;
  const phase  = ((r(seed * 23) + phaseOffset * 0.6) % 1 + 1) % 1;
  const xNorm  = ((t / period + phase) % 1 + 1) % 1;
  const rawX   = xNorm * (w + size * 2) - size;
  const cx     = dir > 0 ? rawX : w + size - rawX;
  const yBase  = h * 0.3 + r(seed * 31) * h * 0.5;
  const cy     = yBase + Math.sin(t * (0.25 + r(seed * 37) * 0.15) + r(seed * 43) * 6) * 25;
  const wobble = Math.sin(t * 5 + r(seed * 53) * 6) * 4;  // tail waggle expressed as rotation
  const opacity= 0.45 + 0.35 * Math.sin(t * (0.6 + r(seed * 59) * 0.4) + r(seed * 61) * 6);
  // flip horizontally if moving right so fish faces correct direction
  const flipX  = dir > 0 ? -1 : 1;

  return (
    <Img
      src={staticFile("sprites/objects/fish_deep.png")}
      style={{
        position: "absolute",
        left: cx - size / 2, top: cy - size / 2,
        width: size, height: size,
        opacity,
        mixBlendMode: "screen" as const,
        transform: `scaleX(${flipX}) rotate(${wobble}deg)`,
        filter: `drop-shadow(0 0 ${size * 0.15}px rgba(0,220,200,0.5))`,
        pointerEvents: "none",
      }}
    />
  );
};

// ── Ocean: caustic light rays from above ─────────────────────────────────────
const OceanCaustics: React.FC<{ w: number; h: number; frame: number }> = ({ w, h, frame }) => {
  const t = frame / 30;
  return (
    <>
      {[0, 1, 2, 3].map(i => {
        const x   = w * (0.15 + i * 0.22 + Math.sin(t * 0.08 + i * 1.4) * 0.05);
        const ht  = h * (0.4 + Math.sin(t * 0.05 + i * 2.1) * 0.08);
        const op  = 0.04 + 0.025 * Math.sin(t * 0.12 + i * 1.7);
        const wid = 30 + Math.sin(t * 0.09 + i * 1.1) * 14;
        return (
          <div key={i} style={{
            position: "absolute",
            left: x - wid / 2, top: 0,
            width: wid, height: ht,
            background: `linear-gradient(180deg, rgba(80,160,255,${op}) 0%, transparent 100%)`,
            transform: `skewX(${Math.sin(t * 0.07 + i * 0.9) * 6}deg)`,
          }} />
        );
      })}
    </>
  );
};

// ── Garden/Forest: firefly (large glow, always visible, drifts independently) ─
const Firefly: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number;
  color: string; phaseOffset: number;
}> = ({ seed, w, h, frame, fps, color, phaseOffset }) => {
  const r = seededRand;
  const t = frame / fps;

  // Position shifts per language via phaseOffset (Rule 8 + per-language differentiation)
  const baseX = ((r(seed * 7) + phaseOffset * 0.3) % 1) * w * 0.82 + w * 0.09;
  const baseY = h * 0.22 + r(seed * 11) * h * 0.55;

  // Independent drift per firefly (Rule 8: each has unique phase)
  const driftX = Math.sin(t * (0.35 + r(seed * 13) * 0.28) + seed * 1.2) * (52 + r(seed * 15) * 35);
  const driftY = Math.cos(t * (0.28 + r(seed * 17) * 0.22) + seed * 0.8) * (38 + r(seed * 19) * 22);

  // Size: 14–30px (was 6px — Rule 6)
  const sz = 14 + r(seed * 3) * 16;

  // Always-visible glow: min 0.50 so firefly never disappears (Rule 3)
  const glowCycle = 0.50 + 0.50 * Math.pow(
    Math.abs(Math.sin(t * (1.1 + r(seed * 5) * 0.7) + r(seed * 21) * Math.PI * 2)), 1.3
  );

  // Wobble (PIP/BWW — Rule 7)
  const s = seed * 0.1;
  const scale = 1 + Math.sin(t * (8.3 + s * 0.7)) * 0.04 + Math.cos(t * (5.1 + s * 0.4)) * 0.02;

  return (
    <div style={{
      position: "absolute",
      left: baseX + driftX - (sz * scale) / 2,
      top:  baseY + driftY - (sz * scale) / 2,
      width: sz * scale, height: sz * scale,
      borderRadius: "50%",
      backgroundColor: color,
      opacity: glowCycle * 0.95,
      boxShadow: `0 0 ${sz * 1.8 * glowCycle}px ${sz * glowCycle}px ${color}, 0 0 ${sz * 3.5 * glowCycle}px ${color}55`,
    }} />
  );
};

// ── Garden: floating petal / Forest: floating leaf ────────────────────────────
const FloatingParticle: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number;
  isForest: boolean; phaseOffset: number;
}> = ({ seed, w, h, frame, fps, isForest, phaseOffset }) => {
  const r = seededRand;
  const t = frame / fps;
  const speed  = 18 + r(seed * 7) * 22;           // px/s upward
  const period = (h * 1.3) / speed;
  const initPh = ((r(seed * 13) + phaseOffset * 0.45) % 1 + 1) % 1;
  const yNorm  = ((t / period + initPh) % 1 + 1) % 1;
  const cy     = h * 1.1 - yNorm * (h * 1.45);
  const cx     = r(seed * 23) * w * 0.78 + w * 0.11
               + Math.sin(t * (0.38 + r(seed * 29) * 0.28) + seed * 1.6) * 38;
  const pW     = isForest ? 8 + r(seed * 3) * 10 : 6 + r(seed * 3) * 8;
  const pH     = pW * (0.35 + r(seed * 5) * 0.40);
  const rot    = r(seed * 31) * 360 + t * (18 + r(seed * 37) * 28);
  const opacity = 0.30 + 0.42 * Math.abs(Math.sin(t * (0.45 + r(seed * 41) * 0.3) + r(seed * 43) * 6));
  // Garden: pink/white petals; Forest: brown/amber leaves. Hue shifts per language.
  const hue  = isForest ? 28 + r(seed * 43) * 20 + phaseOffset * 15
                        : 320 + r(seed * 43) * 50 + phaseOffset * 40;
  const sat  = isForest ? 50 : 55;
  const lig  = isForest ? 55 : 85;

  return (
    <div style={{
      position: "absolute",
      left: cx - pW / 2, top: cy - pH / 2,
      width: pW, height: pH,
      borderRadius: "50%",
      backgroundColor: `hsla(${hue}, ${sat}%, ${lig}%, ${opacity})`,
      transform: `rotate(${rot}deg)`,
    }} />
  );
};

// ── Garden/Forest scene background (ground, plants, trees) ───────────────────
const NightSceneBackground: React.FC<{
  w: number; h: number; frame: number; isForest: boolean; phaseOffset: number;
}> = ({ w, h, frame, isForest, phaseOffset }) => {
  const t = frame / 30;

  // Tree count: forest=more/larger, garden=fewer/smaller
  const treeCount  = isForest ? 7 : 4;
  const treeScale  = isForest ? 1.35 : 1.0;
  const groundHue  = isForest ? 140 : 130;

  return (
    <>
      {/* Ground strip */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        height: h * 0.22,
        background: `linear-gradient(0deg, hsl(${groundHue},25%,3%) 0%, hsl(${groundHue},20%,6%) 100%)`,
      }} />

      {/* Garden only: moonlit path shifts position per language */}
      {!isForest && (
        <div style={{
          position: "absolute",
          left: w * (0.36 + phaseOffset * 0.10),
          bottom: 0,
          width: w * 0.28,
          height: h * 0.22,
          background: `linear-gradient(0deg, rgba(${isForest ? "20,18,12" : "38,35,20"},0.5) 0%, rgba(${isForest ? "15,13,8" : "30,28,15"},0.18) 100%)`,
          clipPath: "polygon(18% 0%, 82% 0%, 100% 100%, 0% 100%)",
        }} />
      )}

      {/* Bushes / undergrowth */}
      {Array.from({ length: isForest ? 9 : 6 }, (_, i) => {
        const bX = ((seededRand(i * 7 + 200) + phaseOffset * 0.25) % 1) * w;
        const bW = (isForest ? 70 : 55) + seededRand(i * 11 + 200) * 85;
        const bH = bW * (0.35 + seededRand(i * 13 + 200) * 0.38);
        return (
          <div key={`bu${i}`} style={{
            position: "absolute",
            left: bX - bW / 2,
            bottom: h * 0.19,
            width: bW, height: bH,
            borderRadius: isForest ? "40% 60% 0 0" : "50% 50% 10% 10%",
            backgroundColor: `hsl(${groundHue + 10},22%,5%)`,
          }} />
        );
      })}

      {/* Trees */}
      {Array.from({ length: treeCount }, (_, i) => {
        const tX = (seededRand(i * 7 + 300 + phaseOffset * 10) * 0.9 + 0.05) * w;
        const tW = (50 + seededRand(i * 11 + 300) * 60) * treeScale;
        const tH = h * (0.38 + seededRand(i * 13 + 300) * 0.28) * treeScale;
        const isPine = seededRand(i * 17 + 300) > (isForest ? 0.35 : 0.6);
        return (
          <React.Fragment key={`sc${i}`}>
            <div style={{
              position: "absolute",
              left: tX - tW * 0.07, bottom: h * 0.19,
              width: tW * 0.14, height: tH * 0.48,
              backgroundColor: `hsl(${groundHue},18%,4%)`,
            }} />
            {isPine ? (
              <div style={{
                position: "absolute",
                left: tX - tW / 2, bottom: h * 0.19 + tH * 0.38,
                width: tW, height: tH * 0.72,
                backgroundColor: `hsl(${groundHue + 5},20%,4%)`,
                clipPath: "polygon(50% 0%, 5% 100%, 95% 100%)",
              }} />
            ) : (
              <div style={{
                position: "absolute",
                left: tX - tW / 2, bottom: h * 0.19 + tH * 0.30,
                width: tW, height: tH * 0.82,
                borderRadius: "50%",
                backgroundColor: `hsl(${groundHue + 5},20%,4%)`,
              }} />
            )}
          </React.Fragment>
        );
      })}

      {/* Garden: flower glow spots at ground level */}
      {!isForest && Array.from({ length: 18 }, (_, i) => {
        const fx  = ((seededRand(i * 7 + 400) + phaseOffset * 0.2) % 1) * w * 0.85 + w * 0.08;
        const fy  = h * 0.77 + seededRand(i * 11 + 400) * h * 0.04;
        const fsz = 4 + seededRand(i * 3 + 400) * 5;
        const pulse = 0.55 + 0.45 * Math.sin(t * (0.8 + seededRand(i * 5 + 400) * 0.5) + i * 0.9 + phaseOffset * 4);
        const fhue = 260 + seededRand(i * 17 + 400) * 100 + phaseOffset * 50;
        return (
          <div key={`fl${i}`} style={{
            position: "absolute",
            left: fx - fsz / 2, top: fy - fsz / 2,
            width: fsz, height: fsz,
            borderRadius: "50%",
            backgroundColor: `hsla(${fhue}, 70%, 75%, ${0.65 * pulse})`,
            boxShadow: `0 0 ${fsz * 1.8}px hsla(${fhue}, 70%, 75%, ${0.45 * pulse})`,
          }} />
        );
      })}

      {/* Moonlight glow on ground (position shifts per language) */}
      <div style={{
        position: "absolute",
        left: w * (0.22 + phaseOffset * 0.15),
        bottom: h * 0.19,
        width: w * 0.56,
        height: h * 0.07,
        background: "radial-gradient(ellipse at center, rgba(200,215,255,0.10) 0%, transparent 70%)",
      }} />
    </>
  );
};

// ── Rain: falling drop (visible width, proper opacity, angle per language) ────
const RainDrop: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number; phaseOffset: number;
}> = ({ seed, w, h, frame, fps, phaseOffset }) => {
  const r  = seededRand;
  const t  = frame / fps;
  const spd   = 280 + r(seed * 11) * 240; // px/s
  const period = (h + 60) / spd;
  const initPh = r(seed * 13);
  const yNorm  = ((t / period + initPh) % 1 + 1) % 1;
  const cy     = yNorm * (h + 60) - 30;
  const cx     = r(seed * 7) * w;
  const dropH  = 14 + r(seed * 5) * 20;
  const dropW  = 2 + r(seed * 3) * 1.5;  // 2–3.5px (was 1px)
  const opacity = 0.28 + r(seed * 17) * 0.30; // 0.28–0.58 (was 0.05–0.17)
  // Angle varies per language: EN=10°, AR=13°, ID=7°
  const angle  = 7 + phaseOffset * 9;
  return (
    <div style={{
      position: "absolute",
      left: cx, top: cy,
      width: dropW,
      height: dropH,
      background: `linear-gradient(180deg, transparent 0%, rgba(160,210,255,${opacity}) 40%, rgba(130,185,240,${opacity}) 100%)`,
      borderRadius: dropW,
      transform: `rotate(${angle}deg)`,
    }} />
  );
};

// ── Rain: water streaks running down the glass ────────────────────────────────
const WaterStreak: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number;
}> = ({ seed, w, h, frame, fps }) => {
  const r  = seededRand;
  const t  = frame / fps;
  const cx    = r(seed * 7) * w * 0.82 + w * 0.09;
  const speed = 60 + r(seed * 11) * 90; // px/s (much slower than drops)
  const period = h / speed;
  const initPh = r(seed * 13);
  const yNorm  = ((t / period + initPh) % 1 + 1) % 1;
  const cy     = yNorm * h;
  const sway   = Math.sin(t * (0.4 + r(seed * 17) * 0.3) + seed * 1.4) * 12;
  const stH    = 40 + r(seed * 19) * 80;
  const opacity = 0.12 + r(seed * 21) * 0.14;
  return (
    <div style={{
      position: "absolute",
      left: cx + sway, top: cy,
      width: 2, height: stH,
      background: `linear-gradient(180deg, transparent 0%, rgba(150,200,255,${opacity}) 30%, rgba(120,180,240,${opacity}) 75%, transparent 100%)`,
      borderRadius: 2,
    }} />
  );
};

// ── Moon ─────────────────────────────────────────────────────────────────────
const Moon: React.FC<{ frame: number; w: number }> = ({ frame, w }) => {
  const t = frame / 30;
  const glow = 0.14 + 0.05 * Math.sin(t * 0.4);
  const breathe = 1 + 0.015 * Math.sin(t * 0.25);
  return (
    <div style={{
      position: "absolute",
      right: w * 0.08,
      top: "6%",
      width: 110 * breathe, height: 110 * breathe,
      borderRadius: "50%",
      backgroundColor: "#FFFFD5",
      opacity: 0.75,
      boxShadow: `0 0 ${70 + glow * 50}px ${35 + glow * 30}px rgba(255,255,180,${glow}), 0 0 ${140 + glow * 80}px rgba(255,255,150,${glow * 0.4})`,
    }} />
  );
};

// ── Main ─────────────────────────────────────────────────────────────────────
export const LullabyLoop: React.FC<LullabyLoopProps> = ({
  theme,
  bgColorTop,
  bgColorBottom,
  accentColor,
  musicFile,
  bpm = 52,
  phaseOffset = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;

  // Train: sky hue shifts per language so EN/AR/ID look different
  // EN(0)→hsl(215), AR(0.37)→hsl(224), ID(0.68)→hsl(232)
  const trainSkyHue = 215 + phaseOffset * 25;

  const PARTICLE_COUNT = theme === "rain" ? 40 : 12;

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(180deg, ${bgColorTop} 0%, ${bgColorBottom} 100%)`,
      overflow: "hidden",
    }}>
      {musicFile && (
        <Audio
          src={staticFile(`music/${musicFile}`)}
          volume={0.12}
          loop
        />
      )}

      {/* Moon for all themes except train (train renders its own moon inside the window) */}
      {theme !== "train" && <Moon frame={frame} w={width} />}

      {/* Theme-specific elements */}
      {theme === "stars" && (
        <>
          {/* Background field of tiny static-drift stars */}
          <StarField w={width} h={height} frame={frame} color={accentColor} />

          {/* Far layer: 3 small slow stars */}
          {[1,2,3].map(i => (
            <DriftingStar key={`far${i}`} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* Mid layer: 4 medium stars */}
          {[4,5,6,7].map(i => (
            <DriftingStar key={`mid${i}`} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* Near layer: 3 large fast stars */}
          {[8,9,10].map(i => (
            <DriftingStar key={`near${i}`} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* 3 pairs: two stars drifting together with Y offset */}
          {[20,21,22].map(i => (
            <React.Fragment key={`pair${i}`}>
              <DriftingStar seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} yOffset={-28} sizeScale={1.0} />
              <DriftingStar seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} yOffset={32} sizeScale={0.7} />
            </React.Fragment>
          ))}
        </>
      )}

      {theme === "ocean" && (
        <>
          {/* Caustic light shafts from surface */}
          <OceanCaustics w={width} h={height} frame={frame} />

          {/* 5 drifting FLUX jellyfish, 2 size tiers */}
          {[1,2,3,4,5].map(i => (
            <DriftingJellyfish key={i} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* 3 drifting fish */}
          {[10,11,12].map(i => (
            <DriftingFish key={i} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* Rising bubbles: 18 at various sizes + speeds */}
          {Array.from({ length: 18 }, (_, i) => (
            <RisingBubble key={i} seed={i + 1} w={width} h={height} frame={frame} fps={fps} />
          ))}

          {/* Deep ocean ambient glow at bottom */}
          <div style={{
            position: "absolute", bottom: 0, left: 0, right: 0, height: "30%",
            background: "linear-gradient(0deg, rgba(0,40,80,0.5) 0%, transparent 100%)",
            pointerEvents: "none",
          }} />
        </>
      )}

      {(theme === "garden" || theme === "forest") && (
        <>
          {/* Ground, trees, bushes, plants */}
          <NightSceneBackground
            w={width} h={height} frame={frame}
            isForest={theme === "forest"} phaseOffset={phaseOffset}
          />

          {/* 22 fireflies: large glowing dots, always visible (Rule 3, 6) */}
          {Array.from({ length: 22 }, (_, i) => (
            <Firefly
              key={i} seed={i + 1}
              w={width} h={height} frame={frame} fps={fps}
              color={accentColor} phaseOffset={phaseOffset}
            />
          ))}

          {/* 20 floating petals (garden) or leaves (forest) */}
          {Array.from({ length: 20 }, (_, i) => (
            <FloatingParticle
              key={i} seed={i + 1}
              w={width} h={height} frame={frame} fps={fps}
              isForest={theme === "forest"} phaseOffset={phaseOffset}
            />
          ))}
        </>
      )}

      {theme === "rain" && (
        <>
          {/* Dark rainy-night exterior behind glass */}
          <div style={{
            position: "absolute", inset: 0,
            background: "linear-gradient(180deg, #050810 0%, #030608 100%)",
          }} />

          {/* Blurry building/tree silhouettes visible through wet glass */}
          {Array.from({ length: 5 }, (_, i) => {
            const bW = 110 + seededRand(i * 7 + phaseOffset * 3) * 130;
            const bH = height * (0.22 + seededRand(i * 11) * 0.28);
            const bX = ((seededRand(i * 13 + phaseOffset * 5) * 0.8) + 0.1) * width;
            return (
              <div key={`bld${i}`} style={{
                position: "absolute",
                left: bX - bW / 2,
                bottom: height * 0.13,
                width: bW, height: bH,
                backgroundColor: "rgba(8,12,20,0.75)",
                filter: "blur(4px)",
              }} />
            );
          })}

          {/* 65 rain drops: 2–3.5px wide, 0.28–0.58 opacity — clearly visible */}
          {Array.from({ length: 65 }, (_, i) => (
            <RainDrop key={i} seed={i + 1} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* 14 water streaks running down glass */}
          {Array.from({ length: 14 }, (_, i) => (
            <WaterStreak key={i} seed={i + 1} w={width} h={height} frame={frame} fps={fps} />
          ))}

          {/* Window sill */}
          <div style={{
            position: "absolute", bottom: "12%", left: 0, right: 0,
            height: 7, backgroundColor: "rgba(35,22,10,0.55)",
          }} />

          {/* Interior window frame panels */}
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "11%",
            background: "linear-gradient(180deg, rgba(5,3,1,0.95) 0%, transparent 100%)" }} />
          <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "13%",
            background: "linear-gradient(0deg, rgba(5,3,1,0.98) 0%, transparent 100%)" }} />
          <div style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: "8%",
            background: "linear-gradient(90deg, rgba(4,2,1,0.95) 0%, transparent 100%)" }} />
          <div style={{ position: "absolute", top: 0, bottom: 0, right: 0, width: "8%",
            background: "linear-gradient(270deg, rgba(4,2,1,0.95) 0%, transparent 100%)" }} />

          {/* Cosy interior amber glow from below — much stronger than before */}
          {/* Hue shifts per language: EN=amber, AR=warm orange, ID=golden */}
          <div style={{
            position: "absolute", bottom: 0, left: "8%", right: "8%", height: "40%",
            background: `radial-gradient(ellipse 100% 100% at 50% 100%,
              hsla(${30 + phaseOffset * 12}, 90%, 55%, ${0.20 + 0.05 * Math.sin(t * 0.7)}) 0%,
              hsla(${30 + phaseOffset * 12}, 80%, 45%, 0.08) 50%,
              transparent 100%)`,
          }} />

          {/* Warm candle/lamp spot (position shifts per language) */}
          <div style={{
            position: "absolute",
            bottom: "13%",
            left: `${12 + phaseOffset * 18}%`,
            width: 100, height: 70,
            background: `radial-gradient(ellipse at center,
              rgba(255,200,80,${0.28 + 0.08 * Math.sin(t * 1.6)}) 0%, transparent 70%)`,
          }} />
        </>
      )}

      {theme === "train" && (
        <>
          {/* ── Night sky: replaces the near-black AbsoluteFill background ── */}
          {/* EN≈cool blue, AR≈blue-violet, ID≈indigo — trainSkyHue shifts per language */}
          <div style={{
            position: "absolute", inset: 0,
            background: `linear-gradient(180deg,
              hsl(${trainSkyHue},52%,15%) 0%,
              hsl(${trainSkyHue},46%,10%) 42%,
              hsl(${trainSkyHue},38%,6%) 65%,
              hsl(${trainSkyHue},28%,3%) 100%)`,
          }} />

          {/* Stars twinkling in the sky */}
          {Array.from({ length: 80 }, (_, i) => {
            const cx = seededRand(i * 7 + 1) * width;
            const cy = seededRand(i * 11 + 1) * height * 0.50;
            const sz = 0.8 + seededRand(i * 3 + 1) * 1.8;
            const tw = 0.5 + 0.5 * Math.sin(t * (0.7 + seededRand(i * 5 + 1) * 0.5) + i * 0.7);
            return (
              <div key={`ts${i}`} style={{
                position: "absolute",
                left: cx - sz / 2, top: cy - sz / 2,
                width: sz, height: sz,
                borderRadius: "50%",
                backgroundColor: "#FFFFFF",
                opacity: tw * 0.78,
                boxShadow: sz > 1.8 ? `0 0 ${sz * 1.5}px rgba(255,255,255,0.45)` : "none",
              }} />
            );
          })}

          {/* Moon — position shifts per language (EN right → ID center-left) */}
          {(() => {
            const moonX  = width * (0.74 - phaseOffset * 0.22);
            const moonG  = 0.13 + 0.04 * Math.sin(t * 0.3);
            const mb     = 1 + 0.012 * Math.sin(t * 0.22);
            return (
              <div style={{
                position: "absolute",
                left: moonX - 55,
                top: height * 0.05,
                width: 110 * mb, height: 110 * mb,
                borderRadius: "50%",
                backgroundColor: "#FFFDD5",
                opacity: 0.90,
                boxShadow: `0 0 ${55+moonG*45}px ${28+moonG*22}px rgba(255,250,175,${moonG}), 0 0 ${110+moonG*65}px rgba(255,245,155,${moonG*0.35})`,
              }} />
            );
          })()}

          {/* Far mountains (slowest, 0.12 px/frame) */}
          {Array.from({ length: 7 }, (_, i) => {
            const speed  = 0.12;
            const mW     = width * 0.34;
            const totalW = 7 * mW;
            const initX  = phaseOffset * totalW;
            const x = ((i * mW + initX - frame * speed) % totalW + totalW) % totalW - mW;
            const mH = height * (0.22 + seededRand(i * 7 + 11) * 0.18);
            return (
              <div key={`mtn${i}`} style={{
                position: "absolute",
                left: x,
                bottom: height * 0.22,
                width: mW,
                height: mH,
                backgroundColor: `hsl(${trainSkyHue - 10},35%,6%)`,
                clipPath: "polygon(20% 100%, 50% 0%, 80% 100%)",
              }} />
            );
          })}

          {/* Far rolling hills */}
          {Array.from({ length: 6 }, (_, i) => {
            const speed  = 0.28;
            const hW     = width * 0.48;
            const totalW = 6 * hW;
            const initX  = phaseOffset * totalW;
            const x = ((i * hW + initX - frame * speed) % totalW + totalW) % totalW - hW;
            const hH = height * (0.14 + seededRand(i * 11 + 5) * 0.10);
            return (
              <div key={`hl${i}`} style={{
                position: "absolute",
                left: x,
                bottom: height * 0.22,
                width: hW,
                height: hH,
                borderRadius: "60% 60% 0 0",
                backgroundColor: `hsl(${trainSkyHue - 5},32%,5%)`,
              }} />
            );
          })}

          {/* Horizon glow (moonlight on fields) */}
          <div style={{
            position: "absolute",
            left: 0, right: 0,
            bottom: height * 0.22,
            height: 50,
            background: `linear-gradient(0deg, hsl(${trainSkyHue+15},40%,8%) 0%, transparent 100%)`,
          }} />

          {/* Mid trees: pines and round trees alternating */}
          {Array.from({ length: 18 }, (_, i) => {
            const speed   = 1.6;
            const gap     = 90 + seededRand(i * 7 + 3) * 85;
            const totalW  = 18 * 115;
            const initX   = phaseOffset * totalW;
            const x = ((i * gap + initX - frame * speed) % totalW + totalW) % totalW - gap;
            const tH      = height * (0.15 + seededRand(i * 11 + 7) * 0.14);
            const tW      = 26 + seededRand(i * 13 + 5) * 36;
            const isPine  = seededRand(i * 17 + 3) > 0.42;
            return (
              <React.Fragment key={`tr${i}`}>
                <div style={{
                  position: "absolute",
                  left: x + tW * 0.43, bottom: height * 0.22,
                  width: tW * 0.14, height: tH * 0.44,
                  backgroundColor: "#060A0F",
                }} />
                {isPine ? (
                  <div style={{
                    position: "absolute",
                    left: x, bottom: height * 0.22 + tH * 0.36,
                    width: tW, height: tH * 0.74,
                    backgroundColor: "#040910",
                    clipPath: "polygon(50% 0%, 5% 100%, 95% 100%)",
                  }} />
                ) : (
                  <div style={{
                    position: "absolute",
                    left: x, bottom: height * 0.22 + tH * 0.30,
                    width: tW, height: tH * 0.82,
                    borderRadius: "50%",
                    backgroundColor: "#050A10",
                  }} />
                )}
              </React.Fragment>
            );
          })}

          {/* Telegraph poles (near, fast: 5.5 px/frame) + cross-arm + wire */}
          {Array.from({ length: 9 }, (_, i) => {
            const speed  = 5.5;
            const gap    = 260;
            const totalW = 9 * gap;
            const initX  = phaseOffset * totalW;
            const x = ((i * gap + initX - frame * speed) % totalW + totalW) % totalW - gap;
            const pH = height * 0.45;
            return (
              <React.Fragment key={`pl${i}`}>
                <div style={{
                  position: "absolute",
                  left: x, bottom: height * 0.22,
                  width: 6, height: pH,
                  backgroundColor: "#1E1810",
                }} />
                <div style={{
                  position: "absolute",
                  left: x - 22, bottom: height * 0.22 + pH - 20,
                  width: 48, height: 5,
                  backgroundColor: "#181410",
                }} />
                <div style={{
                  position: "absolute",
                  left: x, bottom: height * 0.22 + pH - 9,
                  width: gap, height: 2,
                  backgroundColor: "#16120E",
                }} />
              </React.Fragment>
            );
          })}

          {/* Ground (track bed) */}
          <div style={{
            position: "absolute",
            bottom: 0, left: 0, right: 0,
            height: height * 0.23,
            background: `linear-gradient(0deg, #010305 0%, hsl(${trainSkyHue},22%,4%) 100%)`,
          }} />

          {/* Converging rails (perspective) */}
          {([-1, 1] as const).map(side => (
            <div key={`rl${side}`} style={{
              position: "absolute",
              left: width * 0.5 + side * (width * 0.055 + height * 0.20 * 0.22),
              bottom: 0,
              width: 4,
              height: height * 0.23,
              background: "linear-gradient(0deg, rgba(110,90,55,0.75) 0%, rgba(110,90,55,0.2) 100%)",
            }} />
          ))}

          {/* Distant town + farmhouse lights — warm/cool mix varies by language */}
          {Array.from({ length: 10 }, (_, i) => {
            const speed  = 0.5;
            const gap    = width * 0.22 + seededRand(i * 7 + 9) * width * 0.15;
            const totalW = 10 * (width * 0.28);
            const initX  = phaseOffset * totalW;
            const x = ((i * gap + initX - frame * speed) % totalW + totalW) % totalW - gap;
            const flicker = 0.5 + 0.5 * Math.sin(t * (0.9 + seededRand(i * 5 + 1) * 0.6) + i * 1.9);
            const y = height * 0.28 + seededRand(i * 7 + 3) * height * 0.22;
            const sz = 3 + seededRand(i * 11 + 5) * 6;
            const isWarm = seededRand(i * 13 + phaseOffset * 7) > 0.45;
            const col  = isWarm ? `rgba(255,185,55,${0.75*flicker})` : `rgba(180,210,255,${0.55*flicker})`;
            const glow = isWarm ? `rgba(255,160,40,${0.35*flicker})` : `rgba(160,200,255,${0.3*flicker})`;
            return (
              <div key={`lgt${i}`} style={{
                position: "absolute",
                left: x, top: y,
                width: sz, height: sz * 0.65,
                borderRadius: "50%",
                backgroundColor: col,
                boxShadow: `0 0 ${sz * 2.5 * flicker}px ${sz * 1.2 * flicker}px ${glow}`,
              }} />
            );
          })}

          {/* ── Interior window frame panels ── */}
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "14%",
            background: "linear-gradient(180deg, rgba(5,3,1,1) 0%, rgba(5,3,1,0.82) 60%, transparent 100%)" }} />
          <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "20%",
            background: "linear-gradient(0deg, rgba(5,3,1,1) 0%, rgba(5,3,1,0.82) 55%, transparent 100%)" }} />
          <div style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: "10%",
            background: "linear-gradient(90deg, rgba(4,2,1,0.98) 0%, rgba(12,8,3,0.55) 70%, transparent 100%)" }} />
          <div style={{ position: "absolute", top: 0, bottom: 0, right: 0, width: "10%",
            background: "linear-gradient(270deg, rgba(4,2,1,0.98) 0%, rgba(12,8,3,0.55) 70%, transparent 100%)" }} />

          {/* Warm amber lamp glow from interior below */}
          <div style={{
            position: "absolute", bottom: 0, left: "10%", right: "10%", height: "28%",
            background: `radial-gradient(ellipse 90% 100% at 50% 100%, rgba(255,135,25,${0.09+0.025*Math.sin(t*0.5)}) 0%, transparent 100%)`,
          }} />

          {/* Subtle rhythmic screen flash = train wheel bump feel */}
          <div style={{
            position: "absolute", inset: 0,
            opacity: 0.018 * Math.abs(Math.sin(t * 16.5)),
            backgroundColor: "#F0EDE5",
            pointerEvents: "none",
          }} />
        </>
      )}

      {/* Seamless gradient fade for loop */}
      <div style={{
        position: "absolute",
        inset: 0,
        background: `radial-gradient(ellipse 80% 50% at 50% 100%, rgba(0,0,0,0.4) 0%, transparent 60%)`,
        pointerEvents: "none",
      }} />
    </AbsoluteFill>
  );
};
