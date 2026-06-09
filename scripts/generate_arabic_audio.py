#!/usr/bin/env python3
"""
Generate Arabic TTS voiceover files using edge-tts.
Voice: ar-SA-ZariyahNeural (female, Saudi Arabic)
Rate:  -15%  (slower — native speakers said default was too fast)

Output: assets/audio/voiceover/ar/
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT  = ROOT / "assets" / "audio" / "voiceover" / "ar"

VOICE = "ar-SA-ZariyahNeural"
RATE  = "-15%"

# ── Phrases to generate ───────────────────────────────────────────────────────

# Format: filename_stem → text
# Colors: mirrors English "red__red__can_you_find_something_red.mp3"
COLORS = {
    "ar_red__احمر__هل_يمكنك_ايجاد_شيء_احمر":
        "أحمر! أحمر! هل يمكنك إيجاد شيء أحمر؟",
    "ar_orange__برتقالي__هل_يمكنك_ايجاد_شيء_برتقالي":
        "برتقالي! برتقالي! هل يمكنك إيجاد شيء برتقالي؟",
    "ar_yellow__اصفر__هل_يمكنك_ايجاد_شيء_اصفر":
        "أصفر! أصفر! هل يمكنك إيجاد شيء أصفر؟",
    "ar_green__اخضر__هل_يمكنك_ايجاد_شيء_اخضر":
        "أخضر! أخضر! هل يمكنك إيجاد شيء أخضر؟",
    "ar_blue__ازرق__هل_يمكنك_ايجاد_شيء_ازرق":
        "أزرق! أزرق! هل يمكنك إيجاد شيء أزرق؟",
    "ar_purple__بنفسجي__هل_يمكنك_ايجاد_شيء_بنفسجي":
        "بنفسجي! بنفسجي! هل يمكنك إيجاد شيء بنفسجي؟",
    "ar_pink__وردي__هل_يمكنك_ايجاد_شيء_وردي":
        "وردي! وردي! هل يمكنك إيجاد شيء وردي؟",
}

# Shapes: mirrors English "circle__this_is_a_circle__a_circle.mp3"
# Arabic grammar: دائرة/نجمة = feminine (هذه), rest = masculine (هذا)
SHAPES = {
    "ar_circle__dairah__this_is_a_circle":
        "دائرة! هذه دائرة. دائرة!",
    "ar_square__murabba__this_is_a_square":
        "مربع! هذا مربع. مربع!",
    "ar_triangle__muthalath__this_is_a_triangle":
        "مثلث! هذا مثلث. مثلث!",
    "ar_star__najma__this_is_a_star":
        "نجمة! هذه نجمة. نجمة!",
    "ar_diamond__muaayan__this_is_a_diamond":
        "معين! هذا معين. معين!",
    "ar_heart__qalb__this_is_a_heart":
        "قلب! هذا قلب. قلب!",
    "ar_hexagon__musaddas__this_is_a_hexagon":
        "مسدس! هذا مسدس. مسدس!",
    "ar_oval__baydawi__this_is_an_oval":
        "بيضاوي! هذا شكل بيضاوي. بيضاوي!",
}

# Dancing names (for dance shorts — short name only)
DANCE = {
    "ar_dance_bear":      "دب يرقص! دب يرقص!",
    "ar_dance_lion":      "أسد يرقص! أسد يرقص!",
    "ar_dance_elephant":  "فيل يرقص! فيل يرقص!",
    "ar_dance_duck":      "بطة ترقص! بطة ترقص!",
    "ar_dance_cat":       "قطة ترقص! قطة ترقص!",
    "ar_dance_dog":       "كلب يرقص! كلب يرقص!",
    "ar_dance_monkey":    "قرد يرقص! قرد يرقص!",
    "ar_dance_tiger":     "نمر يرقص! نمر يرقص!",
    "ar_dance_penguin":   "بطريق يرقص! بطريق يرقص!",
    "ar_dance_rabbit":    "أرنب يرقص! أرنب يرقص!",
    "ar_dance_frog":      "ضفدع يرقص! ضفدع يرقص!",
    "ar_dance_owl":       "بومة ترقص! بومة ترقص!",
    "ar_dance_koala":     "كوالا يرقص! كوالا يرقص!",
    "ar_dance_panda":     "باندا يرقص! باندا يرقص!",
    "ar_dance_parrot":    "ببغاء يرقص! ببغاء يرقص!",
    "ar_dance_unicorn":   "وحيد القرن يرقص! وحيد القرن يرقص!",
    # Fruits
    "ar_dance_apple":      "تفاحة ترقص! تفاحة ترقص!",
    "ar_dance_banana":     "موزة ترقص! موزة ترقص!",
    "ar_dance_strawberry": "فراولة ترقص! فراولة ترقص!",
    "ar_dance_watermelon": "بطيخ يرقص! بطيخ يرقص!",
    "ar_dance_orange":     "برتقالة ترقص! برتقالة ترقص!",
    "ar_dance_grapes":     "عنب يرقص! عنب يرقص!",
    "ar_dance_pineapple":  "أناناس يرقص! أناناس يرقص!",
    "ar_dance_cherry":     "كرز يرقص! كرز يرقص!",
    "ar_dance_lemon":      "ليمون يرقص! ليمون يرقص!",
    "ar_dance_peach":      "خوخ يرقص! خوخ يرقص!",
    "ar_dance_pear":       "إجاصة ترقص! إجاصة ترقص!",
    "ar_dance_melon":      "شمام يرقص! شمام يرقص!",
    # Vegetables
    "ar_dance_carrot":    "جزرة ترقص! جزرة ترقص!",
    "ar_dance_broccoli":  "بروكلي يرقص! بروكلي يرقص!",
    "ar_dance_corn":      "ذرة ترقص! ذرة ترقص!",
    "ar_dance_tomato":    "طماطم ترقص! طماطم ترقص!",
    "ar_dance_cucumber":  "خيار يرقص! خيار يرقص!",
    "ar_dance_eggplant":  "باذنجان يرقص! باذنجان يرقص!",
    "ar_dance_onion":     "بصلة ترقص! بصلة ترقص!",
    "ar_dance_potato":    "بطاطا ترقص! بطاطا ترقص!",
    "ar_dance_pepper":    "فلفل يرقص! فلفل يرقص!",
    "ar_dance_mushroom":  "فطر يرقص! فطر يرقص!",
}

ALL_PHRASES = {**COLORS, **SHAPES, **DANCE}


async def generate_one(stem: str, text: str, force: bool) -> bool:
    import edge_tts
    out = OUT / f"{stem}.mp3"
    if out.exists() and not force:
        print(f"  skip  {stem}")
        return True
    try:
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
        await communicate.save(str(out))
        size = out.stat().st_size
        print(f"  ✓  {stem}  ({size//1024}KB)")
        return True
    except Exception as e:
        print(f"  ✗  {stem}: {e}")
        return False


async def main(force: bool = False):
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"\nGenerating {len(ALL_PHRASES)} Arabic TTS files")
    print(f"  Voice: {VOICE}  Rate: {RATE}\n")

    tasks = [generate_one(stem, text, force) for stem, text in ALL_PHRASES.items()]
    results = await asyncio.gather(*tasks)

    ok = sum(results)
    print(f"\nDone: {ok}/{len(ALL_PHRASES)} files → {OUT}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    asyncio.run(main(args.force))
