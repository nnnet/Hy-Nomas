# Шаблон JSON-сценария для Hy-Nomas

Этот файл — справочник для LLM при создании новых JSON-сценариев в папке `apps/cs-skins-city-complete/`. Каждый ключ описан с примером значения. JSON должен быть массивом объектов (каждый объект = одна запись/видео).

## Структура массива

```json
[
  { ...ключи записи... }
]
```

---

## Ключи верхнего уровня (каждая запись)

| Ключ | Тип | Описание | Пример |
|------|-----|----------|--------|
| `test_id` | строка | Уникальный идентификатор записи | `"cs-skins-city-pulemot-01"` |
| `test_type` | строка | Тип теста / жанр контента | `"cs_skins_city_2d"` |
| `test_focus` | строка | Фокус сцены (ггерой / действие) | `"pulemot_trade_lock"` |
| `dimension` | строка | Размерность контента | `"emotion"` |
| `benchmark_kind` | строка | Вид загрузки: `whole_item` или `events` | `"whole_item"` |
| `trajectory_family` | строка | Семейство камеры | `"camera_none"` |
| `trajectory_class` | строка | Класс камеры | `"static"` |
| `trajectory_variant` | строка | Вариант камеры | `"none"` |
| `duration_bucket` | строка | Диапазон длительности | `"8-18s"` |
| `total_duration` | число | Общая длина видео в секундах | `17` |
| `perspective` | строка | Ракурс съёмки | `"first_person"` |
| `perspective_compatibility` | строка | Формат кадра | `"vertical_1080x1920"` |
| `scene_type` | строка | Тип сцены | `"interior"` |
| `scene_category` | строка | Категория сцены | `"apartment"` |
| `content_domain` | строка | Домен контента | `"cs_skins_city"` |
| `game_genre` | строка | Жанр игры | `"counter_strike"` |
| `obstacle_meta` | строка | Препятствие / сюжетный крючок | `"trade_lock_7_days"` |
| `camera_trajectory_spec` | объект или `null` | Спецификация траектории камеры (если есть NPZ-файл) | `null` |
| `joint_control_spec` | объект или `null` | Управление камерой (совместное) | `null` |
| `evaluation_criteria` | объект или `null` | Критерии оценки | `null` |
| `org_raw_id` | строка | Исходный идентификатор (для имени файла) | `"cs-skins-city-pulemot-01"` |
| `image_reference` | объект или `null` | Референсное изображение героя (фото для генерации внешности) | `{...}` |
| `segments` | массив | Массив сцен (см. ниже) | `[...]` |
| `subject_list` | массив | Список героев (см. ниже) | `[...]` |

---

## Ключи внутри массива `segments`

| Ключ | Тип | Описание | Пример |
|------|-----|----------|--------|
| `segment_index` | число | Индекс сцены (0, 1, 2...) | `0` |
| `segment_control` | объект или `null` | Управление сценой | `null` |
| `joint_caption_constraint` | объект или `null` | Ограничение подписи | `null` |
| `start_time` | строка | Начало сцены, формат `MM:SS.mmm` | `"00:00.000"` |
| `end_time` | строка | Конец сцены, формат `MM:SS.mmm` | `"00:06.000"` |
| `visual_description_long` | строка | Полное описание сцены (основной текст подсказки генерации) | `"Плоская 2D-заливка... Пулемёт ставит чашку..."` |
| `description_change` | строка или `null` | Описание изменения в сцене | `null` |
| `contained_actions` | массив | Действия внутри сцены (см. ниже) | `[...]` |

---

## Ключи внутри массива `contained_actions`

| Ключ | Тип | Описание | Пример |
|------|-----|----------|--------|
| `start_time` | строка | Начало действия | `"00:00.000"` |
| `end_time` | строка | Конец действия | `"00:03.000"` |
| `action_description` | строка | Описание действия | `"Пулемёт ставит чашку на подоконник"` |

---

## Ключи внутри массива `subject_list`

| Ключ | Тип | Описание | Пример |
|------|-----|----------|--------|
| `subject_id` | строка | Идентификатор героя | `"<|Subject1|>"` |
| `display_name` | строка | Имя героя | `"Пулемёт"` |
| `subject_attribute` | строка | Описание героя и его визуальных знаков | `"Антропоморфный ствол, оливковая куртка, жёлтые ботинки"` |
| `image_reference` | объект или `null` | Референсное фото героя (загружается в веб-UI или указывается по URL) | `{...}` |

### Ключи внутри `image_reference`

| Ключ | Тип | Описание | Пример |
|------|-----|----------|--------|
| `id` | строка | Идентификатор референса | `"img_pulemot"` |
| `url` | строка | Путь к изображению относительно репозитория | `"apps/cs-skins-city-complete/assets/pulemot_reference.jpg"` |
| `width` | число | Ширина изображения | `512` |
| `height` | число | Высота изображения | `512` |
| `caption` | строка или `null` | Описание референса | `"Референс героя Пулемёт"` |

---

## Пример полной записи

```json
[
  {
    "test_id": "cs-skins-city-pulemot-01",
    "test_type": "cs_skins_city_2d",
    "test_focus": "pulemot_trade_lock",
    "dimension": "emotion",
    "benchmark_kind": "whole_item",
    "trajectory_family": "camera_none",
    "trajectory_class": "static",
    "trajectory_variant": "none",
    "duration_bucket": "8-18s",
    "total_duration": 17,
    "perspective": "first_person",
    "perspective_compatibility": "vertical_1080x1920",
    "scene_type": "interior",
    "scene_category": "apartment",
    "content_domain": "cs_skins_city",
    "game_genre": "counter_strike",
    "obstacle_meta": "trade_lock_7_days",
    "camera_trajectory_spec": null,
    "joint_control_spec": null,
    "evaluation_criteria": null,
    "org_raw_id": "cs-skins-city-pulemot-01",
    "segments": [
      {
        "segment_index": 0,
        "segment_control": null,
        "joint_caption_constraint": null,
        "start_time": "00:00.000",
        "end_time": "00:06.000",
        "visual_description_long": "Плоская 2D-заливка... Пулемёт в оливковой куртке ставит чашку на подоконник.",
        "description_change": null,
        "contained_actions": [
          {
            "start_time": "00:00.000",
            "end_time": "00:03.000",
            "action_description": "Пулемёт ставит на подоконник чашку чая."
          }
        ]
      }
    ],
    "subject_list": [
      {
        "subject_id": "<|Subject1|>",
        "display_name": "Пулемёт",
        "subject_attribute": "Антропоморфный ствол в оливковой куртке и жёлтых ботинках"
      }
    ]
  }
]
```

---

## Правила заполнения

- Массив верхнего уровня может содержать несколько записей — каждая порождает своё видео.
- `total_duration` должна совпадать с суммой длительностей сцен.
- `start_time` / `end_time` в секундах с точностью до миллисекунд, формат `00:00.000`.
- `visual_description_long` — самый важный ключ: именно его текст передаётся в генерацию видео.
- Пустые значения (`null`, `""`) допустимы, код их пропустит.
- Файл должен быть валидным JSON.
- Сохраняйте в папку `apps/cs-skins-city-complete/` с именем `scenario_*.json`.

---

## Команда генерации

```bash
./run_hynomas_16.sh apps/cs-skins-city-complete/scenario_<имя>.json
```

Видео появится в папке `outputs/YYYYMMDD_HHMMSS/` (с временной меткой запуска).

---

## Как загружать картинки (image_reference)

Поле `image_reference` позволяет передать референсное фото героя для визуальной консистентности при генерации. Два способа:

### Способ 1: Указать путь в JSON
В ключе `image_reference.url` укажите относительный путь к файлу изображения внутри репозитория:

```json
"image_reference": {
  "id": "img_pulemot",
  "url": "apps/cs-skins-city-complete/assets/pulemot_reference.jpg",
  "width": 512,
  "height": 512,
  "caption": "Референс героя Пулемёт"
}
```

Файл изображения положите в папку `apps/cs-skins-city-complete/assets/` (создайте её, если нет).

### Способ 2: Загрузить через веб-интерфейс
Когда бэкенд запущен (`make cuda-build` + `docker compose up -d`):

1. Откройте `http://localhost:7878`
2. В разделе "Image reference" нажмите кнопку **"Upload image"**
3. Выберите файл изображения (PNG/JPEG, до 8 MiB)
4. Изображение сохранится во временное хранилище бэкенда и будет использовано как референс внешности героя при генерации

### Требования к изображениям
- Формат: PNG или JPEG
- Максимальный размер: 8 MiB
- Рекомендуемое разрешение: 512×512 или выше

---

## Команда генерации

```bash
./run_hynomas_16.sh apps/cs-skins-city-complete/scenario_<имя>.json
```

Видео появится в папке `outputs/YYYYMMDD_HHMMSS/` (с временной меткой запуска).
