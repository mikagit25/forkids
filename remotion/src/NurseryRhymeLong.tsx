/**
 * NurseryRhymeLong — 20-25 min nursery rhyme video.
 * Character bounces + Arabic lyrics + English subtitles synced to TTS audio.
 * Format: 1920×1080, 30fps.
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

export interface LyricSegment {
  arabic: string;
  english: string;
  startFrame: number;
  durationFrames: number;
  audioFile?: string;         // TTS audio for this segment
  animation?: "bounce" | "swim" | "walk" | "wave" | "idle";
}

export interface NurseryRhymeLongProps {
  segments: LyricSegment[];
  characterSprite: string;    // e.g. "animals_flux/duck.png"
  bgColorTop: string;         // gradient top
  bgColorBottom: string;      // gradient bottom
  accentColor: string;
  musicFile?: string;
  musicVolume?: number;
  titleArabic: string;
  titleEnglish: string;
}

const BPM = 95;

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ── Floating particle (bubbles / raindrops / stars depending on accent) ──────
const Particle: React.FC<{
  seed: number; width: number; height: number; color: string;
}> = ({ seed, width, height, color }) => {
  const frame = useCurrentFrame();
  const r = seededRand;
  const size    = 12 + r(seed * 3) * 28;
  const baseX   = r(seed * 7)  * (width  - size);
  const baseY   = r(seed * 11) * (height - size);
  const speed   = 0.2 + r(seed * 13) * 0.3;
  const opacity = 0.05 + r(seed * 5) * 0.08;
  const x = baseX + Math.sin((frame / 90) * speed + seed) * 20;
  const y = baseY + Math.cos((frame / 110) * speed + seed * 2) * 15;
  return (
    <div style={{
      position: "absolute", left: x, top: y,
      width: size, height: size,
      borderRadius: "50%",
      backgroundColor: color,
      opacity,
      pointerEvents: "none",
    }} />
  );
};

// ── Main ─────────────────────────────────────────────────────────────────────
export const NurseryRhymeLong: React.FC<NurseryRhymeLongProps> = ({
  segments,
  characterSprite,
  bgColorTop,
  bgColorBottom,
  accentColor,
  musicFile,
  musicVolume = 0.18,
  titleArabic,
  titleEnglish,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  // ── Current segment ───────────────────────────────────────────────────────
  const currentSeg = segments.reduce<LyricSegment | null>((found, seg) => {
    if (frame >= seg.startFrame && frame < seg.startFrame + seg.durationFrames) return seg;
    return found;
  }, null);

  const anim = currentSeg?.animation ?? "bounce";

  // ── Beat-sync bounce ─────────────────────────────────────────────────────
  const beatsPerFrame = BPM / 60 / fps;
  const beatPhase     = frame * beatsPerFrame * Math.PI * 2;
  const bounceNorm    = Math.abs(Math.sin(beatPhase));
  const maxBounce     = anim === "swim" ? 30 : 80;
  const bounceY       = bounceNorm * maxBounce;

  const scaleY = 0.88 + 0.22 * bounceNorm;
  const scaleX = 1.12 - 0.18 * bounceNorm;

  // Swim: horizontal sway
  const rotation = anim === "swim"
    ? Math.sin(frame / fps * 1.2) * 15
    : Math.sin(beatPhase * 0.5) * 6;

  // Walk: left-right drift
  const walkX = anim === "walk"
    ? Math.sin(frame / fps * 0.6) * (width * 0.25)
    : Math.sin(frame / fps * 0.25) * (width * 0.08);

  // ── Entrance ─────────────────────────────────────────────────────────────
  const entrance = spring({
    frame, fps,
    config: { damping: 12, stiffness: 120, mass: 1 },
    durationInFrames: Math.round(fps * 1.8),
  });
  const entranceY = interpolate(entrance, [0, 1], [height * 0.5, 0]);

  const spriteSize  = Math.round(Math.min(width * 0.38, height * 0.42));
  const charCenterX = width * 0.5 + walkX;
  const charCenterY = height * 0.42 - bounceY + entranceY;
  const groundY     = height * 0.42 + entranceY + 20;

  // Shadow
  const shadowW = spriteSize * 0.7 * (1.1 - 0.3 * bounceNorm);
  const shadowOpacity = 0.28 * (1 - bounceNorm * 0.5);

  // ── Lyrics: fade in/out ───────────────────────────────────────────────────
  let arabicOpacity = 0;
  let englishOpacity = 0;

  if (currentSeg) {
    const localFrame = frame - currentSeg.startFrame;
    const fadeLen    = Math.round(fps * 0.4);
    arabicOpacity  = interpolate(localFrame, [0, fadeLen], [0, 1], { extrapolateRight: "clamp" });
    englishOpacity = interpolate(localFrame, [0, fadeLen + 6], [0, 1], { extrapolateRight: "clamp" });

    const fadeOutStart = currentSeg.durationFrames - fadeLen;
    if (localFrame > fadeOutStart) {
      arabicOpacity  *= interpolate(localFrame, [fadeOutStart, currentSeg.durationFrames], [1, 0], { extrapolateRight: "clamp" });
      englishOpacity *= interpolate(localFrame, [fadeOutStart, currentSeg.durationFrames], [1, 0], { extrapolateRight: "clamp" });
    }
  }

  // ── Global fade out ───────────────────────────────────────────────────────
  const fadeOut = interpolate(
    frame,
    [durationInFrames - fps * 2, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(180deg, ${bgColorTop} 0%, ${bgColorBottom} 100%)`,
      overflow: "hidden",
    }}>
      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={musicVolume} loop />
      )}

      {/* Per-segment TTS audio */}
      {segments.map((seg, i) =>
        seg.audioFile ? (
          <Sequence key={i} from={seg.startFrame}>
            <Audio src={staticFile(`audio/nursery/${seg.audioFile}`)} />
          </Sequence>
        ) : null
      )}

      <AbsoluteFill style={{ opacity: fadeOut }}>
        {/* Background particles */}
        {Array.from({ length: 12 }, (_, i) => (
          <Particle key={i} seed={i + 1} width={width} height={height} color={accentColor} />
        ))}

        {/* Drop shadow */}
        <div style={{
          position: "absolute",
          left: charCenterX - shadowW / 2,
          top: groundY,
          width: shadowW,
          height: shadowW * 0.2,
          background: "radial-gradient(ellipse, rgba(0,0,0,0.4) 0%, transparent 75%)",
          borderRadius: "50%",
          opacity: shadowOpacity,
        }} />

        {/* Character */}
        <div style={{
          position: "absolute",
          left: charCenterX - spriteSize / 2,
          top: charCenterY - spriteSize / 2,
          width: spriteSize,
          height: spriteSize,
          transform: `scaleX(${scaleX}) scaleY(${scaleY}) rotate(${rotation}deg)`,
          transformOrigin: "center bottom",
        }}>
          <Img
            src={staticFile(`sprites/${characterSprite}`)}
            style={{ width: "100%", height: "100%", objectFit: "contain" }}
          />
        </div>

        {/* Arabic lyrics */}
        {currentSeg?.arabic && (
          <div style={{
            position: "absolute",
            top: "62%",
            left: "5%",
            right: "5%",
            display: "flex",
            justifyContent: "center",
            opacity: arabicOpacity,
          }}>
            <span style={{
              fontFamily: "'Noto Sans Arabic', 'Noto Kufi Arabic', Arial, sans-serif",
              fontSize: 72,
              fontWeight: 700,
              color: "#1a1a1a",
              textShadow: "0 3px 12px rgba(255,255,255,0.9)",
              background: "rgba(255,255,255,0.75)",
              borderRadius: 20,
              padding: "10px 40px",
              direction: "rtl",
              textAlign: "center",
              lineHeight: 1.4,
            }}>
              {currentSeg.arabic}
            </span>
          </div>
        )}

        {/* English subtitle */}
        {currentSeg?.english && (
          <div style={{
            position: "absolute",
            top: "78%",
            left: "5%",
            right: "5%",
            display: "flex",
            justifyContent: "center",
            opacity: englishOpacity,
          }}>
            <span style={{
              fontFamily: "'Arial', sans-serif",
              fontSize: 44,
              fontWeight: 600,
              color: "#333",
              textShadow: "0 2px 8px rgba(255,255,255,0.8)",
              background: "rgba(255,255,255,0.6)",
              borderRadius: 14,
              padding: "6px 30px",
              textAlign: "center",
              lineHeight: 1.3,
            }}>
              {currentSeg.english}
            </span>
          </div>
        )}

        {/* Channel branding */}
        <div style={{
          position: "absolute",
          bottom: "2%",
          left: 0, right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: 0.5,
        }}>
          <span style={{
            fontFamily: "'Arial', sans-serif",
            fontSize: 38,
            color: "white",
            textShadow: "0 2px 8px rgba(0,0,0,0.4)",
          }}>
            Happy Bear Kids
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
