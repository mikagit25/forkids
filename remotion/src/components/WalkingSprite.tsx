/**
 * WalkingSprite — sprite that walks across the screen left-to-right (or loops).
 * Applies translateX travel + Math.sin vertical bounce for organic walking feel.
 * Used by OCDVehicles, DancePet, ShapeRoundelay, etc.
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
  /** Frame on which walking begins (default: 0) */
  startFrame?: number;
  /** Frame on which walking ends (default: durationInFrames) */
  endFrame?: number;
  /** Flip horizontally when walking right-to-left (default: false) */
  flipX?: boolean;
  /** Extra CSS transform appended after walk (e.g. "scale(1.1)") */
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

  const bounce = localF >= 0
    ? Math.abs(Math.sin(t * bounceFreq)) * bounceAmp
    : 0;

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
        transform: `translateX(${x}px) translateY(${-bounce}px) scaleX(${scaleX}) ${extraTransform}`,
        willChange: "transform",
      }}
    />
  );
};
