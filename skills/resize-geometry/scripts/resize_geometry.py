#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy"]
# ///
"""resize-geometry: Resize, crop, auto-crop, pad, rotate/flip, and montage grid layout."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageColor

# ---------------------------------------------------------------------------
# Supported extensions (lowercase, with leading dot)
# ---------------------------------------------------------------------------
_SUPPORTED_READ = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp", ".gif"}
_SUPPORTED_WRITE = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp", ".gif"}


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
    return p


def _validate_output(path: str) -> Path:
    p = Path(path)
    if not p.parent.exists():
        _err(f"Output directory does not exist: {p.parent}")
    ext = p.suffix.lower()
    if ext not in _SUPPORTED_WRITE:
        _err(f"Unsupported output format '{ext}'. Supported: {', '.join(sorted(_SUPPORTED_WRITE))}")
    return p


def _open_image(path: Path) -> Image.Image:
    try:
        img = Image.open(path)
        img.load()
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
    """Build format-specific save kwargs from output extension."""
    ext = output_path.suffix.lower()
    params: dict = {}

    if ext in (".jpg", ".jpeg"):
        params["format"] = "JPEG"
        params["quality"] = getattr(args, "quality", None) or 85
    elif ext == ".png":
        params["format"] = "PNG"
    elif ext == ".webp":
        params["format"] = "WEBP"
        params["quality"] = getattr(args, "quality", None) or 80
    elif ext in (".tiff", ".tif"):
        params["format"] = "TIFF"
    elif ext == ".bmp":
        params["format"] = "BMP"
    elif ext == ".gif":
        params["format"] = "GIF"

    return params


def _parse_color(color_str: str) -> tuple[int, ...]:
    """Parse hex or named color string to RGB(A) tuple."""
    try:
        return ImageColor.getrgb(color_str)
    except (ValueError, AttributeError):
        _err(f"Invalid color '{color_str}'. Use hex (#RRGGBB) or named color (white, red, etc.).")


def _parse_size(size_str: str) -> tuple[int, int]:
    """Parse 'WxH' string into (width, height) tuple."""
    parts = size_str.lower().split("x")
    if len(parts) != 2:
        _err(f"Invalid size '{size_str}'. Expected format: WxH (e.g., 800x600).")
    try:
        w, h = int(parts[0]), int(parts[1])
    except ValueError:
        _err(f"Invalid size '{size_str}'. Width and height must be integers.")
    if w <= 0 or h <= 0:
        _err(f"Invalid size '{size_str}'. Width and height must be positive.")
    return w, h


def _ensure_mode_for_output(img: Image.Image, output_path: Path) -> Image.Image:
    """Convert image mode if needed for the output format."""
    ext = output_path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        if img.mode == "RGBA":
            _err(
                "Cannot save RGBA image as JPEG (JPEG does not support transparency). "
                "Remove alpha first with format-io: uv run format_io.py alpha INPUT -o intermediate.png --mode remove"
            )
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
    elif ext == ".bmp":
        if img.mode == "RGBA":
            img = img.convert("RGB")
    return img


# ---------------------------------------------------------------------------
# Resampling filter map
# ---------------------------------------------------------------------------
_RESAMPLE_MAP = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}


# ---------------------------------------------------------------------------
# Gravity helper
# ---------------------------------------------------------------------------
def _gravity_offset(
    inner_w: int, inner_h: int, outer_w: int, outer_h: int, gravity: str
) -> tuple[int, int]:
    """Compute (x, y) offset to place inner rect within outer rect by gravity."""
    gravity = gravity.lower().replace("-", "").replace("_", "")
    cx = (outer_w - inner_w) // 2
    cy = (outer_h - inner_h) // 2

    offsets = {
        "center": (cx, cy),
        "top": (cx, 0),
        "bottom": (cx, outer_h - inner_h),
        "left": (0, cy),
        "right": (outer_w - inner_w, cy),
        "topleft": (0, 0),
        "topright": (outer_w - inner_w, 0),
        "bottomleft": (0, outer_h - inner_h),
        "bottomright": (outer_w - inner_w, outer_h - inner_h),
    }

    if gravity not in offsets:
        _err(
            f"Invalid gravity '{gravity}'. "
            f"Choose from: center, top, bottom, left, right, top-left, top-right, bottom-left, bottom-right."
        )
    return offsets[gravity]


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_resize(args: argparse.Namespace) -> None:
    """Resize image by dimensions, percentage, or fit-within bounds."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    orig_w, orig_h = img.size
    resample = _RESAMPLE_MAP[args.resample]

    # Determine target dimensions
    has_width = args.width is not None
    has_height = args.height is not None
    has_percent = args.percent is not None
    has_fit = args.fit is not None

    mode_count = sum([has_width or has_height, has_percent, has_fit])
    if mode_count == 0:
        _err("Specify at least one of: --width/--height, --percent, or --fit.")
    if mode_count > 1:
        _err("Use only one resize mode: --width/--height, --percent, or --fit. Do not combine them.")

    if has_percent:
        if args.percent <= 0:
            _err(f"--percent must be positive, got {args.percent}.")
        scale = args.percent / 100.0
        new_w = max(1, round(orig_w * scale))
        new_h = max(1, round(orig_h * scale))

    elif has_fit:
        fit_w, fit_h = _parse_size(args.fit)
        # Fit within bounds preserving aspect ratio
        ratio = min(fit_w / orig_w, fit_h / orig_h)
        new_w = max(1, round(orig_w * ratio))
        new_h = max(1, round(orig_h * ratio))

    else:
        # --width and/or --height
        if has_width and has_height:
            new_w = args.width
            new_h = args.height
        elif has_width:
            new_w = args.width
            new_h = max(1, round(orig_h * (args.width / orig_w)))
        else:
            new_h = args.height
            new_w = max(1, round(orig_w * (args.height / orig_h)))

        if new_w <= 0 or new_h <= 0:
            _err(f"Computed dimensions {new_w}x{new_h} are invalid. Check your --width/--height values.")

    result = img.resize((new_w, new_h), resample)
    _info(f"Resized: {orig_w}x{orig_h} -> {new_w}x{new_h}")

    result = _ensure_mode_for_output(result, out)
    save_params = _infer_save_params(out, args)
    _save_image(result, out, **save_params)


def cmd_crop(args: argparse.Namespace) -> None:
    """Crop image by box coordinates or aspect ratio."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    orig_w, orig_h = img.size

    has_box = args.box is not None
    has_aspect = args.aspect is not None

    if not has_box and not has_aspect:
        _err("Specify one of: --box x1,y1,x2,y2 or --aspect RATIO (e.g., 16:9).")
    if has_box and has_aspect:
        _err("Use only one crop mode: --box or --aspect, not both.")

    if has_box:
        # Parse box coordinates
        parts = args.box.split(",")
        if len(parts) != 4:
            _err(f"Invalid --box '{args.box}'. Expected x1,y1,x2,y2 (comma-separated integers).")
        try:
            x1, y1, x2, y2 = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        except ValueError:
            _err(f"Invalid --box '{args.box}'. All values must be integers.")

        if x1 >= x2 or y1 >= y2:
            _err(f"Invalid crop box: x1 must be < x2 and y1 must be < y2. Got ({x1},{y1},{x2},{y2}).")
        if x1 < 0 or y1 < 0:
            _err(f"Invalid crop box: coordinates must be non-negative. Got ({x1},{y1},{x2},{y2}).")
        if x2 > orig_w or y2 > orig_h:
            _err(
                f"Crop box ({x1},{y1},{x2},{y2}) exceeds image bounds ({orig_w}x{orig_h}). "
                f"Adjust coordinates or use resize-geometry pad to enlarge the canvas first."
            )

        result = img.crop((x1, y1, x2, y2))

    else:
        # Aspect ratio crop
        aspect_presets = {
            "1:1": (1, 1),
            "4:3": (4, 3),
            "3:4": (3, 4),
            "16:9": (16, 9),
            "9:16": (9, 16),
            "2:1": (2, 1),
            "1:2": (1, 2),
        }

        if args.aspect in aspect_presets:
            aw, ah = aspect_presets[args.aspect]
        else:
            # Try parsing custom W:H
            ratio_parts = args.aspect.split(":")
            if len(ratio_parts) != 2:
                _err(
                    f"Invalid aspect ratio '{args.aspect}'. "
                    f"Use preset (1:1, 4:3, 16:9, 2:1) or custom W:H format."
                )
            try:
                aw, ah = int(ratio_parts[0]), int(ratio_parts[1])
            except ValueError:
                _err(f"Invalid aspect ratio '{args.aspect}'. Both values must be integers.")
            if aw <= 0 or ah <= 0:
                _err(f"Invalid aspect ratio '{args.aspect}'. Both values must be positive.")

        # Compute crop box for the target aspect ratio
        target_ratio = aw / ah
        current_ratio = orig_w / orig_h

        if current_ratio > target_ratio:
            # Image is wider than target — crop width
            crop_h = orig_h
            crop_w = round(orig_h * target_ratio)
        else:
            # Image is taller than target — crop height
            crop_w = orig_w
            crop_h = round(orig_w / target_ratio)

        # Clamp to image bounds
        crop_w = min(crop_w, orig_w)
        crop_h = min(crop_h, orig_h)

        gravity = args.gravity or "center"
        x_off, y_off = _gravity_offset(crop_w, crop_h, orig_w, orig_h, gravity)
        result = img.crop((x_off, y_off, x_off + crop_w, y_off + crop_h))

    crop_w, crop_h = result.size
    _info(f"Cropped: {orig_w}x{orig_h} -> {crop_w}x{crop_h}")

    result = _ensure_mode_for_output(result, out)
    save_params = _infer_save_params(out, args)
    _save_image(result, out, **save_params)


def cmd_auto_crop(args: argparse.Namespace) -> None:
    """Remove uniform borders from image."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    orig_w, orig_h = img.size

    # Determine border color
    if args.color:
        bg_color = _parse_color(args.color)
    else:
        # Auto-detect from top-left pixel
        bg_color = img.getpixel((0, 0))
        if isinstance(bg_color, int):
            bg_color = (bg_color,)
        _info(f"Auto-detected border color from top-left pixel: {bg_color}")

    tolerance = args.tolerance

    # Create a solid background of the border color and diff against it
    bg = Image.new(img.mode, img.size, bg_color)
    diff = ImageChops.difference(img, bg)

    # Apply tolerance: if all channels of a pixel are below tolerance, treat as background
    if tolerance > 0:
        import numpy as np

        diff_arr = np.array(diff)
        if diff_arr.ndim == 2:
            # Grayscale
            mask_arr = (diff_arr > tolerance).astype("uint8") * 255
        else:
            # Multi-channel: pixel is foreground if ANY channel exceeds tolerance
            mask_arr = (diff_arr.max(axis=2) > tolerance).astype("uint8") * 255
        mask = Image.fromarray(mask_arr, mode="L")
    else:
        # Convert diff to grayscale for bbox detection
        if diff.mode != "L":
            mask = diff.convert("L")
        else:
            mask = diff
        # Any non-zero pixel is foreground
        mask = mask.point(lambda x: 255 if x > 0 else 0)

    bbox = mask.getbbox()
    if bbox is None:
        _info("Image is entirely the border color. No crop applied — saving as-is.")
        result = img
    else:
        result = img.crop(bbox)
        _info(f"Auto-cropped: {orig_w}x{orig_h} -> {result.size[0]}x{result.size[1]}")

    result = _ensure_mode_for_output(result, out)
    save_params = _infer_save_params(out, args)
    _save_image(result, out, **save_params)


def cmd_pad(args: argparse.Namespace) -> None:
    """Add padding / letterbox to target size."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    orig_w, orig_h = img.size
    target_w, target_h = _parse_size(args.size)
    bg_color = _parse_color(args.color)
    gravity = args.gravity or "center"

    if orig_w > target_w or orig_h > target_h:
        _err(
            f"Image ({orig_w}x{orig_h}) is larger than target ({target_w}x{target_h}). "
            f"Resize the image first with: uv run resize_geometry.py resize INPUT -o OUT --fit {target_w}x{target_h}"
        )

    # Extend color tuple to match image mode
    if img.mode == "RGBA" and len(bg_color) == 3:
        bg_color = bg_color + (255,)
    elif img.mode == "L" and len(bg_color) >= 3:
        # Convert RGB color to grayscale value
        bg_color = (round(0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]),)

    canvas = Image.new(img.mode, (target_w, target_h), bg_color)
    x_off, y_off = _gravity_offset(orig_w, orig_h, target_w, target_h, gravity)
    canvas.paste(img, (x_off, y_off))

    _info(f"Padded: {orig_w}x{orig_h} -> {target_w}x{target_h} (gravity: {gravity})")

    canvas = _ensure_mode_for_output(canvas, out)
    save_params = _infer_save_params(out, args)
    _save_image(canvas, out, **save_params)


def cmd_rotate(args: argparse.Namespace) -> None:
    """Rotate and/or flip image."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    has_angle = args.angle is not None
    has_flip = args.flip is not None

    if not has_angle and not has_flip:
        _err("Specify at least one of: --angle DEGREES or --flip h/v.")

    # Determine fill color
    if args.fill:
        fill_color = _parse_color(args.fill)
    else:
        if img.mode == "RGBA":
            fill_color = (0, 0, 0, 0)
        elif img.mode == "L":
            fill_color = 255
        else:
            fill_color = (255, 255, 255)

    result = img

    # Apply flip first (if specified)
    if has_flip:
        flip = args.flip.lower()
        if flip == "h":
            result = result.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            _info("Flipped horizontally.")
        elif flip == "v":
            result = result.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            _info("Flipped vertically.")
        else:
            _err(f"Invalid --flip value '{args.flip}'. Use 'h' (horizontal) or 'v' (vertical).")

    # Apply rotation (if specified)
    if has_angle:
        angle = args.angle
        # Special-case exact 90/180/270 for lossless transpose
        norm_angle = angle % 360
        if norm_angle == 90:
            result = result.transpose(Image.Transpose.ROTATE_90)
            _info("Rotated 90 degrees (lossless transpose).")
        elif norm_angle == 180:
            result = result.transpose(Image.Transpose.ROTATE_180)
            _info("Rotated 180 degrees (lossless transpose).")
        elif norm_angle == 270:
            result = result.transpose(Image.Transpose.ROTATE_270)
            _info("Rotated 270 degrees (lossless transpose).")
        elif norm_angle == 0:
            _info("Rotation angle is 0 — no rotation applied.")
        else:
            result = result.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=fill_color)
            _info(f"Rotated {angle} degrees (expand=True).")

    result = _ensure_mode_for_output(result, out)
    save_params = _infer_save_params(out, args)
    _save_image(result, out, **save_params)


def cmd_montage(args: argparse.Namespace) -> None:
    """Combine multiple images into a grid layout."""
    if len(args.inputs) < 2:
        _err("Montage requires at least 2 input images.")

    out = _validate_output(args.output)

    # Validate and load all inputs
    images: list[Image.Image] = []
    for p in args.inputs:
        inp = _validate_input(p)
        images.append(_open_image(inp))

    n = len(images)
    cols = args.cols or min(n, 4)
    if cols <= 0:
        _err(f"--cols must be positive, got {cols}.")
    rows = (n + cols - 1) // cols
    spacing = args.spacing
    bg_color = _parse_color(args.background)

    # Determine cell size: use the dimensions of the first image
    cell_w, cell_h = images[0].size

    # Resize all images to match cell size
    resized: list[Image.Image] = []
    for i, img in enumerate(images):
        if img.size != (cell_w, cell_h):
            img = img.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
            _info(f"Image {i} resized to {cell_w}x{cell_h} to match grid cell size.")
        resized.append(img)

    # Compute canvas size
    canvas_w = cols * cell_w + (cols - 1) * spacing
    canvas_h = rows * cell_h + (rows - 1) * spacing

    # Determine canvas mode (use RGBA if any input has alpha, else RGB)
    has_alpha = any(img.mode in ("RGBA", "LA", "PA") for img in resized)
    canvas_mode = "RGBA" if has_alpha else "RGB"

    # Extend bg_color for the canvas mode
    if canvas_mode == "RGBA" and len(bg_color) == 3:
        canvas_bg = bg_color + (255,)
    else:
        canvas_bg = bg_color[:3] if canvas_mode == "RGB" else bg_color

    canvas = Image.new(canvas_mode, (canvas_w, canvas_h), canvas_bg)

    for idx, img in enumerate(resized):
        row = idx // cols
        col = idx % cols
        x = col * (cell_w + spacing)
        y = row * (cell_h + spacing)
        # Convert to canvas mode if needed
        if img.mode != canvas_mode:
            img = img.convert(canvas_mode)
        canvas.paste(img, (x, y))

    _info(f"Montage: {n} images in {rows}x{cols} grid, cell {cell_w}x{cell_h}, canvas {canvas_w}x{canvas_h}")

    canvas = _ensure_mode_for_output(canvas, out)
    save_params = _infer_save_params(out, args)
    _save_image(canvas, out, **save_params)


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resize_geometry",
        description="Resize, crop, auto-crop, pad, rotate/flip, and montage grid layout.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- resize ---
    p_resize = sub.add_parser("resize", help="Resize image by dimensions, percentage, or fit-within")
    p_resize.add_argument("input", help="Input image path")
    p_resize.add_argument("-o", "--output", required=True, help="Output image path")
    p_resize.add_argument("--width", type=int, help="Target width (pixels)")
    p_resize.add_argument("--height", type=int, help="Target height (pixels)")
    p_resize.add_argument("--percent", type=float, help="Scale by percentage (e.g., 50 for half size)")
    p_resize.add_argument("--fit", help="Fit within bounds, e.g., 800x600")
    p_resize.add_argument(
        "--resample", default="lanczos", choices=["nearest", "bilinear", "bicubic", "lanczos"],
        help="Resampling method (default: lanczos)",
    )

    # --- crop ---
    p_crop = sub.add_parser("crop", help="Crop image by box or aspect ratio")
    p_crop.add_argument("input", help="Input image path")
    p_crop.add_argument("-o", "--output", required=True, help="Output image path")
    p_crop.add_argument("--box", help="Crop box as x1,y1,x2,y2 (comma-separated)")
    p_crop.add_argument("--aspect", help="Aspect ratio: 1:1, 4:3, 16:9, 2:1, or custom W:H")
    p_crop.add_argument(
        "--gravity", default="center",
        choices=["center", "top", "bottom", "left", "right", "top-left", "top-right", "bottom-left", "bottom-right"],
        help="Anchor point for aspect crop (default: center)",
    )

    # --- auto-crop ---
    p_autocrop = sub.add_parser("auto-crop", help="Remove uniform borders")
    p_autocrop.add_argument("input", help="Input image path")
    p_autocrop.add_argument("-o", "--output", required=True, help="Output image path")
    p_autocrop.add_argument("--color", help="Border color to remove (hex or named). Default: auto-detect from top-left pixel.")
    p_autocrop.add_argument("--tolerance", type=int, default=0, help="Color tolerance for border detection (default: 0)")

    # --- pad ---
    p_pad = sub.add_parser("pad", help="Add padding / letterbox to target size")
    p_pad.add_argument("input", help="Input image path")
    p_pad.add_argument("-o", "--output", required=True, help="Output image path")
    p_pad.add_argument("--size", required=True, help="Target canvas size as WxH (e.g., 800x600)")
    p_pad.add_argument("--color", default="white", help="Fill color (default: white)")
    p_pad.add_argument(
        "--gravity", default="center",
        choices=["center", "top", "bottom", "left", "right", "top-left", "top-right", "bottom-left", "bottom-right"],
        help="Image placement (default: center)",
    )

    # --- rotate ---
    p_rotate = sub.add_parser("rotate", help="Rotate and/or flip image")
    p_rotate.add_argument("input", help="Input image path")
    p_rotate.add_argument("-o", "--output", required=True, help="Output image path")
    p_rotate.add_argument("--angle", type=float, help="Rotation angle in degrees (counter-clockwise)")
    p_rotate.add_argument("--flip", choices=["h", "v"], help="Flip: h = horizontal, v = vertical")
    p_rotate.add_argument("--fill", help="Fill color for exposed corners (default: transparent for RGBA, white for RGB)")

    # --- montage ---
    p_montage = sub.add_parser("montage", help="Combine multiple images into a grid")
    p_montage.add_argument("inputs", nargs="+", help="Input image paths (at least 2)")
    p_montage.add_argument("-o", "--output", required=True, help="Output image path")
    p_montage.add_argument("--cols", type=int, help="Number of columns (default: min(n, 4))")
    p_montage.add_argument("--spacing", type=int, default=0, help="Spacing between cells in pixels (default: 0)")
    p_montage.add_argument("--background", default="white", help="Background/spacing color (default: white)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "resize": cmd_resize,
        "crop": cmd_crop,
        "auto-crop": cmd_auto_crop,
        "pad": cmd_pad,
        "rotate": cmd_rotate,
        "montage": cmd_montage,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
