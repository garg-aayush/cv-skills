---
name: image-combine
description: Composite, blend, overlay, and paste images together; add text or image watermarks; compute visual difference maps; remove backgrounds. Use when the user wants to combine or layer two images, create a watermark, compare two images for differences, merge photos, or remove a background to produce a transparent PNG cutout. Do NOT use for arranging images in a grid (use resize-transform montage) or for edge/contour analysis (use edges-masks).
user_invocable: true
---

# image-combine

Composite, blend, watermark, diff, and background removal for images.

## Prerequisites

- `uv` on PATH

## Running Scripts

All commands use:

```
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py <subcommand> [args]
```

- Always run with `uv run` — never `python`, `pip install`, or virtualenv activation
- Dependencies are declared inline (PEP 723) — `uv run` handles resolution automatically
- Do NOT modify or install from a requirements.txt

## Subcommands

### composite

Alpha composite, blend, or paste two images together.

```bash
# Alpha composite (both images become RGBA, overlay on base)
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py composite base.png overlay.png -o result.png --mode alpha

# Weighted blend (50/50 crossfade)
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py composite img1.png img2.png -o blended.png --mode blend --ratio 0.5

# Blend favoring image2 (30% img1, 70% img2)
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py composite img1.jpg img2.jpg -o blended.jpg --mode blend --ratio 0.7

# Paste overlay at specific position
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py composite base.png overlay.png -o result.png --mode paste --position 100,50
```

| Flag | Description |
|---|---|
| `--mode alpha` | Alpha composite — both images converted to RGBA, overlay composited on base. Same size required. |
| `--mode blend` | Weighted blend — crossfade between two images. Same size and mode required. |
| `--mode paste` | Paste overlay onto base at position. Overlay alpha used as mask if present. |
| `--ratio F` | Blend ratio for `--mode blend` (0.0 = all image1, 1.0 = all image2, default: 0.5) |
| `--position x,y` | Paste position for `--mode paste` (default: 0,0) |

**Notes:**
- `alpha` and `blend` require both images to be the same size. Resize first with resize-transform.
- `alpha` mode output is RGBA — use PNG or WebP as output format (not JPEG).
- `paste` mode preserves the base image's mode. If overlay has alpha, it is used as a transparency mask.

### watermark

Add a text or image watermark with opacity control.

```bash
# Text watermark in bottom-right corner
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py watermark photo.jpg -o marked.jpg --text "Copyright 2024"

# Text watermark centered, larger font, more opaque
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py watermark photo.png -o marked.png --text "DRAFT" --position center --font-size 72 --opacity 0.5

# Image watermark in top-right
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py watermark photo.jpg -o marked.jpg --image logo.png --position top-right --opacity 0.4

# Image watermark at explicit coordinates
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py watermark photo.png -o marked.png --image logo.png --position 200,100 --opacity 0.3
```

| Flag | Description |
|---|---|
| `--text TEXT` | Text watermark string (mutually exclusive with `--image`) |
| `--image FILE` | Image watermark file path (mutually exclusive with `--text`) |
| `--opacity F` | Watermark opacity (0.0-1.0, default: 0.3) |
| `--position POS` | Position: `center`, `top-left`, `top-right`, `bottom-left`, `bottom-right`, or `x,y` (default: `bottom-right`) |
| `--font-size N` | Font size for text watermark (default: 24) |

**Notes:**
- One of `--text` or `--image` is required (mutually exclusive).
- Image watermarks are auto-resized if larger than the base image.
- Text watermarks use white text with the specified opacity on an RGBA overlay layer.

### diff

Compute a pixel difference map between two images.

```bash
# Basic difference map
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py diff before.png after.png -o diff.png

# Amplified difference (10x) to make subtle changes visible
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py diff img1.png img2.png -o diff.png --amplify 10

# Thresholded difference (ignore changes below 20)
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py diff img1.png img2.png -o diff.png --threshold 20

# Amplified and thresholded
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py diff img1.jpg img2.jpg -o diff.png --amplify 5 --threshold 10
```

| Flag | Description |
|---|---|
| `--amplify N` | Multiply differences by N to increase visibility (default: 1) |
| `--threshold N` | Set pixels with difference below N to 0 (default: 0) |

**Notes:**
- Both images must be the same size. Resize first with resize-transform if needed.
- RGBA images are compared as RGB (alpha channel ignored).
- Output is the absolute per-pixel difference, clipped to 0-255.

### remove-bg

Remove background using OpenCV GrabCut algorithm.

```bash
# Remove background with foreground bounding box
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py remove-bg photo.jpg -o cutout.png --rect 50,30,400,500

# More iterations for better accuracy
uv run ${CLAUDE_SKILL_DIR}/scripts/compositing_blending.py remove-bg photo.png -o cutout.png --rect 10,10,300,400 --iterations 10
```

| Flag | Description |
|---|---|
| `--rect x,y,w,h` | Foreground bounding box (required). Must be within image bounds. |
| `--iterations N` | GrabCut iterations (default: 5). More iterations = better but slower. |

**Notes:**
- Output must be PNG or WebP (RGBA format with alpha mask). JPEG is not supported.
- The `--rect` defines the region containing the foreground object. GrabCut refines the mask within this region.
- Larger `--iterations` values improve accuracy at the cost of speed.

## Output Conventions

- **Messages** (confirmations, warnings) -> **stderr**
- **Errors** -> stderr with `Error:` prefix, exit code 1
- Image output is written to the path specified by `-o`/`--output`

## Anti-patterns

- Do NOT use `composite --mode blend` to resize images — use the `resize-transform` skill first, then blend
- Do NOT use `remove-bg` for edge detection — use `edges-masks` for Canny/Sobel edges
- Do NOT use `diff` for color comparison — it computes per-pixel absolute difference, not perceptual similarity
- Do NOT save `remove-bg` output as JPEG — JPEG does not support alpha. Use PNG or WebP.
- Do NOT use `watermark` for compositing two full images — use `composite` instead
- Do NOT assume `composite --mode alpha` handles different-sized images — both must be the same size
