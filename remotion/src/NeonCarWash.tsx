/**
 * NeonCarWash — grey car enters, goes through magic neon wash, exits as colorful car.
 * No text. Universal content. Loops via frame % (vehicles.length * 300).
 *
 * Per cycle (300f = 10s at 30fps):
 *   0–60f   ENTER  — grey car rolls in from left
 *   60–120f FOAM   — car stops, foam cloud drops from above
 *   120–180f WASH  — neon curtains sweep, foam swirls
 *   180–240f REVEAL — grey fades, color springs + sparkles
 *   240–300f EXIT   — color car vrooms out right
 *
 * Works as 60s short (3 vehicles) or 5-min loop (18 cycles) → extend to 30 min.
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

// ── Public types ──────────────────────────────────────────────────────────────
export interface VehicleItem {
  /** Drives visual style: "car" | "truck" | "bus" | "firetruck" | "ambulance" | "tractor" */
  label:       string;
  color:       string;
  accentColor: string;
  bgColor:     string;
  foamColor:   string;
}

// ── Default vehicles (city theme) ─────────────────────────────────────────────
const DEFAULT_VEHICLES: VehicleItem[] = [
  { label: "truck",  color: "#E53935", accentColor: "#E53935", bgColor: "#FFEBEE", foamColor: "#FF8A80" },
  { label: "car",    color: "#1565C0", accentColor: "#1565C0", bgColor: "#E3F2FD", foamColor: "#82B1FF" },
  { label: "bus",    color: "#F9A825", accentColor: "#F9A825", bgColor: "#FFFDE7", foamColor: "#FFD740" },
];

// ── CSS Vehicle drawing ───────────────────────────────────────────────────────
const CSSVehicle: React.FC<{
  cx: number; cy: number; w: number; h: number;
  color: string; grayscale?: boolean; label: string;
}> = ({ cx, cy, w, h, color, grayscale = false, label }) => {
  const filter = grayscale ? "grayscale(1) brightness(0.65)" : "none";
  const bodyH  = h * 0.50;
  const bodyY  = cy - h * 0.28;
  const wheelR = h * 0.22;

  const isBus     = label === "bus";
  const isTruck   = label === "truck";
  const isFire    = label === "firetruck";
  const isAmb     = label === "ambulance";
  const isTractor = label === "tractor";

  const cabinW = isBus || isTractor ? w * 0.80 : w * 0.52;
  const cabinH = h * 0.34;
  const cabinX = isBus || isTractor ? cx - cabinW / 2 : cx - cabinW * 0.10;
  const cabinY = bodyY - cabinH + 4;
  const bodyColor = isAmb ? "#ECEFF1" : color;

  return (
    <>
      {/* Body */}
      <div style={{
        position: "absolute", left: cx - w / 2, top: bodyY, width: w, height: bodyH,
        borderRadius: "12px 12px 8px 8px",
        background: `linear-gradient(145deg, ${bodyColor}dd, ${bodyColor})`,
        filter, boxShadow: `0 8px 32px ${bodyColor}55`,
      }} />
      {/* Cabin */}
      <div style={{
        position: "absolute", left: cabinX, top: cabinY, width: cabinW, height: cabinH,
        borderRadius: "16px 16px 4px 4px",
        background: `linear-gradient(135deg, ${bodyColor}cc, ${bodyColor}ee)`,
        filter,
      }} />
      {/* Windows */}
      <div style={{
        position: "absolute", left: cabinX + 12, top: cabinY + 10,
        width: cabinW - 24, height: cabinH - 24,
        borderRadius: 8, background: "rgba(180,220,255,0.75)", filter,
      }} />
      {/* Police stripe */}
      {label === "car" && (
        <div style={{
          position: "absolute", left: cx - w / 2, top: bodyY + bodyH * 0.25,
          width: w, height: 9,
          background: "repeating-linear-gradient(90deg, #FFF 0px, #FFF 18px, #1565C0 18px, #1565C0 36px)",
          filter,
        }} />
      )}
      {/* Ambulance cross */}
      {isAmb && (
        <>
          <div style={{
            position: "absolute", left: cx - 8, top: bodyY + 10, width: 16, height: bodyH - 20,
            backgroundColor: "#E53935", filter, borderRadius: 4,
          }} />
          <div style={{
            position: "absolute", left: cx - 24, top: bodyY + bodyH * 0.3, width: 48, height: 14,
            backgroundColor: "#E53935", filter, borderRadius: 4,
          }} />
        </>
      )}
      {/* Fire ladder */}
      {isFire && (
        <div style={{
          position: "absolute", left: cx - w * 0.3, top: cabinY - 16,
          width: w * 0.6, height: 14,
          background: "repeating-linear-gradient(90deg, #FFF9C4 0, #FFF9C4 16px, #F57F17 16px, #F57F17 20px)",
          filter, borderRadius: 4,
        }} />
      )}
      {/* Tractor large back wheel */}
      {isTractor && (
        <div style={{
          position: "absolute", left: cx - w * 0.32 - wheelR * 1.5,
          top: bodyY + bodyH - wheelR * 0.4,
          width: wheelR * 3, height: wheelR * 3, borderRadius: "50%",
          background: "radial-gradient(circle at 35% 35%, #616161, #212121)",
          border: "5px solid #424242", filter,
        }} />
      )}
      {/* Wheels */}
      {(isTractor ? [w * 0.28] : [-w * 0.29, w * 0.29]).map((dx, i) => (
        <div key={i} style={{
          position: "absolute",
          left: cx + dx - wheelR, top: bodyY + bodyH - wheelR * 0.5,
          width: wheelR * 2, height: wheelR * 2, borderRadius: "50%",
          background: "radial-gradient(circle at 35% 35%, #616161, #212121)",
          border: "4px solid #424242", filter,
        }} />
      ))}
    </>
  );
};

// ── Foam cloud ─────────────────────────────────────────────────────────────────
const FoamCloud: React.FC<{
  cx: number; cy: number; frame: number; color: string; phase: "drop" | "wash" | "clear";
}> = ({ cx, cy, frame, color, phase }) => (
  <>
    {Array.from({ length: 9 }, (_, i) => {
      const angle  = (i / 9) * Math.PI * 2;
      const r      = 80 + (i % 3) * 30;
      const sz     = 70 + (i % 4) * 28;
      const wobble = Math.sin(frame * 0.2 + i) * 12;
      const op     = phase === "clear"
        ? interpolate(frame, [0, FOAM_DUR * 0.8], [0.85, 0], { extrapolateRight: "clamp" })
        : phase === "drop"
        ? interpolate(frame, [0, FOAM_DUR * 0.4], [0, 0.85], { extrapolateRight: "clamp" })
        : 0.85;
      return (
        <div key={i} style={{
          position: "absolute",
          left: cx + Math.cos(angle) * r * 0.7 + wobble - sz / 2,
          top:  cy + Math.sin(angle) * r * 0.55 - sz / 2,
          width: sz, height: sz, borderRadius: "50%",
          background: `radial-gradient(circle, rgba(255,255,255,0.9) 0%, ${color}88 60%, transparent 100%)`,
          opacity: op, filter: "blur(4px)", pointerEvents: "none",
        }} />
      );
    })}
  </>
);

// ── Neon wash curtains ─────────────────────────────────────────────────────────
const NeonCurtain: React.FC<{
  cx: number; height: number; frame: number; color: string;
}> = ({ cx, height: h, frame, color }) => (
  <>
    {Array.from({ length: 6 }, (_, i) => {
      const x    = cx - 100 + i * 40;
      const wave = Math.sin(frame * 0.35 + i * 0.8) * 18;
      const op   = 0.5 + Math.sin(frame * 0.2 + i) * 0.25;
      return (
        <div key={i} style={{
          position: "absolute", left: x + wave, top: 0, width: 32, height: h,
          background: `linear-gradient(180deg, transparent, ${color}66, ${color}aa, ${color}66, transparent)`,
          filter: "blur(6px)", opacity: op, pointerEvents: "none",
        }} />
      );
    })}
  </>
);

// ── Sparkle burst ──────────────────────────────────────────────────────────────
const Sparkle: React.FC<{ cx: number; cy: number; frame: number; color: string }> = ({
  cx, cy, frame, color,
}) => (
  <>
    {Array.from({ length: 12 }, (_, i) => {
      const angle = (i / 12) * Math.PI * 2 + 0.2;
      const dist  = frame * 16;
      const op    = interpolate(frame, [0, REVEAL_DUR], [1, 0], { extrapolateRight: "clamp" });
      const sz    = 12 + (i % 3) * 10;
      return (
        <div key={i} style={{
          position: "absolute",
          left: cx + Math.cos(angle) * dist - sz / 2,
          top:  cy + Math.sin(angle) * dist - frame * 2 - sz / 2,
          width: sz, height: sz, borderRadius: "50%",
          backgroundColor: i % 2 === 0 ? color : "#FFF",
          opacity: op, pointerEvents: "none",
        }} />
      );
    })}
  </>
);

// ── Wash arch gate ─────────────────────────────────────────────────────────────
const WashArch: React.FC<{ cx: number; height: number; color: string; frame: number }> = ({
  cx, height: h, color, frame,
}) => {
  const pulse = 1 + Math.sin(frame * 0.25) * 0.04;
  const glow  = `0 0 30px 10px ${color}88`;
  return (
    <>
      {[cx - 160, cx + 138].map((lx, i) => (
        <div key={i} style={{
          position: "absolute", left: lx, top: h * 0.15, width: 22, height: h * 0.7,
          background: `linear-gradient(180deg, ${color}, ${color}77)`,
          borderRadius: 11, boxShadow: glow,
          transform: `scaleY(${pulse})`, transformOrigin: "bottom",
        }} />
      ))}
      <div style={{
        position: "absolute", left: cx - 160, top: h * 0.15 - 28, width: 320, height: 56,
        borderRadius: "50% 50% 0 0",
        background: `linear-gradient(90deg, ${color}cc, #fff8, ${color}cc)`,
        boxShadow: glow,
        transform: `scaleX(${pulse})`, transformOrigin: "center",
      }} />
    </>
  );
};

// ── Road ──────────────────────────────────────────────────────────────────────
const Road: React.FC<{ width: number; y: number; frame: number }> = ({ width: w, y, frame }) => (
  <>
    <div style={{
      position: "absolute", left: 0, top: y, width: w, height: 70,
      backgroundColor: "#37474f", borderTop: "5px solid #546e7a", borderBottom: "5px solid #263238",
    }} />
    <div style={{
      position: "absolute", left: 0, top: y + 28, width: w, height: 14, overflow: "hidden",
    }}>
      <div style={{
        position: "absolute", top: 0, left: -(frame * 5) % 100, width: w + 100, height: "100%",
        background: "repeating-linear-gradient(90deg, transparent 0, transparent 40px, #FFEB3B44 40px, #FFEB3B44 44px, transparent 44px, transparent 80px)",
      }} />
    </div>
  </>
);

// ── Main composition ──────────────────────────────────────────────────────────
export interface NeonCarWashProps {
  vehicles?:  VehicleItem[];
  musicFile?: string;
  bgColor?:   string;
}

export const NeonCarWash: React.FC<NeonCarWashProps> = ({
  vehicles  = DEFAULT_VEHICLES,
  musicFile = "Pinball Spring.mp3",
  bgColor   = "#E8F5E9",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const loopFrame = frame % (vehicles.length * CYCLE);
  const carIdx    = Math.floor(loopFrame / CYCLE);
  const localF    = loopFrame % CYCLE;
  const car       = vehicles[carIdx];

  const WASH_CX = width / 2;
  const ROAD_Y  = height * 0.62;
  const CAR_W   = 380; const CAR_H = 200;
  const CAR_Y   = ROAD_Y - CAR_H * 0.15;

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

  let carX = WASH_CX;
  if (isEnter) {
    carX = interpolate(enterF, [0, ENTER_DUR], [-CAR_W, WASH_CX], { extrapolateRight: "clamp" });
  } else if (isExit) {
    const sp = spring({ frame: exitF, fps, config: { damping: 14, stiffness: 180, mass: 0.6 }, durationInFrames: EXIT_DUR });
    carX = interpolate(sp, [0, 1], [WASH_CX, width + CAR_W], { extrapolateRight: "clamp" });
  }

  const colorProgress = isReveal
    ? interpolate(revealF, [0, REVEAL_DUR * 0.7], [0, 1], { extrapolateRight: "clamp" })
    : (isExit ? 1 : 0);

  const revealSp    = spring({ frame: revealF, fps, config: { damping: 6, stiffness: 160, mass: 0.4 }, durationInFrames: 20 });
  const revealBounce = isReveal ? interpolate(revealSp, [0, 1], [0, -30], { extrapolateRight: "clamp" }) : 0;
  const revealScale  = isReveal ? 1 + Math.abs(revealSp - 1) * 0.12 : 1;
  const exitBounce   = isExit ? Math.abs(Math.sin(exitF * 0.35)) * 28 : 0;
  const carFinalY    = CAR_Y + revealBounce - exitBounce;

  const showFoam   = isFoam || isWash || (isReveal && revealF < REVEAL_DUR * 0.5);
  const foamPhase: "drop" | "wash" | "clear" = isFoam ? "drop" : isWash ? "wash" : "clear";

  const bgLayers: ParallaxLayer[] = [
    { background: `linear-gradient(180deg, ${car.bgColor} 0%, ${bgColor} 100%)`, speed: 0, opacity: 1 },
    { background: "linear-gradient(180deg, transparent 65%, rgba(0,0,0,0.04) 100%)", speed: 0.08, opacity: 1 },
  ];

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {musicFile && <Audio src={staticFile(`music/${musicFile}`)} volume={0.22} loop />}
      <BackgroundParallax layers={bgLayers} />

      {/* Ceiling strip */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: height * 0.15,
        background: "linear-gradient(180deg, #b0bec5 0%, #cfd8dc 100%)",
        borderBottom: "4px solid #90a4ae",
      }} />
      <WashArch cx={WASH_CX} height={height} color={car.accentColor} frame={frame} />
      <Road width={width} y={ROAD_Y} frame={frame} />
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        height: height - ROAD_Y - 70,
        background: "linear-gradient(180deg, #eceff1 0%, #cfd8dc 100%)",
        borderTop: "4px solid #b0bec5",
      }} />

      {isWash && <NeonCurtain cx={WASH_CX} height={height} frame={washF} color={car.accentColor} />}
      {showFoam && (
        <FoamCloud
          cx={WASH_CX} cy={CAR_Y - CAR_H * 0.3}
          frame={isFoam ? foamF : isWash ? washF : revealF}
          color={car.foamColor} phase={foamPhase}
        />
      )}

      {/* B&W car */}
      <div style={{
        position: "absolute", left: carX - CAR_W / 2, top: carFinalY, width: CAR_W, height: CAR_H,
        transform: `scale(${revealScale})`, transformOrigin: "center bottom",
      }}>
        <CSSVehicle cx={CAR_W/2} cy={CAR_H*0.7} w={CAR_W*0.85} h={CAR_H*0.85}
          color="#888" grayscale label={car.label} />
      </div>

      {/* Color car (fades in) */}
      {colorProgress > 0 && (
        <div style={{
          position: "absolute", left: carX - CAR_W / 2, top: carFinalY, width: CAR_W, height: CAR_H,
          opacity: colorProgress,
          transform: `scale(${revealScale + colorProgress * 0.04})`, transformOrigin: "center bottom",
        }}>
          <CSSVehicle cx={CAR_W/2} cy={CAR_H*0.7} w={CAR_W*0.85} h={CAR_H*0.85}
            color={car.color} label={car.label} />
        </div>
      )}

      {isReveal && revealF < REVEAL_DUR && (
        <Sparkle cx={carX} cy={carFinalY - CAR_H * 0.5} frame={revealF} color={car.accentColor} />
      )}

      {/* Progress dots */}
      <div style={{
        position: "absolute", top: height * 0.07, right: 60, display: "flex", gap: 14,
      }}>
        {vehicles.map((v, i) => (
          <div key={i} style={{
            width: 20, height: 20, borderRadius: 6,
            backgroundColor: i === carIdx ? v.accentColor : "#cfd8dc",
            boxShadow: i === carIdx ? `0 0 10px 4px ${v.accentColor}` : "none",
          }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
