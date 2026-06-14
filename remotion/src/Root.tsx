import React from "react";
import { Composition } from "remotion";
import { VocabularyShort, VocabularyShortProps } from "./VocabularyShort";
import { ShapeFloat, ShapeFloatProps } from "./ShapeFloat";
import { ShapeDance, ShapeDanceProps } from "./ShapeDance";
import { ColorLearn, ColorLearnProps } from "./ColorLearn";
import { ColorLearnLong, ColorLearnLongProps } from "./ColorLearnLong";
import { DanceSpriteShort, DanceSpriteShortProps } from "./DanceSpriteShort";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const C = Composition as React.ComponentType<any>;

const FPS = 30;
const SHORT_DUR = 55;   // seconds
const LONG_DUR  = 1800; // 30 minutes

// ── VocabularyShort (A-Z) ────────────────────────────────────────────────────
const defaultVocabProps: VocabularyShortProps = {
  letter: "A",
  word: "APPLE",
  spritePath: "fruits/apple.png",
  audioFile: "a__apple__a_is_for_apple.mp3",
  letterColor: "#E53935",
  bgColor: "#E8F5E9",
};

// ── ShapeFloat ───────────────────────────────────────────────────────────────
const defaultFloatProps: ShapeFloatProps = {
  shapeName: "circle",
  shapeColor: "#2980B9",
  bgColor: "#E3F2FD",
  mode: "tb",
  count: 6,
  showLabel: true,
  audioFile: "circle__this_is_a_circle__a_circle.mp3",
  musicFile: "Carefree.mp3",
  speed: "slow",
};

// ── ShapeDance ───────────────────────────────────────────────────────────────
const defaultDanceProps: ShapeDanceProps = {
  shapes: ["circle", "square", "triangle"],
  colors: ["#FF4444", "#27AE60", "#2980B9"],
  bgColor: "#FFFDE7",
  bpm: 110,
  showLabels: true,
  audioFile: null,
  musicFile: "Quirky Dog.mp3",
};

// ── ColorLearn ───────────────────────────────────────────────────────────────
const defaultColorProps: ColorLearnProps = {
  colorName: "RED",
  colorHex: "#FF4444",
  bgColor: "#FFF5F5",
  audioFile: "red__red__can_you_find_something_red.mp3",
  musicFile: "Happy Happy Game Show.mp3",
};

export const Root: React.FC = () => {
  return (
    <>
      {/* Short compositions (55s) */}
      <C
        id="VocabularyShort"
        component={VocabularyShort}
        durationInFrames={FPS * SHORT_DUR}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={defaultVocabProps}
      />
      <C
        id="ShapeFloatShort"
        component={ShapeFloat}
        durationInFrames={FPS * SHORT_DUR}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={defaultFloatProps}
      />
      <C
        id="ShapeDanceShort"
        component={ShapeDance}
        durationInFrames={FPS * SHORT_DUR}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={defaultDanceProps}
      />
      <C
        id="ColorLearnShort"
        component={ColorLearn}
        durationInFrames={FPS * SHORT_DUR}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={defaultColorProps}
      />

      {/* DanceSpriteShort — animated character dance (animals/fruits/vegetables) */}
      <C
        id="DanceSpriteShort"
        component={DanceSpriteShort}
        durationInFrames={FPS * SHORT_DUR}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          spritePath: "animals/bear.png",
          characterName: "Bear",
          audioFile: null,
          musicFile: "Carefree.mp3",
          bgColor: "#FFF9E6",
          accentColor: "#E67E22",
        } as DanceSpriteShortProps}
      />

      {/* ColorLearnLong — 20-min "One Concept Deep" landscape */}
      <C
        id="ColorLearnLong"
        component={ColorLearnLong}
        durationInFrames={FPS * 1200}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          colorName: "RED",
          colorHex: "#E53935",
          bgColor: "#FFF5F5",
          rtl: false,
          lang: "en",
          colorKey: "red",
          musicFile: "Happy Happy Game Show.mp3",
          objects: [
            { name: "strawberry", nameLocalized: "Strawberry", spritePath: "fruits/strawberry.png" },
            { name: "apple",      nameLocalized: "Apple",      spritePath: "fruits/apple.png" },
            { name: "tomato",     nameLocalized: "Tomato",     spritePath: "vegetables/tomato.png" },
          ],
        } as ColorLearnLongProps}
      />

      {/* Long compositions (30 min, landscape) */}
      <C
        id="ShapeFloatLong"
        component={ShapeFloat}
        durationInFrames={FPS * LONG_DUR}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ ...defaultFloatProps, count: 10, speed: "slow" }}
      />
      <C
        id="ShapeDanceLong"
        component={ShapeDance}
        durationInFrames={FPS * LONG_DUR}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          ...defaultDanceProps,
          shapes: ["circle", "square", "triangle", "star"],
          colors: ["#FF4444", "#27AE60", "#2980B9", "#F9A825"],
        }}
      />
    </>
  );
};
