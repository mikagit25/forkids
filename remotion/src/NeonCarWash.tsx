/**
 * NeonCarWash — grey car enters, goes through magic neon wash, exits as colorful 3D car.
 * No text. Universal content.
 *
 * Per cycle (300f = 10s at 30fps):
 *   0–60f   ENTER  — grey car rolls in from left
 *   60–120f FOAM   — car stops, foam cloud drops from above
 *   120–180f WASH  — neon curtains sweep, foam swirls
 *   180–240f REVEAL — grey fades, color car springs + sparkles
 *   240–300f EXIT   — color car vrooms out right with bounce
 *
 * 3 cars × 300f = 900f loop. Composition: 1620f (~3 loops).
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { BackgroundParallax, ParallaxLayer } from "./components/BackgroundParallax";

// ── Timing ────────────────────────────────────────────────────────────────────
const ENTER_DUR  = 60;
const FOAM_DUR   = 60;
const WASH_DUR   = 60;
const REVEAL_DUR = 60;
const EXIT_DUR   = 60;
const CYCLE      = ENTER_DUR + FOAM_DUR + WASH_DUR + REVEAL_DUR + EXIT_DUR; // 300f

// ── Car catalogue ─────────────────────────────────────────────────────────────
interface CarCfg {
  label: string;
  spriteBw: string;
  spriteColor: string;
  accentColor: string;
  bgColor: string;
  foamColor: string;
}

const CARS: CarCfg[] = [
  {
    label: "monster_truck",
    spriteBw:    "sprites/objects/car_3d.png",
    spriteColor: "sprites/objects/car_3d.png",
    accentColor: "#E53935",
    bgColor:     "#FFEBEE",
    foamColor:   "#FF8A80",
  },
  {
    label: "police",
    spriteBw:    "sprites/objects/car_3d.png",
    spriteColor: "sprites/objects/car_3d.png",
    accentColor: "#1565C0",
    bgColor:     "#E3F2FD",
    foamColor:   "#82B1FF",
  },
  {
    label: "school_bus",
    spriteBw:    "sprites/objects/car_3d.png",
    spriteColor: "sprites/objects/car_3d.png",
    accentColor: "#F9A825",
    bgColor:     "#FFFDE7",
    foamColor:   "#FFD740",
  },
];

// ── CSS Car (when no per-type sprite available) ───────────────────────────────
const CSSCar: React.FC<{
  cx: number; cy: number; w: number; h: number;
  color: string; grayscale?: boolean; label: string;
}> = ({ cx, cy, w, h, color, grayscale = false, label }) => {
  const filter = grayscale ? "grayscale(1) brightness(0.65)" : "none";
  const bodyH  = h * 0.52;
  const cabinH = h * 0.36;
  const wheelR = h * 0.22;
  const bodyY  = cy - h * 0.3;
  const cabinY = bodyY - cabinH + 4;

  // school bus is wider cabin
  const cabinW = label === "school_bus" ? w * 0.82 : w * 0.54;
  const cabinX = label === "school_bus" ? cx - cabinW / 2 : cx - cabinW * 0.12;

  return (
    <>
      {/* Body */}
      <div style={{
        position: "absolute",
        left: cx - w / 2, top: bodyY,
        width: w, height: bodyH,
        borderRadius: "12px 12px 8px 8px",
        background: `linear-gradient(145deg, ${color}dd, ${color})`,
        filter,
        boxShadow: `0 8px 32px ${color}55`,
      }} />
      {/* Cabin */}
      <div style={{
        position: "absolute",
        left: cabinX, top: cabinY,
        width: cabinW, height: cabinH,
        borderRadius: "16px 16px 4px 4px",
        background: `linear-gradient(135deg, ${color}cc, ${color}ee)`,
        filter,
      }} />
      {/* Windows */}
      <div style={{
        position: "absolute",
        left: cabinX + 12, top: cabinY + 10,
        width: cabinW - 24, height: cabinH - 24,
        borderRadius: 8,
        background: "rgba(180,220,255,0.75)",
        filter,
      }} />
      {/* Wheels */}
      {[-w * 0.29, w * 0.29].map((dx, i) => (
        <div key={i} style={{
          position: "absolute",
          left: cx + dx - wheelR,
          top: bodyY + bodyH - wheelR * 0.5,
          width: wheelR * 2, height: wheelR * 2,
          borderRadius: "50%",
          background: "radial-gradient(circle at 35% 35%, #616161, #212121)",
          border: "4px solid #424242",
          filter,
        }} />
      ))}
      {/* Accent stripe for police */}
      {label === "police" && (
        <div style={{
          position: "absolute",
          left: cx - w / 2, top: bodyY + bodyH * 0.25,
          width: w, height: 10,
          background: "repeating-linear-gradient(90deg, #FFF 0px, #FFF 20px, #1565C0 20px, #1565C0 40px)",
          filter,
        }} />
      )}
    </>
  );
};

// ── Foam cloud ─────────────────────────────────────────────────────────────────
const FoamCloud: React.FC<{
  cx: number; cy: number; frame: number; color: string; phase: "drop" | "wash" | "clear";
}> = ({ cx, cy, frame, color, phase }) => {
  const BLOBS = 9;
  return (
    <>
      {Array.from({ length: BLOBS }, (_, i) => {
        const angle = (i / BLOBS) * Math.PI * 2;
        const r = 80 + (i % 3) * 30;
        const bx = cx + Math.cos(angle) * r * 0.7;
        const by = cy + Math.sin(angle) * r * 0.55;
        const sz = 70 + (i % 4) * 28;
        const wobble = Math.sin(frame * 0.2 + i) * 12;
        const op = phase === "clear"
          ? interpolate(frame, [0, FOAM_DUR * 0.8], [0.85, 0], { extrapolateRight: "clamp" })
          : phase === "drop"
          ? interpolate(frame, [0, FOAM_DUR * 0.4], [0, 0.85], { extrapolateRight: "clamp" })
          : 0.85;
        return (
          <div key={i} style={{
            position: "absolute",
            left: bx + wobble - sz / 2,
            top: by - sz / 2,
            width: sz, height: sz,
            borderRadius: "50%",
            background: `radial-gradient(circle, rgba(255,255,255,0.9) 0%, ${color}88 60%, transparent 100%)`,
            opacity: op,
            filter: "blur(4px)",
            pointerEvents: "none",
          }} />
        );
      })}
    </>
  );
};

// ── Neon wash curtains ─────────────────────────────────────────────────────────
const NeonCurtain: React.FC<{
  cx: number; height: number; frame: number; color: string;
}> = ({ cx, height: h, frame, color }) => {
  const STRIPS = 6;
  return (
    <>
      {Array.from({ length: STRIPS }, (_, i) => {
        const x = cx - 100 + i * 40;
        const wave = Math.sin(frame * 0.35 + i * 0.8) * 18;
        const op = 0.5 + Math.sin(frame * 0.2 + i) * 0.25;
        return (
          <div key={i} style={{
            position: "absolute",
            left: x + wave, top: 0,
            width: 32, height: h,
            background: `linear-gradient(180deg, transparent, ${color}66, ${color}aa, ${color}66, transparent)`,
            filter: "blur(6px)",
            opacity: op,
            pointerEvents: "none",
          }} />
        );
      })}
    </>
  );
};

// ── Sparkle burst ──────────────────────────────────────────────────────────────
const Sparkle: React.FC<{ cx: number; cy: number; frame: number; color: string }> = ({
  cx, cy, frame, color,
}) => {
  const PARTICLES = 12;
  return (
    <>
      {Array.from({ length: PARTICLES }, (_, i) => {
        const angle = (i / PARTICLES) * Math.PI * 2 + 0.2;
        const dist  = frame * 16;
        const px    = cx + Math.cos(angle) * dist;
        const py    = cy + Math.sin(angle) * dist - frame * 2; // slight upward drift
        const op    = interpolate(frame, [0, REVEAL_DUR], [1, 0], { extrapolateRight: "clamp" });
        const sz    = 12 + (i % 3) * 10;
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

// ── Arch gate for wash zone ────────────────────────────────────────────────────
const WashArch: React.FC<{ cx: number; height: number; color: string; frame: number }> = ({
  cx, height: h, color, frame,
}) => {
  const pulse = 1 + Math.sin(frame * 0.25) * 0.04;
  const glow  = `0 0 30px 10px ${color}88`;
  return (
    <>
      <div style={{
        position: "absolute", left: cx - 160, top: h * 0.15,
        width: 22, height: h * 0.7,
        background: `linear-gradient(180deg, ${color}, ${color}77)`,
        borderRadius: 11, boxShadow: glow,
        transform: `scaleY(${pulse})`, transformOrigin: "bottom",
      }} />
      <div style={{
        position: "absolute", left: cx + 138, top: h * 0.15,
        width: 22, height: h * 0.7,
        background: `linear-gradient(180deg, ${color}, ${color}77)`,
        borderRadius: 11, boxShadow: glow,
        transform: `scaleY(${pulse})`, transformOrigin: "bottom",
      }} />
      <div style={{
        position: "absolute",
        left: cx - 160, top: h * 0.15 - 28,
        width: 320, height: 56,
        borderRadius: "50% 50% 0 0",
        background: `linear-gradient(90deg, ${color}cc, #fff8, ${color}cc)`,
        boxShadow: glow,
        transform: `scaleX(${pulse})`, transformOrigin: "center",
      }} />
    </>
  );
};

// ── Road ──────────────────────────────────────────────────────────────────────
const Road: React.FC<{ width: number; y: number; frame: number }> = ({ width: w, y, frame }) => {
  const scrollX = -(frame * 5) % 100;
  return (
    <>
      <div style={{
        position: "absolute", left: 0, top: y, width: w, height: 70,
        backgroundColor: "#37474f",
        borderTop: "5px solid #546e7a",
        borderBottom: "5px solid #263238",
      }} />
      <div style={{
        position: "absolute", left: 0, top: y + 28, width: w, height: 14,
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute",
          top: 0, left: scrollX,
          width: w + 100, height: "100%",
          background: "repeating-linear-gradient(90deg, transparent 0, transparent 40px, #FFEB3B44 40px, #FFEB3B44 44px, transparent 44px, transparent 80px)",
        }} />
      </div>
    </>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────
export interface NeonCarWashProps {
  musicFile?: string;
  bgColor?: string;
}

export const NeonCarWash: React.FC<NeonCarWashProps> = ({
  musicFile = "Pinball Spring.mp3",
  bgColor = "#E8F5E9",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const totalCycle = CARS.length * CYCLE;
  const loopFrame  = frame % totalCycle;
  const carIdx     = Math.floor(loopFrame / CYCLE);
  const localF     = loopFrame % CYCLE;
  const car        = CARS[carIdx];

  const WASH_CX = width / 2;
  const ROAD_Y  = height * 0.62;
  const CAR_W   = 380;
  const CAR_H   = 200;
  const CAR_Y   = ROAD_Y - CAR_H * 0.15;

  // ── Phase detection ────────────────────────────────────────────────────────
  const isEnter  = localF < ENTER_DUR;
  const isFoam   = localF >= ENTER_DUR && localF < ENTER_DUR + FOAM_DUR;
  const isWash   = localF >= ENTER_DUR + FOAM_DUR && localF < ENTER_DUR + FOAM_DUR + WASH_DUR;
  const isReveal = localF >= ENTER_DUR + FOAM_DUR + WASH_DUR && localF < ENTER_DUR + FOAM_DUR + WASH_DUR + REVEAL_DUR;
  const isExit   = localF >= ENTER_DUR + FOAM_DUR + WASH_DUR + REVEAL_DUR;

  const enterF  = localF;
  const foamF   = localF - ENTER_DUR;
  const washF   = localF - ENTER_DUR - FOAM_DUR;
  const revealF = localF - ENTER_DUR - FOAM_DUR - WASH_DUR;
  const exitF   = localF - ENTER_DUR - FOAM_DUR - WASH_DUR - REVEAL_DUR;

  // ── Car X position ─────────────────────────────────────────────────────────
  let carX = WASH_CX;
  if (isEnter) {
    carX = interpolate(enterF, [0, ENTER_DUR], [-CAR_W, WASH_CX], { extrapolateRight: "clamp" });
  } else if (isExit) {
    const exitSp = spring({ frame: exitF, fps, config: { damping: 14, stiffness: 180, mass: 0.6 }, durationInFrames: EXIT_DUR });
    carX = interpolate(exitSp, [0, 1], [WASH_CX, width + CAR_W], { extrapolateRight: "clamp" });
  }

  // ── Color progress (B&W → color) ──────────────────────────────────────────
  const colorProgress = isReveal
    ? interpolate(revealF, [0, REVEAL_DUR * 0.7], [0, 1], { extrapolateRight: "clamp" })
    : (isExit ? 1 : 0);

  // ── Reveal bounce ─────────────────────────────────────────────────────────
  const revealSp = spring({ frame: revealF, fps, config: { damping: 6, stiffness: 160, mass: 0.4 }, durationInFrames: 20 });
  const revealBounce = isReveal ? interpolate(revealSp, [0, 1], [0, -30], { extrapolateRight: "clamp" }) : 0;
  const revealScale  = isReveal ? 1 + Math.abs(revealSp - 1) * 0.12 : 1;

  // ── Exit bounce ───────────────────────────────────────────────────────────
  const exitBounce = isExit ? Math.abs(Math.sin(exitF * 0.35)) * 28 : 0;

  const carFinalY = CAR_Y + revealBounce - exitBounce;

  // ── Background ────────────────────────────────────────────────────────────
  const bgLayers: ParallaxLayer[] = [
    { background: `linear-gradient(180deg, ${car.bgColor} 0%, ${bgColor} 100%)`, speed: 0, opacity: 1 },
    { background: "linear-gradient(180deg, transparent 65%, rgba(0,0,0,0.04) 100%)", speed: 0.08, opacity: 1 },
  ];

  // Foam phase: drop or swirling or clearing
  const foamPhase: "drop" | "wash" | "clear" = isFoam ? "drop" : isWash ? "wash" : "clear";
  const showFoam = isFoam || isWash || (isReveal && revealF < REVEAL_DUR * 0.5);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {musicFile && <Audio src={staticFile(`music/${musicFile}`)} volume={0.22} loop />}

      <BackgroundParallax layers={bgLayers} />

      {/* Sky / building backdrop */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: height * 0.15,
        background: "linear-gradient(180deg, #b0bec5 0%, #cfd8dc 100%)",
        borderBottom: "4px solid #90a4ae",
      }} />

      {/* Wash arch */}
      <WashArch cx={WASH_CX} height={height} color={car.accentColor} frame={frame} />

      {/* Road */}
      <Road width={width} y={ROAD_Y} frame={frame} />

      {/* Floor */}
      <div style={{
        position: "absolute",
        bottom: 0, left: 0, right: 0,
        height: height - ROAD_Y - 70,
        background: "linear-gradient(180deg, #eceff1 0%, #cfd8dc 100%)",
        borderTop: "4px solid #b0bec5",
      }} />

      {/* Wash curtains (active during wash phase) */}
      {isWash && (
        <NeonCurtain cx={WASH_CX} height={height} frame={washF} color={car.accentColor} />
      )}

      {/* Foam cloud */}
      {showFoam && (
        <FoamCloud
          cx={WASH_CX} cy={CAR_Y - CAR_H * 0.3}
          frame={isFoam ? foamF : isWash ? washF : revealF}
          color={car.foamColor}
          phase={foamPhase}
        />
      )}

      {/* Car — B&W layer */}
      <div style={{
        position: "absolute",
        left: carX - CAR_W / 2,
        top:  carFinalY,
        width: CAR_W, height: CAR_H,
        transform: `scale(${revealScale})`,
        transformOrigin: "center bottom",
      }}>
        <CSSCar
          cx={CAR_W / 2} cy={CAR_H * 0.7}
          w={CAR_W * 0.85} h={CAR_H * 0.85}
          color="#888"
          grayscale={true}
          label={car.label}
        />
      </div>

      {/* Car — Color overlay (fades in during reveal) */}
      {colorProgress > 0 && (
        <div style={{
          position: "absolute",
          left: carX - CAR_W / 2,
          top:  carFinalY,
          width: CAR_W, height: CAR_H,
          opacity: colorProgress,
          transform: `scale(${revealScale + colorProgress * 0.04})`,
          transformOrigin: "center bottom",
        }}>
          <CSSCar
            cx={CAR_W / 2} cy={CAR_H * 0.7}
            w={CAR_W * 0.85} h={CAR_H * 0.85}
            color={car.accentColor}
            grayscale={false}
            label={car.label}
          />
        </div>
      )}

      {/* Sparkle burst at color reveal */}
      {isReveal && revealF < REVEAL_DUR && (
        <Sparkle cx={carX} cy={carFinalY - CAR_H * 0.5} frame={revealF} color={car.accentColor} />
      )}

      {/* Car dots progress indicator */}
      <div style={{
        position: "absolute", top: height * 0.07, right: 60,
        display: "flex", gap: 14,
      }}>
        {CARS.map((c, i) => (
          <div key={i} style={{
            width: 20, height: 20, borderRadius: 6,
            backgroundColor: i === carIdx ? c.accentColor : "#cfd8dc",
            boxShadow: i === carIdx ? `0 0 10px 4px ${c.accentColor}` : "none",
          }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
