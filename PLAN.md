# cv-skills Plugin Plan

A Claude Code **plugin** for image processing — covering both basic image operations and classical computer vision. This plugin will eventually **replace** the existing `basic-image-editing` skill, providing a comprehensive, self-contained image processing toolkit.

**Target users:** People working in image processing, segmentation, ML dataset preparation, and image generation. Not a full CV replacement — focused on the most commonly used operations.

**Format:** Plugin with `plugin.json` + `marketplace.json`, namespaced skills (e.g., `/cv-skills:resize`, `/cv-skills:canny`).

**Status:** Planning phase. Will iterate on this plan, review best practices and other plugins, then build.

---

## Plugin Structure

```
cv-skills/
├── .claude-plugin/
│   ├── plugin.json              # plugin metadata (name, version, author, license, keywords)
│   └── marketplace.json         # skill listing for marketplace distribution
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
│   └── UV_RULES.md              # UV-only workflow rules for all scripts
├── requirements.txt             # reference only — not needed for running scripts
├── PLAN.md
└── CLAUDE.md
```

## Dependencies & Runtime

### UV-Only Workflow (no pip install, no virtualenv)

All scripts use PEP 723 inline dependency declarations and are run with `uv run`:

```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "opencv-python-headless", "numpy"]
# ///
```

Rules (inspired by [Hugging Face Skills UV_RULES.md](https://github.com/huggingface/skills)):
1. Every script declares its own deps inline via PEP 723
2. Always run with `uv run scripts/X.py`, never `python` or `pip install`
3. No `.venv` activation needed — `uv run` handles everything
4. `requirements.txt` exists as a human reference only, not for runtime

### Per-Skill Dependencies

| Skill | PEP 723 deps |
|---|---|
| format-io | `pillow`, `pillow-heif`, `numpy` |
| svg-convert | `pillow` (resvg CLI binary called via subprocess; cairosvg as fallback) |
| resize-geometry | `pillow`, `numpy` |
| color-adjustment | `pillow`, `opencv-python-headless`, `numpy` |
| filters-enhancement | `pillow`, `opencv-python-headless`, `numpy` |
| segment-morphology | `opencv-python-headless`, `numpy` |
| compositing-blending | `pillow`, `opencv-python-headless`, `numpy` |

### SVG Conversion: resvg + cairosvg Fallback

The `svg-convert` skill uses a two-tier approach:
- **Primary: resvg CLI** — Pre-built binary (Rust-based, high-quality rendering, handles fonts/filters well). Called via subprocess, not Python bindings.
- **Fallback: cairosvg** — Python package via `uv run`, for systems where resvg is not installed and libcairo2 is available (most Linux distros).
- **Hook on first use**: Check if `resvg` binary is on PATH → if missing, guide user to install pre-built binary from [resvg GitHub releases](https://github.com/RazrFalcon/resvg/releases). If resvg unavailable and cairosvg works, use that instead.

---

## Skill 1: `format-io` — Format & I/O (6 operations)

Everything about reading, writing, and converting raster image files.

| # | Operation | Description | Library |
|---|---|---|---|
| 1 | Image info | Display dimensions, format, file size, color mode, DPI | Pillow |
| 2 | Format conversion | PNG ↔ JPEG ↔ WebP ↔ TIFF ↔ BMP ↔ HEIC with quality/compression control (JPEG quality, WebP lossy/lossless, PNG compression level) | Pillow |
| 3 | Alpha handling | Remove transparency (composite on color), extract alpha channel | Pillow |
| 4 | EXIF handling | Read metadata, strip metadata, and auto-orient (apply EXIF orientation tag and strip) | Pillow |
| 5 | ICC profile handling | Strip or convert color profiles (sRGB normalization) | Pillow |
| 6 | Animated GIF/WebP frames | Split into individual frames, or assemble frames into animated GIF/WebP with delay control | Pillow |

---

## Skill 2: `svg-convert` — SVG to Raster Conversion (3 operations)

Vector-to-raster conversion — separate skill because SVG handling requires external tools (resvg binary or system libcairo2) and deals with vector images, not pixel data. Inspired by [aayushgarg.dev/tools/svg-viewer](https://aayushgarg.dev/tools/svg-viewer.html).

| # | Operation | Description | Renderer |
|---|---|---|---|
| 1 | SVG info | Display SVG dimensions, viewBox, file size, element count (paths, text, groups) | XML parsing (stdlib) |
| 2 | SVG → raster | Convert SVG to PNG (default), JPEG, or WebP. Options: quality for lossy formats, background color (especially for JPEG when SVG has transparency) | resvg CLI → cairosvg fallback |
| 3 | SVG resize render | Render SVG at scale factor (1x, 2x, 3x, 4x) or custom width/height with aspect ratio lock | resvg CLI → cairosvg fallback |

---

## Skill 3: `resize-geometry` — Resize & Geometry (6 operations)

Spatial transformations — changing dimensions, orientation, and layout.

| # | Operation | Description | Library |
|---|---|---|---|
| 1 | Resize | By dimensions, percentage, or fit-within bounds. Resampling control (nearest, bilinear, bicubic, Lanczos). Aspect ratio lock. Also serves as thumbnail generation (fit-within + aspect preserve) | Pillow |
| 2 | Crop | By box coordinates (x1,y1,x2,y2) or by aspect ratio constraint with presets (free, 1:1, 4:3, 16:9, 2:1) | Pillow |
| 3 | Auto-crop / trim | Remove uniform borders (whitespace, solid color, transparency) | Pillow |
| 4 | Pad / letterbox | Add padding to reach target size with fill color | Pillow |
| 5 | Rotate / Flip | Rotate by any angle with fill control, flip horizontal or vertical | Pillow |
| 6 | Montage / grid | Combine multiple images into a grid layout | Pillow |

---

## Skill 4: `color-adjustment` — Color & Adjustment (9 operations)

Color manipulation, tone adjustments, channel operations, and histogram analysis. _(Sharpness moved to filters-enhancement.)_

| # | Operation | Description | Library |
|---|---|---|---|
| 1 | Tone adjustment | Brightness (linear shift), contrast (range expand/compress), and gamma correction (non-linear curve) | Pillow/OpenCV/numpy |
| 2 | Saturation | Increase/decrease color intensity | Pillow |
| 3 | Grayscale | RGB → luminance (with BT.601/BT.709 control) | OpenCV |
| 4 | Invert / negative | 255 - value per channel | OpenCV |
| 5 | Color space conversion | RGB ↔ HSV ↔ LAB ↔ YCbCr ↔ BGR | OpenCV |
| 6 | Channel split / merge | Extract or replace individual channels | OpenCV |
| 7 | Histogram computation | Compute and export grayscale/color pixel intensity distribution | OpenCV |
| 8 | Histogram equalization | Global equalization or CLAHE (adaptive/local) for contrast improvement | OpenCV |
| 9 | Auto-levels | Stretch histogram to full range per channel | numpy |

---

## Skill 5: `filters-enhancement` — Filters & Enhancement (4 operations)

Spatial filtering, noise reduction, and sharpening.

| # | Operation | Description | Library |
|---|---|---|---|
| 1 | Blur | Gaussian (sigma control), box (uniform averaging), or median (salt-and-pepper noise removal) | OpenCV/Pillow |
| 2 | Bilateral filter | Edge-preserving smoothing (separate from blur — fundamentally different algorithm) | OpenCV |
| 3 | Sharpen | Basic (ImageEnhance), unsharp mask, or Laplacian edge-enhancing sharpness | Pillow/OpenCV |
| 4 | Denoise (non-local means) | Photo noise reduction (color + grayscale) | OpenCV |

---

## Skill 6: `segment-morphology` — Segmentation & Morphology (7 operations)

Thresholding, edge detection, morphological operations, masking, and segmentation — merged into one skill because these are almost always chained together in pipelines (threshold → morphology cleanup → mask/contour extraction).

| # | Operation | Description | Library |
|---|---|---|---|
| 1 | Threshold | Binary split: fixed value, Otsu (auto-calculated), or adaptive (local block-based for uneven lighting) | OpenCV |
| 2 | Canny edge detection | Clean edges with hysteresis threshold control | OpenCV |
| 3 | Gradient edge detection | Sobel (directional X/Y/magnitude) or Laplacian (second-derivative) edge maps | OpenCV |
| 4 | Morphological operations | Erosion, dilation, opening, closing, or morphological gradient. Kernel size/shape control | OpenCV |
| 5 | Contour extraction | Find and draw object boundaries (with area filtering) | OpenCV |
| 6 | Color-based segmentation | Mask pixels within HSV/LAB range | OpenCV |
| 7 | GrabCut | Foreground extraction with bounding box | OpenCV |

---

## Skill 7: `compositing-blending` — Compositing & Blending (4 operations)

Multi-image operations — combining, comparing, and assembling.

| # | Operation | Description | Library |
|---|---|---|---|
| 1 | Composite / blend | Alpha composite (RGBA layers), weighted blend (crossfade by ratio), or paste/overlay at position (x, y) | Pillow |
| 2 | Watermark | Add text or image watermark with opacity | Pillow |
| 3 | Image diff | Highlight pixel differences between two images | numpy |
| 4 | Background removal | Generate mask via GrabCut, apply as alpha | OpenCV+Pillow |

---

## Summary

| Skill | Operations | Primary Libraries |
|---|---|---|
| format-io | 6 | Pillow |
| svg-convert | 3 | resvg CLI + cairosvg fallback |
| resize-geometry | 6 | Pillow |
| color-adjustment | 9 | Pillow, OpenCV, numpy |
| filters-enhancement | 4 | OpenCV, Pillow |
| segment-morphology | 7 | OpenCV |
| compositing-blending | 4 | Pillow, OpenCV, numpy |
| **Total** | **42** | |

## Future Version Candidates

See `docs/future_candidates.md` for the full list of operations deferred to v2+.

## Suggested Build Order

1. **Skills 1-3** (format-io, svg-convert, resize-geometry) — foundational, replaces basic-image-editing
2. **Skills 4-5** (color-adjustment, filters-enhancement) — preprocessing pipeline
3. **Skills 6-7** (segment-morphology, compositing-blending) — core CV operations

## Design Decisions

- **UV-only workflow** — PEP 723 inline deps, `uv run` for all scripts, no `pip install` or virtualenv (inspired by [HF Skills](https://github.com/huggingface/skills))
- **Plugin format** — `.claude-plugin/plugin.json` + `marketplace.json` with namespaced skills
- **One script per skill** — argparse subcommands, self-contained PEP 723 deps
- **Consistent CLI** — `uv run scripts/X.py INPUT -o OUTPUT --operation [--params]`
- **BGR↔RGB conversion** at boundaries between OpenCV and Pillow
- **SVG: resvg CLI + cairosvg fallback** — resvg binary via subprocess (primary), cairosvg Python package (fallback). Prerequisite check on first use.
- **Replaces basic-image-editing** — self-contained, no external skill dependencies
- **SKILL.md writing principles** (from [evals-skills](https://github.com/hamelsmu/evals-skills)):
  - Write directives, not wisdom — the agent knows what OpenCV is
  - Frontmatter descriptions with triggers AND exclusions ("Use when X. Do NOT use when Y.")
  - Concrete CLI examples as primary documentation
  - Anti-patterns section (concise one-liners)
  - Under 500 lines per SKILL.md

## Reference Links

### Plugin & Skill Best Practices
- [Anthropic Plugins Guide](https://docs.anthropic.com/en/docs/claude-code/plugins) — official guide for plugin structure, plugin.json manifest, testing, distribution
- [Anthropic Plugins Reference](https://docs.anthropic.com/en/docs/claude-code/plugins-reference) — full manifest schema, directory structure, debugging
- [Anthropic Skills Guide](https://docs.anthropic.com/en/docs/claude-code/skills) — official guide for SKILL.md authoring, progressive disclosure, naming
- [Hugging Face Skills](https://github.com/huggingface/skills) — UV_RULES.md, PEP 723 script pattern, marketplace.json, SKILL.md structure
- [Evals Skills (Hamel Husain)](https://github.com/hamelsmu/evals-skills) — meta-skill.md writing principles ("directives not wisdom"), frontmatter with triggers + exclusions

### OpenCV & Image Processing Tutorials
- [OpenCV Python Tutorials (GeeksforGeeks)](https://www.geeksforgeeks.org/python/opencv-python-tutorial/) — comprehensive operation reference
- [OpenCV Tutorial: Basic to Advanced (Kaggle)](https://www.kaggle.com/code/talhabu/opencv-tutorial-from-basic-to-advanced) — local copy at `/Users/aayushgarg/Downloads/opencv-tutorial-from-basic-to-advanced.ipynb`
- [OpenCV Official Imgproc Tutorials](https://docs.opencv.org/4.x/d7/da8/tutorial_table_of_content_imgproc.html)

### SVG Conversion
- [SVG Viewer & Converter (aayushgarg.dev)](https://aayushgarg.dev/tools/svg-viewer.html) — design reference for svg-convert skill (format, scale, background options)
- [resvg GitHub releases](https://github.com/RazrFalcon/resvg/releases) — pre-built CLI binaries
- [cairosvg on PyPI](https://pypi.org/project/cairosvg/) — fallback renderer

### Image Operations Design Reference
- [Image Resizer (aayushgarg.dev)](https://aayushgarg.dev/tools/image-resizer.html) — resize modes (dimensions, percentage, fit-within), aspect ratio lock
- [Image Cropper (aayushgarg.dev)](https://aayushgarg.dev/tools/image-cropper.html) — freeform + aspect ratio presets
- [Image Operations (aayushgarg.dev)](https://aayushgarg.dev/tools/image-operations.html) — brightness, contrast, grayscale, invert, flip/rotate

---

## Resolved Items

- [x] ~~Review reference plugins for best practices~~ — Reviewed [HF Skills](https://github.com/huggingface/skills) and [evals-skills](https://github.com/hamelsmu/evals-skills)
- [x] ~~SVG library choice~~ — resvg CLI (primary) + cairosvg (fallback)
- [x] ~~CLI interface pattern~~ — **Subcommands** (e.g., `uv run script.py blur INPUT -o OUT --sigma 2`). Each operation is a subcommand with its own params and `--help`. Matches HF datasets pattern.
- [x] ~~Error handling~~ — **Strict with helpful errors**. Reject bad input with actionable messages (e.g., `"Error: Expected grayscale image, got RGB. Run color-adjustment grayscale first."`). No silent auto-conversion.

