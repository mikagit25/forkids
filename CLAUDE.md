# Happy Bear Kids — Claude Code Context

**Отдельный проект от MedMind.** Работать только из `/opt/kids_channel/`.  
GitHub: https://github.com/mikagit25/forkids

## YouTube каналы

| Канал | Язык | Хэндл | Channel ID | Google аккаунт | Токен | Очередь |
|-------|------|--------|------------|----------------|-------|---------|
| **Happy Bear Kids** | EN | @HappyBearKids1 | UCIOerrKr02oTAAk2_oOg0Xg | lapidainvest@gmail.com | `credentials/youtube_token.json` | `output/queue/` |
| **Happy Bear Kids العربية** | AR | @happybearkidsar | UCTAAc0Ih4PpwY9agi2tT8Gg | kidsar6945071@gmail.com | `credentials/youtube_token_ar.json` | `output/queue_ar/` |
| **Happy Bear Kids Indonesia** | ID | @happybearkidsin | UCOozTZwjXgkfYiTAzSzePAA | kidain6945071@gmail.com | `credentials/youtube_token_id.json` | `output/queue_id/` |

- GCP проект: `kids-chanel-497308` (588442208504) — отдельный от MedMind

### Аутентификация (OAuth)
```bash
python3 scripts/reauth_youtube.py              # EN канал
python3 scripts/reauth_youtube.py --channel ar # AR канал
python3 scripts/reauth_youtube.py --channel id # ID канал (нужен отдельный Google аккаунт)
```

### Статус каналов
- ✅ EN — авторизован, работает, видео публикуются
- ✅ AR — авторизован (`youtube_token_ar.json`), готов к публикации
- ✅ ID — авторизован (`youtube_token_id.json`), ждёт видео + раскомментировать cron
- Раскомментировать ID cron: убрать `#` перед строками `0 10/14/18 * * *` в crontab

---

## ПРАВИЛА ГЕНЕРАЦИИ ВИДЕО

### 1. Каждое видео ОБЯЗАНО иметь три файла перед публикацией
```
output/queue/my_video_20260614.mp4          ← само видео
output/queue/meta_my_video_20260614.yaml    ← заголовок + описание + теги + language
output/queue/thumb_my_video_20260614.png    ← превью (1280×720, через Together.ai)
```
publish_queue.py **не опубликует** видео если любого из трёх нет — это жёсткая проверка.

### 2. Мета-файл: обязательные поля
```yaml
title: "..."          # не пустой
description: "..."    # минимум 200 слов, хэштеги в конце
tags: [...]           # до 40 тегов
video_type: dance     # см. таблицу типов ниже
language: en          # en, ar или id
is_short: false       # true для Shorts (≤60с)
status: public
```

### 3. Язык строго отдельный для каждого канала
- **EN видео** (`language: en`) → `output/queue/` → EN канал
- **AR видео** (`language: ar`) → `output/queue_ar/` → AR канал
- **ID видео** (`language: id`) → `output/queue_id/` → Indonesian канал
- **Видео БЕЗ текста и голоса** → можно на несколько каналов (отдельные meta для каждого языка)
- **НЕЛЬЗЯ:** английский текст/голос на арабском или индонезийском канале

### 4. Описание должно быть на языке видео
- EN видео → описание полностью на английском + английские хэштеги
- AR видео → описание полностью на арабском + арабские хэштеги
- ID видео → описание полностью на индонезийском (Bahasa Indonesia) + индонезийские хэштеги
- Минимум 200 слов. Включать: что изучаем, образовательная ценность, серия, подписка, Kevin MacLeod attribution

### 4а. Правила превью (thumbnails) по языку
- **EN** → FLUX prompt на английском, текст в превью РАЗРЕШЁН (Latin script)
- **AR** → FLUX prompt на английском + суффикс `no text, no letters, no words, no numbers` — FLUX не понимает арабский
- **ID** → FLUX prompt на английском, текст РАЗРЕШЁН (Bahasa Indonesia — Latin script, как EN)
- Генерация: `python3 scripts/generate_ai_thumbs.py --queue id --backend together`

### 5. Рендеры запускать ПОСЛЕДОВАТЕЛЬНО (не одновременно)
Сервер: 15GB RAM. Одновременный запуск двух Remotion-рендеров = OOM crash.
```bash
# Правильно — один за другим:
bash scripts/run_renders_sequential.sh

# Неправильно — одновременно:
python3 generate_color.py & python3 generate_number.py &
```
Скрипт `run_renders_sequential.sh` управляет очерёдностью автоматически.

### 6. После рендера — всегда thumbnail
Скрипты `generate_color_learn_long.py` и `generate_number_learn_long.py` генерируют thumbnail автоматически через Together.ai после каждого успешного рендера.

Если thumbnail не сгенерировался (API ошибка, старый код) — запустить вручную:
```bash
python3 scripts/generate_color_learn_long.py --regen-meta
python3 scripts/generate_number_learn_long.py --regen-meta
python3 scripts/generate_ai_thumbs.py --queue en --backend together
python3 scripts/generate_ai_thumbs.py --queue ar --backend together
python3 scripts/generate_ai_thumbs.py --queue id --backend together
```

### 7. Dance-видео (Manim) требуют meta вручную
Manim-пайплайн (`generate_video.py`) не создаёт meta-файлы автоматически.
После генерации:
```bash
# Скопировать meta от предыдущей версии и обновить дату:
cp output/queue/meta_dance_animals_YYYYMMDD.yaml output/queue/meta_dance_animals_$(date +%Y%m%d).yaml
# Затем сгенерировать thumbnail:
python3 scripts/generate_ai_thumbs.py --queue en --backend together
```

---

## ПРАВИЛА ПУБЛИКАЦИИ (ОЧЕРЕДЬ)

### Расписание (cron ежедневно, 3 отдельных канала)
```
06:00  EN → output/queue/      07:00  AR → output/queue_ar/   08:00  ID → output/queue_id/
09:00  EN → output/queue/      10:00  ID → output/queue_id/   11:00  AR → output/queue_ar/
12:00  ID → output/queue_id/   13:00  EN → output/queue/      14:00  ID → output/queue_id/
15:00  AR → output/queue_ar/   16:00  ID → output/queue_id/   17:00  EN → output/queue/
18:00  ID → output/queue_id/   19:00  AR → output/queue_ar/   20:00  EN → output/queue/
21:00  AR → output/queue_ar/   22:00  EN → output/queue/      23:00  AR → output/queue_ar/
```
Итого: 6 EN + 6 AR + 6 ID = 18 длинных видео/день. Каждый канал — отдельный YouTube аккаунт и токен.

### publish_queue.py проверяет готовность автоматически
```bash
python3 scripts/publish_queue.py --dry-run --queue en --type long  # показать что готово
python3 scripts/publish_queue.py --queue en --type long --limit 1  # опубликовать 1
```
Видео без meta или без thumbnail будет пропущено с объяснением причины.

### Роутинг в плейлисты
manage_playlists.py автоматически добавляет по `video_type` + `language`:
- `video_type: numbers` + `language: ar` → плейлист `counting_ar`
- `video_type: colors` + `language: ar` → плейлист `colors_ar`
- `video_type: dance` + `language: ar` → плейлист `dance_ar`

### Порядок публикации внутри очереди
Файлы публикуются по времени создания (st_mtime), самые старые первыми.

---

## КОНВЕЙЕР

```
Генерация → output/queue/ + queue_ar/ + queue_id/ → (meta + thumb обязательны) → publish_queue.py → YouTube
```

```bash
# Проверить состояние очереди (сколько готово к публикации)
python3 scripts/publish_queue.py --dry-run --queue en --type long
python3 scripts/publish_queue.py --dry-run --queue ar --type long
python3 scripts/publish_queue.py --dry-run --queue id --type long

# Проверить прогресс рендеринга
tail -f logs/renders_sequential.log
tail -f logs/number_learn.log
tail -f logs/color_learn.log
```

---

## Типы видео — полная таблица генерации

**ИСТОЧНИК ПРАВДЫ:** Google Sheets → https://docs.google.com/spreadsheets/d/1MAHh_LxESZCd0sWOx0qAjSWWIElR79oTfo-XiPbJc7o  
**Оркестратор:** `python3 scripts/scenario_orchestrator.py` (читает Sheet, ставит статусы)  
Резервный фикс-скрипт: `bash scripts/run_renders_sequential.sh --from N`

### Все 39 сценариев (из Google Sheet — источник правды)

| # | type | key | lang | Статус | Скрипт/Remotion | Примечание |
|---|------|-----|------|--------|-----------------|------------|
| 1 | color_learn | purple | both | pending | generate_color_learn_long.py | Фиолетовый |
| 2 | number_learn | eleven | both | planned | generate_number_learn_long.py | NEEDS: добавить в number_learn_data.yaml |
| 3 | shape_learn | pentagon | both | planned | generate_shape_learn.py | NEEDS: добавить в SHAPES dict |
| 4-9 | nursery_id | balonku/cicak/naik_kereta/pelangi/dua_mata/kebunku | id | pending | generate_nursery_id.py | 6 индонезийских песен |
| 10-12 | nursery_ar | batta_batta/ya_matar/dajaja | ar | pending | generate_nursery_ar.py | 3 арабские песни |
| 13-14 | sensory_loop | sensory_1_3 / sensory_4_14 | both | pending | ⬜ NEEDS: SensoryLoop Remotion | 3+11 эпизодов |
| 15 | stars_bubbles | stars_bubbles | en | pending | StarsBubblesLong ✅ | 22 мин, POP sound |
| 16 | dance_shape | dance_shapes_series | both | pending | DanceShapeLong ✅ | 12 эпизодов × 25м |
| 17 | dance_pet | dance_pets_series | both | pending | ⬜ NEEDS: generate_dance_pet.py | 33 видео, кошки/собаки/etc |
| 18 | dance_item | dance_items_series | both | pending | ⬜ NEEDS: generate_dance_item.py | 25 предметов |
| 19 | lullaby_long | lullaby_nature | both | pending | ⬜ NEEDS: 1-2hr LullabyLong | 5-мин Remotion × FFmpeg loop |
| 20-24 | transform_block | fruits/color/physics/patterns/nature | both | pending | TransformLong ✅ | 5 блоков × 4 видео |
| 25 | dance_fruits_group | fruits_veg_group_8 | both | pending | ⬜ NEEDS: generate_fruits_group.py | 8 групповых видео |
| 26 | dance_fruits_2stage | fruits_veg_2stage | both | pending | ⬜ NEEDS: 2-stage Remotion | Без слов + обучение |
| 27 | learn_to_talk | learn_to_talk_series | en | pending | ⬜ NEEDS: LearnToTalk Remotion | Ms Rachel стиль, EN only |
| 28 | emotions_ocean | emotions_4series | both | pending | generate_emotions_ocean.py ✅ | 25 эпизодов скрипт готов |
| 29 | special_mechanics | special_mech_8series | both | pending | generate_special_mechanics.py ✅ | 8 эпизодов скрипт готов |
| 30 | shape_roundelay | shape_roundelay | both | pending | ⬜ NEEDS: ShapeRoundelay Remotion | Фигуры в хороводе |
| 31 | ocd_vehicles | vehicles_ocd_series | both | pending | ⬜ NEEDS: OCDVehicles Remotion | Грузовики, экскаваторы, поезда |
| 32 | construction_music | construction_instruments | both | pending | ⬜ NEEDS: новый Remotion | Инструменты строителя + музыкальные |
| 33 | bubble_pop_song | bubble_pop | en | planned | ⬜ NEEDS: BubblePop Remotion | Оригинальная хит-песня |
| 34 | satisfying_3fmt | satisfying_guess_surprise | both | pending | ⬜ NEEDS: 3 Remotion comp | Satisfying / Guess Sound / Surprise |
| 35 | nature_calm | nature_calm_cat2 | both | pending | ⬜ NEEDS: NatureCalm Remotion | Спокойная природа |
| 36 | interactive_coview | coview_cat3 | both | planned | ⬜ NEEDS: Interactive Remotion | Родитель+ребёнок |
| 37 | emotional_values | emotions_values_cat4 | both | pending | ⬜ NEEDS: EmotionalValues Remotion | Эмпатия/ценности |
| 38 | shorts_funnel | shorts_from_long | both | pending | clip script | Нарезка шортсов из лонгов |
| 39 | edu_entertain | edu_entertain_cat1 | both | planned | ⬜ NEEDS: EduEntertain Remotion | Обучение + развлечение |
| + | wiggle_party | animals/fruits/veg/mixed/night | both | pending | generate_wiggle_party.py ✅ | Добавлено в Sheet не было |

**Готовые скрипты (✅):** generate_special_mechanics.py, generate_emotions_ocean.py, generate_wiggle_party.py  
**Нужны новые Remotion-композиции (⬜):** SensoryLoop, dance_pet/item, LullabyLong(1-2hr), 2stage, LearnToTalk, ShapeRoundelay, OCDVehicles, BubblePop, Satisfying×3, NatureCalm, Interactive, EmotionalValues

### Шортсы (после завершения всех длинных видео)

Запускаются отдельно: `bash scripts/run_shorts.sh` (не входит в основной оркестратор)

| video_type | Скрипт | Длина | Каналы | Кол-во | Код |
|-----------|--------|-------|--------|--------|-----|
| short_vocab | `scripts/generate_vocab_shorts.py` | 55с | EN | A-Z=26 | ✅ |
| short_colorlearn | `scripts/generate_color_learn_shorts.py` | 55с | EN+AR+ID | 7×3=21 | ✅ |
| short_shape_float | `scripts/generate_shape_float_shorts.py` | 55с | EN | 8×4=32 | ✅ |
| short_shape_dance | `scripts/generate_shape_dance_shorts.py` | 55с | EN | 13 | ✅ |
| short_dance | `scripts/generate_animal_shorts.py` | 60с | EN | 20 | ✅ |
| short_dance | `scripts/generate_fruit_shorts.py` | 60с | EN | 12 | ✅ |
| short_dance | `scripts/generate_vegetable_shorts.py` | 60с | EN | 10 | ✅ |
| short_counting | `scripts/generate_counting_shorts.py` | 60с | EN | 8 | ✅ |
| short_shapes | `scripts/generate_shapes_shorts.py` | 60с | EN | 16 | ✅ |
| short_shape_float/dance | `scripts/generate_shape_notxt.py` | 55с | AR+ID | 45×2 | ✅ |

### Шортсы (после завершения всех длинных видео)

Запускаются отдельно: `bash scripts/run_shorts.sh` (не входит в основной оркестратор)

| video_type | Скрипт | Длина | Каналы | Кол-во | Код |
|-----------|--------|-------|--------|--------|-----|
| short_vocab | `scripts/generate_vocab_shorts.py` | 55с | EN | A-Z=26 | ✅ |
| short_colorlearn | `scripts/generate_color_learn_shorts.py` | 55с | EN+AR+ID | 7×3=21 | ✅ |
| short_shape_float | `scripts/generate_shape_float_shorts.py` | 55с | EN | 8×4=32 | ✅ |
| short_shape_dance | `scripts/generate_shape_dance_shorts.py` | 55с | EN | 13 | ✅ |
| short_dance | `scripts/generate_animal_shorts.py` | 60с | EN | 20 | ✅ |
| short_dance | `scripts/generate_fruit_shorts.py` | 60с | EN | 12 | ✅ |
| short_dance | `scripts/generate_vegetable_shorts.py` | 60с | EN | 10 | ✅ |
| short_counting | `scripts/generate_counting_shorts.py` | 60с | EN | 8 | ✅ |
| short_shapes | `scripts/generate_shapes_shorts.py` | 60с | EN | 16 | ✅ |
| short_shape_float/dance | `scripts/generate_shape_notxt.py` | 55с | AR+ID | 45×2 | ✅ |

**Remotion композиции:** NumberLearnLong, ColorLearnLong, ShapeLearnLong, CharacterDialogueLong, LullabyLong, NurseryRhymeLong, VocabularyShort, ColorLearnShort, ShapeFloatShort, ShapeDanceShort, ShapeFloatLong, ShapeDanceLong

---

## Быстрые команды

```bash
# Рендеринг (последовательно, не одновременно!)
bash scripts/run_renders_sequential.sh

# Thumbnails для всей очереди (если пропустили)
python3 scripts/generate_ai_thumbs.py --queue en --backend together
python3 scripts/generate_ai_thumbs.py --queue ar --backend together
python3 scripts/generate_ai_thumbs.py --queue id --backend together

# Переместить в hold (приостановить публикацию)
mv output/queue/video.mp4 output/hold/
mv output/queue/meta_video.yaml output/hold/
mv output/queue/thumb_video.png output/hold/

# Заменить видео на YouTube (удалить старое + загрузить новое)
python3 scripts/replace_youtube_videos.py --list
python3 scripts/replace_youtube_videos.py --delete VIDEO_ID
python3 scripts/replace_youtube_videos.py --upload output/queue_ar/new_video.mp4

# Плейлисты
python3 scripts/manage_playlists.py --list
python3 scripts/manage_playlists.py --add VIDEO_ID --video-type dance --language en
```

---

## Танцевальный конвейер (Фаза 11)

```bash
# 30-мин скрипты
python3 scripts/generate_dance_script.py --duration 30
python3 scripts/generate_fruit_dance_script.py --duration 30
python3 scripts/generate_vegetable_dance_script.py --duration 30

# 30-мин видео (каждое ~45-60 мин рендера, Manim)
python3 scripts/generate_video.py --theme animals --duration 30 \
  --script config/scripts/dance_animals.yaml \
  --output output/queue/dance_animals_$(date +%Y%m%d).mp4
# ВАЖНО: после этого создать meta вручную и thumbnail!

# Шортсы (42 шт: 20 животных + 12 фруктов + 10 овощей)
python3 scripts/generate_animal_shorts.py
python3 scripts/generate_fruit_shorts.py
python3 scripts/generate_vegetable_shorts.py
```

---

## Ассеты

- Спрайты: `assets/sprites_new/{animals,fruits,vegetables}/` (OpenMoji CC0)
- Музыка: `assets/music/kevin/` (14 треков Kevin MacLeod CC0)
- Voiceover EN: `assets/audio/voiceover/en/` (111 MP3)
- Thumbnails: Together.ai FLUX.1-schnell (ключ: `credentials/together_api_key.txt`)

## Credentials

- `credentials/youtube_client.json` — OAuth (в .gitignore, не коммитить!)
- `credentials/token.pickle` — токен (валиден, авторефреш)
- `credentials/together_api_key.txt` — Together.ai для thumbnail генерации

---

## Текущий статус рендеринга (обновить при смене)

| Скрипт | Статус | Видео | Очередь |
|---|---|---|---|
| number_learn | 🔄 в процессе | 10 цифр × 2 языка = 20 | queue/ + queue_ar/ (ID не готов) |
| color_learn | ⏳ ждёт number_learn | 9 цветов × 2 языка = 18 | queue/ + queue_ar/ (ID не готов) |

Следить: `tail -f logs/renders_sequential.log`

---

---

## ПРАВИЛО: ВИДЕО БЕЗ ТЕКСТА → ТРИ КАНАЛА

**Если видео не содержит текста/слов на экране и голосового сопровождения —**
оно публикуется на ВСЕХ ТРЁХ каналах (EN + AR + ID) с разными описаниями на каждом языке.

Это делается через:
1. Один рендер (один MP4 файл)
2. Копия MP4 кладётся в `output/queue/` (EN), `output/queue_ar/` (AR) и `output/queue_id/` (ID)
3. Для каждого канала — своя `meta_*.yaml` (EN / AR / ID описание)
4. Для каждого канала — свой `thumb_*.png`

**Почему:** пользователь читает описание на своём языке и понимает контент, хотя само видео одинаковое.

**ПО УМОЛЧАНИЮ: все новые серии без текста генерируются для всех 3 каналов.**

Примеры: ShapeLearnLong, ShapeFloatLong, shape_dance без меток, sensory_loop, lullaby, transform_block

---

## Серия: Shape Learn Long (8 видео, 30 мин, без текста)

Сценарий: Google Doc "⭕ ГЕОМЕТРИЧЕСКИЕ ФИГУРЫ"
Методика "One Concept Deep": Форма → Цвет → Количество → Гипно-петля

**Скрипт:** `scripts/generate_shape_learn.py`
**Composition:** `ShapeLearnLong` (Remotion, 1920×1080, 30 мин)

```bash
# Генерировать все 8 фигур (ЗАПУСКАТЬ ПОСЛЕ завершения number_learn + color_learn!)
python3 scripts/generate_shape_learn.py

# Одна фигура
python3 scripts/generate_shape_learn.py --shapes circle

# Регенерировать только мета+thumbnail (видео уже есть)
python3 scripts/generate_shape_learn.py --regen-meta
```

**Фигуры:** circle, square, triangle, star, diamond, heart, hexagon, oval

**Структура видео (30 мин):**
- INTRO (0–30с): Фигура падает с анимацией пружины
- FORM (30–630с): Фигура в разных размерах, повторяющиеся циклы
- COLOR (630–1080с): Фигура медленно меняет цвет через радугу
- COUNT (1080–1440с): 1→2→3 фигуры, визуальный счёт без цифр
- HYPNO (1440–1770с): Много фигур с дрейфом цвета, для сна
- OUTRO (1770–1800с): Фигура затухает

**Публикация:** 1 рендер → EN queue + AR queue + ID queue (отдельное описание на каждом языке)

---

## Следующие задачи (по приоритету)

1. ✅ **Публикация EN+AR+ID** — cron 3 канала, каждый публикует независимо
2. ✅ **number_learn** — видео EN+AR (ID pending: generate_number_learn_long.py для ID)
3. ✅ **color_learn** — видео EN+AR (ID pending: generate_color_learn_long.py для ID)
4. ✅ **publish_queue.py** — проверка meta+thumbnail перед публикацией
5. ✅ **ShapeLearnLong** — скрипт написан, генерирует EN+AR+ID
6. ✅ **Все серии без текста** — generate_* скрипты обновлены для 3 каналов
7. ⏸️ **Шортсы** — НЕ ТРОГАТЬ до завершения длинных видео
8. ⏸️ **ABC (Manim)** — на паузе, заменён Vocab Remotion. Контент в hold/hold_abc/

Полный роадмап: `ROADMAP.md`
