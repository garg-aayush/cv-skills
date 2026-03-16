---
name: image-format
description: Convert between image formats (PNG, JPEG, WebP, TIFF, BMP, HEIC), inspect image metadata, handle alpha/transparency, manage EXIF and ICC profiles, and split/assemble animated GIF/WebP frames. Use when the user wants to change file type, save as a different format, export for web, check image info, strip metadata, fix photo orientation, extract an image's existing transparency mask (alpha channel), or work with animation frames. Do NOT use for SVG-to-raster conversion (use svg-convert). For removing transparency by compositing on a background, use this skill's alpha command, not image-combine.
user_invocable: true
---

# image-format

Image format conversion, metadata inspection, alpha/EXIF/ICC handling, and animation frame split/assemble.

## Prerequisites

- `uv` on PATH

## Running Scripts

All commands use:

```
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py <subcommand> [args]
```

- Always run with `uv run` — never `python`, `pip install`, or virtualenv activation
- Dependencies are declared inline (PEP 723) — `uv run` handles resolution automatically
- Do NOT modify or install from a requirements.txt

## Subcommands

### info

Display image metadata as JSON (to stdout).

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py info photo.jpg
```

Output fields: `file`, `format`, `mode`, `width`, `height`, `file_size_bytes`, `dpi`, `n_frames`, `is_animated`, `has_exif`, `has_icc_profile`, `has_alpha`.

### convert

Convert between raster formats. Output format is inferred from the file extension.

```bash
# PNG to JPEG at quality 90
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py convert input.png -o output.jpg --quality 90

# JPEG to lossless WebP
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py convert photo.jpg -o photo.webp --lossless

# PNG with compression level
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py convert input.bmp -o output.png --compress-level 6

# TIFF with LZW compression
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py convert input.png -o output.tiff --tiff-compression tiff_lzw
```

| Flag | Description |
|---|---|
| `--quality N` | JPEG/WebP/HEIC quality (1-100) |
| `--lossless` | Lossless WebP output |
| `--compress-level N` | PNG compression (0-9) |
| `--tiff-compression` | TIFF compression method |

RGBA → JPEG is handled automatically: alpha is composited onto white and stripped. To choose a different background color, run `alpha --mode remove --background COLOR` first.

### alpha

Remove or extract the alpha channel.

```bash
# Remove alpha, composite on white background
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py alpha input.png -o output.png --mode remove

# Remove alpha, composite on red background
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py alpha input.png -o output.png --mode remove --background "#FF0000"

# Extract alpha channel as grayscale mask
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py alpha input.png -o mask.png --mode extract
```

| Flag | Description |
|---|---|
| `--mode remove` | Composite on background color, remove alpha |
| `--mode extract` | Save alpha channel as grayscale image |
| `--background COLOR` | Background color for remove (default: `white`). Hex or named. |

### exif

Read, strip, or auto-orient EXIF metadata.

```bash
# Read EXIF as JSON (stdout)
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py exif photo.jpg --mode read

# Strip EXIF data
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py exif photo.jpg --mode strip -o cleaned.jpg

# Apply EXIF orientation and strip orientation tag
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py exif photo.jpg --mode auto-orient -o oriented.jpg
```

| Flag | Description |
|---|---|
| `--mode read` | Print EXIF tags as JSON to stdout. No `-o` needed. |
| `--mode strip` | Remove all EXIF. Requires `-o`. |
| `--mode auto-orient` | Apply orientation tag, then strip it. Requires `-o`. |

### icc

Strip or convert ICC color profiles. Convert normalizes to sRGB.

```bash
# Strip ICC profile
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py icc input.tiff -o output.tiff --mode strip

# Convert to sRGB with perceptual intent
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py icc input.tiff -o output.png --mode convert

# Convert with relative colorimetric intent
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py icc input.tiff -o output.png --mode convert --intent relative
```

| Flag | Description |
|---|---|
| `--mode strip` | Remove ICC profile |
| `--mode convert` | Convert to sRGB |
| `--intent` | Rendering intent: `perceptual` (default), `relative`, `saturation`, `absolute` |

### split-frames

Split an animated GIF/WebP into individual frame files.

```bash
# Split animated GIF into PNG frames
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py split-frames animation.gif -o ./frames/

# Split into WebP frames
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py split-frames animation.webp -o ./frames/ --format webp
```

Creates numbered frames (`frame_000.png`, `frame_001.png`, ...) and a `frames_info.json` with durations.

| Flag | Description |
|---|---|
| `--format FMT` | Frame output format (default: `png`) |

### assemble-frames

Assemble frame images into an animated GIF or WebP.

```bash
# Assemble frames into GIF with 100ms delay
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py assemble-frames frame_*.png -o animation.gif --delay 100

# Assemble with per-frame durations from JSON
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py assemble-frames frame_*.png -o animation.webp --durations frames_info.json

# Assemble with specific loop count
uv run ${CLAUDE_SKILL_DIR}/scripts/format_io.py assemble-frames frame_*.png -o animation.gif --loop 3
```

| Flag | Description |
|---|---|
| `--delay MS` | Uniform frame delay in ms (default: 100) |
| `--loop N` | Loop count, 0 = infinite (default: 0) |
| `--durations FILE` | JSON file with per-frame durations (array or `{"durations_ms": [...]}`) |

Output must be `.gif` or `.webp`. Requires at least 2 frames. All frames must have the same dimensions.

## Output Conventions

- **Data** (JSON from `info`, `exif read`) → **stdout** — pipe-friendly
- **Messages** (confirmations, warnings) → **stderr**
- **Errors** → stderr with `Error:` prefix, exit code 1

## Anti-patterns

- Do NOT use `convert` for resizing — use the `resize-transform` skill
- Do NOT use `convert` to adjust colors/brightness — use `color-adjust`
- Do NOT manually parse EXIF bytes — use `exif --mode read`
- Do NOT strip alpha by converting RGBA to RGB directly — `convert` auto-composites on white for JPEG; use `alpha --mode remove` if you need a custom background color
- Do NOT convert animated images with `convert` — use `split-frames` / `assemble-frames`
