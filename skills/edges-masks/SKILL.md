---
name: edges-masks
description: >
  Threshold images, detect edges, apply morphological operations, find contours,
  segment by color, and extract foreground masks with GrabCut. Use when the user
  wants to create a binary mask, find outlines or edges, clean up a mask with
  erode/dilate, extract object boundaries, isolate a color range, or generate a
  foreground/background segmentation for analysis. For removing a background to
  produce a transparent cutout image, use image-combine remove-bg instead.
---

# edges-masks

Thresholding, edge detection, morphological operations, contour extraction, color segmentation, and GrabCut foreground extraction.

## Prerequisites

- `uv` on PATH

## Running Scripts

All commands use:

```
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py <subcommand> [args]
```

- Always run with `uv run` — never `python`, `pip install`, or virtualenv activation
- Dependencies are declared inline (PEP 723) — `uv run` handles resolution automatically
- Do NOT modify or install from a requirements.txt

## Subcommands

### threshold

Binary thresholding with fixed, Otsu (automatic), or adaptive (local block-based) methods.

```bash
# Fixed threshold at value 128
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py threshold input.png -o binary.png --method fixed --value 128

# Otsu automatic threshold
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py threshold input.png -o binary.png --method otsu

# Adaptive threshold for uneven lighting
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py threshold input.png -o binary.png --method adaptive --block-size 11 --c 2
```

| Flag | Description |
|---|---|
| `--method` | **Required.** `fixed`, `otsu`, or `adaptive` |
| `--value N` | Threshold value for `fixed` method (default: 128) |
| `--block-size N` | Block size for `adaptive` (must be odd, default: 11) |
| `--c N` | Constant subtracted from mean for `adaptive` (default: 2) |

Output is a single-channel (grayscale) binary image.

### canny

Canny edge detection with hysteresis thresholds.

```bash
# Default thresholds (100, 200)
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py canny input.png -o edges.png

# Custom thresholds for finer/coarser edges
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py canny input.png -o edges.png --low 50 --high 150
```

| Flag | Description |
|---|---|
| `--low N` | Lower hysteresis threshold (default: 100) |
| `--high N` | Upper hysteresis threshold (default: 200) |

Output is a single-channel edge map.

### gradient

Sobel (directional) or Laplacian (second-derivative) gradient edge detection.

```bash
# Sobel edges in both directions (magnitude)
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py gradient input.png -o edges.png --method sobel --direction both

# Sobel horizontal edges only
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py gradient input.png -o edges.png --method sobel --direction x

# Laplacian edges
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py gradient input.png -o edges.png --method laplacian --ksize 5
```

| Flag | Description |
|---|---|
| `--method` | **Required.** `sobel` or `laplacian` |
| `--direction` | Sobel direction: `x`, `y`, or `both` (default: `both`). Ignored for laplacian. |
| `--ksize N` | Kernel size (must be odd, default: 3) |

Output is a single-channel normalized gradient map (0-255).

### morphology

Erosion, dilation, opening, closing, or morphological gradient.

```bash
# Dilate with 5x5 rectangular kernel
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py morphology input.png -o dilated.png --op dilate

# Erode with elliptical kernel, 3 iterations
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py morphology input.png -o eroded.png --op erode --shape ellipse --kernel 3 --iterations 3

# Opening (erosion then dilation) to remove small noise
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py morphology binary.png -o cleaned.png --op open --kernel 5

# Closing to fill small holes
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py morphology binary.png -o filled.png --op close

# Morphological gradient (dilation - erosion) for outlines
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py morphology input.png -o outline.png --op gradient
```

| Flag | Description |
|---|---|
| `--op` | **Required.** `erode`, `dilate`, `open`, `close`, or `gradient` |
| `--kernel N` | Structuring element size (default: 5) |
| `--shape` | Kernel shape: `rect`, `ellipse`, or `cross` (default: `rect`) |
| `--iterations N` | Number of iterations (default: 1) |

Works on both grayscale and color images.

### contours

Find object boundaries and draw them on the original image. Internally converts to grayscale, applies Otsu threshold, then finds contours.

```bash
# Find and draw all contours in green
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py contours input.png -o contours.png

# Filter small contours, draw in red with thick lines
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py contours input.png -o contours.png --min-area 500 --color "#FF0000" --thickness 3

# Filter by area range
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py contours input.png -o contours.png --min-area 100 --max-area 50000
```

| Flag | Description |
|---|---|
| `--min-area N` | Minimum contour area in pixels (filter out smaller) |
| `--max-area N` | Maximum contour area in pixels (filter out larger) |
| `--color HEX` | Contour color as `#RRGGBB` hex (default: `#00FF00` green) |
| `--thickness N` | Line thickness in pixels (default: 2) |

Output is a color image with contours drawn on the original.

### color-segment

Create a binary mask of pixels within a color range in HSV or LAB space.

```bash
# Segment green objects in HSV
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py color-segment input.png -o mask.png --space hsv --lower 35,100,100 --upper 85,255,255

# Segment by LAB range
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py color-segment input.png -o mask.png --space lab --lower 0,0,0 --upper 255,128,128
```

| Flag | Description |
|---|---|
| `--space` | **Required.** Color space: `hsv` or `lab` |
| `--lower` | **Required.** Lower bound as `H,S,V` or `L,A,B` (comma-separated integers) |
| `--upper` | **Required.** Upper bound as `H,S,V` or `L,A,B` (comma-separated integers) |

Output is a single-channel binary mask (white = in range, black = out of range). Requires a color input image.

### grabcut

Foreground extraction using GrabCut with a bounding box. Output is RGBA with background set to transparent.

```bash
# Extract foreground within bounding box
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py grabcut input.png -o foreground.png --rect 50,50,200,300

# More iterations for better accuracy
uv run ${CLAUDE_SKILL_DIR}/scripts/segment_morphology.py grabcut input.png -o foreground.png --rect 10,10,400,400 --iterations 10
```

| Flag | Description |
|---|---|
| `--rect` | **Required.** Bounding box as `x,y,w,h` (comma-separated integers) |
| `--iterations N` | Number of GrabCut iterations (default: 5) |

Output must be `.png` (RGBA with alpha channel). Requires a color input image.

## Output Conventions

- **Grayscale outputs** (threshold, canny, gradient, color-segment) are saved as single-channel images
- **Color outputs** (morphology on color input, contours) preserve the original color space
- **RGBA outputs** (grabcut) include an alpha channel for transparency
- **Messages** (confirmations, stats) go to **stderr**
- **Errors** go to stderr with `Error:` prefix, exit code 1

## Anti-patterns

- Do NOT use `threshold` for noise removal — use `morphology --op open` to clean up a binary image
- Do NOT use `canny` for sharpening — use the `image-filters` skill's sharpen subcommand
- Do NOT use `contours` on a noisy image without preprocessing — threshold or blur first
- Do NOT use `color-segment` with RGB values — convert your range to HSV or LAB first
- Do NOT use `grabcut` with JPEG output — GrabCut produces RGBA, which requires PNG
- Do NOT chain `threshold` + `morphology` manually for simple cleanup — use `morphology --op open/close` directly on the binary result
