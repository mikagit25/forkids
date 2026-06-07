import React from "react";

export type ShapeName =
  | "circle" | "square" | "triangle" | "star"
  | "diamond" | "heart" | "hexagon" | "oval";

const CLIP_PATHS: Record<ShapeName, string | null> = {
  circle:   null, // handled via borderRadius
  oval:     null,
  square:   null,
  triangle: "polygon(50% 0%, 0% 100%, 100% 100%)",
  star:     "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)",
  diamond:  "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)",
  heart:    "path('M 50 85 C 10 55 0 35 0 25 C 0 5 15 0 25 0 C 35 0 45 8 50 18 C 55 8 65 0 75 0 C 85 0 100 5 100 25 C 100 35 90 55 50 85 Z')",
  hexagon:  "polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)",
};

interface ShapeProps {
  name: ShapeName;
  size: number;        // px
  color: string;       // hex
  opacity?: number;
  style?: React.CSSProperties;
}

export const Shape: React.FC<ShapeProps> = ({
  name, size, color, opacity = 1, style = {}
}) => {
  const clip = CLIP_PATHS[name];

  const base: React.CSSProperties = {
    width: name === "oval" ? size * 1.4 : size,
    height: size,
    backgroundColor: color,
    opacity,
    flexShrink: 0,
    ...style,
  };

  if (name === "circle") {
    return <div style={{ ...base, borderRadius: "50%" }} />;
  }
  if (name === "oval") {
    return <div style={{ ...base, borderRadius: "50%" }} />;
  }
  if (name === "square") {
    return <div style={{ ...base, borderRadius: size * 0.08 }} />;
  }
  if (name === "heart") {
    // SVG-based heart for better shape
    return (
      <svg width={size} height={size} viewBox="0 0 100 90" style={{ opacity, flexShrink: 0, ...style }}>
        <path
          d="M 50 85 C 10 55 0 35 0 25 C 0 5 15 0 25 0 C 35 0 45 10 50 20 C 55 10 65 0 75 0 C 85 0 100 5 100 25 C 100 35 90 55 50 85 Z"
          fill={color}
        />
      </svg>
    );
  }

  return (
    <div
      style={{
        ...base,
        clipPath: clip ?? undefined,
        WebkitClipPath: clip ?? undefined,
      }}
    />
  );
};

// Human-readable display names
export const SHAPE_LABELS: Record<ShapeName, string> = {
  circle:   "CIRCLE",
  oval:     "OVAL",
  square:   "SQUARE",
  triangle: "TRIANGLE",
  star:     "STAR",
  diamond:  "DIAMOND",
  heart:    "HEART",
  hexagon:  "HEXAGON",
};
