---
name: image-filters
description: Blur, sharpen, denoise, and apply edge-preserving bilateral filters. Use when the user wants to smooth an image, soften details, reduce noise or grain, sharpen a blurry photo, or apply Gaussian/median/unsharp-mask filters. Do NOT use for edge detection (use edges-masks) or color/brightness adjustments (use color-adjust).
user_invocable: true
---

# image-filters

Spatial filtering, noise reduction, and sharpening for raster images.

## Prerequisites

- `uv` on PATH

## Running Scripts

All commands use:

```
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py <subcommand> [args]
```

- Always run with `uv run` — never `python`, `pip install`, or virtualenv activation
- Dependencies are declared inline (PEP 723) — `uv run` handles resolution automatically
- Do NOT modify or install from a requirements.txt

## Subcommands

### blur

Apply Gaussian, box, or median blur.

```bash
# Gaussian blur with sigma 2
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py blur input.png -o blurred.png --method gaussian --sigma 2

# Gaussian blur with explicit kernel size
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py blur input.png -o blurred.png --method gaussian --sigma 1.5 --kernel 7

# Box blur (uniform averaging) with kernel 9
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py blur input.jpg -o blurred.jpg --method box --kernel 9

# Median blur (good for salt-and-pepper noise)
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py blur input.png -o blurred.png --method median --kernel 5
```

| Flag | Description |
|---|---|
| `--method` | **Required.** `gaussian`, `box`, or `median` |
| `--sigma F` | Sigma for Gaussian blur (default: 1.0). Ignored by box/median. |
| `--kernel N` | Kernel size. Must be odd for gaussian/median. Default: auto for gaussian, 5 for box/median. |

### bilateral

Edge-preserving bilateral filter. Smooths flat regions while preserving edges.

```bash
# Default bilateral filter
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py bilateral input.png -o smoothed.png

# Strong smoothing with large neighborhood
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py bilateral input.jpg -o smoothed.jpg --d 15 --sigma-color 100 --sigma-space 100

# Subtle smoothing
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py bilateral photo.png -o photo_smooth.png --d 5 --sigma-color 50 --sigma-space 50
```

| Flag | Description |
|---|---|
| `--d N` | Diameter of pixel neighborhood (default: 9). Larger = slower. |
| `--sigma-color F` | Filter sigma in color space (default: 75). Larger = more color mixing. |
| `--sigma-space F` | Filter sigma in coordinate space (default: 75). Larger = farther pixels influence. |

### sharpen

Sharpen image using basic enhancement, unsharp mask, or Laplacian method.

```bash
# Basic sharpening (Pillow ImageEnhance)
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py sharpen input.png -o sharp.png --method basic --amount 2.0

# Unsharp mask (subtle sharpening for photos)
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py sharpen photo.jpg -o sharp.jpg --method unsharp --amount 1.5 --radius 5

# Strong unsharp mask
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py sharpen input.png -o sharp.png --method unsharp --amount 3.0 --radius 3

# Laplacian edge-enhancing sharpness
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py sharpen input.png -o sharp.png --method laplacian --amount 1.0
```

| Flag | Description |
|---|---|
| `--method` | **Required.** `basic`, `unsharp`, or `laplacian` |
| `--amount F` | Sharpening strength. Default: 2.0 (basic), 1.5 (unsharp), 1.0 (laplacian). |
| `--radius N` | Gaussian kernel radius for unsharp mask (default: 5). Ignored by basic/laplacian. |

### denoise

Non-local means denoising for photo noise reduction.

```bash
# Auto-detect color/gray and denoise
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py denoise noisy.jpg -o clean.jpg

# Force color denoising with higher strength
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py denoise noisy.png -o clean.png --color --strength 15

# Force grayscale denoising
uv run ${CLAUDE_SKILL_DIR}/scripts/filters_enhancement.py denoise noisy.png -o clean.png --gray --strength 10
```

| Flag | Description |
|---|---|
| `--strength F` | Filter strength (default: 10). Higher = more smoothing but may lose detail. |
| `--color` | Force color denoising (fastNlMeansDenoisingColored) |
| `--gray` | Force grayscale denoising (fastNlMeansDenoising) |

Default: auto-detect from image mode (RGB/RGBA uses color, L uses gray).

## Output Conventions

- **Messages** (confirmations, filter parameters) → **stderr**
- **Errors** → stderr with `Error:` prefix, exit code 1
- Saved file path and size reported to stderr

## Anti-patterns

- Do NOT use `blur` for edge-preserving smoothing — use `bilateral` instead
- Do NOT use `sharpen` to enhance edges for detection — use the `edges-masks` skill (Canny/Sobel)
- Do NOT use `denoise` for artistic blur effects — use `blur` with appropriate kernel/sigma
- Do NOT pass even kernel sizes to gaussian or median blur — they must be odd integers
- Do NOT use this skill for brightness/contrast adjustment — use `color-adjust`
