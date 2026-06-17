/**
 * ShapeFloat — shapes drifting across screen in various patterns.
 * Educational value: repeated visual exposure to a single shape name.
 *
 * Modes:
 *   "lr"    — left → right
 *   "tb"    — top → bottom (rain)
 *   "diag"  — diagonal (top-left → bottom-right)
 *   "float" — gentle random floating (multiple sizes, slow)
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Shape, ShapeName, SHAPE_LABELS } from "./components/Shape";
import { ArabicFonts } from "./components/ArabicFonts";

export type FloatMode = "lr" | "tb" | "diag" | "float";

export interface ShapeFloatProps {
  shapeName: ShapeName;
  shapeColor: string;
  bgColor: string;
  mode: FloatMode;
  count: number;          // shapes visible at once
  showLabel: boolean;     // show shape name text
  audioFile?: string | null;
  musicFile?: string | null;
  speed: "slow" | "medium" | "fast";
  customLabel?: string;   // override label (e.g. Arabic text)
  rtl?: boolean;          // right-to-left layout
}

// Deterministic pseudo-random from seed
function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

interface FloaterProps {
  shapeName: ShapeName;
  color: string;
  mode: FloatMode;
  seed: number;           // unique per shape instance
  speed: number;          // frames per full traversal
  durationInFrames: number;
  width: number;
  height: number;
}

const Floater: React.FC<FloaterProps> = ({
  shapeName, color, mode, seed, speed, durationInFrames, width, height,
}) => {
  const frame = useCurrentFrame();

  const r = seededRand;
  const size = 140 + r(seed * 7) * 180;      // 140–320px
  const opacity = 0.55 + r(seed * 3) * 0.4;  // 0.55–0.95
  // Stagger start: each shape begins at a different point in the cycle
  const offset = r(seed * 5) * speed;
  const t = ((frame + offset) % speed) / speed; // 0→1 progress

  let x = 0, y = 0;

  if (mode === "lr") {
    x = interpolate(t, [0, 1], [-size, width + size]);
    y = r(seed * 11) * (height - size);
  } else if (mode === "tb") {
    x = r(seed * 13) * (width - size);
    y = interpolate(t, [0, 1], [-size, height + size]);
  } else if (mode === "diag") {
    // Random diagonal direction per shape
    const goRight = seed % 2 === 0;
    const startX = goRight ? -size : width + size;
    const endX   = goRight ? width + size : -size;
    x = interpolate(t, [0, 1], [startX, endX]);
    y = interpolate(t, [0, 1], [-size, height + size]);
  } else {
    // float: gentle sine-wave drift
    const baseX = r(seed * 17) * (width - size);
    const baseY = r(seed * 19) * (height - size);
    x = baseX + Math.sin((frame / 90 + seed) * 0.8) * 60;
    y = baseY + Math.cos((frame / 110 + seed * 2) * 0.6) * 50;
  }

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        pointerEvents: "none",
      }}
    >
      <Shape name={shapeName} size={size} color={color} opacity={opacity} />
    </div>
  );
};

export const ShapeFloat: React.FC<ShapeFloatProps> = ({
  shapeName, shapeColor, bgColor, mode, count,
  showLabel, audioFile, musicFile, speed,
  customLabel, rtl = false,
}) => {
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const frame = useCurrentFrame();

  const speedFrames = { slow: fps * 8, medium: fps * 5, fast: fps * 3 }[speed];

  // Label fade: appears at 1s, stays throughout
  const labelOpacity = interpolate(frame, [fps * 0.5, fps * 1.5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Fade out last 1.5s
  const fadeOut = interpolate(
    frame,
    [durationInFrames - fps * 1.5, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const label = customLabel ?? SHAPE_LABELS[shapeName];

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, overflow: "hidden" }}>
      <ArabicFonts />
      {audioFile && (
        <>
          <Sequence from={Math.round(fps * 1)}>
            <Audio src={staticFile(`audio/${audioFile}`)} />
          </Sequence>
          <Sequence from={Math.round(fps * 20)}>
            <Audio src={staticFile(`audio/${audioFile}`)} />
          </Sequence>
          <Sequence from={Math.round(fps * 39)}>
            <Audio src={staticFile(`audio/${audioFile}`)} />
          </Sequence>
        </>
      )}
      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={0.18} loop />
      )}

      <AbsoluteFill style={{ opacity: fadeOut }}>
        {/* Floating shape instances */}
        {Array.from({ length: count }, (_, i) => (
          <Floater
            key={i}
            shapeName={shapeName}
            color={shapeColor}
            mode={mode}
            seed={i + 1}
            speed={speedFrames}
            durationInFrames={durationInFrames}
            width={width}
            height={height}
          />
        ))}

        {/* Shape name label */}
        {showLabel && (
          <div
            style={{
              position: "absolute",
              bottom: "8%",
              left: 0,
              right: 0,
              display: "flex",
              justifyContent: "center",
              opacity: labelOpacity,
              pointerEvents: "none",
            }}
          >
            <span
              style={{
                fontFamily: rtl
                  ? "'Noto Sans Arabic', 'Noto Kufi Arabic', sans-serif"
                  : "'Arial Black', 'Arial Bold', sans-serif",
                fontSize: 110,
                fontWeight: 900,
                color: shapeColor,
                WebkitTextStroke: "5px white",
                textShadow: "0 4px 20px rgba(0,0,0,0.15)",
                letterSpacing: rtl ? 0 : 6,
                background: "rgba(255,255,255,0.55)",
                borderRadius: 24,
                padding: "12px 52px",
                direction: rtl ? "rtl" : "ltr",
              }}
            >
              {label}
            </span>
          </div>
        )}

        {/* Channel brand */}
        <div
          style={{
            position: "absolute",
            bottom: "2%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            opacity: 0.5,
          }}
        >
          <span style={{
            fontFamily: "'Arial', sans-serif",
            fontSize: 42,
            color: "white",
            textShadow: "0 2px 8px rgba(0,0,0,0.3)",
          }}>
            Happy Bear Kids
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
