#!/bin/bash
set -e

echo "=== Hy-Nomas Web UI (Docker Compose) ==="

# Проверка Docker
if ! command -v docker >/dev/null 2>&1; then
    echo "ОШИБКА: docker не найден в системе."
    exit 1
fi

if ! command -v docker compose >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
    echo "ОШИБКА: docker compose не найден в системе."
    exit 1
fi

# Сборка образа веб-UI (лёгкий, без CUDA)
echo "Сборка образа hy-nomas-web..."
docker build -f docker/Dockerfile.web -t hy-nomas-web .

# Поднятие сервисов
echo "Запуск docker compose up..."
docker compose up -d

echo ""
echo "Готово. Веб-UI доступен по адресу: http://localhost"
echo "API бэкенда: http://localhost:8000"
echo ""
echo "Посмотреть логи:   docker compose logs -f"
echo "Остановить:        docker compose down"
echo "Пересобрать веб:   docker compose build web && docker compose up -d web"
