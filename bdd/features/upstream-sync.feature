# language: ru
Функция: Безопасная синхронизация с апстримом

  @REQ-upstream-sync-001
  Сценарий: Проверка Git remotes автоматизирована
    Дано репозиторий проекта
    Тогда файл "sh/upstream_sync.sh" содержит "verify_remotes"
    И файл "sh/upstream_sync.sh" содержит "DISABLED"

  @REQ-upstream-sync-002
  Сценарий: Апстрим остаётся базовой веткой
    Дано репозиторий проекта
    Тогда файл "sh/upstream_sync.sh" содержит "upstream/main"
    И файл "docs/upstream-workflow.md" существует

  @REQ-upstream-sync-003
  Сценарий: Именованная цель синхронизации не прячет изменения
    Дано репозиторий проекта
    Тогда файл "Makefile" содержит "upstream-sync"
    И файл "sh/upstream_sync.sh" содержит "status --porcelain"
    И файл "sh/upstream_sync.sh" содержит "rebase.autoStash=false"
