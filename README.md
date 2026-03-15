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

| Skill | Ops | What it covers |
|---|---|---|
| **format-io** | 6 | Format conversion, alpha channels, EXIF, ICC profiles, animated frames |
| **svg-convert** | 3 | SVG to raster (PNG/JPEG/WebP), metadata inspection, scaled rendering |
| **resize-geometry** | 6 | Resize, crop, auto-crop, pad, rotate/flip, montage grids |
| **color-adjustment** | 9 | Tone, saturation, grayscale, invert, color spaces, channels, histograms |
| **filters-enhancement** | 4 | Blur, bilateral filter, sharpen, denoise |
| **segment-morphology** | 7 | Threshold, edge detection, morphology, contours, color segmentation, GrabCut |
| **compositing-blending** | 4 | Composite/blend, watermark, image diff, background removal |

## How It Works

Every script uses [PEP 723](https://peps.python.org/pep-0723/) inline dependency declarations and runs with `uv run` — no pip install, no virtualenv, no setup. Dependencies are resolved automatically on first run.

Just describe what you need — Claude picks the right skill and operations automatically.

## License

MIT
