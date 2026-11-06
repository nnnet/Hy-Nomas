#!/bin/bash
set -e

export HOST_MODEL_PATH="$(pwd)/models"
export HY_NOMAS_IMAGE="hynomasoss/hynomasoss:cu130"

echo "=== Запуск Docker с исправленным патчем входного масштабирования для RTX 5090 ==="
docker run --rm -it --gpus all --ipc=host --network=host \
  -v "$(pwd):/workspace/Hy-Nomas" \
  -v "$HOST_MODEL_PATH:/models" \
  -v "$HOST_MODEL_PATH/hf_cache:/root/.cache/huggingface" \
  -e Hy_Nomas_Path="/workspace/Hy-Nomas" \
  -e Hy_Nomas_Model_Path="/models" \
  -w /workspace/Hy-Nomas \
  "$HY_NOMAS_IMAGE" \
  bash -c "
    python -c '
import sys
import torch
import torch.nn.functional as F
import runpy

sys.path.append(\"/workspace/Hy-Nomas\")

from hymm.models.vae.pixelumm_decoder.cutlass_fp8 import CutlassFP8Linear

# Полностью инвариантный патч: масштабируем входной тензор x_bf по его последней оси
def safe_forward(self, x):
    x_bf = x.to(torch.bfloat16)
    w_bf = self.fp8_weight.to(torch.bfloat16)

    # Извлекаем одномерный вектор масштабов группы
    s_w = self.fp8_scale.to(torch.bfloat16).flatten()

    # Динамически подгоняем масштаб под входную размерность тензора (последняя ось x_bf)
    in_feats = x_bf.shape[-1]
    if s_w.shape[0] != in_feats:
        repeats = in_feats // s_w.shape[0]
        s_w = s_w.repeat_interleave(max(1, repeats))

    # Масштабируем входные признаки. view(1, 1, -1) идеально ложится на трехмерный [B, T, C]
    x_bf = x_bf * s_w.view(1, 1, -1)

    bias = getattr(self, \"bias\", None)
    if bias is not None:
        bias = bias.to(torch.bfloat16)

    # Выполняем нативный линейный слой PyTorch силами архитектуры Blackwell
    return F.linear(x_bf, w_bf, bias).to(x.dtype)

# Инжектируем патч в память процесса
CutlassFP8Linear.forward = safe_forward
print(\"✔ Универсальный патч входного масштаба применен. Запуск инференса...\")

sys.argv = [
    \"hymm/inference.py\",
    \"+experiment=single_gpu_low_mem_inference\",
    \"dit_weight=/models/DiT/distilled_int8/diffusion_pytorch_model_ema_0_995_int8.safetensors\",
    \"model.vae.checkpoint=/models/VAE/PixelUMM_FT_FP8/diffusion_pytorch_model_fp8.safetensors\",
    \"inference.prompt=apps/prompts/examples.json\",
    \"inference.save_path=./outputs/single_gpu\"
]
runpy.run_path(\"hymm/inference.py\", run_name=\"__main__\")
'
"
