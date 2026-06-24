/**
 * DanceSpriteLong — 25-30 min sprite-based character dance, no text.
 * Universal: EN + AR + ID (no language content on screen).
 *
 * Used for:
 *  - dance_pet series  (cats, dogs, rabbits, etc.)
 *  - dance_item series (household items, kitchen, toys, etc.)
 *
 * Shares motion types with DanceShapeLong (BOB/SWAY/SPIN/DRIFT/PULSE/WAVE/ORBIT/BOUNCE/MARCH).
 * Sprites are rendered as <Img> with squash-stretch on bounce moves.
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

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SpriteItem {
  path: string;        // relative to remotion/public/sprites/ (e.g. "animals/cat.png")
  size: number;        // px
  posX: number;        // 0–1 of width
  posY: number;        // 0–1 of height
  seed: number;
  orbitRadius?: number;
  orbitPeriodSec?: number;
  orbitCcw?: boolean;
  flipX?: boolean;     // mirror the sprite horizontally
}

export type SpriteMotionType =
  | "BOB" | "SWAY" | "SPIN" | "DRIFT" | "PULSE"
  | "WAVE" | "ORBIT" | "BOUNCE" | "MARCH"
  | "FADEIN" | "FADEOUT" | "NONE";

export interface SpriteMotionBlock {
  startSec: number;
  endSec: number;
  motion: SpriteMotionType;
  period?: number;
  amplitude?: number;
  waveDelay?: number;
  orbitCenterX?: number;
  orbitCenterY?: number;
  bobAmplitude?: number;
  bgColorOverride?: string;  // optional per-block background tint
  wobble?: boolean;          // PIP/BWW outline wobble for this block
}

export interface DanceSpriteLongProps {
  sprites: SpriteItem[];
  blocks: SpriteMotionBlock[];
  bgColor: string;
  bgColorEnd?: string;
  accentColor?: string;        // for background bubbles (default white)
  musicFile: string;
  volume?: number;
  bgEffect?: "bubbles" | "sparkles" | "none"; // default "bubbles"
  nightMode?: boolean;
  wobble?: boolean;            // global PIP/BWW wobble on all sprites (can override per block)
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

function lerpColor(a: string, b: string, t: number): string {
  const p = (hex: string, s: number) => parseInt(hex.slice(s, s + 2), 16);
  return `#${
    Math.round(p(a, 1) + (p(b, 1) - p(a, 1)) * t).toString(16).padStart(2, "0")
  }${
    Math.round(p(a, 3) + (p(b, 3) - p(a, 3)) * t).toString(16).padStart(2, "0")
  }${
    Math.round(p(a, 5) + (p(b, 5) - p(a, 5)) * t).toString(16).padStart(2, "0")
  }`;
}

// ── Background floating bubbles ────────────────────────────────────────────────
const FloatingBubble: React.FC<{
  seed: number; width: number; height: number; color: string;
}> = ({ seed, width, height, color }) => {
  const frame = useCurrentFrame();
  const r = seededRand;
  const size    = 18 + r(seed * 3) * 70;
  const baseX   = r(seed * 7)  * (width  - size);
  const baseY   = r(seed * 11) * (height - size);
  const speed   = 0.2 + r(seed * 13) * 0.3;
  const opacity = 0.05 + r(seed * 5) * 0.08;
  const x = baseX + Math.sin((frame / 90) * speed + seed)      * 24;
  const y = baseY + Math.cos((frame / 110) * speed + seed * 2) * 18;
  return (
    <div style={{
      position: "absolute", left: x, top: y,
      width: size, height: size, borderRadius: "50%",
      backgroundColor: color, opacity, pointerEvents: "none",
    }} />
  );
};

// ── Motion computation ─────────────────────────────────────────────────────────

interface SpriteTransform {
  cx: number; cy: number;
  rotation: number; scaleX: number; scaleY: number;
  opacity: number;
}

function computeSpriteTransform(
  block: SpriteMotionBlock,
  sprite: SpriteItem,
  shapeIdx: number,
  numSprites: number,
  fSec: number,
  width: number,
  height: number,
  globalWobble: boolean,
): SpriteTransform {
  const t       = fSec - block.startSec;
  const blockDur = block.endSec - block.startSec;
  const period   = block.period   ?? 3;
  const amplitude = block.amplitude ?? 40;
  const tau      = 2 * Math.PI;

  const baseX = sprite.posX * width;
  const baseY = sprite.posY * height;

  let cx = baseX, cy = baseY, rotation = 0;
  let scaleX = 1, scaleY = 1, opacity = 1;

  const phaseDelay = shapeIdx * (block.waveDelay ?? 0.4);

  switch (block.motion) {
    case "BOB": {
      const phase = (t / period) * tau;
      cy = baseY + Math.sin(phase) * amplitude;
      // Squash at bottom, stretch at top
      const norm = Math.sin(phase); // -1 to 1
      scaleX = 1 - norm * 0.06;
      scaleY = 1 + norm * 0.06;
      break;
    }
    case "SWAY":
      cx = baseX + Math.sin((t / period) * tau) * amplitude;
      rotation = Math.sin((t / period) * tau) * 8;
      break;

    case "SPIN":
      rotation = (t / period) * 360;
      break;

    case "DRIFT": {
      const ph = sprite.seed * 2.1;
      cx = baseX + Math.sin(t * (tau / (period * 1.618)) + ph) * amplitude;
      cy = baseY + Math.sin(t * (tau / period) + ph + 1.3) * (amplitude * 0.6);
      rotation = Math.sin(t * 0.4 + sprite.seed) * 12;
      break;
    }
    case "PULSE": {
      const pct = (amplitude) / 100;
      const ps = 1 + Math.sin((t / period) * tau) * pct;
      scaleX = ps;
      scaleY = ps;
      cy = baseY + Math.sin((t / period) * tau + 0.3) * 10;
      break;
    }
    case "WAVE": {
      const td = t - shapeIdx * phaseDelay;
      cy = baseY + Math.sin((td / period) * tau) * amplitude;
      break;
    }
    case "ORBIT": {
      const r = sprite.orbitRadius ?? 0;
      if (r <= 0) {
        scaleX = 1 + Math.sin(t * 0.8 + sprite.seed) * 0.05;
        scaleY = scaleX;
      } else {
        const oPeriod = sprite.orbitPeriodSec ?? 8;
        const dir = sprite.orbitCcw ? -1 : 1;
        const angle = dir * (t / oPeriod) * tau + sprite.seed;
        const ocx = (block.orbitCenterX ?? 0.5) * width;
        const ocy = (block.orbitCenterY ?? 0.45) * height;
        cx = ocx + Math.cos(angle) * r;
        cy = ocy + Math.sin(angle) * r * 0.55;
        rotation = Math.sin(t * 0.6 + sprite.seed) * 10;
      }
      break;
    }
    case "BOUNCE": {
      const phase = (t / period) * tau;
      cy = baseY - Math.abs(Math.sin(phase)) * amplitude;
      // Squash at landing
      const norm = Math.abs(Math.sin(phase));
      scaleX = 1 + (1 - norm) * 0.10;
      scaleY = 1 - (1 - norm) * 0.08;
      break;
    }
    case "MARCH": {
      const spacing = width / numSprites;
      const startX  = shapeIdx * spacing + sprite.size / 2;
      const marchDist = (t / period) * width;
      cx = ((startX + marchDist) % (width + sprite.size)) - sprite.size / 2;
      cy = baseY;
      const bobAmp = block.bobAmplitude ?? 18;
      cy = baseY - Math.abs(Math.sin((t / (period / numSprites)) * tau)) * bobAmp;
      rotation = Math.sin((t / period) * tau * numSprites + shapeIdx) * 6;
      // Flip direction based on movement
      break;
    }
    case "FADEIN": {
      const perSprite = blockDur / numSprites;
      const appearAt  = block.startSec + shapeIdx * perSprite;
      opacity = interpolate(fSec, [appearAt, appearAt + 4], [0, 1], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      });
      const ph = sprite.seed * 2.1;
      cx = baseX + Math.sin(t * 0.22 + ph) * 60;
      cy = baseY + Math.sin(t * 0.16 + ph + 1) * 35;
      break;
    }
    case "FADEOUT": {
      const perSprite = blockDur / numSprites;
      const disappearAt = block.startSec + (numSprites - 1 - shapeIdx) * perSprite;
      opacity = interpolate(fSec, [disappearAt, disappearAt + 4], [1, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      });
      const ph = sprite.seed * 2.1;
      cx = baseX + Math.sin(t * 0.22 + ph) * 60;
      cy = baseY + Math.sin(t * 0.16 + ph + 1) * 35;
      break;
    }
    case "NONE":
    default:
      // Gentle idle float — never fully static
      cx = baseX + Math.sin(t * 0.55 + sprite.seed) * 18;
      cy = baseY + Math.sin(t * 0.42 + sprite.seed * 1.4) * 14;
      scaleX = 1 + Math.sin(t * 0.9 + sprite.seed * 0.7) * 0.04;
      scaleY = scaleX;
      break;
  }

  // PIP/BWW wobble — multi-frequency outline breathing, unique per sprite via seed
  if (globalWobble || block.wobble) {
    const s = sprite.seed;
    scaleX *= 1 + Math.sin(t * (8.3 + s * 0.7)) * 0.038 + Math.sin(t * (5.1 + s * 0.4)) * 0.020;
    scaleY *= 1 + Math.sin(t * (7.7 + s * 0.9)) * 0.038 + Math.cos(t * (4.2 + s * 1.1)) * 0.020;
    rotation += Math.sin(t * (6.5 + s * 0.5)) * 1.4;
    cx += Math.sin(t * (9.1 + s * 0.8)) * 2.8;
    cy += Math.cos(t * (7.3 + s * 0.6)) * 2.8;
  }

  return { cx, cy, rotation, scaleX, scaleY, opacity };
}

// ── Main composition ──────────────────────────────────────────────────────────

export const DanceSpriteLong: React.FC<DanceSpriteLongProps> = ({
  sprites,
  blocks,
  bgColor,
  bgColorEnd,
  accentColor = "#FFFFFF",
  musicFile,
  volume = 0.2,
  bgEffect = "bubbles",
  nightMode = false,
  wobble = false,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const fSec = frame / fps;

  // Background fade for night mode
  const bgProgress = bgColorEnd
    ? interpolate(fSec, [0, durationInFrames / fps], [0, 1], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 0;
  const currentBg = bgColorEnd ? lerpColor(bgColor, bgColorEnd, bgProgress) : bgColor;

  // Night dim
  const nightDim = nightMode
    ? interpolate(fSec, [0, durationInFrames / fps], [1, 0.65], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 1;

  // Global fade out last 3s
  const fadeOut = interpolate(
    frame,
    [durationInFrames - fps * 3, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  // Current block
  const currentBlock =
    [...blocks].reverse().find((b) => fSec >= b.startSec && fSec < b.endSec) ??
    blocks[blocks.length - 1];

  // Block fade-in (smooth 1.5s at block start)
  const blockIdx   = blocks.indexOf(currentBlock);
  const blockAlpha = blockIdx === 0
    ? interpolate(fSec, [0, 1.5], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : interpolate(fSec,
        [currentBlock.startSec, currentBlock.startSec + 1.5], [0, 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: currentBg, overflow: "hidden" }}>
      <Audio src={staticFile(`music/${musicFile}`)} volume={volume} loop />

      <AbsoluteFill style={{ opacity: fadeOut * nightDim * blockAlpha }}>
        {/* Background effect */}
        {bgEffect === "bubbles" && Array.from({ length: 14 }, (_, i) => (
          <FloatingBubble
            key={i} seed={i + 1} width={width} height={height} color={accentColor}
          />
        ))}

        {/* Sprites */}
        {sprites.map((sprite, i) => {
          const { cx, cy, rotation, scaleX, scaleY, opacity } = computeSpriteTransform(
            currentBlock, sprite, i, sprites.length, fSec, width, height, wobble,
          );
          const size = sprite.size;
          const flipX = sprite.flipX ? -1 : 1;

          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: cx - size / 2,
                top:  cy - size / 2,
                width: size,
                height: size,
                transform: `scaleX(${scaleX * flipX}) scaleY(${scaleY}) rotate(${rotation}deg)`,
                transformOrigin: "center center",
                opacity,
              }}
            >
              <Img
                src={staticFile(`sprites/${sprite.path}`)}
                style={{ width: size, height: size, objectFit: "contain" }}
              />
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
