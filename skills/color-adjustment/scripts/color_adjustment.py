#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "opencv-python-headless", "numpy"]
# ///
"""color-adjustment: Tone, saturation, grayscale, invert, color space, channel ops, histograms, equalization, auto-levels."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageDraw, ImageOps

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
        # Handle JPEG mode incompatibilities
        ext = path.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            if img.mode == "RGBA":
                _err(
                    "Cannot save RGBA image as JPEG (JPEG does not support transparency). "
                    "Remove alpha first with format-io: uv run format_io.py alpha INPUT -o intermediate.png --mode remove"
                )
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            kwargs.setdefault("quality", 85)
        img.save(str(path), **kwargs)
        _info(f"Saved: {path} ({os.path.getsize(path)} bytes)")
    except Exception as e:
        _err(f"Failed to save image '{path}': {e}")


def _to_cv(pil_img: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV numpy array (RGB -> BGR)."""
    if pil_img.mode == "RGBA":
        arr = np.array(pil_img)
        # RGBA -> BGRA
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    elif pil_img.mode == "L":
        return np.array(pil_img)
    else:
        # Ensure RGB
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        arr = np.array(pil_img)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _from_cv(arr: np.ndarray) -> Image.Image:
    """Convert OpenCV numpy array (BGR) back to PIL Image (RGB)."""
    if arr.ndim == 2:
        # Grayscale
        return Image.fromarray(arr, mode="L")
    channels = arr.shape[2] if arr.ndim == 3 else 1
    if channels == 4:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA)
        return Image.fromarray(rgb, mode="RGBA")
    else:
        rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb, mode="RGB")


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_tone(args: argparse.Namespace) -> None:
    """Adjust brightness, contrast, and/or gamma."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    brightness = args.brightness
    contrast = args.contrast
    gamma = args.gamma

    if brightness == 1.0 and contrast == 1.0 and gamma == 1.0:
        _info("All tone parameters are at default (1.0). Saving as-is.")
        _save_image(img, out)
        return

    # Brightness
    if brightness != 1.0:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)

    # Contrast
    if contrast != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)

    # Gamma
    if gamma != 1.0:
        # Work in numpy for gamma correction
        arr = np.array(img).astype(np.float64)
        arr = np.clip(((arr / 255.0) ** (1.0 / gamma)) * 255.0, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr, mode=img.mode)

    _save_image(img, out)


def cmd_saturation(args: argparse.Namespace) -> None:
    """Adjust color saturation."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    factor = args.factor
    if factor < 0:
        _err("--factor must be >= 0. Use 0.0 for grayscale, 1.0 for unchanged, >1 for more saturation.")

    enhancer = ImageEnhance.Color(img)
    result = enhancer.enhance(factor)
    _save_image(result, out)


def cmd_grayscale(args: argparse.Namespace) -> None:
    """Convert image to grayscale."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    method = args.method

    # Ensure RGB input
    if img.mode == "L":
        _info("Image is already grayscale. Saving as-is.")
        _save_image(img, out)
        return

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    has_alpha = img.mode == "RGBA"
    alpha = None
    if has_alpha:
        alpha = img.split()[3]
        img = img.convert("RGB")

    arr = np.array(img).astype(np.float64)

    if method == "bt601":
        weights = np.array([0.299, 0.587, 0.114])
    else:  # bt709
        weights = np.array([0.2126, 0.7152, 0.0722])

    gray = np.dot(arr[..., :3], weights)
    gray = np.clip(gray, 0, 255).astype(np.uint8)
    result = Image.fromarray(gray, mode="L")

    if has_alpha and alpha is not None:
        result = result.convert("LA")
        result.putalpha(alpha)

    _save_image(result, out)


def cmd_invert(args: argparse.Namespace) -> None:
    """Invert (negate) image colors."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    # Handle alpha channel: invert only color channels, preserve alpha
    if img.mode == "RGBA":
        r, g, b, a = img.split()
        rgb = Image.merge("RGB", (r, g, b))
        rgb_inv = ImageOps.invert(rgb)
        ri, gi, bi = rgb_inv.split()
        result = Image.merge("RGBA", (ri, gi, bi, a))
    elif img.mode == "LA":
        l_ch, a = img.split()
        l_inv = ImageOps.invert(l_ch)
        result = Image.merge("LA", (l_inv, a))
    elif img.mode in ("RGB", "L"):
        result = ImageOps.invert(img)
    else:
        # Convert to RGB, invert, then keep
        converted = img.convert("RGB")
        result = ImageOps.invert(converted)

    _save_image(result, out)


def cmd_colorspace(args: argparse.Namespace) -> None:
    """Convert image to a different color space."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    target = args.to

    if img.mode == "L":
        _err("Cannot convert grayscale image to a multi-channel color space. Convert to RGB first.")

    # Ensure RGB for conversion
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    has_alpha = img.mode == "RGBA"
    alpha = None
    if has_alpha:
        alpha = img.split()[3]
        img = img.convert("RGB")

    cv_img = _to_cv(img)

    color_codes = {
        "hsv": cv2.COLOR_BGR2HSV,
        "lab": cv2.COLOR_BGR2LAB,
        "ycbcr": cv2.COLOR_BGR2YCrCb,
        "bgr": None,  # Already BGR in OpenCV
    }

    if target not in color_codes:
        _err(f"Unsupported target color space '{target}'. Supported: {', '.join(sorted(color_codes.keys()))}")

    if target == "bgr":
        # OpenCV image is already BGR; save it directly as-is (BGR channel order)
        converted = cv_img
    else:
        converted = cv2.cvtColor(cv_img, color_codes[target])

    # Save the converted result — note: these are raw channel values, not displayable as RGB
    # We save via PIL, treating the 3 channels as-is
    result = Image.fromarray(converted)

    _info(f"Converted to {target.upper()} color space. Note: channels represent {target.upper()} values, not RGB.")
    _save_image(result, out)


def cmd_channel(args: argparse.Namespace) -> None:
    """Split or merge color channels."""
    inp = _validate_input(args.input)
    img = _open_image(inp)

    mode = args.mode

    if mode == "split":
        out = _validate_output(args.output)
        # Ensure RGB
        if img.mode == "L":
            _err("Cannot split channels of a grayscale image — it has only one channel.")
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        channels = img.split()
        stem = out.stem
        suffix = out.suffix
        parent = out.parent

        for i, ch in enumerate(channels):
            ch_path = parent / f"{stem}_{i}{suffix}"
            _save_image(ch, ch_path)

        _info(f"Split {len(channels)} channels from {inp}")

    elif mode == "merge":
        out = _validate_output(args.output)
        channel_idx = args.channel
        replace_path = args.replace

        if channel_idx is None or replace_path is None:
            _err("--channel N and --replace FILE are required for merge mode.")

        replace_file = _validate_input(replace_path)
        replace_img = _open_image(replace_file)

        # Ensure input is multi-channel
        if img.mode == "L":
            _err("Cannot merge channels into a grayscale image. Convert to RGB first.")
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        channels = list(img.split())
        n_channels = len(channels)

        if channel_idx < 0 or channel_idx >= n_channels:
            _err(f"Channel index {channel_idx} out of range. Image has {n_channels} channels (0-{n_channels - 1}).")

        # Ensure replacement is grayscale and same size
        if replace_img.mode != "L":
            replace_img = replace_img.convert("L")

        if replace_img.size != img.size:
            _err(
                f"Replacement image size {replace_img.size} doesn't match input size {img.size}. "
                "Resize the replacement first with resize-geometry."
            )

        channels[channel_idx] = replace_img
        result = Image.merge(img.mode, tuple(channels))
        _save_image(result, out)
        _info(f"Replaced channel {channel_idx} with {replace_path}")


def cmd_histogram(args: argparse.Namespace) -> None:
    """Compute and save histogram as an image."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    cv_img = _to_cv(img)

    # Determine mode
    is_gray = img.mode == "L" or (img.mode in ("LA",) and True)
    if args.gray:
        draw_color = False
    elif args.color:
        draw_color = True
    else:
        # Auto-detect
        draw_color = img.mode not in ("L", "LA")

    # Histogram plot dimensions
    hist_w = 512
    hist_h = 400
    margin = 40
    plot_w = hist_w - 2 * margin
    plot_h = hist_h - 2 * margin

    # Create white background
    hist_img = Image.new("RGB", (hist_w, hist_h), (255, 255, 255))
    draw = ImageDraw.Draw(hist_img)

    if draw_color and cv_img.ndim == 3:
        # Per-channel histograms (BGR in OpenCV)
        colors_bgr = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # BGR channel colors
        colors_rgb = [(0, 0, 255), (0, 128, 0), (255, 0, 0)]   # RGB display colors (B=blue, G=green, R=red)

        max_val = 0
        hists = []
        for i in range(3):
            hist = cv2.calcHist([cv_img], [i], None, [256], [0, 256])
            hists.append(hist)
            max_val = max(max_val, hist.max())

        for i, hist in enumerate(hists):
            color = colors_rgb[i]
            for x in range(256):
                h = int((hist[x][0] / max_val) * plot_h) if max_val > 0 else 0
                px = margin + int(x * plot_w / 256)
                draw.line(
                    [(px, margin + plot_h - h), (px, margin + plot_h)],
                    fill=color,
                    width=1,
                )
    else:
        # Grayscale histogram
        if cv_img.ndim == 3:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv_img

        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        max_val = hist.max()

        for x in range(256):
            h = int((hist[x][0] / max_val) * plot_h) if max_val > 0 else 0
            px = margin + int(x * plot_w / 256)
            draw.line(
                [(px, margin + plot_h - h), (px, margin + plot_h)],
                fill=(64, 64, 64),
                width=2,
            )

    # Draw axes
    draw.line([(margin, margin), (margin, margin + plot_h)], fill=(0, 0, 0), width=2)
    draw.line([(margin, margin + plot_h), (margin + plot_w, margin + plot_h)], fill=(0, 0, 0), width=2)

    # Axis labels
    draw.text((margin, margin + plot_h + 5), "0", fill=(0, 0, 0))
    draw.text((margin + plot_w - 20, margin + plot_h + 5), "255", fill=(0, 0, 0))

    _save_image(hist_img, out)


def cmd_equalize(args: argparse.Namespace) -> None:
    """Histogram equalization (global or CLAHE)."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    method = args.method

    has_alpha = img.mode == "RGBA"
    alpha = None
    if has_alpha:
        alpha = img.split()[3]

    if img.mode in ("L", "LA"):
        # Grayscale equalization
        if img.mode == "LA":
            gray = np.array(img.split()[0])
        else:
            gray = np.array(img)

        if method == "clahe":
            clahe = cv2.createCLAHE(
                clipLimit=args.clip_limit,
                tileGridSize=(args.grid_size, args.grid_size),
            )
            equalized = clahe.apply(gray)
        else:
            equalized = cv2.equalizeHist(gray)

        result = Image.fromarray(equalized, mode="L")
        if img.mode == "LA" and alpha is not None:
            # Retrieve alpha from original LA image
            la_alpha = img.split()[1]
            result = result.convert("LA")
            result.putalpha(la_alpha)

    else:
        # Color equalization — work in LAB space, equalize L channel only
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        if has_alpha:
            rgb_img = img.convert("RGB")
        else:
            rgb_img = img

        cv_img = _to_cv(rgb_img)
        lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)

        if method == "clahe":
            clahe = cv2.createCLAHE(
                clipLimit=args.clip_limit,
                tileGridSize=(args.grid_size, args.grid_size),
            )
            l_eq = clahe.apply(l_ch)
        else:
            l_eq = cv2.equalizeHist(l_ch)

        lab_eq = cv2.merge([l_eq, a_ch, b_ch])
        bgr_eq = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)
        result = _from_cv(bgr_eq)

        if has_alpha and alpha is not None:
            result = result.convert("RGBA")
            result.putalpha(alpha)

    _save_image(result, out)


def cmd_auto_levels(args: argparse.Namespace) -> None:
    """Per-channel percentile clipping + linear stretch."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    clip_percent = args.clip_percent
    if clip_percent < 0 or clip_percent >= 50:
        _err("--clip-percent must be >= 0 and < 50.")

    has_alpha = img.mode == "RGBA"
    alpha = None
    if has_alpha:
        alpha = img.split()[3]
        img = img.convert("RGB")

    if img.mode == "LA":
        la_alpha = img.split()[1]
        img_l = img.split()[0]
        arr = np.array(img_l).astype(np.float64)
        lo = np.percentile(arr, clip_percent)
        hi = np.percentile(arr, 100 - clip_percent)
        if hi > lo:
            arr = np.clip((arr - lo) / (hi - lo) * 255.0, 0, 255)
        stretched = arr.astype(np.uint8)
        result = Image.fromarray(stretched, mode="L")
        result = result.convert("LA")
        result.putalpha(la_alpha)
        _save_image(result, out)
        return

    if img.mode == "L":
        arr = np.array(img).astype(np.float64)
        lo = np.percentile(arr, clip_percent)
        hi = np.percentile(arr, 100 - clip_percent)
        if hi > lo:
            arr = np.clip((arr - lo) / (hi - lo) * 255.0, 0, 255)
        stretched = arr.astype(np.uint8)
        result = Image.fromarray(stretched, mode="L")
        _save_image(result, out)
        return

    if img.mode not in ("RGB",):
        img = img.convert("RGB")

    arr = np.array(img).astype(np.float64)

    for c in range(arr.shape[2]):
        channel = arr[:, :, c]
        lo = np.percentile(channel, clip_percent)
        hi = np.percentile(channel, 100 - clip_percent)
        if hi > lo:
            arr[:, :, c] = np.clip((channel - lo) / (hi - lo) * 255.0, 0, 255)

    stretched = arr.astype(np.uint8)
    result = Image.fromarray(stretched, mode="RGB")

    if has_alpha and alpha is not None:
        result = result.convert("RGBA")
        result.putalpha(alpha)

    _save_image(result, out)


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="color_adjustment",
        description="Color adjustment: tone, saturation, grayscale, invert, color spaces, channels, histograms, equalization, auto-levels.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- tone ---
    p_tone = sub.add_parser("tone", help="Adjust brightness, contrast, and/or gamma")
    p_tone.add_argument("input", help="Input image path")
    p_tone.add_argument("-o", "--output", required=True, help="Output image path")
    p_tone.add_argument("--brightness", type=float, default=1.0, help="Brightness factor (default: 1.0, >1 brighter)")
    p_tone.add_argument("--contrast", type=float, default=1.0, help="Contrast factor (default: 1.0, >1 more contrast)")
    p_tone.add_argument("--gamma", type=float, default=1.0, help="Gamma correction (default: 1.0, <1 brighter, >1 darker)")

    # --- saturation ---
    p_sat = sub.add_parser("saturation", help="Adjust color saturation")
    p_sat.add_argument("input", help="Input image path")
    p_sat.add_argument("-o", "--output", required=True, help="Output image path")
    p_sat.add_argument("--factor", type=float, required=True, help="Saturation factor (0.0=grayscale, 1.0=unchanged, >1=more)")

    # --- grayscale ---
    p_gray = sub.add_parser("grayscale", help="Convert to grayscale")
    p_gray.add_argument("input", help="Input image path")
    p_gray.add_argument("-o", "--output", required=True, help="Output image path")
    p_gray.add_argument("--method", choices=["bt601", "bt709"], default="bt709", help="Luminance weights (default: bt709)")

    # --- invert ---
    p_inv = sub.add_parser("invert", help="Invert (negate) colors")
    p_inv.add_argument("input", help="Input image path")
    p_inv.add_argument("-o", "--output", required=True, help="Output image path")

    # --- colorspace ---
    p_cs = sub.add_parser("colorspace", help="Convert to a different color space")
    p_cs.add_argument("input", help="Input image path")
    p_cs.add_argument("-o", "--output", required=True, help="Output image path")
    p_cs.add_argument("--to", required=True, choices=["hsv", "lab", "ycbcr", "bgr"], help="Target color space")

    # --- channel ---
    p_ch = sub.add_parser("channel", help="Split or merge color channels")
    p_ch.add_argument("input", help="Input image path")
    p_ch.add_argument("-o", "--output", required=True, help="Output image path")
    p_ch.add_argument("--mode", required=True, choices=["split", "merge"], help="Channel operation")
    p_ch.add_argument("--channel", type=int, help="Channel index for merge (0-based)")
    p_ch.add_argument("--replace", help="Replacement channel image file for merge")

    # --- histogram ---
    p_hist = sub.add_parser("histogram", help="Compute and save histogram plot")
    p_hist.add_argument("input", help="Input image path")
    p_hist.add_argument("-o", "--output", required=True, help="Output histogram image path")
    p_hist_group = p_hist.add_mutually_exclusive_group()
    p_hist_group.add_argument("--color", action="store_true", help="Per-channel (R/G/B) histogram")
    p_hist_group.add_argument("--gray", action="store_true", help="Single grayscale histogram")

    # --- equalize ---
    p_eq = sub.add_parser("equalize", help="Histogram equalization")
    p_eq.add_argument("input", help="Input image path")
    p_eq.add_argument("-o", "--output", required=True, help="Output image path")
    p_eq.add_argument("--method", choices=["global", "clahe"], default="global", help="Equalization method (default: global)")
    p_eq.add_argument("--clip-limit", type=float, default=2.0, help="CLAHE clip limit (default: 2.0)")
    p_eq.add_argument("--grid-size", type=int, default=8, help="CLAHE tile grid size (default: 8)")

    # --- auto-levels ---
    p_al = sub.add_parser("auto-levels", help="Per-channel percentile stretch")
    p_al.add_argument("input", help="Input image path")
    p_al.add_argument("-o", "--output", required=True, help="Output image path")
    p_al.add_argument("--clip-percent", type=float, default=1.0, help="Clip percent from each end (default: 1.0)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "tone": cmd_tone,
        "saturation": cmd_saturation,
        "grayscale": cmd_grayscale,
        "invert": cmd_invert,
        "colorspace": cmd_colorspace,
        "channel": cmd_channel,
        "histogram": cmd_histogram,
        "equalize": cmd_equalize,
        "auto-levels": cmd_auto_levels,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
