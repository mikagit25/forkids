import React from "react";
import {
  useCurrentFrame,
  useVideoConfig,
  spring,
  Audio,
  staticFile,
  Sequence,
  interpolate,
  AbsoluteFill,
} from "remotion";
import { Shape, ShapeName } from "./components/Shape";

// ── Types ────────────────────────────────────────────────────────────────────

export type SortFixRound = {
  slotShape: ShapeName;
  slotColor: string;
  wrongShape: ShapeName;
  wrongColor: string;
};

export type SortFixLongProps = {
  rounds: SortFixRound[];
  musicFile: string;
  musicVolume?: number;
  bgColor?: string;
};

// ── Timing constants (all in frames, ROUND_FRAMES = 5s @ 30fps) ──────────────

const ROUND_FRAMES = 150;
const WRONG_ENTER_END   = 44;   // 0–30%: wrong piece slides to center
const BUZZ_START        = 44;   // 30–36%: buzz reject
const BUZZ_END          = 54;
const RIGHT_ENTER_START = 54;   // 36–60%: right piece slides in
const RIGHT_ENTER_END   = 90;
const DING_START        = 90;   // 60–100%: snap + sparkles

const GRAVITY = 800; // px/s²

// ── Sparkles sub-component (gravity-physics, reusable) ────────────────────────

export type SparklesProps = {
  cx: number;
  cy: number;
  frame: number;
  fps: number;
  count?: number;
};

const SPARK_COLORS = [
  "#FFD700", "#FF6B6B", "#4ECDC4", "#FED766",
  "#96CEB4", "#FF9FF3", "#54A0FF", "#A29BFE",
];

function sr(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

export const Sparkles: React.FC<SparklesProps> = ({
  cx, cy, frame, fps, count = 14,
}) => {
  if (frame < 0) return null;
  const maxAge = fps * 1.5;
  const t = frame / fps;
  const fade = interpolate(frame, [0, maxAge * 0.55], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  if (fade <= 0) return null;

  return (
    <>
      {Array.from({ length: count }, (_, i) => {
        const angle = (i / count) * Math.PI * 2 + sr(i * 13) * 0.5;
        const speed = 240 + sr(i * 7 + 100) * 200;
        const vx = Math.cos(angle) * speed;
        const vy = Math.sin(angle) * speed - 120;
        const px = cx + vx * t;
        const py = cy + vy * t + 0.5 * GRAVITY * t * t;
        const sz = 10 + sr(i * 3 + 50) * 13;
        const color = SPARK_COLORS[i % SPARK_COLORS.length];
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: px - sz / 2,
              top: py - sz / 2,
              width: sz,
              height: sz,
              borderRadius: "50%",
              backgroundColor: color,
              opacity: fade * 0.9,
            }}
          />
        );
      })}
    </>
  );
};

// ── Slot outline (dashed border matching target shape) ────────────────────────

const SLOT_CLIPS: Partial<Record<ShapeName, string>> = {
  triangle: "polygon(50% 0%, 0% 100%, 100% 100%)",
  star:     "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)",
  diamond:  "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)",
  hexagon:  "polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)",
};

const SlotOutline: React.FC<{
  shape: ShapeName;
  size: number;
  color: string;
  cx: number;
  cy: number;
  scale?: number;
}> = ({ shape, size, color, cx, cy, scale = 1 }) => {
  const w = (shape === "oval" ? size * 1.4 : size) * scale;
  const h = size * scale;
  const clip = SLOT_CLIPS[shape];

  const base: React.CSSProperties = {
    position: "absolute",
    left: cx - w / 2,
    top: cy - h / 2,
    width: w,
    height: h,
    border: `8px dashed ${color}`,
    backgroundColor: color + "28",
    boxSizing: "border-box",
    boxShadow: `0 0 40px 10px ${color}44, inset 0 0 20px 4px ${color}22`,
  };

  if (shape === "circle" || shape === "oval") {
    return <div style={{ ...base, borderRadius: "50%" }} />;
  }
  if (shape === "square") {
    return <div style={{ ...base, borderRadius: size * 0.08 * scale }} />;
  }
  if (clip) {
    return (
      <div
        style={{
          ...base,
          clipPath: clip,
          WebkitClipPath: clip,
        } as React.CSSProperties}
      />
    );
  }
  return <div style={base} />;
};

// ── Single round renderer ─────────────────────────────────────────────────────

const Round: React.FC<{
  round: SortFixRound;
  localFrame: number;
  fps: number;
  width: number;
  height: number;
}> = ({ round, localFrame, fps, width, height }) => {
  const cx = width / 2;
  const cy = height / 2;
  const pieceSize = 220;
  const slotSize  = pieceSize + 60;

  // Wrong piece: slides in from left
  const wrongEntry = spring({
    frame: localFrame,
    fps,
    config: { damping: 13, stiffness: 110 },
    durationInFrames: WRONG_ENTER_END,
  });
  const wrongEntryX = interpolate(wrongEntry, [0, 1], [-(pieceSize / 2 + 120), cx]);

  // Buzz shake (high-freq oscillation damped over BUZZ window)
  const buzzPhase = localFrame - BUZZ_START;
  const buzzShake =
    localFrame >= BUZZ_START && localFrame < BUZZ_END
      ? Math.sin(buzzPhase * 2.8) * 22 * (1 - buzzPhase / (BUZZ_END - BUZZ_START))
      : 0;

  // Wrong piece exits back left after buzz
  const wrongExitProg =
    localFrame >= BUZZ_END
      ? spring({
          frame: localFrame - BUZZ_END,
          fps,
          config: { damping: 11, stiffness: 100 },
          durationInFrames: 50,
        })
      : 0;

  const wrongX =
    localFrame < BUZZ_END
      ? wrongEntryX + buzzShake
      : cx - wrongExitProg * (cx + pieceSize / 2 + 120);

  // Right piece: slides in from right
  const rightEntry =
    localFrame >= RIGHT_ENTER_START
      ? spring({
          frame: localFrame - RIGHT_ENTER_START,
          fps,
          config: { damping: 13, stiffness: 130 },
          durationInFrames: RIGHT_ENTER_END - RIGHT_ENTER_START,
        })
      : 0;
  const rightX = interpolate(
    rightEntry,
    [0, 1],
    [width + pieceSize / 2 + 120, cx],
  );

  // Slot snap-pulse on ding
  const snapScale =
    localFrame >= DING_START
      ? 1 +
        spring({
          frame: localFrame - DING_START,
          fps,
          config: { damping: 5, stiffness: 380 },
          durationInFrames: 18,
        }) *
          0.12
      : 1;

  // ✕ icon (buzz reject)
  const crossVisible =
    localFrame >= BUZZ_START && localFrame < RIGHT_ENTER_START;
  const crossScale = spring({
    frame: localFrame - BUZZ_START,
    fps,
    config: { damping: 8, stiffness: 240 },
    durationInFrames: 12,
  });

  // ✓ icon (ding success)
  const checkVisible = localFrame >= DING_START;
  const checkScale = spring({
    frame: localFrame - DING_START,
    fps,
    config: { damping: 8, stiffness: 220 },
    durationInFrames: 15,
  });

  return (
    <>
      {/* Slot outline */}
      <SlotOutline
        shape={round.slotShape}
        size={slotSize}
        color={round.slotColor}
        cx={cx}
        cy={cy}
        scale={snapScale}
      />

      {/* Wrong piece (hidden once right piece is fully in) */}
      {localFrame < RIGHT_ENTER_END && (
        <div
          style={{
            position: "absolute",
            left: wrongX - pieceSize / 2,
            top: cy - pieceSize / 2,
          }}
        >
          <Shape name={round.wrongShape} size={pieceSize} color={round.wrongColor} />
        </div>
      )}

      {/* Right piece */}
      {localFrame >= RIGHT_ENTER_START && (
        <div
          style={{
            position: "absolute",
            left: rightX - pieceSize / 2,
            top: cy - pieceSize / 2,
          }}
        >
          <Shape name={round.slotShape} size={pieceSize} color={round.slotColor} />
        </div>
      )}

      {/* ✕ reject icon */}
      {crossVisible && (
        <div
          style={{
            position: "absolute",
            left: cx + pieceSize * 0.28,
            top: cy - slotSize / 2 - 80,
            fontSize: 88,
            color: "#FF3B30",
            lineHeight: 1,
            transform: `scale(${crossScale})`,
            transformOrigin: "left top",
            userSelect: "none",
          }}
        >
          ✕
        </div>
      )}

      {/* ✓ success icon */}
      {checkVisible && (
        <div
          style={{
            position: "absolute",
            left: cx + pieceSize * 0.28,
            top: cy - slotSize / 2 - 80,
            fontSize: 88,
            color: "#30D158",
            lineHeight: 1,
            transform: `scale(${checkScale})`,
            transformOrigin: "left top",
            userSelect: "none",
          }}
        >
          ✓
        </div>
      )}

      {/* Sparkles burst on ding */}
      {localFrame >= DING_START && (
        <Sparkles
          cx={cx}
          cy={cy}
          frame={localFrame - DING_START}
          fps={fps}
          count={16}
        />
      )}
    </>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────

export const SortFixLong: React.FC<SortFixLongProps> = ({
  rounds,
  musicFile,
  musicVolume = 0.20,
  bgColor = "#FFF8E1",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const roundIndex = Math.min(
    Math.floor(frame / ROUND_FRAMES),
    rounds.length - 1,
  );
  const localFrame = frame - roundIndex * ROUND_FRAMES;
  const round = rounds[roundIndex];

  // Background softly tinted toward current slot color
  const bgStyle: React.CSSProperties = {
    background: `radial-gradient(ellipse at center, ${round.slotColor}18 0%, ${bgColor} 70%)`,
  };

  // Only mount SFX sequences within a ±2 round window to keep DOM lean
  const sfxStart = Math.max(0, roundIndex - 1);
  const sfxEnd   = Math.min(rounds.length - 1, roundIndex + 2);

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor }}>
      <div style={{ position: "absolute", inset: 0, ...bgStyle }} />

      {/* Music */}
      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={musicVolume} />
      )}

      {/* SFX — 5 sounds per round, windowed ±2 rounds around current */}
      {Array.from({ length: sfxEnd - sfxStart + 1 }, (_, offset) => {
        const i  = sfxStart + offset;
        const rs = i * ROUND_FRAMES;
        return (
          <React.Fragment key={i}>
            {/* Wrong piece enters */}
            <Sequence from={rs} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/whoosh.mp3")} volume={0.55} />
            </Sequence>
            {/* Buzz reject */}
            <Sequence from={rs + BUZZ_START} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/boing.mp3")} volume={0.72} />
            </Sequence>
            {/* Right piece enters */}
            <Sequence from={rs + RIGHT_ENTER_START} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/whoosh.mp3")} volume={0.28} />
            </Sequence>
            {/* Ding success */}
            <Sequence from={rs + DING_START} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/ding.mp3")} volume={0.80} />
            </Sequence>
            {/* Chime sparkle */}
            <Sequence from={rs + DING_START + 6} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/chime.mp3")} volume={0.60} />
            </Sequence>
          </React.Fragment>
        );
      })}

      {/* Current round visuals */}
      <Round
        round={round}
        localFrame={localFrame}
        fps={fps}
        width={width}
        height={height}
      />
    </AbsoluteFill>
  );
};
