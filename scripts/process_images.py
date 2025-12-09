#!/usr/bin/env python3
"""Generate responsive image variants and modern formats for the site.

The workflow assumes high-resolution source assets live under
``static/source_images``. Running this script will:

* Copy any missing originals from ``static/Images`` into ``source_images``
  (first-run bootstrap).
* Produce an optimised fallback asset in ``static/Images`` (JPEG/PNG).
* Export WebP renditions for multiple widths (default: 480, 768, 1024, 1440).
* Export AVIF renditions when the local Pillow build supports it.

Example usage::

    python scripts/process_images.py --sizes 480,768,1024,1440 --quality 82

Install the ``Pillow`` dependency (see ``requirements.txt``) before running.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
SOURCE_DIR = STATIC_DIR / "source_images"
TARGET_DIR = STATIC_DIR / "Images"
DEFAULT_SIZES = (480, 768, 1024, 1440)


def _bootstrap_source(from_dir: Path, to_dir: Path) -> None:
    """Ensure ``source_images`` contains originals.

    Copies any JPEG/PNG files from the public Images directory into the source
    directory the first time the script runs.
    """

    if any(to_dir.rglob("*")):
        return

    candidates = list(from_dir.rglob("*.jpg")) + list(from_dir.rglob("*.jpeg")) + list(from_dir.rglob("*.png"))
    if not candidates:
        return

    print("[process-images] Bootstrapping source_images with existing assets…")
    for asset in candidates:
        relative = asset.relative_to(from_dir)
        destination = to_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(asset, destination)


def _parse_sizes(raw: str | None) -> tuple[int, ...]:
    if not raw:
        return DEFAULT_SIZES
    sizes: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            value = int(token)
        except ValueError as exc:  # pragma: no cover - defensive
            raise argparse.ArgumentTypeError(f"Invalid size '{token}'") from exc
        if value <= 0:
            raise argparse.ArgumentTypeError("Image widths must be greater than zero")
        sizes.append(value)
    if not sizes:
        return DEFAULT_SIZES
    return tuple(sorted(set(sizes)))


def _ensure_rgb(image: Image.Image) -> Image.Image:
    if image.mode in {"RGB", "RGBA", "LA"}:
        return image
    if image.mode == "P":
        return image.convert("RGBA")
    return image.convert("RGB")


def _resize(image: Image.Image, width: int) -> Image.Image:
    if image.width <= width:
        return image.copy()
    ratio = width / image.width
    height = int(round(image.height * ratio))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def _save_fallback(image: Image.Image, destination: Path, *, quality: int, overwrite: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        return

    ext = destination.suffix.lower()
    params: dict[str, object] = {"optimize": True}
    processed = image
    if ext in {".jpg", ".jpeg"}:
        params["quality"] = quality
        processed = image.convert("RGB")
    elif ext == ".png":
        params["compress_level"] = 6
        processed = ImageOps.exif_transpose(image)

    processed.save(destination, **params)
    print(f"[process-images] Saved fallback {destination.relative_to(STATIC_DIR)}")


def _supports_avif() -> bool:
    try:
        Image.registered_extensions()
    except Exception:  # pragma: no cover - extremely defensive
        return False

    return any(fmt.lower() == "avif" for fmt in Image.registered_extensions().values())


def _save_weighted(image: Image.Image, destination: Path, *, format_: str, quality: int, overwrite: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        return

    params: dict[str, object] = {"quality": quality}
    if format_.upper() == "WEBP":
        params["method"] = 6
        params["lossless"] = False
    img = image
    if image.mode not in {"RGB", "RGBA"}:
        img = image.convert("RGBA" if "A" in image.mode else "RGB")
    img.save(destination, format=format_.upper(), **params)
    print(f"[process-images] Saved {format_.lower()} {destination.relative_to(STATIC_DIR)}")


def _process_single(
    source_path: Path,
    *,
    widths: Iterable[int],
    quality: int,
    webp_quality: int,
    avif_quality: int,
    overwrite: bool,
    export_avif: bool,
) -> None:
    relative = source_path.relative_to(SOURCE_DIR)
    base_name = relative.stem
    target_base_dir = (TARGET_DIR / relative).parent
    fallback_ext = source_path.suffix.lower()
    fallback_path = target_base_dir / f"{base_name}{fallback_ext}"

    with Image.open(source_path) as original:
        original = ImageOps.exif_transpose(original)
        largest_width = max(widths)
        fallback_image = _resize(_ensure_rgb(original), largest_width)
        _save_fallback(fallback_image, fallback_path, quality=quality, overwrite=overwrite)

        for width in widths:
            resized = _resize(fallback_image if fallback_image.width <= width else original, width)
            webp_path = target_base_dir / f"{base_name}-{width}w.webp"
            _save_weighted(resized, webp_path, format_="WEBP", quality=webp_quality, overwrite=overwrite)
            if export_avif:
                avif_path = target_base_dir / f"{base_name}-{width}w.avif"
                try:
                    _save_weighted(resized, avif_path, format_="AVIF", quality=avif_quality, overwrite=overwrite)
                except (ValueError, OSError) as error:
                    # Pillow may lack AVIF support depending on the install. Skip gracefully.
                    print(f"[process-images] Skipping AVIF for {relative} ({error})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate responsive image derivatives")
    parser.add_argument("--sizes", help="Comma-separated list of widths", default=None)
    parser.add_argument("--quality", type=int, default=85, help="Fallback JPEG quality (default: 85)")
    parser.add_argument("--webp-quality", type=int, default=80, help="WebP quality (default: 80)")
    parser.add_argument("--avif-quality", type=int, default=45, help="AVIF quality (default: 45)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing derivatives")
    args = parser.parse_args(argv)

    widths = _parse_sizes(args.sizes)

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    _bootstrap_source(TARGET_DIR, SOURCE_DIR)

    export_avif = _supports_avif()
    if export_avif:
        print("[process-images] AVIF support detected – AVIF assets will be created.")
    else:
        print("[process-images] AVIF support not available – skipping AVIF outputs.")

    sources = sorted(
        path
        for path in SOURCE_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )

    if not sources:
        print("[process-images] No source images found. Add originals to static/source_images.")
        return 0

    for source in sources:
        _process_single(
            source,
            widths=widths,
            quality=args.quality,
            webp_quality=args.webp_quality,
            avif_quality=args.avif_quality,
            overwrite=args.overwrite,
            export_avif=export_avif,
        )

    print("[process-images] Completed image processing.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
