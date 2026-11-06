#!/bin/bash
set -e

export HOST_MODEL_PATH="$(pwd)/models"
export HY_NOMAS_IMAGE="hynomasoss/hynomasoss:cu130"

echo "=== Запуск Docker с исправленным патчем осей и быстрым стартом для RTX 5090 ==="
docker run --rm --gpus all --ipc=host --network=host \
  -v "$(pwd):/workspace/Hy-Nomas" \
  -v "$HOST_MODEL_PATH:/models" \
  -v "$HOST_MODEL_PATH/hf_cache:/root/.cache/huggingface" \
  -e Hy_Nomas_Path="/workspace/Hy-Nomas" \
  -e Hy_Nomas_Model_Path="/models" \
  -w /workspace/Hy-Nomas \
  "$HY_NOMAS_IMAGE" \
  bash -c '
cat <<'"'"'PYEOF'"'"' > /tmp/patch_vae.py
import sys
import torch
import torch.nn.functional as F
import runpy

sys.path.append("/workspace/Hy-Nomas")

from hymm.models.vae.pixelumm_decoder.cutlass_fp8 import CutlassFP8Linear

# Полностью универсальный forward: масштабы веса на строки (dim 0 = out_features)
def safe_forward(self, x):
    x_bf = x.to(torch.bfloat16)
    w_bf = self.fp8_weight.to(torch.bfloat16)           # [out_features, in_features]
    s_w = self.fp8_scale.to(torch.bfloat16).flatten()    # по одному масштабу на выходной признак

    # Вектор масштабов тянется под ось признаков веса: строки (out_features),
    # столбцы (in_features) или блоки 128x128 — конвенция зависит от слоя.
    m, k = w_bf.shape
    if s_w.shape[0] == m:
        # по одному масштабу на выходной признак (строки матрицы весов)
        w_bf = w_bf * s_w.view(-1, 1)
    elif s_w.shape[0] == k:
        # по одному масштабу на входной признак (столбцы матрицы весов)
        w_bf = w_bf * s_w.view(1, -1)
    else:
        # блокwise квантование: scale.shape = [ceil(m/128), k//128], сплющенный
        nb = (m + 127) // 128
        nk = k // 128
        if k % 128 or s_w.shape[0] != nb * nk:
            raise ValueError(
                f"fp8_scale length {s_w.shape[0]} не подходит к весу {tuple(w_bf.shape)}")
        s_blocks = s_w.view(nb, nk)
        w_padded = F.pad(w_bf, (0, 0, 0, nb * 128 - m))
        w_blocks = w_padded.view(nb, 128, nk, 128)
        w_blocks = w_blocks * s_blocks.view(nb, 1, nk, 1)
        w_bf = w_blocks.reshape(nb * 128, k)[:m].contiguous()

    bias = getattr(self, "bias", None)
    if bias is not None:
        bias = bias.to(torch.bfloat16)

    return F.linear(x_bf, w_bf, bias).to(x.dtype)

# Инжектируем метод в класс
CutlassFP8Linear.forward = safe_forward
print("✔ Аппаратный патч осей Blackwell успешно применен. Запуск генерации...")

sys.argv = [
    "hymm/inference.py",
    "+experiment=single_gpu_low_mem_inference",
    "dit_weight=/models/DiT/distilled_int8/diffusion_pytorch_model_ema_0_995_int8.safetensors",
    "model.vae.checkpoint=/models/VAE/PixelUMM_FT_FP8/diffusion_pytorch_model_fp8.safetensors",
    "inference.prompt=apps/prompts/examples.json",
    "inference.save_path=./outputs/single_gpu"
]
runpy.run_path("hymm/inference.py", run_name="__main__")
PYEOF

python /tmp/patch_vae.py
'
