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

# Публикация из очереди (авто-thumbnail + плейлисты)
python3 scripts/publish_queue.py --dry-run
python3 scripts/publish_queue.py --limit 1
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

## Ассеты

- Спрайты: `assets/sprites/{animals,fruits,shapes}/`
- Музыка: `assets/music/kevin/` (20 треков Kevin MacLeod CC0)
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
4. **Новые типы:** vocabulary, counting_objects (voiceover уже готов)
5. **Vegetables** тема спрайтов

Полный роадмап: `ROADMAP.md`
