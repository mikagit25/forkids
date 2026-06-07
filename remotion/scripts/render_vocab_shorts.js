#!/usr/bin/env node
/**
 * Render all 26 vocabulary shorts using Remotion.
 * Output: /opt/kids_channel/output/queue/short_vocab_{letter}_{date}.mp4
 *
 * Usage:
 *   node scripts/render_vocab_shorts.js
 *   node scripts/render_vocab_shorts.js --letters A B C
 *   node scripts/render_vocab_shorts.js --quality medium
 */
const { execSync, spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");
const yaml = require("yaml");

const ROOT_CHANNEL = path.resolve(__dirname, "../../");
const QUEUE_DIR = path.join(ROOT_CHANNEL, "output", "queue");
const SPRITES = path.join(ROOT_CHANNEL, "assets", "sprites_new");

const LETTERS = {
  A: { word: "APPLE",      audio: "a__apple__a_is_for_apple.mp3",         sprite: "fruits/apple.png",      color: "#E53935", bg: "#E8F5E9" },
  B: { word: "BANANA",     audio: "b__banana__b_is_for_banana.mp3",       sprite: "fruits/banana.png",     color: "#F9A825", bg: "#FFF9C4" },
  C: { word: "CAT",        audio: "c__cat__c_is_for_cat.mp3",             sprite: "animals/cat.png",       color: "#F57C00", bg: "#FFF3E0" },
  D: { word: "DOG",        audio: "d__dog__d_is_for_dog.mp3",             sprite: "animals/dog.png",       color: "#6D4C41", bg: "#EFEBE9" },
  E: { word: "ELEPHANT",   audio: "e__elephant__e_is_for_elephant.mp3",   sprite: "animals/elephant.png",  color: "#546E7A", bg: "#ECEFF1" },
  F: { word: "FROG",       audio: "f__frog__f_is_for_frog.mp3",           sprite: "animals/frog.png",      color: "#2E7D32", bg: "#E8F5E9" },
  G: { word: "GIRAFFE",    audio: "g__giraffe__g_is_for_giraffe.mp3",     sprite: null,                    color: "#F9A825", bg: "#FFFDE7" },
  H: { word: "HIPPO",      audio: "h__hippo__h_is_for_hippo.mp3",         sprite: null,                    color: "#7B1FA2", bg: "#F3E5F5" },
  I: { word: "IGLOO",      audio: "i__igloo__i_is_for_igloo.mp3",         sprite: null,                    color: "#1565C0", bg: "#E3F2FD" },
  J: { word: "JELLYFISH",  audio: "j__jellyfish__j_is_for_jellyfish.mp3", sprite: null,                    color: "#C2185B", bg: "#FCE4EC" },
  K: { word: "KOALA",      audio: "k__koala__k_is_for_koala.mp3",         sprite: "animals/koala.png",     color: "#546E7A", bg: "#ECEFF1" },
  L: { word: "LION",       audio: "l__lion__l_is_for_lion.mp3",           sprite: "animals/lion.png",      color: "#E65100", bg: "#FFF3E0" },
  M: { word: "MONKEY",     audio: "m__monkey__m_is_for_monkey.mp3",       sprite: "animals/monkey.png",    color: "#5D4037", bg: "#EFEBE9" },
  N: { word: "NEST",       audio: "n__nest__n_is_for_nest.mp3",           sprite: null,                    color: "#4E342E", bg: "#FFF8E1" },
  O: { word: "OWL",        audio: "o__owl__o_is_for_owl.mp3",             sprite: "animals/owl.png",       color: "#4527A0", bg: "#EDE7F6" },
  P: { word: "PENGUIN",    audio: "p__penguin__p_is_for_penguin.mp3",     sprite: "animals/penguin.png",   color: "#1A237E", bg: "#E8EAF6" },
  Q: { word: "QUEEN",      audio: "q__queen__q_is_for_queen.mp3",         sprite: null,                    color: "#6A1B9A", bg: "#F3E5F5" },
  R: { word: "RABBIT",     audio: "r__rabbit__r_is_for_rabbit.mp3",       sprite: "animals/rabbit.png",    color: "#AD1457", bg: "#FCE4EC" },
  S: { word: "STAR",       audio: "s__star__s_is_for_star.mp3",           sprite: null,                    color: "#F57F17", bg: "#FFFDE7" },
  T: { word: "TIGER",      audio: "t__tiger__t_is_for_tiger.mp3",         sprite: "animals/tiger.png",     color: "#E65100", bg: "#FFF3E0" },
  U: { word: "UMBRELLA",   audio: "u__umbrella__u_is_for_umbrella.mp3",   sprite: null,                    color: "#0277BD", bg: "#E1F5FE" },
  V: { word: "VIOLIN",     audio: "v__violin__v_is_for_violin.mp3",       sprite: null,                    color: "#6A1B9A", bg: "#EDE7F6" },
  W: { word: "WATERMELON", audio: "w__watermelon__w_is_for_watermelon.mp3", sprite: "fruits/watermelon.png", color: "#2E7D32", bg: "#E8F5E9" },
  X: { word: "XYLOPHONE",  audio: "x__xylophone__x_is_for_xylophone.mp3", sprite: null,                   color: "#C62828", bg: "#FFEBEE" },
  Y: { word: "YAK",        audio: "y__yak__y_is_for_yak.mp3",             sprite: null,                    color: "#558B2F", bg: "#F1F8E9" },
  Z: { word: "ZEBRA",      audio: "z__zebra__z_is_for_zebra.mp3",         sprite: null,                    color: "#212121", bg: "#FAFAFA" },
};

const QUALITY_MAP = { low: "low", medium: "medium", high: "high" };

function parseArgs() {
  const args = process.argv.slice(2);
  const letters = [];
  let quality = "medium";
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--letters") {
      while (i + 1 < args.length && !args[i + 1].startsWith("--")) {
        letters.push(args[++i].toUpperCase());
      }
    } else if (args[i] === "--quality" && args[i + 1]) {
      quality = args[++i];
    }
  }
  return {
    letters: letters.length ? letters : Object.keys(LETTERS),
    quality: QUALITY_MAP[quality] || "medium",
  };
}

function makeMeta(letter, word, outPath) {
  const wordCap = word.charAt(0) + word.slice(1).toLowerCase();
  const meta = {
    title: `Letter ${letter} | ${letter} is for ${wordCap} | ABC for Kids | Happy Bear Kids #shorts`,
    video_type: "short_vocab",
    theme: "abc",
    duration_minutes: 1,
    is_short: true,
    tags: [
      "abc", "alphabet", `letter ${letter.toLowerCase()}`, word.toLowerCase(),
      `${letter} is for ${wordCap}`, "kids learning", "abc for kids",
      "letters for toddlers", "preschool", "happy bear kids",
      "educational", "shorts", "phonics", "vocabulary",
    ],
    status: "public",
  };
  const metaPath = outPath.replace(/\.mp4$/, "").replace(
    /([^/]+)$/,
    (_, stem) => `meta_${stem}.yaml`
  );
  fs.writeFileSync(metaPath, require("js-yaml").dump(meta));
}

async function main() {
  const { letters, quality } = parseArgs();
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  fs.mkdirSync(QUEUE_DIR, { recursive: true });

  console.log(`\nRendering ${letters.length} vocabulary shorts (quality=${quality})\n`);

  let ok = 0;
  for (const letter of letters) {
    const data = LETTERS[letter];
    if (!data) { console.log(`  [${letter}] unknown, skipping`); continue; }

    const outFile = path.join(QUEUE_DIR, `short_vocab_${letter.toLowerCase()}_${dateStr}.mp4`);
    const spriteExists = data.sprite && fs.existsSync(path.join(SPRITES, data.sprite));

    process.stdout.write(`  [${letter}=${data.word.padEnd(10)}] ${ spriteExists ? "sprite" : "shape " }  `);

    const props = JSON.stringify({
      letter,
      word: data.word,
      spritePath: spriteExists ? data.sprite : null,
      audioFile: data.audio,
      letterColor: data.color,
      bgColor: data.bg,
    });

    const result = spawnSync(
      "npx",
      [
        "remotion", "render",
        "src/index.ts",
        "VocabularyShort",
        outFile,
        "--props", props,
        "--log", "error",
        `--video-image-format=jpeg`,
        `--jpeg-quality=85`,
      ],
      {
        cwd: path.resolve(__dirname, ".."),
        stdio: ["ignore", "pipe", "pipe"],
        encoding: "utf8",
      }
    );

    if (result.status === 0 && fs.existsSync(outFile)) {
      const sizeMb = (fs.statSync(outFile).size / 1024 / 1024).toFixed(1);
      console.log(`✓  ${path.basename(outFile)}  ${sizeMb}MB`);
      // makeMeta(letter, data.word, outFile);  // needs js-yaml
      ok++;
    } else {
      console.log(`✗  ${result.stderr?.slice(-200) || "unknown error"}`);
    }
  }

  console.log(`\nDone: ${ok}/${letters.length} vocabulary shorts rendered → ${QUEUE_DIR}`);
}

main().catch(console.error);
