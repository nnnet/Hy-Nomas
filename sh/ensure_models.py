"""Download only missing Hy-Nomas checkpoints into the persistent model tree."""

import os
from pathlib import Path

STORE_ROOT = Path(
    os.environ.get("AI_MODEL_STORE", "/mnt/A4C45B32C45B2C87/ai-models")
).resolve()
os.environ.setdefault("HF_HOME", str(STORE_ROOT / "huggingface"))
os.environ.setdefault("HF_HUB_CACHE", str(STORE_ROOT / "huggingface" / "hub"))
os.environ.setdefault("HF_XET_CACHE", str(STORE_ROOT / "huggingface" / "xet"))
os.environ.setdefault("HF_ASSETS_CACHE", str(STORE_ROOT / "huggingface" / "assets"))

from huggingface_hub import hf_hub_download
from model_store import init_store, migrate_file


REPO_ID = "tencent/Hy-Nomas"
REVISION = "bac719a80c8d02f91c485fca804bb8221e149b70"
MODEL_ROOT = STORE_ROOT / "views" / "hy-nomas"
REQUIRED = (
    "DiT/distilled_int8/diffusion_pytorch_model_ema_0_995_int8.safetensors",
    "VAE/PixelUMM_FT_FP8/diffusion_pytorch_model_fp8.safetensors",
    "VAE/DCAE-V/dc-ae-v-1.0-f32t4c32-bf16.pt",
)


init_store(STORE_ROOT)
for filename in REQUIRED:
    target = MODEL_ROOT / filename
    if target.is_file() and target.stat().st_size > 0:
        print(f"model present: {target}")
        continue
    print(f"downloading missing model once: {filename}")
    downloaded = Path(
        hf_hub_download(
            repo_id=REPO_ID,
            filename=filename,
            revision=REVISION,
            local_dir=MODEL_ROOT,
        )
    )
    if not downloaded.is_file() or downloaded.stat().st_size <= 0:
        raise RuntimeError(f"model download did not produce {target}")
    migrate_file(STORE_ROOT, downloaded)
