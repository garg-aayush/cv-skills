---
name: svg-convert
description: >
  Convert SVG files to raster formats (PNG/JPEG/WebP), inspect SVG metadata,
  and render at custom scales or dimensions. Use when the task involves SVG
  rendering, SVG-to-raster conversion, or SVG inspection. Do NOT use for
  raster-to-raster conversion (use format-io) or raster image editing.
---

# svg-convert

SVG to raster conversion, SVG metadata inspection, and scaled rendering.

## Prerequisites

- `uv` on PATH
- `resvg` on PATH (recommended) — or system libcairo2 for cairosvg fallback

## Running Scripts

SVG rendering uses the `resvg` CLI binary (called via subprocess). The Python script handles argument parsing and fallback.

```
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py <subcommand> [args]
```

- Always run with `uv run` — never `python`, `pip install`, or virtualenv activation
- Dependencies are declared inline (PEP 723) — `uv run` handles resolution automatically
- Do NOT modify or install from a requirements.txt
- Requires `resvg` on PATH — if missing, the script falls back to cairosvg

## Subcommands

### info

Display SVG metadata as JSON (to stdout). Uses XML parsing — no renderer needed.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py info logo.svg
```

Output fields: `file`, `file_size_bytes`, `width`, `height`, `viewBox`, `total_elements`, `element_counts`.

### render

Render SVG to a raster format. Output format is inferred from the file extension.

```bash
# SVG to PNG (default)
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py render logo.svg -o logo.png

# SVG to JPEG with white background (auto)
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py render logo.svg -o logo.jpg

# SVG to JPEG with custom background
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py render logo.svg -o logo.jpg --background "#FF0000"

# SVG to WebP at quality 90
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py render logo.svg -o logo.webp --quality 90
```

| Flag | Description |
|---|---|
| `--format FMT` | Override output format (`png`, `jpg`, `webp`) |
| `--quality N` | Quality for JPEG/WebP (1-100) |
| `--background COLOR` | Background color (hex or named). Default: `white` for JPEG. |

### resize-render

Render SVG at a scale factor or custom pixel dimensions. Aspect ratio is preserved when only one dimension is given.

```bash
# Render at 2x scale
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py resize-render icon.svg -o icon_2x.png --scale 2

# Render at 0.5x (half size)
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py resize-render icon.svg -o icon_half.png --scale 0.5

# Render at specific width (height auto-calculated)
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py resize-render banner.svg -o banner.png --width 1200

# Render at exact dimensions
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py resize-render icon.svg -o icon.png --width 512 --height 512

# Render 3x to JPEG with background
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py resize-render logo.svg -o logo_3x.jpg --scale 3 --background white
```

| Flag | Description |
|---|---|
| `--scale N` | Scale factor (e.g., `2.0` for 2x). Cannot combine with `--width`/`--height`. |
| `--width W` | Target width in pixels. Height auto-calculated if omitted. |
| `--height H` | Target height in pixels. Width auto-calculated if omitted. |
| `--background COLOR` | Background color (hex or named). Default: `white` for JPEG. |

## Output Conventions

- **Data** (JSON from `info`) -> **stdout** -- pipe-friendly
- **Messages** (renderer choice, file saved) -> **stderr**
- **Errors** -> stderr with `Error:` prefix, exit code 1

## Anti-patterns

- Do NOT use this skill for raster-to-raster conversion -- use the `format-io` skill
- Do NOT use this skill to resize raster images -- use the `resize-geometry` skill
- Do NOT combine `--scale` with `--width`/`--height` in `resize-render` -- use one or the other
- Do NOT assume SVG has width/height attributes -- check with `info` first if dimensions are needed
- Do NOT use `render` when you need a specific output size -- use `resize-render` with `--scale` or `--width`/`--height`
