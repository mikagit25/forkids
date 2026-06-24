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

export interface VocabularyShortProps {
  letter: string;
  word: string;
  spritePath: string | null;
  audioFile: string;
  letterColor: string;
  bgColor: string;
  musicFile?: string;
}

// Spring-based scale animation
function useSpringScale(frame: number, fps: number, delay = 0, damping = 12) {
  return spring({ frame: frame - delay, fps, config: { damping, stiffness: 120, mass: 1 } });
}

export const VocabularyShort: React.FC<VocabularyShortProps> = ({
  letter,
  word,
  spritePath,
  audioFile,
  letterColor,
  bgColor,
  musicFile,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Phase timing (55s total at 30fps = 1650 frames)
  const phase1End = Math.round(fps * 18);   // 0–18s: letter intro
  const phase2End = Math.round(fps * 36);   // 18–36s: tagline + repeat
  // phase 3: 36–55s: celebration

  // ── Letter drop-in ──────────────────────────────────────────────────────────
  const letterDropProgress = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 180, mass: 1 },
    durationInFrames: Math.round(fps * 1.2),
  });
  const letterY = interpolate(letterDropProgress, [0, 1], [-700, 0]);

  // Letter pulse at t≈1s
  const letterPulse = spring({
    frame: frame - Math.round(fps * 1.2),
    fps,
    config: { damping: 8, stiffness: 200, mass: 0.8 },
    durationInFrames: Math.round(fps * 0.9),
  });
  const letterPulseScale = interpolate(
    Math.min(letterPulse, 1),
    [0, 0.5, 1],
    [1, 1.3, 1]
  );

  // ── Sprite slide-in from right ───────────────────────────────────────────────
  const spriteSlide = spring({
    frame: frame - Math.round(fps * 1.8),
    fps,
    config: { damping: 12, stiffness: 160, mass: 1 },
    durationInFrames: Math.round(fps * 0.9),
  });
  const spriteX = interpolate(spriteSlide, [0, 1], [400, 0]);

  // ── Word write-in ─────────────────────────────────────────────────────────────
  const wordReveal = spring({
    frame: frame - Math.round(fps * 4),
    fps,
    config: { damping: 10, stiffness: 150 },
    durationInFrames: Math.round(fps * 1.4),
  });
  const wordOpacity = Math.min(wordReveal, 1);
  const wordScale = interpolate(wordReveal, [0, 1], [0.4, 1], {
    extrapolateRight: "clamp",
  });

  // ── Tagline fade-in at phase2 ─────────────────────────────────────────────────
  const taglineOpacity = interpolate(frame, [phase1End, phase1End + Math.round(fps * 0.8)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ── Phase 3: word bounce (celebration) ──────────────────────────────────────
  const bounceFrame = frame - phase2End;
  const bounce = bounceFrame > 0
    ? Math.sin((bounceFrame / fps) * Math.PI * 4) * 12
    : 0;

  // ── Continuous idle animations (apply at all times) ───────────────────────
  const fSec = frame / fps;
  const letterBreathe = 1 + Math.sin(fSec * 1.4) * 0.04;   // gentle scale pulse
  const spriteFloat   = Math.sin(fSec * 1.8) * 18;          // up-down float
  const spriteRock    = Math.sin(fSec * 2.1) * 4;            // slight rotation
  const wordBreathe   = 1 + Math.sin(fSec * 2.0 + 1) * 0.03;

  // Background floating orbs
  const orbs = [
    { x: 15, y: 10, r: 120, phase: 0 },
    { x: 80, y: 25, r: 90,  phase: 1.5 },
    { x: 10, y: 60, r: 100, phase: 2.8 },
    { x: 75, y: 70, r: 80,  phase: 0.8 },
    { x: 45, y: 88, r: 110, phase: 2.0 },
  ];

  // Final fade-out (last 1.5s)
  const fadeOutOpacity = interpolate(
    frame,
    [durationInFrames - Math.round(fps * 1.5), durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // ── Layout constants (portrait 1080×1920) ─────────────────────────────────────
  const centerX = "50%";

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, overflow: "hidden" }}>
      {/* Background floating orbs — always in motion */}
      {orbs.map((o, i) => (
        <div key={i} style={{
          position: "absolute",
          left: `${o.x}%`, top: `${o.y + Math.sin(fSec * 0.7 + o.phase) * 4}%`,
          width: o.r * 2, height: o.r * 2,
          borderRadius: "50%",
          backgroundColor: letterColor,
          opacity: 0.06 + Math.sin(fSec * 0.9 + o.phase) * 0.02,
          transform: `scale(${1 + Math.sin(fSec * 0.5 + o.phase) * 0.08})`,
        }} />
      ))}

      {/* Background music (optional) */}
      {musicFile && <Audio src={staticFile(`music/${musicFile}`)} volume={0.13} loop />}

      {/* Audio: voiceover plays 3× at t=1s, 19s, 37.5s */}
      <Sequence from={Math.round(fps * 1)}>
        <Audio src={staticFile(`audio/${audioFile}`)} />
      </Sequence>
      <Sequence from={Math.round(fps * 19)}>
        <Audio src={staticFile(`audio/${audioFile}`)} />
      </Sequence>
      <Sequence from={Math.round(fps * 37.5)}>
        <Audio src={staticFile(`audio/${audioFile}`)} />
      </Sequence>

      <AbsoluteFill style={{ opacity: fadeOutOpacity }}>
        {/* ── Big letter (top area) ──────────────────────────────────────────── */}
        <div
          style={{
            position: "absolute",
            top: "5%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            transform: `translateY(${letterY}px) scale(${letterPulseScale * letterBreathe})`,
          }}
        >
          <span
            style={{
              fontFamily: "'Arial Black', 'Arial Bold', sans-serif",
              fontSize: 420,
              fontWeight: 900,
              color: letterColor,
              WebkitTextStroke: `12px white`,
              textShadow: `0 12px 32px rgba(0,0,0,0.22)`,
              lineHeight: 1,
            }}
          >
            {letter}
          </span>
        </div>

        {/* ── Sprite (center) ───────────────────────────────────────────────── */}
        <div
          style={{
            position: "absolute",
            top: "33%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            transform: `translateX(${spriteX}px) translateY(${spriteFloat}px) rotate(${spriteRock}deg)`,
          }}
        >
          {spritePath ? (
            <Img
              src={staticFile(`sprites/${spritePath}`)}
              style={{ width: 520, height: 520, objectFit: "contain" }}
            />
          ) : (
            // Fallback star shape
            <div
              style={{
                width: 460,
                height: 460,
                backgroundColor: letterColor,
                clipPath: "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)",
                opacity: 0.85,
              }}
            />
          )}
        </div>

        {/* ── Word label ───────────────────────────────────────────────────── */}
        <div
          style={{
            position: "absolute",
            top: "63%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            opacity: wordOpacity,
            transform: `scale(${wordScale * wordBreathe}) translateY(${bounce}px)`,
          }}
        >
          <span
            style={{
              fontFamily: "'Arial Black', 'Arial Bold', sans-serif",
              fontSize: 150,
              fontWeight: 900,
              color: letterColor,
              WebkitTextStroke: "5px white",
              textShadow: "0 6px 20px rgba(0,0,0,0.18)",
              letterSpacing: 6,
            }}
          >
            {word}
          </span>
        </div>

        {/* ── Tagline ───────────────────────────────────────────────────────── */}
        <div
          style={{
            position: "absolute",
            top: "77%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            opacity: taglineOpacity,
          }}
        >
          <span
            style={{
              fontFamily: "'Arial', sans-serif",
              fontSize: 88,
              fontWeight: 700,
              color: "white",
              WebkitTextStroke: `4px ${letterColor}`,
              textShadow: `0 4px 16px rgba(0,0,0,0.22)`,
              textAlign: "center",
              padding: "0 40px",
            }}
          >
            {letter} is for {word.charAt(0) + word.slice(1).toLowerCase()}
          </span>
        </div>

        {/* ── Channel branding (bottom) ─────────────────────────────────────── */}
        <div
          style={{
            position: "absolute",
            bottom: "2.5%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            opacity: 0.65,
          }}
        >
          <span
            style={{
              fontFamily: "'Arial', sans-serif",
              fontSize: 52,
              fontWeight: 600,
              color: "white",
              textShadow: `0 2px 8px rgba(0,0,0,0.35)`,
            }}
          >
            Happy Bear Kids
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
