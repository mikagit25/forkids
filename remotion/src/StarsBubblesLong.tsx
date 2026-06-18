/**
 * StarsBubblesLong — 22-min abstract sensory video.
 * Floating transparent bubbles + twinkling / shooting stars.
 * No text, no sprites — pure procedural SVG / CSS animation.
 * Universal: EN + AR + ID channels.
 */
import React, { useMemo } from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface StarsBubblesSegment {
  startSec: number;
  endSec: number;
  mode: "intro" | "bubbles" | "stars" | "calm" | "both" | "finale";
  bubbleCount?: number;   // concurrent bubbles (default by mode)
  starCount?: number;     // twinkling stars visible (default by mode)
  shootRate?: number;     // shooting stars per minute; 0 = none
  bgColor?: string;       // optional per-segment bg override
}

export interface StarsBubblesLongProps {
  bgColor: string;
  musicFile: string;
  volume?: number;
  segments: StarsBubblesSegment[];
  seed?: number;
}

// ── Constants ─────────────────────────────────────────────────────────────────

type RGB = [number, number, number];

const BUBBLE_RGB: RGB[] = [
  [255, 192, 210],  // soft pink
  [180, 220, 245],  // ice blue
  [255, 255, 185],  // soft yellow
  [170, 240, 195],  // mint
  [225, 185, 245],  // lavender
  [215, 240, 255],  // near-white blue
];

const STAR_COLORS = [
  "#FFD700", "#FFFFFF", "#FFB6C1", "#87CEEB", "#E2D0FF", "#B0FFD0",
];

const N_BUBBLE = 50;
const N_STAR   = 30;

const MODE_BUBBLES: Record<string, number> = {
  intro: 1, bubbles: 22, stars: 2, calm: 5, both: 13, finale: 38,
};
const MODE_STARS: Record<string, number> = {
  intro: 4, bubbles: 5, stars: 24, calm: 8, both: 16, finale: 28,
};
const MODE_SHOOT: Record<string, number> = {
  intro: 0, bubbles: 0, stars: 8, calm: 1, both: 4, finale: 12,
};

// ── Seeded RNG ─────────────────────────────────────────────────────────────────

function lcgN(seed: number, n: number): number[] {
  const out: number[] = [];
  let s = ((Math.abs(seed) * 2654435761) ^ 0xDEAD1234) >>> 0;
  for (let i = 0; i < n; i++) {
    s = ((s * 1664525 + 1013904223) & 0xFFFFFFFF) >>> 0;
    out.push(s / 0xFFFFFFFF);
  }
  return out;
}

// ── Slot definitions ──────────────────────────────────────────────────────────

interface BubbleSlot {
  baseX: number;         // 0–1 screen
  radius: number;        // px
  rgb: RGB;
  swayAmp: number;       // px
  swayPeriod: number;    // s
  riseDuration: number;  // s from bottom to top
  phaseShift: number;    // 0–1 fraction of riseDuration as start offset
  popFrac: number;       // 0–1 when it pops mid-rise
  hiX: number; hiY: number; // highlight position 0–1
}

interface StarSlot {
  x: number; y: number;  // 0–1 screen
  size: number;          // outer radius px
  color: string;
  period: number;        // twinkle period s
  phase: number;         // phase offset radians
}

interface ShootEvent {
  startSec: number;
  fromX: number; fromY: number;  // 0–1 (can be slightly outside)
  angle: number;                 // radians travel direction
  duration: number;              // s
  speed: number;                 // px/s
  color: string;
  size: number;                  // head radius px
}

// ── Builders ──────────────────────────────────────────────────────────────────

function buildBubbles(seed: number): BubbleSlot[] {
  return Array.from({ length: N_BUBBLE }, (_, i) => {
    const r = lcgN(seed * 41 + i * 997, 11);
    return {
      baseX:        0.04 + r[0] * 0.92,
      radius:       22   + r[1] * 58,
      rgb:          BUBBLE_RGB[Math.floor(r[5] * BUBBLE_RGB.length)],
      swayAmp:      12   + r[2] * 42,
      swayPeriod:   3    + r[3] * 5,
      riseDuration: 9    + r[4] * 8,
      phaseShift:   r[6],
      popFrac:      0.20 + r[7] * 0.60,
      hiX:          0.22 + r[8] * 0.22,
      hiY:          0.18 + r[9] * 0.18,
    };
  });
}

function buildStars(seed: number): StarSlot[] {
  return Array.from({ length: N_STAR }, (_, i) => {
    const r = lcgN(seed * 67 + i * 1117, 6);
    return {
      x:      0.02 + r[0] * 0.96,
      y:      0.02 + r[1] * 0.96,
      size:   5    + r[2] * 15,
      color:  STAR_COLORS[Math.floor(r[3] * STAR_COLORS.length)],
      period: 1.5  + r[4] * 2.5,
      phase:  r[5] * Math.PI * 2,
    };
  });
}

function buildShootEvents(seed: number, segs: StarsBubblesSegment[]): ShootEvent[] {
  const events: ShootEvent[] = [];
  let idx = 0;
  for (const seg of segs) {
    const rate = seg.shootRate ?? MODE_SHOOT[seg.mode] ?? 0;
    if (rate <= 0) continue;
    const interval = 60 / rate;
    let t = seg.startSec + interval * 0.4;
    while (t + 1.5 < seg.endSec) {
      const r = lcgN(seed * 89 + idx * 2333, 8);
      const fromLeft = r[0] > 0.35;
      const fromX    = fromLeft ? -0.05 : 0.04 + r[1] * 0.92;
      const fromY    = fromLeft ? 0.04 + r[0] * 0.92 : -0.05;
      const baseAng  = fromLeft
        ? (-0.45 + r[2] * 0.90)
        : (Math.PI / 2 + (-0.45 + r[2] * 0.90));
      events.push({
        startSec: t,
        fromX, fromY,
        angle:    baseAng,
        duration: 0.55 + r[3] * 0.75,
        speed:    1100 + r[4] * 900,
        color:    STAR_COLORS[Math.floor(r[5] * STAR_COLORS.length)],
        size:     4    + r[6] * 7,
      });
      t += interval * (0.75 + r[7] * 0.5);
      idx++;
    }
  }
  return events;
}

// ── Star path ──────────────────────────────────────────────────────────────────

function starPath(cx: number, cy: number, r: number): string {
  const inner = r * 0.42;
  const pts: string[] = [];
  for (let i = 0; i < 10; i++) {
    const a  = (i * Math.PI) / 5 - Math.PI / 2;
    const rr = i % 2 === 0 ? r : inner;
    pts.push(`${cx + rr * Math.cos(a)},${cy + rr * Math.sin(a)}`);
  }
  return `M${pts.join("L")}Z`;
}

// ── Segment helpers ────────────────────────────────────────────────────────────

function findSeg(fSec: number, segs: StarsBubblesSegment[]): StarsBubblesSegment {
  return (
    [...segs].reverse().find((s) => fSec >= s.startSec && fSec < s.endSec) ??
    segs[segs.length - 1]
  );
}

function findPrevSeg(
  fSec: number,
  segs: StarsBubblesSegment[],
): StarsBubblesSegment | null {
  const cur = findSeg(fSec, segs);
  const curIdx = segs.indexOf(cur);
  return curIdx > 0 ? segs[curIdx - 1] : null;
}

function segBubbles(seg: StarsBubblesSegment | null): number {
  if (!seg) return 0;
  return seg.bubbleCount ?? MODE_BUBBLES[seg.mode] ?? 10;
}

function segStars(seg: StarsBubblesSegment | null): number {
  if (!seg) return 0;
  return seg.starCount ?? MODE_STARS[seg.mode] ?? 8;
}

// ── Component ──────────────────────────────────────────────────────────────────

export const StarsBubblesLong: React.FC<StarsBubblesLongProps> = ({
  bgColor,
  musicFile,
  volume = 0.18,
  segments,
  seed = 42,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const fSec = frame / fps;

  const bubbleSlots = useMemo(() => buildBubbles(seed), [seed]);
  const starSlots   = useMemo(() => buildStars(seed), [seed]);
  const shootEvents = useMemo(() => buildShootEvents(seed, segments), [seed, segments]);

  const seg      = findSeg(fSec, segments);
  const prevSeg  = findPrevSeg(fSec, segments);
  const transitionP = interpolate(fSec, [seg.startSec, seg.startSec + 3], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  // Smooth count transitions (3 s ramp)
  const targetBubbles = segBubbles(seg);
  const prevBubbles   = segBubbles(prevSeg) || targetBubbles;
  const smoothBubbles = prevBubbles + (targetBubbles - prevBubbles) * transitionP;

  const targetStars  = segStars(seg);
  const prevStars    = segStars(prevSeg) || targetStars;
  const smoothStars  = prevStars + (targetStars - prevStars) * transitionP;

  // Global envelope
  const fadeIn  = interpolate(fSec, [0, 2], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [durationInFrames - fps * 4, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const globalOp = fadeIn * fadeOut;

  const currentBg = seg.bgColor ?? bgColor;

  // ── Bubbles ─────────────────────────────────────────────────────────────────
  const bubbleEls = bubbleSlots.map((slot, i) => {
    // slot opacity: 0 if far beyond smoothBubbles, 1 if clearly within
    const slotOp = interpolate(i, [smoothBubbles - 1.5, smoothBubbles + 1.5], [1, 0], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });
    if (slotOp <= 0.01) return null;

    // Rise progress within current cycle
    const tShifted = fSec - slot.phaseShift * slot.riseDuration;
    const progress = ((tShifted % slot.riseDuration) + slot.riseDuration) % slot.riseDuration / slot.riseDuration;
    const visible  = progress < slot.popFrac;

    // Pop ring: brief expanding ring just after pop
    const timeSincePop = (progress - slot.popFrac) * slot.riseDuration;
    const ringActive   = !visible && timeSincePop >= 0 && timeSincePop < 0.60;
    const ringT        = timeSincePop; // 0..0.60 s

    // Position
    const riseY = 1.08 - progress * 1.18;   // bottom off-screen → top off-screen
    const sway  = Math.sin((fSec / slot.swayPeriod) * Math.PI * 2 + i * 0.73) * slot.swayAmp;
    const cx    = slot.baseX * width + sway;
    const cy    = riseY * height;
    const r     = slot.radius;
    const [rr, gg, bb] = slot.rgb;

    return (
      <React.Fragment key={i}>
        {visible && (
          <div
            style={{
              position: "absolute",
              width:  r * 2,
              height: r * 2,
              left:   cx - r,
              top:    cy - r,
              borderRadius: "50%",
              opacity: slotOp,
              background: `radial-gradient(circle at ${slot.hiX * 100}% ${slot.hiY * 100}%,
                rgba(${rr},${gg},${bb},0.60) 0%,
                rgba(${rr},${gg},${bb},0.18) 38%,
                rgba(${rr},${gg},${bb},0.07) 66%,
                transparent 100%)`,
              border: `1.5px solid rgba(${rr},${gg},${bb},0.38)`,
              boxShadow: `inset 0 0 ${r * 0.45}px rgba(255,255,255,0.09),
                          0 0 ${r * 0.18}px rgba(${rr},${gg},${bb},0.14)`,
            }}
          >
            {/* Main highlight */}
            <div style={{
              position: "absolute",
              width: "19%", height: "12%",
              left: `${slot.hiX * 90}%`, top: `${slot.hiY * 95}%`,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.72)",
              transform: "rotate(-28deg)",
            }} />
            {/* Secondary tiny highlight */}
            <div style={{
              position: "absolute",
              width: "7%", height: "5%",
              left: "62%", top: "20%",
              borderRadius: "50%",
              background: "rgba(255,255,255,0.45)",
            }} />
          </div>
        )}
        {ringActive && (() => {
          const rp  = Math.min(ringT / 0.60, 1);
          const rR  = r * (1 + rp * 1.5);
          const rop = slotOp * (1 - rp) * 0.85;
          const rw  = Math.max(0.5, r * 0.10 * (1 - rp));
          return (
            <div style={{
              position: "absolute",
              width:  rR * 2, height: rR * 2,
              left:   cx - rR, top: cy - rR,
              borderRadius: "50%",
              border: `${rw}px solid rgba(${rr},${gg},${bb},${rop})`,
              pointerEvents: "none",
            }} />
          );
        })()}
      </React.Fragment>
    );
  });

  // ── Twinkling stars ────────────────────────────────────────────────────────
  const twinklePaths = starSlots.map((star, i) => {
    const starOp = interpolate(i, [smoothStars - 1.5, smoothStars + 1.5], [1, 0], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });
    if (starOp <= 0.01) return null;
    const tw = 0.38 + 0.62 * (0.5 + 0.5 * Math.sin(
      (fSec / star.period) * Math.PI * 2 + star.phase,
    ));
    return (
      <path
        key={i}
        d={starPath(star.x * width, star.y * height, star.size)}
        fill={star.color}
        opacity={tw * starOp}
      />
    );
  });

  // ── Shooting stars ─────────────────────────────────────────────────────────
  const shootEls = shootEvents
    .filter((evt) => fSec >= evt.startSec - 0.05 && fSec < evt.startSec + evt.duration + 0.3)
    .map((evt, i) => {
      const elapsed  = fSec - evt.startSec;
      if (elapsed < 0) return null;
      const progress = elapsed / evt.duration;
      const fade     =
        progress < 0.10 ? progress * 10 :
        progress > 0.80 ? (1 - progress) / 0.20 : 1;
      const distPx   = evt.speed * Math.min(elapsed, evt.duration);
      const dx       = Math.cos(evt.angle);
      const dy       = Math.sin(evt.angle);
      const hx       = evt.fromX * width  + dx * distPx;
      const hy       = evt.fromY * height + dy * distPx;
      const trailLen = Math.min(200 + evt.size * 12, distPx);
      const tx       = hx - dx * trailLen;
      const ty       = hy - dy * trailLen;
      const gid      = `sbsg${i}_${Math.round(evt.startSec * 10)}`;
      return (
        <g key={gid} opacity={fade}>
          <defs>
            <linearGradient id={gid} x1={tx} y1={ty} x2={hx} y2={hy} gradientUnits="userSpaceOnUse">
              <stop offset="0%"   stopColor={evt.color} stopOpacity="0" />
              <stop offset="100%" stopColor={evt.color} stopOpacity="0.92" />
            </linearGradient>
          </defs>
          <line
            x1={tx} y1={ty} x2={hx} y2={hy}
            stroke={`url(#${gid})`}
            strokeWidth={evt.size * 0.75}
            strokeLinecap="round"
          />
          <circle cx={hx} cy={hy} r={evt.size}       fill={evt.color} opacity={0.95} />
          <circle cx={hx} cy={hy} r={evt.size * 2.8} fill={evt.color} opacity={0.15} />
        </g>
      );
    });

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <AbsoluteFill style={{ backgroundColor: currentBg }}>
      <Audio src={staticFile(`music/${musicFile}`)} volume={volume} loop />

      <AbsoluteFill style={{ opacity: globalOp }}>
        {/* Stars + shooting stars layer (SVG) */}
        <svg
          style={{ position: "absolute", left: 0, top: 0, width: "100%", height: "100%", overflow: "visible" }}
          viewBox={`0 0 ${width} ${height}`}
        >
          {twinklePaths}
          {shootEls}
        </svg>

        {/* Bubbles layer (CSS divs) */}
        {bubbleEls}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
