#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "opencv-python-headless", "numpy"]
# ///
"""segment-morphology: Threshold, edge detection, morphology, contours, color segmentation, and GrabCut."""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

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
    """Open image with Pillow."""
    try:
        img = Image.open(path)
        img.load()
        return img
    except Exception as e:
        _err(f"Failed to open image '{path}': {e}")


def _save_image(img: Image.Image, path: Path, **kwargs) -> None:
    """Save image with Pillow."""
    try:
        img.save(str(path), **kwargs)
        _info(f"Saved: {path} ({os.path.getsize(path)} bytes)")
    except Exception as e:
        _err(f"Failed to save image '{path}': {e}")


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


def _to_cv(pil_img: Image.Image) -> np.ndarray:
    """Convert PIL Image (RGB/RGBA/L) to OpenCV numpy array (BGR/BGRA/grayscale)."""
    if pil_img.mode == "L":
        return np.array(pil_img)
    elif pil_img.mode == "RGBA":
        arr = np.array(pil_img)
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    else:
        # Convert to RGB first if not already
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        arr = np.array(pil_img)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _from_cv(arr: np.ndarray) -> Image.Image:
    """Convert OpenCV numpy array (BGR/BGRA/grayscale) to PIL Image (RGB/RGBA/L)."""
    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L")
    elif arr.shape[2] == 4:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA)
        return Image.fromarray(rgb, mode="RGBA")
    else:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb, mode="RGB")


def _parse_hex_color(color_str: str) -> tuple[int, int, int]:
    """Parse hex color string (#RRGGBB) to (R, G, B) tuple."""
    color_str = color_str.strip().lstrip("#")
    if len(color_str) != 6:
        _err(f"Invalid hex color '#{color_str}'. Use format #RRGGBB (e.g., #00FF00).")
    try:
        r = int(color_str[0:2], 16)
        g = int(color_str[2:4], 16)
        b = int(color_str[4:6], 16)
        return (r, g, b)
    except ValueError:
        _err(f"Invalid hex color '#{color_str}'. Use format #RRGGBB (e.g., #00FF00).")


def _parse_triple(value: str, label: str) -> tuple[int, int, int]:
    """Parse comma-separated triple 'a,b,c' into (int, int, int)."""
    parts = value.split(",")
    if len(parts) != 3:
        _err(f"Invalid {label} '{value}'. Expected 3 comma-separated integers (e.g., 35,100,100).")
    try:
        return tuple(int(p.strip()) for p in parts)  # type: ignore[return-value]
    except ValueError:
        _err(f"Invalid {label} '{value}'. All values must be integers.")


def _parse_rect(value: str) -> tuple[int, int, int, int]:
    """Parse comma-separated rect 'x,y,w,h' into (int, int, int, int)."""
    parts = value.split(",")
    if len(parts) != 4:
        _err(f"Invalid rect '{value}'. Expected 4 comma-separated integers: x,y,w,h.")
    try:
        return tuple(int(p.strip()) for p in parts)  # type: ignore[return-value]
    except ValueError:
        _err(f"Invalid rect '{value}'. All values must be integers.")


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_threshold(args: argparse.Namespace) -> None:
    """Apply binary thresholding."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    pil_img = _open_image(inp)

    # Convert to grayscale via OpenCV
    cv_img = _to_cv(pil_img)
    if cv_img.ndim == 3:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv_img

    method = args.method

    if method == "fixed":
        _, result = cv2.threshold(gray, args.value, 255, cv2.THRESH_BINARY)
    elif method == "otsu":
        _, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif method == "adaptive":
        block_size = args.block_size
        if block_size % 2 == 0:
            _err(f"--block-size must be odd, got {block_size}. Try {block_size + 1}.")
        if block_size < 3:
            _err(f"--block-size must be >= 3, got {block_size}.")
        result = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, args.c
        )
    else:
        _err(f"Unknown threshold method '{method}'. Use: fixed, otsu, adaptive.")

    # Save as grayscale
    out_img = Image.fromarray(result, mode="L")
    save_params = _infer_save_params(out)

    # JPEG doesn't support L mode well on all systems — convert if needed
    if out.suffix.lower() in (".jpg", ".jpeg"):
        save_params["format"] = "JPEG"

    _save_image(out_img, out, **save_params)
    _info(f"Threshold applied (method: {method}).")


def cmd_canny(args: argparse.Namespace) -> None:
    """Canny edge detection."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    pil_img = _open_image(inp)

    cv_img = _to_cv(pil_img)
    if cv_img.ndim == 3:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv_img

    edges = cv2.Canny(gray, args.low, args.high)

    out_img = Image.fromarray(edges, mode="L")
    save_params = _infer_save_params(out)
    _save_image(out_img, out, **save_params)
    _info(f"Canny edge detection applied (low={args.low}, high={args.high}).")


def cmd_gradient(args: argparse.Namespace) -> None:
    """Sobel or Laplacian gradient edge detection."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    pil_img = _open_image(inp)

    cv_img = _to_cv(pil_img)
    if cv_img.ndim == 3:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv_img

    method = args.method
    ksize = args.ksize

    if ksize % 2 == 0:
        _err(f"--ksize must be odd, got {ksize}. Try {ksize + 1}.")

    if method == "sobel":
        direction = args.direction
        if direction == "x":
            grad = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
        elif direction == "y":
            grad = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)
        elif direction == "both":
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)
            grad = np.sqrt(grad_x ** 2 + grad_y ** 2)
        else:
            _err(f"Unknown direction '{direction}'. Use: x, y, both.")

        # Normalize to 0-255
        result = np.abs(grad)
        result = (result / result.max() * 255).astype(np.uint8) if result.max() > 0 else result.astype(np.uint8)

    elif method == "laplacian":
        grad = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
        result = np.abs(grad)
        result = (result / result.max() * 255).astype(np.uint8) if result.max() > 0 else result.astype(np.uint8)

    else:
        _err(f"Unknown gradient method '{method}'. Use: sobel, laplacian.")

    out_img = Image.fromarray(result, mode="L")
    save_params = _infer_save_params(out)
    _save_image(out_img, out, **save_params)
    _info(f"Gradient edge detection applied (method: {method}).")


def cmd_morphology(args: argparse.Namespace) -> None:
    """Apply morphological operations."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    pil_img = _open_image(inp)

    cv_img = _to_cv(pil_img)

    # Build structuring element
    shape_map = {
        "rect": cv2.MORPH_RECT,
        "ellipse": cv2.MORPH_ELLIPSE,
        "cross": cv2.MORPH_CROSS,
    }
    shape = shape_map.get(args.shape)
    if shape is None:
        _err(f"Unknown kernel shape '{args.shape}'. Use: rect, ellipse, cross.")

    kernel = cv2.getStructuringElement(shape, (args.kernel, args.kernel))

    # Map operation name to OpenCV constant
    op_map = {
        "erode": cv2.MORPH_ERODE,
        "dilate": cv2.MORPH_DILATE,
        "open": cv2.MORPH_OPEN,
        "close": cv2.MORPH_CLOSE,
        "gradient": cv2.MORPH_GRADIENT,
    }
    op = op_map.get(args.op)
    if op is None:
        _err(f"Unknown morphology operation '{args.op}'. Use: erode, dilate, open, close, gradient.")

    result = cv2.morphologyEx(cv_img, op, kernel, iterations=args.iterations)

    out_img = _from_cv(result)
    save_params = _infer_save_params(out)

    # Handle mode compatibility for JPEG
    if out.suffix.lower() in (".jpg", ".jpeg") and out_img.mode == "RGBA":
        _err(
            "Cannot save RGBA image as JPEG (JPEG does not support transparency). "
            "Use PNG or remove alpha first with format-io: "
            "uv run format_io.py alpha INPUT -o intermediate.png --mode remove"
        )

    _save_image(out_img, out, **save_params)
    _info(f"Morphology applied (op: {args.op}, kernel: {args.kernel}, shape: {args.shape}, iterations: {args.iterations}).")


def cmd_contours(args: argparse.Namespace) -> None:
    """Find and draw contours on the image."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    pil_img = _open_image(inp)

    cv_img = _to_cv(pil_img)

    # Convert to grayscale for thresholding
    if cv_img.ndim == 3:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = cv_img

    # Otsu threshold for contour detection
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter by area
    filtered = []
    for c in contours:
        area = cv2.contourArea(c)
        if args.min_area is not None and area < args.min_area:
            continue
        if args.max_area is not None and area > args.max_area:
            continue
        filtered.append(c)

    # Parse color
    r, g, b = _parse_hex_color(args.color)
    # OpenCV uses BGR
    draw_color = (b, g, r)

    # Draw on original color image
    if cv_img.ndim == 2:
        # Convert grayscale to BGR for colored contour drawing
        draw_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2BGR)
    else:
        draw_img = cv_img.copy()

    cv2.drawContours(draw_img, filtered, -1, draw_color, args.thickness)

    out_img = _from_cv(draw_img)
    save_params = _infer_save_params(out)

    if out.suffix.lower() in (".jpg", ".jpeg") and out_img.mode == "RGBA":
        _err(
            "Cannot save RGBA image as JPEG. Use PNG output or remove alpha first."
        )

    _save_image(out_img, out, **save_params)
    _info(f"Drew {len(filtered)} contours (of {len(contours)} found).")


def cmd_color_segment(args: argparse.Namespace) -> None:
    """Segment image by color range in HSV or LAB space."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    pil_img = _open_image(inp)

    cv_img = _to_cv(pil_img)
    if cv_img.ndim == 2:
        _err("Color segmentation requires a color image, got grayscale. Convert to RGB first.")

    lower = np.array(_parse_triple(args.lower, "--lower"), dtype=np.uint8)
    upper = np.array(_parse_triple(args.upper, "--upper"), dtype=np.uint8)

    space = args.space
    if space == "hsv":
        converted = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
    elif space == "lab":
        converted = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
    else:
        _err(f"Unknown color space '{space}'. Use: hsv, lab.")

    mask = cv2.inRange(converted, lower, upper)

    # Save binary mask as grayscale
    out_img = Image.fromarray(mask, mode="L")
    save_params = _infer_save_params(out)
    _save_image(out_img, out, **save_params)
    _info(f"Color segmentation applied (space: {space}).")


def cmd_grabcut(args: argparse.Namespace) -> None:
    """Foreground extraction using GrabCut."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    pil_img = _open_image(inp)

    cv_img = _to_cv(pil_img)
    if cv_img.ndim == 2:
        _err("GrabCut requires a color image, got grayscale. Convert to RGB first.")

    x, y, w, h = _parse_rect(args.rect)

    # Validate rect against image dimensions
    img_h, img_w = cv_img.shape[:2]
    if x < 0 or y < 0 or w <= 0 or h <= 0:
        _err(f"Invalid rect ({x},{y},{w},{h}). All values must be non-negative and w,h must be positive.")
    if x + w > img_w or y + h > img_h:
        _err(
            f"Rect ({x},{y},{w},{h}) exceeds image bounds ({img_w}x{img_h}). "
            f"Ensure x+w <= {img_w} and y+h <= {img_h}."
        )

    rect = (x, y, w, h)
    mask = np.zeros(cv_img.shape[:2], dtype=np.uint8)
    bgd_model = np.zeros((1, 65), dtype=np.float64)
    fgd_model = np.zeros((1, 65), dtype=np.float64)

    cv2.grabCut(cv_img, mask, rect, bgd_model, fgd_model, args.iterations, cv2.GC_INIT_WITH_RECT)

    # Create binary mask: foreground = GC_FGD (1) or GC_PR_FGD (3)
    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # Apply mask as alpha channel for RGBA output
    # Convert BGR to RGB
    rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    rgba = np.dstack([rgb, fg_mask])

    out_img = Image.fromarray(rgba, mode="RGBA")

    # GrabCut outputs RGBA — force PNG if output is JPEG
    out_ext = out.suffix.lower()
    if out_ext in (".jpg", ".jpeg"):
        _err(
            "GrabCut produces RGBA output (transparency for background). "
            "Use .png output instead of .jpg to preserve the alpha channel."
        )

    save_params = _infer_save_params(out)
    _save_image(out_img, out, **save_params)
    _info(f"GrabCut foreground extraction applied (rect: {rect}, iterations: {args.iterations}).")


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="segment_morphology",
        description="Threshold, edge detection, morphology, contours, color segmentation, and GrabCut.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- threshold ---
    p_thresh = sub.add_parser("threshold", help="Binary thresholding")
    p_thresh.add_argument("input", help="Input image path")
    p_thresh.add_argument("-o", "--output", required=True, help="Output image path")
    p_thresh.add_argument(
        "--method", required=True, choices=["fixed", "otsu", "adaptive"],
        help="Threshold method: fixed (manual value), otsu (auto), adaptive (local block-based)"
    )
    p_thresh.add_argument("--value", type=int, default=128, help="Threshold value for fixed method (default: 128)")
    p_thresh.add_argument("--block-size", type=int, default=11, help="Block size for adaptive method (must be odd, default: 11)")
    p_thresh.add_argument("--c", type=int, default=2, help="Constant subtracted from mean for adaptive method (default: 2)")

    # --- canny ---
    p_canny = sub.add_parser("canny", help="Canny edge detection")
    p_canny.add_argument("input", help="Input image path")
    p_canny.add_argument("-o", "--output", required=True, help="Output image path")
    p_canny.add_argument("--low", type=int, default=100, help="Lower hysteresis threshold (default: 100)")
    p_canny.add_argument("--high", type=int, default=200, help="Upper hysteresis threshold (default: 200)")

    # --- gradient ---
    p_grad = sub.add_parser("gradient", help="Sobel or Laplacian gradient edge detection")
    p_grad.add_argument("input", help="Input image path")
    p_grad.add_argument("-o", "--output", required=True, help="Output image path")
    p_grad.add_argument(
        "--method", required=True, choices=["sobel", "laplacian"],
        help="Gradient method: sobel (directional) or laplacian (second-derivative)"
    )
    p_grad.add_argument("--direction", default="both", choices=["x", "y", "both"],
                         help="Sobel direction (default: both). Ignored for laplacian.")
    p_grad.add_argument("--ksize", type=int, default=3, help="Kernel size (must be odd, default: 3)")

    # --- morphology ---
    p_morph = sub.add_parser("morphology", help="Morphological operations")
    p_morph.add_argument("input", help="Input image path")
    p_morph.add_argument("-o", "--output", required=True, help="Output image path")
    p_morph.add_argument(
        "--op", required=True, choices=["erode", "dilate", "open", "close", "gradient"],
        help="Morphological operation"
    )
    p_morph.add_argument("--kernel", type=int, default=5, help="Kernel size (default: 5)")
    p_morph.add_argument("--shape", default="rect", choices=["rect", "ellipse", "cross"],
                          help="Structuring element shape (default: rect)")
    p_morph.add_argument("--iterations", type=int, default=1, help="Number of iterations (default: 1)")

    # --- contours ---
    p_cont = sub.add_parser("contours", help="Find and draw contours")
    p_cont.add_argument("input", help="Input image path")
    p_cont.add_argument("-o", "--output", required=True, help="Output image path")
    p_cont.add_argument("--min-area", type=float, default=None, help="Minimum contour area (filter small contours)")
    p_cont.add_argument("--max-area", type=float, default=None, help="Maximum contour area (filter large contours)")
    p_cont.add_argument("--color", default="#00FF00", help="Contour color as hex (default: #00FF00 green)")
    p_cont.add_argument("--thickness", type=int, default=2, help="Contour line thickness (default: 2)")

    # --- color-segment ---
    p_cseg = sub.add_parser("color-segment", help="Color-based segmentation via HSV/LAB range")
    p_cseg.add_argument("input", help="Input image path")
    p_cseg.add_argument("-o", "--output", required=True, help="Output image path")
    p_cseg.add_argument("--space", required=True, choices=["hsv", "lab"],
                         help="Color space for range check")
    p_cseg.add_argument("--lower", required=True,
                         help="Lower bound as comma-separated triple (e.g., 35,100,100)")
    p_cseg.add_argument("--upper", required=True,
                         help="Upper bound as comma-separated triple (e.g., 85,255,255)")

    # --- grabcut ---
    p_grab = sub.add_parser("grabcut", help="Foreground extraction with GrabCut")
    p_grab.add_argument("input", help="Input image path")
    p_grab.add_argument("-o", "--output", required=True, help="Output image path")
    p_grab.add_argument("--rect", required=True,
                         help="Bounding box as x,y,w,h (comma-separated)")
    p_grab.add_argument("--iterations", type=int, default=5,
                         help="Number of GrabCut iterations (default: 5)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "threshold": cmd_threshold,
        "canny": cmd_canny,
        "gradient": cmd_gradient,
        "morphology": cmd_morphology,
        "contours": cmd_contours,
        "color-segment": cmd_color_segment,
        "grabcut": cmd_grabcut,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
