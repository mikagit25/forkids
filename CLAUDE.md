# Happy Bear Kids + Sacred Drift — Claude Code Context v2.2

**Отдельный проект от MedMind.** Работать только из `/opt/kids_channel/`.  
GitHub: https://github.com/mikagit25/forkids

> **СТРАТЕГИЯ v2.2 (с октября 2026):** 3 активных канала: EN детский, Sacred Drift (медитация/фокус), Calm Classics (классика, спит).  
> AR канал (@happybearkidsar) **перепрофилирован в Sacred Drift** — детский контент туда НЕ идёт.  
> Триаж сценариев: https://docs.google.com/spreadsheets/d/15jxsyr1sTL9Ciy3Fh5e7ONbhnni28hjyM4mkZ3VPTYQ

---

## YouTube каналы

| Канал | Тип | Хэндл | Channel ID | Токен | Очередь |
|-------|-----|--------|------------|-------|---------|
| **Happy Bear Kids** | Детский EN | @HappyBearKids1 | UCIOerrKr02oTAAk2_oOg0Xg | `credentials/youtube_token.json` | `output/queue/` |
| **Sacred Drift** *(бывш. AR)* | Взрослый EN | @SacredDrift | UCTAAc0Ih4PpwY9agi2tT8Gg | `credentials/youtube_token_ar.json` | `sacred_drift/output/queue/` |
| **Calm Classics** *(бывш. ID)* | Взрослый EN | @happybearkidsin | UCOozTZwjXgkfYiTAzSzePAA | `credentials/youtube_token_id.json` | `output/queue_id/` |

> ⚠️ `youtube_token_ar.json` — это токен Sacred Drift (взрослый канал медитации), НЕ детский AR!  
> AR-очередь `output/queue_ar/` заморожена. AR-контент не генерировать.

- GCP проект: `kids-chanel-497308` (588442208504) — отдельный от MedMind
- `made_for_kids: true` — **только Happy Bear Kids EN**
- `made_for_kids: false` — **обязательно** для Sacred Drift и Calm Classics (монетизация!)
- YouTube категория: `"10"` (Music) для Sacred Drift и Calm Classics; `"27"` (Education) для EN детского

### Аутентификация (OAuth)
```bash
python3 scripts/reauth_youtube.py              # EN канал
python3 scripts/reauth_youtube.py --channel ar # Sacred Drift (бывш. AR)
python3 scripts/reauth_youtube.py --channel id # Calm Classics канал
```

### Sacred Drift — отдельная инфраструктура
- Конфиг: `sacred_drift/config/channel_metadata_sd.yaml`
- Очередь: `sacred_drift/output/queue/` → `--queue sd`
- Живые стримы: 21:00–07:00 UTC ежедневно (`live_stream.py --channel sd --slot eu`)
- **ЗАПРЕЩЕНО стримить классику (Musopen)** — Content ID риск на весь канал; все `*_classics_*` мета имеют `stream_safe: false`
- Генерация: `generate_sd_compilation.py`, `generate_sacred_drift.py`
- YouTube категория 10 (Music), `made_for_kids: false`

---

## РАСПИСАНИЕ ПУБЛИКАЦИЙ v2.2

| Канал | Тип | Слоты | Кол-во |
|-------|-----|-------|--------|
| EN (Happy Bear) | длинные | ежедневно 18:00 UTC | 7/нед |
| EN (Happy Bear) | шортсы | ежедневно 10:30 UTC, до 3 шт | 7/нед |
| **Sacred Drift** | длинные | ежедневно 20:00 UTC | 7/нед |
| **Sacred Drift** | шортсы | ежедневно 10:00 UTC | 7/нед |
| **Sacred Drift** | **live stream** | 21:00–07:00 UTC ежедневно | ежедневно |
| Calm Classics | длинные | по мере генерации | по наличию |

**AR канал заморожен** — `queue_ar/` не трогать, AR контент не генерировать.  
Sacred Drift — день-недели ротация: Пн=классика, Вт=лечение, Ср=природа, Чт=фокус, Пт=сакральное, Сб=джаз, Вс=космос.

---

## ПРАВИЛА ГЕНЕРАЦИИ ВИДЕО

### 1. Каждое видео ОБЯЗАНО иметь три файла перед публикацией
```
output/queue/my_video_20260614.mp4          ← само видео
output/queue/meta_my_video_20260614.yaml    ← заголовок + описание + теги + language
output/queue/thumb_my_video_20260614.png    ← превью (1280×720, через Together.ai)
```
publish_queue.py **не опубликует** видео если любого из трёх нет.

### 2. Мета-файл: обязательные поля
```yaml
title: "..."            # не пустой
description: "..."      # минимум 200 слов, хэштеги в конце
tags: [...]             # до 40 тегов
video_type: dance       # см. таблицу типов ниже
language: en            # en или ar (id для Calm Classics = en!)
is_short: false         # true для Shorts (≤60с)
status: public
made_for_kids: false    # false для Calm Classics, true для EN/AR детских
```

### 3. Язык и канал

> **ВАЖНО: Sacred Drift и Calm Classics — ВЗРОСЛЫЕ каналы.**  
> Детский контент туда НЕ идёт. `queue_id` и `sacred_drift/output/queue/` ≠ дети.  
> `youtube_token_ar.json` = Sacred Drift (взрослый), НЕ детский AR!

| Канал | Очередь | `--queue` флаг | Разрешённый контент |
|-------|---------|----------------|-------------------|
| EN детский (@HappyBearKids1) | `output/queue/` | `en` | Всё детское: dance, vocab, nursery, emotions, lullaby, etc. |
| **Sacred Drift** (@SacredDrift) | `sacred_drift/output/queue/` | `sd` | Meditation, chakra, solfeggio, ambient, nature sounds, AI compilations |
| **Calm Classics** (@happybearkidsin) | `output/queue_id/` | `id` | `sleep_program`, `focus_program`, `visual_theme`, `nature_calm` — классика |
| ~~AR~~ (заморожен) | `output/queue_ar/` | `ar` | **НЕ ГЕНЕРИРОВАТЬ** |

**Правило lang в сценариях:**
- `lang=en` → только EN канал
- `lang=ar` → **ЗАМОРОЖЕН**, не использовать
- `lang=kids` → только EN — для детского no-text контента
- `lang=id` → только Calm Classics
- `lang=sd` → только Sacred Drift
- `lang=both` → EN + AR (заморожен — не использовать)

**Перекрёстный контент (изредка):**
- Классическая музыка (kids_classical_*) → EN детский канал с `made_for_kids: true`
- Детские персонажи, dance videos, ABC, счёт → **никогда на Sacred Drift или Calm Classics**

### 4. Описание по языку
- EN/CC → английский + английские хэштеги
- AR → арабский + арабские хэштеги
- Минимум 200 слов. Для классической музыки: атрибуция композитора/исполнителя/лицензии.

### 4а. Правила превью (thumbnails)
- **EN/CC** → FLUX prompt на английском, текст разрешён
- **AR** → FLUX prompt на английском + суффикс `no text, no letters, no words, no numbers`

### 5. Рендеры — ПОСЛЕДОВАТЕЛЬНО
Сервер: 15GB RAM. Одновременный запуск двух Remotion = OOM crash.
```bash
bash scripts/run_renders_sequential.sh   # правильно
```

### 6. Музыкальное лицензирование (ОБЯЗАТЕЛЬНО для Calm Classics)
- Все классические записи → `assets/music/classical/licenses.yaml`
- Источник: Musopen (musopen.org) — только `license: pd` или `license: cc0`
- `license: rejected` → файл НЕ использовать
- Content ID споры → решить в течение 48 часов

### 7. Музыкальные треки — ТОЛЬКО СОБСТВЕННЫЕ (с июля 2026)

**Kevin MacLeod ЗАПРЕЩЁН** — больше не используем ни в видео, ни в описаниях.

| Контент | Музыка |
|---------|--------|
| Детские видео (EN/AR) | Suno AI-треки из `assets/audio/suno/` |
| Классика / Calm Classics | Musopen PD/CC0 из `assets/music/classical/Music/` |

- Треки для Remotion: `remotion/public/music/` (туда копируются нужные файлы)
- Instr. треки (фон для DanceSpriteLong): `Afternoon in F v2`, `Tide and Piano v2`, `Morning Trail v2` и т.д.
- Сборники песен: `scripts/generate_song_compilation.py` (18 EN-песен / 7 AR-песен, 25 мин)
- В мета-описании: `🎵 Original music by Happy Bear Kids (AI-generated, © 2026)` (EN)
  или `🎵 موسيقى أصلية من هابي بير كيدز` (AR)
- **НИКОГДА** не писать "Kevin MacLeod", "incompetech", "CC Attribution" в описаниях

### 7а. Процедурная музыка (код, без ИИ) — основной источник для Sacred Drift
`scripts/generate_ambient_audio.py` синтезирует эмбиент с нуля (numpy/scipy): пэды со сменой
аккордов и тональностей, поющие чаши, гонги, колокольчики, дроны, дождь, реверб. Без сэмплов,
без ИИ-моделей → нет риска Content ID, нет лимитов, бесплатно.

```bash
python3 scripts/generate_ambient_audio.py --list-styles
python3 scripts/generate_ambient_audio.py --style bowls --minutes 12 --count 4     # 4 трека подряд
python3 scripts/generate_ambient_audio.py --style solfeggio --hz 432 --minutes 60
python3 scripts/generate_ambient_audio.py --style sleep --minutes 480 --format flac  # 8 ч
```
- Стили: `bowls`, `cosmic`, `sleep` (−20 LUFS), `solfeggio --hz N`, `rain`, `morning`. Остальные −18 LUFS.
- Частоты: `--hz` любое значение (без флага — случайно из 111…963), `--register -12` — глубже пэд,
  `--binaural 4` — бинауральные биения (левое ухо hz, правое hz+4; в названии «Binaural Beats»).
- Дождь: по умолчанию `--rain window` (за открытым окном, с накатами как волны), `inside` — приглушённо
  из комнаты, `outside` — открытый. У каждого режима своё название («Soft Rain Heard From Indoors» и т.д.).
- Чаши: `--variant ringing` (звонкие), `slow` (редкие удары, долгое звучание, эхо, большой зал),
  `deep` (низкие чаши + гонг). Без флага — случайно, спокойные варианты чаще. Свои названия:
  «Tibetan Singing Bowls», «Slow Tibetan Bowls Meditation», «Deep Tibetan Bowls & Gong».
- Каждый трек получает описание характера (звук, слои, пространство, темп, «Best for …») в
  `ambient_log.jsonl`; `generate_sd_compilation.py` вставляет их в описание видео блоком «About this session».
- Разнообразие: каждый seed = свой рецепт (тональность, прогрессия, длина аккорда, тембр пэда
  soft/dark/warm/hollow/glass, слои gong/chimes/choir/waves/shimmer/plucks/thunder, размер реверба, темп).
  Новый трек автоматически перегенерируется, если похож на один из 8 последних того же стиля
  (или совпадает имя). Рецепт пишется в `ambient_log.jsonl`. Отключить: `--allow-repeat`.
- Выход: `sacred_drift/audio/code_ambient/<Title> (<seed>).mp3`, журнал `ambient_log.jsonl`
  (seed + параметры = доказательство авторства; трек воспроизводится по seed).
- `generate_sd_compilation.py` подхватывает эту папку автоматически; категория — по ключевым словам в названии.
- Подпись в описании ставится сама: «Original music composed and synthesized by Sacred Drift» (не писать «AI»).
- Скорость ~7 с на минуту аудио, память ~0.5 ГБ при любой длине (рендер кусками по 30 с).
- НЕ зацикливать один короткий трек в длинное видео (reused content). Генерировать нужную длину.
- Вокал, джаз, живые инструменты → по-прежнему ИИ-сервис (Suno/Mureka/Lyria) или Musopen.

### 8. Suno (AI-музыка)
- Требует активной платной подписки + документация промпта
- Нельзя упоминать известных артистов по имени
- В мета: `ai_generated: true`

---

## ТРИАЖ СЦЕНАРИЕВ v2.1

**Источник правды:** https://docs.google.com/spreadsheets/d/15jxsyr1sTL9Ciy3Fh5e7ONbhnni28hjyM4mkZ3VPTYQ

### Статусы:
| Статус | Значение |
|--------|----------|
| `frozen` | Не генерировать. Массовые серии v1, нет данных аналитики |
| `frozen_id` | Заморожено до Phase 3-4 (Индонезийский канал, месяц 3-4) |
| `candidate` | Пилот после получения данных аналитики. Не массово |
| `reuse_now` | Переиспользовать с доработкой под v2.1 |
| `new_v2` | Новый контент, создавать по плану фаз |

### Замороженные типы (НЕ ГЕНЕРИРОВАТЬ):
`color_learn`, `number_learn`, `shape_learn`, `shape_learn_v2`, `dance_shape`,
`dance_pet`, `dance_item`, `dance_fruits_group`, `dance_fruits_2stage`,
`wiggle_party`, `transform_block`, `sensory_loop`, `ocd_vehicles`,
`construction_music`, `shape_roundelay`, `satisfying_loop`, `learn_to_talk`,
`interactive_coview`, `nursery_id` (до месяца 3-4)

### Активные треки (генерировать):
| Трек | Типы | Приоритет |
|------|------|-----------|
| `calm_classics` | `sleep_program`, `focus_program`, `visual_theme` | 1 |
| `kids_sleep` | `lullaby_long` (Musopen), `sleep_lullaby` | 1 |
| `kids_song` | `bubble_pop_song`, `song_suno` | 1 |
| `shorts` | `sleep_short` (45с из лупов) | 2 |
| `kids_quality` | pilot: `emotions_ocean`×1, `special_mechanics`×1 | 3 |
| `ar_kids` | `nursery_ar` — проверить права записи | 2 |

---

## ФАЗЫ РАЗРАБОТКИ v2.1

### Phase 0 ✅ (Дни 1-2) — Инфраструктура
- [x] Заморожен v1-контент (перемещён в hold)
- [x] Обновлён кроник (новое расписание)
- [x] Создан `channel_metadata_cc.yaml`
- [x] Создана структура `assets/music/classical/`
- [x] Создан `config/sleep_programs/`
- [x] Обновлён CLAUDE.md

### Phase 1 (Недели 1-2) — Аудио-фундамент
- [ ] Загрузить 30-50 записей из Musopen
- [ ] Заполнить `assets/music/classical/licenses.yaml`
- [ ] Создать `config/sleep_programs/sleep_chopin_01.yaml` и др. (ids 101-108)

### Phase 2 (Недели 2-3) — Видео-движок
- [ ] Remotion-компонент `SleepClassicalLoop`
  - Темы: `night_bear` / `moon_clouds` / `warm_waves` / `rain_window`
  - Правило периодов: все периоды анимации делятся на длину лупа нацело
  - Длина лупа: 240с (moon_clouds) / 300с (night_bear)
- [ ] `generate_sleep_classical.py` — сборка 1h/3h/8h из лупов через FFmpeg
- [ ] `make_sleep_short.py` — 45с вертикальный шорт из лупа

### Phase 3-4 (Недели 3-8) — Контент
- [ ] 8 sleep_program (ids 101-108): Chopin, Debussy, Bach focus, Mozart
- [ ] `lullaby_long` с Musopen-музыкой (Brahms, Schubert, Satie, Bach)
- [ ] `nature_calm` как визуал для Calm Classics
- [ ] Аналитика: `scripts/analytics_report.py` (id 112)

### Phase 5-6 (Месяц 2-3) — Оригинальный контент
- [ ] Suno: "Goodnight, Little Bear" — 65 BPM, F major (id 111)
- [ ] `bubble_pop_song` — фирменная песня EN (id 33)
- [ ] Пилоты kids_quality: `emotions_ocean`×1, `special_mechanics`×1

### Цель монетизации Calm Classics
- 1000 подписчиков + 4000 часов просмотра → YPP к месяцу 3-4
- Go/No-go решение по аналитике к месяцу 6

---

## ПРАВИЛА ПУБЛИКАЦИИ

```bash
# Проверить очереди
python3 scripts/publish_queue.py --dry-run --queue en --type long
python3 scripts/publish_queue.py --dry-run --queue ar --type long
python3 scripts/publish_queue.py --dry-run --queue id --type long   # Calm Classics

# Thumbnails
python3 scripts/generate_ai_thumbs.py --queue all --backend together

# Плейлисты
python3 scripts/manage_playlists.py --list
```

## МУЛЬТИЯЗЫЧНЫЕ ЗАГОЛОВКИ (YouTube Localizations)

Одно видео на EN канале — YouTube показывает локализованный заголовок/описание по региону зрителя.  
Языки: **es** (испанский), **fr** (французский), **pt** (португальский/Бразилия), **id** (индонезийский).  
Перевод через Together.ai LLM (Llama-3.3-70B). Теги не переводятся (YouTube не поддерживает per-lang теги).

```bash
# Одно видео по ID
python3 scripts/localize_video.py --video-id VIDEO_ID_HERE
python3 scripts/localize_video.py --video-id VIDEO_ID_HERE --channel id  # Calm Classics

# Видео из meta-файла (нужен youtube_id внутри)
python3 scripts/localize_video.py --meta output/queue/meta_myfile.yaml
python3 scripts/localize_video.py --meta output/queue_id/meta_myfile.yaml --channel id

# Только некоторые языки
python3 scripts/localize_video.py --meta output/queue/meta_myfile.yaml --langs es,fr

# Все видео в очереди с youtube_id (пакетная обработка)
python3 scripts/localize_video.py --queue              # EN kids (output/queue/)
python3 scripts/localize_video.py --queue --channel id # Calm Classics (output/queue_id/)

# Проверка без реальной загрузки
python3 scripts/localize_video.py --queue --dry-run
python3 scripts/localize_video.py --queue --channel id --dry-run
```

После успешной локализации в meta YAML добавляется поле `localized_langs: [es, fr, pt, id]` — повторный запуск пропустит уже обработанные видео.  
Для Calm Classics промпт перевода адаптирован под взрослый контент (классика / сон / фокус), не детский.

## Ассеты

- Спрайты: `assets/sprites_new/{animals,fruits,vegetables}/` (OpenMoji CC0)
- Музыка детская: `assets/music/kevin/` (Kevin MacLeod CC0)
- Музыка классическая: `assets/music/classical/` (Musopen PD/CC0)
- Voiceover EN: `assets/audio/voiceover/en/`
- Thumbnails: Together.ai FLUX.1-schnell (`credentials/together_api_key.txt`)
- Suno: `credentials/suno_session.txt` (когда настроен)

## Credentials

- `credentials/youtube_token.json` — EN канал
- `credentials/youtube_token_ar.json` — AR канал
- `credentials/youtube_token_id.json` — Calm Classics канал
- `credentials/youtube_client.json` — OAuth (в .gitignore, не коммитить!)
- `credentials/together_api_key.txt` — Together.ai для thumbnails

---

## ВИЗУАЛЬНЫЕ ПРАВИЛА (накоплены из git-истории)

Эти правила применяются ко ВСЕМ Remotion-компонентам и генераторам. Нарушение = регрессия.

### Rule 3 — Элементы всегда видимы
Минимальная opacity любого элемента ≥ 0.50 в любой момент времени.  
Частицы/светлячки: size ≥ 14px (не 6px). Нельзя делать элементы "почти невидимыми".

### Rule 4 — Только 3D спрайты
Использовать `_3d.png` Pixar-стиль спрайты из `remotion/public/sprites/`.  
CSS flat shapes и SVG — запрещены для основного контента.

### Rule 6 — Большие размеры спрайтов
Главный спрайт: **440–460px** (не 200-300px). Вторичные спрайты: **140–210px**.  
При изменении существующих размеров: увеличить на **+15%** от текущих.  
ColorLearnLong: 556px main, 484px song, 506px review, 414px outro, 210px intro.

### Rule 7 — Wobble (PIP/BWW) на всех спрайтах
Каждый блок motion должен иметь `"wobble": True`.  
В DanceSpriteLong: добавлять к каждому блоку в `blocks[]`.  
В DanceShapeLong: аналогично через `block.wobble`.  
Wobble = multi-frequency outline breathing, уникальный per-seed.

### Rule 8 — Независимые фазы движения
Каждый спрайт должен иметь уникальный `seed` (1, 2, 3, 4, 5...).  
Никакие два спрайта не должны двигаться синхронно.  
Для per-language вариаций: использовать `phaseOffset`.

### Rule 9 — Idle float всегда активен
Спрайты никогда не стоят на месте, даже в блоке NONE/default.  
Минимальное idle движение: `cx ±18px` sin-волна, `cy ±14px`, scale breathing `±4%`.  
В DanceSpriteLong это встроено в default case computeSpriteTransform().

### Rule 10 — 3D depth simulation (DanceSpriteLong v2)
Каждый спрайт может иметь `depth: 0–1` (0=дальний фон, 1=передний план, дефолт 0.5).  
Depth влияет на:  
- **Parallax**: `parallaxMult = 0.6 + depth * 0.8` (0.6–1.4) — ближние двигаются активнее  
- **Drop shadow**: глубина тени растёт с depth (4–16px offset, 8–24px blur, 10–32% opacity)  
- **Z-порядок**: спрайты рендерятся back-to-front по depth (painter's algorithm)

Новые типы движения (добавлены в v2):
- `ZFLOAT` — медленное breathing zoom (scale ±9%), имитирует подлёт к зрителю и отлёт  
- `YFLIP` — поворот по Y-оси через `scaleX = cos(phase)` (1→0→−1→0→1)

**Обратная совместимость**: `depth` опционально, дефолт 0.5 → `parallaxMult=1.0` → поведение идентично v1.

### Применение правил при написании новых генераторов
```python
# Правильный шаблон для DanceSpriteLong:
"sprites": [
    {"path": "characters/bear_happy_3d.png", "size": 460, "posX": 0.50, "posY": 0.44, "seed": 1},  # Rule 4, 6
    {"path": "objects/star_3d.png",          "size": 165, "posX": 0.18, "posY": 0.28, "seed": 2},  # Rule 6, 8
],
"blocks": [
    {"startSec": 0,   "endSec": 200, "motion": "FADEIN", "amplitude": 60, "wobble": True},  # Rule 7
    {"startSec": 200, "endSec": 700, "motion": "BOB",    "period": 3.5,  "amplitude": 45, "wobble": True},
    {"startSec": 700, "endSec": 1500,"motion": "WAVE",   "period": 4.0,  "amplitude": 55, "waveDelay": 0.5, "wobble": True},
]
