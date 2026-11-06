# HANDOFF — Hy-Nomas Docker Compose (web + single-GPU backend)

## Текущее состояние

Стек поднят и проверен 2026-11-05:

| Компонент | Состояние | Адрес |
|---|---|---|
| React UI | работает | `http://localhost:7878/` |
| Hy-Nomas API | работает, модель загружена | `http://localhost:7879/` |
| API через UI origin | работает | `http://localhost:7878/health`, `/v1/config` |

`docker compose ps` показывает три контейнера с общим префиксом:
`hynomas-web`, `hynomas-backend` и `hynomas-worker`.

## Архитектура

`apps/frontend` подключён к `apps/seg_ar_gateway.py`; GPU-модель работает в
отдельном queue worker на основе `apps/seg_ar_web_server.py`. Gateway добавляет
загрузку изображений, Gallery, durable queue, shares и session API. Это не
frontend для Reactor Runtime: его отдельный клиент находится в `reactor/demo`.

API-образ `hy-nomas-api` — тонкий слой поверх уже рабочего
`hynomasoss/hynomasoss:cu130`. Поэтому он повторно использует CUDA/PyTorch и
модели, с которыми работает:

```bash
sh/run_hynomas_16.sh apps/cs-skins-city-complete/scenario_all_keys.json
```

`docker/run_api.py` применяет тот же безопасный FP8 decoder patch для RTX 5090,
после чего запускает single-GPU low-memory worker. `docker/run_gateway.py`
запускает gateway, наполняет Gallery существующими MP4 и использует локальное
описание изображения, когда отдельный Nomas-PE сервис отсутствует.

Gallery хранит реальные ролики в `gallery/media/favorites` и индекс в
`gallery/.media_items.json`. При старте gateway исключает побайтные дубликаты из
видимого пользовательского индекса, не удаляя MP4, и скрывает встроенную
frontend-карточку, если отсутствует её MP4. При наличии настоящих demo-файлов
адаптер показывает шесть актуальных официальных `curated-20261022-*` карточек
перед пользовательскими `favorites`. `make gallery-ensure` скачивает эти MP4
с официального сайта только при отсутствии и проверяет pinned SHA-256.
Устаревшие локальные карточки скрываются; пользовательские генерации запрещено
копировать под именами встроенных demo-видео.
GPU worker использует стабильный id
`hynomas-worker:seg-ar-slot-0`, поэтому рестарты не накапливают устаревшие
worker-записи.

nginx опубликован на `localhost:7878`, отдаёт SPA и проксирует same-origin
запросы `/health`, `/v1/*`, `/outputs/*` и `/gallery/*` в gateway. Backend отдельно
опубликован на `localhost:7879`.

Persistent bind mounts:

- `.runtime/hynomas` — очередь, настройки и compiler cache;
- `outputs/web` — uploads, reference images, generated videos и metadata;
- `gallery` — Gallery media и индекс;
- `models` и `models/hf_cache` — веса и Hugging Face cache.

DCAE-V encoder находится в
`models/VAE/DCAE-V/dc-ae-v-1.0-f32t4c32-bf16.pt`. `make models-ensure`
проверяет DiT, PixelUMM и DCAE-V и скачивает только отсутствующий checkpoint
на pinned revision. Загруженные изображения получают локальное безопасное
описание, если отдельный Nomas-PE endpoint не настроен; сами пиксели кодируются
DCAE-V и остаются источником визуального состояния.

## Управление

```bash
make compose-build
make compose-up
make compose-restart
make compose-rebuild
make compose-smoke
make compose-persistence-check
make compose-logs
make compose-down
```

`make up` и `make rebuild` сначала выполняют `make models-ensure`. Проверка
использует pinned revision и скачивает только отсутствующие checkpoints;
повторные старты используют `models/` и `models/hf_cache` без загрузки заново.

Короткие эквиваленты: `make up`, `make restart`, `make rebuild`, `make logs`,
`make ps`, `make down`.

После изменения образов сначала выполнить `make compose-build`, затем один раз
`make compose-up`. Модели смонтированы из `./models`, результаты пишутся в
`./outputs/web`.

## Последняя проверка

Зелёные цели:

- `make compose-smoke`
- `make compose-persistence-check` — upload/settings/Gallery пережили restart
- `make bdd` — 5 passed
- `make spec-coverage` — 3 требования / 3 тега
- `make spec-validate` — 2 passed

Логи и terminal receipts лежат в `.agent/check-logs/`.
