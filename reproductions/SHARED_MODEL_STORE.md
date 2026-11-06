# Общее хранилище моделей

Канонический корень:

```text
/mnt/A4C45B32C45B2C87/ai-models
```

## Структура

- `objects/sha256/<prefix>/<sha256>/data` — единственный физический
  экземпляр каждого checkpoint;
- `views/comfyui/` — категории ComfyUI;
- `views/hy-nomas/` — штатная структура `DiT/` и `VAE/`;
- `views/catalog/` — обзор модей по формату;
- `huggingface/` — общие Hub, Xet и assets caches;
- `manifests/` — инвентарь, карта миграции и terminal receipts;
- `incoming/` — временные копии до проверки SHA-256.

Каждый прежний путь модели остаётся рабочим символическим
ссылкам. Outputs, workflows, gallery и runtime в store не переносятся.

## Окружение

```bash
set -a && source reproductions/model-store.env && set +a
```

Для Docker тот же store монтируется в `/opt/ai-models`: objects и views
read-only, Hugging Face cache read-write. Проектные outputs остаются
в прежних volumes.

## ComfyUI

Скопировать или подключить
`reproductions/comfyui-extra-model-paths.yaml` как
`<ComfyUI>/extra_model_paths.yaml`. Все файлы в `views/comfyui` — ссылки
на проверенные canonical objects.

В Docker используйте вариант
`reproductions/comfyui-extra-model-paths.docker.yaml` и добавьте к сервису
ComfyUI следующие mounts (имя сервиса зависит от проекта):

```yaml
volumes:
  - /mnt/A4C45B32C45B2C87/ai-models/objects:/opt/ai-models/objects:ro
  - /mnt/A4C45B32C45B2C87/ai-models/views:/opt/ai-models/views:ro
  - /mnt/A4C45B32C45B2C87/ai-models/huggingface:/opt/ai-models/huggingface
```

Если контейнер читает прежнюю host-папку моделей, содержащую абсолютные
симлинки, дополнительно смонтируйте весь store по тому же абсолютному пути:

```yaml
volumes:
  - /mnt/A4C45B32C45B2C87/ai-models:/mnt/A4C45B32C45B2C87/ai-models:ro
```

Это требуется Docker: абсолютный симлинк разрешается в namespace контейнера,
а не хоста. Upstream compose-файлы других проектов миграция не меняет.

## Команды

```bash
make model-store-init
make model-store-audit
make model-store-check
make model-store-verify
make compose-config
```

`make model-store-migrate` меняет файлы и поэтому запускается только с
проверенным `MODEL_STORE_MANIFEST`. Мигратор не заменяет исходник,
пока временная копия не сброшена на диск и не проверена SHA-256.

Генерация и GPU для проверок store не используются.
