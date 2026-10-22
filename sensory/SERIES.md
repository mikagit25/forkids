# Dancing Objects — series design (sensory channel / Happy Bear Kids EN)

Same genre as the big sensory channels (glossy objects on black, dancing on the beat, no speech),
with our own characters, our own code-made music and a different episode every time.

## 1. Character families (all drawn in code: glossy body, highlight, glow, blinking face)
| Family | Characters (first wave → later) |
|---|---|
| Fruits | berry ✅, pear ✅, plum ✅, orange, banana, lemon, cherry pair, watermelon slice |
| Veggies | carrot, broccoli, tomato, pea pod, corn, pumpkin (seasonal) |
| Sweets | cupcake, donut, ice-cream cone, lollipop, jelly |
| Toys | ball, block, rubber duck, spinning top, balloon |
| Sky | sun, cloud, star, moon, rainbow, raindrop |
| Sea | fish, jellyfish, bubble, starfish, little whale |
| Shapes | circle, heart, star, triangle (high-contrast format) |
Seasonal accessories as a separate layer: party hat, Santa hat, pumpkin hat, sunglasses, bow.

## 2. Moves (beat-locked, from the beat phase)
bounce ✅ · sway ✅ · stretch ✅ · next: spin (Y-flip), jump-turn, wobble-jelly, hop-across,
arms (noodle arms: wave, clap, raise), head-bob, peek (pop up from bottom), freeze-pose on breaks.

## 3. Choreography templates (one per 8/16 bars, scene change on the song's sections)
solo (big, centre) · duet mirror · trio wave (one after another) · conga line across the screen ·
circle / orbit · "pop-in" counting 1…N · call & answer (one dances, the rest copy) · finale: everyone.
Transitions: fly in/out, zoom, pop with elastic easing; never a hard flash (> 3 flashes/s forbidden).

## 4. Music (sensory/music.py — code, our rights, exact beat map)
Genres: disco · calypso (steel drum) · march (toy band) · bounce (electro-pop) · lullaby (sleep).
Each seed → new key, tempo, chords, a catchy 2-bar motif; song form intro/A/A'/B/break/A/B'/A/outro,
sections = scene changes. Next: tempo-mapped counting songs, seasonal (jingle bells feel, spooky-fun),
more lead instruments (kalimba, whistle-synth, xylophone), "minis" 2–3 min and 1-hour mixes.

## 5. Formats
1. Dance (main) 10–25 min  2. Counting 1–10  3. High contrast (newborns) 15–45 min
4. Sleep 30–120 min (lullaby + slow floating moon/stars/fish)  5. Shorts 30–55 s (best chorus)

## 6. Episode generator (step 4+)
`episode.yaml` or auto from a seed: theme (family / season) → cast, genre, choreography per section,
title, thumbnail, 200+ word description, made_for_kids: true, queue `output/queue/`.
Anti-repetition: log of used (cast, genre, key, motif) — a new episode must differ.

## Status
step 1 stills ✅ · step 2 beat motion + face ✅ · step 3 music engine + dance to it ✅ ·
step 4 scenes/choreography by sections · step 5 character families · step 6 counting/contrast/sleep ·
step 7 long versions + parallel rendering · step 8 thumbnails + meta + queue
