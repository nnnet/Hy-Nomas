# Hy-Nomas в ComfyUI

Исследовано 2026-11-06. Рекомендуемая самим Hy-Nomas community-интеграция —
[`PedroMarinhoDev/ComfyUI-Hy-Nomas`](https://github.com/PedroMarinhoDev/ComfyUI-Hy-Nomas),
проверенный commit `712614ecf1d57a7159f9ab96b7894152f3195a26`.

## Как встраивается

- Это **альтернативный runtime внутри ComfyUI**, а не клиент нашего работающего
  gateway/backend. Custom nodes устанавливаются в `ComfyUI/custom_nodes` через
  Manager/Registry или Git; после установки ComfyUI перезапускается.
- Веса размещаются в стандартных каталогах ComfyUI:
  `models/diffusion_models` (Hy-Nomas DiT INT8), `models/vae` (PixelUMM FP8 с
  encoder) и `models/text_encoders` (Qwen2.5-VL-7B).
- Наши Tencent DiT INT8 и PixelUMM FP8 побайтно совместимы с файлами, на которые
  ссылается интеграция; их разумно подключить ссылкой/через `extra_model_paths`,
  чтобы не держать второй комплект. ComfyUI Qwen text encoder — отдельный
  single-file asset.
- Основной graph:
  `Load CLIP + World Prompt → Segment → KSampler → Extend World → ... → Decode → Video`.
  `Extend World` делает дополнительный cache pass; состояние и KV-history
  передаются между узлами как объект `WORLD`.
- Доступны готовые workflow JSON: per-segment, one-node, start-from-image,
  camera-control и interactive Drive. Камера задаётся записью WASD/стрелок,
  typed key timeline или импортом trajectory JSON из Tencent demo.
- Image reference кодируется DCAE-V как начальный сегмент истории. Это
  community-приём: исходная модель не обучалась на неподвижном клипе как past.

## Плюсы

- Наглядный и воспроизводимый graph: prompt, seed, sampler, camera path, decode
  и постобработка сохраняются одним workflow JSON.
- Легко компоновать с другими ComfyUI-узлами: upscale, frame interpolation,
  монтаж, аудио и экспорт без отдельного glue-кода.
- Сегменты можно строить явно, продолжая один `WORLD`; есть text control,
  camera recording, typed camera keys, image start и интерактивный Drive.
- Dynamic VRAM/offload плюс INT8 DiT и FP8 PixelUMM снижают порог до заявленных
  12 GB VRAM; не требуется отдельный FastAPI/nginx/frontend стек.
- Два самых больших наших checkpoint можно переиспользовать без повторной
  загрузки; интеграция использует stock ComfyUI loader/KSampler abstractions.

## Минусы

- Это молодой **community WIP**, не официальный Tencent runtime: inputs и
  workflows могут меняться, возможны rough edges и несовпадения с upstream.
- Сейчас нет аналога Nomas-PE: structured world JSON и follow-up tags приходится
  писать вручную; автоматический prompt-rewriter указан только в roadmap.
- Не гарантируется pixel-identical parity: другие kernels/attention и
  quantization дают небольшие численные отличия, а whole-model output к ним
  чувствителен.
- Drive не real-time: автор указывает примерно 3.5–4 секунды вычисления на
  1 секунду видео при 832×480 на RTX 4090; 20 секунд 720p — около трёх минут.
- Требования всё ещё высокие: около 27 GB моделей, минимум 32 GB RAM; history
  растёт примерно на 5.9 GB RAM за каждые 5 секунд 1280×704.
- Image-start — экспериментальная community-функция, не обученная и не
  поставляемая Tencent; возможен drift после нескольких сегментов.
- Лицензии ограничивают применение: node code — GPL-3.0, а PixelUMM weights —
  NVIDIA One-Way Noncommercial License (research/evaluation only).
- Это второй runtime и второй жизненный цикл состояния; наши Compose sessions,
  Gallery, durable queue и результаты автоматически в ComfyUI не мигрируют.

## Вывод для нашего проекта

- ComfyUI выгоден для **экспериментов, workflow-композиции и ручного сравнения**.
- Наш Compose лучше для **стабильного web UX, очереди, persistent sessions и
  Gallery**.
- Практичный вариант — держать ComfyUI отдельным profile/compose, монтировать те
  же `models/`, но не запускать его одновременно с `hynomas-worker` на одной GPU.

## Первичные источники

- [Hy-Nomas upstream: community integration](https://github.com/Tencent-Hunyuan/Hy-Nomas/blob/main/README.md#-community-contributions)
- [ComfyUI-Hy-Nomas README, pinned commit](https://github.com/PedroMarinhoDev/ComfyUI-Hy-Nomas/blob/712614ecf1d57a7159f9ab96b7894152f3195a26/README.md)
- [ComfyUI: Custom Nodes](https://docs.comfy.org/basic-concepts/custom-nodes)
- [ComfyUI: manual installation](https://docs.comfy.org/installation/manual_install)
