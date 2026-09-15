/**
 * SensoryBlobLoop — 5-min meditative goo/metaball animation for toddlers 0+.
 *
 * Dark deep-blue/purple gradient background. 5 coloured blobs morph and
 * merge via SVG goo filter (feGaussianBlur + feColorMatrix metaball trick).
 *
 * Seamless loop guarantee: every position/size function is sin/cos with an
 * integer number of cycles in LOOP_FRAMES=9000. Frame 0 === frame 9000
 * in every dimension → clean FFmpeg -stream_loop with NO re-render.
 *
 * Music: our own Suno AI tracks (v2 instrumentals). Kevin MacLeod NOT used.
 * No text → one render covers EN + AR.
 */
import React from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// 5 min × 60 s × 30 fps = 9000.  All animation periods must divide 9000.
const LOOP_FRAMES = 9_000;

// ── Seamless periodic helpers ─────────────────────────────────────────────────
// loopSin completes exactly n full cycles over LOOP_FRAMES.
// Proof: at frame=9000, sin(2π·n·9000/9000 + φ) = sin(2π·n + φ) = sin(φ). ✓
function loopSin(f: number, n: number, phase = 0) {
  return Math.sin((2 * Math.PI * n * f) / LOOP_FRAMES + phase);
}
function loopCos(f: number, n: number, phase = 0) {
  return Math.cos((2 * Math.PI * n * f) / LOOP_FRAMES + phase);
}

// ── Blob definitions ──────────────────────────────────────────────────────────
// cx/cy = centre position (px).  r = base radius.
// xA/yA = drift amplitude.  xN/yN = cycle count over LOOP_FRAMES.
// rA = radius pulse amplitude.  rN = cycle count.  xP/yP/rP = phase offset.
// All N values must divide 9000 (checked: 2,3,4,5,6,10,12 all divide 9000).
const BLOBS = [
  { cx: 680,  cy: 390, r: 170, xA: 190, xN: 3, xP: 0,                 yA: 140, yN: 2,  yP: Math.PI / 3,          rA: 40, rN: 5,  rP: 0,   color: "#FF2D78" },
  { cx: 1220, cy: 340, r: 150, xA: 250, xN: 2, xP: Math.PI / 2,       yA: 200, yN: 3,  yP: Math.PI / 4,          rA: 45, rN: 10, rP: 1.1, color: "#00E5FF" },
  { cx: 960,  cy: 610, r: 190, xA: 160, xN: 4, xP: (2*Math.PI) / 3,   yA: 220, yN: 2,  yP: Math.PI / 6,          rA: 50, rN: 6,  rP: 2.2, color: "#C6FF00" },
  { cx: 480,  cy: 720, r: 130, xA: 220, xN: 5, xP: Math.PI,           yA: 170, yN: 4,  yP: (3*Math.PI) / 4,      rA: 35, rN: 12, rP: 3.3, color: "#FF6D00" },
  { cx: 1420, cy: 670, r: 120, xA: 280, xN: 3, xP: (5*Math.PI) / 6,   yA: 190, yN: 5,  yP: Math.PI / 2,          rA: 38, rN: 10, rP: 4.4, color: "#D500F9" },
] as const;

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SensoryBlobLoopProps {
  /** Include ambient music track (default false = silent). */
  sound?:        boolean;
  /** Filename in remotion/public/music/ (default: Dreamy Arpeggios v2.mp3). */
  musicFile?:    string;
  musicVolume?:  number;
  /**
   * Frames per full hue cycle (default 750 = 25 s).
   * Must divide LOOP_FRAMES (9000) for seamless loop.
   * Valid: 750, 900, 1500, 1800, 3000 …
   */
  hueSpeed?:     number;
  /** feGaussianBlur stdDeviation — controls goo merge radius (default 18). */
  blurStrength?: number;
}

// ── Component ─────────────────────────────────────────────────────────────────

export const SensoryBlobLoop: React.FC<SensoryBlobLoopProps> = ({
  sound        = false,
  musicFile    = "Dreamy Arpeggios v2.mp3",
  musicVolume  = 0.18,
  hueSpeed     = 750,
  blurStrength = 18,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  // hueAngle increases linearly; seamless because hueSpeed divides LOOP_FRAMES
  const hueAngle = (frame * 360) / hueSpeed;

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(145deg, #0A0A2E 0%, #14003A 40%, #04060F 100%)",
        overflow: "hidden",
      }}
    >
      {sound && musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={musicVolume} loop />
      )}

      {/* SVG filter: blur → alpha-contrast = goo/metaball merge effect */}
      <svg width={0} height={0} style={{ position: "absolute" }}>
        <defs>
          <filter
            id="goo"
            x="-40%"
            y="-40%"
            width="180%"
            height="180%"
          >
            <feGaussianBlur
              in="SourceGraphic"
              stdDeviation={blurStrength}
              result="blur"
            />
            {/* Multiply alpha × 22, offset −9 → sharp merge at A=0.41 threshold */}
            <feColorMatrix
              in="blur"
              type="matrix"
              values="1 0 0 0 0
                      0 1 0 0 0
                      0 0 1 0 0
                      0 0 0 22 -9"
              result="goo"
            />
          </filter>
        </defs>
      </svg>

      {/* Blob layer: goo filter + slow hue rotation */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width,
          height,
          filter: `url(#goo) hue-rotate(${hueAngle}deg)`,
        }}
      >
        {BLOBS.map((b, i) => {
          const bx = b.cx + b.xA * loopSin(frame, b.xN, b.xP);
          const by = b.cy + b.yA * loopCos(frame, b.yN, b.yP);
          const br = b.r  + b.rA * loopSin(frame, b.rN, b.rP);
          const d  = br * 2;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: bx - br,
                top:  by - br,
                width:  d,
                height: d,
                borderRadius: "50%",
                background: b.color,
              }}
            />
          );
        })}
      </div>

      {/* Soft radial vignette — adds depth without hiding the blobs */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55) 100%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
