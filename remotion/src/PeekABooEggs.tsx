/**
 * PeekABooEggs — magic egg hatches → animal springs out.
 * No text. Universal EN/AR/ID (pig→panda swap done by generator in props).
 *
 * Per cycle (180f = 6s at 30fps):
 *   0–45f    FALL      — egg drops from top with spring squeeze
 *   45–90f   SHAKE     — accelerating sin shake + crack lines
 *   90–120f  BURST     — egg scale→0 + animal spring-in + shard particles
 *   120–180f CELEBRATE — animal bounces + exits right
 *
 * Loops via frame % (eggs.length * 180). Works as 60s short or 5-min loop.
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { BackgroundParallax, ParallaxLayer } from "./components/BackgroundParallax";

// ── Timing ────────────────────────────────────────────────────────────────────
const FALL_DUR      = 45;
const SHAKE_DUR     = 45;
const BURST_DUR     = 30;
const CELEBRATE_DUR = 60;
const CYCLE         = FALL_DUR + SHAKE_DUR + BURST_DUR + CELEBRATE_DUR; // 180f

// ── Public types ──────────────────────────────────────────────────────────────
export interface EggItem {
  shellColor:   string;
  spotColor:    string;
  /** Full static path, e.g. "sprites/animals/cow.png" */
  animalSprite: string;
  /** Audio file relative to remotion/public/audio/ (optional) */
  audio?:       string;
  bgColor:      string;
  accentColor:  string;
}

// ── Default eggs (farm theme, US-safe — pig included) ─────────────────────────
const DEFAULT_EGGS: EggItem[] = [
  { shellColor: "#7BC67E", spotColor: "#A5D6A7", animalSprite: "sprites/animals/cow.png",
    accentColor: "#66BB6A", bgColor: "#F1F8E9" },
  { shellColor: "#64B5F6", spotColor: "#90CAF9", animalSprite: "sprites/animals/lion.png",
    audio: "this_is_a_lion__lion__lion.mp3", accentColor: "#42A5F5", bgColor: "#E3F2FD" },
  { shellColor: "#F48FB1", spotColor: "#F8BBD0", animalSprite: "sprites/animals/pig.png",
    accentColor: "#EC407A", bgColor: "#FCE4EC" },
  { shellColor: "#FFF176", spotColor: "#FFF9C4", animalSprite: "sprites/animals/duck.png",
    accentColor: "#FDD835", bgColor: "#FFFDE7" },
];

// ── CSS Egg shape ─────────────────────────────────────────────────────────────
const Egg: React.FC<{
  cx: number; cy: number; size: number;
  shellColor: string; spotColor: string;
  scaleX: number; scaleY: number; opacity?: number; rotation?: number;
}> = ({ cx, cy, size, shellColor, spotColor, scaleX, scaleY, opacity = 1, rotation = 0 }) => {
  const w = size * 0.7; const h = size;
  return (
    <div style={{
      position: "absolute", left: cx - w / 2, top: cy - h / 2, width: w, height: h,
      transform: `scaleX(${scaleX}) scaleY(${scaleY}) rotate(${rotation}deg)`,
      transformOrigin: "center center", opacity,
    }}>
      <div style={{
        position: "absolute", inset: 0,
        borderRadius: "50% 50% 50% 50% / 60% 60% 40% 40%",
        background: `radial-gradient(ellipse at 35% 30%, ${spotColor} 0%, ${shellColor} 55%)`,
        boxShadow: `0 12px 40px ${shellColor}88, inset 0 -6px 20px rgba(0,0,0,0.12)`,
      }} />
      <div style={{
        position: "absolute", left: "18%", top: "12%", width: "28%", height: "22%",
        borderRadius: "50%", background: "rgba(255,255,255,0.55)", filter: "blur(6px)",
      }} />
    </div>
  );
};

// ── Crack lines ───────────────────────────────────────────────────────────────
const EggCracks: React.FC<{ cx: number; cy: number; size: number; progress: number }> = ({
  cx, cy, size, progress,
}) => {
  const op = interpolate(progress, [0.4, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (op <= 0) return null;
  const w = size * 0.7; const h = size;
  return (
    <svg style={{ position: "absolute", left: cx - w / 2, top: cy - h / 2, pointerEvents: "none" }}
      width={w} height={h}>
      <path d={`M ${w*0.35} ${h*0.42} L ${w*0.28} ${h*0.52} L ${w*0.38} ${h*0.58}`}
        stroke="#555" strokeWidth={3} fill="none" opacity={op} strokeLinecap="round" />
      <path d={`M ${w*0.62} ${h*0.45} L ${w*0.70} ${h*0.54} L ${w*0.58} ${h*0.62}`}
        stroke="#555" strokeWidth={2.5} fill="none" opacity={op * 0.8} strokeLinecap="round" />
    </svg>
  );
};

// ── Shell burst shards ────────────────────────────────────────────────────────
const ShellBurst: React.FC<{ cx: number; cy: number; frame: number; color: string }> = ({
  cx, cy, frame, color,
}) => (
  <>
    {Array.from({ length: 8 }, (_, i) => {
      const angle = (i / 8) * Math.PI * 2 + 0.3;
      const dist  = frame * 22;
      const op    = interpolate(frame, [0, BURST_DUR], [1, 0], { extrapolateRight: "clamp" });
      const sz    = 18 + (i % 3) * 10;
      return (
        <div key={i} style={{
          position: "absolute",
          left: cx + Math.cos(angle) * dist - sz / 2,
          top:  cy + Math.sin(angle) * dist + frame * frame * 0.4 - sz / 2,
          width: sz, height: sz,
          borderRadius: "50% 50% 50% 50% / 60% 60% 40% 40%",
          background: color, opacity: op,
          transform: `rotate(${frame * (i % 2 === 0 ? 15 : -12)}deg)`,
          pointerEvents: "none",
        }} />
      );
    })}
  </>
);

// ── Star celebration ──────────────────────────────────────────────────────────
const StarBurst: React.FC<{ cx: number; cy: number; frame: number; color: string }> = ({
  cx, cy, frame, color,
}) => (
  <>
    {Array.from({ length: 6 }, (_, i) => {
      const angle = (i / 6) * Math.PI * 2;
      const dist  = 60 + i * 15;
      const bob   = Math.sin(frame * 0.25 + i) * 12;
      const op    = interpolate(frame, [0, 15, CELEBRATE_DUR - 10, CELEBRATE_DUR],
                                [0, 1, 1, 0], { extrapolateRight: "clamp" });
      return (
        <div key={i} style={{
          position: "absolute",
          left: cx + Math.cos(angle) * dist - 14,
          top:  cy + Math.sin(angle) * dist + bob - 14,
          fontSize: 28, opacity: op,
          transform: `rotate(${frame * 4 + i * 60}deg)`,
          userSelect: "none",
        }}>⭐</div>
      );
    })}
  </>
);

// ── Main composition ──────────────────────────────────────────────────────────
export interface PeekABooEggsProps {
  /** Item list — can have 3–8 eggs. Generator sets region-specific sprites. */
  eggs?:      EggItem[];
  musicFile?: string;
  bgColor?:   string;
}

export const PeekABooEggs: React.FC<PeekABooEggsProps> = ({
  eggs      = DEFAULT_EGGS,
  musicFile = "Happy Happy Game Show.mp3",
  bgColor   = "#FFF8F0",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const loopFrame = frame % (eggs.length * CYCLE);
  const eggIdx    = Math.floor(loopFrame / CYCLE);
  const localF    = loopFrame % CYCLE;
  const egg       = eggs[eggIdx];

  const cx = width / 2; const cy = height / 2;
  const EGG_SIZE    = Math.min(260, height * 0.24);
  const ANIMAL_SIZE = Math.min(300, height * 0.28);

  const isFall      = localF < FALL_DUR;
  const isShake     = localF >= FALL_DUR && localF < FALL_DUR + SHAKE_DUR;
  const isBurst     = localF >= FALL_DUR + SHAKE_DUR && localF < FALL_DUR + SHAKE_DUR + BURST_DUR;
  const isCelebrate = localF >= FALL_DUR + SHAKE_DUR + BURST_DUR;

  const fallF      = localF;
  const shakeF     = localF - FALL_DUR;
  const burstF     = localF - FALL_DUR - SHAKE_DUR;
  const celebrateF = localF - FALL_DUR - SHAKE_DUR - BURST_DUR;

  // Fall with spring + squash
  const fallSp = spring({ frame: fallF, fps,
    config: { damping: 12, stiffness: 100, mass: 0.7 }, durationInFrames: FALL_DUR });
  const eggY     = isFall ? interpolate(fallSp, [0, 1], [cy - height * 0.8, cy], { extrapolateRight: "clamp" }) : cy;
  const squash   = isFall ? interpolate(fallSp, [0.7, 1], [1, 1.3], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
  const squashY  = isFall ? interpolate(fallSp, [0.7, 1], [1, 0.78], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
  const eggScaleX = isBurst ? interpolate(burstF, [0, BURST_DUR * 0.5], [1, 0], { extrapolateRight: "clamp" }) : squash;
  const eggScaleY = isBurst ? interpolate(burstF, [0, BURST_DUR * 0.5], [1, 0], { extrapolateRight: "clamp" }) : squashY;

  // Shake with acceleration
  const shakeAmp = isShake ? interpolate(shakeF, [0, SHAKE_DUR], [8, 22], { extrapolateRight: "clamp" }) : 0;
  const shakeX   = isShake ? Math.sin(shakeF * 0.8) * shakeAmp : 0;
  const shakeRot = isShake ? Math.sin(shakeF * 0.7) * (shakeAmp * 0.4) : 0;
  const crackProg = isShake ? shakeF / SHAKE_DUR : (isBurst ? 1 : 0);

  // Animal spring-in
  const animalSp = spring({ frame: isBurst ? burstF - 5 : 0, fps,
    config: { damping: 8, stiffness: 120, mass: 0.5 }, durationInFrames: 20 });
  const showAnimal   = isBurst || isCelebrate;
  const animalScale  = showAnimal
    ? interpolate(isBurst ? animalSp : 1, [0, 1], [0, 1], { extrapolateRight: "clamp" })
    : 0;
  const celebrateBob = isCelebrate ? Math.abs(Math.sin(celebrateF * 0.25)) * 40 : 0;
  const exitX        = isCelebrate
    ? interpolate(celebrateF, [CELEBRATE_DUR - 25, CELEBRATE_DUR], [0, width * 0.7],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 0;
  const exitOp       = isCelebrate
    ? interpolate(celebrateF, [CELEBRATE_DUR - 15, CELEBRATE_DUR], [1, 0],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
    : 1;

  const eggPosX = cx + shakeX;
  const eggPosY = (isBurst || isCelebrate) ? cy : eggY;
  const animalX = cx + exitX;
  const animalY = cy - celebrateBob;
  const confettiColors = [egg.accentColor, egg.shellColor, "#FFF", "#FFD700"];

  const bgLayers: ParallaxLayer[] = [
    { background: `linear-gradient(180deg, ${egg.bgColor} 0%, ${bgColor} 100%)`, speed: 0, opacity: 1 },
    { background: "radial-gradient(ellipse at 50% 30%, rgba(255,255,255,0.5) 0%, transparent 65%)", speed: 0.04, opacity: 0.9 },
  ];

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {musicFile && <Audio src={staticFile(`music/${musicFile}`)} volume={0.22} loop />}
      {egg.audio && isBurst && burstF >= 5 && burstF < 10 && (
        <Audio src={staticFile(`audio/${egg.audio}`)} volume={1} />
      )}
      <BackgroundParallax layers={bgLayers} />

      {/* Confetti backdrop */}
      {Array.from({ length: 18 }, (_, i) => {
        const op = 0.12 + Math.sin(frame / fps + i * 0.9) * 0.06;
        return (
          <div key={i} style={{
            position: "absolute",
            left: (i * 113 + eggIdx * 50) % width,
            top: ((frame * 2.5 + i * 60) % (height + 60)) - 30,
            width: 16, height: 16,
            borderRadius: i % 3 === 0 ? "50%" : "3px",
            backgroundColor: confettiColors[i % confettiColors.length],
            opacity: op,
            transform: `rotate(${frame * 2 + i * 25}deg)`,
            pointerEvents: "none",
          }} />
        );
      })}

      {isBurst && <ShellBurst cx={eggPosX} cy={eggPosY} frame={burstF} color={egg.shellColor} />}

      {/* Animal */}
      {showAnimal && (
        <div style={{
          position: "absolute",
          left: animalX - ANIMAL_SIZE / 2, top: animalY - ANIMAL_SIZE * 0.9,
          width: ANIMAL_SIZE, height: ANIMAL_SIZE,
          transform: `scale(${animalScale})`, transformOrigin: "center bottom", opacity: exitOp,
        }}>
          <Img src={staticFile(egg.animalSprite)}
            style={{ width: ANIMAL_SIZE, height: ANIMAL_SIZE, objectFit: "contain" }} />
        </div>
      )}
      {isCelebrate && (
        <StarBurst cx={animalX} cy={animalY - ANIMAL_SIZE * 0.4} frame={celebrateF} color={egg.accentColor} />
      )}

      {/* Egg */}
      {!isCelebrate && (
        <>
          <Egg cx={eggPosX} cy={eggPosY} size={EGG_SIZE}
            shellColor={egg.shellColor} spotColor={egg.spotColor}
            scaleX={eggScaleX} scaleY={eggScaleY} rotation={shakeRot}
            opacity={isBurst ? interpolate(burstF, [0, BURST_DUR * 0.6], [1, 0], { extrapolateRight: "clamp" }) : 1}
          />
          <EggCracks cx={eggPosX} cy={eggPosY} size={EGG_SIZE} progress={crackProg} />
        </>
      )}

      {/* Ground shadow */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: height * 0.12,
        background: "linear-gradient(to top, rgba(0,0,0,0.07) 0%, transparent 100%)",
        pointerEvents: "none",
      }} />

      {/* Egg counter dots */}
      <div style={{
        position: "absolute", bottom: height * 0.06, left: 0, right: 0,
        display: "flex", justifyContent: "center", gap: 18,
      }}>
        {eggs.map((e, i) => (
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
