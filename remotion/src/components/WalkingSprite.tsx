/**
 * WalkingSprite — sprite that walks across the screen (WalkingWrapper pattern).
 * translateX travel + Math.sin vertical bounce + Math.sin lean rotation.
 * Lean (±maxLeanDeg) alternates each "step" — like a character rocking side to side.
 * Used by OCDVehicles, DancePet, ShapeRoundelay, PeekABoo, etc.
 */
import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export interface WalkingSpriteProps {
  /** Path relative to remotion/public/ e.g. "sprites/animals/cat.png" */
  src: string;
  /** Start X position in px (default: -200, off-screen left) */
  startX?: number;
  /** End X position in px (default: 2120, off-screen right) */
  endX?: number;
  /** Y base position from bottom in px (default: 160) */
  bottomPx?: number;
  /** Sprite size in px (default: 320) */
  size?: number;
  /** Bounce amplitude in px (default: 22) */
  bounceAmp?: number;
  /** Bounce frequency — higher = faster steps (default: 4.5) */
  bounceFreq?: number;
  /** Max lean/tilt angle in degrees (default: 8). Set 0 to disable. */
  maxLeanDeg?: number;
  /** Frame on which walking begins (default: 0) */
  startFrame?: number;
  /** Frame on which walking ends (default: durationInFrames) */
  endFrame?: number;
  /** Flip horizontally when walking right-to-left (default: false) */
  flipX?: boolean;
  /** Extra CSS transform appended last */
  extraTransform?: string;
}

export const WalkingSprite: React.FC<WalkingSpriteProps> = ({
  src,
  startX = -200,
  endX = 2120,
  bottomPx = 160,
  size = 320,
  bounceAmp = 22,
  bounceFreq = 4.5,
  maxLeanDeg = 8,
  startFrame = 0,
  endFrame,
  flipX = false,
  extraTransform = "",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const end = endFrame ?? durationInFrames;
  const t = frame / fps;
  const localF = frame - startFrame;

  const x = interpolate(
    frame,
    [startFrame, end],
    [startX, endX],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Vertical bounce — abs(sin) so object always lifts, never dips below baseline
  const bounce = localF >= 0 ? Math.abs(Math.sin(t * bounceFreq)) * bounceAmp : 0;

  // Side-to-side lean synced with bounce (lean right when bouncing up on right foot)
  const lean = maxLeanDeg > 0 ? Math.sin(t * bounceFreq) * maxLeanDeg : 0;

  const scaleX = flipX ? -1 : 1;

  return (
    <Img
      src={staticFile(src)}
      style={{
        position: "absolute",
        bottom: bottomPx,
        left: 0,
        width: size,
        height: size,
        objectFit: "contain",
        transform: `translateX(${x}px) translateY(${-bounce}px) rotate(${lean}deg) scaleX(${scaleX}) ${extraTransform}`,
        transformOrigin: "center bottom",
        willChange: "transform",
      }}
    />
  );
};
