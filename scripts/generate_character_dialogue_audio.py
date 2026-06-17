#!/usr/bin/env python3
"""
Generate TTS audio for CharacterDialogueLong episodes.
Bear character speaks TO the child — conversational, repeated, engaging.

Structure per episode (8 sections):
  intro    — character greeting, episode title
  scene1   — scene 1: repeat concept 3-4x, ask child, encourage
  scene2   — scene 2
  scene3   — scene 3
  scene4   — scene 4
  song     — recap chant with all 4 concepts
  outro    — goodbye, subscribe

Usage:
  python3 scripts/generate_character_dialogue_audio.py --episode emotions
  python3 scripts/generate_character_dialogue_audio.py --episode emotions --lang ar
  python3 scripts/generate_character_dialogue_audio.py --all
  python3 scripts/generate_character_dialogue_audio.py --all --force
"""
import argparse
import asyncio
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    sys.exit("edge_tts not installed. Run: pip3 install edge-tts")

ROOT    = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "remotion" / "public" / "audio" / "character_dialogue"

# ── Voice map ─────────────────────────────────────────────────────────────────
VOICES = {
    "en": "en-US-JennyNeural",
    "ar": "ar-SA-ZariyahNeural",
    "id": "id-ID-GadisNeural",
}

# ── Episode audio scripts ─────────────────────────────────────────────────────
# Each episode has 7 keys: intro, scene1..scene4, song, outro
# Designed to be CONVERSATIONAL — speaking TO the child multiple times
EPISODES: dict[str, dict[str, dict[str, str]]] = {

    # ── EMOTIONS ──────────────────────────────────────────────────────────────
    "emotions": {
        "en": {
            "intro": (
                "Hello little friend! I am Roundy the Bear! "
                "Today we are going to learn about feelings! "
                "Feelings! Do you know what feelings are? "
                "When you smile, you feel HAPPY! When you cry, you feel SAD! "
                "Let's learn about feelings together! Are you ready? Let's go!"
            ),
            "scene1": (
                "Look! This is HAPPY! Happy! Can you say HAPPY? "
                "Say it with me! HAPPY! "
                "When you smile and laugh, you feel HAPPY! "
                "Are YOU happy right now? Show me your happy face! "
                "Big smile! Yes! That's HAPPY! Happy! "
                "Can you say it again? HAPPY! Wonderful! I am so proud of you!"
            ),
            "scene2": (
                "Now look at this. This is SAD. Sad. Can you say SAD? "
                "Say it with me! SAD! "
                "When you cry or feel down, you feel SAD. "
                "But that's okay! Everyone feels sad sometimes. "
                "Can you show me your sad face? "
                "That's it! SAD! "
                "Say it one more time! SAD! Very good! You are so smart!"
            ),
            "scene3": (
                "Ooh! Look at this! This is ANGRY! Angry! "
                "Can you say ANGRY? "
                "ANGRY! Say it with me! ANGRY! "
                "When something makes you upset, you feel ANGRY! "
                "Can you show me your angry face? "
                "Grr! That's it! ANGRY! "
                "But remember, it's okay to feel angry. Take a deep breath! "
                "ANGRY! Great job saying that!"
            ),
            "scene4": (
                "Wow! What is this? This is SURPRISED! Surprised! "
                "Can you say SURPRISED? "
                "Say it with me! SURPRISED! "
                "When something unexpected happens, you feel SURPRISED! "
                "Can you make a surprised face? "
                "Big round eyes! Mouth open! Yes! That's SURPRISED! "
                "SURPRISED! Amazing! You know all the feelings!"
            ),
            "song": (
                "Let's sing together! "
                "HAPPY, SAD, ANGRY, SURPRISED! "
                "These are feelings, big and small! "
                "HAPPY when we laugh and play! "
                "SAD when things don't go our way! "
                "ANGRY, take a breath today! "
                "SURPRISED when something comes our way! "
                "HAPPY, SAD, ANGRY, SURPRISED! "
                "You know your feelings! Hooray!"
            ),
            "outro": (
                "Wonderful job today, little friend! "
                "You learned HAPPY, SAD, ANGRY, and SURPRISED! "
                "You are so clever! "
                "Don't forget to tell your mommy and daddy what you learned today! "
                "I am Roundy the Bear, and I love you! "
                "See you next time! Bye bye!"
            ),
        },
        "ar": {
            "intro": (
                "مرحباً يا صديقي الصغير! أنا راوندي الدب! "
                "اليوم سنتعلم عن المشاعر! "
                "المشاعر! هل تعرف ما هي المشاعر؟ "
                "عندما تبتسم، تشعر بالسعادة! عندما تبكي، تشعر بالحزن! "
                "هيا نتعلم المشاعر معاً! هل أنت مستعد؟ هيا بنا!"
            ),
            "scene1": (
                "انظر! هذا هو السعيد! سعيد! هل يمكنك أن تقول سعيد؟ "
                "قل معي! سعيد! "
                "عندما تبتسم وتضحك، تشعر بالسعادة! "
                "هل أنت سعيد الآن؟ أرني وجهك السعيد! "
                "ابتسامة كبيرة! نعم! هذا هو سعيد! سعيد! "
                "هل يمكنك أن تقوله مرة أخرى؟ سعيد! رائع! أنا فخور بك!"
            ),
            "scene2": (
                "الآن انظر إلى هذا. هذا هو الحزين. حزين. هل يمكنك أن تقول حزين؟ "
                "قل معي! حزين! "
                "عندما تبكي أو تشعر بالكآبة، تشعر بالحزن. "
                "لكن هذا طبيعي! الجميع يشعر بالحزن أحياناً. "
                "هل يمكنك أن تريني وجهك الحزين؟ "
                "هكذا! حزين! "
                "قله مرة أخرى! حزين! جيد جداً! أنت ذكي جداً!"
            ),
            "scene3": (
                "أوه! انظر إلى هذا! هذا هو الغاضب! غاضب! "
                "هل يمكنك أن تقول غاضب؟ "
                "غاضب! قل معي! غاضب! "
                "عندما يزعجك شيء ما، تشعر بالغضب! "
                "هل يمكنك أن تريني وجهك الغاضب؟ "
                "غر! هكذا! غاضب! "
                "لكن تذكر، من الطبيعي أن تشعر بالغضب. خذ نفساً عميقاً! "
                "غاضب! أحسنت في قول ذلك!"
            ),
            "scene4": (
                "واو! ما هذا؟ هذا هو المندهش! مندهش! "
                "هل يمكنك أن تقول مندهش؟ "
                "قل معي! مندهش! "
                "عندما يحدث شيء غير متوقع، تشعر بالدهشة! "
                "هل يمكنك أن تعمل وجهاً مندهشاً؟ "
                "عيون كبيرة مستديرة! فم مفتوح! نعم! هذا هو مندهش! "
                "مندهش! رائع! أنت تعرف كل المشاعر!"
            ),
            "song": (
                "هيا نغني معاً! "
                "سعيد، حزين، غاضب، مندهش! "
                "هذه مشاعر كبيرة وصغيرة! "
                "سعيد عندما نضحك ونلعب! "
                "حزين عندما تسوء الأمور! "
                "غاضب، خذ نفساً اليوم! "
                "مندهش عندما يأتي شيء ما! "
                "سعيد، حزين، غاضب، مندهش! "
                "أنت تعرف مشاعرك! يا هلا!"
            ),
            "outro": (
                "عمل رائع اليوم يا صديقي الصغير! "
                "تعلمت سعيد وحزين وغاضب ومندهش! "
                "أنت ذكي جداً! "
                "لا تنس أن تخبر أمك وأبيك بما تعلمته اليوم! "
                "أنا راوندي الدب، وأحبك! "
                "أراك في المرة القادمة! مع السلامة!"
            ),
        },
        "id": {
            "intro": (
                "Halo teman kecilku! Aku Roundy si Beruang! "
                "Hari ini kita akan belajar tentang perasaan! "
                "Perasaan! Apakah kamu tahu apa itu perasaan? "
                "Ketika kamu tersenyum, kamu merasa SENANG! Ketika kamu menangis, kamu merasa SEDIH! "
                "Ayo kita belajar perasaan bersama! Siap? Ayo!"
            ),
            "scene1": (
                "Lihat! Ini adalah SENANG! Senang! Bisakah kamu bilang SENANG? "
                "Bilang bersamaku! SENANG! "
                "Ketika kamu tersenyum dan tertawa, kamu merasa SENANG! "
                "Apakah KAMU senang sekarang? Tunjukkan wajah senangmu! "
                "Senyum besar! Ya! Itulah SENANG! Senang! "
                "Bisakah kamu bilang lagi? SENANG! Bagus sekali! Aku bangga padamu!"
            ),
            "scene2": (
                "Sekarang lihat ini. Ini adalah SEDIH. Sedih. Bisakah kamu bilang SEDIH? "
                "Bilang bersamaku! SEDIH! "
                "Ketika kamu menangis atau merasa down, kamu merasa SEDIH. "
                "Tapi tidak apa-apa! Semua orang kadang merasa sedih. "
                "Bisakah kamu tunjukkan wajah sedihmu? "
                "Begitu! SEDIH! "
                "Bilang sekali lagi! SEDIH! Sangat bagus! Kamu sangat pintar!"
            ),
            "scene3": (
                "Ooh! Lihat ini! Ini adalah MARAH! Marah! "
                "Bisakah kamu bilang MARAH? "
                "MARAH! Bilang bersamaku! MARAH! "
                "Ketika sesuatu membuatmu kesal, kamu merasa MARAH! "
                "Bisakah kamu tunjukkan wajah marahmu? "
                "Grr! Begitu! MARAH! "
                "Tapi ingat, boleh merasa marah. Tarik napas dalam! "
                "MARAH! Bagus sekali mengucapkan itu!"
            ),
            "scene4": (
                "Wow! Apa ini? Ini adalah TERKEJUT! Terkejut! "
                "Bisakah kamu bilang TERKEJUT? "
                "Bilang bersamaku! TERKEJUT! "
                "Ketika sesuatu yang tidak terduga terjadi, kamu merasa TERKEJUT! "
                "Bisakah kamu membuat wajah terkejut? "
                "Mata besar bulat! Mulut terbuka! Ya! Itulah TERKEJUT! "
                "TERKEJUT! Luar biasa! Kamu tahu semua perasaan!"
            ),
            "song": (
                "Ayo bernyanyi bersama! "
                "SENANG, SEDIH, MARAH, TERKEJUT! "
                "Ini adalah perasaan besar dan kecil! "
                "SENANG ketika kita tertawa dan bermain! "
                "SEDIH ketika sesuatu tidak berjalan dengan baik! "
                "MARAH, tarik napas hari ini! "
                "TERKEJUT ketika sesuatu datang! "
                "SENANG, SEDIH, MARAH, TERKEJUT! "
                "Kamu tahu perasaanmu! Hore!"
            ),
            "outro": (
                "Kerja bagus hari ini, teman kecilku! "
                "Kamu belajar SENANG, SEDIH, MARAH, dan TERKEJUT! "
                "Kamu sangat pintar! "
                "Jangan lupa ceritakan kepada mama dan papa apa yang kamu pelajari hari ini! "
                "Aku Roundy si Beruang, dan aku menyayangimu! "
                "Sampai jumpa! Dadah!"
            ),
        },
    },

    # ── COLORS (character version) ────────────────────────────────────────────
    "colors_character": {
        "en": {
            "intro": (
                "Hello there! I am Roundy the Bear! "
                "Today we are going to learn about COLORS! "
                "Colors are everywhere! In your toys, in the sky, in flowers! "
                "Are you ready to learn colors with me? Let's go!"
            ),
            "scene1": (
                "Look at this beautiful color! This is RED! Red! "
                "Can you say RED? Say it with me! RED! "
                "Strawberries are red! Apples are red! Tomatoes are red! "
                "Can you find something RED around you? "
                "Look around! Do you see something red? "
                "RED! Great job! You found it!"
            ),
            "scene2": (
                "Now look at this! This is BLUE! Blue! "
                "Can you say BLUE? BLUE! Say it with me! BLUE! "
                "The sky is blue! Water is blue! Blueberries are blue! "
                "Can you find something BLUE around you? "
                "BLUE! Say it again! BLUE! Wonderful!"
            ),
            "scene3": (
                "Oh what a beautiful color! This is YELLOW! Yellow! "
                "Can you say YELLOW? Say it with me! YELLOW! "
                "The sun is yellow! Bananas are yellow! Stars are yellow! "
                "Can you find something YELLOW near you? "
                "YELLOW! You are doing amazing!"
            ),
            "scene4": (
                "Look at this gorgeous color! This is GREEN! Green! "
                "Can you say GREEN? GREEN! Say it with me! GREEN! "
                "Grass is green! Leaves are green! Frogs are green! "
                "Can you find something GREEN around you? "
                "GREEN! Fantastic! You know so many colors!"
            ),
            "song": (
                "Let's sing the color song! "
                "RED, BLUE, YELLOW, GREEN! "
                "Colors everywhere we've seen! "
                "RED like apples, BLUE like sky! "
                "YELLOW like the sun up high! "
                "GREEN like grass where I can play! "
                "I know my colors every day! "
                "RED, BLUE, YELLOW, GREEN! Hooray!"
            ),
            "outro": (
                "You did it! You learned RED, BLUE, YELLOW, and GREEN! "
                "You are a colors expert now! "
                "I am Roundy the Bear and I am so proud of you! "
                "See you next time! Bye bye!"
            ),
        },
        "ar": {
            "intro": (
                "مرحباً! أنا راوندي الدب! "
                "اليوم سنتعلم عن الألوان! "
                "الألوان في كل مكان! في ألعابك، في السماء، في الزهور! "
                "هل أنت مستعد لتعلم الألوان معي؟ هيا بنا!"
            ),
            "scene1": (
                "انظر إلى هذا اللون الجميل! هذا هو الأحمر! أحمر! "
                "هل يمكنك أن تقول أحمر؟ قل معي! أحمر! "
                "الفراولة حمراء! التفاح أحمر! الطماطم حمراء! "
                "هل يمكنك أن تجد شيئاً أحمر حولك؟ "
                "انظر حولك! هل ترى شيئاً أحمر؟ "
                "أحمر! عمل رائع! وجدته!"
            ),
            "scene2": (
                "الآن انظر إلى هذا! هذا هو الأزرق! أزرق! "
                "هل يمكنك أن تقول أزرق؟ أزرق! قل معي! أزرق! "
                "السماء زرقاء! الماء أزرق! التوت الأزرق أزرق! "
                "هل يمكنك أن تجد شيئاً أزرق حولك؟ "
                "أزرق! قله مرة أخرى! أزرق! رائع!"
            ),
            "scene3": (
                "يا له من لون جميل! هذا هو الأصفر! أصفر! "
                "هل يمكنك أن تقول أصفر؟ قل معي! أصفر! "
                "الشمس صفراء! الموز أصفر! النجوم صفراء! "
                "هل يمكنك أن تجد شيئاً أصفر بالقرب منك؟ "
                "أصفر! أنت تقوم بعمل رائع!"
            ),
            "scene4": (
                "انظر إلى هذا اللون الرائع! هذا هو الأخضر! أخضر! "
                "هل يمكنك أن تقول أخضر؟ أخضر! قل معي! أخضر! "
                "العشب أخضر! الأوراق خضراء! الضفادع خضراء! "
                "هل يمكنك أن تجد شيئاً أخضر حولك؟ "
                "أخضر! رائع! أنت تعرف الكثير من الألوان!"
            ),
            "song": (
                "هيا نغني أغنية الألوان! "
                "أحمر، أزرق، أصفر، أخضر! "
                "ألوان في كل مكان رأيناها! "
                "أحمر مثل التفاح، أزرق مثل السماء! "
                "أصفر مثل الشمس عالياً في السماء! "
                "أخضر مثل العشب حيث يمكنني اللعب! "
                "أنا أعرف ألواني كل يوم! "
                "أحمر، أزرق، أصفر، أخضر! يا هلا!"
            ),
            "outro": (
                "فعلتها! تعلمت الأحمر والأزرق والأصفر والأخضر! "
                "أنت الآن خبير في الألوان! "
                "أنا راوندي الدب وأنا فخور جداً بك! "
                "أراك في المرة القادمة! مع السلامة!"
            ),
        },
        "id": {
            "intro": (
                "Halo! Aku Roundy si Beruang! "
                "Hari ini kita akan belajar tentang WARNA! "
                "Warna ada di mana-mana! Di mainanmu, di langit, di bunga! "
                "Siap belajar warna bersamaku? Ayo!"
            ),
            "scene1": (
                "Lihat warna indah ini! Ini adalah MERAH! Merah! "
                "Bisakah kamu bilang MERAH? Bilang bersamaku! MERAH! "
                "Stroberi itu merah! Apel itu merah! Tomat itu merah! "
                "Bisakah kamu menemukan sesuatu yang MERAH di sekitarmu? "
                "Lihat sekeliling! Apakah kamu melihat sesuatu yang merah? "
                "MERAH! Kerja bagus! Kamu menemukannya!"
            ),
            "scene2": (
                "Sekarang lihat ini! Ini adalah BIRU! Biru! "
                "Bisakah kamu bilang BIRU? BIRU! Bilang bersamaku! BIRU! "
                "Langit itu biru! Air itu biru! Blueberry itu biru! "
                "Bisakah kamu menemukan sesuatu yang BIRU di sekitarmu? "
                "BIRU! Bilang lagi! BIRU! Luar biasa!"
            ),
            "scene3": (
                "Oh warna yang indah sekali! Ini adalah KUNING! Kuning! "
                "Bisakah kamu bilang KUNING? Bilang bersamaku! KUNING! "
                "Matahari itu kuning! Pisang itu kuning! Bintang itu kuning! "
                "Bisakah kamu menemukan sesuatu yang KUNING di dekatmu? "
                "KUNING! Kamu melakukan hal yang luar biasa!"
            ),
            "scene4": (
                "Lihat warna yang indah ini! Ini adalah HIJAU! Hijau! "
                "Bisakah kamu bilang HIJAU? HIJAU! Bilang bersamaku! HIJAU! "
                "Rumput itu hijau! Daun itu hijau! Katak itu hijau! "
                "Bisakah kamu menemukan sesuatu yang HIJAU di sekitarmu? "
                "HIJAU! Fantastis! Kamu tahu banyak warna!"
            ),
            "song": (
                "Ayo nyanyikan lagu warna! "
                "MERAH, BIRU, KUNING, HIJAU! "
                "Warna ada di mana-mana yang kita lihat! "
                "MERAH seperti apel, BIRU seperti langit! "
                "KUNING seperti matahari tinggi di atas! "
                "HIJAU seperti rumput tempat aku bermain! "
                "Aku tahu warnaku setiap hari! "
                "MERAH, BIRU, KUNING, HIJAU! Hore!"
            ),
            "outro": (
                "Kamu berhasil! Kamu belajar MERAH, BIRU, KUNING, dan HIJAU! "
                "Kamu sekarang ahli warna! "
                "Aku Roundy si Beruang dan aku sangat bangga padamu! "
                "Sampai jumpa! Dadah!"
            ),
        },
    },

    # ── NUMBERS (character version) ───────────────────────────────────────────
    "numbers_character": {
        "en": {
            "intro": (
                "Hi there little friend! I am Roundy the Bear! "
                "Today we are going to COUNT together! "
                "One, two, three! Can you count? "
                "Let's learn numbers together! Are you ready? "
                "One! Two! Three! Four! Let's go!"
            ),
            "scene1": (
                "Look at this! This is the number ONE! One! "
                "Can you say ONE? Say it with me! ONE! "
                "One, one, one! Hold up ONE finger! "
                "Show me one finger! "
                "ONE! That is one finger! "
                "ONE! You are so smart!"
            ),
            "scene2": (
                "Now look here! This is the number TWO! Two! "
                "Can you say TWO? TWO! Say it with me! TWO! "
                "Two eyes! Two ears! Two hands! "
                "Hold up TWO fingers! "
                "One, two! TWO fingers! "
                "TWO! Amazing! You can count!"
            ),
            "scene3": (
                "Wow look at this! This is the number THREE! Three! "
                "Can you say THREE? Say it with me! THREE! "
                "Let's count together! One! Two! Three! "
                "Hold up THREE fingers! "
                "One, two, three! THREE! "
                "THREE! You are brilliant!"
            ),
            "scene4": (
                "Ooh here comes number FOUR! Four! "
                "Can you say FOUR? FOUR! Say it with me! FOUR! "
                "Let's count! One, two, three, FOUR! "
                "Hold up FOUR fingers! "
                "One, two, three, four! FOUR fingers! "
                "FOUR! You did it! You can count to four!"
            ),
            "song": (
                "Let's count together in our number song! "
                "ONE! ONE little friend says hi! "
                "TWO! TWO little eyes that blink! "
                "THREE! THREE little stars that shine! "
                "FOUR! FOUR little legs that jump! "
                "One, two, three, four! "
                "You can count! You can count! Hooray!"
            ),
            "outro": (
                "You did amazing! You counted ONE, TWO, THREE, FOUR! "
                "You are a counting superstar! "
                "I am Roundy the Bear and I love counting with you! "
                "See you next time! Bye bye!"
            ),
        },
        "ar": {
            "intro": (
                "مرحباً يا صديقي الصغير! أنا راوندي الدب! "
                "اليوم سنعد معاً! "
                "واحد، اثنان، ثلاثة! هل يمكنك العد؟ "
                "هيا نتعلم الأرقام معاً! هل أنت مستعد؟ "
                "واحد! اثنان! ثلاثة! أربعة! هيا بنا!"
            ),
            "scene1": (
                "انظر إلى هذا! هذا هو الرقم واحد! واحد! "
                "هل يمكنك أن تقول واحد؟ قل معي! واحد! "
                "واحد، واحد، واحد! ارفع إصبعاً واحداً! "
                "أرني إصبعاً واحداً! "
                "واحد! هذا إصبع واحد! "
                "واحد! أنت ذكي جداً!"
            ),
            "scene2": (
                "الآن انظر هنا! هذا هو الرقم اثنان! اثنان! "
                "هل يمكنك أن تقول اثنان؟ اثنان! قل معي! اثنان! "
                "عينان! أذنان! يدان! "
                "ارفع إصبعين! "
                "واحد، اثنان! إصبعان! "
                "اثنان! رائع! يمكنك العد!"
            ),
            "scene3": (
                "واو انظر إلى هذا! هذا هو الرقم ثلاثة! ثلاثة! "
                "هل يمكنك أن تقول ثلاثة؟ قل معي! ثلاثة! "
                "هيا نعد معاً! واحد! اثنان! ثلاثة! "
                "ارفع ثلاثة أصابع! "
                "واحد، اثنان، ثلاثة! ثلاثة! "
                "ثلاثة! أنت رائع!"
            ),
            "scene4": (
                "أوه ها هو الرقم أربعة! أربعة! "
                "هل يمكنك أن تقول أربعة؟ أربعة! قل معي! أربعة! "
                "هيا نعد! واحد، اثنان، ثلاثة، أربعة! "
                "ارفع أربعة أصابع! "
                "واحد، اثنان، ثلاثة، أربعة! أربعة أصابع! "
                "أربعة! فعلتها! يمكنك العد حتى أربعة!"
            ),
            "song": (
                "هيا نعد معاً في أغنية الأرقام! "
                "واحد! صديق واحد يقول مرحباً! "
                "اثنان! عينان صغيرتان تطرفان! "
                "ثلاثة! ثلاثة نجوم صغيرة تتألق! "
                "أربعة! أربعة أرجل صغيرة تقفز! "
                "واحد، اثنان، ثلاثة، أربعة! "
                "يمكنك العد! يمكنك العد! يا هلا!"
            ),
            "outro": (
                "أدهشتني! عددت واحد، اثنان، ثلاثة، أربعة! "
                "أنت نجم العد! "
                "أنا راوندي الدب وأحب العد معك! "
                "أراك في المرة القادمة! مع السلامة!"
            ),
        },
        "id": {
            "intro": (
                "Hai teman kecilku! Aku Roundy si Beruang! "
                "Hari ini kita akan MENGHITUNG bersama! "
                "Satu, dua, tiga! Bisakah kamu menghitung? "
                "Ayo belajar angka bersama! Siap? "
                "Satu! Dua! Tiga! Empat! Ayo!"
            ),
            "scene1": (
                "Lihat ini! Ini adalah angka SATU! Satu! "
                "Bisakah kamu bilang SATU? Bilang bersamaku! SATU! "
                "Satu, satu, satu! Angkat SATU jari! "
                "Tunjukkan satu jari padaku! "
                "SATU! Itu satu jari! "
                "SATU! Kamu sangat pintar!"
            ),
            "scene2": (
                "Sekarang lihat di sini! Ini adalah angka DUA! Dua! "
                "Bisakah kamu bilang DUA? DUA! Bilang bersamaku! DUA! "
                "Dua mata! Dua telinga! Dua tangan! "
                "Angkat DUA jari! "
                "Satu, dua! DUA jari! "
                "DUA! Luar biasa! Kamu bisa menghitung!"
            ),
            "scene3": (
                "Wow lihat ini! Ini adalah angka TIGA! Tiga! "
                "Bisakah kamu bilang TIGA? Bilang bersamaku! TIGA! "
                "Ayo hitung bersama! Satu! Dua! Tiga! "
                "Angkat TIGA jari! "
                "Satu, dua, tiga! TIGA! "
                "TIGA! Kamu luar biasa!"
            ),
            "scene4": (
                "Ooh datang angka EMPAT! Empat! "
                "Bisakah kamu bilang EMPAT? EMPAT! Bilang bersamaku! EMPAT! "
                "Ayo hitung! Satu, dua, tiga, EMPAT! "
                "Angkat EMPAT jari! "
                "Satu, dua, tiga, empat! EMPAT jari! "
                "EMPAT! Kamu berhasil! Kamu bisa menghitung sampai empat!"
            ),
            "song": (
                "Ayo hitung bersama dalam lagu angka kita! "
                "SATU! SATU teman kecil bilang hai! "
                "DUA! DUA mata kecil yang berkedip! "
                "TIGA! TIGA bintang kecil yang bersinar! "
                "EMPAT! EMPAT kaki kecil yang melompat! "
                "Satu, dua, tiga, empat! "
                "Kamu bisa menghitung! Kamu bisa menghitung! Hore!"
            ),
            "outro": (
                "Kamu luar biasa! Kamu menghitung SATU, DUA, TIGA, EMPAT! "
                "Kamu adalah bintang menghitung! "
                "Aku Roundy si Beruang dan aku suka menghitung bersamamu! "
                "Sampai jumpa! Dadah!"
            ),
        },
    },

    # ── ANIMALS (character version) ───────────────────────────────────────────
    "animals_character": {
        "en": {
            "intro": (
                "Hello hello! I am Roundy the Bear! "
                "Today we are going to meet some amazing ANIMALS! "
                "Animals! Do you have a favorite animal? "
                "Let's learn animal names together! Are you ready? Let's go!"
            ),
            "scene1": (
                "Look at this cute animal! This is a DUCK! Duck! "
                "Can you say DUCK? Say it with me! DUCK! "
                "Ducks say quack quack! Can you quack like a duck? "
                "Quack quack! Quack quack! "
                "Ducks love to swim in the water! "
                "DUCK! Say it again! DUCK! Wonderful!"
            ),
            "scene2": (
                "Oh look at this fluffy animal! This is a CAT! Cat! "
                "Can you say CAT? CAT! Say it with me! CAT! "
                "Cats say meow! Can you meow? "
                "Meow meow! Meow meow! "
                "Cats love to cuddle and play! "
                "CAT! You are doing great!"
            ),
            "scene3": (
                "Wow look at this animal! This is a FROG! Frog! "
                "Can you say FROG? Say it with me! FROG! "
                "Frogs say ribbit ribbit! Can you ribbit? "
                "Ribbit ribbit! Ribbit ribbit! "
                "Frogs love to jump and hop! Jump! Jump! "
                "FROG! Say it again! FROG! Amazing!"
            ),
            "scene4": (
                "Oh oh oh! Look at this big animal! This is an ELEPHANT! Elephant! "
                "Can you say ELEPHANT? ELEPHANT! Say it with me! ELEPHANT! "
                "Elephants have a big trunk! They go TOOT TOOT! "
                "Can you be an elephant? Put your arm out like a trunk! "
                "ELEPHANT! You are a superstar!"
            ),
            "song": (
                "Let's sing the animal song! "
                "DUCK says quack quack quack! "
                "CAT says meow meow meow! "
                "FROG says ribbit ribbit ribbit! "
                "ELEPHANT goes toot toot toot! "
                "Animals all around! Animals all around! "
                "Duck, cat, frog, elephant! Hooray!"
            ),
            "outro": (
                "You learned DUCK, CAT, FROG, and ELEPHANT today! "
                "You are an animal expert! "
                "I am Roundy the Bear and animals are my best friends too! "
                "See you next time! Bye bye!"
            ),
        },
        "ar": {
            "intro": (
                "مرحباً مرحباً! أنا راوندي الدب! "
                "اليوم سنلتقي ببعض الحيوانات الرائعة! "
                "الحيوانات! هل لديك حيوان مفضل؟ "
                "هيا نتعلم أسماء الحيوانات معاً! هل أنت مستعد؟ هيا بنا!"
            ),
            "scene1": (
                "انظر إلى هذا الحيوان اللطيف! هذه بطة! بطة! "
                "هل يمكنك أن تقول بطة؟ قل معي! بطة! "
                "البط تقول كواك كواك! هل يمكنك أن تقول كواك مثل البطة؟ "
                "كواك كواك! كواك كواك! "
                "البط تحب السباحة في الماء! "
                "بطة! قلها مرة أخرى! بطة! رائع!"
            ),
            "scene2": (
                "أوه انظر إلى هذا الحيوان الأفرش! هذا قط! قط! "
                "هل يمكنك أن تقول قط؟ قط! قل معي! قط! "
                "القطط تقول مياو! هل يمكنك أن تقول مياو؟ "
                "مياو مياو! مياو مياو! "
                "القطط تحب الحضن واللعب! "
                "قط! أنت تقوم بعمل رائع!"
            ),
            "scene3": (
                "واو انظر إلى هذا الحيوان! هذا ضفدع! ضفدع! "
                "هل يمكنك أن تقول ضفدع؟ قل معي! ضفدع! "
                "الضفادع تقول نقنق! هل يمكنك أن تقول نقنق؟ "
                "نقنق نقنق! نقنق نقنق! "
                "الضفادع تحب القفز! اقفز! اقفز! "
                "ضفدع! قله مرة أخرى! ضفدع! رائع!"
            ),
            "scene4": (
                "أوه أوه أوه! انظر إلى هذا الحيوان الكبير! هذا فيل! فيل! "
                "هل يمكنك أن تقول فيل؟ فيل! قل معي! فيل! "
                "الأفيال لها خرطوم كبير! تقول تووت تووت! "
                "هل يمكنك أن تكون فيلاً؟ ضع يدك للأمام مثل الخرطوم! "
                "فيل! أنت نجم!"
            ),
            "song": (
                "هيا نغني أغنية الحيوانات! "
                "البطة تقول كواك كواك كواك! "
                "القط يقول مياو مياو مياو! "
                "الضفدع يقول نقنق نقنق نقنق! "
                "الفيل يقول تووت تووت تووت! "
                "حيوانات في كل مكان! حيوانات في كل مكان! "
                "بطة، قط، ضفدع، فيل! يا هلا!"
            ),
            "outro": (
                "تعلمت البطة والقط والضفدع والفيل اليوم! "
                "أنت خبير في الحيوانات! "
                "أنا راوندي الدب والحيوانات هي أصدقائي المفضلون أيضاً! "
                "أراك في المرة القادمة! مع السلامة!"
            ),
        },
        "id": {
            "intro": (
                "Halo halo! Aku Roundy si Beruang! "
                "Hari ini kita akan bertemu beberapa HEWAN yang luar biasa! "
                "Hewan! Apakah kamu punya hewan favorit? "
                "Ayo belajar nama-nama hewan bersama! Siap? Ayo!"
            ),
            "scene1": (
                "Lihat hewan lucu ini! Ini adalah BEBEK! Bebek! "
                "Bisakah kamu bilang BEBEK? Bilang bersamaku! BEBEK! "
                "Bebek bilang kwek kwek! Bisakah kamu kwek seperti bebek? "
                "Kwek kwek! Kwek kwek! "
                "Bebek suka berenang di air! "
                "BEBEK! Bilang lagi! BEBEK! Luar biasa!"
            ),
            "scene2": (
                "Oh lihat hewan berbulu ini! Ini adalah KUCING! Kucing! "
                "Bisakah kamu bilang KUCING? KUCING! Bilang bersamaku! KUCING! "
                "Kucing bilang meong! Bisakah kamu meong? "
                "Meong meong! Meong meong! "
                "Kucing suka bermanja dan bermain! "
                "KUCING! Kamu melakukan hal yang bagus!"
            ),
            "scene3": (
                "Wow lihat hewan ini! Ini adalah KATAK! Katak! "
                "Bisakah kamu bilang KATAK? Bilang bersamaku! KATAK! "
                "Katak bilang koak koak! Bisakah kamu koak? "
                "Koak koak! Koak koak! "
                "Katak suka melompat dan loncat! Lompat! Lompat! "
                "KATAK! Bilang lagi! KATAK! Luar biasa!"
            ),
            "scene4": (
                "Oh oh oh! Lihat hewan besar ini! Ini adalah GAJAH! Gajah! "
                "Bisakah kamu bilang GAJAH? GAJAH! Bilang bersamaku! GAJAH! "
                "Gajah punya belalai besar! Mereka bersuara tut tut! "
                "Bisakah kamu jadi gajah? Ulurkan tanganmu seperti belalai! "
                "GAJAH! Kamu adalah superstar!"
            ),
            "song": (
                "Ayo nyanyikan lagu hewan! "
                "BEBEK bilang kwek kwek kwek! "
                "KUCING bilang meong meong meong! "
                "KATAK bilang koak koak koak! "
                "GAJAH bilang tut tut tut! "
                "Hewan ada di mana-mana! Hewan ada di mana-mana! "
                "Bebek, kucing, katak, gajah! Hore!"
            ),
            "outro": (
                "Kamu belajar BEBEK, KUCING, KATAK, dan GAJAH hari ini! "
                "Kamu adalah ahli hewan! "
                "Aku Roundy si Beruang dan hewan juga sahabat terbaikku! "
                "Sampai jumpa! Dadah!"
            ),
        },
    },
}

SECTIONS = ["intro", "scene1", "scene2", "scene3", "scene4", "song", "outro"]


async def generate_file(text: str, voice: str, out_path: Path) -> bool:
    try:
        comm = edge_tts.Communicate(text=text, voice=voice, rate="-10%", pitch="+5Hz")
        await comm.save(str(out_path))
        return True
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


async def generate_episode(episode_key: str, lang: str, force: bool) -> tuple[int, int, int]:
    if episode_key not in EPISODES:
        print(f"Unknown episode: {episode_key}")
        return 0, 0, 0
    ep = EPISODES[episode_key]
    if lang not in ep:
        print(f"No {lang} script for episode {episode_key}")
        return 0, 0, 0

    scripts = ep[lang]
    voice = VOICES[lang]
    out_dir = OUT_DIR / lang / episode_key
    out_dir.mkdir(parents=True, exist_ok=True)

    ok = skip = fail = 0
    for section in SECTIONS:
        if section not in scripts:
            continue
        out_path = out_dir / f"{episode_key}_{section}.mp3"
        if out_path.exists() and not force:
            print(f"  ✓ {out_path.name} — skip")
            skip += 1
            continue
        print(f"  Generating {out_path.name}...", end=" ", flush=True)
        success = await generate_file(scripts[section], voice, out_path)
        if success:
            size_kb = out_path.stat().st_size // 1024
            print(f"✓ {size_kb}KB")
            ok += 1
        else:
            fail += 1
        await asyncio.sleep(0.3)

    return ok, skip, fail


async def main_async(args):
    episodes_to_run: list[tuple[str, str]] = []

    if args.all:
        for ep in EPISODES:
            for lng in VOICES:
                episodes_to_run.append((ep, lng))
    elif args.episode:
        langs = [args.lang] if args.lang else list(VOICES.keys())
        for lng in langs:
            episodes_to_run.append((args.episode, lng))
    else:
        print("Specify --episode <name> or --all")
        return

    total_ok = total_skip = total_fail = 0
    for ep_key, lng in episodes_to_run:
        print(f"\n[{ep_key} / {lng}]")
        ok, skip, fail = await generate_episode(ep_key, lng, args.force)
        total_ok += ok; total_skip += skip; total_fail += fail

    print(f"\n{'='*50}")
    print(f"Total: {total_ok} generated, {total_skip} skipped, {total_fail} failed")
    print(f"Output: {OUT_DIR}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", help=f"Episode key: {', '.join(EPISODES.keys())}")
    parser.add_argument("--lang",    choices=list(VOICES.keys()), help="Language (default: all)")
    parser.add_argument("--all",     action="store_true", help="Generate all episodes × all languages")
    parser.add_argument("--force",   action="store_true", help="Overwrite existing files")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
