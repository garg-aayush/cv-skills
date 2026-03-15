# cv-skills

A Claude Code plugin for image processing — 42 operations across 7 skills covering basic image operations and classical computer vision.

## Install

```bash
# From marketplace
/plugin marketplace add aayushgarg/cv-skills
/plugin install cv-skills@cv-skills

# Or load from local directory
claude --plugin-dir ./cv-skills
```

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager (required for all skills)
- [resvg](https://github.com/RazrFalcon/resvg/releases) — SVG renderer (recommended for svg-convert; falls back to cairosvg)

Pre-use hooks automatically check for these and provide install instructions if missing.

## Skills

| Skill | Ops | Subcommands |
|---|---|---|
| **format-io** | 6 | `info` `convert` `alpha` `exif` `icc` `split-frames` `assemble-frames` |
| **svg-convert** | 3 | `info` `render` `resize-render` |
| **resize-geometry** | 6 | `resize` `crop` `auto-crop` `pad` `rotate` `montage` |
| **color-adjustment** | 9 | `tone` `saturation` `grayscale` `invert` `colorspace` `channel` `histogram` `equalize` `auto-levels` |
| **filters-enhancement** | 4 | `blur` `bilateral` `sharpen` `denoise` |
| **segment-morphology** | 7 | `threshold` `canny` `gradient` `morphology` `contours` `color-segment` `grabcut` |
| **compositing-blending** | 4 | `composite` `watermark` `diff` `remove-bg` |

## Quick Examples

```bash
# Get image info
uv run skills/format-io/scripts/format_io.py info photo.jpg

# Convert PNG to JPEG
uv run skills/format-io/scripts/format_io.py convert input.png -o output.jpg --quality 90

# Render SVG to PNG at 2x
uv run skills/svg-convert/scripts/svg_convert.py resize-render logo.svg -o logo@2x.png --scale 2

# Resize to 50%
uv run skills/resize-geometry/scripts/resize_geometry.py resize photo.png -o thumb.png --percent 50

# Adjust brightness and contrast
uv run skills/color-adjustment/scripts/color_adjustment.py tone photo.png -o bright.png --brightness 1.3 --contrast 1.2

# Gaussian blur
uv run skills/filters-enhancement/scripts/filters_enhancement.py blur photo.png -o blurred.png --method gaussian --sigma 2

# Edge detection
uv run skills/segment-morphology/scripts/segment_morphology.py canny photo.png -o edges.png

# Add text watermark
uv run skills/compositing-blending/scripts/compositing_blending.py watermark photo.png -o marked.png --text "DRAFT"
```

## How It Works

Every script uses [PEP 723](https://peps.python.org/pep-0723/) inline dependency declarations and runs with `uv run` — no pip install, no virtualenv, no setup. Dependencies are resolved automatically on first run.

Each skill is a single Python script with argparse subcommands following a consistent CLI pattern:

```
uv run scripts/<skill>.py <subcommand> INPUT -o OUTPUT [--params]
```

## License

MIT
