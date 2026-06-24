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

// ── Jellyfish (ocean theme) ──────────────────────────────────────────────────
const Jellyfish: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number; color: string;
}> = ({ seed, w, h, frame, fps, color }) => {
  const r = seededRand;
  const baseX = r(seed * 7) * w * 0.8 + w * 0.1;
  const baseY = r(seed * 11) * h * 0.6 + h * 0.2;
  const sz    = 40 + r(seed * 3) * 60;
  const pulseSpeed = 0.5 + r(seed * 5) * 0.3;
  const pulse = 1 + 0.15 * Math.sin(frame * pulseSpeed * 0.05);
  const swayX = Math.sin(frame * 0.008 + r(seed * 13) * 6) * 30;
  const swayY = Math.cos(frame * 0.006 + r(seed * 17) * 4) * 20;
  const opacity = 0.2 + r(seed * 19) * 0.25;
  return (
    <div style={{
      position: "absolute",
      left: baseX + swayX - sz * pulse / 2,
      top:  baseY + swayY - sz * pulse / 2,
      width:  sz * pulse,
      height: sz * pulse * 0.7,
      borderRadius: "50% 50% 0 0",
      backgroundColor: color,
      opacity,
      boxShadow: `0 0 ${sz * 0.5}px ${color}`,
    }} />
  );
};

// ── Firefly ──────────────────────────────────────────────────────────────────
const Firefly: React.FC<{
  seed: number; w: number; h: number; frame: number; color: string;
}> = ({ seed, w, h, frame, color }) => {
  const r = seededRand;
  const baseX = r(seed * 7) * w;
  const baseY = h * 0.4 + r(seed * 11) * h * 0.5;
  const driftX = Math.sin(frame * 0.012 + r(seed * 13) * 6) * 60;
  const driftY = Math.cos(frame * 0.009 + r(seed * 17) * 4) * 40;
  const glowCycle = 0.3 + 0.7 * Math.pow(Math.sin(frame * 0.04 + r(seed * 5) * Math.PI), 2);
  return (
    <div style={{
      position: "absolute",
      left: baseX + driftX - 3,
      top:  baseY + driftY - 3,
      width: 6, height: 6,
      borderRadius: "50%",
      backgroundColor: color,
      opacity: glowCycle * 0.9,
      boxShadow: `0 0 ${8 * glowCycle}px ${4 * glowCycle}px ${color}`,
    }} />
  );
};

// ── Rain drop ────────────────────────────────────────────────────────────────
const RainDrop: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number;
}> = ({ seed, w, h, frame, fps }) => {
  const r = seededRand;
  const x = r(seed * 7) * w;
  const speed = 3 + r(seed * 11) * 4; // px per frame
  const startY = -(20 + r(seed * 3) * 30);
  const offset = Math.round(r(seed * 13) * fps * 5);
  const localFrame = (frame + offset) % (fps * 5);
  const y = startY + localFrame * speed;
  if (y > h + 20) return null;
  const opacity = 0.05 + r(seed * 17) * 0.12;
  return (
    <div style={{
      position: "absolute",
      left: x,
      top: y,
      width: 1,
      height: 12 + r(seed * 5) * 8,
      backgroundColor: "#AACCEE",
      opacity,
      transform: "rotate(10deg)",
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

      {/* Moon visible in all themes */}
      <Moon frame={frame} w={width} />

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
          {Array.from({ length: 6 }, (_, i) => (
            <Jellyfish key={i} seed={i + 1} w={width} h={height} frame={frame} fps={fps} color={accentColor} />
          ))}
        </>
      )}

      {(theme === "garden" || theme === "forest") && (
        <>
          {Array.from({ length: PARTICLE_COUNT }, (_, i) => (
            <Firefly key={i} seed={i + 1} w={width} h={height} frame={frame} color={accentColor} />
          ))}
        </>
      )}

      {theme === "rain" && (
        <>
          {Array.from({ length: PARTICLE_COUNT }, (_, i) => (
            <RainDrop key={i} seed={i + 1} w={width} h={height} frame={frame} fps={fps} />
          ))}
          {/* Cosy window glow */}
          <div style={{
            position: "absolute",
            right: "8%", bottom: "10%",
            width: 200, height: 250,
            borderRadius: 8,
            background: `radial-gradient(ellipse at center, rgba(255,200,100,0.12) 0%, transparent 70%)`,
          }} />
        </>
      )}

      {theme === "train" && (
        <>
          {/* Train window lights scrolling */}
          {Array.from({ length: 4 }, (_, i) => {
            const speed = 0.3;
            const startX = i * 280;
            const x = (startX - frame * speed) % (width + 280);
            return (
              <div key={i} style={{
                position: "absolute",
                left: x - 280, bottom: "25%",
                width: 220, height: 140,
                border: "3px solid rgba(180,120,50,0.3)",
                borderRadius: 4,
                background: "rgba(255,190,80,0.06)",
              }} />
            );
          })}
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
