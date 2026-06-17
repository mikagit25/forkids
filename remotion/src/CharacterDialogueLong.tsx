/**
 * CharacterDialogueLong — 20-min character-based educational dialogue video.
 * Cute bear character speaks to child, teaches concepts through dialogue.
 * 1920×1080, 30fps, ~20 minutes.
 *
 * Structure per episode:
 *   INTRO  (0–30s)   : Character enters, greets child
 *   SCENES (30–1140s): 4 learning scenes × 5 cycles each
 *   SONG   (1140–1170s): Recap chant
 *   OUTRO  (1170–1200s): Goodbye
 *
 * Props driven by episode JSON config. Character sprite: bear_character*.png
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig, Sequence,
} from "remotion";
import { ArabicFonts } from "./components/ArabicFonts";

export interface DialogueScene {
  id: string;
  title: string;         // e.g. "Happy"
  titleLocalized: string;
  spritePath: string;    // scene illustration / emoji concept sprite
  bgColor: string;       // scene background tint
}

export interface CharacterDialogueLongProps {
  episodeKey: string;
  episodeTitle: string;     // "Feelings with Roundy"
  characterSprite: string;  // "characters/bear_happy.png"
  accentColor: string;
  bgColor: string;
  rtl: boolean;
  lang: "en" | "ar" | "id";
  musicFile: string;
  audioBase: string;        // "audio/character_dialogue/{lang}/{key}"
  scenes: [DialogueScene, DialogueScene, DialogueScene, DialogueScene];
}

const FPS = 30;
const T_INTRO  = 0;
const T_SCENES = 30;
const T_SONG   = 1140;
const T_OUTRO  = 1170;

const SCENE_DUR    = (T_SONG - T_SCENES) / 4;  // 277.5s per scene
const CYCLE_DUR    = SCENE_DUR / 5;             // ~55s per cycle

const CONFETTI_COLORS = ["#FF4444","#FFD700","#4CAF50","#2196F3","#FF69B4","#FF9800","#9C27B0"];

// ── Confetti ─────────────────────────────────────────────────────────────────
const Confetti: React.FC<{ f: number }> = ({ f }) => {
  const fps = FPS;
  if (f < 0 || f > fps * 3) return null;
  return (
    <>
      {Array.from({ length: 20 }, (_, i) => {
        const fall  = f * 5;
        const sway  = Math.sin(f * 0.1 + i) * 40;
        const alpha = interpolate(f, [0, 10, fps * 2.5], [0, 1, 0], { extrapolateRight: "clamp" });
        return (
          <div key={i} style={{
            position: "absolute",
            left: 60 + i * 94, top: 0 + fall,
            width: 14, height: 14,
            backgroundColor: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
            borderRadius: 3, opacity: alpha,
            transform: `translateX(${sway}px) rotate(${f * 8 + i * 25}deg)`,
          }} />
        );
      })}
    </>
  );
};

// ── Character component ───────────────────────────────────────────────────────
const Character: React.FC<{
  spritePath: string;
  f: number;
  talking: boolean;
  size?: number;
  side?: "left" | "center" | "right";
}> = ({ spritePath, f, talking, size = 380, side = "center" }) => {
  const bounce = talking
    ? Math.sin(f * 0.18) * 12 + Math.abs(Math.sin(f * 0.35)) * 8
    : Math.abs(Math.sin(f * 0.06)) * 10;

  const leftPos = side === "left" ? "8%" : side === "right" ? "auto" : "50%";
  const rightPos = side === "right" ? "8%" : "auto";
  const transformX = side === "center" ? "translateX(-50%)" : "none";

  return (
    <div style={{
      position: "absolute",
      bottom: "8%",
      left: leftPos,
      right: rightPos,
      transform: `${transformX} translateY(${-bounce}px)`,
      width: size,
    }}>
      <Img
        src={staticFile(spritePath)}
        style={{ width: size, height: size, objectFit: "contain" }}
      />
    </div>
  );
};

// ── Speech bubble ─────────────────────────────────────────────────────────────
const SpeechBubble: React.FC<{
  text: string; f: number; startF: number;
  font: string; rtl: boolean; accentColor: string;
  position?: "top" | "mid";
}> = ({ text, f, startF, font, rtl, accentColor, position = "top" }) => {
  const localF = f - startF;
  if (localF < 0) return null;

  const appear = spring({
    frame: localF, fps: FPS,
    config: { damping: 14, stiffness: 180 },
    durationInFrames: FPS * 0.5,
  });
  const sc = interpolate(appear, [0, 1], [0.7, 1], { extrapolateRight: "clamp" });
  const op = interpolate(appear, [0, 1], [0, 1], { extrapolateRight: "clamp" });

  const topPct = position === "top" ? "5%" : "30%";

  return (
    <div style={{
      position: "absolute", top: topPct, left: "50%",
      transform: `translateX(-50%) scale(${sc})`,
      opacity: op,
      backgroundColor: "white",
      borderRadius: 32, padding: "20px 48px",
      boxShadow: `0 8px 32px ${accentColor}44`,
      border: `4px solid ${accentColor}`,
      maxWidth: "80%",
      direction: rtl ? "rtl" : "ltr",
    }}>
      <span style={{
        fontFamily: font, fontSize: 68, fontWeight: 900,
        color: accentColor,
        textShadow: "0 2px 8px rgba(0,0,0,0.1)",
        lineHeight: 1.2,
      }}>
        {text}
      </span>
      {/* Tail */}
      <div style={{
        position: "absolute", bottom: -28, left: "50%",
        transform: "translateX(-50%)",
        width: 0, height: 0,
        borderLeft: "20px solid transparent",
        borderRight: "20px solid transparent",
        borderTop: `28px solid ${accentColor}`,
      }} />
    </div>
  );
};

// ── One learning cycle ────────────────────────────────────────────────────────
const LearningCycle: React.FC<{
  frame: number; cycleStart: number; sceneStart: number; cycleIdx: number;
  scene: DialogueScene; characterSprite: string;
  accentColor: string; font: string; rtl: boolean; lang: string;
  episodeKey: string; sceneIdx: number; audioBase: string;
}> = ({ frame, cycleStart, sceneStart, cycleIdx, scene, characterSprite,
        accentColor, font, rtl, lang, episodeKey, sceneIdx, audioBase }) => {

  const f    = frame - cycleStart;
  const lenF = Math.round(CYCLE_DUR * FPS);
  if (f < 0 || f >= lenF) return null;

  const fSec = f / FPS;
  const fadeOut = interpolate(f, [lenF - FPS * 3, lenF], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Scene illustration bouncing
  const illuSp = spring({ frame: f, fps: FPS,
    config: { damping: 12, stiffness: 100 }, durationInFrames: FPS * 1.5 });
  const illuScale = interpolate(illuSp, [0, 1], [0.3, 1], { extrapolateRight: "clamp" });
  const illuBounce = fSec > 2 ? Math.abs(Math.sin(fSec * 1.4)) * 22 : 0;

  const talking = fSec > 1 && fSec < CYCLE_DUR - 4;
  const celebrating = fSec > CYCLE_DUR - 8 && fSec < CYCLE_DUR - 3;

  // Audio: one file per scene (plays once per cycle)
  const audioFile = `${audioBase}_scene${sceneIdx + 1}.mp3`;

  return (
    <AbsoluteFill style={{ backgroundColor: scene.bgColor + "33", opacity: fadeOut }}>

      {/* Scene audio */}
      <Audio src={staticFile(audioFile)} />

      {/* Scene illustration — large, centered top */}
      <div style={{
        position: "absolute", top: "6%", left: "50%",
        transform: `translateX(-50%) scale(${illuScale}) translateY(${-illuBounce}px)`,
      }}>
        <Img
          src={staticFile(`sprites/${scene.spritePath}`)}
          style={{ width: 460, height: 460, objectFit: "contain" }}
        />
      </div>

      {/* Concept name — big, clear */}
      <SpeechBubble
        text={scene.titleLocalized}
        f={f} startF={FPS * 1}
        font={font} rtl={rtl} accentColor={accentColor}
        position="mid"
      />

      {/* Character */}
      <Character
        spritePath={characterSprite}
        f={f} talking={talking}
        side="left"
      />

      {/* Celebration confetti */}
      {celebrating && <Confetti f={f - Math.round((CYCLE_DUR - 8) * FPS)} />}

    </AbsoluteFill>
  );
};

// ── Main composition ──────────────────────────────────────────────────────────
export const CharacterDialogueLong: React.FC<CharacterDialogueLongProps> = ({
  episodeTitle, characterSprite, accentColor, bgColor,
  rtl, lang, musicFile, audioBase, scenes,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const f    = frame;
  const fSec = f / fps;
  const font = rtl
    ? "'Noto Sans Arabic','Noto Kufi Arabic',sans-serif"
    : "'Arial Black',sans-serif";

  const fadeOut = interpolate(
    f, [durationInFrames - fps * 2, durationInFrames], [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Intro character spring
  const introSp    = spring({ frame: f, fps, config: { damping: 10, stiffness: 90 }, durationInFrames: fps * 1.5 });
  const introScale = interpolate(introSp, [0, 1], [0.1, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, overflow: "hidden" }}>
      <ArabicFonts />
      <Audio src={staticFile(`music/${musicFile}`)} volume={0.1} loop />

      {/* Section audio */}
      <Audio src={staticFile(`${audioBase}_intro.mp3`)} />
      <Sequence from={fps * T_SONG}>
        <Audio src={staticFile(`${audioBase}_song.mp3`)} />
      </Sequence>
      <Sequence from={fps * T_OUTRO}>
        <Audio src={staticFile(`${audioBase}_outro.mp3`)} />
      </Sequence>

      <AbsoluteFill style={{ opacity: fadeOut }}>

        {/* ── INTRO (0–30s) ───────────────────────────────────────────── */}
        {fSec < T_SCENES && (
          <AbsoluteFill style={{ display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 24 }}>
            {/* Episode title */}
            <span style={{
              fontFamily: font, fontSize: 96, fontWeight: 900,
              color: accentColor, WebkitTextStroke: "5px white",
              direction: rtl ? "rtl" : "ltr",
              textShadow: `0 10px 40px ${accentColor}44`,
              transform: `scale(${introScale})`,
            }}>
              {episodeTitle}
            </span>

            {/* Character big + bouncing */}
            <div style={{ transform: `scale(${introScale}) translateY(${Math.abs(Math.sin(fSec * 1.2)) * -20}px)` }}>
              <Img src={staticFile(characterSprite)}
                   style={{ width: 480, height: 480, objectFit: "contain" }} />
            </div>
          </AbsoluteFill>
        )}

        {/* ── 4 SCENES ────────────────────────────────────────────────── */}
        {scenes.map((scene, si) => {
          const sceneStartS = T_SCENES + si * SCENE_DUR;
          const sceneEndS   = sceneStartS + SCENE_DUR;
          if (fSec < sceneStartS || fSec >= sceneEndS) return null;

          const sceneStartF = Math.round(sceneStartS * fps);
          const numCycles   = 5;

          return (
            <AbsoluteFill key={scene.id}>
              {/* Scene background color bar */}
              <div style={{
                position: "absolute", top: 0, left: 0, right: 0, height: 8,
                backgroundColor: scene.bgColor,
              }} />

              {/* Cycles */}
              {Array.from({ length: numCycles }, (_, ci) => {
                const cycleStart = sceneStartF + Math.round(ci * CYCLE_DUR * fps);
                return (
                  <LearningCycle
                    key={ci}
                    frame={f} cycleStart={cycleStart} sceneStart={sceneStartF}
                    cycleIdx={ci} scene={scene}
                    characterSprite={characterSprite}
                    accentColor={accentColor} font={font} rtl={rtl} lang={lang}
                    episodeKey="" sceneIdx={si} audioBase={audioBase}
                  />
                );
              })}
            </AbsoluteFill>
          );
        })}

        {/* ── SONG (1140–1170s) ────────────────────────────────────────── */}
        {fSec >= T_SONG && fSec < T_OUTRO && (
          <AbsoluteFill style={{ display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 40 }}>

            {/* All 4 concepts grid */}
            <div style={{ display: "flex", gap: 40, flexWrap: "wrap",
              justifyContent: "center", maxWidth: 1400 }}>
              {scenes.map((sc, i) => {
                const pulse = 1 + Math.abs(Math.sin(fSec * 2 + i * 0.8)) * 0.12;
                return (
                  <div key={sc.id} style={{ display: "flex", flexDirection: "column",
                    alignItems: "center", gap: 12, transform: `scale(${pulse})` }}>
                    <Img src={staticFile(`sprites/${sc.spritePath}`)}
                         style={{ width: 260, height: 260, objectFit: "contain" }} />
                    <span style={{
                      fontFamily: font, fontSize: 44, fontWeight: 900,
                      color: accentColor, direction: rtl ? "rtl" : "ltr",
                    }}>
                      {sc.titleLocalized}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Character */}
            <Character spritePath={characterSprite} f={f} talking size={300} side="center" />
          </AbsoluteFill>
        )}

        {/* ── OUTRO (1170–1200s) ───────────────────────────────────────── */}
        {fSec >= T_OUTRO && (
          <AbsoluteFill style={{ display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 32 }}>
            <span style={{
              fontFamily: font, fontSize: 90, fontWeight: 900,
              color: accentColor, WebkitTextStroke: "5px white",
              direction: rtl ? "rtl" : "ltr",
            }}>
              {episodeTitle}
            </span>
            <Img src={staticFile(characterSprite)}
                 style={{ width: 420, height: 420, objectFit: "contain",
                   transform: `translateY(${Math.abs(Math.sin(fSec * 1.4)) * -24}px)` }} />
            <span style={{ fontFamily: "'Arial', sans-serif", fontSize: 52, color: "#888" }}>
              Happy Bear Kids
            </span>
          </AbsoluteFill>
        )}

      </AbsoluteFill>
    </AbsoluteFill>
  );
};
