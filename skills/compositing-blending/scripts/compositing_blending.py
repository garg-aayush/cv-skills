#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "opencv-python-headless", "numpy"]
# ///
"""compositing-blending: Alpha composite, blend, paste/overlay, watermark, pixel diff, and background removal."""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Supported extensions (lowercase, with leading dot)
# ---------------------------------------------------------------------------
_SUPPORTED_READ = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp", ".gif"}
_SUPPORTED_WRITE = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp", ".gif"}
_ALPHA_FORMATS = {".png", ".webp", ".tiff", ".tif", ".gif"}


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


def _to_cv(pil_img: Image.Image) -> np.ndarray:
    """Convert Pillow image (RGB/RGBA) to OpenCV ndarray (BGR/BGRA)."""
    arr = np.array(pil_img)
    if pil_img.mode == "RGBA":
        import cv2
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    elif pil_img.mode == "RGB":
        import cv2
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    elif pil_img.mode == "L":
        return arr
    else:
        # Convert to RGB first, then to BGR
        import cv2
        rgb = np.array(pil_img.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _from_cv(arr: np.ndarray) -> Image.Image:
    """Convert OpenCV ndarray (BGR/BGRA) to Pillow image (RGB/RGBA)."""
    import cv2
    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L")
    elif arr.shape[2] == 4:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA)
        return Image.fromarray(rgb, mode="RGBA")
    else:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb, mode="RGB")


def _validate_alpha_output(path: Path) -> None:
    """Ensure output format supports alpha channel."""
    ext = path.suffix.lower()
    if ext not in _ALPHA_FORMATS:
        _err(
            f"Output format '{ext}' does not support alpha/transparency. "
            f"Use PNG or WebP for RGBA output. "
            f"Or remove alpha first with: uv run format_io.py alpha INPUT -o intermediate.png --mode remove"
        )


def _infer_save_params(output_path: Path) -> dict:
    """Build format-specific save kwargs from output extension."""
    ext = output_path.suffix.lower()
    params: dict = {}

    if ext in (".jpg", ".jpeg"):
        params["format"] = "JPEG"
        params["quality"] = 85
    elif ext == ".png":
        params["format"] = "PNG"
    elif ext == ".webp":
        params["format"] = "WEBP"
        params["quality"] = 80
    elif ext in (".tiff", ".tif"):
        params["format"] = "TIFF"
    elif ext == ".bmp":
        params["format"] = "BMP"
    elif ext == ".gif":
        params["format"] = "GIF"

    return params


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_composite(args: argparse.Namespace) -> None:
    """Alpha composite, blend, or paste two images."""
    inp1 = _validate_input(args.input1)
    inp2 = _validate_input(args.input2)
    out = _validate_output(args.output)

    img1 = _open_image(inp1)
    img2 = _open_image(inp2)

    mode = args.mode

    if mode == "alpha":
        # Alpha composite: both must be RGBA
        if img1.mode != "RGBA":
            img1 = img1.convert("RGBA")
            _info("Converted base image to RGBA for alpha compositing.")
        if img2.mode != "RGBA":
            img2 = img2.convert("RGBA")
            _info("Converted overlay image to RGBA for alpha compositing.")

        # Overlay must match base size — resize overlay if needed
        if img1.size != img2.size:
            _err(
                f"Image size mismatch: base is {img1.size[0]}x{img1.size[1]}, "
                f"overlay is {img2.size[0]}x{img2.size[1]}. "
                f"Images must be the same size for alpha compositing. "
                f"Resize first with the resize-geometry skill."
            )

        result = Image.alpha_composite(img1, img2)

        # Check if output supports alpha
        out_ext = out.suffix.lower()
        if out_ext in (".jpg", ".jpeg", ".bmp"):
            _err(
                f"Output format '{out_ext}' does not support alpha. "
                f"Alpha composite produces RGBA output. Use PNG or WebP."
            )

        save_params = _infer_save_params(out)
        _save_image(result, out, **save_params)

    elif mode == "blend":
        # Weighted blend: images must be same size and mode
        ratio = args.ratio
        if ratio < 0.0 or ratio > 1.0:
            _err("--ratio must be between 0.0 and 1.0.")

        if img1.size != img2.size:
            _err(
                f"Image size mismatch: image1 is {img1.size[0]}x{img1.size[1]}, "
                f"image2 is {img2.size[0]}x{img2.size[1]}. "
                f"Images must be the same size for blending. "
                f"Resize first with the resize-geometry skill."
            )

        # Ensure same mode
        if img1.mode != img2.mode:
            # Convert both to RGB (or RGBA if either has alpha)
            if "A" in img1.mode or "A" in img2.mode:
                img1 = img1.convert("RGBA")
                img2 = img2.convert("RGBA")
                _info("Converted both images to RGBA for blending.")
            else:
                img1 = img1.convert("RGB")
                img2 = img2.convert("RGB")
                _info("Converted both images to RGB for blending.")

        result = Image.blend(img1, img2, ratio)
        save_params = _infer_save_params(out)

        # JPEG can't handle RGBA
        out_ext = out.suffix.lower()
        if out_ext in (".jpg", ".jpeg") and result.mode == "RGBA":
            _err(
                f"Blended result is RGBA but output format '{out_ext}' does not support alpha. "
                f"Use PNG or WebP, or ensure both inputs are RGB."
            )

        _save_image(result, out, **save_params)

    elif mode == "paste":
        # Paste overlay onto base at position
        pos_parts = args.position.split(",")
        if len(pos_parts) != 2:
            _err("--position must be two comma-separated integers: x,y (e.g., 0,0 or 100,50)")
        try:
            x, y = int(pos_parts[0]), int(pos_parts[1])
        except ValueError:
            _err("--position must be two comma-separated integers: x,y")

        base = img1.copy()

        # If overlay has alpha, use it as mask for transparency-aware pasting
        if img2.mode == "RGBA":
            mask = img2.split()[3]
            base.paste(img2, (x, y), mask=mask)
        else:
            base.paste(img2, (x, y))

        save_params = _infer_save_params(out)

        # Check alpha compatibility
        out_ext = out.suffix.lower()
        if out_ext in (".jpg", ".jpeg") and base.mode == "RGBA":
            _err(
                f"Base image is RGBA but output format '{out_ext}' does not support alpha. "
                f"Use PNG or WebP, or convert base to RGB first."
            )

        _save_image(base, out, **save_params)


def cmd_watermark(args: argparse.Namespace) -> None:
    """Add a text or image watermark."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    opacity = args.opacity
    if opacity < 0.0 or opacity > 1.0:
        _err("--opacity must be between 0.0 and 1.0.")

    if args.text:
        # Text watermark
        # Work in RGBA for transparency
        if img.mode != "RGBA":
            base = img.convert("RGBA")
        else:
            base = img.copy()

        # Create transparent overlay for text
        txt_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_layer)

        font_size = args.font_size
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()
                _info("Using default font (system fonts not found).")

        # Measure text
        bbox = draw.textbbox((0, 0), args.text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Determine position
        x, y = _resolve_position(args.position, base.size, (text_w, text_h))

        # Draw text with opacity
        alpha_val = int(255 * opacity)
        draw.text((x, y), args.text, fill=(255, 255, 255, alpha_val), font=font)

        result = Image.alpha_composite(base, txt_layer)

        # If original was RGB and output is JPEG, convert back
        out_ext = out.suffix.lower()
        if out_ext in (".jpg", ".jpeg"):
            result = result.convert("RGB")
        elif out_ext == ".bmp":
            result = result.convert("RGB")

        save_params = _infer_save_params(out)
        _save_image(result, out, **save_params)

    elif args.image:
        # Image watermark
        wm_path = _validate_input(args.image)
        wm = _open_image(wm_path)

        # Work in RGBA
        if img.mode != "RGBA":
            base = img.convert("RGBA")
        else:
            base = img.copy()

        if wm.mode != "RGBA":
            wm = wm.convert("RGBA")

        # Resize watermark if larger than base
        if wm.size[0] > base.size[0] or wm.size[1] > base.size[1]:
            # Fit within base dimensions
            wm.thumbnail(base.size, Image.LANCZOS)
            _info(f"Resized watermark to {wm.size[0]}x{wm.size[1]} to fit within base image.")

        # Apply opacity to watermark alpha channel
        wm_arr = np.array(wm)
        wm_arr[:, :, 3] = (wm_arr[:, :, 3].astype(float) * opacity).astype(np.uint8)
        wm = Image.fromarray(wm_arr, mode="RGBA")

        # Determine position
        x, y = _resolve_position(args.position, base.size, wm.size)

        # Composite watermark onto base
        wm_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        wm_layer.paste(wm, (x, y))
        result = Image.alpha_composite(base, wm_layer)

        # Convert if needed for output
        out_ext = out.suffix.lower()
        if out_ext in (".jpg", ".jpeg", ".bmp"):
            result = result.convert("RGB")

        save_params = _infer_save_params(out)
        _save_image(result, out, **save_params)


def _resolve_position(
    pos_str: str, base_size: tuple[int, int], overlay_size: tuple[int, int]
) -> tuple[int, int]:
    """Resolve position string to (x, y) coordinates.

    Accepts named positions (center, top-left, top-right, bottom-left, bottom-right)
    or explicit x,y coordinates.
    """
    bw, bh = base_size
    ow, oh = overlay_size
    padding = 10  # margin for named positions

    named = {
        "center": ((bw - ow) // 2, (bh - oh) // 2),
        "top-left": (padding, padding),
        "top-right": (bw - ow - padding, padding),
        "bottom-left": (padding, bh - oh - padding),
        "bottom-right": (bw - ow - padding, bh - oh - padding),
    }

    if pos_str in named:
        return named[pos_str]

    # Try parsing as x,y
    parts = pos_str.split(",")
    if len(parts) == 2:
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError:
            pass

    _err(
        f"Invalid position '{pos_str}'. "
        f"Use one of: center, top-left, top-right, bottom-left, bottom-right, or x,y coordinates."
    )


def cmd_diff(args: argparse.Namespace) -> None:
    """Compute pixel difference map between two images."""
    inp1 = _validate_input(args.input1)
    inp2 = _validate_input(args.input2)
    out = _validate_output(args.output)

    img1 = _open_image(inp1)
    img2 = _open_image(inp2)

    # Must be same size
    if img1.size != img2.size:
        _err(
            f"Image size mismatch: image1 is {img1.size[0]}x{img1.size[1]}, "
            f"image2 is {img2.size[0]}x{img2.size[1]}. "
            f"Images must be the same size for diff. "
            f"Resize first with the resize-geometry skill."
        )

    # Convert to same mode for comparison
    if img1.mode != img2.mode:
        img1 = img1.convert("RGB")
        img2 = img2.convert("RGB")
        _info("Converted both images to RGB for comparison.")
    elif img1.mode == "RGBA":
        # Compare RGB channels only (ignore alpha)
        img1 = img1.convert("RGB")
        img2 = img2.convert("RGB")
        _info("Converted RGBA to RGB for comparison (alpha ignored).")
    elif img1.mode not in ("RGB", "L"):
        img1 = img1.convert("RGB")
        img2 = img2.convert("RGB")

    arr1 = np.array(img1).astype(np.int16)
    arr2 = np.array(img2).astype(np.int16)

    diff = np.abs(arr1 - arr2)

    # Apply amplification
    amplify = args.amplify
    if amplify < 1:
        _err("--amplify must be >= 1.")
    if amplify > 1:
        diff = diff * amplify

    # Apply threshold
    threshold = args.threshold
    if threshold < 0:
        _err("--threshold must be >= 0.")
    if threshold > 0:
        diff[diff < threshold] = 0

    # Clip to 0-255
    diff = np.clip(diff, 0, 255).astype(np.uint8)

    result = Image.fromarray(diff)
    save_params = _infer_save_params(out)
    _save_image(result, out, **save_params)


def cmd_remove_bg(args: argparse.Namespace) -> None:
    """Remove background using GrabCut."""
    import cv2

    inp = _validate_input(args.input)
    out = _validate_output(args.output)

    # Output must support alpha
    _validate_alpha_output(out)

    img = _open_image(inp)

    # Parse rect
    rect_parts = args.rect.split(",")
    if len(rect_parts) != 4:
        _err("--rect must be four comma-separated integers: x,y,w,h (e.g., 10,10,200,300)")
    try:
        rx, ry, rw, rh = int(rect_parts[0]), int(rect_parts[1]), int(rect_parts[2]), int(rect_parts[3])
    except ValueError:
        _err("--rect must be four comma-separated integers: x,y,w,h")

    if rw <= 0 or rh <= 0:
        _err("--rect width and height must be positive.")
    if rx < 0 or ry < 0:
        _err("--rect x and y must be non-negative.")
    if rx + rw > img.size[0] or ry + rh > img.size[1]:
        _err(
            f"--rect ({rx},{ry},{rw},{rh}) exceeds image bounds ({img.size[0]}x{img.size[1]}). "
            f"Ensure x+w <= width and y+h <= height."
        )

    iterations = args.iterations
    if iterations < 1:
        _err("--iterations must be >= 1.")

    # Convert to BGR for OpenCV
    if img.mode != "RGB":
        img = img.convert("RGB")
    cv_img = _to_cv(img)

    # GrabCut
    mask = np.zeros(cv_img.shape[:2], np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    rect = (rx, ry, rw, rh)
    cv2.grabCut(cv_img, mask, rect, bgd_model, fgd_model, iterations, cv2.GC_INIT_WITH_RECT)

    # Create binary mask: definite foreground + probable foreground
    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # Convert back to Pillow and apply alpha
    result_pil = _from_cv(cv_img)
    if result_pil.mode != "RGBA":
        result_pil = result_pil.convert("RGBA")

    # Apply GrabCut mask as alpha channel
    alpha = Image.fromarray(fg_mask, mode="L")
    result_pil.putalpha(alpha)

    save_params = _infer_save_params(out)
    _save_image(result_pil, out, **save_params)
    _info(f"Background removed using GrabCut ({iterations} iterations, rect={rect}).")


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compositing_blending",
        description="Alpha composite, blend, paste/overlay, watermark, pixel diff, and background removal.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- composite ---
    p_composite = sub.add_parser("composite", help="Alpha composite, blend, or paste two images")
    p_composite.add_argument("input1", help="Base/first input image path")
    p_composite.add_argument("input2", help="Overlay/second input image path")
    p_composite.add_argument("-o", "--output", required=True, help="Output image path")
    p_composite.add_argument(
        "--mode", required=True, choices=["alpha", "blend", "paste"],
        help="Compositing mode: alpha (RGBA composite), blend (weighted mix), paste (overlay at position)"
    )
    p_composite.add_argument(
        "--ratio", type=float, default=0.5,
        help="Blend ratio for --mode blend (0.0 = all image1, 1.0 = all image2, default: 0.5)"
    )
    p_composite.add_argument(
        "--position", default="0,0",
        help="Paste position as x,y for --mode paste (default: 0,0)"
    )

    # --- watermark ---
    p_watermark = sub.add_parser("watermark", help="Add text or image watermark")
    p_watermark.add_argument("input", help="Input image path")
    p_watermark.add_argument("-o", "--output", required=True, help="Output image path")
    wm_group = p_watermark.add_mutually_exclusive_group(required=True)
    wm_group.add_argument("--text", help="Text watermark string")
    wm_group.add_argument("--image", help="Image watermark file path")
    p_watermark.add_argument(
        "--opacity", type=float, default=0.3,
        help="Watermark opacity (0.0-1.0, default: 0.3)"
    )
    p_watermark.add_argument(
        "--position", default="bottom-right",
        help="Position: center, top-left, top-right, bottom-left, bottom-right, or x,y (default: bottom-right)"
    )
    p_watermark.add_argument(
        "--font-size", type=int, default=24,
        help="Font size for text watermark (default: 24)"
    )

    # --- diff ---
    p_diff = sub.add_parser("diff", help="Pixel difference map between two images")
    p_diff.add_argument("input1", help="First input image path")
    p_diff.add_argument("input2", help="Second input image path")
    p_diff.add_argument("-o", "--output", required=True, help="Output difference image path")
    p_diff.add_argument(
        "--amplify", type=int, default=1,
        help="Amplify differences by factor N (default: 1)"
    )
    p_diff.add_argument(
        "--threshold", type=int, default=0,
        help="Set pixels with diff below threshold to 0 (default: 0)"
    )

    # --- remove-bg ---
    p_rmbg = sub.add_parser("remove-bg", help="Remove background via GrabCut")
    p_rmbg.add_argument("input", help="Input image path")
    p_rmbg.add_argument("-o", "--output", required=True, help="Output image path (must be PNG or WebP)")
    p_rmbg.add_argument(
        "--rect", required=True,
        help="Foreground bounding box as x,y,w,h (e.g., 10,10,200,300)"
    )
    p_rmbg.add_argument(
        "--iterations", type=int, default=5,
        help="GrabCut iterations (default: 5)"
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "composite": cmd_composite,
        "watermark": cmd_watermark,
        "diff": cmd_diff,
        "remove-bg": cmd_remove_bg,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
