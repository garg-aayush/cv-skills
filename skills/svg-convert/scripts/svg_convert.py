#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "cairosvg"]
# ///
"""svg-convert: Convert SVG files to raster formats, inspect SVG metadata, and render at custom scales."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


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
    """Validate that the input is an existing .svg file."""
    p = Path(path)
    if not p.exists():
        _err(f"Input file not found: {path}")
    if not p.is_file():
        _err(f"Input path is not a file: {path}")
    ext = p.suffix.lower()
    if ext != ".svg":
        _err(f"Unsupported input format '{ext}'. This skill only handles SVG files (.svg). "
             "For raster-to-raster conversion, use the image-format skill.")
    return p


_SUPPORTED_OUTPUT = {".png", ".jpg", ".jpeg", ".webp"}


def _validate_output(path: str) -> Path:
    """Validate the output path and extension."""
    p = Path(path)
    if not p.parent.exists():
        _err(f"Output directory does not exist: {p.parent}")
    ext = p.suffix.lower()
    if ext not in _SUPPORTED_OUTPUT:
        _err(f"Unsupported output format '{ext}'. Supported: {', '.join(sorted(_SUPPORTED_OUTPUT))}")
    return p


# ---------------------------------------------------------------------------
# Renderer detection
# ---------------------------------------------------------------------------
_HAS_RESVG = shutil.which("resvg") is not None

_HAS_CAIROSVG = False
try:
    import cairosvg  # noqa: F401
    _HAS_CAIROSVG = True
except (ImportError, OSError):
    pass


def _check_renderer() -> None:
    """Ensure at least one SVG renderer is available."""
    if not _HAS_RESVG and not _HAS_CAIROSVG:
        _err(
            "No SVG renderer available. Install one of:\n"
            "  1. resvg CLI — download from https://github.com/RazrFalcon/resvg/releases and add to PATH\n"
            "  2. cairosvg — 'uv pip install cairosvg' (requires system libcairo2)"
        )


# ---------------------------------------------------------------------------
# SVG parsing helpers
# ---------------------------------------------------------------------------
def _parse_svg_tree(svg_path: Path) -> ET.ElementTree:
    """Parse SVG XML, return the ElementTree."""
    try:
        return ET.parse(svg_path)
    except ET.ParseError as e:
        _err(f"Failed to parse SVG XML: {e}")


def _parse_length(value: str | None) -> float | None:
    """Parse an SVG length value (e.g., '100', '100px', '10cm') to a numeric value.
    Returns pixels for px/unitless, or None if unparseable."""
    if value is None:
        return None
    value = value.strip()
    # Strip common units — we treat px and unitless the same
    for unit in ("px", "pt", "em", "ex", "cm", "mm", "in", "%"):
        if value.endswith(unit):
            value = value[: -len(unit)].strip()
            break
    try:
        return float(value)
    except ValueError:
        return None


def _get_svg_dimensions(tree: ET.ElementTree) -> tuple[float | None, float | None, str | None]:
    """Extract width, height, and viewBox from SVG root element.
    Returns (width, height, viewBox_string)."""
    root = tree.getroot()
    # Handle namespace
    tag = root.tag
    ns = ""
    if tag.startswith("{"):
        ns = tag[: tag.index("}") + 1]

    if root.tag not in (f"{ns}svg", "svg"):
        _err("Root element is not <svg>. Is this a valid SVG file?")

    width = _parse_length(root.get("width"))
    height = _parse_length(root.get("height"))
    viewbox_str = root.get("viewBox")

    # If width/height not set but viewBox exists, derive from viewBox
    if (width is None or height is None) and viewbox_str:
        parts = viewbox_str.replace(",", " ").split()
        if len(parts) == 4:
            try:
                vb_w = float(parts[2])
                vb_h = float(parts[3])
                if width is None:
                    width = vb_w
                if height is None:
                    height = vb_h
            except ValueError:
                pass

    return width, height, viewbox_str


def _count_elements(tree: ET.ElementTree) -> dict[str, int]:
    """Count SVG elements by local tag name."""
    counts: dict[str, int] = {}
    for elem in tree.iter():
        tag = elem.tag
        # Strip namespace
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        counts[tag] = counts.get(tag, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def _render_with_resvg(
    svg_path: Path,
    output_path: Path,
    width: int | None = None,
    height: int | None = None,
    background: str | None = None,
) -> Path:
    """Render SVG to raster using resvg CLI. Returns the output path.
    resvg only outputs PNG, so for JPEG/WebP we render to a temp PNG then convert."""
    out_ext = output_path.suffix.lower()
    needs_conversion = out_ext in (".jpg", ".jpeg", ".webp")

    if needs_conversion:
        # resvg outputs PNG; we'll convert after
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(tmp_fd)
        render_target = Path(tmp_path)
    else:
        render_target = output_path

    cmd = ["resvg", str(svg_path), str(render_target)]
    if width is not None:
        cmd.extend(["--width", str(width)])
    if height is not None:
        cmd.extend(["--height", str(height)])
    if background is not None:
        cmd.extend(["--background", background])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if needs_conversion and Path(tmp_path).exists():
                os.unlink(tmp_path)
            _err(f"resvg failed (exit {result.returncode}): {stderr}")
    except FileNotFoundError:
        if needs_conversion and Path(tmp_path).exists():
            os.unlink(tmp_path)
        _err("resvg binary not found on PATH.")
    except subprocess.TimeoutExpired:
        if needs_conversion and Path(tmp_path).exists():
            os.unlink(tmp_path)
        _err("resvg timed out after 60 seconds.")

    if needs_conversion:
        try:
            _convert_png_to_format(render_target, output_path, background)
        finally:
            if render_target.exists():
                os.unlink(render_target)

    return output_path


def _render_with_cairosvg(
    svg_path: Path,
    output_path: Path,
    width: int | None = None,
    height: int | None = None,
    background: str | None = None,
) -> Path:
    """Render SVG to raster using cairosvg. Returns the output path.
    cairosvg outputs PNG natively; for JPEG/WebP we convert after."""
    import cairosvg as _cairosvg

    out_ext = output_path.suffix.lower()
    needs_conversion = out_ext in (".jpg", ".jpeg", ".webp")

    if needs_conversion:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(tmp_fd)
        render_target = Path(tmp_path)
    else:
        render_target = output_path

    kwargs: dict = {"url": str(svg_path), "write_to": str(render_target)}
    if width is not None:
        kwargs["output_width"] = width
    if height is not None:
        kwargs["output_height"] = height
    if background is not None:
        kwargs["background_color"] = background

    try:
        _cairosvg.svg2png(**kwargs)
    except Exception as e:
        if needs_conversion and Path(tmp_path).exists():
            os.unlink(tmp_path)
        _err(f"cairosvg rendering failed: {e}")

    if needs_conversion:
        try:
            _convert_png_to_format(render_target, output_path, background)
        finally:
            if render_target.exists():
                os.unlink(render_target)

    return output_path


def _convert_png_to_format(
    png_path: Path, output_path: Path, background: str | None = None
) -> None:
    """Convert a rendered PNG to JPEG or WebP using Pillow."""
    out_ext = output_path.suffix.lower()
    try:
        img = Image.open(png_path)
        img.load()
    except Exception as e:
        _err(f"Failed to open rendered PNG for conversion: {e}")

    if out_ext in (".jpg", ".jpeg"):
        # JPEG doesn't support alpha — composite on background
        if img.mode in ("RGBA", "LA", "PA"):
            bg_color = background or "white"
            try:
                from PIL import ImageColor
                rgb = ImageColor.getrgb(bg_color)
            except (ValueError, AttributeError):
                rgb = (255, 255, 255)
            bg = Image.new("RGB", img.size, rgb[:3])
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            elif img.mode == "PA":
                img = img.convert("RGBA")
                bg.paste(img, mask=img.split()[3])
            elif img.mode == "LA":
                bg_l = Image.new("L", img.size, rgb[0] if len(rgb) >= 1 else 255)
                bg_l.paste(img.split()[0], mask=img.split()[1])
                bg = bg_l.convert("RGB")
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(str(output_path), format="JPEG", quality=85)
    elif out_ext == ".webp":
        img.save(str(output_path), format="WEBP", quality=80)
    else:
        img.save(str(output_path))


def _render_svg(
    svg_path: Path,
    output_path: Path,
    width: int | None = None,
    height: int | None = None,
    background: str | None = None,
) -> Path:
    """Render SVG using the best available renderer."""
    _check_renderer()

    if _HAS_RESVG:
        _info("Using resvg renderer.")
        return _render_with_resvg(svg_path, output_path, width, height, background)
    else:
        _info("resvg not found, using cairosvg fallback.")
        return _render_with_cairosvg(svg_path, output_path, width, height, background)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------
def cmd_info(args: argparse.Namespace) -> None:
    """Display SVG metadata as JSON to stdout."""
    inp = _validate_input(args.input)
    tree = _parse_svg_tree(inp)
    width, height, viewbox = _get_svg_dimensions(tree)
    element_counts = _count_elements(tree)

    # Total element count (excluding root svg)
    total_elements = sum(element_counts.values())

    result: dict = {
        "file": str(inp),
        "file_size_bytes": os.path.getsize(inp),
        "width": width,
        "height": height,
        "viewBox": viewbox,
        "total_elements": total_elements,
        "element_counts": element_counts,
    }

    print(json.dumps(result, indent=2))


def cmd_render(args: argparse.Namespace) -> None:
    """Render SVG to raster format (PNG/JPEG/WebP)."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)

    # Determine output format
    out_ext = out.suffix.lower()
    fmt = args.format
    if fmt:
        fmt = fmt.lower().lstrip(".")
        fmt_map = {"png": ".png", "jpg": ".jpg", "jpeg": ".jpeg", "webp": ".webp"}
        if fmt not in fmt_map:
            _err(f"Unsupported format '{fmt}'. Supported: png, jpg, jpeg, webp")
        # Warn if extension doesn't match --format
        expected_ext = fmt_map[fmt]
        if out_ext != expected_ext and not (out_ext in (".jpg", ".jpeg") and fmt in ("jpg", "jpeg")):
            _info(f"Warning: --format '{fmt}' does not match output extension '{out_ext}'. "
                  f"Using extension '{out_ext}'.")

    # Parse SVG to get natural dimensions for default sizing
    tree = _parse_svg_tree(inp)
    nat_w, nat_h, _ = _get_svg_dimensions(tree)

    render_w: int | None = None
    render_h: int | None = None

    if nat_w and nat_h:
        render_w = int(nat_w)
        render_h = int(nat_h)

    background = args.background

    # For JPEG, default to white background if none specified
    if out_ext in (".jpg", ".jpeg") and background is None:
        background = "white"

    _render_svg(inp, out, render_w, render_h, background)

    # Apply quality settings for JPEG/WebP if using Pillow conversion
    if args.quality and out_ext in (".jpg", ".jpeg", ".webp"):
        # Re-save with specified quality
        try:
            img = Image.open(out)
            img.load()
            if out_ext in (".jpg", ".jpeg"):
                img.save(str(out), format="JPEG", quality=args.quality)
            elif out_ext == ".webp":
                img.save(str(out), format="WEBP", quality=args.quality)
        except Exception as e:
            _err(f"Failed to apply quality setting: {e}")

    _info(f"Saved: {out} ({os.path.getsize(out)} bytes)")


def cmd_resize_render(args: argparse.Namespace) -> None:
    """Render SVG at a custom scale or explicit dimensions."""
    inp = _validate_input(args.input)
    out = _validate_output(args.output)

    tree = _parse_svg_tree(inp)
    nat_w, nat_h, _ = _get_svg_dimensions(tree)

    scale = args.scale
    width = args.width
    height = args.height

    # Validate argument combinations
    if scale is not None and (width is not None or height is not None):
        _err("Cannot combine --scale with --width/--height. Use one or the other.")

    if scale is not None:
        if nat_w is None or nat_h is None:
            _err("SVG has no width/height or viewBox — cannot apply --scale. "
                 "Use --width and --height instead.")
        if scale <= 0:
            _err(f"Scale must be positive, got {scale}.")
        render_w = int(nat_w * scale)
        render_h = int(nat_h * scale)
    elif width is not None or height is not None:
        if width is not None and height is not None:
            render_w = width
            render_h = height
        elif width is not None:
            # Compute height to preserve aspect ratio
            if nat_w and nat_h:
                render_w = width
                render_h = int(nat_h * (width / nat_w))
            else:
                _err("SVG has no intrinsic dimensions — must specify both --width and --height.")
        else:
            # Only height specified
            if nat_w and nat_h:
                render_h = height
                render_w = int(nat_w * (height / nat_h))
            else:
                _err("SVG has no intrinsic dimensions — must specify both --width and --height.")
    else:
        # No scale or dimensions — use natural size
        if nat_w is None or nat_h is None:
            _err("SVG has no width/height or viewBox. Specify --scale, --width, or --height.")
        render_w = int(nat_w)
        render_h = int(nat_h)

    out_ext = out.suffix.lower()
    background = args.background

    # For JPEG, default to white background
    if out_ext in (".jpg", ".jpeg") and background is None:
        background = "white"

    _render_svg(inp, out, render_w, render_h, background)
    _info(f"Saved: {out} ({render_w}x{render_h}, {os.path.getsize(out)} bytes)")


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="svg_convert",
        description="Convert SVG files to raster formats, inspect SVG metadata, and render at custom scales.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- info ---
    p_info = sub.add_parser("info", help="Display SVG metadata as JSON")
    p_info.add_argument("input", help="Input SVG file path")

    # --- render ---
    p_render = sub.add_parser("render", help="Render SVG to raster format")
    p_render.add_argument("input", help="Input SVG file path")
    p_render.add_argument("-o", "--output", required=True, help="Output image path (.png, .jpg, .webp)")
    p_render.add_argument("--format", help="Override output format (png, jpg, webp)")
    p_render.add_argument("--quality", type=int, help="Quality for JPEG/WebP (1-100)")
    p_render.add_argument("--background", help="Background color (hex or named, e.g., white, #FF0000). Default: white for JPEG.")

    # --- resize-render ---
    p_resize = sub.add_parser("resize-render", help="Render SVG at custom scale or dimensions")
    p_resize.add_argument("input", help="Input SVG file path")
    p_resize.add_argument("-o", "--output", required=True, help="Output image path (.png, .jpg, .webp)")
    p_resize.add_argument("--scale", type=float, help="Scale factor (e.g., 2.0 for 2x)")
    p_resize.add_argument("--width", type=int, help="Target width in pixels")
    p_resize.add_argument("--height", type=int, help="Target height in pixels")
    p_resize.add_argument("--background", help="Background color (hex or named). Default: white for JPEG.")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "info": cmd_info,
        "render": cmd_render,
        "resize-render": cmd_resize_render,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
