# Kids Channel + Calm Classics — Roadmap v2.1

> **Актуальная стратегия — в CLAUDE.md (фазы 0-6). Этот файл — история и статус.**  
> Устаревший v1 (Happy Bear Kids EN, 18 видео/день) → заморожен.

---

## Статус фаз v2.1 на 2026-07-08

### Phase 0 ✅ — Инфраструктура (дни 1-2)
- [x] Заморожен v1-контент (перемещён в hold/)
- [x] Обновлён кронтаб (v2.1 расписание: EN/AR/CC)
- [x] Создан config/channel_metadata_id.yaml (Classical Night Relax)
- [x] Создана структура assets/music/classical/
- [x] Создан config/sleep_programs/
- [x] Перебрендинг канала: 121 старое видео скрыто, 4 "night series" восстановлены с EN описаниями
- [x] Дубликаты в кронтабе удалены

### Phase 1 🔄 — Аудио-фундамент (недели 1-2)
- [x] 23 трека загружены из Musopen → assets/music/classical/Music/
- [x] licenses.yaml заполнен (23 трека, все license=pd)
- [ ] 30-50 треков (осталось скачать: Bach, Mozart, Debussy, Satie, Brahms, Schubert)
- [x] Программы созданы: sleep_swan_lake_01, sleep_chopin_01, focus_beethoven_01
- [ ] Программы заблокированы (нет аудио): focus_bach_01, focus_mozart_01, sleep_debussy_01, sleep_lullaby_01

### Phase 2 ✅ — Видео-движок (недели 2-3)
- [x] SleepClassicalLoop Remotion-компонент (4 темы: moon_clouds/night_bear/warm_waves/rain_window)
- [x] Все 4 лупа отрендерены (15/20/29/31 MB, без аудио)
- [x] generate_sleep_classical.py — сборка 1h/3h/8h из лупов + FFmpeg
- [x] make_sleep_short.py — 45с вертикальные шортсы из лупов
- [x] generate_ai_thumbs.py — поддержка sleep_program/focus_program типов (CC промпты)
- [x] publish_queue.py — распознаёт sleep_short_ префикс

### Phase 3-4 🔄 — Контент (недели 3-8)
**Сгенерировано:**
- [x] sleep_swan_lake_01 1h → queue_id ✅ (66MB, с тумбнейлом)
- [x] sleep_chopin_01 1h → queue_id ✅ (66MB, с тумбнейлом)
- [x] focus_beethoven_01 1h → queue_id 🔄 (кодируется, ~30 мин)
- [ ] sleep_swan_lake_01 3h+8h → кодируется в фоне
- [ ] sleep_chopin_01 3h+8h → кодируется в фоне
- [ ] focus_beethoven_01 3h → кодируется в фоне
- [x] 4 × sleep_short (45с, все 4 темы) → queue_id ✅
- [x] nature_calm_ocean_20260708.mp4 → queue_id ✅

**Заблокировано (нет аудио):**
- [ ] focus_bach_01 — нет треков Bach на диске
- [ ] focus_mozart_01 — нет треков Mozart
- [ ] sleep_debussy_01 — нет Debussy/Satie
- [ ] sleep_lullaby_01 — нет Brahms/Schubert

**Публикация CC (queue_id):**
- 4 long + 4 short в очереди
- Кронтаб: длинные Пн-Пт 20:00, шортсы Пн/Ср/Пт 21:00

### Phase 5-6 ⬜ — Оригинальный контент (месяц 2-3)
- [ ] Suno: "Goodnight, Little Bear" (65 BPM, F major)
- [ ] bubble_pop_song EN (id 33)
- [ ] emotions_ocean ×1 pilot
- [ ] special_mechanics ×1 pilot

---

## Цель монетизации Calm Classics
1000 подписчиков + 4000 часов просмотра → YPP к месяцу 3-4  
Go/No-go по аналитике к месяцу 6.

---

## Happy Bear Kids v1 (заморожено)

Исходный канал EN. Текущий контент в очереди автоматически публикуется.  
Новый v1-контент не генерируется (frozen статусы в CLAUDE.md).  
Аналитика после 4 недель → решение по типам контента (candidate → активация).

---

## Следующие действия

### Немедленно (когда появятся треки):
```bash
# После загрузки Bach/Mozart/Debussy/Satie/Brahms из Musopen:
python3 scripts/scan_music.py            # авто-регистрация в licenses.yaml
python3 scripts/generate_sleep_classical.py --program focus_bach_01    --durations 1 3
python3 scripts/generate_sleep_classical.py --program focus_mozart_01   --durations 1 3
python3 scripts/generate_sleep_classical.py --program sleep_debussy_01  --durations 1 3 8
python3 scripts/generate_sleep_classical.py --program sleep_lullaby_01  --durations 1 2
```

### Аналитика (фаза 3-4):
```bash
# После 4 недель публикации:
python3 scripts/analytics_report.py  # (ещё не создан)
```
