# Воспроизведение официальных curated-видео

Все команды выполняются из корня `Hy-Nomas`. Не запускайте генерацию, пока GPU
занята. Source pack и проверки GPU не используют.

## 1. Проверить источники

```bash
make upstream-sources-check
jq '.cases[] | {slug, exact_replay, missing}' \
  reproductions/upstream-curated/manifest.json
```

Исходник metadata — pinned production bundle официального сайта. В каждой папке:

- `upstream-gallery-entry.json` — неизменённая публичная запись и prompt timeline;
- `provenance.json` — URL и SHA-256 bundle/video;
- `availability.json` — что опубликовано и чего не хватает;
- `camera-control.json` — интервалы camera control и trajectory, если она
  опубликована (у этих шести точная trajectory не опубликована);
- `scenario.json` — CLI/Web adapter, только если exact replay возможен;
- `web-replay.json` — настройки UI и тот же structured JSON.

## 2. Проверить GPU перед запуском

```bash
nvidia-smi
docker compose ps
```

CLI и Compose worker нельзя одновременно держать на одной GPU. Для CLI сначала
остановите Compose; bind mounts и файлы при этом сохраняются:

```bash
make down
```

## 3. Точные CLI replay

Upstream полностью опубликовал text timeline только для трёх видео:

```bash
make upstream-cli UPSTREAM_CASE=snow-palace-ascent
make upstream-cli UPSTREAM_CASE=voxel-adventure
make upstream-cli UPSTREAM_CASE=kitchen-stories
```

Каждая команда создаёт новый каталог `outputs/<timestamp>/` и ничего не
перезаписывает. Модели берутся из `models/` и повторно не скачиваются.

## 4. Точные Web replay

После завершения CLI поднимите стек и дождитесь `ready`:

```bash
make up
until curl -fsS http://127.0.0.1:7878/health | jq -e \
  '.worker_status == "ready"' >/dev/null; do sleep 5; done
```

Для каждого полного кейса откройте соответствующий `web-replay.json`:

```bash
jq . reproductions/upstream-curated/snow-palace-ascent/web-replay.json
jq . reproductions/upstream-curated/voxel-adventure/web-replay.json
jq . reproductions/upstream-curated/kitchen-stories/web-replay.json
```

В `http://localhost:7878` создайте New world с полями из `setup`, затем вставьте
массив `scenario` одним JSON в поле direction. UI распознаёт structured SegAR
JSON и передаёт его без prompt enhancer. Компактный payload можно получить так:

```bash
make upstream-web-payload UPSTREAM_CASE=snow-palace-ascent
make upstream-web-payload UPSTREAM_CASE=voxel-adventure
make upstream-web-payload UPSTREAM_CASE=kitchen-stories
```

## 5. Три неполных upstream-кейса

Точное воспроизведение ниже невозможно из публичных данных; launcher намеренно
не создаёт для них `scenario.json` и не выдумывает отсутствующие значения.

```bash
jq . reproductions/upstream-curated/snow-palace-walk/availability.json
jq . reproductions/upstream-curated/coastal-waterfall/availability.json
jq . reproductions/upstream-curated/street-coffee/availability.json
```

- `snow-palace-walk`: отсутствуют prompts 1, 3, 4 и camera trajectory 6–18 с;
- `coastal-waterfall`: отсутствует camera trajectory 29–40.458333 с;
- `street-coffee`: отсутствуют prompts 4 и 5 (32–41.625 с).

Их можно повторить только после получения этих исходников у upstream. Любая
ручная реконструкция должна сохраняться под другим именем, например
`scenario.local-reconstruction.json`, и сравниваться как approximate, не exact.

## 6. Сравнить upstream и локальный результат

Укажите полученный MP4. Команды не изменяют исходные ролики:

```bash
CASE=snow-palace-ascent
GENERATED=outputs/<timestamp>/<generated>.viewable.mp4
UPSTREAM=gallery/media/curated-20261022-${CASE}.mp4

for VIDEO in "$UPSTREAM" "$GENERATED"; do
  printf '%s\n' "$VIDEO"
  ffprobe -v error \
    -show_entries stream=codec_name,width,height,r_frame_rate,duration \
    -of json "$VIDEO"
done

mkdir -p "comparisons/$CASE"
ffmpeg -y -i "$UPSTREAM" -i "$GENERATED" -filter_complex \
  '[0:v]scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2[left];[1:v]scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2[right];[left][right]hstack=inputs=2[out]' \
  -map '[out]' -shortest "comparisons/$CASE/side-by-side.mp4"
```

Слева будет официальный upstream, справа — локальная генерация. Поскольку
генерация стохастическая, совпадение SHA/пикселей не ожидается; сравнивайте
сюжетные события, длительности сегментов, ракурс и сохранение субъекта.

## 7. Проверки без генерации

```bash
make upstream-sources-check
make bdd
make spec-coverage
make spec-validate
```

`outputs/20261106_002609/` — незавершённая OOM-попытка, MP4 там не создан.
