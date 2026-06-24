/**
 * ShapeLearnLong — 30-min "One Concept Deep" shape learning video.
 * 1920×1080 landscape. No text — universal (EN + AR channels).
 *
 * Structure (30 min = 1800s at 30fps):
 *   INTRO      0–30s    : Shape drops in, bounces, glows
 *   FORM       30–630s  : Shape in canonical color, repeat reveal cycles (10 min)
 *   COLOR      630–1080s: Shape slowly cycles through rainbow (7.5 min)
 *   COUNT      1080–1440s: Visual 1→2→3 count cycles, dot patterns (6 min)
 *   HYPNO      1440–1770s: Multi-shape float + color drift, sleep-friendly (5.5 min)
 *   OUTRO      1770–1800s: Single shape pulses, fades to bg color
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Shape, ShapeName } from "./components/Shape";

export interface ShapeLearnLongProps {
  shapeName: ShapeName;
  shapeColor: string;   // canonical hex color for this shape
  bgColor: string;      // base background color
  musicFile: string;    // Kevin MacLeod track filename
  accentColor?: string; // optional second accent (defaults to shapeColor darker)
}

const FPS = 30;

// Section boundaries (seconds)
const T_INTRO  = 0;
const T_FORM   = 30;
const T_COLOR  = 630;
const T_COUNT  = 1080;
const T_HYPNO  = 1440;
const T_OUTRO  = 1770;
const T_END    = 1800;

// Rainbow hues for color phase (HSL hue degrees)
const RAINBOW_HUES = [0, 30, 60, 120, 180, 210, 270, 330, 360];

function hslToHex(h: number, s: number, l: number): string {
  h = h % 360;
  s /= 100; l /= 100;
  const k = (n: number) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  const r = Math.round(255 * f(0));
  const g = Math.round(255 * f(8));
  const b = Math.round(255 * f(4));
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

function hexToHSL(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h = 0, s = 0;
  const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = d / (1 - Math.abs(2 * l - 1));
    if (max === r) h = ((g - b) / d + 6) % 6 * 60;
    else if (max === g) h = ((b - r) / d + 2) * 60;
    else h = ((r - g) / d + 4) * 60;
  }
  return [h, s * 100, l * 100];
}

// ── INTRO: shape drops in from top, spring bounce ─────────────────────────────
const IntroSection: React.FC<{
  shapeName: ShapeName; color: string; bg: string;
  frame: number; fps: number;
}> = ({ shapeName, color, bg, frame, fps }) => {
  const localF = frame - T_INTRO * fps;
  const dropSpring = spring({ frame: localF, fps, config: { damping: 8, stiffness: 80 }, durationInFrames: fps * 2 });
  const y = interpolate(dropSpring, [0, 1], [-500, 0]);
  const glow = interpolate(localF, [fps * 1.5, fps * 2.5, fps * 4], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pulseScale = 1 + Math.sin(localF / (fps * 0.4)) * 0.04 * Math.max(0, 1 - localF / (fps * 3));

  return (
    <AbsoluteFill style={{ backgroundColor: bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{
        transform: `translateY(${y}px) scale(${pulseScale})`,
        filter: glow > 0.01 ? `drop-shadow(0 0 ${40 * glow}px ${color})` : undefined,
      }}>
        <Shape name={shapeName} size={340} color={color} />
      </div>
    </AbsoluteFill>
  );
};

// ── FORM: repeating reveal cycles — large / medium / small ────────────────────
const FORM_CYCLE = 30; // seconds per reveal cycle

const FormSection: React.FC<{
  shapeName: ShapeName; color: string; bg: string;
  frame: number; fps: number;
}> = ({ shapeName, color, bg, frame, fps }) => {
  const localF = frame - T_FORM * fps;
  const cycleF = fps * FORM_CYCLE;
  const cycleIdx = Math.floor(localF / cycleF);
  const f = localF % cycleF;

  const sizes = [380, 280, 200, 340, 250, 320];
  const size = sizes[cycleIdx % sizes.length];

  const appear = spring({ frame: f, fps, config: { damping: 12, stiffness: 100 }, durationInFrames: fps * 1.5 });
  const fadeOut = interpolate(f, [cycleF - fps * 3, cycleF], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const scale = interpolate(appear, [0, 1], [0.1, 1]);

  // Background shifts slightly per cycle
  const [h, s, l] = hexToHSL(bg);
  const bgShift = hslToHex((h + cycleIdx * 15) % 360, s * 0.5, Math.min(l + 5, 95));

  // Always-active animation — never static
  const fSec = f / fps;
  const idlePulse = 1 + Math.sin(fSec * 1.4) * 0.09;
  const idleFloat = Math.sin(fSec * 1.1) * 22;
  const idleSway  = Math.sin(fSec * 0.75 + 0.6) * 18;

  return (
    <AbsoluteFill style={{ backgroundColor: bgShift, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{
        transform: `scale(${scale * idlePulse}) translate(${idleSway}px, ${idleFloat}px)`,
        opacity: fadeOut,
      }}>
        <Shape name={shapeName} size={size} color={color} />
      </div>

      {/* Decorative smaller shapes in corners — each floats independently */}
      {[
        { x: "8%",  y: "10%" },
        { x: "82%", y: "10%" },
        { x: "8%",  y: "75%" },
        { x: "82%", y: "75%" },
      ].map((pos, i) => {
        const cornerDelay = fps * (1 + i * 0.3);
        const cornerA = spring({ frame: Math.max(0, f - cornerDelay), fps, config: { damping: 14, stiffness: 90 }, durationInFrames: fps });
        const cFloat  = Math.sin(fSec * 1.3 + i * 1.1) * 10;
        const cPulse  = 1 + Math.abs(Math.sin(fSec * 1.6 + i * 0.8)) * 0.12;
        return (
          <div key={i} style={{
            position: "absolute", left: pos.x, top: pos.y,
            transform: `scale(${interpolate(cornerA, [0, 1], [0, cPulse])}) translateY(${cFloat}px)`,
            opacity: fadeOut * 0.4,
          }}>
            <Shape name={shapeName} size={80} color={color} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ── COLOR: shape cycles through rainbow ───────────────────────────────────────
const ColorSection: React.FC<{
  shapeName: ShapeName; baseColor: string; bg: string;
  frame: number; fps: number;
}> = ({ shapeName, baseColor, bg, frame, fps }) => {
  const localF = frame - T_COLOR * fps;
  const totalF = (T_COUNT - T_COLOR) * fps;
  const t = localF / totalF; // 0→1 across whole section

  // Hue cycles 1.5× through rainbow
  const hue = (t * 540) % 360;
  const color = hslToHex(hue, 75, 55);
  const bgColor = hslToHex((hue + 180) % 360, 30, 90); // complementary bg

  const pulse = 1 + Math.sin(localF / (fps * 1.2)) * 0.06;

  // Slow gentle spin for variety
  const rotation = (localF / fps) * 3; // 3°/s

  return (
    <AbsoluteFill style={{ backgroundColor: bgColor, display: "flex", alignItems: "center", justifyContent: "center", transition: "background 0.5s" }}>
      <div style={{ transform: `scale(${pulse}) rotate(${rotation}deg)` }}>
        <Shape name={shapeName} size={360} color={color} />
      </div>

      {/* Color rings spreading out */}
      {[1, 2, 3].map((ring) => {
        const ringAlpha = interpolate(
          Math.sin((localF / fps + ring * 0.8) * 0.5),
          [-1, 1], [0.05, 0.18]
        );
        return (
          <div key={ring} style={{
            position: "absolute",
            width: 360 + ring * 160,
            height: 360 + ring * 160,
            borderRadius: "50%",
            border: `${8 - ring}px solid ${color}`,
            opacity: ringAlpha,
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
          }} />
        );
      })}
    </AbsoluteFill>
  );
};

// ── COUNT: visual 1 → 2 → 3 with dot patterns ────────────────────────────────
const COUNT_CYCLE = 45; // seconds per count cycle (1→2→3)

const DotPattern: React.FC<{ count: number; color: string; size: number }> = ({ count, color, size }) => {
  // Arrange dots in pleasant grid
  const positions: Array<{ x: number; y: number }> = count === 1
    ? [{ x: 0, y: 0 }]
    : count === 2
    ? [{ x: -size * 0.6, y: 0 }, { x: size * 0.6, y: 0 }]
    : [{ x: 0, y: -size * 0.6 }, { x: -size * 0.6, y: size * 0.4 }, { x: size * 0.6, y: size * 0.4 }];

  return (
    <>
      {positions.map((p, i) => (
        <div key={i} style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: `translate(calc(-50% + ${p.x}px), calc(-50% + ${p.y}px))`,
        }}>
          <Shape name="circle" size={size * 0.18} color={color} />
        </div>
      ))}
    </>
  );
};

const CountSection: React.FC<{
  shapeName: ShapeName; color: string; bg: string;
  frame: number; fps: number;
}> = ({ shapeName, color, bg, frame, fps }) => {
  const localF = frame - T_COUNT * fps;
  const cycleF = fps * COUNT_CYCLE;
  const f = localF % cycleF;
  const t = f / cycleF; // 0→1 within cycle

  // Which count to show: 1 for first third, 2 for second, 3 for last
  const count = t < 0.33 ? 1 : t < 0.66 ? 2 : 3;

  const prevCount = t < 0.33 ? 0 : t < 0.66 ? 1 : 2;
  const phaseStart = t < 0.33 ? 0 : t < 0.66 ? 0.33 : 0.66;
  const phaseT = (t - phaseStart) / 0.33;

  const shapes: Array<{ x: number; y: number }> =
    count === 1 ? [{ x: 0, y: 0 }]
    : count === 2 ? [{ x: -280, y: 0 }, { x: 280, y: 0 }]
    : [{ x: 0, y: -200 }, { x: -280, y: 180 }, { x: 280, y: 180 }];

  // Light bg
  const [h, s, l] = hexToHSL(bg);
  const countBg = hslToHex(h, s * 0.4, Math.min(l + 8, 96));

  // Idle animation for placed shapes — always moving
  const fSecCount = f / fps;

  return (
    <AbsoluteFill style={{ backgroundColor: countBg, display: "flex", alignItems: "center", justifyContent: "center" }}>
      {shapes.map((pos, i) => {
        const isNew = i >= prevCount;
        const entryF = isNew ? Math.max(0, (phaseT - 0.1 * i) * fps * COUNT_CYCLE * 0.33) : fps * 2;
        const entrySpring = spring({ frame: entryF, fps, config: { damping: 10, stiffness: 120 }, durationInFrames: fps * 1.2 });
        const sc        = interpolate(entrySpring, [0, 1], [0.1, 1], { extrapolateRight: "clamp" });
        const idlePulse = 1 + Math.abs(Math.sin(fSecCount * 1.5 + i * 0.8)) * 0.09;
        const idleFloat = Math.sin(fSecCount * 1.2 + i * 1.0) * 16;
        return (
          <div key={i} style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: `translate(calc(-50% + ${pos.x}px), calc(-50% + ${pos.y + idleFloat}px)) scale(${sc * idlePulse})`,
          }}>
            <Shape name={shapeName} size={300} color={color} />
          </div>
        );
      })}

      {/* Dot counter bottom bar */}
      <div style={{ position: "absolute", bottom: "8%", left: 0, right: 0, display: "flex", justifyContent: "center", gap: 20 }}>
        {[1, 2, 3].map((n) => (
          <div key={n} style={{
            width: 40, height: 40, borderRadius: "50%",
            backgroundColor: n <= count ? color : "rgba(0,0,0,0.12)",
            transition: "background 0.3s",
            boxShadow: n <= count ? `0 0 12px ${color}` : "none",
          }} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ── HYPNO: multi-shape float with hue drift ───────────────────────────────────
interface HypnoFloater {
  seed: number;
  size: number;
  baseX: number;
  baseY: number;
  speed: number;
  hueOffset: number;
}

function seededRand(seed: number): number {
  const x = Math.sin(seed + 1) * 10000;
  return x - Math.floor(x);
}

const HypnoSection: React.FC<{
  shapeName: ShapeName; bg: string; frame: number; fps: number;
}> = ({ shapeName, bg, frame, fps }) => {
  const localF = frame - T_HYPNO * fps;
  const { width, height } = { width: 1920, height: 1080 };

  const floaters: HypnoFloater[] = Array.from({ length: 12 }, (_, i) => ({
    seed: i + 1,
    size: 100 + seededRand(i * 7) * 180,
    baseX: seededRand(i * 13) * (width - 200) + 100,
    baseY: seededRand(i * 17) * (height - 200) + 100,
    speed: 80 + seededRand(i * 11) * 120,
    hueOffset: seededRand(i * 19) * 360,
  }));

  // Overall hue slowly drifts
  const globalHue = (localF / fps) * 4; // 4°/s

  const fadeIn = interpolate(localF, [0, fps * 3], [0, 1], { extrapolateRight: "clamp" });
  const [h, s, l] = hexToHSL(bg);
  const hypnoBg = hslToHex((h + globalHue * 0.3) % 360, s * 0.5, Math.max(l - 5, 80));

  return (
    <AbsoluteFill style={{ backgroundColor: hypnoBg, opacity: fadeIn }}>
      {floaters.map((fl) => {
        const hue = (globalHue + fl.hueOffset) % 360;
        const color = hslToHex(hue, 70, 55);
        const x = fl.baseX + Math.sin((localF / fl.speed) + fl.seed) * 70;
        const y = fl.baseY + Math.cos((localF / fl.speed * 0.8) + fl.seed * 2) * 50;
        const scale = 1 + Math.sin((localF / fl.speed * 1.3) + fl.seed * 3) * 0.15;
        const opacity = 0.45 + seededRand(fl.seed * 5) * 0.4;

        return (
          <div key={fl.seed} style={{
            position: "absolute",
            left: x - fl.size / 2,
            top: y - fl.size / 2,
            transform: `scale(${scale})`,
            opacity,
          }}>
            <Shape name={shapeName} size={fl.size} color={color} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ── OUTRO: single shape pulses, fades ─────────────────────────────────────────
const OutroSection: React.FC<{
  shapeName: ShapeName; color: string; bg: string;
  frame: number; fps: number;
}> = ({ shapeName, color, bg, frame, fps }) => {
  const localF = frame - T_OUTRO * fps;
  const totalF = (T_END - T_OUTRO) * fps;
  const fadeOut = interpolate(localF, [0, totalF * 0.7, totalF], [1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pulse = 1 + Math.sin(localF / (fps * 1.5)) * 0.05;

  return (
    <AbsoluteFill style={{ backgroundColor: bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ transform: `scale(${pulse})`, opacity: fadeOut }}>
        <Shape name={shapeName} size={320} color={color} />
      </div>
    </AbsoluteFill>
  );
};

// ── MAIN ─────────────────────────────────────────────────────────────────────
export const ShapeLearnLong: React.FC<ShapeLearnLongProps> = ({
  shapeName, shapeColor, bgColor, musicFile,
}) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  const sec = frame / fps;

  const section =
    sec < T_FORM   ? "intro"  :
    sec < T_COLOR  ? "form"   :
    sec < T_COUNT  ? "color"  :
    sec < T_HYPNO  ? "count"  :
    sec < T_OUTRO  ? "hypno"  : "outro";

  return (
    <AbsoluteFill>
      {/* Continuous background music (loop) */}
      {musicFile && (
        <Audio src={staticFile(`music/${musicFile}`)} volume={0.20} loop />
      )}

      {section === "intro" && (
        <IntroSection shapeName={shapeName} color={shapeColor} bg={bgColor} frame={frame} fps={fps} />
      )}
      {section === "form" && (
        <FormSection shapeName={shapeName} color={shapeColor} bg={bgColor} frame={frame} fps={fps} />
      )}
      {section === "color" && (
        <ColorSection shapeName={shapeName} baseColor={shapeColor} bg={bgColor} frame={frame} fps={fps} />
      )}
      {section === "count" && (
        <CountSection shapeName={shapeName} color={shapeColor} bg={bgColor} frame={frame} fps={fps} />
      )}
      {section === "hypno" && (
        <HypnoSection shapeName={shapeName} bg={bgColor} frame={frame} fps={fps} />
      )}
      {section === "outro" && (
        <OutroSection shapeName={shapeName} color={shapeColor} bg={bgColor} frame={frame} fps={fps} />
      )}

      {/* Subtle brand watermark */}
      <div style={{
        position: "absolute", bottom: "1.5%", right: "2%",
        opacity: 0.25, pointerEvents: "none",
      }}>
        <span style={{ fontFamily: "Arial, sans-serif", fontSize: 32, color: shapeColor, fontWeight: 700 }}>
          Happy Bear Kids
        </span>
      </div>
    </AbsoluteFill>
  );
};
