# Happy Bear Kids + Calm Classics — Claude Code Context v2.1

**Отдельный проект от MedMind.** Работать только из `/opt/kids_channel/`.  
GitHub: https://github.com/mikagit25/forkids

> **СТРАТЕГИЯ v2.1 (с июля 2026):** отказ от 18 видео/день. Упор на качество.  
> ID канал перепрофилирован в **Calm Classics** (взрослый, английский, сон/фокус).  
> Триаж сценариев: https://docs.google.com/spreadsheets/d/15jxsyr1sTL9Ciy3Fh5e7ONbhnni28hjyM4mkZ3VPTYQ

---

## YouTube каналы

| Канал | Тип | Хэндл | Channel ID | Токен | Очередь |
|-------|-----|--------|------------|-------|---------|
| **Happy Bear Kids** | Детский EN | @HappyBearKids1 | UCIOerrKr02oTAAk2_oOg0Xg | `credentials/youtube_token.json` | `output/queue/` |
| **Happy Bear Kids العربية** | Детский AR | @happybearkidsar | UCTAAc0Ih4PpwY9agi2tT8Gg | `credentials/youtube_token_ar.json` | `output/queue_ar/` |
| **Calm Classics** *(бывш. ID)* | Взрослый EN | @happybearkidsin | UCOozTZwjXgkfYiTAzSzePAA | `credentials/youtube_token_id.json` | `output/queue_id/` |

- GCP проект: `kids-chanel-497308` (588442208504) — отдельный от MedMind
- `made_for_kids: true` — только для EN и AR каналов
- `made_for_kids: false` — **обязательно** для Calm Classics (монетизация!)

### Аутентификация (OAuth)
```bash
python3 scripts/reauth_youtube.py              # EN канал
python3 scripts/reauth_youtube.py --channel ar # AR канал
python3 scripts/reauth_youtube.py --channel id # Calm Classics канал
```

---

## РАСПИСАНИЕ ПУБЛИКАЦИЙ v2.1

| Канал | Тип | Слоты | Кол-во |
|-------|-----|-------|--------|
| EN (Happy Bear) | длинные | ежедневно 18:00 | 7/нед |
| EN (Happy Bear) | шортсы | Вт/Чт/Сб 10:30 | 3/нед |
| AR (Happy Bear) | длинные | Пн+Чт 19:00 | 2/нед |
| AR (Happy Bear) | шортсы | Ср 09:00 | 1/нед |
| Calm Classics | длинные | Пн–Пт 20:00 | 5/нед |
| Calm Classics | шортсы | Пн/Ср/Пт 21:00 | 3/нед |

**Было:** 18 видео/день (6 EN + 6 AR + 6 ID). **Стало:** ~21 видео/нед на 3 канала.

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

> **ВАЖНО: Calm Classics / Classical Night Relax (@ClassicalNightRelax) — это ВЗРОСЛЫЙ канал.**  
> Детский контент туда НЕ идёт. `queue_id` ≠ дети.

| Канал | Очередь | Разрешённый контент |
|-------|---------|-------------------|
| EN детский (@HappyBearKids1) | `output/queue/` | Всё детское: dance, vocab, nursery, emotions, lullaby, etc. |
| AR детский (@happybearkidsar) | `output/queue_ar/` | Всё детское на арабском |
| **Calm Classics / CNRelax** | `output/queue_id/` | **ТОЛЬКО:** `sleep_program`, `focus_program`, `sleep_short`, `visual_theme`, `nature_calm` — классическая музыка / ambient для взрослых |

**Правило lang в сценариях:**
- `lang=en` → только EN канал
- `lang=ar` → только AR канал
- `lang=kids` → EN + AR (никогда не CNRelax) — для любого детского no-text контента
- `lang=id` → только CNRelax
- `lang=both` → EN + AR (с голосом/текстом, 2 рендера)
- `lang=all` → EN + AR + CNRelax — **только если контент одобрен для взрослого канала**

**Перекрёстный контент (изредка):**
- Классическая музыка может идти на детские каналы с детским thumbnail (`made_for_kids: true`)
- Абстрактные визуалы (nature_calm) могут дублироваться на CNRelax с взрослым meta
- Детские персонажи, dance videos, ABC, счёт, nursery rhymes → **никогда на CNRelax**

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

### 7. Suno (AI-музыка)
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
