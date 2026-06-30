/**
 * SensoryLoop — 5-minute calming sensory loop for babies/toddlers.
 * Rendered once, extended to 1-2h via FFmpeg.
 * No text, no faces — universal EN/AR/ID content.
 * Uses BackgroundParallax + spring() entry + Math.sin organic float.
 *
 * Themes: bubbles, bloom, ocean, galaxy
 */
import React from "react";
import {
  AbsoluteFill, Audio, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { BackgroundParallax, ParallaxLayer } from "./components/BackgroundParallax";

export interface SensoryLoopProps {
  theme: "bubbles" | "bloom" | "ocean" | "galaxy";
  musicFile?: string;
  phaseOffset?: number; // 0..1, offsets animation phase for EN/AR/ID
}

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ── Floating orb / bubble ────────────────────────────────────────────────────
const FloatingOrb: React.FC<{
  cx: number; cy: number; r: number;
  color: string; frame: number; phase: number; speed: number;
  opacity: number;
}> = ({ cx, cy, r, color, frame, phase, speed, opacity }) => {
  const t = frame / 30;
  const x = cx + Math.sin(t * speed + phase) * 60;
  const y = cy + Math.cos(t * speed * 0.7 + phase * 1.3) * 40;
  const sc = 0.85 + Math.sin(t * speed * 0.4 + phase) * 0.15;

  return (
    <div style={{
      position: "absolute",
      left: x - r,
      top: y - r,
      width: r * 2,
      height: r * 2,
      borderRadius: "50%",
      background: `radial-gradient(circle at 35% 35%, white 0%, ${color} 60%, transparent 100%)`,
      opacity,
      transform: `scale(${sc})`,
      willChange: "transform",
    }} />
  );
};

// ── Bloom petal ──────────────────────────────────────────────────────────────
const Petal: React.FC<{
  cx: number; cy: number; angle: number; r: number;
  color: string; frame: number; phase: number;
}> = ({ cx, cy, angle, r, color, frame, phase }) => {
  const t = frame / 30;
  const pulse = 1 + Math.sin(t * 0.8 + phase) * 0.12;
  const rad = (angle * Math.PI) / 180;
  const px = cx + Math.cos(rad) * r * pulse;
  const py = cy + Math.sin(rad) * r * pulse;
  const sz = r * 0.55;

  return (
    <div style={{
      position: "absolute",
      left: px - sz,
      top: py - sz,
      width: sz * 2,
      height: sz * 2,
      borderRadius: "50% 50% 50% 50% / 60% 60% 40% 40%",
      background: `radial-gradient(circle, white 0%, ${color} 70%)`,
      opacity: 0.85,
      transform: `rotate(${angle}deg) scale(${pulse})`,
      willChange: "transform",
    }} />
  );
};

// ── Galaxy star ──────────────────────────────────────────────────────────────
const GalaxyStar: React.FC<{
  x: number; y: number; sz: number; frame: number; phase: number; color: string;
}> = ({ x, y, sz, frame, phase, color }) => {
  const t = frame / 30;
  const op = 0.3 + Math.sin(t * 1.1 + phase) * 0.35;
  const sc = 0.7 + Math.sin(t * 0.6 + phase) * 0.3;

  return (
    <div style={{
      position: "absolute",
      left: x - sz / 2,
      top: y - sz / 2,
      width: sz,
      height: sz,
      borderRadius: "50%",
      backgroundColor: color,
      opacity: op,
      transform: `scale(${sc})`,
      boxShadow: `0 0 ${sz * 2}px ${color}`,
    }} />
  );
};

// ── Theme configs ─────────────────────────────────────────────────────────────
const THEMES = {
  bubbles: {
    layers: [
      { background: "linear-gradient(180deg, #e0f7fa 0%, #b2ebf2 50%, #80deea 100%)", speed: 0.03, opacity: 1 },
      { background: "linear-gradient(135deg, #b3e5fc44 0%, transparent 100%)", speed: 0.12, opacity: 0.6 },
      { background: "radial-gradient(ellipse at 30% 70%, #e1f5fe66 0%, transparent 70%)", speed: 0.25, opacity: 0.5 },
    ] as ParallaxLayer[],
    colors: ["#81d4fa","#4fc3f7","#29b6f6","#ce93d8","#f48fb1","#80cbc4","#a5d6a7"],
    count: 18,
  },
  bloom: {
    layers: [
      { background: "linear-gradient(180deg, #fce4ec 0%, #f8bbd0 40%, #f48fb1 100%)", speed: 0.02, opacity: 1 },
      { background: "linear-gradient(135deg, #fff9c444 0%, transparent 100%)", speed: 0.10, opacity: 0.7 },
      { background: "radial-gradient(circle at 70% 30%, #e8f5e966 0%, transparent 60%)", speed: 0.18, opacity: 0.5 },
    ] as ParallaxLayer[],
    colors: ["#f48fb1","#ce93d8","#ffcc80","#a5d6a7","#80deea","#ef9a9a","#fff59d"],
    count: 5,
  },
  ocean: {
    layers: [
      { background: "linear-gradient(180deg, #1a237e 0%, #283593 40%, #1565c0 100%)", speed: 0.04, opacity: 1 },
      { background: "linear-gradient(180deg, transparent 60%, #0d47a166 100%)", speed: 0.15, opacity: 0.8 },
      { background: "radial-gradient(ellipse at 50% 0%, #42a5f544 0%, transparent 60%)", speed: 0.30, bobAmplitude: 12, bobFreq: 0.2, opacity: 0.5 },
    ] as ParallaxLayer[],
    colors: ["#4fc3f7","#29b6f6","#81d4fa","#e0f7fa","#b2ebf2","#4dd0e1","#80deea"],
    count: 22,
  },
  galaxy: {
    layers: [
      { background: "linear-gradient(135deg, #0d0221 0%, #1a0533 50%, #0d1b2a 100%)", speed: 0.01, opacity: 1 },
      { background: "radial-gradient(ellipse at 20% 50%, #6a0dad22 0%, transparent 60%)", speed: 0.08, opacity: 0.9 },
      { background: "radial-gradient(ellipse at 80% 30%, #1a237e33 0%, transparent 50%)", speed: 0.18, opacity: 0.7 },
    ] as ParallaxLayer[],
    colors: ["#e040fb","#7c4dff","#40c4ff","#69f0ae","#ffd740","#ff6d00","#f50057"],
    count: 80,
  },
};

// ── Main composition ──────────────────────────────────────────────────────────
export const SensoryLoop: React.FC<SensoryLoopProps> = ({
  theme = "bubbles",
  musicFile = "Gymnopedie No 1.mp3",
  phaseOffset = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  const cfg = THEMES[theme];

  // Spring-in for the whole scene (first 2s)
  const sceneSpring = spring({
    frame,
    fps,
    config: { damping: 20, stiffness: 60 },
    durationInFrames: fps * 2,
  });
  const sceneOpacity = interpolate(sceneSpring, [0, 1], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ overflow: "hidden", opacity: sceneOpacity }}>
      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={0.18} loop />
      )}

      {/* Parallax background layers */}
      <BackgroundParallax layers={cfg.layers} scrollRange={120} cycleSec={50} />

      {/* Theme-specific elements */}
      {(theme === "bubbles" || theme === "ocean") && (
        <>
          {Array.from({ length: cfg.count }, (_, i) => {
            const r = seededRand;
            const cx = r(i * 7) * width;
            const cy = r(i * 11) * height;
            const radius = 20 + r(i * 3) * 90;
            const color = cfg.colors[i % cfg.colors.length];
            const phase = r(i * 13) * Math.PI * 2 + phaseOffset * Math.PI * 2;
            const speed = 0.3 + r(i * 5) * 0.7;
            const opacity = 0.25 + r(i * 17) * 0.45;

            // Spring-in staggered
            const entrySpring = spring({
              frame: frame - i * 4,
              fps,
              config: { damping: 16, stiffness: 80 },
              durationInFrames: fps * 1.5,
            });
            const entryOp = interpolate(entrySpring, [0, 1], [0, 1], { extrapolateRight: "clamp" });

            return (
              <FloatingOrb
                key={i}
                cx={cx} cy={cy} r={radius}
                color={color} frame={frame} phase={phase} speed={speed}
                opacity={opacity * entryOp}
              />
            );
          })}
        </>
      )}

      {theme === "bloom" && (
        <>
          {Array.from({ length: cfg.count }, (_, fi) => {
            const r = seededRand;
            const cx = (0.15 + fi * 0.17) * width;
            const cy = (0.3 + r(fi * 9) * 0.4) * height;
            const radius = 80 + r(fi * 3) * 60;
            const color = cfg.colors[fi % cfg.colors.length];
            const phase = r(fi * 13) * Math.PI * 2 + phaseOffset * Math.PI * 2;

            const entrySpring = spring({
              frame: frame - fi * 15,
              fps,
              config: { damping: 12, stiffness: 70 },
              durationInFrames: fps * 2,
            });
            const sc = interpolate(entrySpring, [0, 1], [0, 1], { extrapolateRight: "clamp" });

            return (
              <div key={fi} style={{
                position: "absolute",
                left: cx - radius,
                top: cy - radius,
                transform: `scale(${sc})`,
              }}>
                {/* Center */}
                <FloatingOrb cx={radius} cy={radius} r={radius * 0.28}
                  color="#fff" frame={frame} phase={phase} speed={0.5} opacity={0.9} />
                {/* Petals */}
                {Array.from({ length: 6 }, (_, pi) => (
                  <Petal key={pi}
                    cx={radius} cy={radius}
                    angle={pi * 60}
                    r={radius * 0.72}
                    color={color}
                    frame={frame}
                    phase={phase + pi * 0.5}
                  />
                ))}
              </div>
            );
          })}
        </>
      )}

      {theme === "galaxy" && (
        <>
          {Array.from({ length: cfg.count }, (_, i) => {
            const r = seededRand;
            const x = r(i * 7) * width;
            const y = r(i * 11) * height;
            const sz = 2 + r(i * 3) * 12;
            const color = cfg.colors[i % cfg.colors.length];
            const phase = r(i * 13) * Math.PI * 2 + phaseOffset * Math.PI * 2;

            return (
              <GalaxyStar key={i} x={x} y={y} sz={sz}
                frame={frame} phase={phase} color={color} />
            );
          })}
        </>
      )}

      {/* Slow color-shift vignette overlay */}
      <div style={{
        position: "absolute",
        inset: 0,
        background: "radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.35) 100%)",
        pointerEvents: "none",
      }} />
    </AbsoluteFill>
  );
};
