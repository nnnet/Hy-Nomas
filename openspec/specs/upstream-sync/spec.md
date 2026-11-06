# upstream-sync Specification

## Purpose

Локальные оверлеи хранятся в нашем fork, а исходный
Tencent-Hunyuan/Hy-Nomas остаётся чистой обновляемой базой.

## Requirements

### Requirement: REQ-upstream-sync-001 Разделённые Git remotes
Репозиторий SHALL использовать `upstream` только для получения
Tencent-Hunyuan/Hy-Nomas и `origin` для чтения и записи нашего fork.
Push URL для `upstream` SHALL быть отключён.

#### Scenario: Апстрим защищён от push
- **WHEN** проверяется Git-конфигурация
- **THEN** `origin` указывает на наш fork, `upstream` — на Tencent, а push в `upstream` невозможен

### Requirement: REQ-upstream-sync-002 Чистая upstream-база
Локальная ветка `main` SHALL точно следовать `upstream/main`.
Наши файлы SHALL жить в отдельной ветке `integration/local-runtime`;
файлы, уже отслеживаемые апстримом, SHALL оставаться без
локальных изменений.

#### Scenario: Наши изменения не подменяют апстрим
- **WHEN** интеграционная ветка проверяется относительно `upstream/main`
- **THEN** она содержит только добавочные локальные файлы

### Requirement: REQ-upstream-sync-003 Безопасное обновление
Именованная Make-цель SHALL проверять remotes и чистоту
рабочего дерева, получать `upstream`, обновлять локальный
`main` и rebase-ить текущую integration-ветку. Сценарий SHALL не
push-ить автоматически.

#### Scenario: Обновление отказывается работать с незакоммиченными файлами
- **WHEN** в рабочем дереве есть изменения
- **THEN** команда sync завершается до fetch, rebase и push
