# comfyui-integration Specification

## Purpose

Локальная исследовательская заметка фиксирует способ интеграции Hy-Nomas с
ComfyUI, её преимущества, ограничения и источники без установки community-кода.

## Requirements

### Requirement: REQ-comfyui-integration-001 Проверяемый обзор интеграции
Локальный оверлей SHALL содержать краткий обзор рекомендуемой upstream community
интеграции Hy-Nomas с ComfyUI. Обзор SHALL отличать отдельный ComfyUI runtime от
подключения к текущему backend, описывать data flow, повторное использование
весов, основные плюсы и минусы и ссылаться на первичные источники.

#### Scenario: Обзор ComfyUI сохранён с архитектурой и trade-offs
- **WHEN** пользователь открывает локальную заметку
- **THEN** он видит схему встраивания, плюсы, минусы и ссылки на Hy-Nomas,
  ComfyUI-Hy-Nomas и официальную документацию ComfyUI
