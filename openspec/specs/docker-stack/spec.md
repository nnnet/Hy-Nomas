# docker-stack Specification

## Purpose

Локальный Docker Compose стек предоставляет совместимые друг с другом web UI
и одногпуговый Hy-Nomas backend, используя уже проверенное CUDA-окружение.

## Requirements

### Requirement: REQ-docker-stack-001 UI обращается к backend через один origin
Docker Compose стек SHALL отдавать React UI на `localhost:7878` и проксировать его
same-origin запросы `/health`, `/v1/*` и `/outputs/*` в Hy-Nomas backend,
доступный на `localhost:7879` и запущенный с single-GPU low-memory весами.
Локальный Compose-оверлей SHALL явно задавать
`parallelism.tp_size=1`, чтобы новый multi-GPU TP default апстрима не
применялся к несовместимым с TP INT8 DiT-весам.
Имена web, gateway и GPU worker контейнеров SHALL начинаться с общего префикса
`hynomas-`.

#### Scenario: UI и backend доступны на назначенных портах
- **WHEN** стек Docker Compose поднят и backend готов
- **THEN** корень `localhost:7878` возвращает HTML приложения
- **AND** `/health` через `localhost:7878` возвращает JSON backend со статусом `ok`
- **AND** прямой `/health` через `localhost:7879` возвращает тот же статус
- **AND** single-GPU worker запущен с `parallelism.tp_size=1`
- **AND** все контейнеры имеют префикс `hynomas-`

### Requirement: REQ-docker-stack-002 Пользовательские данные переживают рестарт
Стек SHALL хранить очередь и настройки в `.runtime/hynomas`, загруженные
изображения и результаты в `outputs/web`, Gallery-индекс и его видео в
`gallery`, а модели и кэши — в явных bind mounts. Gateway SHALL предоставлять
маршруты загрузки изображений и Gallery после рестарта контейнеров без потери
ранее записанных файлов и индексов. Gallery SHALL показывать один элемент для
одинакового содержимого среди пользовательских сохранений и SHALL отдавать
каждое видимое видео браузеру. Встроенные upstream demo-карточки SHALL
отображаться независимо от пользовательских сохранений, когда соответствующие
MP4 присутствуют в примонтированной Gallery. Стек SHALL NOT подставлять
пользовательскую генерацию вместо отсутствующего встроенного demo-видео;
карточка SHALL оставаться видимой, но ложный media URL SHALL NOT воспроизводиться.

#### Scenario: Загрузки и Gallery доступны после рестарта
- **WHEN** пользователь загрузил изображение и Gallery содержит видео
- **AND** контейнеры были перезапущены
- **THEN** запись загруженного изображения доступна по прежнему id
- **AND** Gallery возвращает сохранённые видео
- **AND** worker снова сообщает состояние `ready`

### Requirement: REQ-docker-stack-003 Upstream-примеры имеют проверяемый source pack
Локальный оверлей SHALL раскладывать шесть официальных curated-видео по отдельным
каталогам в `reproductions/upstream-curated/`. Каждый каталог SHALL содержать
неизменённую публичную Gallery-запись, provenance с URL и SHA-256 upstream bundle
и видео, опубликованный prompt timeline и явный статус доступности исходных
prompt/camera данных. Полный CLI/Web replay SHALL создаваться только для примера,
у которого upstream опубликовал весь timeline и не оставил camera-control
trajectory скрытой. Отсутствующие prompts или camera trajectory SHALL быть
помечены как недоступные и SHALL NOT заменяться придуманными значениями.
CLI adapter SHALL явно отключать TP для single-GPU INT8 replay.
Созданные контейнером artifacts SHALL возвращаться владельцу
рабочего каталога, чтобы H.264-копия сохранялась рядом с
оригиналом, а не в `/tmp`.

#### Scenario: Исходники upstream разложены без реконструкции скрытых данных
- **WHEN** source pack извлечён из pinned official bundle
- **THEN** существуют шесть отдельных каталогов с проверяемым provenance
- **AND** полные text-only примеры имеют одинаковый JSON для CLI и Web replay
- **AND** CLI adapter запускает INT8 replay с `parallelism.tp_size=1`
- **AND** CLI wrapper возвращает владение output-файлами локальному пользователю
- **AND** частичные примеры не объявлены доступными для exact replay
- **AND** camera-control сегменты без опубликованной trajectory содержат `null`
