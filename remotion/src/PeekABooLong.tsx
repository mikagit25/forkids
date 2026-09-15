/**
 * PeekABooLong — 18–22 min peek-a-boo format for toddlers 0+.
 *
 * Single centred box. One character per reveal cycle:
 *   PEEK   (0–18%)  Box slides in; silhouette barely visible (brightness:0)
 *   WIGGLE (18–48%) Silhouette rocks left-right — tension build-up
 *   POP    (48–60%) spring() launch + brightness 0→1 + confetti burst
 *   WOBBLE (60–90%) Character bounces in full colour above the box
 *   HIDE   (90–100%)Character descends back; brightness fades to 0
 *
 * `cycleDuration` prop (frames, default 360 = 12s at 30fps) controls cycle length.
 * `boxTheme` selects a colour palette + background: warm | night | tropical | candy
 * `bgImage`  shows a FLUX background with Ken Burns zoom behind the box.
 * Generator passes ALL available 3D sprites (~88 items) so the video has
 * ~17.6 min of unique content — no looping, no repetition.
 * No text → single render works for EN / AR.
 */
import React from "react";
import {
  AbsoluteFill, Audio, Img,
  interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
  Sequence,
} from "remotion";

// ── Phase proportions ────────────────────────────────────────────────────────
const PEEK_PCT   = 0.18;
const WIGGLE_PCT = 0.30;
const POP_PCT    = 0.12;
const WOBBLE_PCT = 0.30;

function phaseFrames(cycleDur: number) {
  const peek   = Math.round(cycleDur * PEEK_PCT);
  const wiggle = Math.round(cycleDur * WIGGLE_PCT);
  const pop    = Math.round(cycleDur * POP_PCT);
  const wobble = Math.round(cycleDur * WOBBLE_PCT);
  const hide   = cycleDur - peek - wiggle - pop - wobble;
  return {
    PEEK_DUR: peek, WIGGLE_DUR: wiggle, POP_DUR: pop, WOBBLE_DUR: wobble, HIDE_DUR: hide,
    WIGGLE_START: peek,
    POP_START:    peek + wiggle,
    WOBBLE_START: peek + wiggle + pop,
    HIDE_START:   peek + wiggle + pop + wobble,
  };
}

// ── Box themes ────────────────────────────────────────────────────────────────

interface BoxThemeData {
  bgColor:    string;
  bgColorEnd: string;
  /** null = use per-character boxColor from generator */
  palette:    string[] | null;
  confetti:   string[];
}

const BOX_THEMES: Record<string, BoxThemeData> = {
  warm: {
    bgColor:    "#FFF9C4",
    bgColorEnd: "#E1F5FE",
    palette:    null,
    confetti:   ["#FF5252","#FFEB3B","#69F0AE","#40C4FF","#E040FB","#FF9800","#00E5FF"],
  },
  night: {
    bgColor:    "#0D1B4B",
    bgColorEnd: "#1A0533",
    palette:    ["#B39DDB","#80DEEA","#FFD54F","#EF9A9A","#A5D6A7","#80CBC4","#CE93D8","#FFF176","#FFAB91","#81D4FA"],
    confetti:   ["#FFD700","#C0C0C0","#E040FB","#40C4FF","#FFEB3B","#A0E0FF","#69F0AE"],
  },
  tropical: {
    bgColor:    "#E0F7FA",
    bgColorEnd: "#FFF8E1",
    palette:    ["#FF7043","#26C6DA","#AB47BC","#66BB6A","#FFA726","#26A69A","#EF5350","#29B6F6","#D4E157","#FF8F00"],
    confetti:   ["#FF5722","#00BCD4","#8BC34A","#FF9800","#9C27B0","#03A9F4","#CDDC39"],
  },
  candy: {
    bgColor:    "#FCE4EC",
    bgColorEnd: "#F3E5F5",
    palette:    ["#F48FB1","#CE93D8","#80DEEA","#A5D6A7","#FFCC80","#80CBC4","#F06292","#BA68C8","#FFE082","#B39DDB"],
    confetti:   ["#FF80AB","#EA80FC","#80D8FF","#CCFF90","#FFD180","#A7FFEB","#FF6E40"],
  },
};

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CharacterEntry {
  sprite:   string;
  boxColor: string;
}

export interface PeekABooLongProps {
  characters?:    CharacterEntry[];
  musicFile?:     string;
  musicVolume?:   number;
  bgColor?:       string;
  bgColorEnd?:    string;
  /** Colour theme — overrides bgColor/bgColorEnd and box palette. */
  boxTheme?:      "warm" | "night" | "tropical" | "candy";
  /** Filename in remotion/public/backgrounds/ — Ken Burns zoom behind box. */
  bgImage?:       string;
  /** 0–1 darken overlay on bgImage for contrast (default 0.18). */
  bgDim?:         number;
  /** Frames per reveal cycle. Default 360 = 12s at 30fps. */
  cycleDuration?: number;
}

// ── Default characters (25, used when no prop passed) ─────────────────────────

const DEFAULT_CHARACTERS: CharacterEntry[] = [
  { sprite: "animals/bear_3d.png",              boxColor: "#A1887F" },
  { sprite: "animals/cat_3d.png",               boxColor: "#42A5F5" },
  { sprite: "animals/dog_3d.png",               boxColor: "#FF7043" },
  { sprite: "animals/rabbit_3d.png",            boxColor: "#EC407A" },
  { sprite: "animals/penguin_3d.png",           boxColor: "#5C6BC0" },
  { sprite: "animals/lion_3d.png",              boxColor: "#FFA726" },
  { sprite: "animals/elephant_3d.png",          boxColor: "#7E57C2" },
  { sprite: "animals/monkey_3d.png",            boxColor: "#8D6E63" },
  { sprite: "animals/frog_3d.png",              boxColor: "#43A047" },
  { sprite: "animals/owl_3d.png",               boxColor: "#26A69A" },
  { sprite: "animals/dino_3d.png",              boxColor: "#66BB6A" },
  { sprite: "animals/duck_3d.png",              boxColor: "#F9A825" },
  { sprite: "animals/tiger_3d.png",             boxColor: "#FF8F00" },
  { sprite: "animals/panda_3d.png",             boxColor: "#78909C" },
  { sprite: "animals/koala_3d.png",             boxColor: "#6D4C41" },
  { sprite: "fruits/apple_3d.png",              boxColor: "#E53935" },
  { sprite: "fruits/banana_3d.png",             boxColor: "#FDD835" },
  { sprite: "fruits/strawberry_3d.png",         boxColor: "#E91E63" },
  { sprite: "fruits/orange_3d.png",             boxColor: "#FB8C00" },
  { sprite: "fruits/watermelon_3d.png",         boxColor: "#388E3C" },
  { sprite: "vegetables/carrot_3d.png",         boxColor: "#EF6C00" },
  { sprite: "vegetables/corn_3d.png",           boxColor: "#F9A825" },
  { sprite: "vegetables/pumpkin_3d.png",        boxColor: "#E64A19" },
  { sprite: "characters/bear_happy_3d.png",     boxColor: "#8D6E63" },
  { sprite: "characters/bear_celebrate_3d.png", boxColor: "#FF8F00" },
];

// ── Colour helpers ────────────────────────────────────────────────────────────

function adjustBright(hex: string, f: number): string {
  const h = hex.replace("#", "");
  const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
  const r = clamp(parseInt(h.slice(0, 2), 16) * f);
  const g = clamp(parseInt(h.slice(2, 4), 16) * f);
  const b = clamp(parseInt(h.slice(4, 6), 16) * f);
  return `rgb(${r},${g},${b})`;
}

function sr(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

// ── BoxShape ──────────────────────────────────────────────────────────────────

interface BoxShapeProps {
  x: number; y: number; w: number; h: number;
  color: string;
  entranceOffsetY?: number;
}

const BoxShape: React.FC<BoxShapeProps> = ({ x, y, w, h, color, entranceOffsetY = 0 }) => {
  const light  = adjustBright(color, 1.28);
  const dark   = adjustBright(color, 0.68);
  const darker = adjustBright(color, 0.46);
  const flapW  = w * 0.47;
  const flapH  = h * 0.26;
  const ey     = entranceOffsetY;

  return (
    <>
      <div style={{
        position: "absolute",
        left: x, top: y + ey, width: w, height: h,
        background: `linear-gradient(155deg, ${light} 0%, ${color} 45%, ${dark} 100%)`,
        borderRadius: "6px 6px 12px 12px",
        boxShadow: "0 16px 52px rgba(0,0,0,0.27)",
        zIndex: 2,
      }} />
      <div style={{
        position: "absolute",
        left: x, top: y - flapH + ey,
        width: flapW, height: flapH,
        background: `linear-gradient(125deg, ${light} 0%, ${color} 100%)`,
        transformOrigin: "bottom left",
        transform: "rotateZ(-38deg)",
        borderRadius: "5px 5px 0 0",
        boxShadow: "0 -3px 12px rgba(0,0,0,0.16)",
        zIndex: 1,
      }} />
      <div style={{
        position: "absolute",
        left: x + w - flapW, top: y - flapH + ey,
        width: flapW, height: flapH,
        background: `linear-gradient(55deg, ${color} 0%, ${light} 100%)`,
        transformOrigin: "bottom right",
        transform: "rotateZ(38deg)",
        borderRadius: "5px 5px 0 0",
        boxShadow: "0 -3px 12px rgba(0,0,0,0.16)",
        zIndex: 1,
      }} />
      <div style={{
        position: "absolute",
        left: x - 4, top: y + h * 0.44 + ey,
        width: w + 8, height: h * 0.58 + 16,
        background: `linear-gradient(170deg, ${dark} 0%, ${darker} 100%)`,
        borderRadius: "4px 4px 12px 12px",
        boxShadow: "0 18px 34px rgba(0,0,0,0.32), inset 0 3px 8px rgba(255,255,255,0.12)",
        zIndex: 10,
      }}>
        <div style={{
          position: "absolute", left: "8%", right: "8%", top: "38%",
          height: 3, background: "rgba(0,0,0,0.14)", borderRadius: 2,
        }} />
      </div>
    </>
  );
};

// ── ConfettiBurst ─────────────────────────────────────────────────────────────

interface ConfettiBurstProps {
  cx: number; cy: number;
  age: number;
  fps: number;
  maxAge: number;
  colors: string[];
}

const ConfettiBurst: React.FC<ConfettiBurstProps> = ({ cx, cy, age, fps, maxAge, colors }) => {
  if (age <= 0 || age > maxAge) return null;

  const t = age / fps;

  const fade = interpolate(age, [0, maxAge * 0.8], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const els: React.ReactNode[] = [];

  const r1 = interpolate(age, [0, maxAge * 0.65], [50, 230], { extrapolateRight: "clamp" });
  for (let i = 0; i < 12; i++) {
    const a  = (i / 12) * Math.PI * 2;
    const px = cx + Math.cos(a) * r1;
    const py = cy + Math.sin(a) * r1;
    const sz = 15 + sr(i * 7) * 9;
    const col = colors[i % colors.length];
    els.push(
      <div key={`r1_${i}`} style={{
        position: "absolute",
        left: px - sz / 2, top: py - sz / 2,
        width: sz, height: sz,
        borderRadius: sr(i * 11) > 0.5 ? "50%" : "3px",
        backgroundColor: col,
        opacity: fade * (0.65 + sr(i * 13) * 0.35),
        transform: `rotate(${age * (3 + sr(i * 17) * 4)}deg)`,
      }} />
    );
  }

  const r2 = interpolate(age, [0, maxAge * 0.80], [80, 360], { extrapolateRight: "clamp" });
  const fade2 = interpolate(age, [0, maxAge * 0.9], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  for (let i = 0; i < 10; i++) {
    const a  = (i / 10) * Math.PI * 2 + Math.PI / 10;
    const px = cx + Math.cos(a) * r2;
    const py = cy + Math.sin(a) * r2;
    const sz = 18 + sr(i * 5 + 100) * 14;
    const col = colors[(i + 3) % colors.length];
    els.push(
      <div key={`r2_${i}`} style={{
        position: "absolute",
        left: px - sz / 2, top: py - sz / 2,
        width: sz, height: sz * 0.58,
        borderRadius: "2px",
        backgroundColor: col,
        opacity: fade2 * (0.55 + sr(i * 9 + 50) * 0.45),
        transform: `rotate(${age * (2 + sr(i * 19 + 80) * 5)}deg)`,
      }} />
    );
  }

  const GRAVITY = 900;
  const sparkFade = interpolate(age, [0, maxAge * 0.6], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  for (let i = 0; i < 8; i++) {
    const a     = (i / 8) * Math.PI * 2;
    const speed = 360 + sr(i * 3 + 200) * 220;
    const vx    = Math.cos(a) * speed;
    const vy    = Math.sin(a) * speed - 80;
    const px    = cx + vx * t;
    const py    = cy + vy * t + 0.5 * GRAVITY * t * t;
    const sz    = 20 + sr(i * 7 + 300) * 10;
    els.push(
      <div key={`sp_${i}`} style={{
        position: "absolute",
        left: px - sz / 2, top: py - sz / 2,
        width: sz, height: sz,
        fontSize: sz, lineHeight: 1,
        color: colors[i % colors.length],
        opacity: sparkFade,
        textAlign: "center",
        userSelect: "none",
      }}>✦</div>
    );
  }

  return <>{els}</>;
};

// ── Main composition ──────────────────────────────────────────────────────────

export const PeekABooLong: React.FC<PeekABooLongProps> = ({
  characters    = DEFAULT_CHARACTERS,
  musicFile     = "Monkeys Spinning Monkeys.mp3",
  musicVolume   = 0.20,
  bgColor       = "#FFF9C4",
  bgColorEnd    = "#E1F5FE",
  boxTheme,
  bgImage,
  bgDim         = 0.18,
  cycleDuration = 360,
}) => {
  const frame  = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  const {
    PEEK_DUR, WIGGLE_DUR, POP_DUR, WOBBLE_DUR, HIDE_DUR,
    WIGGLE_START, POP_START, WOBBLE_START, HIDE_START,
  } = phaseFrames(cycleDuration);

  // Resolve theme
  const theme    = boxTheme ? BOX_THEMES[boxTheme] ?? BOX_THEMES.warm : null;
  const resolvedBgColor    = theme ? theme.bgColor    : bgColor;
  const resolvedBgColorEnd = theme ? theme.bgColorEnd : bgColorEnd;
  const confettiColors     = theme ? theme.confetti   : BOX_THEMES.warm.confetti;

  const CYCLE = cycleDuration;

  const totalCycleFrames = characters.length * CYCLE;
  const loopFrame  = frame % totalCycleFrames;
  const cycleIdx   = Math.floor(loopFrame / CYCLE);
  const localF     = loopFrame % CYCLE;

  const char     = characters[cycleIdx % characters.length];
  const { sprite } = char;

  // Box colour: theme palette overrides per-character colour
  const boxColor = theme?.palette
    ? theme.palette[cycleIdx % theme.palette.length]
    : char.boxColor;

  // Global fade
  const fadeIn  = interpolate(frame, [0, fps * 0.6], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [durationInFrames - fps, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Box geometry
  const boxW = Math.round(width  * 0.22);
  const boxH = Math.round(height * 0.295);
  const boxX = (width - boxW) / 2;
  const boxY = Math.round(height * 0.545);

  const spriteSize = Math.round(boxW * 0.66);
  const spriteCX   = boxX + boxW / 2;

  const frontPanelTopY = boxY + boxH * 0.44;
  const spriteHiddenCY = frontPanelTopY;
  const spriteRevealCY = boxY - spriteSize * 0.62;

  const entranceOff = interpolate(localF, [0, 10], [56, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  const wiggleT = localF - WIGGLE_START;
  const popT    = localF - POP_START;
  const wobbleT = localF - WOBBLE_START;
  const hideT   = localF - HIDE_START;

  const wiggleX = (localF >= WIGGLE_START && localF < POP_START)
    ? Math.sin(wiggleT * 0.52) * 30 : 0;
  const wiggleUp = (localF >= WIGGLE_START && localF < POP_START)
    ? -Math.abs(Math.sin(wiggleT * 0.27)) * 14 : 0;

  const popSp = spring({
    frame: popT, fps,
    config: { damping: 7, stiffness: 130, mass: 0.35 },
    durationInFrames: 18,
  });

  const wobbleY   = (localF >= WOBBLE_START && localF < HIDE_START)
    ? -Math.abs(Math.sin(wobbleT * 0.21)) * 26 : 0;
  const wobbleRot = (localF >= WOBBLE_START && localF < HIDE_START)
    ? Math.sin(wobbleT * 0.15) * 10 : 0;
  const wobbleSc  = (localF >= WOBBLE_START && localF < HIDE_START)
    ? 1 + Math.sin(wobbleT * 0.42) * 0.048 : 1;

  const hideProgress = (localF >= HIDE_START)
    ? interpolate(hideT, [0, HIDE_DUR], [0, 1], { extrapolateRight: "clamp" })
    : 0;

  let spriteCY  = spriteHiddenCY;
  let brightness = 0.0;
  let rot        = 0;
  let sc         = 1;
  let spriteX    = spriteCX + wiggleX;

  if (localF < WIGGLE_START) {
    spriteCY   = spriteHiddenCY + spriteSize * 0.06 + entranceOff;
    brightness = 0;
    spriteX    = spriteCX;
  } else if (localF < POP_START) {
    spriteCY   = spriteHiddenCY + wiggleUp;
    brightness = 0;
  } else if (localF < WOBBLE_START) {
    spriteCY   = interpolate(popSp, [0, 1], [spriteHiddenCY, spriteRevealCY]);
    brightness = interpolate(popT, [0, 5], [0, 1], { extrapolateRight: "clamp" });
    sc         = 1 + popSp * 0.10;
    spriteX    = spriteCX;
  } else if (localF < HIDE_START) {
    spriteCY   = spriteRevealCY + wobbleY;
    brightness = 1;
    rot        = wobbleRot;
    sc         = wobbleSc;
    spriteX    = spriteCX;
  } else {
    spriteCY   = interpolate(hideProgress, [0, 1], [spriteRevealCY, spriteHiddenCY]);
    brightness = interpolate(hideProgress, [0.55, 1.0], [1, 0], { extrapolateRight: "clamp" });
    spriteX    = spriteCX;
  }

  const spriteFilter = brightness < 0.99
    ? `brightness(${brightness.toFixed(2)})` : undefined;

  const confettiAge = localF - POP_START;
  const confettiMaxAge = POP_DUR + WOBBLE_DUR;

  // Ken Burns scale for bgImage
  const kbScale = bgImage
    ? interpolate(frame, [0, durationInFrames], [1.0, 1.08])
    : 1;

  // Night theme: brighter sparkles; warm: gentle
  const sparkleOpBase = theme?.bgColor === BOX_THEMES.night.bgColor ? 0.20 : 0.11;
  const bgGlyphs = ["⭐", "✨", "🌟"];
  const bgSparkles = Array.from({ length: 18 }, (_, i) => {
    const sx = (i * 107 + 40) % width;
    const sy = (i * 83  + 20) % (height * 0.72);
    const op = sparkleOpBase + Math.sin(frame * 0.04 + i * 1.1) * 0.07;
    const sz = 14 + (i % 3) * 7;
    return (
      <div key={i} style={{
        position: "absolute", left: sx, top: sy,
        fontSize: sz, opacity: op, userSelect: "none", zIndex: 0,
      }}>
        {bgGlyphs[i % 3]}
      </div>
    );
  });

  return (
    <AbsoluteFill style={{
      background: `linear-gradient(155deg, ${resolvedBgColor} 0%, ${resolvedBgColorEnd} 100%)`,
      overflow: "hidden",
      opacity: Math.min(fadeIn, fadeOut),
    }}>
      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={musicVolume} loop />
      )}

      {/* Background image with Ken Burns zoom */}
      {bgImage && (
        <>
          <div style={{
            position: "absolute", inset: 0, zIndex: 0,
            overflow: "hidden",
          }}>
            <Img
              src={staticFile(`backgrounds/${bgImage}`)}
              style={{
                width: "100%", height: "100%",
                objectFit: "cover",
                transform: `scale(${kbScale})`,
                transformOrigin: "center center",
              }}
            />
          </div>
          {bgDim > 0 && (
            <div style={{
              position: "absolute", inset: 0, zIndex: 1,
              background: `rgba(0,0,0,${bgDim})`,
            }} />
          )}
        </>
      )}

      {bgSparkles}

      <BoxShape x={boxX} y={boxY} w={boxW} h={boxH} color={boxColor} entranceOffsetY={entranceOff} />

      <div style={{
        position: "absolute",
        left: spriteX - spriteSize / 2,
        top:  spriteCY - spriteSize / 2,
        width: spriteSize, height: spriteSize,
        zIndex: 5,
        filter: spriteFilter,
        transform: `rotate(${rot}deg) scale(${sc})`,
        transformOrigin: "center center",
      }}>
        <Img
          src={staticFile(`sprites/${sprite}`)}
          style={{ width: spriteSize, height: spriteSize, objectFit: "contain" }}
        />
      </div>

      <div style={{
        position: "absolute", left: 0, top: 0, width, height,
        zIndex: 20, pointerEvents: "none",
      }}>
        <ConfettiBurst
          cx={spriteCX} cy={spriteRevealCY}
          age={confettiAge} fps={fps}
          maxAge={confettiMaxAge}
          colors={confettiColors}
        />
      </div>

      {characters.map((_, ci) => {
        const cs     = ci * CYCLE;
        const boing2 = Math.round(WIGGLE_DUR * 0.55);
        return (
          <React.Fragment key={ci}>
            <Sequence from={cs} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/whoosh.mp3")} volume={0.52} />
            </Sequence>
            <Sequence from={cs + WIGGLE_START} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/boing.mp3")} volume={0.44} />
            </Sequence>
            <Sequence from={cs + WIGGLE_START + boing2} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/boing.mp3")} volume={0.50} />
            </Sequence>
            <Sequence from={cs + POP_START} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/pop.mp3")} volume={0.90} />
            </Sequence>
            <Sequence from={cs + POP_START + 2} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/chime.mp3")} volume={0.75} />
            </Sequence>
            <Sequence from={cs + WOBBLE_START} durationInFrames={fps}>
              <Audio src={staticFile("audio/sfx/ding.mp3")} volume={0.62} />
            </Sequence>
          </React.Fragment>
        );
      })}

      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        height: height * 0.16,
        background: "linear-gradient(to top, rgba(0,0,0,0.07) 0%, transparent 100%)",
        pointerEvents: "none",
      }} />
    </AbsoluteFill>
  );
};
