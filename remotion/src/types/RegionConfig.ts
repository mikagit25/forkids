/**
 * Shared types for multi-region video generation.
 * Region drives allowed content, music, and SFX packs.
 * Pig is excluded for AR and ID regions (Muslim audiences).
 */

export type Region = "US" | "AR" | "ID";
export type Mechanic = "peek-a-boo" | "factory-transform" | "puzzle-assembly";
export type Theme = "animals" | "fruits" | "vehicles" | "dinosaurs" | "shapes";
export type SfxPack = "default" | "soft" | "bright";

export interface RegionConfig {
  region: Region;
  /** Animals allowed in this region (pig excluded for AR/ID) */
  allowedAnimals: string[];
  bgMusic: string;
  sfxPack: SfxPack;
  /** Right-to-left text direction */
  rtl: boolean;
  /** Language code for audio file selection */
  lang: "en" | "ar" | "id";
}

/** Standard animal list for US/global channel */
export const ANIMALS_US = [
  "bear", "cat", "cow", "dog", "duck", "elephant",
  "fox", "frog", "lion", "monkey", "owl", "panda",
  "parrot", "penguin", "rabbit", "tiger", "unicorn",
];

/** Animals allowed for AR/ID (no pig) */
export const ANIMALS_AR_ID = ANIMALS_US.filter(a => a !== "pig");

export const REGION_CONFIGS: Record<Region, Omit<RegionConfig, "bgMusic">> = {
  US: {
    region: "US",
    allowedAnimals: ANIMALS_US,
    sfxPack: "default",
    rtl: false,
    lang: "en",
  },
  AR: {
    region: "AR",
    allowedAnimals: ANIMALS_AR_ID,
    sfxPack: "soft",
    rtl: true,
    lang: "ar",
  },
  ID: {
    region: "ID",
    allowedAnimals: ANIMALS_AR_ID,
    sfxPack: "bright",
    rtl: false,
    lang: "id",
  },
};

/** Unified video props for mechanic-based compositions */
export interface VideoProps {
  region: Region;
  mechanic: Mechanic;
  theme: Theme;
  itemsCount: number;
  bgMusic: string;
  /** Override allowed animals (uses region default if omitted) */
  animals?: string[];
}
