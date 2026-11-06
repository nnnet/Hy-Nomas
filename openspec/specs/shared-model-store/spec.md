# shared-model-store Specification

## Purpose

Единое локальное хранилище исключает повторное хранение моделей в
проектах, сохраняя привычные пути через символические ссылки.

## Requirements

### Requirement: REQ-shared-model-store-001 Единый content-addressed store
Локальный оверлей SHALL предоставлять инструмент, который помещает
физическое содержимое модели в объект, адресуемый SHA-256. Повторный
файл с тем же хешем SHALL использовать уже существующий объект.

#### Scenario: Одинаковые файлы не дублируют физическое содержимое
- **WHEN** мигрируются два файла моделей с одинаковым SHA-256
- **THEN** оба исходных пути являются ссылками на один canonical object

### Requirement: REQ-shared-model-store-002 Безопасная миграция
Мигратор SHALL сначала создавать временную копию, проверять её SHA-256,
атомарно публиковать canonical object и только после этого заменять
исходный файл символической ссылкой. Миграция SHALL писать журнал
old-path → canonical-path и пропускать битые ссылки и недоступные пути.

#### Scenario: Исходник заменяется только после проверки объекта
- **WHEN** мигратор обрабатывает модель на другой файловой системе
- **THEN** данные копируются через temporary file, проверяются и лишь затем исходник заменяется ссылкой

### Requirement: REQ-shared-model-store-003 Общие пути ComfyUI, Hy-Nomas и Hugging Face
Локальный оверлей SHALL задавать `AI_MODEL_STORE`, `HF_HOME`,
`HF_HUB_CACHE`, `HF_XET_CACHE` и `HF_ASSETS_CACHE`, подключать store к
Hy-Nomas как read-only model tree и предоставлять
`extra_model_paths.yaml` для ComfyUI. Каталоги results, outputs и runtime
SHALL оставаться отдельными для каждого проекта.

#### Scenario: Compose и ComfyUI используют общее хранилище
- **WHEN** локальный оверлей настроен
- **THEN** Compose монтирует model store и единый HF cache, а ComfyUI получает поисковые пути из общего view

### Requirement: REQ-shared-model-store-004 Инвентарь всех локальных дисков
Локальный оверлей SHALL иметь именованную audit-цель, которая
сканирует все уникальные смонтированные локальные filesystems и
записывает candidate, selected и skipped manifests. Docker/container layers,
системные runtime-файлы, datasets, build artifacts и Trash SHALL быть
исключены или записаны в skipped manifest с причиной.

#### Scenario: Audit отделяет модели от немодельных binary-файлов
- **WHEN** оператор запускает `make model-store-audit`
- **THEN** создаётся инвентарь кандидатов, а отклонённые пути сохраняются с причиной
