/**
 * LullabyLoop — 5-minute seamless sleep content loop.
 * Rendered once, then extended to 1-2h via FFmpeg in generate_lullaby.py.
 * Format: 1920×1080, 30fps, dark background, BPM 50-55.
 * No text, no faces after frame 900 — universal content.
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export interface LullabyLoopProps {
  theme: "stars" | "ocean" | "garden" | "train" | "rain" | "forest";
  bgColorTop: string;
  bgColorBottom: string;
  accentColor: string;
  musicFile?: string;
  bpm?: number;
  phaseOffset?: number; // 0..1 — offsets all star phases so EN/AR/ID have different visual rhythm
}

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ── Background star field (tiny CSS dots, 3 depth layers) ────────────────────
const StarField: React.FC<{
  w: number; h: number; frame: number; color: string;
}> = ({ w, h, frame, color }) => {
  const r = seededRand;
  const t = frame / 30;
  return (
    <>
      {Array.from({ length: 90 }, (_, i) => {
        const cx = r(i * 7) * w;
        const cy = r(i * 11) * h;
        const sz = 1 + r(i * 3) * 2.5;
        const tw = 0.6 + r(i * 5) * 0.8;
        const ph = r(i * 13) * Math.PI * 2;
        const op = (0.12 + r(i * 17) * 0.35) * (0.7 + 0.3 * Math.sin(t * tw + ph));
        return (
          <div key={i} style={{
            position: "absolute",
            left: cx - sz / 2, top: cy - sz / 2,
            width: sz, height: sz,
            borderRadius: "50%",
            backgroundColor: color,
            opacity: op,
          }} />
        );
      })}
    </>
  );
};

// ── Drifting star sprite (FLUX PNG, travels across screen) ───────────────────
const DriftingStar: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number;
  phaseOffset: number; yOffset?: number; sizeScale?: number;
}> = ({ seed, w, h, frame, fps, phaseOffset, yOffset = 0, sizeScale = 1 }) => {
  const r = seededRand;
  const t = frame / fps;

  // Size tier by seed range
  const rawSize = seed <= 3  ? 55  + r(seed * 3) * 35   // far: 55–90px
                : seed <= 7  ? 110 + r(seed * 3) * 55   // mid: 110–165px
                :              175 + r(seed * 3) * 95;  // near: 175–270px
  const size = rawSize * sizeScale;

  // Crossing period (seconds): far=slow, near=faster
  const period = seed <= 3  ? 75 + r(seed * 7) * 35
               : seed <= 7  ? 48 + r(seed * 7) * 22
               :              30 + r(seed * 7) * 16;

  const direction = r(seed * 17) > 0.5 ? 1 : -1;
  const phase     = ((r(seed * 23) + phaseOffset) % 1 + 1) % 1;

  // X: linear wrap
  const xNorm = ((t / period + phase) % 1 + 1) % 1;
  const rawX  = xNorm * (w + size * 2) - size;
  const cx    = direction > 0 ? rawX : w + size - rawX;

  // Y: base + gentle oscillation
  const yBase  = r(seed * 31) * h * 0.78 + h * 0.11;
  const yFreq  = 0.12 + r(seed * 37) * 0.14;
  const yAmp   = 22 + r(seed * 41) * 28;
  const yPh    = r(seed * 43) * Math.PI * 2;
  const cy     = yBase + yOffset + Math.sin(t * yFreq + yPh) * yAmp;

  // Wobble (PIP/BWW formula)
  const s = seed * 0.1;
  const scaleX = 1 + Math.sin(t * (8.3 + s * 0.7)) * 0.038 + Math.sin(t * (5.1 + s * 0.4)) * 0.020;
  const scaleY = 1 + Math.sin(t * (7.7 + s * 0.9)) * 0.038 + Math.cos(t * (4.2 + s * 1.1)) * 0.020;
  const rot    = Math.sin(t * (6.5 + s * 0.5)) * 1.4;

  // Twinkle + subtle hue shift
  const twFreq = 0.7 + r(seed * 53) * 0.7;
  const twPh   = r(seed * 59) * Math.PI * 2;
  const opacity = 0.50 + 0.38 * Math.sin(t * twFreq + twPh);
  const hue    = Math.sin(t * 0.07 + seed) * 22;

  return (
    <Img
      src={staticFile("sprites/objects/star_sleep.png")}
      style={{
        position: "absolute",
        left: cx - size / 2,
        top:  cy - size / 2,
        width: size, height: size,
        opacity,
        mixBlendMode: "screen" as const,
        transform: `scaleX(${scaleX}) scaleY(${scaleY}) rotate(${rot}deg)`,
        filter: `drop-shadow(0 0 ${size * 0.22}px rgba(255,215,70,0.65)) hue-rotate(${hue}deg)`,
        pointerEvents: "none",
      }}
    />
  );
};

// ── Ocean: drifting jellyfish (FLUX PNG) ─────────────────────────────────────
const DriftingJellyfish: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number; phaseOffset: number;
}> = ({ seed, w, h, frame, fps, phaseOffset }) => {
  const r = seededRand;
  const t = frame / fps;

  const size    = 100 + r(seed * 3) * 140;   // 100–240px
  const period  = 50  + r(seed * 7) * 40;    // 50–90s to cross screen
  const dir     = r(seed * 17) > 0.5 ? 1 : -1;
  const phase   = ((r(seed * 23) + phaseOffset) % 1 + 1) % 1;
  const xNorm   = ((t / period + phase) % 1 + 1) % 1;
  const rawX    = xNorm * (w + size * 2) - size;
  const cx      = dir > 0 ? rawX : w + size - rawX;

  // Y: mid-screen with gentle vertical drift
  const yBase   = h * 0.2 + r(seed * 31) * h * 0.55;
  const cy      = yBase + Math.sin(t * (0.18 + r(seed * 37) * 0.1) + r(seed * 43) * Math.PI * 2) * 35;

  // Pulse (jellyfish breathing)
  const pulse   = 1 + 0.12 * Math.sin(t * (1.2 + r(seed * 5) * 0.4) + r(seed * 11) * Math.PI * 2);

  // Wobble (PIP/BWW)
  const s       = seed * 0.1;
  const scaleX  = pulse * (1 + Math.sin(t * (8.3 + s * 0.7)) * 0.025);
  const scaleY  = pulse * (1 + Math.cos(t * (7.7 + s * 0.9)) * 0.025);
  const rot     = Math.sin(t * (4.5 + s * 0.5)) * 6;

  // Glow opacity — gentle breathe
  const opacity = 0.55 + 0.32 * Math.sin(t * (0.8 + r(seed * 53) * 0.5) + r(seed * 59) * Math.PI * 2);
  const hue     = Math.sin(t * 0.06 + seed) * 40; // shift between blue and purple

  return (
    <Img
      src={staticFile("sprites/objects/jellyfish_glow.png")}
      style={{
        position: "absolute",
        left: cx - (size * scaleX) / 2,
        top:  cy - (size * scaleY) / 2,
        width: size * scaleX, height: size * scaleY,
        opacity,
        mixBlendMode: "screen" as const,
        transform: `rotate(${rot}deg)`,
        filter: `drop-shadow(0 0 ${size * 0.18}px rgba(80,120,255,0.6)) hue-rotate(${hue}deg)`,
        pointerEvents: "none",
      }}
    />
  );
};

// ── Ocean: rising bubbles ────────────────────────────────────────────────────
const RisingBubble: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number;
}> = ({ seed, w, h, frame, fps }) => {
  const r  = seededRand;
  const t  = frame / fps;
  const sz = 8 + r(seed * 3) * 28;                // 8–36px
  const riseSpeed  = 20 + r(seed * 7) * 30;       // px/s
  const period     = (h + sz) / riseSpeed;
  const initPhase  = r(seed * 13);
  const yNorm      = ((t / period + initPhase) % 1 + 1) % 1;
  const cy         = h + sz - yNorm * (h + sz * 2); // bottom→top
  const cx         = r(seed * 23) * w * 0.9 + w * 0.05;
  const sway       = Math.sin(t * (0.9 + r(seed * 31) * 0.4) + r(seed * 37) * 6) * 18;
  const opacity    = (0.3 + r(seed * 41) * 0.4) * (0.7 + 0.3 * Math.sin(t * 1.5 + r(seed * 43) * 6));
  return (
    <div style={{
      position: "absolute",
      left: cx + sway - sz / 2, top: cy - sz / 2,
      width: sz, height: sz,
      borderRadius: "50%",
      border: `${sz * 0.06 + 0.5}px solid rgba(140,200,255,${opacity * 0.8})`,
      background: `radial-gradient(circle at 35% 35%, rgba(200,230,255,${opacity * 0.3}), rgba(80,140,220,${opacity * 0.08}))`,
      boxShadow: `0 0 ${sz * 0.5}px rgba(100,180,255,${opacity * 0.4})`,
    }} />
  );
};

// ── Ocean: drifting fish (FLUX PNG) ─────────────────────────────────────────
const DriftingFish: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number; phaseOffset: number;
}> = ({ seed, w, h, frame, fps, phaseOffset }) => {
  const r = seededRand;
  const t = frame / fps;
  const size   = 60 + r(seed * 3) * 80;
  const period = 40 + r(seed * 7) * 30;
  const dir    = r(seed * 17) > 0.5 ? 1 : -1;
  const phase  = ((r(seed * 23) + phaseOffset * 0.6) % 1 + 1) % 1;
  const xNorm  = ((t / period + phase) % 1 + 1) % 1;
  const rawX   = xNorm * (w + size * 2) - size;
  const cx     = dir > 0 ? rawX : w + size - rawX;
  const yBase  = h * 0.3 + r(seed * 31) * h * 0.5;
  const cy     = yBase + Math.sin(t * (0.25 + r(seed * 37) * 0.15) + r(seed * 43) * 6) * 25;
  const wobble = Math.sin(t * 5 + r(seed * 53) * 6) * 4;  // tail waggle expressed as rotation
  const opacity= 0.45 + 0.35 * Math.sin(t * (0.6 + r(seed * 59) * 0.4) + r(seed * 61) * 6);
  // flip horizontally if moving right so fish faces correct direction
  const flipX  = dir > 0 ? -1 : 1;

  return (
    <Img
      src={staticFile("sprites/objects/fish_deep.png")}
      style={{
        position: "absolute",
        left: cx - size / 2, top: cy - size / 2,
        width: size, height: size,
        opacity,
        mixBlendMode: "screen" as const,
        transform: `scaleX(${flipX}) rotate(${wobble}deg)`,
        filter: `drop-shadow(0 0 ${size * 0.15}px rgba(0,220,200,0.5))`,
        pointerEvents: "none",
      }}
    />
  );
};

// ── Ocean: caustic light rays from above ─────────────────────────────────────
const OceanCaustics: React.FC<{ w: number; h: number; frame: number }> = ({ w, h, frame }) => {
  const t = frame / 30;
  return (
    <>
      {[0, 1, 2, 3].map(i => {
        const x   = w * (0.15 + i * 0.22 + Math.sin(t * 0.08 + i * 1.4) * 0.05);
        const ht  = h * (0.4 + Math.sin(t * 0.05 + i * 2.1) * 0.08);
        const op  = 0.04 + 0.025 * Math.sin(t * 0.12 + i * 1.7);
        const wid = 30 + Math.sin(t * 0.09 + i * 1.1) * 14;
        return (
          <div key={i} style={{
            position: "absolute",
            left: x - wid / 2, top: 0,
            width: wid, height: ht,
            background: `linear-gradient(180deg, rgba(80,160,255,${op}) 0%, transparent 100%)`,
            transform: `skewX(${Math.sin(t * 0.07 + i * 0.9) * 6}deg)`,
          }} />
        );
      })}
    </>
  );
};

// ── Firefly ──────────────────────────────────────────────────────────────────
const Firefly: React.FC<{
  seed: number; w: number; h: number; frame: number; color: string;
}> = ({ seed, w, h, frame, color }) => {
  const r = seededRand;
  const baseX = r(seed * 7) * w;
  const baseY = h * 0.4 + r(seed * 11) * h * 0.5;
  const driftX = Math.sin(frame * 0.012 + r(seed * 13) * 6) * 60;
  const driftY = Math.cos(frame * 0.009 + r(seed * 17) * 4) * 40;
  const glowCycle = 0.3 + 0.7 * Math.pow(Math.sin(frame * 0.04 + r(seed * 5) * Math.PI), 2);
  return (
    <div style={{
      position: "absolute",
      left: baseX + driftX - 3,
      top:  baseY + driftY - 3,
      width: 6, height: 6,
      borderRadius: "50%",
      backgroundColor: color,
      opacity: glowCycle * 0.9,
      boxShadow: `0 0 ${8 * glowCycle}px ${4 * glowCycle}px ${color}`,
    }} />
  );
};

// ── Rain drop ────────────────────────────────────────────────────────────────
const RainDrop: React.FC<{
  seed: number; w: number; h: number; frame: number; fps: number;
}> = ({ seed, w, h, frame, fps }) => {
  const r = seededRand;
  const x = r(seed * 7) * w;
  const speed = 3 + r(seed * 11) * 4; // px per frame
  const startY = -(20 + r(seed * 3) * 30);
  const offset = Math.round(r(seed * 13) * fps * 5);
  const localFrame = (frame + offset) % (fps * 5);
  const y = startY + localFrame * speed;
  if (y > h + 20) return null;
  const opacity = 0.05 + r(seed * 17) * 0.12;
  return (
    <div style={{
      position: "absolute",
      left: x,
      top: y,
      width: 1,
      height: 12 + r(seed * 5) * 8,
      backgroundColor: "#AACCEE",
      opacity,
      transform: "rotate(10deg)",
    }} />
  );
};

// ── Moon ─────────────────────────────────────────────────────────────────────
const Moon: React.FC<{ frame: number; w: number }> = ({ frame, w }) => {
  const t = frame / 30;
  const glow = 0.14 + 0.05 * Math.sin(t * 0.4);
  const breathe = 1 + 0.015 * Math.sin(t * 0.25);
  return (
    <div style={{
      position: "absolute",
      right: w * 0.08,
      top: "6%",
      width: 110 * breathe, height: 110 * breathe,
      borderRadius: "50%",
      backgroundColor: "#FFFFD5",
      opacity: 0.75,
      boxShadow: `0 0 ${70 + glow * 50}px ${35 + glow * 30}px rgba(255,255,180,${glow}), 0 0 ${140 + glow * 80}px rgba(255,255,150,${glow * 0.4})`,
    }} />
  );
};

// ── Main ─────────────────────────────────────────────────────────────────────
export const LullabyLoop: React.FC<LullabyLoopProps> = ({
  theme,
  bgColorTop,
  bgColorBottom,
  accentColor,
  musicFile,
  bpm = 52,
  phaseOffset = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const PARTICLE_COUNT = theme === "rain" ? 40 : 12;

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(180deg, ${bgColorTop} 0%, ${bgColorBottom} 100%)`,
      overflow: "hidden",
    }}>
      {musicFile && (
        <Audio
          src={staticFile(`music/${musicFile}`)}
          volume={0.12}
          loop
        />
      )}

      {/* Moon visible in all themes */}
      <Moon frame={frame} w={width} />

      {/* Theme-specific elements */}
      {theme === "stars" && (
        <>
          {/* Background field of tiny static-drift stars */}
          <StarField w={width} h={height} frame={frame} color={accentColor} />

          {/* Far layer: 3 small slow stars */}
          {[1,2,3].map(i => (
            <DriftingStar key={`far${i}`} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* Mid layer: 4 medium stars */}
          {[4,5,6,7].map(i => (
            <DriftingStar key={`mid${i}`} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* Near layer: 3 large fast stars */}
          {[8,9,10].map(i => (
            <DriftingStar key={`near${i}`} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* 3 pairs: two stars drifting together with Y offset */}
          {[20,21,22].map(i => (
            <React.Fragment key={`pair${i}`}>
              <DriftingStar seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} yOffset={-28} sizeScale={1.0} />
              <DriftingStar seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} yOffset={32} sizeScale={0.7} />
            </React.Fragment>
          ))}
        </>
      )}

      {theme === "ocean" && (
        <>
          {/* Caustic light shafts from surface */}
          <OceanCaustics w={width} h={height} frame={frame} />

          {/* 5 drifting FLUX jellyfish, 2 size tiers */}
          {[1,2,3,4,5].map(i => (
            <DriftingJellyfish key={i} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* 3 drifting fish */}
          {[10,11,12].map(i => (
            <DriftingFish key={i} seed={i} w={width} h={height} frame={frame} fps={fps} phaseOffset={phaseOffset} />
          ))}

          {/* Rising bubbles: 18 at various sizes + speeds */}
          {Array.from({ length: 18 }, (_, i) => (
            <RisingBubble key={i} seed={i + 1} w={width} h={height} frame={frame} fps={fps} />
          ))}

          {/* Deep ocean ambient glow at bottom */}
          <div style={{
            position: "absolute", bottom: 0, left: 0, right: 0, height: "30%",
            background: "linear-gradient(0deg, rgba(0,40,80,0.5) 0%, transparent 100%)",
            pointerEvents: "none",
          }} />
        </>
      )}

      {(theme === "garden" || theme === "forest") && (
        <>
          {Array.from({ length: PARTICLE_COUNT }, (_, i) => (
            <Firefly key={i} seed={i + 1} w={width} h={height} frame={frame} color={accentColor} />
          ))}
        </>
      )}

      {theme === "rain" && (
        <>
          {Array.from({ length: PARTICLE_COUNT }, (_, i) => (
            <RainDrop key={i} seed={i + 1} w={width} h={height} frame={frame} fps={fps} />
          ))}
          {/* Cosy window glow */}
          <div style={{
            position: "absolute",
            right: "8%", bottom: "10%",
            width: 200, height: 250,
            borderRadius: 8,
            background: `radial-gradient(ellipse at center, rgba(255,200,100,0.12) 0%, transparent 70%)`,
          }} />
        </>
      )}

      {theme === "train" && (
        <>
          {/* ── Outside (seen through window): parallax landscape ── */}

          {/* Far layer: distant hills scrolling very slowly */}
          {Array.from({ length: 5 }, (_, i) => {
            const layerW = width * 0.45;
            const speed  = 0.18; // px/frame
            const x = ((i * layerW - frame * speed) % (layerW * 5 + width) + layerW * 5 + width) % (layerW * 5 + width) - layerW;
            const hillH = height * (0.22 + seededRand(i * 7) * 0.12);
            const hue = 200 + seededRand(i * 11) * 20;
            return (
              <div key={`hill${i}`} style={{
                position: "absolute",
                left: x,
                bottom: height * 0.18,
                width: layerW,
                height: hillH,
                borderRadius: "50% 50% 0 0",
                backgroundColor: `hsl(${hue},25%,9%)`,
              }} />
            );
          })}

          {/* Mid layer: tree silhouettes */}
          {Array.from({ length: 14 }, (_, i) => {
            const speed  = 1.2; // px/frame
            const gap    = 110 + seededRand(i * 7) * 90;
            const totalW = 14 * 140;
            const x = ((i * gap - frame * speed) % totalW + totalW + width) % totalW - gap;
            const treeH  = height * (0.14 + seededRand(i * 11) * 0.10);
            const treeW  = 22 + seededRand(i * 13) * 28;
            return (
              <React.Fragment key={`tree${i}`}>
                {/* Trunk */}
                <div style={{
                  position: "absolute",
                  left: x + treeW * 0.4,
                  bottom: height * 0.18,
                  width: treeW * 0.2,
                  height: treeH * 0.4,
                  backgroundColor: "#090c08",
                }} />
                {/* Crown */}
                <div style={{
                  position: "absolute",
                  left: x,
                  bottom: height * 0.18 + treeH * 0.3,
                  width: treeW,
                  height: treeH * 0.8,
                  borderRadius: "50% 50% 20% 20%",
                  backgroundColor: "#060d05",
                }} />
              </React.Fragment>
            );
          })}

          {/* Near layer: telegraph poles + wire */}
          {Array.from({ length: 8 }, (_, i) => {
            const speed  = 4.5;
            const gap    = 240;
            const totalW = 8 * gap;
            const x = ((i * gap - frame * speed) % totalW + totalW + width) % totalW - gap;
            return (
              <React.Fragment key={`pole${i}`}>
                <div style={{
                  position: "absolute",
                  left: x,
                  bottom: height * 0.18,
                  width: 5,
                  height: height * 0.35,
                  backgroundColor: "rgba(20,15,8,0.9)",
                }} />
                <div style={{
                  position: "absolute",
                  left: x - gap + 5,
                  bottom: height * 0.18 + height * 0.33,
                  width: gap,
                  height: 2,
                  background: "rgba(20,15,8,0.5)",
                }} />
              </React.Fragment>
            );
          })}

          {/* Ground strip */}
          <div style={{
            position: "absolute",
            bottom: 0, left: 0, right: 0,
            height: height * 0.19,
            background: "linear-gradient(0deg, #040602 0%, #080d06 100%)",
          }} />

          {/* Flickering distant lights (farmhouses) */}
          {Array.from({ length: 6 }, (_, i) => {
            const speed  = 0.55;
            const gap    = width * 0.38;
            const totalW = 6 * gap;
            const x = ((i * gap - frame * speed) % totalW + totalW + width) % totalW - gap;
            const flicker = 0.5 + 0.5 * Math.sin(frame * (0.07 + seededRand(i * 5) * 0.04) + i * 1.9);
            const y = height * 0.48 + seededRand(i * 7) * height * 0.12;
            return (
              <div key={`light${i}`} style={{
                position: "absolute",
                left: x, top: y,
                width: 6, height: 4,
                backgroundColor: `rgba(255,200,80,${0.6 * flicker})`,
                boxShadow: `0 0 ${10 * flicker}px ${5 * flicker}px rgba(255,180,60,${0.4 * flicker})`,
              }} />
            );
          })}

          {/* ── Window frame overlay ── */}
          {/* Top/bottom rails */}
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0,
            height: "16%",
            background: "linear-gradient(180deg, rgba(15,10,5,0.98) 0%, rgba(15,10,5,0.7) 70%, transparent 100%)",
          }} />
          <div style={{
            position: "absolute", bottom: 0, left: 0, right: 0,
            height: "18%",
            background: "linear-gradient(0deg, rgba(15,10,5,0.98) 0%, rgba(15,10,5,0.7) 70%, transparent 100%)",
          }} />
          {/* Left/right curtain panels */}
          <div style={{
            position: "absolute", top: 0, bottom: 0, left: 0,
            width: "9%",
            background: "linear-gradient(90deg, rgba(10,6,3,0.95) 0%, rgba(30,18,10,0.4) 100%)",
          }} />
          <div style={{
            position: "absolute", top: 0, bottom: 0, right: 0,
            width: "9%",
            background: "linear-gradient(270deg, rgba(10,6,3,0.95) 0%, rgba(30,18,10,0.4) 100%)",
          }} />

          {/* ── Interior warmth: ambient amber lamp glow ── */}
          <div style={{
            position: "absolute", bottom: 0, left: 0, right: 0, height: "22%",
            background: `radial-gradient(ellipse 60% 80% at 50% 100%, rgba(255,160,40,${0.06 + 0.02 * Math.sin(frame * 0.04)}) 0%, transparent 100%)`,
          }} />

          {/* ── Rhythmic window vibration (train movement feel) ── */}
          <div style={{
            position: "absolute", inset: 0,
            opacity: 0.018 * Math.abs(Math.sin(frame * 0.52)),
            backgroundColor: "#FFFFEE",
          }} />
        </>
      )}

      {/* Seamless gradient fade for loop */}
      <div style={{
        position: "absolute",
        inset: 0,
        background: `radial-gradient(ellipse 80% 50% at 50% 100%, rgba(0,0,0,0.4) 0%, transparent 60%)`,
        pointerEvents: "none",
      }} />
    </AbsoluteFill>
  );
};
