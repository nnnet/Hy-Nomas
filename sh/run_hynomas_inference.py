"""Blackwell-safe launcher used by the local Docker CLI wrapper."""

from __future__ import annotations

import os
import runpy
import sys

import torch
import torch.nn.functional as F

sys.path.append("/workspace/Hy-Nomas")

from hymm.models.vae.pixelumm_decoder.cutlass_fp8 import CutlassFP8Linear


def safe_forward(self, x):
    """Decode serialized FP8 weights with row/column/block scale layouts."""
    x_bf = x.to(torch.bfloat16)
    w_bf = self.fp8_weight.to(torch.bfloat16)
    s_w = self.fp8_scale.to(torch.bfloat16).flatten()
    m, k = w_bf.shape
    if s_w.shape[0] == m:
        w_bf = w_bf * s_w.view(-1, 1)
    elif s_w.shape[0] == k:
        w_bf = w_bf * s_w.view(1, -1)
    else:
        block_rows = (m + 127) // 128
        block_columns = k // 128
        if k % 128 or s_w.shape[0] != block_rows * block_columns:
            raise ValueError(
                f"fp8_scale length {s_w.shape[0]} does not match weight "
                f"{tuple(w_bf.shape)}"
            )
        scales = s_w.view(block_rows, block_columns)
        padded = F.pad(w_bf, (0, 0, 0, block_rows * 128 - m))
        blocks = padded.view(block_rows, 128, block_columns, 128)
        blocks = blocks * scales.view(block_rows, 1, block_columns, 1)
        w_bf = blocks.reshape(block_rows * 128, k)[:m].contiguous()
    bias = getattr(self, "bias", None)
    if bias is not None:
        bias = bias.to(torch.bfloat16)
    return F.linear(x_bf, w_bf, bias).to(x.dtype)


CutlassFP8Linear.forward = safe_forward
print("Applied the Blackwell-safe PixelUMM FP8 decoder patch")

scenario = os.environ["HYNOMAS_SCENARIO"]
save_path = os.environ["HYNOMAS_SAVE_PATH"]
model_root = os.environ.get("Hy_Nomas_Model_Path", "/models").rstrip("/")
sys.argv = [
    "hymm/inference.py",
    "+experiment=single_gpu_low_mem_inference",
    f"dit_weight={model_root}/DiT/distilled_int8/diffusion_pytorch_model_ema_0_995_int8.safetensors",
    f"model.vae.checkpoint={model_root}/VAE/PixelUMM_FT_FP8/diffusion_pytorch_model_fp8.safetensors",
    f"inference.prompt={scenario}",
    f"inference.save_path={save_path}",
    "inference.video_length=event",
]
runpy.run_path("hymm/inference.py", run_name="__main__")
