/**
 * PeekABooEggs — magic egg hatches → animal springs out.
 * No text. Universal EN/AR/ID (pig→panda swap for AR/ID).
 *
 * Per cycle (180f = 6s at 30fps):
 *   0–45f   FALL  — egg drops from top with spring squeeze
 *   45–90f  SHAKE — accelerating sin shake before burst
 *   90–120f BURST — egg scale→0 + animal spring-in
 *   120–180f CELEBRATE — animal bounces + exits right
 *
 * 4 eggs × 180f = 720f total loop. Composition: 1350f.
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { BackgroundParallax, ParallaxLayer } from "./components/BackgroundParallax";
import type { Region } from "./types/RegionConfig";

// ── Timing ────────────────────────────────────────────────────────────────────
const FALL_DUR      = 45;
const SHAKE_DUR     = 45;
const BURST_DUR     = 30;
const CELEBRATE_DUR = 60;
const CYCLE         = FALL_DUR + SHAKE_DUR + BURST_DUR + CELEBRATE_DUR; // 180f

// ── Egg catalogue ─────────────────────────────────────────────────────────────
interface EggCfg {
  shellColor: string;
  spotColor: string;
  animalSprite: (region: Region) => string;
  audio: string | null;
  bgColor: string;
  accentColor: string;
}

const EGGS: EggCfg[] = [
  {
    shellColor: "#7BC67E",
    spotColor:  "#A5D6A7",
    animalSprite: () => "sprites/animals/cow.png",
    audio: null,
    bgColor:  "#F1F8E9",
    accentColor: "#66BB6A",
  },
  {
    shellColor: "#64B5F6",
    spotColor:  "#90CAF9",
    animalSprite: () => "sprites/animals/lion.png",
    audio: "this_is_a_lion__lion__lion.mp3",
    bgColor:  "#E3F2FD",
    accentColor: "#42A5F5",
  },
  {
    shellColor: "#F48FB1",
    spotColor:  "#F8BBD0",
    animalSprite: (r: Region) =>
      r === "US" ? "sprites/animals/pig.png" : "sprites/animals/panda.png",
    audio: null,
    bgColor:  "#FCE4EC",
    accentColor: "#EC407A",
  },
  {
    shellColor: "#FFF176",
    spotColor:  "#FFF9C4",
    animalSprite: () => "sprites/animals/duck.png",
    audio: null,
    bgColor:  "#FFFDE7",
    accentColor: "#FDD835",
  },
];

// ── CSS Egg shape ─────────────────────────────────────────────────────────────
const Egg: React.FC<{
  cx: number; cy: number; size: number;
  shellColor: string; spotColor: string;
  scaleX: number; scaleY: number; opacity?: number;
  rotation?: number;
}> = ({ cx, cy, size, shellColor, spotColor, scaleX, scaleY, opacity = 1, rotation = 0 }) => {
  const w = size * 0.7;
  const h = size;
  return (
    <div style={{
      position: "absolute",
      left: cx - w / 2,
      top: cy - h / 2,
      width: w,
      height: h,
      transform: `scaleX(${scaleX}) scaleY(${scaleY}) rotate(${rotation}deg)`,
      transformOrigin: "center center",
      opacity,
    }}>
      {/* Egg body */}
      <div style={{
        position: "absolute",
        inset: 0,
        borderRadius: "50% 50% 50% 50% / 60% 60% 40% 40%",
        background: `radial-gradient(ellipse at 35% 30%, ${spotColor} 0%, ${shellColor} 55%)`,
        boxShadow: `0 12px 40px ${shellColor}88, inset 0 -6px 20px rgba(0,0,0,0.12)`,
      }} />
      {/* Shine spot */}
      <div style={{
        position: "absolute",
        left: "18%", top: "12%",
        width: "28%", height: "22%",
        borderRadius: "50%",
        background: "rgba(255,255,255,0.55)",
        filter: "blur(6px)",
      }} />
    </div>
  );
};

// ── Crack lines (appear during shake phase) ───────────────────────────────────
const EggCracks: React.FC<{
  cx: number; cy: number; size: number; progress: number; color: string;
}> = ({ cx, cy, size, progress, color }) => {
  const op = interpolate(progress, [0.4, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (op <= 0) return null;
  const w = size * 0.7;
  const h = size;
  return (
    <svg
      style={{ position: "absolute", left: cx - w / 2, top: cy - h / 2, pointerEvents: "none" }}
      width={w} height={h}
    >
      <path d={`M ${w * 0.35} ${h * 0.42} L ${w * 0.28} ${h * 0.52} L ${w * 0.38} ${h * 0.58}`}
        stroke={color} strokeWidth={3} fill="none" opacity={op} strokeLinecap="round" />
      <path d={`M ${w * 0.62} ${h * 0.45} L ${w * 0.70} ${h * 0.54} L ${w * 0.58} ${h * 0.62}`}
        stroke={color} strokeWidth={2.5} fill="none" opacity={op * 0.8} strokeLinecap="round" />
    </svg>
  );
};

// ── Shell shard burst ─────────────────────────────────────────────────────────
const ShellBurst: React.FC<{
  cx: number; cy: number; frame: number; color: string;
}> = ({ cx, cy, frame, color }) => {
  const SHARDS = 8;
  return (
    <>
      {Array.from({ length: SHARDS }, (_, i) => {
        const angle  = (i / SHARDS) * Math.PI * 2 + 0.3;
        const dist   = frame * 22;
        const px     = cx + Math.cos(angle) * dist;
        const py     = cy + Math.sin(angle) * dist + frame * frame * 0.4; // gravity
        const op     = interpolate(frame, [0, BURST_DUR], [1, 0], { extrapolateRight: "clamp" });
        const rot    = frame * (i % 2 === 0 ? 15 : -12);
        const sz     = 18 + (i % 3) * 10;
        return (
          <div key={i} style={{
            position: "absolute",
            left: px - sz / 2, top: py - sz / 2,
            width: sz, height: sz,
            borderRadius: "50% 50% 50% 50% / 60% 60% 40% 40%",
            background: color,
            opacity: op,
            transform: `rotate(${rot}deg)`,
            pointerEvents: "none",
          }} />
        );
      })}
    </>
  );
};

// ── Stars celebration ─────────────────────────────────────────────────────────
const StarBurst: React.FC<{ cx: number; cy: number; frame: number; color: string }> = ({
  cx, cy, frame, color,
}) => {
  const STARS = 6;
  return (
    <>
      {Array.from({ length: STARS }, (_, i) => {
        const angle = (i / STARS) * Math.PI * 2;
        const dist  = 60 + i * 15;
        const bob   = Math.sin(frame * 0.25 + i) * 12;
        const px    = cx + Math.cos(angle) * dist;
        const py    = cy + Math.sin(angle) * dist + bob;
        const op    = interpolate(frame, [0, 15, CELEBRATE_DUR - 10, CELEBRATE_DUR], [0, 1, 1, 0], { extrapolateRight: "clamp" });
        return (
          <div key={i} style={{
            position: "absolute",
            left: px - 14, top: py - 14,
            fontSize: 28,
            opacity: op,
            transform: `rotate(${frame * 4 + i * 60}deg)`,
            userSelect: "none",
          }}>⭐</div>
        );
      })}
    </>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────
export interface PeekABooEggsProps {
  region?: Region;
  musicFile?: string;
  bgColor?: string;
}

export const PeekABooEggs: React.FC<PeekABooEggsProps> = ({
  region = "US",
  musicFile = "Happy Happy Game Show.mp3",
  bgColor = "#FFF8F0",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const totalCycle = EGGS.length * CYCLE;
  const loopFrame  = frame % totalCycle;
  const eggIdx     = Math.floor(loopFrame / CYCLE);
  const localF     = loopFrame % CYCLE;
  const egg        = EGGS[eggIdx];

  const cx = width  / 2;
  const cy = height / 2;
  const EGG_SIZE = 260;
  const ANIMAL_SIZE = 300;

  // ── Phase detection ────────────────────────────────────────────────────────
  const isFall      = localF < FALL_DUR;
  const isShake     = localF >= FALL_DUR && localF < FALL_DUR + SHAKE_DUR;
  const isBurst     = localF >= FALL_DUR + SHAKE_DUR && localF < FALL_DUR + SHAKE_DUR + BURST_DUR;
  const isCelebrate = localF >= FALL_DUR + SHAKE_DUR + BURST_DUR;

  const fallF      = localF;
  const shakeF     = localF - FALL_DUR;
  const burstF     = localF - FALL_DUR - SHAKE_DUR;
  const celebrateF = localF - FALL_DUR - SHAKE_DUR - BURST_DUR;

  // ── Egg fall ──────────────────────────────────────────────────────────────
  const fallSp = spring({
    frame: fallF,
    fps,
    config: { damping: 12, stiffness: 100, mass: 0.7 },
    durationInFrames: FALL_DUR,
  });
  const eggY = isFall
    ? interpolate(fallSp, [0, 1], [cy - height * 0.8, cy], { extrapolateRight: "clamp" })
    : cy;

  // Squash on land: scaleX 1.3, scaleY 0.75 → back to 1
  const squash = isFall
    ? interpolate(fallSp, [0.7, 1], [1, 1.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 1;
  const squashY = isFall
    ? interpolate(fallSp, [0.7, 1], [1, 0.78], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 1;
  const eggScaleX = isBurst
    ? interpolate(burstF, [0, BURST_DUR * 0.5], [1, 0], { extrapolateRight: "clamp" })
    : squash;
  const eggScaleY = isBurst
    ? interpolate(burstF, [0, BURST_DUR * 0.5], [1, 0], { extrapolateRight: "clamp" })
    : squashY;

  // ── Shake ─────────────────────────────────────────────────────────────────
  const shakeIntensity = isShake
    ? interpolate(shakeF, [0, SHAKE_DUR], [8, 22], { extrapolateRight: "clamp" })
    : 0;
  const shakeX = isShake ? Math.sin(shakeF * 0.8) * shakeIntensity : 0;
  const shakeRot = isShake ? Math.sin(shakeF * 0.7) * (shakeIntensity * 0.4) : 0;
  const crackProgress = isShake ? shakeF / SHAKE_DUR : (isBurst ? 1 : 0);

  // ── Animal reveal ─────────────────────────────────────────────────────────
  const animalSp = spring({
    frame: isBurst ? burstF - 5 : celebrateF,
    fps,
    config: { damping: 8, stiffness: 120, mass: 0.5 },
    durationInFrames: 20,
  });
  const showAnimal  = isBurst || isCelebrate;
  const animalScale = showAnimal
    ? interpolate(isBurst ? animalSp : 1, [0, 1], [0, 1], { extrapolateRight: "clamp" })
    : 0;

  // ── Celebrate exit ────────────────────────────────────────────────────────
  const celebrateBounce = isCelebrate
    ? Math.abs(Math.sin(celebrateF * 0.25)) * 40
    : 0;
  const exitX = isCelebrate
    ? interpolate(celebrateF, [CELEBRATE_DUR - 25, CELEBRATE_DUR], [0, width * 0.7], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 0;
  const exitOp = isCelebrate
    ? interpolate(celebrateF, [CELEBRATE_DUR - 15, CELEBRATE_DUR], [1, 0], {
        extrapolateLeft: "clamp", extrapolateRight: "clamp",
      })
    : 1;

  // ── Background ────────────────────────────────────────────────────────────
  const bgLayers: ParallaxLayer[] = [
    { background: `linear-gradient(180deg, ${egg.bgColor} 0%, ${bgColor} 100%)`, speed: 0, opacity: 1 },
    { background: "radial-gradient(ellipse at 50% 30%, rgba(255,255,255,0.5) 0%, transparent 65%)", speed: 0.04, opacity: 0.9 },
  ];

  // ── Floating confetti backdrop ────────────────────────────────────────────
  const confettiColors = [egg.accentColor, egg.shellColor, "#FFF", "#FFD700"];
  const eggX = cx + shakeX;
  const finalEggY = (isBurst || isCelebrate) ? cy : eggY;

  const animalX = cx + exitX;
  const animalY = cy - celebrateBounce;

  const animalSprite = egg.animalSprite(region);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {musicFile && <Audio src={staticFile(`music/${musicFile}`)} volume={0.22} loop />}

      {/* Audio cue on reveal */}
      {egg.audio && isBurst && burstF >= 5 && burstF < 10 && (
        <Audio src={staticFile(`audio/${egg.audio}`)} volume={1} />
      )}

      <BackgroundParallax layers={bgLayers} />

      {/* Floating confetti */}
      {Array.from({ length: 18 }, (_, i) => {
        const x = (i * 113 + eggIdx * 50) % width;
        const yDrift = (frame * 2.5 + i * 60) % (height + 60);
        const op = 0.12 + Math.sin(frame / fps + i * 0.9) * 0.06;
        return (
          <div key={i} style={{
            position: "absolute",
            left: x, top: yDrift - 30,
            width: 16, height: 16,
            borderRadius: i % 3 === 0 ? "50%" : "3px",
            backgroundColor: confettiColors[i % confettiColors.length],
            opacity: op,
            transform: `rotate(${frame * 2 + i * 25}deg)`,
            pointerEvents: "none",
          }} />
        );
      })}

      {/* Shell burst shards */}
      {isBurst && <ShellBurst cx={eggX} cy={finalEggY} frame={burstF} color={egg.shellColor} />}

      {/* Animal (behind egg in z-order when bursting) */}
      {showAnimal && (
        <div style={{
          position: "absolute",
          left: animalX - ANIMAL_SIZE / 2,
          top:  animalY - ANIMAL_SIZE * 0.9,
          width: ANIMAL_SIZE, height: ANIMAL_SIZE,
          transform: `scale(${animalScale})`,
          transformOrigin: "center bottom",
          opacity: exitOp,
        }}>
          <Img
            src={staticFile(animalSprite)}
            style={{ width: ANIMAL_SIZE, height: ANIMAL_SIZE, objectFit: "contain" }}
          />
        </div>
      )}

      {/* Celebration stars */}
      {isCelebrate && (
        <StarBurst cx={animalX} cy={animalY - ANIMAL_SIZE * 0.4} frame={celebrateF} color={egg.accentColor} />
      )}

      {/* Egg shell */}
      {!isCelebrate && (
        <>
          <Egg
            cx={eggX} cy={finalEggY}
            size={EGG_SIZE}
            shellColor={egg.shellColor}
            spotColor={egg.spotColor}
            scaleX={eggScaleX}
            scaleY={eggScaleY}
            rotation={shakeRot}
            opacity={isBurst ? interpolate(burstF, [0, BURST_DUR * 0.6], [1, 0], { extrapolateRight: "clamp" }) : 1}
          />
          <EggCracks
            cx={eggX} cy={finalEggY}
            size={EGG_SIZE}
            progress={crackProgress}
            color={egg.shellColor}
          />
        </>
      )}

      {/* Ground shadow */}
      <div style={{
        position: "absolute",
        bottom: 0, left: 0, right: 0, height: height * 0.12,
        background: "linear-gradient(to top, rgba(0,0,0,0.07) 0%, transparent 100%)",
        pointerEvents: "none",
      }} />

      {/* Egg counter dots */}
      <div style={{
        position: "absolute",
        bottom: height * 0.06,
        left: 0, right: 0,
        display: "flex", justifyContent: "center", gap: 18,
      }}>
        {EGGS.map((e, i) => (
          <div key={i} style={{
            width: 18, height: 18,
            borderRadius: "50% 50% 50% 50% / 60% 60% 40% 40%",
            backgroundColor: i === eggIdx ? e.shellColor : "#cfd8dc",
            boxShadow: i === eggIdx ? `0 0 10px 4px ${e.shellColor}` : "none",
          }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
