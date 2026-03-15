#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "pillow-heif", "numpy"]
# ///
"""format-io: Read image metadata, convert formats, handle alpha/EXIF/ICC, split/assemble animation frames."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image, ExifTags, ImageColor, ImageCms, ImageOps

# ---------------------------------------------------------------------------
# HEIF support (optional — graceful degradation)
# ---------------------------------------------------------------------------
_HEIF_AVAILABLE = False
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    _HEIF_AVAILABLE = True
except Exception:
    pass

# ---------------------------------------------------------------------------
# Supported extensions (lowercase, with leading dot)
# ---------------------------------------------------------------------------
_SUPPORTED_READ = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp", ".gif", ".heic", ".heif"}
_SUPPORTED_WRITE = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp", ".gif", ".heic", ".heif"}


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------
def _err(msg: str) -> None:
    """Print error to stderr and exit 1."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def _info(msg: str) -> None:
    """Print informational message to stderr."""
    print(msg, file=sys.stderr)


def _validate_input(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        _err(f"Input file not found: {path}")
    if not p.is_file():
        _err(f"Input path is not a file: {path}")
    ext = p.suffix.lower()
    if ext not in _SUPPORTED_READ:
        _err(f"Unsupported input format '{ext}'. Supported: {', '.join(sorted(_SUPPORTED_READ))}")
    if ext in (".heic", ".heif") and not _HEIF_AVAILABLE:
        _err("HEIC/HEIF support requires pillow-heif. It failed to load — check your installation.")
    return p


def _validate_output(path: str) -> Path:
    p = Path(path)
    if not p.parent.exists():
        _err(f"Output directory does not exist: {p.parent}")
    ext = p.suffix.lower()
    if ext not in _SUPPORTED_WRITE:
        _err(f"Unsupported output format '{ext}'. Supported: {', '.join(sorted(_SUPPORTED_WRITE))}")
    if ext in (".heic", ".heif") and not _HEIF_AVAILABLE:
        _err("HEIC/HEIF output requires pillow-heif. It failed to load — check your installation.")
    return p


def _open_image(path: Path) -> Image.Image:
    try:
        img = Image.open(path)
        return img
    except Exception as e:
        _err(f"Failed to open image '{path}': {e}")


def _save_image(img: Image.Image, path: Path, **kwargs) -> None:
    try:
        img.save(str(path), **kwargs)
        _info(f"Saved: {path} ({os.path.getsize(path)} bytes)")
    except Exception as e:
        _err(f"Failed to save image '{path}': {e}")


def _infer_save_params(output_path: Path, args: argparse.Namespace) -> dict:
    """Build format-specific save kwargs from output extension + CLI args."""
    ext = output_path.suffix.lower()
    params: dict = {}

    if ext in (".jpg", ".jpeg"):
        params["format"] = "JPEG"
        params["quality"] = getattr(args, "quality", None) or 85
    elif ext == ".png":
        params["format"] = "PNG"
        compress = getattr(args, "compress_level", None)
        if compress is not None:
            params["compress_level"] = compress
    elif ext == ".webp":
        params["format"] = "WEBP"
        if getattr(args, "lossless", False):
            params["lossless"] = True
        else:
            params["quality"] = getattr(args, "quality", None) or 80
    elif ext in (".tiff", ".tif"):
        params["format"] = "TIFF"
        tc = getattr(args, "tiff_compression", None)
        if tc:
            params["compression"] = tc
    elif ext == ".bmp":
        params["format"] = "BMP"
    elif ext == ".gif":
        params["format"] = "GIF"
    elif ext in (".heic", ".heif"):
        params["format"] = "HEIF"
        params["quality"] = getattr(args, "quality", None) or 80

    return params


def _parse_color(color_str: str) -> tuple[int, ...]:
    """Parse hex or named color string to RGB tuple."""
    try:
        return ImageColor.getrgb(color_str)
    except (ValueError, AttributeError):
        _err(f"Invalid color '{color_str}'. Use hex (#RRGGBB) or named color (white, red, etc.).")


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_info(args: argparse.Namespace) -> None:
    """Display image metadata as JSON to stdout."""
    inp = _validate_input(args.input)
    img = _open_image(inp)

    # Basic info (lazy — doesn't load pixels)
    width, height = img.size
    result: dict = {
        "file": str(inp),
        "format": img.format,
        "mode": img.mode,
        "width": width,
        "height": height,
        "file_size_bytes": os.path.getsize(inp),
    }

    # DPI
    dpi = img.info.get("dpi")
    if dpi:
        result["dpi"] = list(dpi)

    # Animation
    n_frames = getattr(img, "n_frames", 1)
    is_animated = getattr(img, "is_animated", False)
    result["n_frames"] = n_frames
    result["is_animated"] = is_animated

    # EXIF presence
    try:
        exif = img.getexif()
        result["has_exif"] = len(exif) > 0
    except Exception:
        result["has_exif"] = False

    # ICC profile presence
    result["has_icc_profile"] = "icc_profile" in img.info

    # Alpha channel
    result["has_alpha"] = img.mode in ("RGBA", "LA", "PA")

    print(json.dumps(result, indent=2))


def cmd_convert(args: argparse.Namespace) -> None:
    """Convert image to a different format."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    # Force-load pixels so we're not tied to the file handle
    img.load()

    out_ext = out.suffix.lower()
    save_params = _infer_save_params(out, args)

    # RGBA → JPEG: explicit error
    if out_ext in (".jpg", ".jpeg") and img.mode == "RGBA":
        _err(
            "Cannot save RGBA image as JPEG (JPEG does not support transparency). "
            "Remove alpha first: uv run format_io.py alpha INPUT -o intermediate.png --mode remove"
        )

    # Palette mode (P) → RGB for JPEG
    if out_ext in (".jpg", ".jpeg") and img.mode == "P":
        img = img.convert("RGB")

    # LA mode → L for JPEG (strip alpha)
    if out_ext in (".jpg", ".jpeg") and img.mode == "LA":
        _err(
            "Cannot save LA (grayscale + alpha) image as JPEG. "
            "Remove alpha first: uv run format_io.py alpha INPUT -o intermediate.png --mode remove"
        )

    # Mode I (32-bit) → 8-bit for formats that need it
    if img.mode == "I" and out_ext in (".jpg", ".jpeg", ".webp", ".bmp", ".gif"):
        import numpy as np

        arr = np.array(img)
        # Normalize to 0-255
        mn, mx = arr.min(), arr.max()
        if mx > mn:
            arr = ((arr - mn) / (mx - mn) * 255).astype("uint8")
        else:
            arr = (arr * 0).astype("uint8")
        img = Image.fromarray(arr, mode="L")
        _info("Converted 32-bit (mode I) to 8-bit grayscale for output format compatibility.")

    # RGBA → GIF: quantize
    if out_ext == ".gif" and img.mode == "RGBA":
        # Preserve transparency for GIF
        save_params["transparency"] = 0
        img = img.convert("RGBA")

    # Ensure RGB for JPEG if still not
    if out_ext in (".jpg", ".jpeg") and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    _save_image(img, out, **save_params)


def cmd_alpha(args: argparse.Namespace) -> None:
    """Handle alpha channel: remove or extract."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)
    img.load()

    mode = args.mode

    if mode == "remove":
        if img.mode not in ("RGBA", "LA", "PA"):
            _info(f"Image has no alpha channel (mode: {img.mode}). Saving as-is.")
            save_params = _infer_save_params(out, args)
            _save_image(img, out, **save_params)
            return

        bg_color = _parse_color(args.background)
        if img.mode == "LA":
            # Grayscale + alpha
            bg = Image.new("L", img.size, bg_color[0] if len(bg_color) >= 1 else 255)
            alpha = img.split()[-1]
            bg.paste(img.split()[0], mask=alpha)
            result = bg
        elif img.mode == "PA":
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, bg_color[:3])
            bg.paste(img, mask=img.split()[3])
            result = bg
        else:
            # RGBA
            bg = Image.new("RGB", img.size, bg_color[:3])
            bg.paste(img, mask=img.split()[3])
            result = bg

        save_params = _infer_save_params(out, args)
        _save_image(result, out, **save_params)

    elif mode == "extract":
        if img.mode not in ("RGBA", "LA", "PA"):
            _err(f"Image has no alpha channel to extract (mode: {img.mode}).")

        if img.mode == "PA":
            img = img.convert("RGBA")

        alpha = img.split()[-1]
        save_params = _infer_save_params(out, args)
        _save_image(alpha, out, **save_params)


def cmd_exif(args: argparse.Namespace) -> None:
    """Handle EXIF data: read, strip, or auto-orient."""
    inp = _validate_input(args.input)
    img = _open_image(inp)
    img.load()

    mode = args.mode

    if mode == "read":
        try:
            exif = img.getexif()
        except Exception:
            exif = {}

        if not exif:
            _info("No EXIF data found.")
            print("{}")
            return

        decoded: dict = {}
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, f"Unknown_{tag_id}")
            # Make values JSON-serializable
            if isinstance(value, bytes):
                # Try to decode as UTF-8, fallback to hex
                try:
                    value = value.decode("utf-8", errors="replace")
                except Exception:
                    value = value.hex()
            elif isinstance(value, tuple):
                value = list(value)
            elif not isinstance(value, (str, int, float, bool, list, type(None))):
                value = str(value)
            decoded[tag_name] = value

        print(json.dumps(decoded, indent=2, default=str))

    elif mode == "strip":
        out = _validate_output(args.output)
        save_params = _infer_save_params(out, args)

        # Preserve ICC profile if present
        icc = img.info.get("icc_profile")

        # Remove EXIF by not passing it, and explicitly clearing
        if "exif" in img.info:
            del img.info["exif"]
        save_params["exif"] = b""

        if icc:
            save_params["icc_profile"] = icc

        _save_image(img, out, **save_params)
        _info("EXIF data stripped.")

    elif mode == "auto-orient":
        out = _validate_output(args.output)

        # Apply EXIF orientation
        oriented = ImageOps.exif_transpose(img)
        if oriented is None:
            oriented = img

        save_params = _infer_save_params(out, args)
        # Save without EXIF orientation (already applied)
        save_params["exif"] = b""

        # Preserve ICC
        icc = img.info.get("icc_profile")
        if icc:
            save_params["icc_profile"] = icc

        _save_image(oriented, out, **save_params)
        _info("Auto-oriented and saved without EXIF orientation tag.")


def cmd_icc(args: argparse.Namespace) -> None:
    """Handle ICC color profiles: strip or convert to sRGB."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)
    img.load()

    mode = args.mode

    if mode == "strip":
        if "icc_profile" not in img.info:
            _info("No ICC profile found. Saving as-is.")
        else:
            del img.info["icc_profile"]
            _info("ICC profile stripped.")

        save_params = _infer_save_params(out, args)
        # Preserve EXIF if present
        exif_data = img.info.get("exif")
        if exif_data:
            save_params["exif"] = exif_data

        _save_image(img, out, **save_params)

    elif mode == "convert":
        icc_data = img.info.get("icc_profile")
        if not icc_data:
            _info("No ICC profile found. Saving as-is (assumed sRGB).")
            save_params = _infer_save_params(out, args)
            _save_image(img, out, **save_params)
            return

        # Check if already sRGB (heuristic: look at profile description)
        try:
            src_profile = ImageCms.ImageCmsProfile(ImageCms.core.profile_frombytes(icc_data))
            desc = ImageCms.getProfileDescription(src_profile).strip().lower()
            if "srgb" in desc:
                _info(f"Profile already sRGB ('{desc}'). Saving as-is.")
                save_params = _infer_save_params(out, args)
                # Keep the existing ICC profile
                save_params["icc_profile"] = icc_data
                exif_data = img.info.get("exif")
                if exif_data:
                    save_params["exif"] = exif_data
                _save_image(img, out, **save_params)
                return
        except Exception:
            pass

        # Intent mapping
        intent_map = {
            "perceptual": ImageCms.Intent.PERCEPTUAL,
            "relative": ImageCms.Intent.RELATIVE_COLORIMETRIC,
            "saturation": ImageCms.Intent.SATURATION,
            "absolute": ImageCms.Intent.ABSOLUTE_COLORIMETRIC,
        }
        intent = intent_map.get(args.intent, ImageCms.Intent.PERCEPTUAL)

        try:
            src_profile = ImageCms.ImageCmsProfile(ImageCms.core.profile_frombytes(icc_data))
            dst_profile = ImageCms.createProfile("sRGB")

            # Determine the correct mode for conversion
            if img.mode == "RGBA":
                conversion_mode = "RGBA"
            elif img.mode in ("L", "LA"):
                # For grayscale, convert to RGB first, then convert profile
                img = img.convert("RGB")
                conversion_mode = "RGB"
            else:
                conversion_mode = "RGB"
                if img.mode != "RGB":
                    img = img.convert("RGB")

            converted = ImageCms.profileToProfile(
                img, src_profile, dst_profile,
                renderingIntent=intent,
                outputMode=conversion_mode,
            )

            # Embed sRGB profile in output
            srgb_profile = ImageCms.ImageCmsProfile(dst_profile)
            srgb_bytes = srgb_profile.tobytes()

            save_params = _infer_save_params(out, args)
            save_params["icc_profile"] = srgb_bytes

            exif_data = img.info.get("exif")
            if exif_data:
                save_params["exif"] = exif_data

            _save_image(converted, out, **save_params)
            _info(f"Converted ICC profile to sRGB (intent: {args.intent}).")

        except Exception as e:
            _err(f"ICC profile conversion failed: {e}")


def cmd_split_frames(args: argparse.Namespace) -> None:
    """Split animated GIF/WebP into individual frames."""
    inp = _validate_input(args.input)
    img = _open_image(inp)

    if not getattr(img, "is_animated", False):
        _err(f"Image is not animated (format: {img.format}, frames: {getattr(img, 'n_frames', 1)}).")

    out_dir = Path(args.output)
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
    elif not out_dir.is_dir():
        _err(f"Output path exists and is not a directory: {out_dir}")

    fmt = args.format.lower()
    if fmt not in ("png", "webp", "jpg", "jpeg", "bmp", "tiff"):
        _err(f"Unsupported frame format '{fmt}'. Use png, webp, jpg, bmp, or tiff.")

    n_frames = getattr(img, "n_frames", 1)
    durations: list[int] = []
    padding = len(str(n_frames - 1))

    for i in range(n_frames):
        img.seek(i)
        frame = img.copy()

        # Convert palette/P mode to RGBA (preserving transparency)
        if frame.mode == "P":
            frame = frame.convert("RGBA")
        elif frame.mode not in ("RGB", "RGBA", "L", "LA"):
            frame = frame.convert("RGB")

        # For JPEG output, ensure no alpha
        if fmt in ("jpg", "jpeg") and frame.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", frame.size, (255, 255, 255))
            if frame.mode == "RGBA":
                bg.paste(frame, mask=frame.split()[3])
            else:
                bg.paste(frame.split()[0], mask=frame.split()[1])
            frame = bg

        frame_name = f"frame_{str(i).zfill(max(padding, 3))}.{fmt}"
        frame_path = out_dir / frame_name
        frame.save(str(frame_path))

        # Get frame duration
        duration = img.info.get("duration", 100)
        durations.append(duration)

    # Write frames info JSON
    frames_info = {
        "source": str(inp),
        "n_frames": n_frames,
        "format": fmt,
        "durations_ms": durations,
        "frames": [f"frame_{str(i).zfill(max(padding, 3))}.{fmt}" for i in range(n_frames)],
    }
    info_path = out_dir / "frames_info.json"
    with open(info_path, "w") as f:
        json.dump(frames_info, f, indent=2)

    _info(f"Split {n_frames} frames to {out_dir}/ (format: {fmt})")
    _info(f"Frame info: {info_path}")


def cmd_assemble_frames(args: argparse.Namespace) -> None:
    """Assemble individual frames into an animated GIF/WebP."""
    out = _validate_output(args.output)
    out_ext = out.suffix.lower()

    if out_ext not in (".gif", ".webp"):
        _err(f"Animated output must be .gif or .webp, got '{out_ext}'.")

    # Collect input frames
    input_paths: list[Path] = []
    for p in args.inputs:
        pp = Path(p)
        if not pp.exists():
            _err(f"Input frame not found: {p}")
        if not pp.is_file():
            _err(f"Input path is not a file: {p}")
        input_paths.append(pp)

    if len(input_paths) < 2:
        _err("Need at least 2 frames to assemble an animation.")

    # Load all frames
    frames: list[Image.Image] = []
    for pp in input_paths:
        try:
            frm = Image.open(pp)
            frm.load()
            frames.append(frm)
        except Exception as e:
            _err(f"Failed to open frame '{pp}': {e}")

    # Verify consistent dimensions
    w0, h0 = frames[0].size
    for i, frm in enumerate(frames[1:], 1):
        if frm.size != (w0, h0):
            _err(
                f"Frame dimension mismatch: frame 0 is {w0}x{h0}, "
                f"frame {i} is {frm.size[0]}x{frm.size[1]}. All frames must have the same dimensions."
            )

    # Determine durations
    durations: list[int] = []
    if args.durations:
        # Load from JSON file
        dur_path = Path(args.durations)
        if not dur_path.exists():
            _err(f"Durations file not found: {args.durations}")
        try:
            with open(dur_path) as f:
                dur_data = json.load(f)
            # Accept either a flat list or a dict with "durations_ms" key
            if isinstance(dur_data, list):
                durations = [int(d) for d in dur_data]
            elif isinstance(dur_data, dict) and "durations_ms" in dur_data:
                durations = [int(d) for d in dur_data["durations_ms"]]
            else:
                _err("Durations file must be a JSON array or object with 'durations_ms' key.")
        except (json.JSONDecodeError, ValueError) as e:
            _err(f"Failed to parse durations file: {e}")

        if len(durations) != len(frames):
            _err(f"Durations count ({len(durations)}) doesn't match frame count ({len(frames)}).")
    else:
        durations = [args.delay] * len(frames)

    # GIF: round durations to 10ms granularity
    if out_ext == ".gif":
        rounded = [max(10, round(d / 10) * 10) for d in durations]
        if rounded != durations:
            _info("GIF durations rounded to 10ms granularity.")
        durations = rounded

    # Ensure correct mode for output
    if out_ext == ".gif":
        # Convert to RGBA for GIF (handles transparency)
        processed: list[Image.Image] = []
        for frm in frames:
            if frm.mode != "RGBA":
                frm = frm.convert("RGBA")
            processed.append(frm)
        frames = processed
    else:
        # WebP: ensure consistent mode
        target_mode = "RGBA" if any(f.mode in ("RGBA", "LA", "PA") for f in frames) else "RGB"
        processed = []
        for frm in frames:
            if frm.mode != target_mode:
                frm = frm.convert(target_mode)
            processed.append(frm)
        frames = processed

    # Build save kwargs
    save_kwargs: dict = {
        "save_all": True,
        "append_images": frames[1:],
        "duration": durations,
        "loop": args.loop,
    }

    if out_ext == ".gif":
        save_kwargs["format"] = "GIF"
        save_kwargs["disposal"] = 2  # restore to background
    else:
        save_kwargs["format"] = "WEBP"

    _save_image(frames[0], out, **save_kwargs)
    _info(f"Assembled {len(frames)} frames into {out}")


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="format_io",
        description="Image format conversion, metadata, and animation frame handling.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- info ---
    p_info = sub.add_parser("info", help="Display image metadata as JSON")
    p_info.add_argument("input", help="Input image path")

    # --- convert ---
    p_convert = sub.add_parser("convert", help="Convert image to a different format")
    p_convert.add_argument("input", help="Input image path")
    p_convert.add_argument("-o", "--output", required=True, help="Output image path")
    p_convert.add_argument("--quality", type=int, help="Quality for JPEG/WebP/HEIC (1-100)")
    p_convert.add_argument("--lossless", action="store_true", help="Lossless WebP output")
    p_convert.add_argument("--compress-level", type=int, help="PNG compression level (0-9)")
    p_convert.add_argument("--tiff-compression", help="TIFF compression: none, tiff_lzw, tiff_deflate, etc.")

    # --- alpha ---
    p_alpha = sub.add_parser("alpha", help="Handle alpha channel")
    p_alpha.add_argument("input", help="Input image path")
    p_alpha.add_argument("-o", "--output", required=True, help="Output image path")
    p_alpha.add_argument("--mode", required=True, choices=["remove", "extract"], help="Alpha operation")
    p_alpha.add_argument("--background", default="white", help="Background color for alpha removal (default: white)")

    # --- exif ---
    p_exif = sub.add_parser("exif", help="Handle EXIF metadata")
    p_exif.add_argument("input", help="Input image path")
    p_exif.add_argument("--mode", required=True, choices=["read", "strip", "auto-orient"], help="EXIF operation")
    p_exif.add_argument("-o", "--output", help="Output path (required for strip/auto-orient)")

    # --- icc ---
    p_icc = sub.add_parser("icc", help="Handle ICC color profiles")
    p_icc.add_argument("input", help="Input image path")
    p_icc.add_argument("-o", "--output", required=True, help="Output image path")
    p_icc.add_argument("--mode", required=True, choices=["strip", "convert"], help="ICC operation")
    p_icc.add_argument("--intent", default="perceptual",
                        choices=["perceptual", "relative", "saturation", "absolute"],
                        help="Rendering intent for ICC conversion (default: perceptual)")

    # --- split-frames ---
    p_split = sub.add_parser("split-frames", help="Split animated image into frames")
    p_split.add_argument("input", help="Input animated image path")
    p_split.add_argument("-o", "--output", required=True, help="Output directory for frames")
    p_split.add_argument("--format", default="png", help="Output frame format (default: png)")

    # --- assemble-frames ---
    p_assemble = sub.add_parser("assemble-frames", help="Assemble frames into animated image")
    p_assemble.add_argument("inputs", nargs="+", help="Input frame paths (in order)")
    p_assemble.add_argument("-o", "--output", required=True, help="Output animated image path (.gif or .webp)")
    p_assemble.add_argument("--delay", type=int, default=100, help="Frame delay in ms (default: 100)")
    p_assemble.add_argument("--loop", type=int, default=0, help="Loop count (0 = infinite, default: 0)")
    p_assemble.add_argument("--durations", help="JSON file with per-frame durations in ms")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Validate output is required for exif strip/auto-orient
    if args.command == "exif" and args.mode in ("strip", "auto-orient") and not args.output:
        _err(f"--output is required for exif {args.mode}")

    dispatch = {
        "info": cmd_info,
        "convert": cmd_convert,
        "alpha": cmd_alpha,
        "exif": cmd_exif,
        "icc": cmd_icc,
        "split-frames": cmd_split_frames,
        "assemble-frames": cmd_assemble_frames,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
