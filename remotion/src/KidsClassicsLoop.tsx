import React from "react";
import { useCurrentFrame } from "remotion";
import { Img, staticFile } from "remotion";

// 5 min seamless loop — integer sin/cos cycles guarantee frame 0 === frame 9000
const LOOP_FRAMES = 9_000;
const W = 1920;
const H = 1080;

function loopSin(f: number, n: number, phase = 0) {
  return Math.sin((2 * Math.PI * n * f) / LOOP_FRAMES + phase);
}
function loopCos(f: number, n: number, phase = 0) {
  return Math.cos((2 * Math.PI * n * f) / LOOP_FRAMES + phase);
}

// Golden ratio phase offset — keeps sprites out of sync
const phi = Math.PI * 0.618033988;

export type KidsClassicsSprite = {
  path: string;
  size: number;
  baseX: number; // 0–1 relative to W
  baseY: number; // 0–1 relative to H
  xAmp: number;  // px drift amplitude
  xN: number;    // integer cycle count
  yAmp: number;
  yN: number;
  scaleAmp: number; // breathing scale amplitude (0.05 = ±5%)
  seed: number;     // unique phase seed
};

export type KidsClassicsLoopProps = {
  bgTop: string;
  bgBottom: string;
  sprites: KidsClassicsSprite[];
};

const DEFAULT_SPRITES: KidsClassicsSprite[] = [
  { path: "animals/bear_3d.png",   size: 460, baseX: 0.50, baseY: 0.44,
    xAmp: 80,  xN: 3, yAmp: 50, yN: 2, scaleAmp: 0.05, seed: 1 },
  { path: "objects/note_gold.png", size: 160, baseX: 0.18, baseY: 0.28,
    xAmp: 100, xN: 2, yAmp: 70, yN: 3, scaleAmp: 0.08, seed: 2 },
  { path: "objects/note_gold.png", size: 130, baseX: 0.80, baseY: 0.32,
    xAmp: 90,  xN: 4, yAmp: 60, yN: 2, scaleAmp: 0.07, seed: 3 },
  { path: "objects/star_3d.png",   size: 140, baseX: 0.14, baseY: 0.68,
    xAmp: 70,  xN: 3, yAmp: 55, yN: 4, scaleAmp: 0.06, seed: 4 },
  { path: "objects/star_3d.png",   size: 110, baseX: 0.86, baseY: 0.72,
    xAmp: 80,  xN: 2, yAmp: 45, yN: 3, scaleAmp: 0.08, seed: 5 },
];

export const KidsClassicsLoop: React.FC<Partial<KidsClassicsLoopProps>> = ({
  bgTop    = "#1a1080",
  bgBottom = "#3b2bb5",
  sprites  = DEFAULT_SPRITES,
}) => {
  const frame = useCurrentFrame();

  return (
    <div
      style={{
        width: W, height: H,
        overflow: "hidden",
        position: "relative",
        background: `linear-gradient(180deg, ${bgTop} 0%, ${bgBottom} 100%)`,
      }}
    >
      {/* Subtle animated background glow */}
      <div style={{
        position: "absolute",
        width: 800, height: 800,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%)",
        left: W * 0.5 - 400 + 120 * loopSin(frame, 2, 0),
        top:  H * 0.5 - 400 + 80  * loopCos(frame, 3, 1),
        pointerEvents: "none",
      }} />

      {(sprites as KidsClassicsSprite[]).map((s, i) => {
        const px  = s.seed * phi;
        const px2 = s.seed * phi + Math.PI * 1.3;
        const x   = s.baseX * W + s.xAmp * loopSin(frame, s.xN, px);
        const y   = s.baseY * H + s.yAmp * loopCos(frame, s.yN, px2);
        const sc  = 1 + s.scaleAmp * loopSin(frame, s.xN + 1, px + 1.5);

        return (
          <Img
            key={i}
            src={staticFile(`sprites/${s.path}`)}
            style={{
              position: "absolute",
              width:  s.size,
              height: s.size,
              left:   x - s.size / 2,
              top:    y - s.size / 2,
              transform: `scale(${sc})`,
              objectFit: "contain",
              filter: "drop-shadow(0px 8px 16px rgba(0,0,0,0.35))",
            }}
          />
        );
      })}
    </div>
  );
};
