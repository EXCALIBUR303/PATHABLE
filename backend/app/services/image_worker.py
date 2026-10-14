"""Standalone decoder with CPU/address-space/output limits; never imports the API."""

import hashlib
import json
import resource
import sys
import warnings
from pathlib import Path


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024 + 1, 10 * 1024 * 1024 + 1))
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = 20_000_000
    warnings.simplefilter("error", Image.DecompressionBombWarning)
    source, target, mime = sys.argv[1:]
    try:
        with Image.open(source) as image:
            expected = {"image/jpeg": "JPEG", "image/png": "PNG"}[mime]
            if (
                image.format != expected
                or getattr(image, "n_frames", 1) != 1
                or image.width * image.height > 20_000_000
            ):
                raise ValueError("Unsupported image")
            image.verify()
        with Image.open(source) as image:
            image.load()
            normalized = ImageOps.exif_transpose(image)
            normalized = normalized.convert("RGB" if mime == "image/jpeg" else "RGBA")
            # A new image discards all source EXIF, GPS, comments and text chunks.
            clean = Image.new(normalized.mode, normalized.size)
            clean.paste(normalized)
            clean.save(target, format=expected, **({"quality": 90} if expected == "JPEG" else {}))
            data = Path(target).read_bytes()
            if not data or len(data) > 10 * 1024 * 1024:
                raise ValueError("Normalized image exceeds its byte limit")
            print(
                json.dumps(
                    {
                        "ok": True,
                        "width_px": clean.width,
                        "height_px": clean.height,
                        "byte_size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                )
            )
    except (Exception, MemoryError):
        Path(target).unlink(missing_ok=True)
        print(json.dumps({"ok": False, "code": "INVALID_IMAGE"}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
