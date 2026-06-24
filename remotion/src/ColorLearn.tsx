/**
 * ColorLearn — one color per video segment.
 * Big colored circle + fruit character in center, supporting fruits float in.
 *
 * Structure (55s):
 *  0–8s   : Big circle pulses + main fruit character appears on top
 *  8–20s  : Supporting fruit sprites float in around the main fruit
 *  20–36s : Everything bounces to beat, color name prominent
 *  36–55s : Review + fade
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
import { Shape, ShapeName } from "./components/Shape";
import { ArabicFonts } from "./components/ArabicFonts";

export interface ColorLearnProps {
  colorName: string;          // "RED" or "أحمر"
  colorHex: string;           // "#FF4444"
  bgColor: string;            // light complementary bg
  audioFile: string;          // voiceover mp3
  musicFile?: string | null;
  taglineText?: string;       // override "Can you find...?" line
  rtl?: boolean;              // Arabic RTL layout
  fruitSprites?: string[];    // sprite paths relative to public/sprites/ (optional)
}

// Fallback: four shapes when no fruit sprites provided
const DEMO_SHAPES: ShapeName[] = ["circle", "square", "triangle", "star"];

const SIDE_POSITIONS = [
  { x: "4%",  y: "56%" },
  { x: "66%", y: "52%" },
  { x: "4%",  y: "74%" },
  { x: "66%", y: "72%" },
];

// ── Floating fruit sprite ────────────────────────────────────────────────────
interface FloatingFruitProps {
  spritePath: string;
  posX: string;
  posY: string;
  size: number;
  entryFrame: number;
  bouncePhase: number;
  fromLeft?: boolean;
}

const FloatingFruit: React.FC<FloatingFruitProps> = ({
  spritePath, posX, posY, size, entryFrame, bouncePhase, fromLeft = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - entryFrame,
    fps,
    config: { damping: 10, stiffness: 120 },
    durationInFrames: Math.round(fps * 1.4),
  });

  const slideIn  = interpolate(entrance, [0, 1], [fromLeft ? -280 : 280, 0]);
  const opacity  = Math.min(entrance * 2, 1);
  const bounce   = frame > entryFrame + fps
    ? Math.sin((frame / fps + bouncePhase) * 1.6) * 12
    : 0;

  return (
    <div style={{
      position: "absolute",
      left: posX,
      top: posY,
      transform: `translateX(${slideIn}px) translateY(${bounce}px)`,
      opacity,
    }}>
      <Img
        src={staticFile(`sprites/${spritePath}`)}
        style={{ width: size, height: size, objectFit: "contain" }}
      />
    </div>
  );
};

// ── Fallback: floating geometric shape (kept for backward compat) ─────────────
interface FloatingShapeProps {
  shapeName: ShapeName;
  color: string;
  posX: string;
  posY: string;
  entryFrame: number;
  bouncePhase: number;
}

const FloatingShape: React.FC<FloatingShapeProps> = ({
  shapeName, color, posX, posY, entryFrame, bouncePhase,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const entrance = spring({
    frame: frame - entryFrame,
    fps,
    config: { damping: 10, stiffness: 130 },
    durationInFrames: Math.round(fps * 1.2),
  });

  const entryOffset = interpolate(entrance, [0, 1], [300, 0]);
  const opacity     = Math.min(entrance * 2, 1);
  const bounce      = frame > entryFrame + fps
    ? Math.sin((frame / fps + bouncePhase) * 1.8) * 14
    : 0;

  return (
    <div style={{
      position: "absolute",
      left: posX,
      top: posY,
      transform: `translateY(${entryOffset + bounce}px)`,
      opacity,
    }}>
      <Shape name={shapeName} size={160} color={color} />
    </div>
  );
};

export const ColorLearn: React.FC<ColorLearnProps> = ({
  colorName, colorHex, bgColor, audioFile, musicFile,
  taglineText, rtl = false, fruitSprites = [],
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const useFruits = fruitSprites.length > 0;
  const mainFruit = fruitSprites[0] ?? null;
  const sideFruits = fruitSprites.slice(1, 5); // up to 4 side fruits

  // Main circle: pulses and scales
  const circleEntrance = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 140 },
    durationInFrames: Math.round(fps * 1.2),
  });
  const circleScale = interpolate(circleEntrance, [0, 1], [0.2, 1], {
    extrapolateRight: "clamp",
  });

  // Beat pulse
  const beatFreq = 100 / 60;
  const beatPulse = 1 + Math.abs(Math.sin(frame / fps * beatFreq * Math.PI)) * 0.08;

  // Main fruit: enters with a bounce-in from top (delayed 0.3s after circle)
  const fruitEntrance = spring({
    frame: frame - Math.round(fps * 0.3),
    fps,
    config: { damping: 8, stiffness: 110 },
    durationInFrames: Math.round(fps * 1.5),
  });
  const fruitScale   = interpolate(fruitEntrance, [0, 1], [0, 1], { extrapolateRight: "clamp" });
  const fruitBounce  = Math.abs(Math.sin(frame / fps * beatFreq * Math.PI)) * 18;

  // Color name text entrance
  const nameEntrance = spring({
    frame: frame - Math.round(fps * 0.8),
    fps,
    config: { damping: 10, stiffness: 120 },
    durationInFrames: Math.round(fps),
  });
  const nameScale   = interpolate(nameEntrance, [0, 1], [0.3, 1], { extrapolateRight: "clamp" });
  const nameOpacity = Math.min(nameEntrance, 1);

  // Side items appear one by one from 8s
  const sideCount      = useFruits ? sideFruits.length : DEMO_SHAPES.length;
  const sideEntryFrames = Array.from({ length: sideCount }, (_, i) =>
    Math.round(fps * (8 + i * 2.5))
  );

  // Tagline at 20s
  const tagOpacity = interpolate(frame, [fps * 20, fps * 21], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Overall fade-out
  const fadeOut = interpolate(
    frame,
    [durationInFrames - fps * 1.5, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, overflow: "hidden" }}>
      <ArabicFonts />
      <Sequence from={Math.round(fps * 1)}>
        <Audio src={staticFile(`audio/${audioFile}`)} />
      </Sequence>
      <Sequence from={Math.round(fps * 20)}>
        <Audio src={staticFile(`audio/${audioFile}`)} />
      </Sequence>
      <Sequence from={Math.round(fps * 39)}>
        <Audio src={staticFile(`audio/${audioFile}`)} />
      </Sequence>
      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={0.15} loop />
      )}

      <AbsoluteFill style={{ opacity: fadeOut }}>
        {/* ── Big central circle (glow behind fruit) ──────────────────────── */}
        <div style={{
          position: "absolute",
          top: "10%",
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          transform: `scale(${circleScale * beatPulse})`,
        }}>
          <div style={{
            width: 420,
            height: 420,
            borderRadius: "50%",
            backgroundColor: colorHex,
            boxShadow: `0 16px 60px ${colorHex}88`,
          }} />
        </div>

        {/* ── Main fruit character centered on circle ──────────────────────── */}
        {useFruits && mainFruit && (
          <div style={{
            position: "absolute",
            top: "8%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            transform: `scale(${fruitScale}) translateY(${-fruitBounce}px)`,
            transformOrigin: "center center",
          }}>
            <Img
              src={staticFile(`sprites/${mainFruit}`)}
              style={{ width: 460, height: 460, objectFit: "contain" }}
            />
          </div>
        )}

        {/* ── Color name ──────────────────────────────────────────────────── */}
        <div style={{
          position: "absolute",
          top: "47%",
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: nameOpacity,
          transform: `scale(${nameScale * (1 + Math.abs(Math.sin(frame / fps * beatFreq * Math.PI)) * 0.07)})`,
        }}>
          <span style={{
            fontFamily: rtl
              ? "'Noto Sans Arabic', 'Noto Kufi Arabic', sans-serif"
              : "'Arial Black', sans-serif",
            fontSize: 180,
            fontWeight: 900,
            color: colorHex,
            WebkitTextStroke: "8px white",
            textShadow: "0 8px 28px rgba(0,0,0,0.18)",
            letterSpacing: rtl ? 0 : 8,
          }}>
            {colorName}
          </span>
        </div>

        {/* ── Side fruits (or fallback shapes) ────────────────────────────── */}
        {useFruits
          ? sideFruits.map((sprite, i) => (
            <FloatingFruit
              key={i}
              spritePath={sprite}
              posX={SIDE_POSITIONS[i % SIDE_POSITIONS.length].x}
              posY={SIDE_POSITIONS[i % SIDE_POSITIONS.length].y}
              size={240}
              entryFrame={sideEntryFrames[i]}
              bouncePhase={i * 0.9}
              fromLeft={i % 2 === 0}
            />
          ))
          : DEMO_SHAPES.map((shape, i) => (
            <FloatingShape
              key={i}
              shapeName={shape}
              color={colorHex}
              posX={SIDE_POSITIONS[i].x}
              posY={SIDE_POSITIONS[i].y}
              entryFrame={sideEntryFrames[i]}
              bouncePhase={i * 0.8}
            />
          ))
        }

        {/* ── Tagline ──────────────────────────────────────────────────────── */}
        <div
          style={{
            position: "absolute",
            bottom: "12%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            opacity: tagOpacity,
            padding: "0 40px",
          }}
        >
          <span
            style={{
              fontFamily: rtl
                ? "'Noto Sans Arabic', 'Noto Kufi Arabic', sans-serif"
                : "'Arial', sans-serif",
              direction: rtl ? "rtl" : "ltr",
              fontSize: 68,
              fontWeight: 700,
              color: "white",
              WebkitTextStroke: `3px ${colorHex}`,
              textShadow: "0 4px 16px rgba(0,0,0,0.2)",
              textAlign: "center",
            }}
          >
            {taglineText ?? `Can you find something ${colorName.charAt(0) + colorName.slice(1).toLowerCase()}?`}
          </span>
        </div>

        {/* ── Channel brand ─────────────────────────────────────────────────── */}
        <div
          style={{
            position: "absolute",
            bottom: "2%",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            opacity: 0.5,
          }}
        >
          <span style={{
            fontFamily: "'Arial', sans-serif",
            fontSize: 42,
            color: "white",
            textShadow: "0 2px 8px rgba(0,0,0,0.3)",
          }}>
            Happy Bear Kids
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
