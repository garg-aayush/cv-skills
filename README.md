# cv-skills

A Claude Code plugin for image processing — covering both basic image operations and classical computer vision. 42 operations across 7 skills.

## Skills

| Skill | Operations | Description |
|---|---|---|
| `format-io` | 6 | Format conversion, alpha, EXIF, ICC, animated frames |
| `svg-convert` | 3 | SVG to raster (PNG/JPEG/WebP), scaling, background |
| `resize-geometry` | 6 | Resize, crop, auto-crop, pad, rotate/flip, montage |
| `color-adjustment` | 9 | Tone, saturation, grayscale, color spaces, channels, histograms |
| `filters-enhancement` | 4 | Blur, bilateral filter, sharpen, denoise |
| `segment-morphology` | 7 | Threshold, edges, morphology, contours, color segmentation, GrabCut |
| `compositing-blending` | 4 | Composite/blend, watermark, image diff, background removal |

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Claude Code 1.0.33+

## Usage

```bash
# Load the plugin
claude --plugin-dir ./cv-skills

# Use a skill
/cv-skills:resize
/cv-skills:blur
/cv-skills:threshold
```

## Development

See `PLAN.md` for the full v1 specification and `docs/future_candidates.md` for v2+ candidates.
