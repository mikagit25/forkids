/**
 * DanceSpriteShort — animated PNG sprite dancing to beat.
 * Squash-and-stretch, drop shadow, position wander, floating bubbles.
 * Portrait 1080×1920, 55s.
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { ArabicFonts } from "./components/ArabicFonts";

export interface SpriteFrames {
  idle:   string;            // "animals_flux/bear_idle.png" — always required
  smile?: string;            // happy expression
  blink?: string;            // eyes closed
  jump?:  string;            // mid-air / arms up
  wave?:  string;            // waving
}

export interface DanceSpriteShortProps {
  spritePath?: string;       // legacy single image "animals/bear.png"
  spriteFrames?: SpriteFrames; // frame-by-frame animation (preferred)
  characterName: string;
  audioFile?: string | null;
  musicFile: string;
  bgColor: string;
  accentColor: string;
  language?: "en" | "ar";
  customLabel?: string;
}

const BPM = 118;
const N_BUBBLES = 16;

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ── Floating background bubble ─────────────────────────────────────────────
const Bubble: React.FC<{
  seed: number; width: number; height: number; color: string;
}> = ({ seed, width, height, color }) => {
  const frame = useCurrentFrame();
  const r = seededRand;

  const size    = 30 + r(seed * 3) * 90;
  const baseX   = r(seed * 7)  * (width  - size);
  const baseY   = r(seed * 11) * (height - size);
  const speed   = 0.25 + r(seed * 13) * 0.35;
  const opacity = 0.06 + r(seed * 5) * 0.09;

  const x = baseX + Math.sin((frame / 90) * speed + seed)       * 28;
  const y = baseY + Math.cos((frame / 110) * speed + seed * 2)  * 22;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: size,
        height: size,
        borderRadius: "50%",
        backgroundColor: color,
        opacity,
        pointerEvents: "none",
      }}
    />
  );
};

// ── Main component ─────────────────────────────────────────────────────────
// ── Frame selector for frame-by-frame animation ───────────────────────────
function selectFrame(
  frames: SpriteFrames,
  currentFrame: number,
  fps: number,
  bounceNorm: number,
): string {
  // Blink every ~3.5s for 5 frames
  const blinkPeriod = Math.round(fps * 3.5);
  const blinkLen    = 5;
  const inBlink     = (currentFrame % blinkPeriod) < blinkLen;
  if (inBlink && frames.blink) return frames.blink;

  // Jump frame at bounce peak
  if (bounceNorm > 0.70 && frames.jump) return frames.jump;

  // Wave: show for 30 frames every ~5s
  const wavePeriod = Math.round(fps * 5);
  const waveLen    = 30;
  if (frames.wave && (currentFrame % wavePeriod) < waveLen) return frames.wave;

  // Smile: alternate every 2s
  const smilePeriod = Math.round(fps * 2);
  if (frames.smile && Math.floor(currentFrame / smilePeriod) % 2 === 1) return frames.smile;

  return frames.idle;
}

export const DanceSpriteShort: React.FC<DanceSpriteShortProps> = ({
  spritePath,
  spriteFrames,
  characterName,
  audioFile,
  musicFile,
  bgColor,
  accentColor,
  language = "en",
  customLabel,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  const isRtl = language === "ar";
  const label = customLabel ?? characterName;

  // ── Beat-sync bounce ─────────────────────────────────────────────────────
  const beatsPerFrame = BPM / 60 / fps;
  const beatPhase     = frame * beatsPerFrame * Math.PI * 2;

  // bounceNorm: 0 = at ground, 1 = at peak
  const bounceNorm = Math.abs(Math.sin(beatPhase));
  const maxBounce  = 110;                // px
  const bounceY    = bounceNorm * maxBounce;

  // Squash on landing, stretch at peak (volume-preserving)
  const scaleY = 0.83 + 0.32 * bounceNorm;   // 0.83 → 1.15
  const scaleX = 1.18 - 0.28 * bounceNorm;   // 1.18 → 0.90

  // Gentle rock left-right (half speed of bounce)
  const rotation = Math.sin(beatPhase * 0.5) * 9;

  // ── Entrance: spring from below ──────────────────────────────────────────
  const entrance = spring({
    frame,
    fps,
    config: { damping: 11, stiffness: 130, mass: 1 },
    durationInFrames: Math.round(fps * 1.6),
  });
  const entranceY = interpolate(entrance, [0, 1], [height * 0.85, 0]);

  // ── Slow position wander ─────────────────────────────────────────────────
  // Period ~10s horizontal, ~14s vertical drift
  const wanderX = Math.sin((frame / fps) * 0.38) * (width * 0.16);
  const wanderY = Math.cos((frame / fps) * 0.27) * 35;

  const charCenterX = width  / 2 + wanderX;
  const charCenterY = height * 0.46 + wanderY - bounceY + entranceY;

  // Ground level for shadow (stays at resting position)
  const groundCenterY = height * 0.46 + wanderY + entranceY + 26;

  // ── Sprite size ──────────────────────────────────────────────────────────
  const spriteSize = Math.round(Math.min(width * 0.72, height * 0.40));

  // ── Shadow ───────────────────────────────────────────────────────────────
  // Wider + darker at ground, narrow + faint at peak
  const shadowW   = spriteSize * 0.62 * (1.18 - 0.40 * bounceNorm);
  const shadowH   = shadowW * 0.23;
  const shadowOpacity = 0.38 * (1 - bounceNorm * 0.58);

  // ── Label bounce (follows beat, smaller amplitude) ───────────────────────
  const labelBounce = bounceNorm * 7;

  // ── Global fade-out ──────────────────────────────────────────────────────
  const fadeOut = interpolate(
    frame,
    [durationInFrames - fps * 1.5, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, overflow: "hidden" }}>
      {isRtl && <ArabicFonts />}

      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={0.22} loop />
      )}
      {audioFile && [fps * 1, fps * 20, fps * 39].map((start, i) => (
        <Sequence key={i} from={Math.round(start)}>
          <Audio src={staticFile(`audio/${audioFile}`)} />
        </Sequence>
      ))}

      <AbsoluteFill style={{ opacity: fadeOut }}>
        {/* Background floating bubbles */}
        {Array.from({ length: N_BUBBLES }, (_, i) => (
          <Bubble key={i} seed={i + 1} width={width} height={height} color={accentColor} />
        ))}

        {/* Drop shadow (drawn before character so it's underneath) */}
        <div
          style={{
            position: "absolute",
            left: charCenterX - shadowW / 2,
            top: groundCenterY,
            width: shadowW,
            height: shadowH,
            background:
              "radial-gradient(ellipse, rgba(0,0,0,0.55) 0%, transparent 75%)",
            borderRadius: "50%",
            opacity: shadowOpacity,
            pointerEvents: "none",
          }}
        />

        {/* Character sprite with squash-stretch + rotation */}
        <div
          style={{
            position: "absolute",
            left: charCenterX - spriteSize / 2,
            top: charCenterY - spriteSize / 2,
            width: spriteSize,
            height: spriteSize,
            transform: `scaleX(${scaleX}) scaleY(${scaleY}) rotate(${rotation}deg)`,
            transformOrigin: "center bottom",
            pointerEvents: "none",
          }}
        >
          <Img
            src={staticFile(`sprites/${
              spriteFrames
                ? selectFrame(spriteFrames, frame, fps, bounceNorm)
                : spritePath ?? ""
            }`)}
            style={{ width: "100%", height: "100%", objectFit: "contain" }}
          />
        </div>

        {/* Name label — stays at fixed position, bounces slightly */}
        <div
          style={{
            position: "absolute",
            bottom: "11%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            transform: `translateY(${-labelBounce}px)`,
          }}
        >
          <span
            style={{
              fontFamily: isRtl
                ? "'Noto Sans Arabic', 'Noto Kufi Arabic', sans-serif"
                : "'Arial Black', 'Arial Bold', sans-serif",
              fontSize: 114,
              fontWeight: 900,
              color: accentColor,
              WebkitTextStroke: "5px white",
              textShadow: "0 5px 22px rgba(0,0,0,0.16)",
              background: "rgba(255,255,255,0.62)",
              borderRadius: 28,
              padding: "8px 52px",
              direction: isRtl ? "rtl" : "ltr",
            }}
          >
            {label}
          </span>
        </div>

        {/* Channel branding */}
        <div
          style={{
            position: "absolute",
            bottom: "2.5%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            opacity: 0.55,
          }}
        >
          <span
            style={{
              fontFamily: "'Arial', sans-serif",
              fontSize: 44,
              color: "white",
              textShadow: "0 2px 8px rgba(0,0,0,0.35)",
            }}
          >
            Happy Bear Kids
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
