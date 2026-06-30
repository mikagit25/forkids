/**
 * FactoryTransform — "Magic Factory" mechanic.
 * A grayscale silhouette rides the conveyor belt → enters the magic gate →
 * emerges full color + 3D. ASMR-style pop/sparkle on transform moment.
 * No text. Universal EN/AR/ID content (no pig for AR/ID).
 *
 * Items cycle one at a time. Total per item ≈ 5 seconds → ~1 min for 12 items loop.
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { BackgroundParallax, ParallaxLayer } from "./components/BackgroundParallax";
import { SpringBox } from "./components/SpringBox";
import type { Region } from "./types/RegionConfig";
import { REGION_CONFIGS } from "./types/RegionConfig";

// ── Item catalogue ────────────────────────────────────────────────────────────
interface FactoryItem {
  key: string;
  /** Grayscale / "before" sprite */
  spriteBw: string;
  /** Color / "after" sprite (3D version if available) */
  spriteColor: string;
  /** Accent color for sparkle burst */
  accentColor: string;
  allowedRegions: Region[];
}

const ALL_ITEMS: FactoryItem[] = [
  // Animals
  { key: "cat",       spriteBw: "sprites/animals/cat.png",       spriteColor: "sprites/animals/cat_3d.png",       accentColor: "#FF7043", allowedRegions: ["US","AR","ID"] },
  { key: "duck",      spriteBw: "sprites/animals/duck.png",       spriteColor: "sprites/animals/duck_3d.png",      accentColor: "#FFEE58", allowedRegions: ["US","AR","ID"] },
  { key: "elephant",  spriteBw: "sprites/animals/elephant.png",   spriteColor: "sprites/animals/elephant_3d.png",  accentColor: "#7E57C2", allowedRegions: ["US","AR","ID"] },
  { key: "frog",      spriteBw: "sprites/animals/frog.png",       spriteColor: "sprites/animals/frog_3d.png",      accentColor: "#66BB6A", allowedRegions: ["US","AR","ID"] },
  { key: "penguin",   spriteBw: "sprites/animals/penguin.png",    spriteColor: "sprites/animals/penguin_3d.png",   accentColor: "#5C6BC0", allowedRegions: ["US","AR","ID"] },
  { key: "rabbit",    spriteBw: "sprites/animals/rabbit.png",     spriteColor: "sprites/animals/rabbit_3d.png",    accentColor: "#EC407A", allowedRegions: ["US","AR","ID"] },
  // Fruits
  { key: "apple",     spriteBw: "sprites/fruits/apple.png",       spriteColor: "sprites/fruits/apple_3d.png",      accentColor: "#EF5350", allowedRegions: ["US","AR","ID"] },
  { key: "banana",    spriteBw: "sprites/fruits/banana.png",      spriteColor: "sprites/fruits/banana_3d.png",     accentColor: "#FDD835", allowedRegions: ["US","AR","ID"] },
  { key: "cherry",    spriteBw: "sprites/fruits/cherry.png",      spriteColor: "sprites/fruits/cherry_3d.png",     accentColor: "#E91E63", allowedRegions: ["US","AR","ID"] },
  { key: "grapes",    spriteBw: "sprites/fruits/grapes.png",      spriteColor: "sprites/fruits/grapes_3d.png",     accentColor: "#9C27B0", allowedRegions: ["US","AR","ID"] },
  { key: "orange",    spriteBw: "sprites/fruits/orange.png",      spriteColor: "sprites/fruits/orange_3d.png",     accentColor: "#FF9800", allowedRegions: ["US","AR","ID"] },
  { key: "lemon",     spriteBw: "sprites/fruits/lemon.png",       spriteColor: "sprites/fruits/lemon_3d.png",      accentColor: "#FFEB3B", allowedRegions: ["US","AR","ID"] },
];

// ── Timing (frames at 30fps) ──────────────────────────────────────────────────
const ENTER_DUR     = 60;   // item slides in from left
const TRANSFORM_DUR = 20;   // B&W → color flash (at gate center)
const EXIT_DUR      = 60;   // color item slides out right
const PAUSE_DUR     = 30;   // gap before next item
const CYCLE         = ENTER_DUR + TRANSFORM_DUR + EXIT_DUR + PAUSE_DUR; // 170f

// ── Sparkle burst particles ───────────────────────────────────────────────────
const Sparkle: React.FC<{
  cx: number; cy: number; frame: number; color: string;
}> = ({ cx, cy, frame, color }) => {
  const PARTICLES = 10;
  return (
    <>
      {Array.from({ length: PARTICLES }, (_, i) => {
        const angle = (i / PARTICLES) * Math.PI * 2;
        const dist  = frame * 18;
        const px    = cx + Math.cos(angle) * dist;
        const py    = cy + Math.sin(angle) * dist;
        const op    = interpolate(frame, [0, 20], [1, 0], { extrapolateRight: "clamp" });
        const sz    = 14 + (i % 3) * 8;
        return (
          <div key={i} style={{
            position: "absolute",
            left: px - sz / 2, top: py - sz / 2,
            width: sz, height: sz,
            borderRadius: "50%",
            backgroundColor: i % 2 === 0 ? color : "#FFF",
            opacity: op,
            pointerEvents: "none",
          }} />
        );
      })}
    </>
  );
};

// ── Gate (magic transform zone) ───────────────────────────────────────────────
const MagicGate: React.FC<{
  cx: number; height: number; frame: number; activeColor: string;
}> = ({ cx, height: h, frame, activeColor }) => {
  const pulse = 1 + Math.sin(frame * 0.3) * 0.06;
  const glow  = `0 0 40px 12px ${activeColor}88`;
  return (
    <>
      {/* Left pillar */}
      <div style={{
        position: "absolute", left: cx - 90, top: h * 0.2,
        width: 22, height: h * 0.6,
        background: `linear-gradient(180deg, ${activeColor}, ${activeColor}88)`,
        borderRadius: 11, boxShadow: glow,
        transform: `scaleY(${pulse})`, transformOrigin: "bottom",
      }} />
      {/* Right pillar */}
      <div style={{
        position: "absolute", left: cx + 68, top: h * 0.2,
        width: 22, height: h * 0.6,
        background: `linear-gradient(180deg, ${activeColor}, ${activeColor}88)`,
        borderRadius: 11, boxShadow: glow,
        transform: `scaleY(${pulse})`, transformOrigin: "bottom",
      }} />
      {/* Arch top */}
      <div style={{
        position: "absolute",
        left: cx - 90, top: h * 0.2 - 24,
        width: 180, height: 48,
        borderRadius: "50% 50% 0 0",
        background: `linear-gradient(90deg, ${activeColor}cc, #fff8, ${activeColor}cc)`,
        boxShadow: glow,
        transform: `scaleX(${pulse})`, transformOrigin: "center",
      }} />
      {/* Neon curtain */}
      <div style={{
        position: "absolute",
        left: cx - 68, top: h * 0.2 + 24,
        width: 136, height: h * 0.6 - 24,
        background: `linear-gradient(90deg, transparent, ${activeColor}44, transparent)`,
        filter: "blur(8px)",
      }} />
    </>
  );
};

// ── Conveyor belt ─────────────────────────────────────────────────────────────
const ConveyorBelt: React.FC<{
  width: number; y: number; height: number; frame: number; color: string;
}> = ({ width: w, y, height: bh, frame, color }) => {
  const scrollX = -(frame * 4) % 80;
  return (
    <>
      {/* Belt body */}
      <div style={{
        position: "absolute", left: 0, top: y, width: w, height: bh,
        backgroundColor: "#37474f",
        borderTop: "4px solid #546e7a",
        borderBottom: "4px solid #263238",
      }} />
      {/* Moving dots */}
      <div style={{
        position: "absolute", left: 0, top: y + bh * 0.2, width: w, height: bh * 0.6,
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", top: 0, left: scrollX, right: scrollX - w,
          height: "100%",
          background: `repeating-linear-gradient(90deg, transparent 0px, transparent 60px, ${color}44 60px, ${color}44 64px, transparent 64px, transparent 80px)`,
        }} />
      </div>
      {/* Rollers */}
      {[0, w - 48].map((rx, i) => (
        <div key={i} style={{
          position: "absolute", left: rx, top: y - 12,
          width: 48, height: bh + 24,
          borderRadius: 24,
          background: "linear-gradient(135deg, #607d8b, #37474f)",
          border: "3px solid #455a64",
        }} />
      ))}
    </>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────
export interface FactoryTransformProps {
  region: Region;
  theme?: "animals" | "fruits" | "mixed";
  musicFile?: string;
  bgColor?: string;
}

export const FactoryTransform: React.FC<FactoryTransformProps> = ({
  region = "US",
  theme = "mixed",
  musicFile = "Pinball Spring.mp3",
  bgColor = "#E8F5E9",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const regionCfg = REGION_CONFIGS[region];

  // Filter items by region + theme
  let items = ALL_ITEMS.filter(it => it.allowedRegions.includes(region));
  if (theme === "animals") items = items.filter(it => ["cat","duck","elephant","frog","penguin","rabbit"].includes(it.key));
  if (theme === "fruits")  items = items.filter(it => ["apple","banana","cherry","grapes","orange","lemon"].includes(it.key));

  const BELT_Y    = height * 0.58;
  const BELT_H    = 80;
  const ITEM_SIZE = 240;
  const GATE_X    = width * 0.5;

  // Current item in cycle
  const loopLen    = items.length * CYCLE;
  const loopFrame  = frame % loopLen;
  const itemIdx    = Math.floor(loopFrame / CYCLE);
  const itemFrame  = loopFrame % CYCLE;
  const currentItem = items[itemIdx % items.length];

  // Item X position: enters from left (-ITEM_SIZE), crosses gate, exits right (width + ITEM_SIZE)
  const totalTravel = width + ITEM_SIZE * 2;
  const travelProgress = itemFrame < ENTER_DUR
    ? interpolate(itemFrame, [0, ENTER_DUR], [0, 0.45])          // approach gate
    : itemFrame < ENTER_DUR + TRANSFORM_DUR
    ? 0.45                                                          // pause at gate
    : interpolate(itemFrame, [ENTER_DUR + TRANSFORM_DUR, ENTER_DUR + TRANSFORM_DUR + EXIT_DUR], [0.45, 1.0]);

  const itemX = -ITEM_SIZE + travelProgress * totalTravel;

  // Transform: 0 = grayscale, 1 = full color (at gate moment)
  const colorProgress = itemFrame < ENTER_DUR ? 0
    : interpolate(itemFrame, [ENTER_DUR, ENTER_DUR + TRANSFORM_DUR], [0, 1], { extrapolateRight: "clamp" });

  // Victory bounce after transform
  const postTransformF = itemFrame - ENTER_DUR - TRANSFORM_DUR;
  const victoryBounce  = postTransformF > 0
    ? Math.abs(Math.sin(postTransformF * 0.25)) * 30
    : 0;

  // Sparkle triggered exactly at transform moment
  const sparkleFrame = itemFrame - ENTER_DUR;

  // Background parallax
  const bgLayers: ParallaxLayer[] = [
    { background: `linear-gradient(180deg, ${bgColor} 0%, ${bgColor}bb 100%)`, speed: 0.0, opacity: 1 },
    { background: "linear-gradient(180deg, transparent 60%, rgba(0,0,0,0.04) 100%)", speed: 0.12, opacity: 1 },
  ];

  // Gate color pulses with accent
  const gateColor = currentItem?.accentColor ?? "#00BCD4";
  const gatePulse = gateColor;

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {musicFile && <Audio src={staticFile(`music/${musicFile}`)} volume={0.2} loop />}

      <BackgroundParallax layers={bgLayers} />

      {/* Factory walls / ceiling */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: height * 0.18,
        background: "linear-gradient(180deg, #b0bec5 0%, #cfd8dc 100%)",
        borderBottom: "6px solid #90a4ae",
      }} />

      {/* Ceiling lights */}
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} style={{
          position: "absolute",
          left: (i + 0.5) * (width / 5) - 16, top: height * 0.18 - 24,
          width: 32, height: 32, borderRadius: "50%",
          backgroundColor: i % 2 === 0 ? "#FFEE58" : "#E8F5E9",
          boxShadow: `0 0 20px 8px ${i % 2 === 0 ? "#FFEE58" : "#E8F5E9"}`,
          opacity: 0.85,
        }} />
      ))}

      {/* Magic gate */}
      {currentItem && (
        <MagicGate
          cx={GATE_X}
          height={height}
          frame={frame}
          activeColor={gatePulse}
        />
      )}

      {/* Conveyor belt */}
      <ConveyorBelt
        width={width} y={BELT_Y} height={BELT_H}
        frame={frame}
        color={currentItem?.accentColor ?? "#00BCD4"}
      />

      {/* Current item */}
      {currentItem && (
        <div style={{
          position: "absolute",
          left: itemX,
          top: BELT_Y - ITEM_SIZE + 20 - victoryBounce,
          width: ITEM_SIZE,
          height: ITEM_SIZE,
          willChange: "transform",
        }}>
          {/* B&W layer (fades out) */}
          <Img
            src={staticFile(currentItem.spriteBw)}
            style={{
              position: "absolute", inset: 0,
              width: ITEM_SIZE, height: ITEM_SIZE, objectFit: "contain",
              filter: `grayscale(1) brightness(0.7)`,
              opacity: 1 - colorProgress,
            }}
          />
          {/* Color layer (fades in) */}
          <Img
            src={staticFile(currentItem.spriteColor)}
            style={{
              position: "absolute", inset: 0,
              width: ITEM_SIZE, height: ITEM_SIZE, objectFit: "contain",
              opacity: colorProgress,
              transform: `scale(${1 + colorProgress * 0.12})`,
            }}
          />
        </div>
      )}

      {/* Sparkle burst at gate center */}
      {currentItem && sparkleFrame >= 0 && sparkleFrame < 20 && (
        <Sparkle
          cx={GATE_X}
          cy={BELT_Y - ITEM_SIZE * 0.5}
          frame={sparkleFrame}
          color={currentItem.accentColor}
        />
      )}

      {/* Pop audio at transform */}
      {currentItem && sparkleFrame >= 0 && sparkleFrame < 3 && (
        <Audio
          src={staticFile("audio/this_is_a_bear__bear__bear.mp3")}
          volume={0}
        />
      )}

      {/* Floor */}
      <div style={{
        position: "absolute",
        bottom: 0, left: 0, right: 0,
        height: height - BELT_Y - BELT_H,
        background: "linear-gradient(180deg, #eceff1 0%, #cfd8dc 100%)",
        borderTop: "6px solid #b0bec5",
      }} />

      {/* Counter badge: which item N / total */}
      <div style={{
        position: "absolute", top: height * 0.06, right: 60,
        display: "flex", gap: 12,
      }}>
        {items.map((it, i) => (
          <div key={it.key} style={{
            width: 22, height: 22, borderRadius: "50%",
            backgroundColor: i === itemIdx % items.length
              ? it.accentColor : "#cfd8dc",
            boxShadow: i === itemIdx % items.length
              ? `0 0 8px 3px ${it.accentColor}` : "none",
            transition: "background-color 0.2s",
          }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
