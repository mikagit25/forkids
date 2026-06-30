/**
 * NatureCalm — 5-minute calm nature scene for babies.
 * 3-layer BackgroundParallax: sky (slow) / hills (medium) / grass (fast).
 * Math.sin cloud bobbing, sun pulse, bird arcs. No text, universal content.
 * Rendered as a loop, extended to 30-60 min via FFmpeg.
 *
 * Themes: meadow | sunset | night | underwater
 */
import React from "react";
import {
  AbsoluteFill, Audio, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { BackgroundParallax, ParallaxLayer } from "./components/BackgroundParallax";

export interface NatureCalmProps {
  theme: "meadow" | "sunset" | "night" | "underwater";
  musicFile?: string;
  phaseOffset?: number;
}

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ── Cloud ─────────────────────────────────────────────────────────────────────
const Cloud: React.FC<{
  x: number; y: number; w: number; frame: number; phase: number; color: string; opacity: number;
}> = ({ x, y, w, frame, phase, color, opacity }) => {
  const t = frame / 30;
  const drift = t * 18 + phase * 200;           // slow rightward drift
  const bob   = Math.sin(t * 0.4 + phase) * 14;
  const wrappedX = ((x + drift) % (1920 + w)) - w;

  return (
    <div style={{
      position: "absolute",
      left: wrappedX,
      top: y + bob,
      width: w,
      height: w * 0.45,
      borderRadius: "50% 50% 40% 40%",
      backgroundColor: color,
      opacity,
      boxShadow: `0 8px 24px ${color}55`,
      willChange: "transform",
    }} />
  );
};

// ── Bird arc (simple V shape, flies across) ───────────────────────────────────
const Bird: React.FC<{
  startX: number; y: number; frame: number; startF: number; color: string;
}> = ({ startX, y, frame, startF, color }) => {
  const t = (frame - startF) / 30;
  if (t < 0) return null;
  const x = startX + t * 90;
  if (x > 2100) return null;
  const bob = Math.sin(t * 5) * 10;

  return (
    <div style={{
      position: "absolute",
      left: x,
      top: y + bob,
      fontSize: 32,
      opacity: 0.75,
      color,
      userSelect: "none",
    }}>
      ︿
    </div>
  );
};

// ── Sun / Moon ────────────────────────────────────────────────────────────────
const CelestialBody: React.FC<{
  x: number; y: number; r: number; color: string; glowColor: string; frame: number;
}> = ({ x, y, r, color, glowColor, frame }) => {
  const t = frame / 30;
  const pulse = 1 + Math.sin(t * 0.5) * 0.04;
  const sc = spring({ frame, fps: 30, config: { damping: 18, stiffness: 60 }, durationInFrames: 90 });
  const scaleIn = interpolate(sc, [0, 1], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div style={{
      position: "absolute",
      left: x - r,
      top: y - r,
      width: r * 2,
      height: r * 2,
      borderRadius: "50%",
      backgroundColor: color,
      transform: `scale(${pulse * scaleIn})`,
      boxShadow: `0 0 ${r * 1.5}px ${r * 0.5}px ${glowColor}`,
    }} />
  );
};

// ── Theme configs ─────────────────────────────────────────────────────────────
const THEMES = {
  meadow: {
    layers: [
      { background: "linear-gradient(180deg, #87CEEB 0%, #b0e2ff 60%, #e8f5e9 100%)", speed: 0.04, opacity: 1 },
      { background: "linear-gradient(180deg, transparent 50%, #a5d6a7 70%, #66bb6a 100%)", speed: 0.18, opacity: 0.9 },
      { background: "linear-gradient(180deg, transparent 70%, #388e3c 88%, #2e7d32 100%)", speed: 0.45, opacity: 1 },
    ] as ParallaxLayer[],
    skyColor: "#87CEEB",
    sunColor: "#FFF9C4",
    sunGlow: "#FFE082",
    celestialPos: { x: 1500, y: 160, r: 88 },
    cloudColor: "rgba(255,255,255,0.9)",
    birdColor: "#555",
    musicDefault: "Gymnopedie No 1.mp3",
  },
  sunset: {
    layers: [
      { background: "linear-gradient(180deg, #FF6B35 0%, #FF8C61 30%, #FFB347 60%, #FFD700 100%)", speed: 0.03, opacity: 1 },
      { background: "linear-gradient(180deg, transparent 55%, #8d5524 75%, #6d4c41 100%)", speed: 0.15, opacity: 0.85 },
      { background: "linear-gradient(180deg, transparent 72%, #4e342e 88%, #3e2723 100%)", speed: 0.38, opacity: 1 },
    ] as ParallaxLayer[],
    skyColor: "#FF6B35",
    sunColor: "#FFD700",
    sunGlow: "#FF8C00",
    celestialPos: { x: 960, y: 320, r: 110 },
    cloudColor: "rgba(255,200,150,0.6)",
    birdColor: "#333",
    musicDefault: "Carefree.mp3",
  },
  night: {
    layers: [
      { background: "linear-gradient(180deg, #0d1b2a 0%, #1a2744 50%, #0d47a1 100%)", speed: 0.02, opacity: 1 },
      { background: "linear-gradient(180deg, transparent 60%, #263238 80%, #1c313a 100%)", speed: 0.12, opacity: 0.9 },
      { background: "linear-gradient(180deg, transparent 75%, #1b5e20 90%, #1b5e20 100%)", speed: 0.30, opacity: 1 },
    ] as ParallaxLayer[],
    skyColor: "#0d1b2a",
    sunColor: "#fffde7",
    sunGlow: "#fff9c4",
    celestialPos: { x: 1400, y: 180, r: 72 },
    cloudColor: "rgba(100,120,180,0.4)",
    birdColor: "#90caf9",
    musicDefault: "Gymnopedie No 1.mp3",
  },
  underwater: {
    layers: [
      { background: "linear-gradient(180deg, #006064 0%, #00838f 40%, #0097a7 100%)", speed: 0.05, opacity: 1 },
      { background: "radial-gradient(ellipse at 30% 80%, #00bcd480 0%, transparent 60%)", speed: 0.20, bobAmplitude: 20, bobFreq: 0.15, opacity: 0.7 },
      { background: "radial-gradient(ellipse at 70% 90%, #4db6ac60 0%, transparent 50%)", speed: 0.40, bobAmplitude: 15, bobFreq: 0.22, opacity: 0.8 },
    ] as ParallaxLayer[],
    skyColor: "#006064",
    sunColor: "#e0f7fa",
    sunGlow: "#80deea",
    celestialPos: { x: 960, y: 120, r: 100 },
    cloudColor: "rgba(178,235,242,0.35)",
    birdColor: "#e0f7fa",
    musicDefault: "Gymnopedie No 1.mp3",
  },
};

// ── Main composition ──────────────────────────────────────────────────────────
export const NatureCalm: React.FC<NatureCalmProps> = ({
  theme = "meadow",
  musicFile,
  phaseOffset = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  const cfg = THEMES[theme];
  const music = musicFile ?? cfg.musicDefault;

  const fadeIn = interpolate(frame, [0, fps * 1.5], [0, 1], { extrapolateRight: "clamp" });

  const clouds = Array.from({ length: 6 }, (_, i) => ({
    x: seededRand(i * 7) * width,
    y: 60 + seededRand(i * 11) * 200,
    w: 180 + seededRand(i * 3) * 240,
    phase: seededRand(i * 13) * Math.PI * 2 + phaseOffset * Math.PI * 2,
  }));

  const birds = Array.from({ length: 4 }, (_, i) => ({
    startX: -80,
    y: 100 + seededRand(i * 9) * 200,
    startF: i * fps * 18 + Math.round(seededRand(i * 5) * fps * 10),
  }));

  return (
    <AbsoluteFill style={{ overflow: "hidden", opacity: fadeIn }}>
      {music && (
        <Audio src={staticFile(`music/${music}`)} volume={0.14} loop />
      )}

      {/* Multi-layer parallax background */}
      <BackgroundParallax layers={cfg.layers} scrollRange={80} cycleSec={60} />

      {/* Celestial body (sun / moon) */}
      <CelestialBody
        x={cfg.celestialPos.x} y={cfg.celestialPos.y} r={cfg.celestialPos.r}
        color={cfg.sunColor} glowColor={cfg.sunGlow} frame={frame}
      />

      {/* Clouds (or underwater light shafts for "underwater" theme) */}
      {clouds.map((c, i) => (
        <Cloud key={i}
          x={c.x} y={c.y} w={c.w}
          frame={frame} phase={c.phase}
          color={cfg.cloudColor} opacity={theme === "underwater" ? 0.25 : 0.88}
        />
      ))}

      {/* Underwater: bubble columns */}
      {theme === "underwater" && Array.from({ length: 14 }, (_, i) => {
        const r = seededRand;
        const bx = r(i * 17) * width;
        const speed = 40 + r(i * 5) * 60;
        const size = 6 + r(i * 3) * 18;
        const phase = r(i * 11) * Math.PI * 2;
        const by = ((height + 60) - (t * speed + phase * 40)) % (height + 60);
        const op = 0.3 + Math.sin(t * 0.8 + phase) * 0.2;
        return (
          <div key={i} style={{
            position: "absolute",
            left: bx + Math.sin(t * 0.5 + phase) * 20,
            top: by,
            width: size, height: size,
            borderRadius: "50%",
            border: "2px solid rgba(178,235,242,0.7)",
            opacity: op,
          }} />
        );
      })}

      {/* Night: stars */}
      {theme === "night" && Array.from({ length: 70 }, (_, i) => {
        const r = seededRand;
        const sx = r(i * 7) * width;
        const sy = r(i * 11) * (height * 0.55);
        const sz = 1.5 + r(i * 3) * 3;
        const phase = r(i * 13) * Math.PI * 2 + phaseOffset * Math.PI * 2;
        const op = 0.4 + Math.sin(t * 0.8 + phase) * 0.35;
        return (
          <div key={i} style={{
            position: "absolute",
            left: sx, top: sy,
            width: sz, height: sz,
            borderRadius: "50%",
            backgroundColor: "#fff",
            opacity: op,
            boxShadow: `0 0 ${sz * 2}px rgba(255,255,255,0.8)`,
          }} />
        );
      })}

      {/* Birds */}
      {theme !== "underwater" && birds.map((b, i) => (
        <Bird key={i}
          startX={b.startX} y={b.y}
          frame={frame} startF={b.startF}
          color={cfg.birdColor}
        />
      ))}

      {/* Bottom vignette for depth */}
      <div style={{
        position: "absolute",
        inset: 0,
        background: "linear-gradient(to top, rgba(0,0,0,0.25) 0%, transparent 35%)",
        pointerEvents: "none",
      }} />
    </AbsoluteFill>
  );
};
