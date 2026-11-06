#!/usr/bin/env python3
"""Safe content-addressed storage for downloaded AI model artifacts.

The migrator never removes a source before a verified canonical copy exists.
Successful migrations leave a symlink at the original path and append a durable
TSV receipt to ``manifests/migrations.tsv``.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Iterable, Iterator


DEFAULT_STORE = Path(
    os.environ.get("AI_MODEL_STORE", "/mnt/A4C45B32C45B2C87/ai-models")
)
CHUNK_SIZE = 16 * 1024 * 1024
FICLONE = 0x40049409
MODEL_SUFFIXES = {
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".bin",
    ".gguf",
    ".onnx",
    ".engine",
    ".h5",
    ".tflite",
    ".pb",
    ".npz",
    ".params",
    ".model",
}
PRUNE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "site-packages",
    "dist-packages",
    "__pycache__",
}
COMFY_CATEGORIES = {
    "checkpoints",
    "configs",
    "loras",
    "vae",
    "text_encoders",
    "clip",
    "diffusion_models",
    "unet",
    "clip_vision",
    "style_models",
    "embeddings",
    "diffusers",
    "vae_approx",
    "controlnet",
    "t2i_adapter",
    "gligen",
    "upscale_models",
    "latent_upscale_models",
    "hypernetworks",
    "photomaker",
    "classifiers",
    "model_patches",
    "audio_encoders",
    "background_removal",
    "frame_interpolation",
    "geometry_estimation",
    "optical_flow",
    "detection",
    "pdd_acc",
}


def stderr(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def init_store(store: Path) -> None:
    directories = (
        store,
        store / "objects" / "sha256",
        store / "views" / "comfyui",
        store / "views" / "hy-nomas",
        store / "views" / "catalog",
        store / "huggingface" / "hub",
        store / "huggingface" / "xet",
        store / "huggingface" / "assets",
        store / "incoming",
        store / "manifests",
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o2775)


def canonical_object(store: Path, digest: str) -> Path:
    return store / "objects" / "sha256" / digest[:2] / digest / "data"


def copy_and_verify(source: Path, destination: Path, expected: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.parent.chmod(0o2775)
    destination.parent.parent.chmod(0o2775)
    incoming = destination.parents[4] / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    temporary = incoming / f"{expected}.{os.getpid()}.{uuid.uuid4().hex}.partial"
    copied_digest = hashlib.sha256()
    try:
        with source.open("rb") as input_handle, temporary.open("xb") as output_handle:
            while chunk := input_handle.read(CHUNK_SIZE):
                output_handle.write(chunk)
                copied_digest.update(chunk)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        if copied_digest.hexdigest() != expected:
            raise RuntimeError(f"source changed while copying: {source}")
        verified = sha256(temporary)
        if verified != expected:
            raise RuntimeError(
                f"temporary checksum mismatch: {temporary}: {verified} != {expected}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(temporary, 0o444)
        os.replace(temporary, destination)
        fsync_directory(destination.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def append_tsv(path: Path, header: list[str], row: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        if new_file:
            writer.writerow(header)
        writer.writerow(row)
        handle.flush()
        os.fsync(handle.fileno())


def relative_link(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    link.parent.chmod(0o2775)
    if link.is_symlink():
        try:
            if link.resolve(strict=True) == target.resolve(strict=True):
                return
        except FileNotFoundError:
            pass
    if link.exists() or link.is_symlink():
        raise FileExistsError(link)
    link.symlink_to(os.path.relpath(target, start=link.parent))


def unique_view_link(base: Path, name: str, target: Path, digest: str) -> Path:
    candidate = base / name
    if candidate.is_symlink():
        try:
            if candidate.resolve(strict=True) == target.resolve(strict=True):
                return candidate
        except FileNotFoundError:
            pass
    if candidate.exists() or candidate.is_symlink():
        suffixes = "".join(Path(name).suffixes)
        stem = name[: -len(suffixes)] if suffixes else name
        candidate = base / f"{stem}--{digest[:12]}{suffixes}"
    relative_link(candidate, target)
    return candidate


def comfy_category(source: Path) -> str | None:
    parts = source.parts
    lowered = [part.lower() for part in parts]
    for index, part in enumerate(lowered):
        if part == "models" and index + 1 < len(parts):
            category = parts[index + 1]
            if category.lower() in COMFY_CATEGORIES and any(
                marker in str(source).lower()
                for marker in ("comfyui", "comfyui-models", "magostudio")
            ):
                return category.lower()
    text = str(source).lower()
    if "/hy-nomas/models/dit/" in text:
        return "diffusion_models"
    if "/hy-nomas/models/vae/" in text:
        return "vae"
    return None


def catalog_category(source: Path) -> str:
    text = str(source).lower()
    suffix = source.suffix.lower()
    if "lora" in text:
        return "loras"
    if "vae" in text:
        return "vae"
    if "whisper" in text or "parakeet" in text or "wav2vec" in text:
        return "audio"
    if suffix == ".gguf":
        return "gguf"
    if suffix == ".onnx":
        return "onnx"
    if suffix == ".safetensors":
        return "safetensors"
    return "checkpoints"


def create_views(store: Path, source: Path, obj: Path, digest: str) -> list[Path]:
    created: list[Path] = []
    source_text = str(source)
    marker = "/Hy-Nomas/models/"
    if marker in source_text:
        relative = Path(source_text.split(marker, 1)[1])
        hynomas_link = store / "views" / "hy-nomas" / relative
        relative_link(hynomas_link, obj)
        created.append(hynomas_link)
    category = comfy_category(source)
    if category:
        comfy_link = unique_view_link(
            store / "views" / "comfyui" / category,
            source.name,
            obj,
            digest,
        )
        created.append(comfy_link)
    catalog_link = unique_view_link(
        store / "views" / "catalog" / catalog_category(source),
        source.name,
        obj,
        digest,
    )
    created.append(catalog_link)
    return created


def migrate_file(store: Path, source: Path, dry_run: bool = False) -> str:
    if source.is_symlink():
        try:
            target = source.resolve(strict=True)
        except FileNotFoundError:
            stderr(f"SKIP broken symlink: {source}")
            return "broken-symlink"
        if store == target or store in target.parents:
            print(f"PRESENT {source} -> {target}", flush=True)
            return "already-migrated"
        stderr(f"SKIP external symlink: {source} -> {target}")
        return "external-symlink"
    if not source.is_file():
        stderr(f"SKIP not a regular file: {source}")
        return "not-file"
    size = source.stat().st_size
    digest = sha256(source)
    obj = canonical_object(store, digest)
    if dry_run:
        print(f"WOULD-MIGRATE {source} -> {obj} sha256={digest}", flush=True)
        return "dry-run"
    if obj.exists():
        if obj.stat().st_size != size or sha256(obj) != digest:
            raise RuntimeError(f"corrupt canonical object: {obj}")
    else:
        copy_and_verify(source, obj, digest)
    create_views(store, source, obj, digest)

    backup = source.with_name(f".{source.name}.model-store-backup-{os.getpid()}")
    if backup.exists() or backup.is_symlink():
        raise FileExistsError(f"stale migration backup: {backup}")
    os.replace(source, backup)
    try:
        source.symlink_to(obj)
        fsync_directory(source.parent)
        if not source.is_file() or source.resolve(strict=True) != obj.resolve(strict=True):
            raise RuntimeError(f"replacement link verification failed: {source}")
    except BaseException:
        if source.is_symlink():
            source.unlink()
        os.replace(backup, source)
        fsync_directory(source.parent)
        raise
    backup.unlink()
    fsync_directory(source.parent)
    append_tsv(
        store / "manifests" / "migrations.tsv",
        ["timestamp", "size_bytes", "sha256", "source", "canonical"],
        [int(time.time()), size, digest, str(source), str(obj)],
    )
    print(f"MIGRATED {source} -> {obj} sha256={digest}", flush=True)
    return "migrated"


def manifest_paths(path: Path) -> Iterator[Path]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames or "path" not in reader.fieldnames:
            raise ValueError(f"manifest must have a 'path' column: {path}")
        for row in reader:
            value = (row.get("path") or "").strip()
            if value:
                yield Path(value)


def audit(roots: Iterable[Path], output: Path, minimum_size: int, store: Path) -> None:
    rows: list[tuple[int, str]] = []
    store_resolved = store.resolve()
    for root in roots:
        for directory, dirnames, filenames in os.walk(root, followlinks=False):
            directory_path = Path(directory)
            dirnames[:] = [
                name
                for name in dirnames
                if name not in PRUNE_DIRS
                and not (
                    (directory_path / name).resolve() == store_resolved
                    or store_resolved in (directory_path / name).resolve().parents
                )
            ]
            for filename in filenames:
                candidate = directory_path / filename
                if candidate.suffix.lower() not in MODEL_SUFFIXES:
                    continue
                try:
                    info = candidate.stat(follow_symlinks=False)
                except (FileNotFoundError, PermissionError):
                    continue
                if stat.S_ISREG(info.st_mode) and info.st_size >= minimum_size:
                    rows.append((info.st_size, str(candidate)))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["size_bytes", "path"])
        writer.writerows(sorted(set(rows), key=lambda row: row[1]))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output)
    fsync_directory(output.parent)
    print(f"AUDIT files={len(rows)} output={output}")


def verify(store: Path) -> None:
    manifest = store / "manifests" / "migrations.tsv"
    if not manifest.is_file():
        raise FileNotFoundError(manifest)
    checked_objects: set[Path] = set()
    failures = 0
    rows = 0
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            rows += 1
            source = Path(row["source"])
            obj = Path(row["canonical"])
            digest = row["sha256"]
            try:
                is_link = source.is_symlink()
                resolved_source = source.resolve(strict=True) if is_link else None
            except PermissionError:
                link_check = subprocess.run(
                    ["sudo", "-n", "test", "-L", str(source)],
                    check=False,
                )
                is_link = link_check.returncode == 0
                resolved_source = None
                if is_link:
                    readlink = subprocess.run(
                        ["sudo", "-n", "readlink", "-f", "--", str(source)],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    resolved_source = Path(readlink.stdout.strip())
            if not is_link:
                stderr(f"FAIL source is not a symlink: {source}")
                failures += 1
                continue
            try:
                if resolved_source != obj.resolve(strict=True):
                    stderr(f"FAIL wrong target: {source}")
                    failures += 1
                    continue
            except FileNotFoundError:
                stderr(f"FAIL broken link: {source}")
                failures += 1
                continue
            if obj not in checked_objects:
                if sha256(obj) != digest:
                    stderr(f"FAIL checksum: {obj}")
                    failures += 1
                checked_objects.add(obj)
    broken = []
    for root in (store / "views").rglob("*"):
        if root.is_symlink() and not root.exists():
            broken.append(root)
    for link in broken:
        stderr(f"FAIL broken view: {link}")
    failures += len(broken)
    print(
        f"VERIFY rows={rows} unique_objects={len(checked_objects)} "
        f"broken_views={len(broken)} failures={failures}"
    )
    if failures:
        raise SystemExit(1)


def copy_regular_verified(source: Path, destination: Path) -> str:
    """Copy one regular file and return its verified SHA-256."""
    expected = sha256(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{os.getpid()}.{uuid.uuid4().hex}.partial"
    )
    try:
        with source.open("rb") as input_handle, temporary.open("xb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle, CHUNK_SIZE)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        shutil.copystat(source, temporary, follow_symlinks=False)
        actual = sha256(temporary)
        if actual != expected:
            raise RuntimeError(
                f"copied file checksum mismatch: {source}: {actual} != {expected}"
            )
        os.replace(temporary, destination)
        fsync_directory(destination.parent)
        return expected
    finally:
        if temporary.exists():
            temporary.unlink()


def reflink_verified(
    source_object: Path, destination: Path, expected: str, source_mode: int
) -> None:
    """Create a Btrfs COW clone with an independent inode and verify it."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{os.getpid()}.{uuid.uuid4().hex}.partial"
    )
    try:
        with source_object.open("rb") as input_handle, temporary.open("xb") as output_handle:
            fcntl.ioctl(output_handle.fileno(), FICLONE, input_handle.fileno())
            output_handle.flush()
            os.fsync(output_handle.fileno())
        os.chmod(temporary, stat.S_IMODE(source_mode))
        if sha256(temporary) != expected:
            raise RuntimeError(f"reflink checksum mismatch: {source_object}")
        os.replace(temporary, destination)
        fsync_directory(destination.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def hf_conflict_path(destination: Path, label: str) -> Path:
    suffixes = "".join(destination.suffixes)
    stem = destination.name[: -len(suffixes)] if suffixes else destination.name
    candidate = destination.with_name(f"{stem}.imported-{label}{suffixes}")
    counter = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = destination.with_name(
            f"{stem}.imported-{label}-{counter}{suffixes}"
        )
        counter += 1
    return candidate


def merge_hf_cache(store: Path, source: Path) -> None:
    """Merge one complete HF_HOME tree, then replace it with a symlink.

    Hub snapshot symlinks are copied verbatim, so their relative links to the
    repository's ``blobs`` directory remain valid in the canonical tree.
    Lock files are transient and deliberately excluded.
    """
    canonical = store / "huggingface"
    canonical.mkdir(parents=True, exist_ok=True)
    source = source.absolute()
    if source.is_symlink():
        try:
            target = source.resolve(strict=True)
        except FileNotFoundError as error:
            raise RuntimeError(f"broken HF cache symlink: {source}") from error
        if target == canonical.resolve():
            print(f"HF-PRESENT {source} -> {canonical}", flush=True)
            return
        raise RuntimeError(f"HF cache is an external symlink: {source} -> {target}")
    if not source.is_dir():
        raise NotADirectoryError(source)
    if source.resolve() == canonical.resolve():
        return
    label = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:12]
    receipt = store / "manifests" / "hf-merges.tsv"
    copied = reflinked = reused = conflicts = symlinks = 0

    for directory, dirnames, filenames in os.walk(source, followlinks=False):
        source_dir = Path(directory)
        relative_dir = source_dir.relative_to(source)
        if ".locks" in relative_dir.parts:
            dirnames[:] = []
            continue
        destination_dir = canonical / relative_dir
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_dir.chmod(destination_dir.stat().st_mode | stat.S_ISGID)

        for dirname in list(dirnames):
            source_entry = source_dir / dirname
            if dirname == ".locks":
                dirnames.remove(dirname)
                continue
            if source_entry.is_symlink():
                dirnames.remove(dirname)
                destination_entry = destination_dir / dirname
                link_text = os.readlink(source_entry)
                if destination_entry.is_symlink() and os.readlink(destination_entry) == link_text:
                    reused += 1
                    continue
                if destination_entry.exists() or destination_entry.is_symlink():
                    destination_entry = hf_conflict_path(destination_entry, label)
                    conflicts += 1
                destination_entry.symlink_to(link_text)
                symlinks += 1

        for filename in filenames:
            source_entry = source_dir / filename
            if ".locks" in source_entry.parts:
                continue
            destination_entry = destination_dir / filename
            if source_entry.is_symlink():
                link_text = os.readlink(source_entry)
                if destination_entry.is_symlink() and os.readlink(destination_entry) == link_text:
                    reused += 1
                    continue
                if destination_entry.exists() or destination_entry.is_symlink():
                    destination_entry = hf_conflict_path(destination_entry, label)
                    conflicts += 1
                destination_entry.symlink_to(link_text)
                symlinks += 1
                continue
            if not source_entry.is_file():
                continue
            source_hash = sha256(source_entry)
            if destination_entry.is_file() and not destination_entry.is_symlink():
                if (
                    destination_entry.stat().st_size == source_entry.stat().st_size
                    and sha256(destination_entry) == source_hash
                ):
                    reused += 1
                    continue
                destination_entry = hf_conflict_path(destination_entry, label)
                conflicts += 1
            elif destination_entry.exists() or destination_entry.is_symlink():
                destination_entry = hf_conflict_path(destination_entry, label)
                conflicts += 1
            obj = canonical_object(store, source_hash)
            if obj.is_file() and obj.stat().st_size == source_entry.stat().st_size:
                try:
                    reflink_verified(
                        obj,
                        destination_entry,
                        source_hash,
                        source_entry.stat().st_mode,
                    )
                    reflinked += 1
                except OSError:
                    copied_hash = copy_regular_verified(source_entry, destination_entry)
                    if copied_hash != source_hash:
                        raise RuntimeError(f"HF merge checksum mismatch: {source_entry}")
                    copied += 1
            else:
                copied_hash = copy_regular_verified(source_entry, destination_entry)
                if copied_hash != source_hash:
                    raise RuntimeError(f"HF merge checksum mismatch: {source_entry}")
                copied += 1

    backup = source.with_name(f".{source.name}.model-store-backup-{os.getpid()}")
    if backup.exists() or backup.is_symlink():
        raise FileExistsError(backup)
    os.replace(source, backup)
    try:
        source.symlink_to(canonical)
        fsync_directory(source.parent)
        if source.resolve(strict=True) != canonical.resolve(strict=True):
            raise RuntimeError(f"HF cache replacement failed: {source}")
    except BaseException:
        if source.is_symlink():
            source.unlink()
        os.replace(backup, source)
        fsync_directory(source.parent)
        raise
    shutil.rmtree(backup)
    fsync_directory(source.parent)
    append_tsv(
        receipt,
        ["timestamp", "source", "canonical", "copied", "reflinked", "reused", "conflicts", "symlinks"],
        [
            int(time.time()),
            str(source),
            str(canonical),
            copied,
            reflinked,
            reused,
            conflicts,
            symlinks,
        ],
    )
    print(
        f"HF-MERGED {source} -> {canonical} copied={copied} reflinked={reflinked} reused={reused} "
        f"conflicts={conflicts} symlinks={symlinks}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--root", action="append", type=Path, required=True)
    audit_parser.add_argument("--output", type=Path, required=True)
    audit_parser.add_argument("--min-size-mib", type=int, default=50)
    migrate_parser = subparsers.add_parser("migrate")
    migrate_parser.add_argument("--manifest", type=Path, required=True)
    migrate_parser.add_argument("--dry-run", action="store_true")
    subparsers.add_parser("verify")
    hf_parser = subparsers.add_parser("merge-hf")
    hf_parser.add_argument("--source", action="append", type=Path, required=True)

    args = parser.parse_args()
    store = args.store.resolve()
    init_store(store)
    if args.command == "init":
        print(store)
    elif args.command == "audit":
        audit(args.root, args.output, args.min_size_mib * 1024 * 1024, store)
    elif args.command == "migrate":
        failures = 0
        for source in manifest_paths(args.manifest):
            try:
                migrate_file(store, source, args.dry_run)
            except BaseException as error:
                failures += 1
                stderr(f"ERROR {source}: {error}")
                if isinstance(error, KeyboardInterrupt):
                    raise
        if failures:
            raise SystemExit(f"migration failures={failures}")
    elif args.command == "verify":
        verify(store)
    elif args.command == "merge-hf":
        for source in args.source:
            merge_hf_cache(store, source)


if __name__ == "__main__":
    main()
