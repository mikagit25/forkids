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
 *
 * 3D depth simulation (v2):
 *  - sprite.depth (0–1): 0=far background, 1=close foreground
 *  - depth drives parallax multiplier, drop-shadow intensity
 *  - New motions: ZFLOAT (Z-axis zoom breathing), YFLIP (Y-axis turn simulation)
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
  depth?: number;      // 0=far background, 1=close foreground (default 0.5)
  orbitRadius?: number;
  orbitPeriodSec?: number;
  orbitCcw?: boolean;
  flipX?: boolean;     // mirror the sprite horizontally
}

export type SpriteMotionType =
  | "BOB" | "SWAY" | "SPIN" | "DRIFT" | "PULSE"
  | "WAVE" | "ORBIT" | "BOUNCE" | "MARCH"
  | "ZFLOAT" | "YFLIP"
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
  accentColor?: string;        // for background bubbles / sparkle tint (default white)
  musicFile: string;
  volume?: number;
  bgEffect?: "bubbles" | "sparkles" | "none"; // default "bubbles"
  nightMode?: boolean;
  wobble?: boolean;            // global PIP/BWW wobble on all sprites (can override per block)
  bgImage?: string;            // filename in remotion/public/backgrounds/ (e.g. "meadow.jpg")
  bgDim?: number;              // 0–1, darken background image for sprite contrast (default 0.18)
  bgImageMotion?: "zoom" | "pan" | "static"; // Ken Burns effect on bgImage (default "zoom")
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
  const opacity = 0.08 + r(seed * 5) * 0.12;
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

// ── Falling sparkles (gold stars) ─────────────────────────────────────────────
const FallingSparkle: React.FC<{
  seed: number; width: number; height: number;
}> = ({ seed, width, height }) => {
  const frame = useCurrentFrame();
  const r = seededRand;

  const startX   = r(seed * 3) * width;
  const size     = 14 + r(seed * 7) * 14;          // 14–28 px
  const fallPx   = 0.5 + r(seed * 11) * 0.8;       // px per frame (slow to medium)
  const rotDir   = r(seed * 13) > 0.5 ? 1 : -1;
  const rotRate  = rotDir * (0.8 + r(seed * 17) * 2.4); // deg/frame
  const swingAmp = 20 + r(seed * 19) * 40;          // horizontal drift amplitude

  const cycleFr  = Math.floor(height / fallPx) + 60;  // frames for one full fall
  const offsetFr = Math.floor(r(seed * 5) * cycleFr);
  const cf       = (frame + offsetFr) % cycleFr;

  const x        = startX + Math.sin((cf * 0.04) + seed) * swingAmp;
  const y        = cf * fallPx - size;
  const rotation = cf * rotRate;

  // Fade in first 20fr, fade out last 20fr of cycle
  const fadeIn   = Math.min(1, cf / 20);
  const fadeOut  = Math.min(1, (cycleFr - cf) / 20);
  const baseOpacity = 0.40 + r(seed * 9) * 0.35;   // 0.40–0.75
  const opacity  = baseOpacity * fadeIn * fadeOut;

  // Alternate between ★ and ✦ for variety
  const glyph = r(seed * 23) > 0.4 ? "★" : "✦";
  // Gold to light-yellow color mix per seed
  const hue   = 42 + Math.floor(r(seed * 29) * 18); // 42–60
  const color = `hsl(${hue}, 100%, 60%)`;

  return (
    <div style={{
      position: "absolute",
      left: x - size / 2,
      top: y,
      width: size,
      height: size,
      fontSize: size,
      lineHeight: 1,
      textAlign: "center",
      color,
      opacity,
      transform: `rotate(${rotation}deg)`,
      pointerEvents: "none",
      userSelect: "none",
    }}>
      {glyph}
    </div>
  );
};

// ── Motion computation ─────────────────────────────────────────────────────────

interface SpriteTransform {
  cx: number; cy: number;
  rotation: number; scaleX: number; scaleY: number;
  opacity: number;
  shadowY: number;
  shadowBlur: number;
  shadowOpacity: number;
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
  const t        = fSec - block.startSec;
  const blockDur = block.endSec - block.startSec;
  const period   = block.period   ?? 3;
  const amplitude = block.amplitude ?? 40;
  const tau      = 2 * Math.PI;

  const baseX = sprite.posX * width;
  const baseY = sprite.posY * height;

  // Depth-based parallax: depth=0 → mult=0.6 (sluggish), depth=1 → mult=1.4 (lively)
  // Default depth=0.5 → mult=1.0 (no change from v1 behaviour)
  const depth        = sprite.depth ?? 0.5;
  const parallaxMult = 0.6 + depth * 0.8;

  // Depth-based drop shadow: closer sprites cast a stronger, lower shadow
  const shadowY      = 4  + depth * 12;   // 4–16 px
  const shadowBlur   = 8  + depth * 16;   // 8–24 px
  const shadowOpacity = 0.10 + depth * 0.22; // 0.10–0.32

  let cx = baseX, cy = baseY, rotation = 0;
  let scaleX = 1, scaleY = 1, opacity = 1;

  const phaseDelay = shapeIdx * (block.waveDelay ?? 0.4);

  switch (block.motion) {
    case "BOB": {
      const phase = (t / period) * tau;
      cy = baseY + Math.sin(phase) * amplitude * parallaxMult;
      const norm = Math.sin(phase);
      scaleX = 1 - norm * 0.06;
      scaleY = 1 + norm * 0.06;
      break;
    }
    case "SWAY":
      cx = baseX + Math.sin((t / period) * tau) * amplitude * parallaxMult;
      rotation = Math.sin((t / period) * tau) * 8;
      break;

    case "SPIN":
      rotation = (t / period) * 360;
      break;

    case "DRIFT": {
      const ph = sprite.seed * 2.1;
      cx = baseX + Math.sin(t * (tau / (period * 1.618)) + ph) * amplitude * parallaxMult;
      cy = baseY + Math.sin(t * (tau / period) + ph + 1.3) * (amplitude * 0.6) * parallaxMult;
      rotation = Math.sin(t * 0.4 + sprite.seed) * 12;
      break;
    }
    case "PULSE": {
      const pct = amplitude / 100;
      const ps = 1 + Math.sin((t / period) * tau) * pct;
      scaleX = ps;
      scaleY = ps;
      cy = baseY + Math.sin((t / period) * tau + 0.3) * 10 * parallaxMult;
      break;
    }
    case "WAVE": {
      const td = t - shapeIdx * phaseDelay;
      cy = baseY + Math.sin((td / period) * tau) * amplitude * parallaxMult;
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
      cy = baseY - Math.abs(Math.sin(phase)) * amplitude * parallaxMult;
      const norm = Math.abs(Math.sin(phase));
      scaleX = 1 + (1 - norm) * 0.12;
      scaleY = 1 - (1 - norm) * 0.10;
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
      break;
    }

    // ── NEW: ZFLOAT — slow zoom breathing (Z-axis approach/recede) ──────────
    case "ZFLOAT": {
      // Each sprite gets unique phase so they breathe independently
      const zPhase = (t / (period * 1.5)) * tau + sprite.seed;
      const zScale = 1 + Math.sin(zPhase) * 0.09;
      scaleX = zScale;
      scaleY = zScale;
      // Gentle lateral drift as it "floats" closer/further
      cx = baseX + Math.sin(t * 0.28 + sprite.seed) * amplitude * 0.35 * parallaxMult;
      cy = baseY + Math.cos(t * 0.22 + sprite.seed * 1.3) * amplitude * 0.25 * parallaxMult;
      break;
    }

    // ── NEW: YFLIP — Y-axis turn simulation (scaleX: 1→0→−1→0→1) ──────────
    case "YFLIP": {
      const flipPhase = (t / period) * tau + sprite.seed * 0.5;
      // cos goes 1→0→-1→0→1: simulates a 360° Y-axis rotation
      scaleX = Math.cos(flipPhase);
      // Gentle bob while flipping
      cy = baseY + Math.sin(flipPhase * 0.5) * amplitude * 0.25 * parallaxMult;
      cx = baseX + Math.sin(t * 0.18 + sprite.seed) * amplitude * 0.18 * parallaxMult;
      break;
    }

    case "FADEIN": {
      const perSprite = blockDur / numSprites;
      const appearAt  = block.startSec + shapeIdx * perSprite;
      opacity = interpolate(fSec, [appearAt, appearAt + 4], [0, 1], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      });
      const ph = sprite.seed * 2.1;
      cx = baseX + Math.sin(t * 0.22 + ph) * 60 * parallaxMult;
      cy = baseY + Math.sin(t * 0.16 + ph + 1) * 35 * parallaxMult;
      break;
    }
    case "FADEOUT": {
      const perSprite = blockDur / numSprites;
      const disappearAt = block.startSec + (numSprites - 1 - shapeIdx) * perSprite;
      opacity = interpolate(fSec, [disappearAt, disappearAt + 4], [1, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      });
      const ph = sprite.seed * 2.1;
      cx = baseX + Math.sin(t * 0.22 + ph) * 60 * parallaxMult;
      cy = baseY + Math.sin(t * 0.16 + ph + 1) * 35 * parallaxMult;
      break;
    }
    case "NONE":
    default:
      // Gentle idle float — never fully static
      cx = baseX + Math.sin(t * 0.55 + sprite.seed) * 18 * parallaxMult;
      cy = baseY + Math.sin(t * 0.42 + sprite.seed * 1.4) * 14 * parallaxMult;
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
    cx += Math.sin(t * (9.1 + s * 0.8)) * 2.8 * parallaxMult;
    cy += Math.cos(t * (7.3 + s * 0.6)) * 2.8 * parallaxMult;
  }

  return { cx, cy, rotation, scaleX, scaleY, opacity, shadowY, shadowBlur, shadowOpacity };
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
  bgImage,
  bgDim = 0.18,
  bgImageMotion = "zoom",
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

  // Sort sprites by depth so background sprites render first (painter's algorithm)
  const sortedSprites = [...sprites].map((s, i) => ({ sprite: s, origIdx: i }))
    .sort((a, b) => (a.sprite.depth ?? 0.5) - (b.sprite.depth ?? 0.5));

  // bgImage Ken Burns transform
  const totalSec = durationInFrames / fps;
  let bgTransform = "";
  if (bgImage) {
    if (bgImageMotion === "zoom") {
      const scale = 1 + bgProgress * 0.08;
      bgTransform = `scale(${scale})`;
    } else if (bgImageMotion === "pan") {
      // slow horizontal pan left-to-right
      const panX = interpolate(fSec, [0, totalSec], [-4, 4], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      });
      bgTransform = `scale(1.10) translateX(${panX}%)`;
    }
    // "static" → no transform
  }

  return (
    <AbsoluteFill style={{ backgroundColor: currentBg, overflow: "hidden" }}>
      <Audio src={staticFile(`music/${musicFile}`)} volume={volume} loop />

      {/* Background image with Ken Burns motion */}
      {bgImage && (
        <AbsoluteFill style={{ overflow: "hidden" }}>
          <Img
            src={staticFile(`backgrounds/${bgImage}`)}
            style={{
              width: "100%", height: "100%",
              objectFit: "cover",
              transform: bgTransform,
              transformOrigin: "center center",
            }}
          />
          {/* Dark veil so sprites pop against any background */}
          <AbsoluteFill style={{ backgroundColor: `rgba(0,0,0,${bgDim})` }} />
        </AbsoluteFill>
      )}

      <AbsoluteFill style={{ opacity: fadeOut * nightDim * blockAlpha }}>
        {/* Background effect */}
        {bgEffect === "bubbles" && Array.from({ length: 14 }, (_, i) => (
          <FloatingBubble
            key={i} seed={i + 1} width={width} height={height} color={accentColor}
          />
        ))}
        {bgEffect === "sparkles" && Array.from({ length: 22 }, (_, i) => (
          <FallingSparkle key={i} seed={i + 1} width={width} height={height} />
        ))}

        {/* Sprites — sorted back-to-front by depth */}
        {sortedSprites.map(({ sprite, origIdx }) => {
          const { cx, cy, rotation, scaleX, scaleY, opacity, shadowY, shadowBlur, shadowOpacity } =
            computeSpriteTransform(
              currentBlock, sprite, origIdx, sprites.length, fSec, width, height, wobble,
            );
          const size = sprite.size;
          const flipX = sprite.flipX ? -1 : 1;
          const shadow = `drop-shadow(0px ${shadowY}px ${shadowBlur}px rgba(0,0,0,${shadowOpacity.toFixed(2)}))`;

          return (
            <div
              key={origIdx}
              style={{
                position: "absolute",
                left: cx - size / 2,
                top:  cy - size / 2,
                width: size,
                height: size,
                transform: `scaleX(${scaleX * flipX}) scaleY(${scaleY}) rotate(${rotation}deg)`,
                transformOrigin: "center center",
                opacity,
                filter: shadow,
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
