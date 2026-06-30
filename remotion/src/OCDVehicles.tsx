/**
 * OCDVehicles — satisfying vehicles parade for toddlers.
 * Trucks, cars, buses walk across the screen in a looping pattern.
 * Uses WalkingSprite + BackgroundParallax road/sky.
 * No text, universal content (EN/AR/ID).
 * 5-minute loop, extended via FFmpeg to 20-30 min.
 *
 * Themes: city | countryside | night | rainbow
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { BackgroundParallax, ParallaxLayer } from "./components/BackgroundParallax";

export interface OCDVehiclesProps {
  theme: "city" | "countryside" | "night" | "rainbow";
  musicFile?: string;
  vehiclesPerLane?: number;
  speedMultiplier?: number;
}

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ── CSS-drawn vehicle components ─────────────────────────────────────────────

const CSSCar: React.FC<{ color: string; size: number }> = ({ color, size }) => (
  <div style={{ width: size, height: size * 0.55, position: "relative" }}>
    {/* Body */}
    <div style={{
      position: "absolute", bottom: 0, left: 0, right: 0,
      height: "65%", backgroundColor: color,
      borderRadius: "12px 12px 6px 6px",
      boxShadow: `0 4px 12px ${color}88`,
    }} />
    {/* Cabin */}
    <div style={{
      position: "absolute", bottom: "55%", left: "20%", right: "15%",
      height: "50%", backgroundColor: `${color}cc`,
      borderRadius: "10px 10px 0 0",
    }} />
    {/* Windows */}
    <div style={{
      position: "absolute", bottom: "62%", left: "23%", width: "22%", height: "28%",
      backgroundColor: "#b3e5fc", borderRadius: 4, opacity: 0.9,
    }} />
    <div style={{
      position: "absolute", bottom: "62%", right: "18%", width: "22%", height: "28%",
      backgroundColor: "#b3e5fc", borderRadius: 4, opacity: 0.9,
    }} />
    {/* Wheels */}
    {[18, size - 38].map((wx, i) => (
      <div key={i} style={{
        position: "absolute", bottom: -size * 0.08, left: wx,
        width: size * 0.20, height: size * 0.20,
        borderRadius: "50%", backgroundColor: "#333",
        border: "3px solid #555",
      }} />
    ))}
  </div>
);

const CSSTruck: React.FC<{ color: string; size: number }> = ({ color, size }) => (
  <div style={{ width: size * 1.5, height: size * 0.65, position: "relative" }}>
    {/* Cargo box */}
    <div style={{
      position: "absolute", bottom: 0, right: 0,
      width: "68%", height: "80%",
      backgroundColor: color,
      borderRadius: "6px 6px 4px 4px",
      boxShadow: `0 4px 12px ${color}88`,
    }} />
    {/* Cabin */}
    <div style={{
      position: "absolute", bottom: 0, left: 0, width: "35%", height: "75%",
      backgroundColor: `${color}dd`,
      borderRadius: "10px 4px 4px 10px",
    }} />
    {/* Windshield */}
    <div style={{
      position: "absolute", bottom: "35%", left: "5%", width: "22%", height: "32%",
      backgroundColor: "#b3e5fc", borderRadius: 5, opacity: 0.85,
    }} />
    {/* Wheels */}
    {[size * 0.06, size * 0.42, size * 0.85].map((wx, i) => (
      <div key={i} style={{
        position: "absolute", bottom: -size * 0.06, left: wx,
        width: size * 0.17, height: size * 0.17,
        borderRadius: "50%", backgroundColor: "#222",
        border: "3px solid #444",
      }} />
    ))}
  </div>
);

const CSSBus: React.FC<{ color: string; size: number }> = ({ color, size }) => (
  <div style={{ width: size * 1.8, height: size * 0.65, position: "relative" }}>
    {/* Body */}
    <div style={{
      position: "absolute", bottom: 0, left: 0, right: 0, height: "82%",
      backgroundColor: color,
      borderRadius: "10px 10px 6px 6px",
      boxShadow: `0 4px 12px ${color}88`,
    }} />
    {/* Windows row */}
    {Array.from({ length: 5 }, (_, i) => (
      <div key={i} style={{
        position: "absolute", top: "8%",
        left: `${12 + i * 17.5}%`, width: "14%", height: "36%",
        backgroundColor: "#b3e5fc", borderRadius: 4, opacity: 0.88,
      }} />
    ))}
    {/* Wheels */}
    {[size * 0.10, size * 0.55, size * 1.15].map((wx, i) => (
      <div key={i} style={{
        position: "absolute", bottom: -size * 0.07, left: wx,
        width: size * 0.18, height: size * 0.18,
        borderRadius: "50%", backgroundColor: "#222",
        border: "3px solid #444",
      }} />
    ))}
  </div>
);

// ── Single vehicle lane entry ─────────────────────────────────────────────────
type VehicleType = "car" | "truck" | "bus" | "sprite_car";

interface VehicleEntry {
  type: VehicleType;
  color: string;
  size: number;
  lane: number;
  startFrame: number;
  speed: number;        // px/frame
  bounceAmp: number;
  flipX: boolean;
}

const VehicleRender: React.FC<{ v: VehicleEntry; frame: number }> = ({ v, frame }) => {
  const localF = frame - v.startFrame;
  if (localF < 0) return null;

  const startX = v.flipX ? 2200 : -400;
  const endX   = v.flipX ? -400 : 2200;
  const x = startX + (v.flipX ? -1 : 1) * localF * v.speed;
  if (v.flipX ? x < -400 : x > 2200) return null;

  const bounce = Math.abs(Math.sin(localF * 0.15)) * v.bounceAmp;

  // Entry spring (first 20 frames)
  const entryScale = interpolate(
    spring({ frame: localF, fps: 30, config: { damping: 12, stiffness: 120 }, durationInFrames: 25 }),
    [0, 1], [0.6, 1], { extrapolateRight: "clamp" }
  );

  const laneY = 500 + v.lane * 130 - bounce;

  return (
    <div style={{
      position: "absolute",
      left: x,
      top: laneY,
      transform: `scaleX(${v.flipX ? -1 : 1}) scale(${entryScale})`,
      transformOrigin: "center bottom",
      willChange: "transform",
    }}>
      {v.type === "car"    && <CSSCar    color={v.color} size={v.size} />}
      {v.type === "truck"  && <CSSTruck  color={v.color} size={v.size} />}
      {v.type === "bus"    && <CSSBus    color={v.color} size={v.size} />}
      {v.type === "sprite_car" && (
        <Img src={staticFile("sprites/objects/car_3d.png")}
             style={{ width: v.size, height: v.size, objectFit: "contain" }} />
      )}
    </div>
  );
};

// ── Theme background layers ───────────────────────────────────────────────────
const THEMES: Record<string, {
  layers: ParallaxLayer[];
  roadColor: string;
  roadLineColor: string;
  musicDefault: string;
}> = {
  city: {
    layers: [
      { background: "linear-gradient(180deg, #87CEEB 0%, #b0d4f1 100%)", speed: 0.04, opacity: 1 },
      { background: "linear-gradient(180deg, transparent 55%, #cfd8dc 70%, #b0bec5 100%)", speed: 0.18, opacity: 0.85 },
    ],
    roadColor: "#607d8b",
    roadLineColor: "#fff",
    musicDefault: "Pinball Spring.mp3",
  },
  countryside: {
    layers: [
      { background: "linear-gradient(180deg, #a8edea 0%, #b2d8b5 100%)", speed: 0.04, opacity: 1 },
      { background: "linear-gradient(180deg, transparent 50%, #81c784 72%, #66bb6a 100%)", speed: 0.15, opacity: 0.9 },
    ],
    roadColor: "#795548",
    roadLineColor: "#ffecb3",
    musicDefault: "Carefree.mp3",
  },
  night: {
    layers: [
      { background: "linear-gradient(180deg, #1a237e 0%, #283593 100%)", speed: 0.03, opacity: 1 },
      { background: "linear-gradient(180deg, transparent 60%, #263238 80%, #1c313a 100%)", speed: 0.12, opacity: 0.9 },
    ],
    roadColor: "#263238",
    roadLineColor: "#ffd740",
    musicDefault: "Gymnopedie No 1.mp3",
  },
  rainbow: {
    layers: [
      { background: "linear-gradient(180deg, #e8d5f5 0%, #d5e8f5 50%, #d5f5e8 100%)", speed: 0.05, opacity: 1 },
      { background: "linear-gradient(180deg, transparent 55%, #e8f5e9 72%, #c8e6c9 100%)", speed: 0.20, opacity: 0.9 },
    ],
    roadColor: "#9e9e9e",
    roadLineColor: "#fff",
    musicDefault: "Happy Happy Game Show.mp3",
  },
};

const VEHICLE_COLORS = {
  city:        ["#e53935","#1e88e5","#f9a825","#00897b","#6d4c41","#5e35b1","#00acc1"],
  countryside: ["#ff7043","#26a69a","#fbc02d","#66bb6a","#ab47bc","#ec407a","#7986cb"],
  night:       ["#e040fb","#40c4ff","#ffd740","#69f0ae","#ff6d00","#b388ff","#ff5252"],
  rainbow:     ["#ef5350","#fb8c00","#fdd835","#43a047","#1e88e5","#9c27b0","#f06292"],
};

// ── Main composition ──────────────────────────────────────────────────────────
export const OCDVehicles: React.FC<OCDVehiclesProps> = ({
  theme = "city",
  musicFile,
  vehiclesPerLane = 5,
  speedMultiplier = 1.0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const cfg = THEMES[theme];
  const colors = VEHICLE_COLORS[theme];
  const music = musicFile ?? cfg.musicDefault;

  const fadeIn = interpolate(frame, [0, fps], [0, 1], { extrapolateRight: "clamp" });

  // Road: 3 lanes, spaced 130px apart starting at y=500
  const ROAD_TOP = 490;
  const ROAD_HEIGHT = 430;
  const LANE_INTERVAL = 130;

  // Generate vehicle schedule: each lane has vehiclesPerLane vehicles
  // cycling with gap of ~180 frames between each
  const vehicles: VehicleEntry[] = [];
  const TYPES: VehicleType[] = ["car", "truck", "bus", "sprite_car", "car"];
  const GAP_FRAMES = 180;

  for (let lane = 0; lane < 3; lane++) {
    for (let v = 0; v < vehiclesPerLane; v++) {
      const seed = lane * 100 + v;
      const r = seededRand;
      const typeIdx = (lane * 3 + v) % TYPES.length;
      const flip = (lane + v) % 2 === 1;
      const colorIdx = (v + lane * 2) % colors.length;

      vehicles.push({
        type: TYPES[typeIdx],
        color: colors[colorIdx],
        size: 120 + Math.round(r(seed * 7) * 40),
        lane,
        startFrame: v * GAP_FRAMES + lane * 55,
        speed: (2.8 + r(seed * 3) * 1.5) * speedMultiplier,
        bounceAmp: 6 + r(seed * 5) * 8,
        flipX: flip,
      });
    }
  }

  return (
    <AbsoluteFill style={{ overflow: "hidden", opacity: fadeIn }}>
      {music && <Audio src={staticFile(`music/${music}`)} volume={0.18} loop />}

      {/* Background parallax */}
      <BackgroundParallax layers={cfg.layers} scrollRange={60} cycleSec={45} />

      {/* Night stars */}
      {theme === "night" && Array.from({ length: 60 }, (_, i) => {
        const r = seededRand;
        const op = 0.3 + Math.sin(frame / 30 * 0.8 + i) * 0.3;
        return (
          <div key={i} style={{
            position: "absolute",
            left: r(i * 7) * width, top: r(i * 11) * ROAD_TOP * 0.8,
            width: 2 + r(i * 3) * 3, height: 2 + r(i * 3) * 3,
            borderRadius: "50%", backgroundColor: "#fff", opacity: op,
          }} />
        );
      })}

      {/* Road surface */}
      <div style={{
        position: "absolute",
        top: ROAD_TOP,
        left: 0, right: 0,
        height: ROAD_HEIGHT,
        backgroundColor: cfg.roadColor,
      }} />

      {/* Road lane markings */}
      {[0, 1].map(li => (
        <div key={li} style={{
          position: "absolute",
          top: ROAD_TOP + 60 + li * LANE_INTERVAL,
          left: 0, right: 0, height: 4,
          background: `repeating-linear-gradient(90deg, ${cfg.roadLineColor} 0px, ${cfg.roadLineColor} 60px, transparent 60px, transparent 120px)`,
          opacity: 0.6,
        }} />
      ))}

      {/* Vehicles */}
      {vehicles.map((v, i) => (
        <VehicleRender key={i} v={v} frame={frame} />
      ))}

      {/* Bottom shadow / grass strip */}
      <div style={{
        position: "absolute",
        bottom: 0, left: 0, right: 0, height: height - ROAD_TOP - ROAD_HEIGHT,
        background: theme === "night"
          ? "linear-gradient(180deg, #1b5e20 0%, #1b5e20 100%)"
          : "linear-gradient(180deg, #388e3c 0%, #2e7d32 100%)",
      }} />
    </AbsoluteFill>
  );
};
