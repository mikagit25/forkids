/**
 * DinoBuild — build a dinosaur piece by piece.
 * Silhouette → 4 parts fly on arc trajectories → magnetic snap → celebration.
 * No text. Universal content. Loops via frame % (dinos.length * 420).
 *
 * Per dino (420f = 14s at 30fps):
 *   0–60f    INTRO     — silhouette fades in
 *   60–300f  BUILD     — 4 parts fly in and snap (60f each)
 *   300–420f CELEBRATE — all parts bounce, confetti, flash
 *
 * Works as 60s short (1 dino) or 5-min loop (21 cycles) → extend to 30 min.
 * Pass custom dinos[] to create different color/theme episodes.
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { BackgroundParallax, ParallaxLayer } from "./components/BackgroundParallax";

// ── Easing ────────────────────────────────────────────────────────────────────
function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

// ── Timing ────────────────────────────────────────────────────────────────────
const INTRO_DUR     = 60;
const PART_DUR      = 60;
const PART_FLY      = 45;
const SNAP_DUR      = 15;
const CELEBRATE_DUR = 120;
const PARTS_COUNT   = 4;
const BUILD_DUR     = INTRO_DUR + PARTS_COUNT * PART_DUR; // 300f
const CYCLE         = BUILD_DUR + CELEBRATE_DUR;           // 420f

// ── Public types ──────────────────────────────────────────────────────────────
export interface DinoCfg {
  /** Sprite path, e.g. "sprites/animals/dino.png" */
  sprite:      string;
  /** CSS hue-rotate degrees (0 = original green, 200 = blue, 300 = pink…) */
  hueRotate:   number;
  bgTop:       string;
  bgBottom:    string;
  accentColor: string;
  snapColor:   string;
}

// ── Default dino themes ───────────────────────────────────────────────────────
const DEFAULT_DINOS: DinoCfg[] = [
  { sprite: "sprites/animals/dino.png", hueRotate:   0,
    bgTop: "#1B5E20", bgBottom: "#4CAF50", accentColor: "#76FF03", snapColor: "#B2FF59" },
  { sprite: "sprites/animals/dino.png", hueRotate: 200,
    bgTop: "#0D47A1", bgBottom: "#42A5F5", accentColor: "#40C4FF", snapColor: "#80D8FF" },
  { sprite: "sprites/animals/dino.png", hueRotate: 300,
    bgTop: "#880E4F", bgBottom: "#E91E63", accentColor: "#FF80AB", snapColor: "#FFB3C5" },
];

// ── Part positions relative to center ────────────────────────────────────────
const PARTS = [
  { label: "body", targetX:   0, targetY:  20, fromX: -1100, fromY:   0, arcHeight: -180, size: 340, rotation:   0 },
  { label: "head", targetX:  60, targetY:-160, fromX:  1100, fromY:-500, arcHeight: -200, size: 220, rotation:  15 },
  { label: "legs", targetX: -20, targetY: 180, fromX:  -800, fromY: 600, arcHeight:  200, size: 200, rotation:   0 },
  { label: "tail", targetX:-160, targetY:  80, fromX:   900, fromY: 400, arcHeight:  160, size: 180, rotation: -20 },
];

// ── Snap flash ────────────────────────────────────────────────────────────────
const SnapFlash: React.FC<{ cx: number; cy: number; frame: number; color: string }> = ({
  cx, cy, frame, color,
}) => {
  const op = interpolate(frame, [0, SNAP_DUR], [0.85, 0], { extrapolateRight: "clamp" });
  if (op <= 0) return null;
  return (
    <div style={{
      position: "absolute", left: cx - 60, top: cy - 60, width: 120, height: 120,
      borderRadius: "50%", backgroundColor: color, opacity: op,
      transform: `scale(${1 + frame * 0.18})`, pointerEvents: "none",
    }} />
  );
};

// ── Screen shake helper ───────────────────────────────────────────────────────
function getShake(lf: number): { x: number; y: number } {
  for (let pi = 0; pi < PARTS_COUNT; pi++) {
    const sf = INTRO_DUR + pi * PART_DUR + PART_FLY;
    const rel = lf - sf;
    if (rel >= 0 && rel < 8) {
      const amp = interpolate(rel, [0, 8], [10, 0], { extrapolateRight: "clamp" });
      return { x: Math.sin(rel * 3.5) * amp, y: Math.cos(rel * 2.8) * amp * 0.6 };
    }
  }
  return { x: 0, y: 0 };
}

// ── Confetti ──────────────────────────────────────────────────────────────────
const Confetti: React.FC<{ width: number; height: number; frame: number; colors: string[] }> = ({
  width: w, height: h, frame, colors,
}) => (
  <>
    {Array.from({ length: 36 }, (_, i) => {
      const op = interpolate(frame, [80, CELEBRATE_DUR], [1, 0], { extrapolateRight: "clamp" });
      return (
        <div key={i} style={{
          position: "absolute",
          left: (i * 59 + 17) % w, top: ((frame * 7 + i * 50) % (h + 80)) - 40,
          width: 14, height: 14,
          borderRadius: i % 3 === 0 ? "50%" : i % 3 === 1 ? "2px" : "0",
          backgroundColor: colors[i % colors.length],
          opacity: op, transform: `rotate(${frame * 7 + i * 37}deg)`, pointerEvents: "none",
        }} />
      );
    })}
  </>
);

// ── Main composition ──────────────────────────────────────────────────────────
export interface DinoBuildProps {
  /** 2–6 dino color themes to cycle through. Generator sets per-episode. */
  dinos?:     DinoCfg[];
  musicFile?: string;
}

export const DinoBuild: React.FC<DinoBuildProps> = ({
  dinos     = DEFAULT_DINOS,
  musicFile = "Wholesome.mp3",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const loopFrame  = frame % (dinos.length * CYCLE);
  const dinoIdx    = Math.floor(loopFrame / CYCLE);
  const localF     = loopFrame % CYCLE;
  const dino       = dinos[dinoIdx];

  const cx = width / 2; const cy = height / 2;
  const isIntro     = localF < INTRO_DUR;
  const isCelebrate = localF >= BUILD_DUR;
  const celebrateF  = localF - BUILD_DUR;

  const silhouetteOp = interpolate(localF, [0, INTRO_DUR], [0, 0.14], { extrapolateRight: "clamp" });
  const victorySp    = spring({ frame: celebrateF, fps,
    config: { damping: 7, stiffness: 110, mass: 0.5 }, durationInFrames: 25 });
  const victoryY     = isCelebrate ? interpolate(victorySp, [0, 1], [0, -100], { extrapolateRight: "clamp" }) : 0;
  const victoryScale = isCelebrate ? 1 + Math.abs(Math.sin(celebrateF * 0.22)) * 0.1 : 1;
  const shake        = getShake(localF);

  const bgLayers: ParallaxLayer[] = [
    { background: `linear-gradient(180deg, ${dino.bgTop} 0%, ${dino.bgBottom} 100%)`, speed: 0, opacity: 1 },
    { background: "radial-gradient(ellipse at 50% 20%, rgba(255,255,255,0.18) 0%, transparent 65%)", speed: 0.06, opacity: 1 },
    { background: "linear-gradient(180deg, transparent 60%, rgba(0,0,0,0.22) 100%)", speed: 0, opacity: 1 },
  ];

  const hueFilter     = dino.hueRotate !== 0 ? `hue-rotate(${dino.hueRotate}deg)` : undefined;
  const confettiColors = [dino.accentColor, dino.snapColor, "#FFF", "#FFD700", "#FF6B6B"];

  return (
    <AbsoluteFill style={{
      overflow: "hidden",
      transform: `translate(${shake.x}px, ${shake.y}px)`,
    }}>
      {musicFile && <Audio src={staticFile(`music/${musicFile}`)} volume={0.22} loop />}
      <BackgroundParallax layers={bgLayers} />

      {isCelebrate && (
        <Confetti width={width} height={height} frame={celebrateF} colors={confettiColors} />
      )}

      {/* Silhouette */}
      <div style={{
        position: "absolute", left: cx - 200, top: cy - 200, width: 400, height: 400,
        opacity: silhouetteOp,
        transform: `translateY(${victoryY}px) scale(${victoryScale})`,
        transformOrigin: "center center",
        filter: "grayscale(1) brightness(2)", pointerEvents: "none",
      }}>
        <Img src={staticFile(dino.sprite)}
          style={{ width: 400, height: 400, objectFit: "contain" }} />
      </div>

      {/* Parts */}
      {PARTS.map((part, pi) => {
        const pieceStartF = INTRO_DUR + pi * PART_DUR;
        const partLocalF  = localF - pieceStartF;
        if (partLocalF < 0) return null;

        const isFlying   = partLocalF >= 0 && partLocalF < PART_FLY;
        const isSnapping = partLocalF >= PART_FLY && partLocalF < PART_FLY + SNAP_DUR;
        const hasLanded  = partLocalF >= PART_FLY;

        let px = cx + part.targetX, py = cy + part.targetY, sc = 1, rot = part.rotation;

        if (isFlying) {
          const t    = partLocalF / PART_FLY;
          const ease = easeOutCubic(t);
          px = (cx + part.fromX) + ease * ((cx + part.targetX) - (cx + part.fromX));
          py = (cy + part.fromY) + ease * ((cy + part.targetY) - (cy + part.fromY))
             + (-part.arcHeight * 4 * t * (1 - t));
          sc  = 0.6 + ease * 0.4;
          rot = part.rotation * ease;
        } else if (isSnapping) {
          const sp = spring({ frame: partLocalF - PART_FLY, fps,
            config: { damping: 5, stiffness: 220, mass: 0.25 }, durationInFrames: SNAP_DUR });
          sc = 1 + Math.abs(sp - 1) * 0.22;
        }
        if (hasLanded && isCelebrate) { py += victoryY; sc *= victoryScale; }

        return (
          <React.Fragment key={pi}>
            <div style={{
              position: "absolute",
              left: px - part.size / 2, top: py - part.size / 2,
              width: part.size, height: part.size,
              transform: `scale(${sc}) rotate(${rot}deg)`,
              transformOrigin: "center center", willChange: "transform",
            }}>
              <Img src={staticFile(dino.sprite)} style={{
                width: part.size, height: part.size, objectFit: "contain",
                filter: hueFilter, opacity: 0.72 + pi * 0.07,
              }} />
            </div>
            {isSnapping && (
              <SnapFlash cx={px} cy={py} frame={partLocalF - PART_FLY} color={dino.snapColor} />
            )}
          </React.Fragment>
        );
      })}

      {/* Victory flash */}
      {isCelebrate && celebrateF < 8 && (
        <div style={{
          position: "absolute", inset: 0, backgroundColor: "#FFF",
          opacity: interpolate(celebrateF, [0, 8], [0.7, 0], { extrapolateRight: "clamp" }),
          pointerEvents: "none",
        }} />
      )}

      {/* Theme dots */}
      <div style={{
        position: "absolute", bottom: height * 0.06, left: 0, right: 0,
        display: "flex", justifyContent: "center", gap: 20,
      }}>
        {dinos.map((d, i) => (
          <div key={i} style={{
            width: 20, height: 20, borderRadius: "50%",
            backgroundColor: i === dinoIdx ? d.accentColor : "rgba(255,255,255,0.25)",
            boxShadow: i === dinoIdx ? `0 0 10px 4px ${d.accentColor}` : "none",
          }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
