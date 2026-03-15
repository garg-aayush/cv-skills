# CV Skills - Image Processing Plugin for Claude Code

A Claude Code plugin for image processing — covering both basic image operations and classical computer vision. 42 operations across 7 skills. Will eventually replace the existing `basic-image-editing` skill.

## Project Structure

```
cv-skills/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   ├── format-io/
│   │   ├── SKILL.md
│   │   └── scripts/format_io.py
│   ├── svg-convert/
│   │   ├── SKILL.md
│   │   └── scripts/svg_convert.py
│   ├── resize-geometry/
│   │   ├── SKILL.md
│   │   └── scripts/resize_geometry.py
│   ├── color-adjustment/
│   │   ├── SKILL.md
│   │   └── scripts/color_adjustment.py
│   ├── filters-enhancement/
│   │   ├── SKILL.md
│   │   └── scripts/filters_enhancement.py
│   ├── segment-morphology/
│   │   ├── SKILL.md
│   │   └── scripts/segment_morphology.py
│   └── compositing-blending/
│       ├── SKILL.md
│       └── scripts/compositing_blending.py
├── scripts/
│   └── UV_RULES.md
├── requirements.txt             # reference only — not needed for running
├── plugin_plan.md
├── future_candidates.md
└── CLAUDE.md
```

## Runtime

UV-only workflow — no `pip install`, no virtualenv. Every script uses PEP 723 inline deps and runs with `uv run scripts/X.py`. SVG conversion uses resvg CLI binary (subprocess) with cairosvg as fallback.

## Skills Overview

| Skill | Ops | What it covers |
|---|---|---|
| format-io | 6 | Format conversion, alpha, EXIF, ICC, animated frames |
| svg-convert | 3 | SVG → raster (PNG/JPEG/WebP), scaling, background |
| resize-geometry | 6 | Resize, crop, auto-crop, pad, rotate/flip, montage |
| color-adjustment | 9 | Tone, saturation, grayscale, color spaces, channels, histograms |
| filters-enhancement | 4 | Blur, bilateral filter, sharpen, denoise |
| segment-morphology | 7 | Threshold, edges, morphology, contours, color segmentation, GrabCut |
| compositing-blending | 4 | Composite/blend, watermark, image diff, background removal |

## Key Design Decisions

- **UV-only** — PEP 723 inline deps, `uv run` for everything, no pip install
- **Plugin format** — `.claude-plugin/plugin.json` + `marketplace.json`
- **One script per skill** — argparse subcommands, self-contained deps
- **Consistent CLI** — `uv run scripts/X.py <subcommand> INPUT -o OUTPUT [--params]`
- **Strict errors** — reject bad input with actionable messages, no silent auto-conversion
- **SVG: resvg CLI + cairosvg fallback** — prerequisite check on first use
- **BGR↔RGB conversion** at boundaries between OpenCV and Pillow
- **Replaces basic-image-editing** — self-contained, no external skill dependencies

## Build Order

1. **Skills 1-3** (format-io, svg-convert, resize-geometry) — foundational
2. **Skills 4-5** (color-adjustment, filters-enhancement) — preprocessing pipeline
3. **Skills 6-7** (segment-morphology, compositing-blending) — core CV operations

## Plan Reference

See `plugin_plan.md` for the full v1 specification (42 operations) and `docs/future_candidates.md` for v2+ candidates.
