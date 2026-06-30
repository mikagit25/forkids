/**
 * PeekABoo — "Who's hiding?" mechanic for toddlers 0+.
 * itemsCount colored boxes line up. Each box vibrates → spring-jumps up →
 * reveals an animal underneath with a matching audio cue.
 * No text on screen. Universal EN/AR/ID content.
 *
 * Timing per item: VIBRATE 30f → JUMP 15f → REVEAL 60f → HOLD 30f → RESET 30f
 * Total cycle ≈ itemsCount × 165f at 30fps ≈ 55s
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig, Sequence,
} from "remotion";
import { BackgroundParallax } from "./components/BackgroundParallax";
import { SpringBox } from "./components/SpringBox";
import type { Region } from "./types/RegionConfig";
import { REGION_CONFIGS } from "./types/RegionConfig";

// ── Animal catalogue ──────────────────────────────────────────────────────────
interface AnimalEntry {
  key: string;
  sprite: string;             // path inside remotion/public/sprites/
  audio: string;              // path inside remotion/public/audio/
  color: string;              // box accent color
}

const ALL_ANIMALS: AnimalEntry[] = [
  { key: "cat",      sprite: "sprites/animals/cat.png",      audio: "this_is_a_cat__cat__cat.mp3",         color: "#FF7043" },
  { key: "dog",      sprite: "sprites/animals/dog.png",       audio: "this_is_a_dog__dog__dog.mp3",          color: "#42A5F5" },
  { key: "elephant", sprite: "sprites/animals/elephant.png",  audio: "this_is_a_elephant__elephant__elephant.mp3", color: "#7E57C2" },
  { key: "frog",     sprite: "sprites/animals/frog.png",      audio: "this_is_a_frog__frog__frog.mp3",       color: "#66BB6A" },
  { key: "lion",     sprite: "sprites/animals/lion.png",      audio: "this_is_a_lion__lion__lion.mp3",       color: "#FFA726" },
  { key: "monkey",   sprite: "sprites/animals/monkey.png",    audio: "this_is_a_monkey__monkey__monkey.mp3", color: "#8D6E63" },
  { key: "owl",      sprite: "sprites/animals/owl.png",       audio: "this_is_a_owl__owl__owl.mp3",          color: "#26A69A" },
  { key: "penguin",  sprite: "sprites/animals/penguin.png",   audio: "this_is_a_penguin__penguin__penguin.mp3", color: "#5C6BC0" },
  { key: "rabbit",   sprite: "sprites/animals/rabbit.png",    audio: "this_is_a_rabbit__rabbit__rabbit.mp3", color: "#EC407A" },
  { key: "tiger",    sprite: "sprites/animals/tiger.png",     audio: "this_is_a_tiger__tiger__tiger.mp3",    color: "#FF8F00" },
  { key: "bear",     sprite: "sprites/characters/bear_happy_3d.png", audio: "this_is_a_bear__bear__bear.mp3", color: "#A1887F" },
  { key: "duck",     sprite: "sprites/animals/duck.png",      audio: "this_is_a_fish__fish__fish.mp3",       color: "#FFEE58" },
];

/** Animals not allowed for AR/ID */
const FORBIDDEN_AR_ID = new Set(["pig"]);

// ── Timing constants (frames at 30fps) ────────────────────────────────────────
const VIBRATE_DUR = 30;  // box shakes
const JUMP_DUR    = 15;  // box springs up
const REVEAL_DUR  = 90;  // animal visible + audio
const HOLD_DUR    = 30;  // all settle
const RESET_DUR   = 30;  // box comes back down
const CYCLE       = VIBRATE_DUR + JUMP_DUR + REVEAL_DUR + HOLD_DUR + RESET_DUR; // 195f

// ── Single box + animal slot ───────────────────────────────────────────────────
const PeekSlot: React.FC<{
  animal: AnimalEntry;
  slotX: number;
  slotY: number;
  boxSize: number;
  startF: number;
  frame: number;
  fps: number;
  playAudio: boolean;
}> = ({ animal, slotX, slotY, boxSize, startF, frame, fps, playAudio }) => {
  const localF = frame - startF;
  if (localF < 0) return null;

  const phase = localF < VIBRATE_DUR ? "vibrate"
    : localF < VIBRATE_DUR + JUMP_DUR ? "jump"
    : localF < VIBRATE_DUR + JUMP_DUR + REVEAL_DUR ? "reveal"
    : localF < VIBRATE_DUR + JUMP_DUR + REVEAL_DUR + HOLD_DUR ? "hold"
    : "reset";

  // Box vibrate: horizontal sine shake
  const vibrateX = phase === "vibrate"
    ? Math.sin(localF * 1.8) * 14
    : 0;

  // Box jump: springs upward
  const jumpSp = spring({
    frame: localF - VIBRATE_DUR,
    fps,
    config: { damping: 10, stiffness: 100, mass: 0.5 },
    durationInFrames: 20,
  });
  const boxLiftY = (phase === "jump" || phase === "reveal" || phase === "hold")
    ? interpolate(jumpSp, [0, 1], [0, -(boxSize * 1.6)], { extrapolateRight: "clamp" })
    : phase === "reset"
    ? interpolate(localF - VIBRATE_DUR - JUMP_DUR - REVEAL_DUR - HOLD_DUR,
                  [0, RESET_DUR], [-(boxSize * 1.6), 0], { extrapolateRight: "clamp" })
    : 0;

  // Animal reveal spring
  const revealF = localF - VIBRATE_DUR - JUMP_DUR;
  const revealSp = spring({
    frame: revealF,
    fps,
    config: { damping: 10, mass: 0.5, stiffness: 100 },
    durationInFrames: 25,
  });
  const animalScale = (phase === "reveal" || phase === "hold")
    ? interpolate(revealSp, [0, 1], [0, 1], { extrapolateRight: "clamp" })
    : phase === "reset"
    ? interpolate(localF - VIBRATE_DUR - JUMP_DUR - REVEAL_DUR - HOLD_DUR,
                  [0, RESET_DUR], [1, 0], { extrapolateRight: "clamp" })
    : 0;

  // Victory bounce when fully revealed
  const victoryBounce = (phase === "reveal" || phase === "hold")
    ? Math.abs(Math.sin(revealF * 0.18)) * 18
    : 0;

  const isRevealed = phase === "reveal" || phase === "hold";

  return (
    <g>
      {/* Animal (beneath box in z-order — rendered first) */}
      {animalScale > 0.01 && (
        <div style={{
          position: "absolute",
          left: slotX - boxSize * 0.5,
          top: slotY - boxSize * 1.1,
          width: boxSize,
          height: boxSize,
          transform: `scale(${animalScale}) translateY(${-victoryBounce}px)`,
          transformOrigin: "center bottom",
        }}>
          <Img
            src={staticFile(animal.sprite)}
            style={{ width: boxSize, height: boxSize, objectFit: "contain" }}
          />
        </div>
      )}

      {/* Audio cue — plays exactly when animal appears */}
      {playAudio && isRevealed && revealF >= 0 && revealF < 5 && (
        <Audio src={staticFile(`audio/${animal.audio}`)} volume={1} />
      )}

      {/* Box */}
      <div style={{
        position: "absolute",
        left: slotX - boxSize * 0.5,
        top: slotY - boxSize * 0.5 + boxLiftY,
        width: boxSize,
        height: boxSize,
        transform: `translateX(${vibrateX}px)`,
        willChange: "transform",
      }}>
        {/* Box body */}
        <div style={{
          width: "100%",
          height: "100%",
          borderRadius: 20,
          background: `linear-gradient(145deg, ${animal.color}ee, ${animal.color}99)`,
          boxShadow: `0 12px 40px ${animal.color}66, inset 0 2px 8px rgba(255,255,255,0.3)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}>
          {/* Question mark — hidden once revealed */}
          {!isRevealed && (
            <span style={{
              fontSize: boxSize * 0.55,
              filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.2))",
              userSelect: "none",
            }}>
              ❓
            </span>
          )}
        </div>
      </div>
    </g>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────
export interface PeekABooProps {
  region: Region;
  itemsCount: number;
  bgColor?: string;
  musicFile?: string;
  /** Override which animals appear (default: picks from allowed list for region) */
  animals?: string[];
}

export const PeekABoo: React.FC<PeekABooProps> = ({
  region = "US",
  itemsCount = 5,
  bgColor = "#FFF8E1",
  musicFile = "Happy Happy Game Show.mp3",
  animals: animalsOverride,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();

  const regionCfg = REGION_CONFIGS[region];
  const allowed = animalsOverride ?? regionCfg.allowedAnimals;

  // Pick itemsCount animals (filter forbidden, pick round-robin)
  const selectedAnimals = ALL_ANIMALS
    .filter(a => allowed.includes(a.key) && !FORBIDDEN_AR_ID.has(a.key) || region === "US")
    .slice(0, itemsCount);

  const BOX_SIZE = Math.min(260, (width * 0.8) / itemsCount);
  const SLOT_Y   = height * 0.62;
  const spacing  = (width * 0.85) / (itemsCount - 1 || 1);
  const startX   = width * 0.075 + BOX_SIZE * 0.5;

  // Background layers: warm gradient
  const bgLayers = [
    { background: `linear-gradient(180deg, ${bgColor} 0%, ${bgColor}cc 100%)`, speed: 0.0, opacity: 1 },
    { background: "radial-gradient(ellipse at 20% 20%, rgba(255,255,255,0.5) 0%, transparent 60%)", speed: 0.05, opacity: 0.8 },
  ];

  // Looping: total cycle for all items, then repeat
  const totalCycle = itemsCount * CYCLE + HOLD_DUR * 2;
  const loopFrame  = frame % totalCycle;

  // Fade in
  const fadeIn = interpolate(frame, [0, fps], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ overflow: "hidden", opacity: fadeIn }}>
      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={0.22} loop />
      )}

      <BackgroundParallax layers={bgLayers} />

      {/* Floating stars background */}
      {Array.from({ length: 20 }, (_, i) => {
        const x = (i * 97) % width;
        const y = (i * 113) % (height * 0.5);
        const op = 0.15 + Math.sin(frame / fps * 0.5 + i) * 0.1;
        const sz = 12 + (i % 4) * 8;
        return (
          <div key={i} style={{
            position: "absolute", left: x, top: y,
            fontSize: sz, opacity: op, userSelect: "none",
          }}>⭐</div>
        );
      })}

      {/* Slots */}
      {selectedAnimals.map((animal, idx) => {
        const slotX   = startX + idx * spacing;
        const startF  = idx * CYCLE;
        return (
          <PeekSlot
            key={animal.key}
            animal={animal}
            slotX={slotX}
            slotY={SLOT_Y}
            boxSize={BOX_SIZE}
            startF={startF}
            frame={loopFrame}
            fps={fps}
            playAudio={region === "US"}  // audio only on EN channel
          />
        );
      })}

      {/* Ground shadow strip */}
      <div style={{
        position: "absolute",
        bottom: 0, left: 0, right: 0, height: height * 0.22,
        background: "linear-gradient(to top, rgba(0,0,0,0.06) 0%, transparent 100%)",
        pointerEvents: "none",
      }} />
    </AbsoluteFill>
  );
};
