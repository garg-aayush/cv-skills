# CV Skills - Image Processing Plugin for Claude Code

A Claude Code plugin for image processing — covering both basic image operations and classical computer vision. 42 operations across 7 skills. Will eventually replace the existing `basic-image-editing` skill.

## Project Structure

```
cv-skills/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── format-io/              ✅ implemented
│   │   ├── SKILL.md
│   │   └── scripts/format_io.py
│   ├── svg-convert/            ✅ implemented
│   │   ├── SKILL.md
│   │   └── scripts/svg_convert.py
│   ├── resize-geometry/        ✅ implemented
│   │   ├── SKILL.md
│   │   └── scripts/resize_geometry.py
│   ├── color-adjustment/       ✅ implemented
│   │   ├── SKILL.md
│   │   └── scripts/color_adjustment.py
│   ├── filters-enhancement/    ✅ implemented
│   │   ├── SKILL.md
│   │   └── scripts/filters_enhancement.py
│   ├── segment-morphology/     ✅ implemented
│   │   ├── SKILL.md
│   │   └── scripts/segment_morphology.py
│   └── compositing-blending/   ✅ implemented
│       ├── SKILL.md
│       └── scripts/compositing_blending.py
├── hooks/
│   └── hooks.json
├── scripts/
│   └── check-uv.sh
├── docs/
│   └── future_candidates.md
├── PLAN.md
├── README.md
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
- **PreToolUse hook** — `hooks/hooks.json` registers a Bash pre-hook (`scripts/check-uv.sh`) that blocks `uv run` commands if `uv` is not installed, with install instructions
- **Replaces basic-image-editing** — self-contained, no external skill dependencies

## SKILL.md Conventions

Every SKILL.md must include a "Running Scripts" section with UV rules inline — each skill must be self-contained for plugin distribution (no reliance on this repo's CLAUDE.md).

**Standard block (6 skills):**
```markdown
## Running Scripts

All commands use:

\`\`\`
uv run ${CLAUDE_SKILL_DIR}/scripts/<script>.py <subcommand> [args]
\`\`\`

- Always run with `uv run` — never `python`, `pip install`, or virtualenv activation
- Dependencies are declared inline (PEP 723) — `uv run` handles resolution automatically
- Do NOT modify or install from a requirements.txt
```

**svg-convert block (uses resvg CLI):**
```markdown
## Running Scripts

SVG rendering uses the `resvg` CLI binary (called via subprocess). The Python script handles argument parsing and fallback.

\`\`\`
uv run ${CLAUDE_SKILL_DIR}/scripts/svg_convert.py <subcommand> [args]
\`\`\`

- Always run with `uv run` — never `python`, `pip install`, or virtualenv activation
- Dependencies are declared inline (PEP 723) — `uv run` handles resolution automatically
- Do NOT modify or install from a requirements.txt
- Requires `resvg` on PATH — if missing, the script falls back to cairosvg
```

## Build Order

1. **Skills 1-3** (format-io, svg-convert, resize-geometry) — foundational
2. **Skills 4-5** (color-adjustment, filters-enhancement) — preprocessing pipeline
3. **Skills 6-7** (segment-morphology, compositing-blending) — core CV operations

## Plan Reference

See `PLAN.md` for the full v1 specification (42 operations) and `docs/future_candidates.md` for v2+ candidates.
