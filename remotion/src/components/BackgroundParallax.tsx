/**
 * BackgroundParallax — reusable multi-layer parallax background.
 * Layers scroll at different speeds to create depth illusion.
 * Drop into any composition; each layer is a CSS gradient or image.
 */
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

export interface ParallaxLayer {
  /** CSS background (gradient or url(...)) */
  background: string;
  /** 0 = static, 1 = full scroll speed. Typical: sky=0.05, hills=0.2, trees=0.5 */
  speed: number;
  /** Optional opacity 0-1 */
  opacity?: number;
  /** Optional vertical oscillation amplitude in px (e.g. clouds bobbing) */
  bobAmplitude?: number;
  /** Oscillation frequency in Hz */
  bobFreq?: number;
}

interface Props {
  layers: ParallaxLayer[];
  /** Total horizontal travel in px for one full cycle (default: 200) */
  scrollRange?: number;
  /** Scroll cycle period in seconds (default: 40) */
  cycleSec?: number;
}

export const BackgroundParallax: React.FC<Props> = ({
  layers,
  scrollRange = 200,
  cycleSec = 40,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {layers.map((layer, i) => {
        const scrollX = Math.sin((t / cycleSec) * Math.PI * 2) * scrollRange * layer.speed;
        const bobY = layer.bobAmplitude
          ? Math.sin(t * (layer.bobFreq ?? 0.3) * Math.PI * 2) * layer.bobAmplitude
          : 0;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              inset: 0,
              background: layer.background,
              opacity: layer.opacity ?? 1,
              transform: `translateX(${scrollX}px) translateY(${bobY}px)`,
              backgroundSize: "cover",
              backgroundPosition: "center",
              willChange: "transform",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
