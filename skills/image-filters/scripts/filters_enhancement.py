#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "opencv-python-headless", "numpy"]
# ///
"""image-filters: Blur, bilateral filter, sharpen, and denoise images."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance

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
        # Handle JPEG mode restrictions
        ext = path.suffix.lower()
        if ext in (".jpg", ".jpeg") and img.mode == "RGBA":
            _err(
                "Cannot save RGBA image as JPEG (JPEG does not support transparency). "
                "Remove alpha first with the image-format skill: "
                "uv run format_io.py alpha INPUT -o intermediate.png --mode remove"
            )
        if ext in (".jpg", ".jpeg") and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(str(path), **kwargs)
        _info(f"Saved: {path} ({os.path.getsize(path)} bytes)")
    except Exception as e:
        _err(f"Failed to save image '{path}': {e}")


def _to_cv(pil_img: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR numpy array."""
    if pil_img.mode == "RGBA":
        arr = np.array(pil_img)
        # RGBA → BGRA
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
    """Convert OpenCV BGR numpy array back to PIL Image (BGR→RGB)."""
    if len(arr.shape) == 2:
        # Grayscale
        return Image.fromarray(arr, mode="L")
    elif arr.shape[2] == 4:
        # BGRA → RGBA
        rgb_arr = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGBA)
        return Image.fromarray(rgb_arr, mode="RGBA")
    else:
        # BGR → RGB
        rgb_arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb_arr, mode="RGB")


def _validate_odd_kernel(k: int, name: str = "kernel") -> int:
    """Validate that a kernel size is a positive odd integer."""
    if k < 1:
        _err(f"Kernel size must be positive, got {k}.")
    if k % 2 == 0:
        _err(f"Kernel size must be an odd integer, got {k}. Try {k - 1} or {k + 1}.")
    return k


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_blur(args: argparse.Namespace) -> None:
    """Apply Gaussian, box, or median blur."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    method = args.method
    cv_img = _to_cv(img)

    if method == "gaussian":
        sigma = args.sigma
        if args.kernel is not None:
            k = _validate_odd_kernel(args.kernel)
        else:
            # kernel 0 means auto-calculate from sigma
            k = 0
        result = cv2.GaussianBlur(cv_img, (k, k), sigma)
        _info(f"Applied Gaussian blur (sigma={sigma}, kernel={k if k > 0 else 'auto'}).")

    elif method == "box":
        k = args.kernel if args.kernel is not None else 5
        if k < 1:
            _err(f"Kernel size must be positive, got {k}.")
        result = cv2.blur(cv_img, (k, k))
        _info(f"Applied box blur (kernel={k}).")

    elif method == "median":
        k = args.kernel if args.kernel is not None else 5
        k = _validate_odd_kernel(k)
        result = cv2.medianBlur(cv_img, k)
        _info(f"Applied median blur (kernel={k}).")

    else:
        _err(f"Unknown blur method '{method}'. Use: gaussian, box, median.")

    result_img = _from_cv(result)
    _save_image(result_img, out)


def cmd_bilateral(args: argparse.Namespace) -> None:
    """Apply edge-preserving bilateral filter."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    d = args.d
    sigma_color = args.sigma_color
    sigma_space = args.sigma_space

    cv_img = _to_cv(img)

    # bilateralFilter only works on 8-bit or floating-point, 1 or 3 channel images
    if len(cv_img.shape) == 3 and cv_img.shape[2] == 4:
        # BGRA: split alpha, filter BGR, reattach alpha
        bgr = cv_img[:, :, :3]
        alpha = cv_img[:, :, 3]
        filtered = cv2.bilateralFilter(bgr, d, sigma_color, sigma_space)
        result = np.dstack([filtered, alpha])
    else:
        result = cv2.bilateralFilter(cv_img, d, sigma_color, sigma_space)

    _info(f"Applied bilateral filter (d={d}, sigmaColor={sigma_color}, sigmaSpace={sigma_space}).")

    result_img = _from_cv(result)
    _save_image(result_img, out)


def cmd_sharpen(args: argparse.Namespace) -> None:
    """Sharpen image using basic, unsharp mask, or Laplacian method."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    method = args.method

    if method == "basic":
        amount = args.amount if args.amount is not None else 2.0
        enhancer = ImageEnhance.Sharpness(img)
        result_img = enhancer.enhance(amount)
        _info(f"Applied basic sharpening (factor={amount}).")
        _save_image(result_img, out)
        return

    elif method == "unsharp":
        amount = args.amount if args.amount is not None else 1.5
        radius = args.radius if args.radius is not None else 5
        # Kernel for Gaussian must be odd
        k = radius if radius % 2 == 1 else radius + 1
        if k < 1:
            k = 1

        cv_img = _to_cv(img)

        if len(cv_img.shape) == 3 and cv_img.shape[2] == 4:
            # BGRA: sharpen BGR, keep alpha
            bgr = cv_img[:, :, :3]
            alpha = cv_img[:, :, 3]
            blurred = cv2.GaussianBlur(bgr, (k, k), 0)
            sharpened = cv2.addWeighted(bgr, 1 + amount, blurred, -amount, 0)
            result = np.dstack([sharpened, alpha])
        else:
            blurred = cv2.GaussianBlur(cv_img, (k, k), 0)
            result = cv2.addWeighted(cv_img, 1 + amount, blurred, -amount, 0)

        _info(f"Applied unsharp mask (amount={amount}, radius={radius}).")
        result_img = _from_cv(result)
        _save_image(result_img, out)
        return

    elif method == "laplacian":
        amount = args.amount if args.amount is not None else 1.0

        cv_img = _to_cv(img)

        if len(cv_img.shape) == 3 and cv_img.shape[2] == 4:
            # BGRA: sharpen BGR, keep alpha
            bgr = cv_img[:, :, :3].astype(np.float64)
            alpha = cv_img[:, :, 3]
            laplacian = cv2.Laplacian(bgr, cv2.CV_64F)
            sharpened = bgr + amount * laplacian
            sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
            result = np.dstack([sharpened, alpha])
        elif len(cv_img.shape) == 2:
            # Grayscale
            img_f = cv_img.astype(np.float64)
            laplacian = cv2.Laplacian(img_f, cv2.CV_64F)
            sharpened = img_f + amount * laplacian
            result = np.clip(sharpened, 0, 255).astype(np.uint8)
        else:
            img_f = cv_img.astype(np.float64)
            laplacian = cv2.Laplacian(img_f, cv2.CV_64F)
            sharpened = img_f + amount * laplacian
            result = np.clip(sharpened, 0, 255).astype(np.uint8)

        _info(f"Applied Laplacian sharpening (amount={amount}).")
        result_img = _from_cv(result)
        _save_image(result_img, out)
        return

    else:
        _err(f"Unknown sharpen method '{method}'. Use: basic, unsharp, laplacian.")


def cmd_denoise(args: argparse.Namespace) -> None:
    """Apply non-local means denoising."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)
    img = _open_image(inp)

    strength = args.strength

    # Determine color vs gray mode
    if args.color:
        use_color = True
    elif args.gray:
        use_color = False
    else:
        # Auto-detect
        use_color = img.mode in ("RGB", "RGBA", "P")

    cv_img = _to_cv(img)
    has_alpha = len(cv_img.shape) == 3 and cv_img.shape[2] == 4

    if use_color:
        if has_alpha:
            # BGRA: denoise BGR, keep alpha
            bgr = cv_img[:, :, :3]
            alpha = cv_img[:, :, 3]
            denoised = cv2.fastNlMeansDenoisingColored(bgr, None, strength, strength, 7, 21)
            result = np.dstack([denoised, alpha])
        elif len(cv_img.shape) == 2:
            # Grayscale image but --color requested — convert to BGR, denoise, convert back
            bgr = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2BGR)
            denoised = cv2.fastNlMeansDenoisingColored(bgr, None, strength, strength, 7, 21)
            result = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
        else:
            result = cv2.fastNlMeansDenoisingColored(cv_img, None, strength, strength, 7, 21)
        _info(f"Applied color denoising (strength={strength}).")
    else:
        if has_alpha:
            # Convert to grayscale for denoising, but this loses color
            gray = cv2.cvtColor(cv_img[:, :, :3], cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray, None, strength, 7, 21)
            result = denoised
        elif len(cv_img.shape) == 3:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray, None, strength, 7, 21)
            result = denoised
        else:
            result = cv2.fastNlMeansDenoising(cv_img, None, strength, 7, 21)
        _info(f"Applied grayscale denoising (strength={strength}).")

    result_img = _from_cv(result)
    _save_image(result_img, out)


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filters_enhancement",
        description="Blur, bilateral filter, sharpen, and denoise images.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- blur ---
    p_blur = sub.add_parser("blur", help="Apply Gaussian, box, or median blur")
    p_blur.add_argument("input", help="Input image path")
    p_blur.add_argument("-o", "--output", required=True, help="Output image path")
    p_blur.add_argument(
        "--method", required=True, choices=["gaussian", "box", "median"],
        help="Blur method",
    )
    p_blur.add_argument("--sigma", type=float, default=1.0, help="Sigma for Gaussian blur (default: 1.0)")
    p_blur.add_argument("--kernel", type=int, default=None, help="Kernel size (must be odd for gaussian/median)")

    # --- bilateral ---
    p_bilateral = sub.add_parser("bilateral", help="Edge-preserving bilateral filter")
    p_bilateral.add_argument("input", help="Input image path")
    p_bilateral.add_argument("-o", "--output", required=True, help="Output image path")
    p_bilateral.add_argument("--d", type=int, default=9, help="Diameter of pixel neighborhood (default: 9)")
    p_bilateral.add_argument("--sigma-color", type=float, default=75.0, help="Filter sigma in color space (default: 75)")
    p_bilateral.add_argument("--sigma-space", type=float, default=75.0, help="Filter sigma in coordinate space (default: 75)")

    # --- sharpen ---
    p_sharpen = sub.add_parser("sharpen", help="Sharpen image")
    p_sharpen.add_argument("input", help="Input image path")
    p_sharpen.add_argument("-o", "--output", required=True, help="Output image path")
    p_sharpen.add_argument(
        "--method", required=True, choices=["basic", "unsharp", "laplacian"],
        help="Sharpen method",
    )
    p_sharpen.add_argument("--amount", type=float, default=None, help="Sharpening amount/factor (default varies by method)")
    p_sharpen.add_argument("--radius", type=int, default=None, help="Radius for unsharp mask Gaussian kernel (default: 5)")

    # --- denoise ---
    p_denoise = sub.add_parser("denoise", help="Non-local means denoising")
    p_denoise.add_argument("input", help="Input image path")
    p_denoise.add_argument("-o", "--output", required=True, help="Output image path")
    p_denoise.add_argument("--strength", type=float, default=10.0, help="Filter strength (default: 10)")
    color_group = p_denoise.add_mutually_exclusive_group()
    color_group.add_argument("--color", action="store_true", help="Force color denoising")
    color_group.add_argument("--gray", action="store_true", help="Force grayscale denoising")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "blur": cmd_blur,
        "bilateral": cmd_bilateral,
        "sharpen": cmd_sharpen,
        "denoise": cmd_denoise,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
