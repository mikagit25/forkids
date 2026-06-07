/**
 * ShapeDance — shapes bouncing and dancing on screen.
 * Multiple shapes jump, spin, and pulse in rhythm.
 * Good for background attention videos and shape recognition.
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Shape, ShapeName, SHAPE_LABELS } from "./components/Shape";

export interface ShapeDanceProps {
  shapes: ShapeName[];       // shapes to show (1–4)
  colors: string[];          // color per shape (same length as shapes)
  bgColor: string;
  bpm: number;               // beat tempo (60–160)
  showLabels: boolean;
  audioFile?: string | null;
  musicFile?: string | null;
  customLabels?: Partial<Record<ShapeName, string>>; // Arabic overrides
  rtl?: boolean;
}

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

interface DancerProps {
  shapeName: ShapeName;
  color: string;
  label: string;
  showLabel: boolean;
  posX: number;    // 0–1 of frame width
  posY: number;    // 0–1 of frame height
  seed: number;
  bpm: number;
  rtl: boolean;
}

const Dancer: React.FC<DancerProps> = ({
  shapeName, color, label, showLabel, posX, posY, seed, bpm, rtl,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const beatsPerFrame = bpm / 60 / fps;
  const beatPhase = (frame * beatsPerFrame * Math.PI * 2 + seed * 1.3) % (Math.PI * 2);

  // Bounce: vertical oscillation on beat (keeps shape intact)
  const bounce = Math.abs(Math.sin(beatPhase)) * 48;
  // Uniform scale pulse — shape stays recognizable
  const pulse = 1 + Math.abs(Math.sin(beatPhase)) * 0.12;
  // Very slow rock (±15°) instead of full spin — shape stays oriented
  const rotation = Math.sin((frame / fps) * 1.2 + seed) * 15;

  // Entrance spring (first 1.5s)
  const entrance = spring({
    frame,
    fps,
    config: { damping: 10, stiffness: 120 },
    durationInFrames: Math.round(fps * 1.5),
  });
  const entranceY = interpolate(entrance, [0, 1], [height * 0.5, 0]);

  const cx = posX * width;
  const cy = posY * height;
  const size = 220 + seededRand(seed * 7) * 60;  // 220–280px

  return (
    <div style={{ position: "absolute", left: cx - size / 2, top: cy - size / 2 + entranceY }}>
      {/* Shape bounces + pulses + rocks — stays recognizable */}
      <div
        style={{
          transform: `translateY(${-bounce}px) scale(${pulse}) rotate(${rotation}deg)`,
          transformOrigin: "center bottom",
        }}
      >
        <Shape name={shapeName} size={size} color={color} />
      </div>

      {/* Label stays upright below shape */}
      {showLabel && (
        <div style={{ display: "flex", justifyContent: "center", marginTop: 14 }}>
          <span
            style={{
              fontFamily: rtl
                ? "'Noto Sans Arabic', 'Noto Kufi Arabic', sans-serif"
                : "'Arial Black', sans-serif",
              fontSize: 52,
              fontWeight: 900,
              color,
              WebkitTextStroke: "3px white",
              textShadow: "0 3px 12px rgba(0,0,0,0.15)",
              whiteSpace: "nowrap",
              direction: rtl ? "rtl" : "ltr",
            }}
          >
            {label}
          </span>
        </div>
      )}
    </div>
  );
};

// Portrait (1080×1920) optimized positions — generous spacing
const POSITIONS: Record<number, { x: number; y: number }[]> = {
  1: [{ x: 0.5,  y: 0.40 }],
  2: [{ x: 0.5,  y: 0.26 }, { x: 0.5,  y: 0.62 }],
  3: [{ x: 0.5,  y: 0.20 }, { x: 0.25, y: 0.57 }, { x: 0.75, y: 0.57 }],
  4: [{ x: 0.25, y: 0.22 }, { x: 0.75, y: 0.22 }, { x: 0.25, y: 0.60 }, { x: 0.75, y: 0.60 }],
};

export const ShapeDance: React.FC<ShapeDanceProps> = ({
  shapes, colors, bgColor, bpm, showLabels, audioFile, musicFile,
  customLabels = {}, rtl = false,
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const frame = useCurrentFrame();

  const n = Math.min(shapes.length, 4);
  const positions = POSITIONS[n] ?? POSITIONS[1];

  const fadeOut = interpolate(
    frame,
    [durationInFrames - fps * 1.5, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, overflow: "hidden" }}>
      {audioFile && (
        <>
          <Audio src={staticFile(`audio/${audioFile}`)} startFrom={Math.round(fps * 1)} />
          <Audio src={staticFile(`audio/${audioFile}`)} startFrom={Math.round(fps * 20)} />
          <Audio src={staticFile(`audio/${audioFile}`)} startFrom={Math.round(fps * 39)} />
        </>
      )}
      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={0.2} loop />
      )}

      <AbsoluteFill style={{ opacity: fadeOut }}>
        {shapes.slice(0, n).map((shape, i) => (
          <Dancer
            key={i}
            shapeName={shape}
            color={colors[i] ?? colors[0]}
            label={customLabels[shape] ?? SHAPE_LABELS[shape]}
            showLabel={showLabels}
            posX={positions[i].x}
            posY={positions[i].y}
            seed={i + 1}
            bpm={bpm}
            rtl={rtl}
          />
        ))}

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
