# Kids Channel — AI Video Automation

Это проект автоматической генерации детских YouTube-видео в стиле Hey Bear Sensory.
**Отдельный проект**, не связан с MedMind.

## Проект

- **GitHub:** https://github.com/mikagit25/forkids (ветка main)
- **Путь:** `/opt/kids_channel/`
- **Вход:** команда `kids` (tmux сессия "kids")

## Stack

- Python 3 + moviepy + Pillow + librosa + numpy
- Анимации: bounce, sway, pulse, spin, float (синхронизация с BPM)
- Рендер: 1920×1080, 30fps, H.264+AAC
- Загрузка: YouTube Data API v3

## Структура

```
scripts/
  generate_video.py   — главный генератор видео
  upload_youtube.py   — загрузка на YouTube
  scheduler.py        — ежедневный планировщик
  setup_assets.py     — генерация спрайтов и тестовой музыки
config/
  settings.yaml       — FPS, цвета, размеры спрайтов, расписание
  playlists.yaml      — темы, теги, описания для YouTube
assets/
  sprites/{theme}/    — PNG спрайты (fruits/vegetables/animals/shapes)
  music/              — royalty-free MP3/WAV лупы
  logo.png            — водяной знак
credentials/
  youtube_client.json — OAuth 2.0 (добавить вручную из Google Cloud Console)
  token.pickle        — токен (создаётся автоматически)
output/               — готовые MP4
uploaded/             — архив загруженных видео
```

## Быстрые команды

```bash
# Генерация тестового видео (1 минута)
python3 scripts/generate_video.py --theme fruits --duration 1 --output output/test.mp4

# Генерация полного видео (30 минут)
python3 scripts/generate_video.py --theme animals --duration 30

# Загрузка на YouTube
python3 scripts/upload_youtube.py --file output/video.mp4 --status unlisted

# Ежедневный запуск (тест без генерации)
python3 scripts/scheduler.py --dry-run

# Пересоздать спрайты и тестовую музыку
python3 scripts/setup_assets.py
```

## Cron (ежедневная загрузка)

```
0 8 * * * cd /opt/kids_channel && python3 scripts/scheduler.py >> logs/cron.log 2>&1
```

## Push на GitHub

```bash
cd /opt/kids_channel && git add -A && git commit -m "..." && git push
```

## Темы

| Тема        | Спрайтов | Описание                     |
|-------------|----------|------------------------------|
| fruits      | 10       | Фрукты с мордашками          |
| vegetables  | 8        | Овощи с мордашками           |
| animals     | 10       | Животные                     |
| shapes      | 6        | Геометрические фигуры        |

## Этапы разработки

- **Этап 1 (MVP) ✅** — базовая анимация, музыка, загрузка, планировщик
- **Этап 2** — Telegram-уведомления при ошибке
- **Этап 3** — Suno API (оригинальная музыка), Stable Diffusion (новые спрайты)
- **Этап 4** — Мультиязычные каналы (EN, RU, ES, DE, TR, AR)

## YouTube API

- Credentials: `credentials/youtube_client.json` (скачать из Google Cloud Console → OAuth 2.0)
- При первом запуске `upload_youtube.py` откроется браузер для авторизации
- `madeForKids: True` выставлено автоматически
