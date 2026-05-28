# Happy Bear Kids — Claude Code Context

**Отдельный проект от MedMind.** Работать только из `/opt/kids_channel/`.  
GitHub: https://github.com/mikagit25/forkids

## YouTube канал
- Название: **Happy Bear Kids** (не путать с "Happy Beer Kids" — опечатка исправлена)
- Хэндл: @HappyBearKids1
- ID: UCIOerrKr02oTAAk2_oOg0Xg
- GCP проект: `kids-chanel-497308` (588442208504) — отдельный от MedMind

## Конвейер

```
plan_week.py → weekly_plan.yaml → batch_generate.py → output/queue/ → publish_queue.py → YouTube
```

**Стратегия:** 6 видео/день = 2 длинных + 4 шортса  
**Cron:** воскресенье 02:00 генерация | пн-сб 9/11/13/15/17/19 публикация по 1

## Быстрые команды

```bash
# Тест плана
python3 scripts/plan_week.py --dry-run

# Генерация одного шортса
python3 scripts/generate_script.py --duration 1 --theme animals \
  --template config/scene_templates/shorts_letter.yaml
python3 scripts/generate_video.py --theme animals \
  --script config/scripts/episode_*.yaml --shorts --output output/test.mp4

# Загрузка
python3 scripts/upload_youtube.py \
  --file output/test.mp4 --video-type short_letter \
  --theme animals --title "..." --status public

# Thumbnails (авто при batch_generate, но можно вручную)
python3 scripts/generate_thumbnail.py --all-previews
python3 scripts/generate_thumbnail.py --type abc --letter A --word Apple --theme animals

# Плейлисты
python3 scripts/manage_playlists.py --create-all   # создать плейлисты на YouTube (1 раз)
python3 scripts/manage_playlists.py --list          # показать плейлисты и их ID
python3 scripts/manage_playlists.py --add VIDEO_ID --video-type dance

# Оформление канала
python3 scripts/generate_channel_art.py    # перегенерить баннер/иконку
python3 scripts/setup_channel.py --all     # применить через API

# Batch генерация (все видео по плану, авто-thumbnail)
python3 scripts/batch_generate.py --dry-run
python3 scripts/batch_generate.py

# Публикация из очереди (авто-thumbnail + плейлисты + scheduled publishing)
python3 scripts/publish_queue.py --dry-run
python3 scripts/publish_queue.py          # scheduled: видео приватные до времени публикации
python3 scripts/publish_queue.py --no-schedule  # сразу публичные
```

## Типы видео

| video_type | шаблон | длина | is_shorts |
|---|---|---|---|
| dance | default.yaml | 30м | — |
| abc | abc.yaml | 6м | — |
| numbers | numbers.yaml | 2м | — |
| colors | colors.yaml | 2м | — |
| short_letter | shorts_letter.yaml | 60с | ✅ |
| short_number | shorts_number.yaml | 60с | ✅ |
| short_color | shorts_color.yaml | 60с | ✅ |
| short_shape | shorts_shape.yaml | 60с | ✅ theme=shapes |
| short_dance | shorts_dance.yaml | 60с | ✅ |

## Танцевальный конвейер (Фаза 11)

```bash
# Генерация всех шортсов (42 штуки: 20 животных + 12 фруктов + 10 овощей)
python3 scripts/generate_animal_shorts.py        # --animals bear tiger ...
python3 scripts/generate_fruit_shorts.py         # --fruits apple banana ...
python3 scripts/generate_vegetable_shorts.py     # --vegetables carrot broccoli ...

# Генерация 30-мин скриптов
python3 scripts/generate_dance_script.py --duration 30
python3 scripts/generate_fruit_dance_script.py --duration 30
python3 scripts/generate_vegetable_dance_script.py --duration 30

# Генерация 30-мин видео (каждое ~45-60 мин рендера)
python3 scripts/generate_video.py --theme animals --duration 30 \
  --script config/scripts/dance_animals.yaml \
  --output output/queue/dance_animals_$(date +%Y%m%d).mp4
python3 scripts/generate_video.py --theme fruits --duration 30 \
  --script config/scripts/dance_fruits.yaml \
  --output output/queue/dance_fruits_$(date +%Y%m%d).mp4
python3 scripts/generate_video.py --theme vegetables --duration 30 \
  --script config/scripts/dance_vegetables.yaml \
  --output output/queue/dance_vegetables_$(date +%Y%m%d).mp4

# Предпросмотр (SSH туннель: ssh -L 8899:localhost:8899 root@38.19.202.103 -N)
python3 preview_server.py   # → http://localhost:8899
```

## Ассеты

- Спрайты новые: `assets/sprites_new/{animals,fruits,vegetables}/` (OpenMoji CC0)
- Спрайты старые: `assets/sprites/{animals,fruits,shapes}/`
- Музыка: `assets/music/kevin/` (14 треков в DANCE_TRACKS, Kevin MacLeod CC0)
- Voiceover: `assets/audio/voiceover/en/` (111 MP3)
- Оформление: `output/channel/{banner,icon,thumbnail_template}.png`

## Credentials

- `credentials/youtube_client.json` — OAuth (в .gitignore, не коммитить!)
- `credentials/token.pickle` — токен (валиден, авторефреш)
- Файлы исключены из git, хранятся только на сервере

## Следующие задачи (по приоритету)

1. ✅ **plan_week.py** → 6 дней (36 видео/неделю)
2. ✅ **generate_thumbnail.py** → авто-thumbnail для каждого видео
3. ✅ **manage_playlists.py** → плейлисты (создать через --create-all после сброса квоты)
4. ✅ **Новые типы:** short_vocabulary + short_counting добавлены
5. ✅ **Scheduled publishing** → publishAt через meta sidecar файлы
6. ✅ **Vegetables** тема спрайтов — 10 спрайтов + shorts + 30-мин скрипт
7. ✅ **Танцевальный конвейер** — 42 шортса (20 животных + 12 фруктов + 10 овощей)
8. ✅ **Публиковать на YouTube** — конвейер запущен, кронтаб Mon-Sat 6/день
9. 🔄 **Цветовые шортсы** — 24 шортса (8 цветов × 3 темы: animals/fruits/vegetables)
10. ⏸️ **ABC** — на паузе, удалено с YouTube. Нужен правильный маппинг букв→картинки.
    Животные покрывают: B=bear, C=cat/cow, D=dog/duck, E=elephant, F=fox/frog,
    G=goat?, K=koala, L=lion, M=monkey, O=owl, P=panda/pig/parrot/penguin, R=rabbit, T=tiger, U=unicorn
    Контент в hold: output/hold_abc/

Полный роадмап: `ROADMAP.md`
