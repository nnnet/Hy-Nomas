# language: ru
Функция: Web UI использует совместимый и долговечный Hy-Nomas backend

  @REQ-docker-stack-001
  Сценарий: UI и backend доступны на назначенных портах
    Дано репозиторий проекта
    Тогда файл "docker-compose.yml" содержит "parallelism.tp_size=1"
    Когда я запрашиваю HTTP путь "/"
    Тогда HTTP статус равен 200
    И HTTP Content-Type содержит "text/html"
    Когда я запрашиваю HTTP путь "/health"
    Тогда HTTP статус равен 200
    И JSON поле "status" равно "ok"
    И JSON поле "worker_status" равно "ready"
    Когда я запрашиваю backend HTTP путь "/health"
    Тогда HTTP статус равен 200
    И JSON поле "status" равно "ok"
    Тогда контейнеры Compose имеют префикс "hynomas-"
    Когда я запрашиваю HTTP путь "/v1/config"
    Тогда HTTP статус равен 200
    И HTTP Content-Type содержит "application/json"
    И JSON поле "architecture" равно "gateway_worker"
    И JSON поле "reference_image_enabled" истинно
    И JSON поле "image_captioning_enabled" истинно

  @REQ-docker-stack-002
  Сценарий: Persistent Gallery и загрузки подключены к gateway
    Дано репозиторий проекта
    Тогда каталог ".runtime/hynomas" существует
    И каталог "outputs/web" существует
    И каталог "gallery" существует
    Когда я запрашиваю HTTP путь "/v1/gallery"
    Тогда HTTP статус равен 200
    И JSON массив "items" не пуст
    И Gallery не содержит видео с одинаковым содержимым
    И встроенные карточки Gallery не подменены сохранёнными генерациями

  @REQ-docker-stack-003
  Сценарий: Исходники upstream разложены без реконструкции скрытых данных
    Дано репозиторий проекта
    Тогда source pack содержит шесть отдельных upstream-примеров
    И provenance source pack закрепляет официальный bundle и видео
    И полные upstream-примеры готовы для одинакового CLI и Web replay
    И неполные upstream-примеры не подменяют скрытые prompts и camera trajectory
