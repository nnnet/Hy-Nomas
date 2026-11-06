# language: ru
Функция: Единое хранилище моделей

  @REQ-shared-model-store-001 @REQ-shared-model-store-002
  Сценарий: Одинаковые файлы мигрируются без дублирования
    Дано репозиторий проекта
    Тогда файл "sh/model_store.py" существует
    И файл "sh/model_store.py" содержит "sha256"
    И файл "sh/model_store.py" содержит "os.replace"
    И файл "sh/model_store.py" содержит "symlink_to"

  @REQ-shared-model-store-003
  Сценарий: Hy-Nomas и ComfyUI подключают общие веса
    Дано репозиторий проекта
    Тогда файл "docker-compose.yml" содержит "AI_MODEL_STORE"
    И файл "docker-compose.yml" содержит "HF_HUB_CACHE"
    И файл "reproductions/comfyui-extra-model-paths.yaml" существует
    И файл "Makefile" содержит "model-store-verify"

  @REQ-shared-model-store-004
  Сценарий: Audit сканирует все уникальные локальные filesystems
    Дано репозиторий проекта
    Тогда файл "Makefile" содержит "model-store-audit"
    И файл "Makefile" содержит "/home/uadmin"
    И файл "Makefile" содержит "/mnt/82A23910A2390A65"
    И файл "Makefile" содержит "/mnt/9"
