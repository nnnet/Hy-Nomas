"""Run the durable gateway with an offline image-caption fallback."""

from __future__ import annotations

import json
import hashlib
import os
import threading
from functools import lru_cache
from pathlib import Path

from apps import k3_image_captioner, kimi_k3_prompt_enhancer


class OfflinePromptEnhancer(kimi_k3_prompt_enhancer.OnlinePromptEnhancer):
    """Select the gateway's deterministic local prompt builder without PE."""

    @property
    def configured(self) -> bool:
        return False

    @property
    def model_options(self) -> list[dict]:
        return []

    @property
    def default_model(self) -> str:
        return ""

    def configured_for(self, enhancer_model: object) -> bool:
        return False


class LocalImageCaptioner(k3_image_captioner.NomasImageCaptioner):
    """Create a conservative prompt while DCAE-V supplies the actual image."""

    @property
    def configured(self) -> bool:
        return True

    def caption(
        self,
        image_path: Path,
        *,
        fps: int = 24,
        perspective: str = "third-person follow",
    ) -> dict:
        selected = k3_image_captioner.selected_perspective(perspective)
        request = {
            "session_id": f"local-image-{image_path.stem}",
            "perspective": selected,
            "subject_description": (
                "The primary subject visible in the uploaded reference image"
            ),
            "environment_description": (
                "Preserve the uploaded reference image faithfully, including its "
                "subjects, composition, environment, lighting, colors, and style."
            ),
        }
        prompt = kimi_k3_prompt_enhancer.build_local_fallback_prompt(
            request,
            None,
            fps=fps,
            duration_seconds=5.0,
        )
        return k3_image_captioner.normalize_caption(
            json.loads(prompt.prompt),
            fps=fps,
            model="local-image-fallback",
            perspective=selected,
        )


kimi_k3_prompt_enhancer.OnlinePromptEnhancer = OfflinePromptEnhancer
k3_image_captioner.NomasImageCaptioner = LocalImageCaptioner

from apps import seg_ar_gateway  # noqa: E402


LEGACY_GALLERY_ITEMS = {
    "station-wagon": "blue-station-wagon.mp4",
    "alpine-convoy": "alpine-armored-convoy.mp4",
    "canal-walk": "canal-side-walk.mp4",
    "coastal-flight": "coastal-city-flight.mp4",
    "desert-drive": "desert-city-drive.mp4",
    "river-raft": "desert-river-raft.mp4",
}

CURATED_GALLERY_ITEMS = {
    "curated-20261022-snow-palace-walk": "curated-20261022-snow-palace-walk.mp4",
    "curated-20261022-snow-palace-ascent": "curated-20261022-snow-palace-ascent.mp4",
    "curated-20261022-coastal-waterfall": "curated-20261022-coastal-waterfall.mp4",
    "curated-20261022-voxel-adventure": "curated-20261022-voxel-adventure.mp4",
    "curated-20261022-kitchen-stories": "curated-20261022-kitchen-stories.mp4",
    "curated-20261022-street-coffee": "curated-20261022-street-coffee.mp4",
}

STATIC_GALLERY_CARDS = (
    {
        "id": "curated-20261022-snow-palace-walk",
        "title": "Snow Palace Walk",
        "video": "gallery/curated-20261022-snow-palace-walk.mp4",
        "duration": "34.0s",
        "perspective": "third-person follow",
        "subject": "A silver-gray snow leopard with thick winter fur and dark rosettes.",
        "attributes": "An animated winter landscape at the foot of the Potala Palace, with deep snow, red-and-white walls, golden rooftops, and distant mountain ridges.",
        "direction": "Walk forward along the snowy path toward the palace.",
    },
    {
        "id": "curated-20261022-snow-palace-ascent",
        "title": "Snow Palace Ascent",
        "video": "gallery/curated-20261022-snow-palace-ascent.mp4",
        "duration": "30.0s",
        "perspective": "third-person follow",
        "subject": "A silver-gray snow leopard with a long tail and broad paws.",
        "attributes": "Snow-covered stone steps rise toward the red-and-white walls of the Potala Palace in a bright animated winter scene.",
        "direction": "Follow the snow leopard as it climbs the snowy steps.",
    },
    {
        "id": "curated-20261022-coastal-waterfall",
        "title": "Coastal Waterfall",
        "video": "gallery/curated-20261022-coastal-waterfall.mp4",
        "duration": "40.5s",
        "perspective": "third-person follow",
        "subject": "A dark brown attack helicopter with a tandem canopy and nose searchlight.",
        "attributes": "A sunlit coastal canyon with turquoise water, a tall bridge, and a waterfall spilling down the cliff.",
        "direction": "Follow the helicopter as it descends toward the water and sweeps its searchlight across the waterfall.",
    },
    {
        "id": "curated-20261022-voxel-adventure",
        "title": "Voxel Adventure",
        "video": "gallery/curated-20261022-voxel-adventure.mp4",
        "duration": "30.0s",
        "perspective": "first-person",
        "subject": "A first-person Minecraft player, visible as a blocky arm and hand.",
        "attributes": "A sunlit voxel landscape with grassy hills, oak trees, flowers, and square clouds.",
        "direction": "Raise a pixelated phone, then switch to a diamond sword.",
    },
    {
        "id": "curated-20261022-kitchen-stories",
        "title": "Kitchen Stories",
        "video": "gallery/curated-20261022-kitchen-stories.mp4",
        "duration": "42.0s",
        "perspective": "first-person",
        "subject": "An adult woman preparing chicken soup in a modern kitchen.",
        "attributes": "A kitchen with white and sage-green cabinets, stainless steel counters, and a steaming pot on the stove.",
        "direction": "Bring the carrots to the stove, lift the lid, and stir the soup.",
    },
    {
        "id": "curated-20261022-street-coffee",
        "title": "Street Coffee",
        "video": "gallery/curated-20261022-street-coffee.mp4",
        "duration": "41.6s",
        "perspective": "second-person",
        "subject": "An adult woman coffee vendor wearing an apron, facing the camera behind a street cart.",
        "attributes": "An outdoor coffee stall with a filter dripper, glass server, and gooseneck kettle under roadside trees.",
        "direction": "Prepare the dripper and pour hot water slowly over the coffee grounds.",
    },
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=128)
def _cached_file_sha256(path: str, size: int, mtime_ns: int) -> str:
    """Hash immutable-looking media once and invalidate on metadata changes."""
    del size, mtime_ns
    return _file_sha256(Path(path))


def _media_sha256(path: Path) -> str:
    stat = path.stat()
    return _cached_file_sha256(str(path), stat.st_size, stat.st_mtime_ns)


def _normalize_gallery(gallery_dir: Path) -> None:
    """Expose only present, byte-unique Gallery cards."""
    index_path = gallery_dir.parent / f".{gallery_dir.name}_items.json"
    raw_items = (
        json.loads(index_path.read_text(encoding="utf-8"))
        if index_path.is_file()
        else []
    )
    retained: list[dict] = []
    seen_hashes: dict[str, str] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "")
        if item_id in LEGACY_GALLERY_ITEMS:
            # Static cards are recomputed from the actual files below.  This
            # also repairs stale hidden markers after files are added/removed.
            continue
        if item.get("hidden") is True:
            retained.append(item)
            continue
        relative_video = str(item.get("relative_video") or "")
        video = (gallery_dir / relative_video).resolve()
        if (
            not relative_video
            or not video.is_relative_to(gallery_dir.resolve())
            or not video.is_file()
        ):
            continue
        content_hash = _file_sha256(video)
        if content_hash in seen_hashes:
            print(
                f"Hiding duplicate Gallery item {item.get('id')} "
                f"(same content as {seen_hashes[content_hash]})",
                flush=True,
            )
            continue
        seen_hashes[content_hash] = str(item.get("id") or "")
        retained.append(item)

    for item_id, filename in LEGACY_GALLERY_ITEMS.items():
        static_video = gallery_dir / filename
        if (
            not static_video.is_file()
            or not static_video.stat().st_size
            or _media_sha256(static_video) in seen_hashes
        ):
            retained.append({"id": item_id, "hidden": True})

    if retained != raw_items:
        temporary = index_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(retained, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, index_path)
        index_path.chmod(0o644)


_original_add_gallery_item = seg_ar_gateway.add_gallery_item_from_source


def _deduplicating_add_gallery_item(
    gallery_dir: Path,
    source: Path,
    payload: dict,
    *,
    process_lock: threading.RLock,
) -> dict:
    """Return an existing card instead of copying identical generated bytes."""
    source_hash = _file_sha256(source)
    index_path = gallery_dir.parent / f".{gallery_dir.name}_items.json"
    with process_lock:
        if index_path.is_file():
            for item in json.loads(index_path.read_text(encoding="utf-8")):
                if not isinstance(item, dict) or item.get("hidden") is True:
                    continue
                candidate = gallery_dir / str(item.get("relative_video") or "")
                if candidate.is_file() and _file_sha256(candidate) == source_hash:
                    return {
                        "item": seg_ar_gateway._gallery_public_item(item),
                        "added": False,
                    }
        return _original_add_gallery_item(
            gallery_dir,
            source,
            payload,
            process_lock=process_lock,
        )


seg_ar_gateway.add_gallery_item_from_source = _deduplicating_add_gallery_item


_original_read_gallery_items = seg_ar_gateway.read_gallery_items


def _read_gallery_items_with_built_ins(
    gallery_dir: Path | None,
) -> list[dict]:
    """Put present upstream cards before locally saved Gallery entries."""
    saved_items = _original_read_gallery_items(gallery_dir)
    if gallery_dir is None:
        return saved_items
    hidden_ids = set(seg_ar_gateway.read_hidden_gallery_item_ids(gallery_dir))
    saved_digests = {
        _media_sha256(candidate)
        for item in saved_items
        if str(item.get("id") or "").startswith("saved-")
        for relative in [str(item.get("video") or "").removeprefix("gallery/")]
        for candidate in [gallery_dir / relative]
        if candidate.is_file()
    }
    built_ins = []
    for source_card in STATIC_GALLERY_CARDS:
        item_id = source_card["id"]
        video_path = gallery_dir / CURATED_GALLERY_ITEMS[item_id]
        if item_id in hidden_ids or not video_path.is_file():
            continue
        card = dict(source_card)
        if _media_sha256(video_path) in saved_digests:
            card["video"] = (
                "gallery/unavailable-upstream/"
                f"{CURATED_GALLERY_ITEMS[item_id]}"
            )
            card["attributes"] = (
                "The upstream demo media is not installed; a local generated "
                "video with this filename was rejected to avoid false playback."
            )
        built_ins.append(card)
    return [*built_ins, *saved_items]


seg_ar_gateway.read_gallery_items = _read_gallery_items_with_built_ins


def _seed_gallery() -> None:
    gallery_dir = Path(os.environ.get("NOMAS_GALLERY_DIR", "/data/gallery-state/media"))
    seed_root = Path(os.environ.get("NOMAS_GALLERY_SEED_DIR", "/seed-outputs"))
    gallery_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(seed_root.rglob("*.mp4")) if seed_root.is_dir() else []
    sources = [source for source in sources if source.is_file() and source.stat().st_size]
    index_path = gallery_dir.parent / f".{gallery_dir.name}_items.json"
    if sources and not index_path.exists():
        lock = threading.RLock()
        for source in sources:
            description = ""
            text_path = source.with_suffix(".txt")
            if text_path.is_file():
                description = text_path.read_text(
                    encoding="utf-8", errors="replace"
                ).strip()[:1200]
            seg_ar_gateway.add_gallery_item_from_source(
                gallery_dir,
                source,
                {
                    "title": source.stem.replace("_", " ").replace("-", " ").title(),
                    "perspective": "third-person follow",
                    "subject": description[:400] or source.stem,
                    "attributes": description,
                    "direction": "Generated locally with Hy-Nomas.",
                },
                process_lock=lock,
            )

    _normalize_gallery(gallery_dir)

_seed_gallery()
seg_ar_gateway.main()
