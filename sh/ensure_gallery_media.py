#!/usr/bin/env python3
"""Download the pinned public Hy-Nomas curated Gallery videos once."""

from __future__ import annotations

import hashlib
import os
import shutil
import urllib.request
from pathlib import Path


BASE_URL = "https://hy-nomas.hy.tencent.com/gallery"
FILES = {
    "curated-20261022-snow-palace-walk.mp4": "49d663c12c13d2971b011fdd009fa444a49ed946566cc5c121949c513d095d0b",
    "curated-20261022-snow-palace-ascent.mp4": "2ef9551d44afe0051681ce83292d2a8d0733f1a054974713b5f65a8e0ebe3c0d",
    "curated-20261022-coastal-waterfall.mp4": "9f00398930046472c3143e69e76627365171e733b7d80dede0ef90c74e63d902",
    "curated-20261022-voxel-adventure.mp4": "7caa5460bb4b22100dd10f442c2f1ec8a3f7b2e892ed44edf718d8cf00e23488",
    "curated-20261022-kitchen-stories.mp4": "274bfea3e0ce83b2a3a1507eb8dadaedef91e0e2ecaa4bdc04ec903d4bde89ee",
    "curated-20261022-street-coffee.mp4": "e11a92e78dc530e908ec4b8ff40b9730b284e3d4222ca9b57147a28bbea800ac",
}


def valid_mp4(path: Path, expected_sha256: str) -> bool:
    if not path.is_file() or path.stat().st_size < 1_000_000:
        return False
    with path.open("rb") as handle:
        header = handle.read(32)
    if b"ftyp" not in header:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest() == expected_sha256


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination_dir = Path(
        os.environ.get("NOMAS_GALLERY_MEDIA_DIR", root / "gallery" / "media")
    )
    destination_dir.mkdir(parents=True, exist_ok=True)

    for filename, expected_sha256 in FILES.items():
        destination = destination_dir / filename
        if destination.exists():
            if not valid_mp4(destination, expected_sha256):
                raise RuntimeError(
                    f"refusing to overwrite invalid existing Gallery file: {destination}"
                )
            print(f"gallery video present: {destination}")
            continue

        temporary = destination.with_suffix(".mp4.part")
        request = urllib.request.Request(
            f"{BASE_URL}/{filename}",
            headers={"User-Agent": "Hy-Nomas-Docker-Setup/1.0"},
        )
        print(f"downloading once: {request.full_url} -> {destination}")
        with urllib.request.urlopen(request, timeout=300) as response:
            if response.status != 200:
                raise RuntimeError(f"download failed with HTTP {response.status}")
            with temporary.open("wb") as handle:
                shutil.copyfileobj(response, handle, length=8 * 1024 * 1024)
        if not valid_mp4(temporary, expected_sha256):
            raise RuntimeError(f"downloaded Gallery file is not a valid MP4: {temporary}")
        os.replace(temporary, destination)


if __name__ == "__main__":
    main()
