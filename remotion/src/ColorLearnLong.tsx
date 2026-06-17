/**
 * ColorLearnLong — 20-minute "One Concept Deep" color learning video.
 * 1920×1080 landscape.
 *
 * Structure per segment (45s each):
 *   0–8s   : Object enters with name label
 *   8–13s  : Question appears ("What color is the X?")
 *   13–17s : Wait / think time (sparkle animation)
 *   17–23s : Answer reveal + confetti ("It's COLOR!")
 *   23–38s : Happy bounce, color name pulses, name label
 *   38–45s : Fade to next
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

export interface ColorLearnLongObject {
  name: string;           // "strawberry"
  nameLocalized: string;  // "Strawberry" or "فراولة"
  spritePath: string;     // relative to public/sprites/
}

export interface ColorLearnLongProps {
  colorName: string;      // "RED" or "أحمر"
  colorHex: string;       // "#E53935"
  bgColor: string;        // "#FFF5F5"
  rtl: boolean;
  objects: [ColorLearnLongObject, ColorLearnLongObject, ColorLearnLongObject];
  // Audio paths relative to public/audio/color_learn/{lang}/
  lang: "en" | "ar" | "id";
  colorKey: string;       // "red"
  musicFile: string;      // from public/music/
}

const FPS = 30;

// Section start times (seconds)
const T_INTRO        = 0;
const T_INTRO_LEN    = 25;
const T_SCENE1       = T_INTRO_LEN;          // 25s
const T_SCENE2       = T_SCENE1 + 4 * 60;    // 25 + 240 = 265s
const T_SCENE3       = T_SCENE2 + 4 * 60;    // 505s
const T_SONG         = T_SCENE3 + 4 * 60;    // 745s
const T_SONG_LEN     = 75;
const T_REVIEW       = T_SONG + T_SONG_LEN;  // 820s
const T_REVIEW_LEN   = 320;
const T_OUTRO        = T_REVIEW + T_REVIEW_LEN; // 1140s

// One 45s dialogue cycle — returns frame-relative value
const CYCLE = 45;

// ── Confetti particle ─────────────────────────────────────────────────────────
const CONFETTI_COLORS = ["#FF4444","#FFD700","#4CAF50","#2196F3","#E91E8C","#FF9800"];

const ConfettiParticle: React.FC<{
  x: number; y: number; size: number; color: string;
  frame: number; startFrame: number;
}> = ({ x, y, size, color, frame, startFrame }) => {
  const f = frame - startFrame;
  if (f < 0) return null;
  const fall  = f * 4;
  const sway  = Math.sin(f * 0.15 + x) * 30;
  const alpha = interpolate(f, [0, 20, 90], [0, 1, 0], { extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", left: x, top: y + fall, width: size, height: size,
      backgroundColor: color, borderRadius: 2, opacity: alpha,
      transform: `translateX(${sway}px) rotate(${f * 5}deg)`,
    }} />
  );
};

// ── Sparkle think animation ───────────────────────────────────────────────────
const ThinkSparkle: React.FC<{ frame: number; startFrame: number; endFrame: number }> = ({
  frame, startFrame, endFrame,
}) => {
  const f = frame - startFrame;
  if (f < 0 || frame > endFrame) return null;
  const dots = [".", "..", "..."];
  const dot = dots[Math.floor(f / 15) % 3];
  return (
    <div style={{
      position: "absolute", bottom: "22%", left: 0, right: 0,
      display: "flex", justifyContent: "center",
    }}>
      <span style={{ fontSize: 80, color: "#FFF", opacity: 0.6 }}>{dot}</span>
    </div>
  );
};

// ── One object scene ──────────────────────────────────────────────────────────
interface ObjectSceneProps {
  frame: number;
  fps: number;
  globalStart: number;  // frame when this scene starts
  obj: ColorLearnLongObject;
  colorName: string;
  colorHex: string;
  bgColor: string;
  rtl: boolean;
  cycleIndex: number;   // which repetition (0-3)
}

const ObjectScene: React.FC<ObjectSceneProps> = ({
  frame, fps, globalStart, obj, colorName, colorHex, bgColor, rtl, cycleIndex,
}) => {
  const cycleStart = globalStart + cycleIndex * CYCLE * fps;
  const f = frame - cycleStart;
  if (f < 0 || f >= CYCLE * fps) return null;

  const fSec = f / fps;

  // Object entrance spring
  const objSpring = spring({ frame: f, fps, config: { damping: 10, stiffness: 100 }, durationInFrames: fps * 1.5 });
  const objY      = interpolate(objSpring, [0, 1], [-600, 0], { extrapolateRight: "clamp" });
  const objScale  = interpolate(objSpring, [0, 1], [0.3, 1], { extrapolateRight: "clamp" });

  // Happy bounce (after 17s)
  const bounceStart = fps * 17;
  const happyBounce = fSec > 17
    ? Math.abs(Math.sin((fSec - 17) * 2.5)) * 30
    : 0;

  // Question: 8–13s
  const qOpacity = interpolate(f, [fps * 8, fps * 9, fps * 13, fps * 14], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Answer: 17–38s
  const aOpacity = interpolate(f, [fps * 17, fps * 18], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const aScale   = interpolate(
    spring({ frame: f - fps * 17, fps, config: { damping: 8, stiffness: 150 }, durationInFrames: fps }),
    [0, 1], [0.3, 1], { extrapolateRight: "clamp" }
  );

  // Fade out last 3s
  const fadeOut = interpolate(f, [fps * (CYCLE - 3), fps * CYCLE], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const font = rtl ? "'Noto Sans Arabic','Noto Kufi Arabic',sans-serif" : "'Arial Black',sans-serif";

  const questionText = rtl
    ? `ما لون ${obj.nameLocalized}؟`
    : `What color is the ${obj.name}?`;
  const answerText = rtl
    ? `${colorName}!`
    : `${colorName}!`;
  const nameText = obj.nameLocalized;

  // Confetti particles
  const confettiParticles = Array.from({ length: 18 }, (_, i) => ({
    x: 100 + i * 100, y: 50,
    size: 10 + (i % 4) * 6,
    color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
  }));

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      {/* Background circle hint */}
      <div style={{
        position: "absolute", top: "50%", left: "50%",
        transform: "translate(-50%, -60%)",
        width: 480, height: 480, borderRadius: "50%",
        backgroundColor: colorHex, opacity: 0.12,
      }} />

      {/* Main sprite */}
      <div style={{
        position: "absolute", left: 0, right: 0, top: "8%",
        display: "flex", justifyContent: "center",
        transform: `translateY(${objY + happyBounce}px) scale(${objScale})`,
      }}>
        <Img
          src={staticFile(`sprites/${obj.spritePath}`)}
          style={{ width: 480, height: 480, objectFit: "contain" }}
        />
      </div>

      {/* Object name label */}
      <div style={{
        position: "absolute", top: "56%", left: 0, right: 0,
        display: "flex", justifyContent: "center",
        opacity: Math.min(objSpring, 1),
        direction: rtl ? "rtl" : "ltr",
      }}>
        <div style={{
          backgroundColor: colorHex, borderRadius: 20, padding: "12px 40px",
        }}>
          <span style={{
            fontFamily: font, fontSize: 72, fontWeight: 900,
            color: "white", textShadow: "0 4px 12px rgba(0,0,0,0.3)",
          }}>
            {nameText}
          </span>
        </div>
      </div>

      {/* Question */}
      <div style={{
        position: "absolute", bottom: "20%", left: 0, right: 0,
        display: "flex", justifyContent: "center", opacity: qOpacity,
        direction: rtl ? "rtl" : "ltr",
      }}>
        <span style={{
          fontFamily: font, fontSize: 60, fontWeight: 700, color: "#333",
          textShadow: "0 2px 8px rgba(0,0,0,0.15)", textAlign: "center",
          padding: "0 60px",
        }}>
          {questionText}
        </span>
      </div>

      {/* Think dots */}
      <ThinkSparkle frame={f} startFrame={fps * 13} endFrame={fps * 17} />

      {/* Answer reveal */}
      <div style={{
        position: "absolute", bottom: "20%", left: 0, right: 0,
        display: "flex", justifyContent: "center",
        opacity: aOpacity, transform: `scale(${aScale})`,
      }}>
        <span style={{
          fontFamily: font, fontSize: 120, fontWeight: 900,
          color: colorHex, WebkitTextStroke: "6px white",
          textShadow: "0 6px 24px rgba(0,0,0,0.2)",
        }}>
          {answerText}
        </span>
      </div>

      {/* Confetti */}
      {fSec > 17 && fSec < 30 && confettiParticles.map((p, i) => (
        <ConfettiParticle key={i} {...p} frame={f} startFrame={fps * 17} />
      ))}
    </AbsoluteFill>
  );
};

// ── Song section ──────────────────────────────────────────────────────────────
const SongSection: React.FC<{
  frame: number; fps: number; globalStart: number;
  objects: ColorLearnLongObject[]; colorName: string; colorHex: string; rtl: boolean;
}> = ({ frame, fps, globalStart, objects, colorName, colorHex, rtl }) => {
  const f = frame - globalStart;
  if (f < 0 || f >= T_SONG_LEN * fps) return null;

  const fSec = f / fps;
  const beatFreq = 120 / 60;
  const beat = 1 + Math.abs(Math.sin(fSec * beatFreq * Math.PI)) * 0.12;

  const font = rtl ? "'Noto Sans Arabic','Noto Kufi Arabic',sans-serif" : "'Arial Black',sans-serif";

  // Cycle through objects
  const objIdx = Math.floor(fSec / (T_SONG_LEN / 3)) % 3;
  const obj    = objects[objIdx];

  const objEntrance = spring({
    frame: f - Math.floor(fSec / (T_SONG_LEN / 3)) * fps * (T_SONG_LEN / 3),
    fps, config: { damping: 12, stiffness: 100 }, durationInFrames: fps * 1.2,
  });
  const bounce = Math.abs(Math.sin(fSec * 2.2)) * 25;

  return (
    <AbsoluteFill>
      {/* Color name big */}
      <div style={{
        position: "absolute", top: "5%", left: 0, right: 0,
        display: "flex", justifyContent: "center",
        transform: `scale(${beat})`,
      }}>
        <span style={{
          fontFamily: font, fontSize: 180, fontWeight: 900,
          color: colorHex, WebkitTextStroke: "8px white",
          textShadow: "0 8px 28px rgba(0,0,0,0.18)",
          direction: rtl ? "rtl" : "ltr",
        }}>
          {colorName}
        </span>
      </div>

      {/* Bouncing object */}
      <div style={{
        position: "absolute", left: 0, right: 0, top: "25%",
        display: "flex", justifyContent: "center",
        transform: `scale(${interpolate(objEntrance, [0, 1], [0.3, 1])}) translateY(${-bounce}px)`,
      }}>
        <Img
          src={staticFile(`sprites/${obj.spritePath}`)}
          style={{ width: 420, height: 420, objectFit: "contain" }}
        />
      </div>

      {/* Object name */}
      <div style={{
        position: "absolute", bottom: "12%", left: 0, right: 0,
        display: "flex", justifyContent: "center",
        direction: rtl ? "rtl" : "ltr",
      }}>
        <span style={{
          fontFamily: font, fontSize: 80, fontWeight: 900,
          color: "white", WebkitTextStroke: `4px ${colorHex}`,
        }}>
          {obj.nameLocalized}
        </span>
      </div>
    </AbsoluteFill>
  );
};

// ── Review section ────────────────────────────────────────────────────────────
const ReviewSection: React.FC<{
  frame: number; fps: number; globalStart: number;
  objects: ColorLearnLongObject[]; colorName: string; colorHex: string; rtl: boolean;
}> = ({ frame, fps, globalStart, objects, colorName, colorHex, rtl }) => {
  const f = frame - globalStart;
  if (f < 0 || f >= T_REVIEW_LEN * fps) return null;

  const fSec     = f / fps;
  const slotLen  = T_REVIEW_LEN / 8;  // 8 review passes
  const pass     = Math.floor(fSec / slotLen);
  const objIdx   = pass % 3;
  const obj      = objects[objIdx];
  const localF   = (fSec % slotLen) / slotLen;

  const font = rtl ? "'Noto Sans Arabic','Noto Kufi Arabic',sans-serif" : "'Arial Black',sans-serif";

  const scale = 0.7 + Math.abs(Math.sin(fSec * 1.8)) * 0.15;
  const anim  = spring({
    frame: f - pass * Math.round(slotLen * fps),
    fps, config: { damping: 12, stiffness: 130 }, durationInFrames: fps,
  });

  const label = rtl
    ? `${obj.nameLocalized} — ${colorName}!`
    : `${obj.nameLocalized} is ${colorName}!`;

  return (
    <AbsoluteFill>
      {/* Big color circle bg */}
      <div style={{
        position: "absolute", top: "50%", left: "50%",
        transform: "translate(-50%, -55%)",
        width: 500, height: 500, borderRadius: "50%",
        backgroundColor: colorHex, opacity: 0.15,
      }} />

      <div style={{
        position: "absolute", left: 0, right: 0, top: "12%",
        display: "flex", justifyContent: "center",
        transform: `scale(${interpolate(anim, [0, 1], [0.5, scale])})`,
      }}>
        <Img
          src={staticFile(`sprites/${obj.spritePath}`)}
          style={{ width: 440, height: 440, objectFit: "contain" }}
        />
      </div>

      <div style={{
        position: "absolute", bottom: "18%", left: 0, right: 0,
        display: "flex", justifyContent: "center",
        direction: rtl ? "rtl" : "ltr",
      }}>
        <div style={{
          backgroundColor: colorHex, borderRadius: 20, padding: "14px 48px",
        }}>
          <span style={{
            fontFamily: font, fontSize: 70, fontWeight: 900, color: "white",
            textShadow: "0 4px 12px rgba(0,0,0,0.25)",
          }}>
            {label}
          </span>
        </div>
      </div>

      {/* Color name pulsing */}
      <div style={{
        position: "absolute", top: "5%", left: 0, right: 0,
        display: "flex", justifyContent: "center",
      }}>
        <span style={{
          fontFamily: font, fontSize: 120, fontWeight: 900,
          color: colorHex, WebkitTextStroke: "6px white",
          opacity: 0.85, direction: rtl ? "rtl" : "ltr",
        }}>
          {colorName}
        </span>
      </div>
    </AbsoluteFill>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────
export const ColorLearnLong: React.FC<ColorLearnLongProps> = ({
  colorName, colorHex, bgColor, rtl, objects, lang, colorKey, musicFile,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const f    = frame;
  const fSec = f / fps;
  const font = rtl ? "'Noto Sans Arabic','Noto Kufi Arabic',sans-serif" : "'Arial Black',sans-serif";

  const audioBase = `audio/color_learn/${lang}/${colorKey}`;

  // Intro pulse
  const introSpring = spring({ frame: f, fps, config: { damping: 10, stiffness: 100 }, durationInFrames: fps * 1.5 });
  const introScale  = interpolate(introSpring, [0, 1], [0.2, 1], { extrapolateRight: "clamp" });
  const introOpacity = interpolate(f, [fps * T_INTRO_LEN - fps * 2, fps * T_INTRO_LEN], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Overall fade out
  const fadeOut = interpolate(
    f, [durationInFrames - fps * 2, durationInFrames], [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, overflow: "hidden" }}>
      <ArabicFonts />

      {/* Background music */}
      <Audio src={staticFile(`music/${musicFile}`)} volume={0.12} loop />

      {/* Audio: intro */}
      <Audio src={staticFile(`${audioBase}_intro.mp3`)} />
      {/* Audio: obj1 — plays once per cycle (4 times) */}
      {[0, 1, 2, 3].map((i) => (
        <Sequence key={`a1_${i}`} from={fps * T_SCENE1 + i * CYCLE * fps}>
          <Audio src={staticFile(`${audioBase}_obj1.mp3`)} />
        </Sequence>
      ))}
      {/* Audio: obj2 */}
      {[0, 1, 2, 3].map((i) => (
        <Sequence key={`a2_${i}`} from={fps * T_SCENE2 + i * CYCLE * fps}>
          <Audio src={staticFile(`${audioBase}_obj2.mp3`)} />
        </Sequence>
      ))}
      {/* Audio: obj3 */}
      {[0, 1, 2, 3].map((i) => (
        <Sequence key={`a3_${i}`} from={fps * T_SCENE3 + i * CYCLE * fps}>
          <Audio src={staticFile(`${audioBase}_obj3.mp3`)} />
        </Sequence>
      ))}
      {/* Audio: song */}
      <Sequence from={fps * T_SONG}>
        <Audio src={staticFile(`${audioBase}_song.mp3`)} />
      </Sequence>
      {/* Audio: review — loops twice to cover 320s */}
      <Sequence from={fps * T_REVIEW}>
        <Audio src={staticFile(`${audioBase}_review.mp3`)} />
      </Sequence>
      <Sequence from={fps * (T_REVIEW + 160)}>
        <Audio src={staticFile(`${audioBase}_review.mp3`)} />
      </Sequence>
      {/* Audio: outro */}
      <Sequence from={fps * T_OUTRO}>
        <Audio src={staticFile(`${audioBase}_outro.mp3`)} />
      </Sequence>

      <AbsoluteFill style={{ opacity: fadeOut }}>

        {/* ── INTRO (0–25s) ──────────────────────────────────────────────── */}
        {fSec < T_INTRO_LEN && (
          <AbsoluteFill style={{ opacity: introOpacity }}>
            {/* Big color circle */}
            <div style={{
              position: "absolute", top: "50%", left: "50%",
              transform: `translate(-50%, -55%) scale(${introScale})`,
              width: 600, height: 600, borderRadius: "50%",
              backgroundColor: colorHex,
              boxShadow: `0 20px 80px ${colorHex}66`,
            }} />
            {/* Color name */}
            <div style={{
              position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              transform: `scale(${introScale})`,
              direction: rtl ? "rtl" : "ltr",
            }}>
              <span style={{
                fontFamily: font, fontSize: 220, fontWeight: 900,
                color: "white", WebkitTextStroke: "10px rgba(0,0,0,0.15)",
                textShadow: "0 10px 40px rgba(0,0,0,0.2)",
              }}>
                {colorName}
              </span>
            </div>
          </AbsoluteFill>
        )}

        {/* ── OBJECT SCENES ─────────────────────────────────────────────── */}
        {/* Scene 1: 4 cycles of 45s */}
        {fSec >= T_SCENE1 && fSec < T_SCENE2 && [0, 1, 2, 3].map((ci) => (
          <ObjectScene
            key={`s1c${ci}`}
            frame={f} fps={fps}
            globalStart={fps * T_SCENE1}
            obj={objects[0]}
            colorName={colorName} colorHex={colorHex} bgColor={bgColor}
            rtl={rtl} cycleIndex={ci}
          />
        ))}

        {/* Scene 2: 4 cycles */}
        {fSec >= T_SCENE2 && fSec < T_SCENE3 && [0, 1, 2, 3].map((ci) => (
          <ObjectScene
            key={`s2c${ci}`}
            frame={f} fps={fps}
            globalStart={fps * T_SCENE2}
            obj={objects[1]}
            colorName={colorName} colorHex={colorHex} bgColor={bgColor}
            rtl={rtl} cycleIndex={ci}
          />
        ))}

        {/* Scene 3: 4 cycles */}
        {fSec >= T_SCENE3 && fSec < T_SONG && [0, 1, 2, 3].map((ci) => (
          <ObjectScene
            key={`s3c${ci}`}
            frame={f} fps={fps}
            globalStart={fps * T_SCENE3}
            obj={objects[2]}
            colorName={colorName} colorHex={colorHex} bgColor={bgColor}
            rtl={rtl} cycleIndex={ci}
          />
        ))}

        {/* ── SONG ────────────────────────────────────────────────────── */}
        <SongSection
          frame={f} fps={fps} globalStart={fps * T_SONG}
          objects={[...objects]} colorName={colorName} colorHex={colorHex} rtl={rtl}
        />

        {/* ── REVIEW ──────────────────────────────────────────────────── */}
        <ReviewSection
          frame={f} fps={fps} globalStart={fps * T_REVIEW}
          objects={[...objects]} colorName={colorName} colorHex={colorHex} rtl={rtl}
        />

        {/* ── OUTRO (last 60s) ────────────────────────────────────────── */}
        {fSec >= T_OUTRO && (
          <AbsoluteFill style={{
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 40,
          }}>
            {/* All 3 objects in a row */}
            <div style={{ display: "flex", gap: 60, alignItems: "center" }}>
              {objects.map((obj, i) => (
                <div key={i} style={{
                  display: "flex", flexDirection: "column", alignItems: "center", gap: 16,
                }}>
                  <Img
                    src={staticFile(`sprites/${obj.spritePath}`)}
                    style={{ width: 360, height: 360, objectFit: "contain" }}
                  />
                  <div style={{
                    backgroundColor: colorHex, borderRadius: 12, padding: "8px 24px",
                  }}>
                    <span style={{
                      fontFamily: font, fontSize: 48, fontWeight: 900, color: "white",
                    }}>
                      {obj.nameLocalized}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            {/* Color name */}
            <span style={{
              fontFamily: font, fontSize: 160, fontWeight: 900,
              color: colorHex, WebkitTextStroke: "8px white",
              textShadow: "0 8px 28px rgba(0,0,0,0.18)",
              direction: rtl ? "rtl" : "ltr",
            }}>
              {colorName}
            </span>
            {/* Channel tag */}
            <span style={{
              fontFamily: "'Arial',sans-serif", fontSize: 48,
              color: "#666", textShadow: "0 2px 8px rgba(0,0,0,0.1)",
            }}>
              Happy Bear Kids
            </span>
          </AbsoluteFill>
        )}

      </AbsoluteFill>
    </AbsoluteFill>
  );
};
