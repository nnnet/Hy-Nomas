#!/bin/bash
set -e

SPLIT=false
SCENARIO=""

while [ $# -gt 0 ]; do
    case "$1" in
        --split)
            SPLIT=true
            shift
            ;;
        -*)
            echo "Неизвестный флаг: $1"
            exit 1
            ;;
        *)
            if [ -z "$SCENARIO" ]; then
                SCENARIO="$1"
            else
                echo "Лишний аргумент: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$SCENARIO" ]; then
    echo "Использование: $0 [--split] <путь_к_сценарию>"
    echo "  --split  генерировать отдельное видео для каждой сцены (сегмента)"
    echo "Пример: $0 apps/cs-skins-city-complete/scenario_all_keys.json"
    exit 1
fi

MODEL_STORE="${AI_MODEL_STORE:-/mnt/A4C45B32C45B2C87/ai-models}"
HY_NOMAS_IMAGE="hynomasoss/hynomasoss:cu130"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
SAVE_PATH="./outputs/${TIMESTAMP}"

echo "=== Запуск Docker с патчем осей и генерацией в ${SAVE_PATH} ==="
echo "Сценарий: ${SCENARIO}"
echo "Режим split: $SPLIT"

if [ ! -d "$MODEL_STORE/objects" ] || [ ! -d "$MODEL_STORE/views/hy-nomas" ]; then
    echo "Общее хранилище моделей не найдено: $MODEL_STORE" >&2
    echo "Выполните: make models-ensure" >&2
    exit 2
fi

set +e
docker run --rm --gpus all --ipc=host --network=host \
  -v "$(pwd):/workspace/Hy-Nomas" \
  -v "$MODEL_STORE/objects:/opt/ai-models/objects:ro" \
  -v "$MODEL_STORE/views:/opt/ai-models/views:ro" \
  -v "$MODEL_STORE/huggingface:/opt/ai-models/huggingface:rw" \
  -e Hy_Nomas_Path="/workspace/Hy-Nomas" \
  -e AI_MODEL_STORE="/opt/ai-models" \
  -e Hy_Nomas_Model_Path="/opt/ai-models/views/hy-nomas" \
  -e HF_HOME="/opt/ai-models/huggingface" \
  -e HF_HUB_CACHE="/opt/ai-models/huggingface/hub" \
  -e HF_XET_CACHE="/opt/ai-models/huggingface/xet" \
  -e HF_ASSETS_CACHE="/opt/ai-models/huggingface/assets" \
  -e HYNOMAS_SCENARIO="$SCENARIO" \
  -e HYNOMAS_SAVE_PATH="$SAVE_PATH" \
  -w /workspace/Hy-Nomas \
  "$HY_NOMAS_IMAGE" \
  python sh/run_hynomas_inference.py
EXIT_CODE=$?
set -e

if ! chown -R "$USER":"$USER" "${SAVE_PATH}" 2>/dev/null; then
    sudo -n chown -R "$USER":"$USER" "${SAVE_PATH}" 2>/dev/null || \
      echo "ВНИМАНИЕ: не удалось вернуть владение ${SAVE_PATH}" >&2
fi

if [ "$EXIT_CODE" -ne 0 ]; then
    echo "Генерация завершилась с ошибкой (код $EXIT_CODE)."
    exit "$EXIT_CODE"
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "ВНИМАНИЕ: ffmpeg не найден в системе."
    echo "Установите: sudo apt update && sudo apt install -y ffmpeg"
    echo "Или откройте оригинал ${SAVE_PATH}/*.mp4 в VLC."
    exit 0
fi

MP4_FILES="$(find "${SAVE_PATH}" -maxdepth 1 -name '*.mp4' | sort)"
if [ -z "$MP4_FILES" ]; then
    echo "ВНИМАНИЕ: .mp4 не найден в ${SAVE_PATH}"
    exit 0
fi

if [ "$SPLIT" = true ]; then
    echo "Разделяем видео по сценам..."
    python3 - "$SCENARIO" "$SAVE_PATH" <<'PYEOF'
import json
import subprocess
import sys
from pathlib import Path

scenario_path = sys.argv[1]
save_path = Path(sys.argv[2])

with open(scenario_path, encoding="utf-8") as handle:
    data = json.load(handle)


def to_sec(value):
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


for item in data:
    test_id = item.get("test_id", "scene")
    mp4_files = list(save_path.glob("*.mp4"))
    if not mp4_files:
        continue
    source = mp4_files[0]
    for index, segment in enumerate(item.get("segments", [])):
        start = to_sec(segment.get("start_time", "00:00:00.000"))
        end = to_sec(segment.get("end_time", "00:00:00.000"))
        output = save_path / f"{test_id}_scene{index + 1:02d}.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(source), "-ss", str(start), "-to", str(end),
                "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(output),
            ],
            check=True,
        )
        print(f"  {output} ({start}s–{end}s)")
PYEOF
else
    MP4_FILE="$(printf '%s\n' "$MP4_FILES" | head -1)"
    VIEWABLE="${MP4_FILE%.mp4}.viewable.mp4"
    echo "Пережимаем видео для совместимости: ${VIEWABLE}"
    if ! ffmpeg -y -hide_banner -loglevel error -i "$MP4_FILE" \
      -c:v libx264 -crf 20 -preset medium \
      -profile:v high -level 4.0 \
      -pix_fmt yuv420p -movflags +faststart \
      "$VIEWABLE" 2>/dev/null; then
        VIEWABLE="/tmp/$(basename "${MP4_FILE%.mp4}").viewable.mp4"
        echo "Директория ${SAVE_PATH} недоступна для записи, результат: ${VIEWABLE}"
        ffmpeg -y -hide_banner -loglevel error -i "$MP4_FILE" \
          -c:v libx264 -crf 20 -preset medium \
          -profile:v high -level 4.0 \
          -pix_fmt yuv420p -movflags +faststart \
          "$VIEWABLE"
    fi
    echo "Готово: ${VIEWABLE}"
    ffprobe -v error -select_streams v:0 \
      -show_entries stream=codec_name,width,height,r_frame_rate,duration,bits_per_raw_sample \
      -of default=noprint_wrappers=1 "$VIEWABLE"
    echo "Размер файла: $(du -h "$VIEWABLE" | cut -f1)"
fi
