# CV Skills - Image Processing Plugin for Claude Code

Skills for performing classical image processing operations: format conversion, SVG rendering, resize/crop/rotate, color adjustment, filters, segmentation/morphology, and compositing/blending.

## Project Structure

```
cv-skills/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   ├── image-format/
│   │   ├── SKILL.md
│   │   └── scripts/format_io.py
│   ├── svg-convert/
│   │   ├── SKILL.md
│   │   └── scripts/svg_convert.py
│   ├── resize-transform/
│   │   ├── SKILL.md
│   │   └── scripts/resize_geometry.py
│   ├── color-adjust/
│   │   ├── SKILL.md
│   │   └── scripts/color_adjustment.py
│   ├── image-filters/
│   │   ├── SKILL.md
│   │   └── scripts/filters_enhancement.py
│   ├── edges-masks/
│   │   ├── SKILL.md
│   │   └── scripts/segment_morphology.py
│   └── image-combine/
│       ├── SKILL.md
│       └── scripts/compositing_blending.py
├── hooks/
│   └── hooks.json
├── scripts/
│   ├── check-uv.sh
│   └── check-svg-renderer.sh
├── docs/
│   └── future_candidates.md
├── PLAN.md
├── README.md
├── LICENSE
└── CLAUDE.md
```

## Runtime

UV-only workflow — no `pip install`, no virtualenv. Every script uses PEP 723 inline deps and runs with `uv run scripts/X.py`. SVG conversion uses resvg CLI binary (subprocess) with cairosvg as fallback.

## Skills Overview

| Skill | Ops | What it covers |
|---|---|---|
| image-format | 6 | Format conversion, alpha, EXIF, ICC, animated frames |
| svg-convert | 3 | SVG → raster (PNG/JPEG/WebP), scaling, background |
| resize-transform | 6 | Resize, crop, auto-crop, pad, rotate/flip, montage |
| color-adjust | 9 | Tone, saturation, grayscale, color spaces, channels, histograms |
| image-filters | 4 | Blur, bilateral filter, sharpen, denoise |
| edges-masks | 7 | Threshold, edges, morphology, contours, color segmentation, GrabCut |
| image-combine | 4 | Composite/blend, watermark, image diff, background removal |

## Key Design Decisions

- **UV-only** — PEP 723 inline deps, `uv run` for everything, no pip install
- **Plugin format** — `.claude-plugin/plugin.json` + `marketplace.json`
- **One script per skill** — argparse subcommands, self-contained deps
- **Consistent CLI** — `uv run scripts/X.py <subcommand> INPUT -o OUTPUT [--params]`
- **Strict errors** — reject bad input with actionable messages, no silent auto-conversion
- **SVG: resvg CLI + cairosvg fallback** — prerequisite check on first use
- **BGR↔RGB conversion** at boundaries between OpenCV and Pillow
- **PreToolUse hooks** — `hooks/hooks.json` registers two Bash pre-hooks: `check-uv.sh` blocks all `uv run` commands if `uv` is missing; `check-svg-renderer.sh` blocks svg-convert render/resize-render if neither resvg nor cairosvg is available (skips `info` which needs no renderer)
- **Self-contained** — no external skill dependencies

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

## Plan Reference

See `PLAN.md` for the full v1 specification (42 operations) and `docs/future_candidates.md` for v2+ candidates.
