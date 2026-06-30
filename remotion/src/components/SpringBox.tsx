/**
 * SpringBox — reusable spring-in wrapper.
 * Any child component gets a spring-based entry: scale + optional translateY drop.
 * Configure damping/stiffness/mass to tune bounciness.
 */
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface SpringBoxProps {
  /** Frame on which the animation begins */
  from?: number;
  /** spring damping (higher = less bounce, default 10) */
  damping?: number;
  /** spring stiffness (higher = faster, default 100) */
  stiffness?: number;
  /** spring mass (lower = snappier, default 0.5) */
  mass?: number;
  /** Initial scale (default 0) */
  fromScale?: number;
  /** Drop-in Y offset in px (positive = from above, default 0) */
  dropY?: number;
  /** Optional opacity fade-in (default true) */
  fadeIn?: boolean;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

export const SpringBox: React.FC<SpringBoxProps> = ({
  from = 0,
  damping = 10,
  stiffness = 100,
  mass = 0.5,
  fromScale = 0,
  dropY = 0,
  fadeIn = true,
  children,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const s = spring({
    frame: frame - from,
    fps,
    config: { damping, stiffness, mass },
    durationInFrames: fps * 1.2,
  });

  const scale = interpolate(s, [0, 1], [fromScale, 1], { extrapolateRight: "clamp" });
  const translateY = interpolate(s, [0, 1], [dropY, 0], { extrapolateRight: "clamp" });
  const opacity = fadeIn ? interpolate(s, [0, 0.3], [0, 1], { extrapolateRight: "clamp" }) : 1;

  return (
    <div
      style={{
        transform: `scale(${scale}) translateY(${translateY}px)`,
        opacity,
        transformOrigin: "center bottom",
        ...style,
      }}
    >
      {children}
    </div>
  );
};
