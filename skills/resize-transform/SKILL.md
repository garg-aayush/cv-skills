---
name: resize-transform
description: Resize, crop, pad, rotate, flip, and arrange images into grids. Use when the user wants to make an image smaller or larger, create a thumbnail, scale by percentage, fit to specific dimensions, cut out a region, trim whitespace or borders, add padding/letterbox, rotate or mirror, or combine images side by side in a montage. Do NOT use for format conversion (use image-format). For arranging images as layers/overlays rather than a grid, use image-combine.
user_invocable: true
---

# resize-transform

Resize, crop, auto-crop, pad, rotate/flip, and montage grid layout for raster images.

## Prerequisites

- `uv` on PATH

## Running Scripts

All commands use:

```
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py <subcommand> [args]
```

- Always run with `uv run` — never `python`, `pip install`, or virtualenv activation
- Dependencies are declared inline (PEP 723) — `uv run` handles resolution automatically
- Do NOT modify or install from a requirements.txt

## Subcommands

### resize

Resize by exact dimensions, percentage, or fit-within bounds.

```bash
# Resize to exact 800x600
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py resize input.png -o output.png --width 800 --height 600

# Resize to width, preserve aspect ratio
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py resize input.png -o output.png --width 800

# Resize to height, preserve aspect ratio
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py resize input.png -o output.png --height 400

# Scale by percentage (50% = half size)
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py resize input.png -o output.png --percent 50

# Fit within 800x600 bounds, preserving aspect ratio (thumbnail)
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py resize input.png -o thumb.png --fit 800x600

# Use nearest-neighbor resampling (pixel art)
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py resize pixel_art.png -o scaled.png --percent 400 --resample nearest
```

| Flag | Description |
|---|---|
| `--width W` | Target width in pixels. Alone = preserve aspect ratio. |
| `--height H` | Target height in pixels. Alone = preserve aspect ratio. |
| `--percent P` | Scale by percentage (e.g., 50 = half, 200 = double). |
| `--fit WxH` | Fit within bounds preserving aspect ratio. |
| `--resample METHOD` | `nearest`, `bilinear`, `bicubic`, `lanczos` (default: `lanczos`). |

Only one resize mode at a time: `--width`/`--height`, `--percent`, or `--fit`.

### crop

Crop by pixel coordinates or aspect ratio.

```bash
# Crop by box coordinates (x1,y1,x2,y2)
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py crop input.png -o output.png --box 100,50,500,350

# Crop to 16:9 aspect ratio, centered
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py crop input.png -o output.png --aspect 16:9

# Crop to 1:1 (square), anchored to top-left
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py crop input.png -o output.png --aspect 1:1 --gravity top-left

# Custom aspect ratio
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py crop input.png -o output.png --aspect 3:2
```

| Flag | Description |
|---|---|
| `--box x1,y1,x2,y2` | Crop box as comma-separated pixel coordinates. |
| `--aspect RATIO` | Aspect ratio preset (`1:1`, `4:3`, `16:9`, `2:1`) or custom `W:H`. |
| `--gravity POS` | Anchor: `center` (default), `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right`. |

Use `--box` or `--aspect`, not both.

### auto-crop

Remove uniform borders (whitespace, solid color).

```bash
# Auto-detect border color from top-left pixel and remove
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py auto-crop input.png -o output.png

# Remove white borders with tolerance
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py auto-crop input.png -o output.png --color white --tolerance 10

# Remove specific color border
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py auto-crop input.png -o output.png --color "#CCCCCC"
```

| Flag | Description |
|---|---|
| `--color COLOR` | Border color to remove (hex or named). Default: auto-detect from top-left pixel. |
| `--tolerance N` | Pixel value tolerance for border detection (default: 0 = exact match). |

### pad

Add padding / letterbox to reach a target canvas size.

```bash
# Center 400x300 image on 800x600 white canvas
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py pad input.png -o output.png --size 800x600

# Pad with black background
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py pad input.png -o output.png --size 800x600 --color black

# Place image at top-left of canvas
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py pad input.png -o output.png --size 800x600 --gravity top-left
```

| Flag | Description |
|---|---|
| `--size WxH` | Target canvas size (required). |
| `--color COLOR` | Fill color (default: `white`). |
| `--gravity POS` | Image placement: `center` (default), `top`, `bottom`, `left`, `right`, `top-left`, `top-right`, `bottom-left`, `bottom-right`. |

Image must be smaller than target size. Resize first if needed.

### rotate

Rotate by angle and/or flip horizontally/vertically.

```bash
# Rotate 90 degrees counter-clockwise
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py rotate input.png -o output.png --angle 90

# Rotate 45 degrees with white fill for corners
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py rotate input.png -o output.png --angle 45 --fill white

# Flip horizontally (mirror)
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py rotate input.png -o output.png --flip h

# Flip vertically
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py rotate input.png -o output.png --flip v

# Flip and rotate (flip applied first, then rotate)
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py rotate input.png -o output.png --flip h --angle 90
```

| Flag | Description |
|---|---|
| `--angle N` | Rotation angle in degrees (counter-clockwise). 90/180/270 use lossless transpose. |
| `--flip h\|v` | `h` = horizontal mirror, `v` = vertical mirror. |
| `--fill COLOR` | Fill color for exposed corners (default: transparent for RGBA, white for RGB). |

Specify at least one of `--angle` or `--flip`.

### montage

Combine multiple images into a grid layout.

```bash
# 2-column grid from 4 images
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py montage img1.png img2.png img3.png img4.png -o grid.png --cols 2

# Single row (all in one row)
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py montage a.png b.png c.png -o row.png --cols 3

# Grid with spacing and black background
uv run ${CLAUDE_SKILL_DIR}/scripts/resize_geometry.py montage *.png -o grid.png --cols 3 --spacing 10 --background black
```

| Flag | Description |
|---|---|
| `--cols N` | Number of columns (default: min(n, 4)). |
| `--spacing N` | Pixel spacing between cells (default: 0). |
| `--background COLOR` | Background/spacing fill color (default: `white`). |

All images are resized to match the first image's dimensions. Requires at least 2 input images.

## Output Conventions

- **Messages** (confirmations, dimension info) -> **stderr**
- **Errors** -> stderr with `Error:` prefix, exit code 1
- No JSON output — all subcommands produce image files

## Anti-patterns

- Do NOT use `resize` for format conversion — use `image-format convert`
- Do NOT use `crop --box` with negative coordinates — coordinates must be within image bounds
- Do NOT combine `--box` and `--aspect` in a single crop — pick one mode
- Do NOT combine `--percent` with `--width`/`--height` or `--fit` — pick one resize mode
- Do NOT use `pad` on images larger than the target — resize first with `resize --fit`
- Do NOT use `rotate` for EXIF orientation fixes — use `image-format exif --mode auto-orient`
