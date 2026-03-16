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
├── images/
│   ├── test.png
│   ├── test.jpeg
│   ├── test.svg
│   ├── TEST_PROMPTS.md
│   └── out/              # test outputs (gitignored)
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
| image-format | 7 | Format conversion, alpha, EXIF, ICC, animated frames |
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
- **Graceful auto-conversion** — handle predictable format mismatches automatically (e.g., RGBA→JPEG strips alpha onto white) with an info message; reject truly invalid input with actionable errors
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

## Testing

### Test Assets

Test images live in `images/` with outputs written to `images/out/`:

| File | Description |
|---|---|
| `images/test.png` | Santa hat with "GRACIE" text, transparent background, 5000x5000 |
| `images/test.jpeg` | "Big sister" grinch art, beige background, 696x602 |
| `images/test.svg` | Hello Kitty vector graphic, 673x901 (viewBox 1530x2048) |

### Test Prompts

`images/TEST_PROMPTS.md` contains 45 natural-language prompts (numbered 1-45) covering all 7 skills. Each prompt is written as a user would type it into Claude Code. The expected skill is noted in brackets — don't include that part when testing.

**Structure:**
- Tests 1-5: image-format
- Tests 6-8: svg-convert
- Tests 9-15: resize-transform
- Tests 16-21: color-adjust
- Tests 22-25: image-filters
- Tests 26-31: edges-masks
- Tests 32-35: image-combine
- Tests 36-45: ambiguous/boundary cases (correct skill routing)

### Two Testing Modes

#### Mode 1: Script testing (direct invocation)

Tests that the scripts produce correct output, CLI flags work as documented, and error messages are actionable.

Invoke scripts directly using repo-relative paths (since `${CLAUDE_SKILL_DIR}` only resolves at skill runtime):

```bash
uv run skills/<skill-name>/scripts/<script>.py <subcommand> [args]
```

For each test:
1. Read the test prompt from `TEST_PROMPTS.md` and translate it to the correct script + subcommand + flags
2. Run the command
3. Check exit code and stderr for errors
4. Read the output image to visually verify correctness
5. Compare against the input image to confirm the operation applied as expected

Some tests require multi-step workflows (e.g., resizing before assembling frames with mismatched dimensions). This is expected — the scripts give actionable error messages that guide the next step.

#### Mode 2: Skill routing (natural-language prompts)

Tests that Claude picks the correct skill from a natural-language prompt and translates user intent into the right subcommand and flags. This is what the prompts in `TEST_PROMPTS.md` are primarily written for.

To run: copy-paste each prompt from `TEST_PROMPTS.md` into Claude Code verbatim (without the bracketed skill hint). Then verify:
1. Claude triggered the **correct skill** (especially important for tests 36-45)
2. Claude chose the right **subcommand and flags** for the user's intent
3. The output image is correct

Mode 2 is the end-to-end test — it validates SKILL.md descriptions, frontmatter trigger/exclusion rules, and Claude's parameter mapping all at once.

### Maintaining Test Prompts

When adding or changing a skill operation:
1. Add a test prompt to the appropriate section in `images/TEST_PROMPTS.md`
2. For new ambiguous cases, add a boundary test in the "Ambiguous / boundary cases" section
3. Run the new test to verify it works
4. If the prompt touches a boundary between two skills, document which skill is correct and why

## Plan Reference

See `PLAN.md` for the full v1 specification (42 operations) and `docs/future_candidates.md` for v2+ candidates.
