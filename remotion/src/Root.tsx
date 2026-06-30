import React from "react";
import { Composition } from "remotion";
import { VocabularyShort, VocabularyShortProps } from "./VocabularyShort";
import { ShapeFloat, ShapeFloatProps } from "./ShapeFloat";
import { ShapeDance, ShapeDanceProps } from "./ShapeDance";
import { ColorLearn, ColorLearnProps } from "./ColorLearn";
import { ColorLearnLong, ColorLearnLongProps } from "./ColorLearnLong";
import { NumberLearnLong, NumberLearnLongProps } from "./NumberLearnLong";
import { DanceSpriteShort, DanceSpriteShortProps } from "./DanceSpriteShort";
import { ShapeLearnLong, ShapeLearnLongProps } from "./ShapeLearnLong";
import { NurseryRhymeLong, NurseryRhymeLongProps } from "./NurseryRhymeLong";
import { LullabyLoop, LullabyLoopProps } from "./LullabyLoop";
import { CharacterDialogueLong, CharacterDialogueLongProps } from "./CharacterDialogueLong";
import { DanceShapeLong, DanceShapeLongProps } from "./DanceShapeLong";
import { DanceSpriteLong, DanceSpriteLongProps } from "./DanceSpriteLong";
import { StarsBubblesLong, StarsBubblesLongProps } from "./StarsBubblesLong";
import { TransformLong, TransformLongProps } from "./TransformLong";
import { ShapeLearnLong2, ShapeLearnLong2Props } from "./ShapeLearnLong2";
import { SensoryLoop, SensoryLoopProps } from "./SensoryLoop";
import { NatureCalm, NatureCalmProps } from "./NatureCalm";
import { OCDVehicles, OCDVehiclesProps } from "./OCDVehicles";
import { PeekABoo, PeekABooProps } from "./PeekABoo";
import { FactoryTransform, FactoryTransformProps } from "./FactoryTransform";
import { PuzzleAssembly, PuzzleAssemblyProps } from "./PuzzleAssembly";
import { PeekABooEggs, PeekABooEggsProps } from "./PeekABooEggs";
import { NeonCarWash, NeonCarWashProps } from "./NeonCarWash";
import { DinoBuild, DinoBuildProps } from "./DinoBuild";

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
  musicFile: "Wholesome.mp3",
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

      {/* NumberLearnLong — 20-min "One Concept Deep" number 1-10 */}
      <C
        id="NumberLearnLong"
        component={NumberLearnLong}
        durationInFrames={FPS * 1200}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          numberValue: 3,
          numberName: "THREE",
          numberDigit: "3",
          accentColor: "#43A047",
          bgColor: "#E8F5E9",
          rtl: false,
          lang: "en",
          numberKey: "three",
          musicFile: "Happy Happy Game Show.mp3",
          objects: [
            { name: "apple",  nameLocalized: "Apple",  pluralLocalized: "Apples",  spritePath: "fruits/apple.png" },
            { name: "star",   nameLocalized: "Star",   pluralLocalized: "Stars",   spritePath: "objects/star.png" },
            { name: "duck",   nameLocalized: "Duck",   pluralLocalized: "Ducks",   spritePath: "animals/duck.png" },
          ],
        } as NumberLearnLongProps}
      />

      {/* ShapeLearnLong — 30-min "One Concept Deep" shape learning, no text, universal */}
      <C
        id="ShapeLearnLong"
        component={ShapeLearnLong}
        durationInFrames={FPS * LONG_DUR}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          shapeName: "circle",
          shapeColor: "#2980B9",
          bgColor: "#E3F2FD",
          musicFile: "Carefree.mp3",
        } as ShapeLearnLongProps}
      />

      {/* NurseryRhymeLong — Arabic/Indonesian nursery rhyme, 20-25 min */}
      <C
        id="NurseryRhymeLong"
        component={NurseryRhymeLong}
        durationInFrames={FPS * 1380}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          segments: [
            { arabic: "بتة بتة بتة", english: "Duck, duck, duck", startFrame: 0, durationFrames: 90 },
          ],
          characterSprite: "animals_flux/duck.png",
          bgColorTop: "#87CEEB",
          bgColorBottom: "#90EE90",
          accentColor: "#FFD700",
          musicFile: "Carefree.mp3",
          titleArabic: "بتة بتة",
          titleEnglish: "Batta Batta",
        } as NurseryRhymeLongProps}
      />

      {/* LullabyLoop — 5-min seamless sleep loop (extended to 1-2h via FFmpeg) */}
      <C
        id="LullabyLoop"
        component={LullabyLoop}
        durationInFrames={FPS * 300}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          theme: "stars",
          bgColorTop: "#020815",
          bgColorBottom: "#050A1A",
          accentColor: "#B0C4DE",
          musicFile: "Gymnopedie No 1.mp3",
          bpm: 50,
        } as LullabyLoopProps}
      />

      {/* CharacterDialogueLong — 20-min bear character educational dialogue */}
      <C
        id="CharacterDialogueLong"
        component={CharacterDialogueLong}
        durationInFrames={FPS * 1200}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          episodeKey: "emotions_happy",
          episodeTitle: "Feelings with Roundy",
          characterSprite: "sprites/characters/bear_happy_3d.png",
          accentColor: "#FF6B35",
          bgColor: "#FFF8F0",
          rtl: false,
          lang: "en",
          musicFile: "Carefree.mp3",
          audioBase: "audio/character_dialogue/en/emotions_happy",
          scenes: [
            { id: "happy",   title: "Happy",   titleLocalized: "Happy",   spritePath: "emotions/happy_3d.png",   bgColor: "#FFD700" },
            { id: "sad",     title: "Sad",     titleLocalized: "Sad",     spritePath: "emotions/sad_3d.png",     bgColor: "#64B5F6" },
            { id: "angry",   title: "Angry",   titleLocalized: "Angry",   spritePath: "emotions/angry_3d.png",   bgColor: "#EF5350" },
            { id: "surprised", title: "Surprised", titleLocalized: "Surprised", spritePath: "emotions/surprised_3d.png", bgColor: "#AB47BC" },
          ],
        } as CharacterDialogueLongProps}
      />

      {/* DanceShapeLong — 25 min pure shape dance, no text, universal */}
      <C
        id="DanceShapeLong"
        component={DanceShapeLong}
        durationInFrames={FPS * 1500}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          bgColor: "#0A1628",
          musicFile: "Carefree.mp3",
          shapes: [
            { shape: "circle", color: "#E53935", size: 380, posX: 0.5, posY: 0.42, seed: 1 },
          ],
          blocks: [
            { startSec: 0, endSec: 300, motion: "BOB", period: 3, amplitude: 40,
              colorPalette: ["#E53935", "#FF9800", "#FDD835", "#43A047"], colorCycleSec: 60 },
            { startSec: 300, endSec: 600, motion: "SWAY", period: 4, amplitude: 50,
              colorPalette: ["#43A047", "#1E88E5", "#8E24AA", "#E53935"], colorCycleSec: 60 },
            { startSec: 600, endSec: 900, motion: "SPIN", period: 6 },
            { startSec: 900, endSec: 1200, motion: "PULSE", period: 4, amplitude: 15 },
            { startSec: 1200, endSec: 1500, motion: "DRIFT", period: 8, amplitude: 280 },
          ],
        } as DanceShapeLongProps}
      />

      {/* DanceShapeLong30 — 30 min variant (aquarium/color circles/night videos) */}
      <C
        id="DanceShapeLong30"
        component={DanceShapeLong}
        durationInFrames={FPS * LONG_DUR}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          bgColor: "#040D1A",
          musicFile: "Gymnopedie No 1.mp3",
          shapes: [
            { shape: "circle", color: "#E53935", size: 200, posX: 0.17, posY: 0.28, seed: 1 },
            { shape: "square", color: "#1E88E5", size: 180, posX: 0.5,  posY: 0.22, seed: 2 },
            { shape: "star",   color: "#FDD835", size: 180, posX: 0.83, posY: 0.28, seed: 3 },
          ],
          blocks: [
            { startSec: 0,    endSec: 600,  motion: "FADEIN",  amplitude: 80 },
            { startSec: 600,  endSec: 1200, motion: "DRIFT",   period: 12, amplitude: 140 },
            { startSec: 1200, endSec: 1800, motion: "FADEOUT", amplitude: 80 },
          ],
        } as DanceShapeLongProps}
      />

      {/* DanceSpriteLong — 25 min sprite dance (pets/items), no text, universal */}
      <C
        id="DanceSpriteLong"
        component={DanceSpriteLong}
        durationInFrames={FPS * 1500}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          bgColor: "#E8F5E9",
          accentColor: "#43A047",
          musicFile: "Carefree.mp3",
          sprites: [
            { path: "animals/cat.png", size: 420, posX: 0.5, posY: 0.42, seed: 1 },
          ],
          blocks: [
            { startSec: 0,   endSec: 300,  motion: "BOB",   period: 2.5, amplitude: 45 },
            { startSec: 300, endSec: 600,  motion: "SWAY",  period: 3,   amplitude: 60 },
            { startSec: 600, endSec: 900,  motion: "DRIFT", period: 8,   amplitude: 200 },
            { startSec: 900, endSec: 1200, motion: "BOUNCE", period: 2,  amplitude: 70 },
            { startSec: 1200, endSec: 1500, motion: "ORBIT",
              orbitCenterX: 0.5, orbitCenterY: 0.42 },
          ],
        } as DanceSpriteLongProps}
      />

      {/* DanceSpriteLong30 — 30 min variant */}
      <C
        id="DanceSpriteLong30"
        component={DanceSpriteLong}
        durationInFrames={FPS * LONG_DUR}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          bgColor: "#E8F5E9",
          accentColor: "#43A047",
          musicFile: "Carefree.mp3",
          sprites: [
            { path: "animals/cat.png", size: 420, posX: 0.5, posY: 0.42, seed: 1 },
          ],
          blocks: [
            { startSec: 0,    endSec: 600,  motion: "FADEIN",  amplitude: 80 },
            { startSec: 600,  endSec: 1200, motion: "DRIFT",   period: 10, amplitude: 150 },
            { startSec: 1200, endSec: 1800, motion: "FADEOUT", amplitude: 80 },
          ],
        } as DanceSpriteLongProps}
      />

      {/* TransformLong — 20-min transformation visual series (grow/kaleidoscope/rain/day_night) */}
      <C
        id="TransformLong"
        component={TransformLong}
        durationInFrames={FPS * 1200}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          mode: "grow",
          bgColor: "#0A1628",
          accentColor: "#E53935",
          altColor: "#4CAF50",
          musicFile: "Gymnopedie No 1.mp3",
          volume: 0.18,
          cycleDuration: 150,
          seed: 42,
        } as TransformLongProps}
      />

      {/* StarsBubblesLong — 22-min abstract bubbles + stars, no text, universal */}
      <C
        id="StarsBubblesLong"
        component={StarsBubblesLong}
        durationInFrames={FPS * 1320}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          bgColor: "#030C1A",
          musicFile: "Gymnopedie No 1.mp3",
          volume: 0.18,
          seed: 42,
          segments: [
            { startSec: 0,   endSec: 30,   mode: "intro" },
            { startSec: 30,  endSec: 240,  mode: "bubbles" },
            { startSec: 240, endSec: 420,  mode: "stars" },
            { startSec: 420, endSec: 510,  mode: "calm" },
            { startSec: 510, endSec: 750,  mode: "bubbles" },
            { startSec: 750, endSec: 960,  mode: "both" },
            { startSec: 960, endSec: 1050, mode: "calm" },
            { startSec: 1050, endSec: 1290, mode: "finale" },
            { startSec: 1290, endSec: 1320, mode: "calm" },
          ],
        } as StarsBubblesLongProps}
      />

      {/* ShapeLearnLong2 — 30-min v2 with 3D sprites, DVD bounce, fly-in count 1→5, wobble */}
      <C
        id="ShapeLearnLong2"
        component={ShapeLearnLong2}
        durationInFrames={FPS * LONG_DUR}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          spritePath: "shapes_3d/circle.png",
          shapeColor: "#2980B9",
          bgColor: "#E3F2FD",
          musicFile: "Carefree.mp3",
          musicFile2: "Wholesome.mp3",
        } as ShapeLearnLong2Props}
      />

      {/* SensoryLoop — 5-min calming loop for babies (bubbles/bloom/ocean/galaxy) */}
      <C
        id="SensoryLoop"
        component={SensoryLoop}
        durationInFrames={FPS * 300}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          theme: "bubbles",
          musicFile: "Gymnopedie No 1.mp3",
          phaseOffset: 0,
        } as SensoryLoopProps}
      />

      {/* NatureCalm — 5-min calm nature loop (meadow/sunset/night/underwater) */}
      <C
        id="NatureCalm"
        component={NatureCalm}
        durationInFrames={FPS * 300}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          theme: "meadow",
          musicFile: "Gymnopedie No 1.mp3",
          phaseOffset: 0,
        } as NatureCalmProps}
      />

      {/* OCDVehicles — satisfying vehicles parade, no text, universal */}
      <C
        id="OCDVehicles"
        component={OCDVehicles}
        durationInFrames={FPS * 300}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          theme: "city",
          musicFile: "Pinball Spring.mp3",
          vehiclesPerLane: 5,
          speedMultiplier: 1.0,
        } as OCDVehiclesProps}
      />

      {/* PeekABoo — "Who's hiding?" mechanic, 5 items, loops ≈ 55s */}
      <C
        id="PeekABoo"
        component={PeekABoo}
        durationInFrames={FPS * SHORT_DUR * 4}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          region: "US",
          itemsCount: 5,
          bgColor: "#FFF8E1",
          musicFile: "Happy Happy Game Show.mp3",
        } as PeekABooProps}
      />

      {/* FactoryTransform — B&W → color conveyor belt mechanic */}
      <C
        id="FactoryTransform"
        component={FactoryTransform}
        durationInFrames={FPS * SHORT_DUR * 4}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          region: "US",
          theme: "mixed",
          musicFile: "Pinball Spring.mp3",
          bgColor: "#E8F5E9",
        } as FactoryTransformProps}
      />

      {/* PuzzleAssembly — arc-trajectory pieces snap into silhouette */}
      <C
        id="PuzzleAssembly"
        component={PuzzleAssembly}
        durationInFrames={FPS * SHORT_DUR * 6}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          puzzle: "star",
          musicFile: "Wholesome.mp3",
          loops: 2,
        } as PuzzleAssemblyProps}
      />

      {/* PeekABooEggs — magic egg hatching mechanic (1350f = 45s) */}
      <C
        id="PeekABooEggs"
        component={PeekABooEggs}
        durationInFrames={1350}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          region: "US",
          musicFile: "Happy Happy Game Show.mp3",
          bgColor: "#FFF8F0",
        } as PeekABooEggsProps}
      />

      {/* NeonCarWash — B&W car → colorful through wash gate (1620f = 54s) */}
      <C
        id="NeonCarWash"
        component={NeonCarWash}
        durationInFrames={1620}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          musicFile: "Pinball Spring.mp3",
          bgColor: "#E8F5E9",
        } as NeonCarWashProps}
      />

      {/* DinoBuild — arc-trajectory dino parts snap together (1800f = 60s) */}
      <C
        id="DinoBuild"
        component={DinoBuild}
        durationInFrames={1800}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{
          musicFile: "Wholesome.mp3",
        } as DinoBuildProps}
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
