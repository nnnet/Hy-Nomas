"""Start the Hy-Nomas web API with the proven Blackwell FP8 decoder patch."""

from __future__ import annotations

import runpy
from pathlib import Path

import torch
import torch.nn.functional as F

from hymm.models.vae.pixelumm_decoder.cutlass_fp8 import CutlassFP8Linear


def _blackwell_safe_forward(self: CutlassFP8Linear, x: torch.Tensor) -> torch.Tensor:
    """Dequantize every supported scale layout before the BF16 linear op."""
    x_bf = x.to(torch.bfloat16)
    weight = self.fp8_weight.to(torch.bfloat16)
    scales = self.fp8_scale.to(torch.bfloat16).flatten()
    rows, columns = weight.shape

    if scales.shape[0] == rows:
        weight = weight * scales.view(-1, 1)
    elif scales.shape[0] == columns:
        weight = weight * scales.view(1, -1)
    else:
        row_blocks = (rows + 127) // 128
        column_blocks = columns // 128
        if columns % 128 or scales.shape[0] != row_blocks * column_blocks:
            raise ValueError(
                f"fp8_scale length {scales.shape[0]} does not match "
                f"weight shape {tuple(weight.shape)}"
            )
        block_scales = scales.view(row_blocks, column_blocks)
        padded = F.pad(weight, (0, 0, 0, row_blocks * 128 - rows))
        blocks = padded.view(row_blocks, 128, column_blocks, 128)
        blocks = blocks * block_scales.view(row_blocks, 1, column_blocks, 1)
        weight = blocks.reshape(row_blocks * 128, columns)[:rows].contiguous()

    bias = getattr(self, "bias", None)
    if bias is not None:
        bias = bias.to(torch.bfloat16)
    return F.linear(x_bf, weight, bias).to(x.dtype)


CutlassFP8Linear.forward = _blackwell_safe_forward
print("Applied the Blackwell-safe PixelUMM FP8 decoder patch", flush=True)

project_root = Path.cwd()
runpy.run_path(
    str(project_root / "apps" / "seg_ar_web_server.py"),
    run_name="__main__",
)
