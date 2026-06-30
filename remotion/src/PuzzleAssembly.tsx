/**
 * PuzzleAssembly — parts fly in on arc trajectories → magnetic spring snap.
 * Silhouette in center fills piece by piece. Victory jump at the end.
 * No text. Universal EN/AR/ID content.
 *
 * Each composition renders 1 "puzzle" object (e.g. a truck, dinosaur, star).
 * Parts: up to 6 pieces defined in props.
 *
 * Timing per piece: 45f arc flight → 8f magnetic snap → hold
 * Victory: all assembled → 30f jump → 20f exit
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { BackgroundParallax, ParallaxLayer } from "./components/BackgroundParallax";
import { SpringBox } from "./components/SpringBox";

// ── Easing helpers ────────────────────────────────────────────────────────────
function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

// ── Puzzle piece definition ───────────────────────────────────────────────────
export interface PuzzlePiece {
  /** Sprite path (relative to remotion/public) */
  sprite: string;
  /** Final resting position relative to puzzle center (0,0) */
  targetX: number;
  targetY: number;
  /** Starting position (off-screen edge) */
  fromX: number;
  fromY: number;
  /** Arc height in px (positive = arcs upward) */
  arcHeight: number;
  /** Final rotation when snapped */
  rotation?: number;
  /** Size in px */
  size: number;
  /** Accent color for snap flash */
  snapColor: string;
}

// ── Pre-built puzzles ─────────────────────────────────────────────────────────
type PuzzleName = "star" | "heart" | "truck" | "rocket" | "flower";

const PUZZLE_PIECES: Record<PuzzleName, { pieces: PuzzlePiece[]; silhouette: string; bgColor: string }> = {
  star: {
    silhouette: "sprites/shapes_3d/star.png",
    bgColor: "#FFF9C4",
    pieces: [
      { sprite: "sprites/shapes_3d/star.png", targetX: 0, targetY: 0, fromX: -1000, fromY: -400, arcHeight: -200, size: 200, snapColor: "#FFD700", rotation: 0 },
      { sprite: "sprites/shapes_3d/star.png", targetX: 120, targetY: 80, fromX: 1000, fromY: -300, arcHeight: -180, size: 140, snapColor: "#FF9800", rotation: 30 },
      { sprite: "sprites/shapes_3d/star.png", targetX: -120, targetY: 80, fromX: -1000, fromY: 300, arcHeight: 160, size: 140, snapColor: "#FFC107", rotation: -25 },
      { sprite: "sprites/shapes_3d/star.png", targetX: 60, targetY: -120, fromX: 1000, fromY: 400, arcHeight: 140, size: 120, snapColor: "#FFEB3B", rotation: 15 },
      { sprite: "sprites/shapes_3d/star.png", targetX: -60, targetY: -100, fromX: 0, fromY: 600, arcHeight: 200, size: 110, snapColor: "#FFD600", rotation: -10 },
    ],
  },
  heart: {
    silhouette: "sprites/shapes_3d/heart.png",
    bgColor: "#FCE4EC",
    pieces: [
      { sprite: "sprites/shapes_3d/heart.png", targetX: 0, targetY: 0, fromX: -1000, fromY: 0, arcHeight: -220, size: 220, snapColor: "#E91E63", rotation: 0 },
      { sprite: "sprites/shapes_3d/heart.png", targetX: 100, targetY: -60, fromX: 1000, fromY: -300, arcHeight: -150, size: 130, snapColor: "#F06292", rotation: 20 },
      { sprite: "sprites/shapes_3d/heart.png", targetX: -100, targetY: 60, fromX: -800, fromY: 400, arcHeight: 180, size: 130, snapColor: "#AD1457", rotation: -20 },
      { sprite: "sprites/shapes_3d/heart.png", targetX: 0, targetY: 120, fromX: 0, fromY: 600, arcHeight: 160, size: 100, snapColor: "#FF4081", rotation: 5 },
    ],
  },
  truck: {
    silhouette: "sprites/objects/car_3d.png",
    bgColor: "#E3F2FD",
    pieces: [
      { sprite: "sprites/objects/car_3d.png",   targetX: 0,   targetY: 0,   fromX: -1000, fromY: 0,    arcHeight: -180, size: 240, snapColor: "#1565C0", rotation: 0  },
      { sprite: "sprites/shapes_3d/circle.png", targetX: -90, targetY: 110, fromX: -800,  fromY: 500,  arcHeight:  200, size: 80,  snapColor: "#37474F", rotation: 0  },
      { sprite: "sprites/shapes_3d/circle.png", targetX:  90, targetY: 110, fromX:  1000, fromY: 500,  arcHeight:  180, size: 80,  snapColor: "#37474F", rotation: 0  },
      { sprite: "sprites/shapes_3d/square.png", targetX:  80, targetY: -60, fromX:  1000, fromY: -400, arcHeight: -160, size: 100, snapColor: "#90CAF9", rotation: 0  },
    ],
  },
  rocket: {
    silhouette: "sprites/shapes_3d/triangle.png",
    bgColor: "#EDE7F6",
    pieces: [
      { sprite: "sprites/shapes_3d/triangle.png", targetX: 0,  targetY: -80, fromX: 0,     fromY: -600, arcHeight:  100, size: 200, snapColor: "#7C4DFF", rotation: 0   },
      { sprite: "sprites/shapes_3d/oval.png",     targetX: 0,  targetY:  80, fromX: -1000, fromY: 0,    arcHeight: -200, size: 140, snapColor: "#E040FB", rotation: 0   },
      { sprite: "sprites/shapes_3d/star.png",     targetX: 0,  targetY: -10, fromX:  1000, fromY: -200, arcHeight: -150, size:  80, snapColor: "#FFD740", rotation: 0   },
      { sprite: "sprites/shapes_3d/diamond.png",  targetX: -80,targetY:  60, fromX: -1000, fromY: 400,  arcHeight:  160, size:  70, snapColor: "#FF6D00", rotation: -30 },
      { sprite: "sprites/shapes_3d/diamond.png",  targetX:  80,targetY:  60, fromX:  1000, fromY: 400,  arcHeight:  160, size:  70, snapColor: "#FF6D00", rotation:  30 },
    ],
  },
  flower: {
    silhouette: "sprites/shapes_3d/oval.png",
    bgColor: "#F3E5F5",
    pieces: [
      { sprite: "sprites/shapes_3d/oval.png",   targetX: 0,    targetY: 0,    fromX: 0,     fromY: -600, arcHeight:  120, size: 120, snapColor: "#FFEB3B", rotation: 0   },
      { sprite: "sprites/shapes_3d/oval.png",   targetX: 0,    targetY: -120, fromX: -800,  fromY: -300, arcHeight: -160, size: 100, snapColor: "#F48FB1", rotation: 0   },
      { sprite: "sprites/shapes_3d/oval.png",   targetX: 0,    targetY:  120, fromX:  800,  fromY:  300, arcHeight:  160, size: 100, snapColor: "#CE93D8", rotation: 0   },
      { sprite: "sprites/shapes_3d/oval.png",   targetX: -120, targetY: 0,    fromX: -1000, fromY: 0,    arcHeight: -140, size: 100, snapColor: "#80DEEA", rotation: 90  },
      { sprite: "sprites/shapes_3d/oval.png",   targetX:  120, targetY: 0,    fromX:  1000, fromY: 0,    arcHeight: -140, size: 100, snapColor: "#A5D6A7", rotation: 90  },
    ],
  },
};

// ── Snap flash ────────────────────────────────────────────────────────────────
const SnapFlash: React.FC<{ cx: number; cy: number; frame: number; color: string }> = ({ cx, cy, frame, color }) => {
  const op = interpolate(frame, [0, 8], [0.9, 0], { extrapolateRight: "clamp" });
  const sc = 1 + frame * 0.15;
  if (op <= 0) return null;
  return (
    <div style={{
      position: "absolute",
      left: cx - 50, top: cy - 50,
      width: 100, height: 100,
      borderRadius: "50%",
      backgroundColor: color,
      opacity: op,
      transform: `scale(${sc})`,
      pointerEvents: "none",
    }} />
  );
};

// ── Main composition ──────────────────────────────────────────────────────────
export interface PuzzleAssemblyProps {
  puzzle: PuzzleName;
  musicFile?: string;
  /** How many times to loop the assembly (default: 2) */
  loops?: number;
}

// Frames per piece
const PIECE_FLY = 45;
const SNAP_DUR  = 10;
const VICTORY   = 60;
const PIECE_DUR = PIECE_FLY + SNAP_DUR;

export const PuzzleAssembly: React.FC<PuzzleAssemblyProps> = ({
  puzzle = "star",
  musicFile = "Wholesome.mp3",
  loops = 2,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();

  const cfg    = PUZZLE_PIECES[puzzle];
  const pieces = cfg.pieces;
  const cx     = width  / 2;
  const cy     = height / 2;

  const totalAssembly = pieces.length * PIECE_DUR + VICTORY;
  const loopFrame     = frame % totalAssembly;

  const assembled     = Math.floor(loopFrame / PIECE_DUR);
  const isVictory     = loopFrame >= pieces.length * PIECE_DUR;
  const victoryF      = loopFrame - pieces.length * PIECE_DUR;

  // Victory jump: spring upward then down
  const victorySp = spring({
    frame: victoryF,
    fps,
    config: { damping: 8, stiffness: 120, mass: 0.6 },
    durationInFrames: 20,
  });
  const victoryY  = isVictory
    ? interpolate(victorySp, [0, 1], [0, -120], { extrapolateRight: "clamp" })
    : 0;
  const victoryScale = isVictory
    ? 1 + Math.abs(Math.sin(victoryF * 0.3)) * 0.08
    : 1;

  // Background
  const bgLayers: ParallaxLayer[] = [
    { background: `linear-gradient(180deg, ${cfg.bgColor} 0%, ${cfg.bgColor}99 100%)`, speed: 0, opacity: 1 },
    { background: "radial-gradient(ellipse at 50% 40%, rgba(255,255,255,0.6) 0%, transparent 70%)", speed: 0.05, opacity: 0.8 },
  ];

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {musicFile && <Audio src={staticFile(`music/${musicFile}`)} volume={0.2} loop />}

      <BackgroundParallax layers={bgLayers} />

      {/* Silhouette (ghost) */}
      <div style={{
        position: "absolute",
        left: cx - 150, top: cy - 150,
        width: 300, height: 300,
        opacity: 0.12,
        transform: `translateY(${victoryY}px) scale(${victoryScale})`,
        transformOrigin: "center center",
      }}>
        <Img src={staticFile(cfg.silhouette)}
             style={{ width: 300, height: 300, objectFit: "contain",
               filter: "grayscale(1)" }} />
      </div>

      {/* Assembled pieces */}
      {pieces.map((piece, pi) => {
        const pieceStartF = pi * PIECE_DUR;
        const localF      = loopFrame - pieceStartF;
        const hasLanded   = loopFrame >= pieceStartF + PIECE_FLY;
        const isFlying    = localF >= 0 && localF < PIECE_FLY;
        const isSnapping  = localF >= PIECE_FLY && localF < PIECE_FLY + SNAP_DUR;

        if (localF < 0) return null;  // not yet started

        let px = cx + piece.targetX;
        let py = cy + piece.targetY;
        let sc = 1;
        let rot = piece.rotation ?? 0;

        if (isFlying) {
          // Arc trajectory: linear X + parabolic Y arc
          const t    = localF / PIECE_FLY;
          const ease = easeOutCubic(t);
          px = (cx + piece.fromX) + ease * ((cx + piece.targetX) - (cx + piece.fromX));
          const arcY = -piece.arcHeight * 4 * t * (1 - t);  // parabola peaking at midpoint
          py = (cy + piece.fromY) + ease * ((cy + piece.targetY) - (cy + piece.fromY)) + arcY;
          sc = 0.7 + ease * 0.3;
          rot = (piece.rotation ?? 0) * ease;
        } else if (isSnapping) {
          // Spring snap into final position
          const snapSp = spring({
            frame: localF - PIECE_FLY,
            fps,
            config: { damping: 6, stiffness: 200, mass: 0.3 },
            durationInFrames: SNAP_DUR,
          });
          sc = 1 + Math.abs(snapSp - 1) * 0.2;  // slight size pulse on snap
        }

        // After assembly: follow victory jump
        if (hasLanded && isVictory) {
          py += victoryY;
          sc  *= victoryScale;
        }

        return (
          <React.Fragment key={pi}>
            <Img
              src={staticFile(piece.sprite)}
              style={{
                position: "absolute",
                left: px - piece.size / 2,
                top:  py - piece.size / 2,
                width: piece.size, height: piece.size,
                objectFit: "contain",
                transform: `scale(${sc}) rotate(${rot}deg)`,
                willChange: "transform",
              }}
            />
            {/* Snap flash */}
            {isSnapping && (
              <SnapFlash
                cx={px} cy={py}
                frame={localF - PIECE_FLY}
                color={piece.snapColor}
              />
            )}
          </React.Fragment>
        );
      })}

      {/* Victory confetti */}
      {isVictory && Array.from({ length: 30 }, (_, i) => {
        const x    = (i * 67) % width;
        const fall = (victoryF * 6 + i * 40) % (height + 80);
        const op   = interpolate(victoryF, [30, 60], [1, 0], { extrapolateRight: "clamp" });
        const colors = ["#FF4444","#FFD700","#4CAF50","#2196F3","#FF69B4","#FF9800"];
        return (
          <div key={i} style={{
            position: "absolute",
            left: x, top: fall - 40,
            width: 14, height: 14,
            borderRadius: i % 2 === 0 ? "50%" : "2px",
            backgroundColor: colors[i % colors.length],
            opacity: op,
            transform: `rotate(${victoryF * 8 + i * 30}deg)`,
          }} />
        );
      })}
    </AbsoluteFill>
  );
};
