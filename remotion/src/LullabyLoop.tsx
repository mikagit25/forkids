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
}

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ── Star particle ────────────────────────────────────────────────────────────
const StarParticle: React.FC<{
  seed: number; w: number; h: number; color: string; frame: number;
}> = ({ seed, w, h, color, frame }) => {
  const r  = seededRand;
  const cx = r(seed * 7) * w;
  const cy = r(seed * 11) * h * 0.7;
  const sz = 1.5 + r(seed * 3) * 4;
  const twinkleSpeed = 0.3 + r(seed * 5) * 0.4;
  const twinklePhase = r(seed * 13) * Math.PI * 2;
  const opacity = 0.15 + r(seed * 17) * 0.5;
  const brightness = opacity * (0.7 + 0.3 * Math.sin(frame * twinkleSpeed * 0.05 + twinklePhase));
  return (
    <div style={{
      position: "absolute",
      left: cx - sz / 2,
      top:  cy - sz / 2,
      width: sz, height: sz,
      borderRadius: "50%",
      backgroundColor: color,
      opacity: brightness,
      boxShadow: brightness > 0.3 ? `0 0 ${sz * 2}px ${color}` : "none",
    }} />
  );
};

// ── Shooting star ────────────────────────────────────────────────────────────
const ShootingStar: React.FC<{
  seed: number; w: number; h: number; frame: number; cycleSec: number; fps: number;
}> = ({ seed, w, h, frame, cycleSec, fps }) => {
  const r = seededRand;
  const totalFrames = cycleSec * fps;
  const offset = Math.round(r(seed * 19) * totalFrames);
  const localFrame = (frame + offset) % totalFrames;
  const active = localFrame < fps * 2;
  if (!active) return null;
  const progress = localFrame / (fps * 2);
  const startX = r(seed * 23) * w;
  const startY = r(seed * 29) * h * 0.5;
  const len = 80 + r(seed * 31) * 120;
  const x = startX + progress * len;
  const y = startY + progress * len * 0.4;
  const opacity = Math.sin(progress * Math.PI);
  return (
    <div style={{
      position: "absolute",
      left: x, top: y,
      width: len * 0.6, height: 1.5,
      background: `linear-gradient(90deg, rgba(255,255,255,${opacity}) 0%, transparent 100%)`,
      transform: `rotate(25deg)`,
      transformOrigin: "left center",
    }} />
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
  const glow = 0.12 + 0.04 * Math.sin(frame * 0.015);
  return (
    <div style={{
      position: "absolute",
      right: w * 0.1,
      top: "8%",
      width: 70, height: 70,
      borderRadius: "50%",
      backgroundColor: "#FFFFCC",
      opacity: 0.6,
      boxShadow: `0 0 ${40 + glow * 30}px ${20 + glow * 20}px rgba(255,255,200,${glow})`,
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
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const PARTICLE_COUNT = theme === "stars" ? 60 : theme === "rain" ? 40 : 12;

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
          {Array.from({ length: PARTICLE_COUNT }, (_, i) => (
            <StarParticle key={i} seed={i + 1} w={width} h={height} color={accentColor} frame={frame} />
          ))}
          {Array.from({ length: 3 }, (_, i) => (
            <ShootingStar key={i} seed={i + 1} w={width} h={height} frame={frame} cycleSec={40} fps={fps} />
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
