# Happy Bear Kids — Roadmap

**Канал:** @HappyBearKids1 | UCIOerrKr02oTAAk2_oOg0Xg  
**Принцип:** Сделать один раз → запускать автоматически.  
**Лимит нового канала:** 6 видео/день (2 длинных + 4 шортса)

---

## Статус фаз на 2026-05-24

```
Фаза 1  Качественные спрайты     ██████████ 100%  ✅
Фаза 2  Видео-движок             ██████████ 100%  ✅
Фаза 3  Контент-конвейер         ██████████ 100%  ✅
Фаза 4  Образовательный контент  ██████████ 100%  ✅
Фаза 5  Автопилот                ████████░░  80%  ⚠️  (баги в кроне)
Фаза 6  Публикация и расписание  ░░░░░░░░░░   0%  ⬜
Фаза 7  Thumbnails               ░░░░░░░░░░   0%  ⬜
Фаза 8  Плейлисты                ░░░░░░░░░░   0%  ⬜
Фаза 9  Мониторинг               ░░░░░░░░░░   0%  ⬜
Фаза 10 Расширение контента      ░░░░░░░░░░   0%  ⬜
```

---

## ✅ Фаза 1 — Спрайты (DONE)

- 13 животных (Kenney CC0 Round style)
- 15 фруктов (OpenMoji CC BY-SA)
- 8 фигур (PIL programmatic: circle, square, triangle, rectangle, oval, star, heart, diamond)
- Музыка: 20 треков Kevin MacLeod CC0

---

## ✅ Фаза 2 — Видео-движок (DONE)

- 7 хореографий: grid_bounce, grid_sway, carousel, parade, line_h, diagonal_in, zigzag
- TextOverlay: буква/цифра/слово + анимация fade+bounce
- gTTS voiceover: 111 MP3, 8 паков
- YouTube Shorts: вертикальный рендер 720×1280, флаг `--shorts`
- Beat sync через librosa BPM detection

---

## ✅ Фаза 3 — Контент-конвейер (DONE)

- `batch_generate.py` → генерирует по `weekly_plan.yaml`
- `publish_queue.py` → загружает из `output/queue/`
- `generate_script.py` → YAML сцены из шаблона
- `upload_youtube.py` → загрузка, описания из `channel_metadata.yaml`

---

## ✅ Фаза 4 — Образовательный контент (DONE)

9 типов видео с шаблонами:

| Тип | Шаблон | Длина | Тема |
|-----|--------|-------|------|
| dance | default.yaml | 30 мин | animals/fruits |
| abc | abc.yaml | 6 мин | animals/fruits |
| numbers | numbers.yaml | 2 мин | animals |
| colors | colors.yaml | 2 мин | animals |
| short_letter | shorts_letter.yaml | 60с | animals |
| short_number | shorts_number.yaml | 60с | animals |
| short_color | shorts_color.yaml | 60с | animals |
| short_shape | shorts_shape.yaml | 60с | **shapes** |
| short_dance | shorts_dance.yaml | 60с | animals/fruits |

Voiceover паки: abc(26), numbers(20), colors(8), shapes(8), vocabulary(18), counting(15), colors_objects(8), shapes_colors(8)

---

## ⚠️ Фаза 5 — Автопилот (80%, есть баги)

### Что работает:
- `plan_week.py` — умная ротация контента без повторов
- Cron Sunday: генерирует план + видео
- Cron Mon-Sat: публикует

### 🐛 КРИТИЧЕСКИЕ БАГИ — исправить в первую очередь:

**Баг 1: Публикуется 1 видео/день вместо 6**
```
# Текущий крон (НЕВЕРНО):
0 9 * * 1-6  publish_queue.py --limit 1

# Нужно: 6 запусков по расписанию из weekly_plan
0 9  * * 1-6  publish_queue.py --limit 1
0 11 * * 1-6  publish_queue.py --limit 1
0 13 * * 1-6  publish_queue.py --limit 1
0 15 * * 1-6  publish_queue.py --limit 1
0 17 * * 1-6  publish_queue.py --limit 1
0 19 * * 1-6  publish_queue.py --limit 1
```

**Баг 2: Plan покрывает только Mon-Wed (3 дня), Thu-Sat пустые**
- `plan_week.py` генерирует 18 видео (6/день × 3 дня)
- Нужно 36 видео (6/день × 6 дней Mon-Sat)
- Исправить: расширить `build_plan()` на 6 дней

**Баг 3: Нет scheduled publishing**
- Видео загружается сразу как `public`, а не в запланированное время
- YouTube API поддерживает `status.publishAt` (ISO 8601 datetime)
- Улучшение: рассчитывать `publishAt` из `upload_day` + `upload_time`

---

## ⬜ Фаза 6 — Правильная публикация (СЛЕДУЮЩЕЕ)

### 6.1 Исправить крон (приоритет 1)
```python
# В publish_queue.py добавить scheduled publishing:
"status": {
    "privacyStatus": "private",
    "publishAt": "2026-05-26T09:00:00Z",  # ISO 8601
    "madeForKids": True,
}
# Тогда одна загрузка — YouTube сам опубликует в нужное время
```

### 6.2 Расширить план на 6 дней
- `plan_week.py`: цикл по 6 дням вместо 3
- `batch_generate.py`: генерировать 36 видео/неделю
- Воскресный крон успеет сгенерировать ~36 видео за ночь

### 6.3 Защита от дублей
- Проверять uploaded/ перед генерацией того же типа/темы/недели
- Не загружать одно видео дважды

---

## ⬜ Фаза 7 — Кастомные Thumbnails

Каждое видео должно иметь уникальный thumbnail (влияет на CTR напрямую).

### 7.1 `scripts/generate_thumbnail.py`
- Шаблон: цветной фон + персонаж + большой текст
- Разные стили по типу: dance (весёлый), abc (буква крупно), numbers (цифра)
- Разрешение: 1280×720 (YouTube max)

### 7.2 Авто-загрузка thumbnail
- `upload_youtube.py`: после загрузки видео → `youtube.thumbnails().set(...)`
- Генерировать thumbnail в `batch_generate.py` перед рендером

---

## ⬜ Фаза 8 — Плейлисты

YouTube алгоритм продвигает видео из плейлистов.

### 8.1 Создать плейлисты через API
```
🎵 Dance & Music       (все dance видео)
🔤 Learn ABC           (все abc видео + short_letter)
🔢 Numbers & Counting  (numbers + short_number)
🎨 Learn Colors        (colors + short_color)
⭐ Shapes for Kids     (shapes + short_shape)
🐻 Happy Bear Shorts   (все #shorts)
```

### 8.2 `scripts/manage_playlists.py`
- Создание плейлистов при первом запуске
- Авто-добавление видео в нужный плейлист после загрузки

---

## ⬜ Фаза 9 — Мониторинг и уведомления

### 9.1 Telegram-бот уведомления
- ✅ Успешная загрузка: "Загружено: [title] → youtu.be/ID"
- ❌ Ошибка загрузки: "Ошибка: quota exceeded / auth failed"
- 📊 Еженедельный отчёт: просмотры, подписчики, топ видео

### 9.2 YouTube Analytics мониторинг
- `scripts/analytics.py` — дёргает YouTube Analytics API
- Метрики: views, watchTime, subscribers, impressionClickThroughRate
- Сохранять в CSV для анализа трендов

### 9.3 Health check
- Проверять что очередь не пустая перед кроном
- Алерт если видео не загрузилось 2 дня подряд

---

## ⬜ Фаза 10 — Расширение контента

### 10.1 Новые типы видео (voiceover уже готов!)
| Тип | Описание | Voiceover пак |
|-----|----------|---------------|
| vocabulary | "This is an apple!" — объект + слово | vocabulary ✅ |
| counting_objects | "1 cat, 2 cats, 3 cats" — счёт предметов | counting ✅ |
| colors_objects | "The apple is red!" | colors_objects ✅ |
| shapes_colors | "A green circle!" | shapes_colors ✅ |

Нужно только создать scene templates + добавить в TEMPLATE_MAP.

### 10.2 Vegetables тема
- Скачать овощи с OpenMoji (морковь, брокколи, кукуруза...)
- Добавить в `download_sprites.py`
- Тема `vegetables` в ротации

### 10.3 Сезонный контент
- Шаблоны: Christmas (декабрь), Halloween (октябрь), Easter (апрель)
- Переопределять bg_color + спрайты на праздничные

### 10.4 Расширение ABC
- Shorts по 5 букв: A-E, F-J, K-O, P-T, U-Z (5 уникальных шортсов)
- Сейчас все shorts_letter показывают одинаковые A-E

---

## ⬜ Фаза 11 — Масштабирование

### 11.1 Второй язык
- gTTS уже поддерживает `lang="es"`, `lang="ru"` и др.
- Дублировать voiceover паки на испанский
- Отдельная очередь для ES контента

### 11.2 Оптимизация рендера
- Параллельный рендер нескольких видео (multiprocessing)
- Кэширование фреймов спрайтов для ускорения
- Целевое время: 30-мин видео за < 15 мин

### 11.3 A/B тесты thumbnails
- Загружать 2 варианта thumbnail, через 48ч менять на лучший по CTR

---

## Приоритеты на ближайшие сессии

### Сессия 1 — Исправить конвейер (СРОЧНО)
1. Баг 1: крон → 6 запусков/день
2. Баг 2: plan_week.py → 6 дней
3. Scheduled publishing через `publishAt`

### Сессия 2 — Thumbnails
4. `generate_thumbnail.py`
5. Авто-загрузка в upload_youtube.py

### Сессия 3 — Плейлисты + мониторинг
6. `manage_playlists.py`
7. Telegram уведомления

### Сессия 4 — Расширение контента
8. Новые типы (vocabulary, counting_objects)
9. Vegetables тема
10. Расширение ABC shorts (A-E, F-J, K-O, P-T, U-Z)

---

## Метрики успеха

| Период | Цель | Что нужно |
|--------|------|-----------|
| Месяц 1 | 50+ видео на канале | Исправить конвейер, загружать 6/день |
| Месяц 2 | 1000 просмотров | Thumbnails, плейлисты, SEO |
| Месяц 3 | 100 подписчиков | Трейлер, end screens, регулярность |
| Год 1 | 1000 подписчиков | Монетизация YouTube Partner Program |
