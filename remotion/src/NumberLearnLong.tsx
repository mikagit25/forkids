/**
 * NumberLearnLong — 20-min "One Concept Deep" number learning video.
 * 1920×1080 landscape. Numbers 1–10, one per video.
 *
 * Structure (20 min = 1200s at 30fps):
 *   INTRO        0–30s   : Digit bounces in, "Today is the number N!"
 *   REVIEW       30–90s  : Flash digits 1…N-1 (skipped for N=1)
 *   SCENE 1      90–390s : Count objects A × N, 4 repetitions per min
 *   SCENE 2      390–690s: Count objects B × N
 *   SCENE 3      690–870s: Count objects C × N (shorter)
 *   FINGERS      870–990s: Animated finger count (pure TSX)
 *   SONG         990–1140s: Number chant with all 3 object types
 *   OUTRO        1140–1200s: All objects in a row + digit + bye
 *
 * Counting cycle (45s):
 *   0–3s  : Question appears, stage empty
 *   3s+i×spacing: Object i bounces in with badge "i+1"
 *   After all N: big digit flashes + confetti
 *   Last 3s: fade
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, Sequence, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { ArabicFonts } from "./components/ArabicFonts";

export interface NumberObject {
  name: string;         // "apple"
  nameLocalized: string;// "Apple" or "تفاحة"
  pluralLocalized: string; // "Apples" or "تفاحات"
  spritePath: string;   // "fruits/apple.png"
}

export interface NumberLearnLongProps {
  numberValue: number;    // 1-10
  numberName: string;     // "THREE" or "ثلاثة"
  numberDigit: string;    // "3"
  accentColor: string;    // "#43A047"
  bgColor: string;
  rtl: boolean;
  lang: "en" | "ar" | "id";
  numberKey: string;      // "three"
  objects: [NumberObject, NumberObject, NumberObject];
  musicFile: string;
}

const FPS  = 30;
const CYCLE = 45;   // seconds per counting cycle

// Section boundaries (seconds)
const T_INTRO   = 0;
const T_REVIEW  = 30;
const T_SCENE1  = 90;
const T_SCENE2  = 390;
const T_SCENE3  = 690;
const T_FINGERS = 870;
const T_SONG    = 990;
const T_OUTRO   = 1140;

const CONFETTI_COLORS = ["#FF4444","#FFD700","#4CAF50","#2196F3","#E91E8C","#FF9800","#9C27B0"];

// ── Confetti ──────────────────────────────────────────────────────────────────
const Confetti: React.FC<{ frame: number; startFrame: number }> = ({ frame, startFrame }) => {
  const f = frame - startFrame;
  if (f < 0 || f > 90) return null;
  const particles = Array.from({ length: 24 }, (_, i) => ({
    x: 80 + i * 76, y: 20,
    size: 8 + (i % 5) * 5,
    color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
  }));
  return (
    <>
      {particles.map((p, i) => {
        const fall = f * 4.5;
        const sway = Math.sin(f * 0.12 + i) * 35;
        const alpha = interpolate(f, [0, 15, 80], [0, 1, 0], { extrapolateRight: "clamp" });
        return (
          <div key={i} style={{
            position: "absolute", left: p.x, top: p.y + fall, width: p.size, height: p.size,
            backgroundColor: p.color, borderRadius: 3, opacity: alpha,
            transform: `translateX(${sway}px) rotate(${f * 6 + i * 30}deg)`,
          }} />
        );
      })}
    </>
  );
};

// ── Counting Badge ─────────────────────────────────────────────────────────────
const Badge: React.FC<{ count: number; color: string; size?: number }> = ({
  count, color, size = 60,
}) => (
  <div style={{
    width: size, height: size, borderRadius: "50%",
    backgroundColor: color, border: "4px solid white",
    display: "flex", alignItems: "center", justifyContent: "center",
    boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
  }}>
    <span style={{
      fontFamily: "'Arial Black', sans-serif",
      fontSize: size * 0.5, fontWeight: 900, color: "white",
      lineHeight: 1,
    }}>
      {count}
    </span>
  </div>
);

// ── Single counting cycle ──────────────────────────────────────────────────────
interface CountSceneProps {
  frame: number;
  fps: number;
  sceneStart: number;     // frame when this SECTION starts
  cycleIndex: number;
  N: number;
  obj: NumberObject;
  accentColor: string;
  numberName: string;
  numberDigit: string;
  rtl: boolean;
  lang: "en" | "ar" | "id";
  numberKey: string;
  objIndex: number;       // 0,1,2 — which object slot
}

const CountScene: React.FC<CountSceneProps> = ({
  frame, fps, sceneStart, cycleIndex,
  N, obj, accentColor, numberName, numberDigit, rtl, lang, numberKey, objIndex,
}) => {
  const cycleStart = sceneStart + cycleIndex * CYCLE * fps;
  const f = frame - cycleStart;
  if (f < 0 || f >= CYCLE * fps) return null;

  const fSec = f / fps;
  const font = rtl ? "'Noto Sans Arabic','Noto Kufi Arabic',sans-serif" : "'Arial Black',sans-serif";

  // Spacing between object appearances within the 45s cycle
  const questionDur = 3;        // seconds for question
  const countWindow = 37;       // seconds for counting (45 - 3 question - 5 fade)
  const spacing     = countWindow / Math.max(N, 1);

  // Audio for this cycle — reuse obj audio track
  const audioFile = `audio/number_learn/${lang}/${numberKey}_obj${objIndex + 1}.mp3`;

  // Question fade out at 3s
  const qOpacity = interpolate(f, [fps * 2.5, fps * 3.5], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Objects — each appears at questionDur + i * spacing
  const objectAppearTimes = Array.from({ length: N }, (_, i) =>
    questionDur + i * spacing
  );

  // Celebration: all objects in + 2s
  const celebStart = questionDur + (N - 1) * spacing + 2;
  const celebrating = fSec >= celebStart && fSec < CYCLE - 3;

  // Fade out last 3s
  const fadeOut = interpolate(f, [fps * (CYCLE - 3), fps * CYCLE], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Layout: N objects in a row (max 5 per row)
  const cols   = Math.min(N, 5);
  const rows   = Math.ceil(N / cols);
  const objW   = Math.min(500, Math.floor(1400 / Math.max(cols, 1)));
  const startX = (1920 - cols * objW) / 2;
  const startY = rows > 1 ? 200 : 280;

  const questionText = rtl
    ? `كم ${obj.name}؟`
    : `How many ${obj.pluralLocalized.toLowerCase()}?`;

  const answerText = rtl
    ? `${numberName}! ${numberDigit} ${obj.pluralLocalized}!`
    : `${numberName}! ${numberDigit} ${obj.pluralLocalized}!`;

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      {/* Audio — start at cycle beginning */}
      <Audio src={staticFile(audioFile)} />

      {/* Question */}
      <div style={{
        position: "absolute", top: "8%", left: 0, right: 0,
        display: "flex", justifyContent: "center", opacity: qOpacity,
        direction: rtl ? "rtl" : "ltr",
      }}>
        <span style={{
          fontFamily: font, fontSize: 72, fontWeight: 700,
          color: "#333", textShadow: "0 2px 8px rgba(0,0,0,0.12)",
        }}>
          {questionText}
        </span>
      </div>

      {/* Objects grid */}
      {objectAppearTimes.map((entryTime, i) => {
        const entryFrame = Math.round(fps * entryTime);
        const visible    = f >= entryFrame;
        if (!visible) return null;

        const spg = spring({
          frame: f - entryFrame, fps,
          config: { damping: 10, stiffness: 120 },
          durationInFrames: Math.round(fps * 1.2),
        });
        const sc  = interpolate(spg, [0, 1], [0.2, 1], { extrapolateRight: "clamp" });
        const row = Math.floor(i / cols);
        const col = i % cols;
        const bounce = celebrating ? Math.abs(Math.sin(fSec * 2.5 + i * 0.6)) * 18 : 0;

        return (
          <div key={i} style={{
            position: "absolute",
            left: startX + col * objW,
            top:  startY + row * (objW + 60),
            width: objW, height: objW,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            transform: `scale(${sc}) translateY(${-bounce}px)`,
          }}>
            <Img
              src={staticFile(`sprites/${obj.spritePath}`)}
              style={{ width: objW * 0.8, height: objW * 0.8, objectFit: "contain" }}
            />
            <div style={{ marginTop: 4 }}>
              <Badge count={i + 1} color={accentColor} size={Math.max(44, objW * 0.22)} />
            </div>
          </div>
        );
      })}

      {/* Celebration: big digit + answer text */}
      {celebrating && (
        <>
          <Confetti frame={f} startFrame={Math.round(fps * celebStart)} />
          <div style={{
            position: "absolute", bottom: "6%", left: 0, right: 0,
            display: "flex", justifyContent: "center",
            direction: rtl ? "rtl" : "ltr",
          }}>
            <span style={{
              fontFamily: font, fontSize: 100, fontWeight: 900,
              color: accentColor, WebkitTextStroke: "5px white",
              textShadow: "0 6px 24px rgba(0,0,0,0.2)",
            }}>
              {answerText}
            </span>
          </div>
        </>
      )}
    </AbsoluteFill>
  );
};

// ── SVG Hand ─────────────────────────────────────────────────────────────────
const HandSVG: React.FC<{
  fingersUp: number; totalFingers: number; color: string; mirror?: boolean;
}> = ({ fingersUp, totalFingers, color, mirror = false }) => {
  const fingerXs  = [14, 40, 64, 88, 110];
  const fingerW   = 22;
  const upHeight  = 100;
  const downHeight = 38;
  const palmTop   = 130;

  return (
    <svg
      width="150" height="220" viewBox="0 0 150 220"
      style={{ transform: mirror ? "scaleX(-1)" : "none" }}
    >
      {/* Palm */}
      <rect x="4" y={palmTop} width="142" height="82" rx="22" fill={color} />
      {/* Fingers */}
      {fingerXs.map((x, i) => {
        const active = i < totalFingers;
        const isUp   = i < fingersUp;
        const h      = isUp ? upHeight : downHeight;
        const y      = isUp ? palmTop - upHeight : palmTop - downHeight + 8;
        return (
          <rect
            key={i}
            x={x} y={y} width={fingerW} height={h}
            rx={fingerW / 2}
            fill={color}
            opacity={active ? (isUp ? 1 : 0.45) : 0}
          />
        );
      })}
      {/* Thumb */}
      <ellipse cx="8" cy={palmTop + 35} rx="14" ry="20" fill={color} />
    </svg>
  );
};

// ── Animated finger counter ───────────────────────────────────────────────────
const FingerCount: React.FC<{
  frame: number; fps: number; globalStart: number;
  N: number; accentColor: string; numberName: string; rtl: boolean;
  lang: "en" | "ar" | "id"; numberKey: string;
}> = ({ frame, fps, globalStart, N, accentColor, numberName, rtl, lang, numberKey }) => {
  const f      = frame - globalStart;
  const totalS = T_SONG - T_FINGERS;  // 120s
  if (f < 0 || f >= totalS * fps) return null;

  const fSec   = f / fps;
  const cycleS = 30;
  const localF = fSec % cycleS;
  const font   = rtl ? "'Noto Sans Arabic','Noto Kufi Arabic',sans-serif" : "'Arial Black',sans-serif";

  // Animate fingers appearing one by one within each 30s cycle
  const fingersShown = Math.min(N, Math.floor(localF * (N + 1) / (cycleS * 0.7)) + 1);
  const leftUp  = Math.min(fingersShown, 5);
  const rightUp = N > 5 ? Math.max(0, fingersShown - 5) : 0;

  const pulse = 1 + Math.abs(Math.sin(fSec * 1.8)) * 0.06;

  return (
    <AbsoluteFill style={{
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: 32,
    }}>
      {/* Audio — voiced finger counting */}
      <Audio
        src={staticFile(`audio/number_learn/${lang}/${numberKey}_fingers.mp3`)}
      />

      {/* Number name */}
      <span style={{
        fontFamily: font, fontSize: 110, fontWeight: 900,
        color: accentColor, WebkitTextStroke: "5px white",
        direction: rtl ? "rtl" : "ltr",
        transform: `scale(${pulse})`,
      }}>
        {numberName}
      </span>

      {/* Hands */}
      <div style={{ display: "flex", gap: 60, alignItems: "flex-end" }}>
        <HandSVG fingersUp={leftUp} totalFingers={Math.min(N, 5)} color={accentColor} />
        {N > 5 && (
          <HandSVG fingersUp={rightUp} totalFingers={N - 5} color={accentColor} mirror />
        )}
      </div>

      {/* Finger count display */}
      <div style={{
        display: "flex", gap: 16, alignItems: "center",
        direction: rtl ? "rtl" : "ltr",
      }}>
        {Array.from({ length: N }, (_, i) => (
          <div key={i} style={{
            width: 54, height: 54, borderRadius: "50%",
            backgroundColor: i < fingersShown ? accentColor : "#ddd",
            border: "4px solid white",
            boxShadow: i < fingersShown ? `0 4px 16px ${accentColor}88` : "none",
            transition: "all 0.3s",
          }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ── Song section ──────────────────────────────────────────────────────────────
const SongSection: React.FC<{
  frame: number; fps: number; globalStart: number;
  N: number; objects: NumberObject[]; numberName: string; numberDigit: string;
  accentColor: string; rtl: boolean; lang: "en" | "ar" | "id"; numberKey: string;
}> = ({ frame, fps, globalStart, N, objects, numberName, numberDigit, accentColor, rtl, lang, numberKey }) => {
  const f    = frame - globalStart;
  const lenS = T_OUTRO - T_SONG;
  if (f < 0 || f >= lenS * fps) return null;

  const fSec   = f / fps;
  const beat   = 120 / 60;
  const pulse  = 1 + Math.abs(Math.sin(fSec * beat * Math.PI)) * 0.1;
  const objIdx = Math.floor(fSec / (lenS / 3)) % 3;
  const obj    = objects[objIdx];
  const font   = rtl ? "'Noto Sans Arabic','Noto Kufi Arabic',sans-serif" : "'Arial Black',sans-serif";
  const bounce = Math.abs(Math.sin(fSec * 2.2)) * 28;

  return (
    <AbsoluteFill>
      <Audio src={staticFile(`audio/number_learn/${lang}/${numberKey}_song.mp3`)} />

      {/* Big digit + name */}
      <div style={{
        position: "absolute", top: "5%", left: 0, right: 0,
        display: "flex", justifyContent: "center", gap: 40,
        transform: `scale(${pulse})`,
        direction: rtl ? "rtl" : "ltr",
      }}>
        <span style={{
          fontFamily: "'Arial Black',sans-serif",
          fontSize: 180, fontWeight: 900,
          color: accentColor, WebkitTextStroke: "8px white",
        }}>
          {numberDigit}
        </span>
        <span style={{
          fontFamily: font, fontSize: 140, fontWeight: 900,
          color: accentColor, WebkitTextStroke: "7px white",
          alignSelf: "center",
        }}>
          {numberName}
        </span>
      </div>

      {/* Bouncing object */}
      <div style={{
        position: "absolute", left: 0, right: 0, top: "30%",
        display: "flex", justifyContent: "center",
        transform: `translateY(${-bounce}px)`,
      }}>
        <Img
          src={staticFile(`sprites/${obj.spritePath}`)}
          style={{ width: 380, height: 380, objectFit: "contain" }}
        />
      </div>

      {/* Object count row */}
      <div style={{
        position: "absolute", bottom: "10%", left: 0, right: 0,
        display: "flex", justifyContent: "center", gap: 20,
        direction: rtl ? "rtl" : "ltr",
      }}>
        <span style={{
          fontFamily: font, fontSize: 72, fontWeight: 900,
          color: "white", WebkitTextStroke: `4px ${accentColor}`,
        }}>
          {numberDigit} {obj.pluralLocalized}
        </span>
      </div>
    </AbsoluteFill>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────
export const NumberLearnLong: React.FC<NumberLearnLongProps> = ({
  numberValue, numberName, numberDigit, accentColor, bgColor,
  rtl, lang, numberKey, objects, musicFile,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const f    = frame;
  const fSec = f / fps;
  const font = rtl ? "'Noto Sans Arabic','Noto Kufi Arabic',sans-serif" : "'Arial Black',sans-serif";
  const N    = numberValue;

  const audioBase = `audio/number_learn/${lang}/${numberKey}`;

  // Overall fade out
  const fadeOut = interpolate(
    f, [durationInFrames - fps * 2, durationInFrames], [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Intro digit spring
  const introSp    = spring({ frame: f, fps, config: { damping: 10, stiffness: 100 }, durationInFrames: fps * 1.5 });
  const introScale = interpolate(introSp, [0, 1], [0.2, 1], { extrapolateRight: "clamp" });
  const introFade  = interpolate(f, [fps * 28, fps * 30], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // How many cycles fit in each scene
  const scene1Dur   = T_SCENE2 - T_SCENE1;   // 300s
  const scene2Dur   = T_SCENE3 - T_SCENE2;   // 300s
  const scene3Dur   = T_FINGERS - T_SCENE3;  // 180s
  const scene1Cycles = Math.floor(scene1Dur / CYCLE);
  const scene2Cycles = Math.floor(scene2Dur / CYCLE);
  const scene3Cycles = Math.floor(scene3Dur / CYCLE);

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, overflow: "hidden" }}>
      <ArabicFonts />
      <Audio src={staticFile(`music/${musicFile}`)} volume={0.1} loop />

      {/* Section audio */}
      <Audio src={staticFile(`${audioBase}_intro.mp3`)} />
      <Sequence from={fps * T_REVIEW}>
        <Audio src={staticFile(`${audioBase}_review.mp3`)} />
      </Sequence>
      <Sequence from={fps * T_OUTRO}>
        <Audio src={staticFile(`${audioBase}_outro.mp3`)} />
      </Sequence>

      <AbsoluteFill style={{ opacity: fadeOut }}>

        {/* ── INTRO ──────────────────────────────────────────────────────── */}
        {fSec < T_REVIEW && (
          <AbsoluteFill style={{ opacity: introFade }}>
            <div style={{
              position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", gap: 24,
              transform: `scale(${introScale})`,
            }}>
              {/* Big digit */}
              <span style={{
                fontFamily: "'Arial Black', sans-serif",
                fontSize: 320, fontWeight: 900,
                color: accentColor, WebkitTextStroke: "12px white",
                textShadow: `0 16px 60px ${accentColor}66`,
                lineHeight: 1,
              }}>
                {numberDigit}
              </span>
              {/* Number name */}
              <span style={{
                fontFamily: font, fontSize: 130, fontWeight: 900,
                color: accentColor, WebkitTextStroke: "7px white",
                direction: rtl ? "rtl" : "ltr",
              }}>
                {numberName}
              </span>
            </div>
          </AbsoluteFill>
        )}

        {/* ── REVIEW (30–90s) ──────────────────────────────────────────────── */}
        {fSec >= T_REVIEW && fSec < T_SCENE1 && (() => {
          const reviewLen = T_SCENE1 - T_REVIEW;
          const fLocal    = fSec - T_REVIEW;

          if (N === 1) {
            // For ONE: pulse the big digit with breathing animation
            const pulse = 1 + Math.abs(Math.sin(fLocal * 1.4)) * 0.14;
            return (
              <AbsoluteFill style={{
                display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center", gap: 24,
              }}>
                <span style={{
                  fontFamily: "'Arial Black', sans-serif",
                  fontSize: 360, fontWeight: 900,
                  color: accentColor, WebkitTextStroke: "14px white",
                  textShadow: `0 20px 80px ${accentColor}66`,
                  lineHeight: 1, transform: `scale(${pulse})`,
                }}>
                  {numberDigit}
                </span>
                <span style={{
                  fontFamily: font, fontSize: 120, fontWeight: 900,
                  color: accentColor, WebkitTextStroke: "6px white",
                  direction: rtl ? "rtl" : "ltr",
                  transform: `scale(${1 + Math.abs(Math.sin(fLocal * 1.4 + 0.8)) * 0.08})`,
                }}>
                  {numberName}
                </span>
              </AbsoluteFill>
            );
          }

          // For N>1: flash previous digits
          const slotLen   = reviewLen / Math.min(N - 1, 6);
          const idx       = Math.floor(fLocal / slotLen);
          const showDigit = String(Math.min(idx + 1, N - 1));
          const sp = spring({
            frame: f - fps * (T_REVIEW + idx * slotLen), fps,
            config: { damping: 12, stiffness: 140 }, durationInFrames: fps * 0.8,
          });
          const sc = interpolate(sp, [0, 1], [0.3, 1], { extrapolateRight: "clamp" });
          return (
            <AbsoluteFill style={{
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", gap: 16,
            }}>
              <span style={{
                fontFamily: font, fontSize: 56, color: "#888",
                direction: rtl ? "rtl" : "ltr",
              }}>
                {rtl ? "نعرف بالفعل:" : "We already know:"}
              </span>
              <span style={{
                fontFamily: "'Arial Black', sans-serif",
                fontSize: 280, fontWeight: 900,
                color: accentColor, WebkitTextStroke: "10px white",
                transform: `scale(${sc})`, lineHeight: 1,
              }}>
                {showDigit}
              </span>
            </AbsoluteFill>
          );
        })()}

        {/* ── SCENE 1 (objects[0]) ───────────────────────────────────────── */}
        {fSec >= T_SCENE1 && fSec < T_SCENE2 &&
          Array.from({ length: scene1Cycles }, (_, ci) => (
            <CountScene
              key={`s1c${ci}`} frame={f} fps={fps}
              sceneStart={fps * T_SCENE1} cycleIndex={ci}
              N={N} obj={objects[0]}
              accentColor={accentColor} numberName={numberName} numberDigit={numberDigit}
              rtl={rtl} lang={lang} numberKey={numberKey} objIndex={0}
            />
          ))
        }

        {/* ── SCENE 2 (objects[1]) ───────────────────────────────────────── */}
        {fSec >= T_SCENE2 && fSec < T_SCENE3 &&
          Array.from({ length: scene2Cycles }, (_, ci) => (
            <CountScene
              key={`s2c${ci}`} frame={f} fps={fps}
              sceneStart={fps * T_SCENE2} cycleIndex={ci}
              N={N} obj={objects[1]}
              accentColor={accentColor} numberName={numberName} numberDigit={numberDigit}
              rtl={rtl} lang={lang} numberKey={numberKey} objIndex={1}
            />
          ))
        }

        {/* ── SCENE 3 (objects[2]) ───────────────────────────────────────── */}
        {fSec >= T_SCENE3 && fSec < T_FINGERS &&
          Array.from({ length: scene3Cycles }, (_, ci) => (
            <CountScene
              key={`s3c${ci}`} frame={f} fps={fps}
              sceneStart={fps * T_SCENE3} cycleIndex={ci}
              N={N} obj={objects[2]}
              accentColor={accentColor} numberName={numberName} numberDigit={numberDigit}
              rtl={rtl} lang={lang} numberKey={numberKey} objIndex={2}
            />
          ))
        }

        {/* ── FINGERS ────────────────────────────────────────────────────── */}
        <FingerCount
          frame={f} fps={fps} globalStart={fps * T_FINGERS}
          N={N} accentColor={accentColor} numberName={numberName} rtl={rtl}
          lang={lang} numberKey={numberKey}
        />

        {/* ── SONG ───────────────────────────────────────────────────────── */}
        <SongSection
          frame={f} fps={fps} globalStart={fps * T_SONG}
          N={N} objects={[...objects]} numberName={numberName} numberDigit={numberDigit}
          accentColor={accentColor} rtl={rtl} lang={lang} numberKey={numberKey}
        />

        {/* ── OUTRO ──────────────────────────────────────────────────────── */}
        {fSec >= T_OUTRO && (
          <AbsoluteFill style={{
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 36,
          }}>
            {/* All 3 objects in a row */}
            <div style={{ display: "flex", gap: 60, alignItems: "flex-end" }}>
              {objects.map((obj, i) => (
                <div key={i} style={{
                  display: "flex", flexDirection: "column", alignItems: "center", gap: 12,
                }}>
                  <Img
                    src={staticFile(`sprites/${obj.spritePath}`)}
                    style={{ width: 200, height: 200, objectFit: "contain" }}
                  />
                  <Badge count={N} color={accentColor} size={52} />
                  <span style={{
                    fontFamily: font, fontSize: 44, fontWeight: 700,
                    color: "#555", direction: rtl ? "rtl" : "ltr",
                  }}>
                    {obj.pluralLocalized}
                  </span>
                </div>
              ))}
            </div>

            {/* Big digit */}
            <span style={{
              fontFamily: "'Arial Black', sans-serif",
              fontSize: 200, fontWeight: 900,
              color: accentColor, WebkitTextStroke: "10px white",
              textShadow: `0 10px 40px ${accentColor}55`,
              lineHeight: 1,
            }}>
              {numberDigit}
            </span>

            {/* Name */}
            <span style={{
              fontFamily: font, fontSize: 110, fontWeight: 900,
              color: accentColor, WebkitTextStroke: "6px white",
              direction: rtl ? "rtl" : "ltr",
            }}>
              {numberName}
            </span>

            <span style={{
              fontFamily: "'Arial', sans-serif",
              fontSize: 48, color: "#888",
            }}>
              Happy Bear Kids
            </span>
          </AbsoluteFill>
        )}

      </AbsoluteFill>
    </AbsoluteFill>
  );
};
