---
name: color-adjust
description: >
  Adjust brightness, contrast, gamma, saturation, and color balance; convert to
  grayscale or between color spaces; split/merge channels; compute and equalize
  histograms; auto-level. Use when the user wants to brighten or darken a photo,
  fix exposure, boost or reduce color intensity, desaturate, invert colors, view
  color channels, or correct color cast. For producing a binary black/white mask
  (thresholding), use edges-masks instead.
---

# color-adjust

Tone, saturation, grayscale, invert, color space conversion, channel split/merge, histograms, equalization, and auto-levels.

## Prerequisites

- `uv` on PATH

## Running Scripts

All commands use:

```
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py <subcommand> [args]
```

- Always run with `uv run` — never `python`, `pip install`, or virtualenv activation
- Dependencies are declared inline (PEP 723) — `uv run` handles resolution automatically
- Do NOT modify or install from a requirements.txt

## Subcommands

### tone

Adjust brightness, contrast, and/or gamma. All three can be combined in one call.

```bash
# Brighten image by 50%
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py tone photo.jpg -o bright.jpg --brightness 1.5

# Increase contrast
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py tone photo.jpg -o contrast.jpg --contrast 1.8

# Gamma correction (brighten dark areas)
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py tone photo.jpg -o gamma.jpg --gamma 2.2

# Combine all three
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py tone photo.jpg -o adjusted.jpg --brightness 1.2 --contrast 1.3 --gamma 1.5
```

| Flag | Description |
|---|---|
| `--brightness F` | Brightness factor (default: 1.0). >1 brighter, <1 darker. |
| `--contrast F` | Contrast factor (default: 1.0). >1 more contrast, <1 less. |
| `--gamma F` | Gamma correction (default: 1.0). <1 brightens midtones, >1 darkens. |

### saturation

Adjust color intensity.

```bash
# Desaturate to grayscale
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py saturation photo.jpg -o desat.jpg --factor 0.0

# Boost saturation
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py saturation photo.jpg -o vivid.jpg --factor 2.0

# Subtle increase
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py saturation photo.jpg -o warm.jpg --factor 1.3
```

| Flag | Description |
|---|---|
| `--factor F` | Saturation factor (required). 0.0=grayscale, 1.0=unchanged, >1=more saturated. |

### grayscale

Convert RGB to luminance grayscale.

```bash
# Default BT.709 weights (modern standard)
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py grayscale photo.jpg -o gray.jpg

# BT.601 weights (legacy/NTSC)
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py grayscale photo.jpg -o gray601.jpg --method bt601
```

| Flag | Description |
|---|---|
| `--method` | `bt709` (default) or `bt601`. BT.709 for modern displays, BT.601 for legacy. |

### invert

Negate all color values (255 - pixel).

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py invert photo.jpg -o negative.jpg
```

No additional flags. Alpha channel is preserved (not inverted).

### colorspace

Convert image to a different color space.

```bash
# Convert to HSV
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py colorspace photo.jpg -o hsv.png --to hsv

# Convert to LAB
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py colorspace photo.jpg -o lab.png --to lab

# Convert to YCbCr
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py colorspace photo.jpg -o ycbcr.png --to ycbcr

# Convert to BGR
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py colorspace photo.jpg -o bgr.png --to bgr
```

| Flag | Description |
|---|---|
| `--to` | Target color space (required): `hsv`, `lab`, `ycbcr`, `bgr`. |

Note: Output channels represent raw color space values, not displayable RGB. Use for analysis or pipeline input.

### channel

Split image into individual channel images, or replace a single channel.

```bash
# Split into separate channel files (out_0.png, out_1.png, out_2.png)
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py channel photo.jpg -o out.png --mode split

# Replace red channel (index 0) with a mask image
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py channel photo.jpg -o merged.png --mode merge --channel 0 --replace mask.png
```

| Flag | Description |
|---|---|
| `--mode split` | Save each channel as a grayscale image. Output names: `{stem}_{i}{ext}`. |
| `--mode merge` | Replace one channel. Requires `--channel` and `--replace`. |
| `--channel N` | Channel index (0-based) for merge. |
| `--replace FILE` | Grayscale image to use as replacement channel. Must match input dimensions. |

### histogram

Compute and save a histogram plot as an image.

```bash
# Auto-detect (color if RGB, gray if grayscale)
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py histogram photo.jpg -o hist.png

# Force color histogram (R/G/B channels)
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py histogram photo.jpg -o hist.png --color

# Force grayscale histogram
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py histogram photo.jpg -o hist.png --gray
```

| Flag | Description |
|---|---|
| `--color` | Draw per-channel R/G/B histograms. |
| `--gray` | Draw single luminance histogram. |

Default: auto-detect from image mode.

### equalize

Histogram equalization for contrast enhancement.

```bash
# Global equalization
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py equalize photo.jpg -o equalized.jpg

# CLAHE (adaptive local equalization)
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py equalize photo.jpg -o clahe.jpg --method clahe

# CLAHE with custom parameters
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py equalize photo.jpg -o clahe.jpg --method clahe --clip-limit 4.0 --grid-size 16
```

| Flag | Description |
|---|---|
| `--method` | `global` (default) or `clahe` (adaptive). |
| `--clip-limit F` | CLAHE contrast clip limit (default: 2.0). Higher = more contrast. |
| `--grid-size N` | CLAHE tile grid size (default: 8). Larger = more global. |

For color images, equalization is applied to the L channel in LAB space (preserving color).

### auto-levels

Stretch histogram per channel to fill the full 0-255 range.

```bash
# Default 1% clip
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py auto-levels photo.jpg -o levels.jpg

# More aggressive clipping
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py auto-levels photo.jpg -o levels.jpg --clip-percent 2.5

# No clipping (pure min-max stretch)
uv run ${CLAUDE_SKILL_DIR}/scripts/color_adjustment.py auto-levels photo.jpg -o levels.jpg --clip-percent 0
```

| Flag | Description |
|---|---|
| `--clip-percent F` | Percentile to clip from each end (default: 1.0). 0 = pure stretch. |

## Output Conventions

- **Messages** (confirmations, warnings) -> **stderr**
- **Errors** -> stderr with `Error:` prefix, exit code 1
- **Data** (histogram plot) -> saved as image to `-o` path

## Anti-patterns

- Do NOT use `tone` for resizing — use the `resize-transform` skill
- Do NOT use `saturation --factor 0` as a grayscale converter — use `grayscale` for proper luminance weighting
- Do NOT use `colorspace` and expect displayable output — the raw channel values are not RGB
- Do NOT use `equalize` on already well-exposed images — it may introduce artifacts
- Do NOT use `channel --mode split` and manually recombine — use `channel --mode merge` instead
- Do NOT blur/sharpen with this skill — use `image-filters`
- Do NOT convert formats with this skill — use `image-format`
