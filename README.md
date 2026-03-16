# cv-skills

Skills for performing classical image processing operations: format conversion, SVG rendering, resize/crop/rotate, color adjustment, filters, segmentation/morphology, and compositing/blending.

## Getting Started

Install the plugin, then just describe what you need — Claude picks the right skill automatically.

```
/plugin marketplace add garg-aayush/cv-skills
/plugin install cv-skills@garg-aayush-cv-skills
```

To update:

```
/plugin update cv-skills@garg-aayush-cv-skills
```

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — required for all skills
- [resvg](https://github.com/RazrFalcon/resvg/releases) — recommended for SVG rendering (falls back to [cairosvg](https://cairosvg.org/))

Pre-use hooks check for these automatically and provide install instructions if missing.

## Skills

| Skill | Description |
|---|---|
| `image-format` | Read image metadata, convert between formats (PNG/JPEG/WebP/TIFF/BMP/HEIC), handle alpha channels, EXIF data, ICC profiles, and animated GIF/WebP frames |
| `svg-convert` | Convert SVG to raster formats, inspect SVG metadata, render at custom scales or dimensions |
| `resize-transform` | Resize, crop, auto-crop, pad, rotate/flip, and combine images into montage grids |
| `color-adjust` | Adjust tone, saturation, grayscale, invert, convert color spaces, split/merge channels, histograms, equalize, auto-levels |
| `image-filters` | Gaussian/box/median blur, bilateral filter, sharpen (basic/unsharp/laplacian), denoise |
| `edges-masks` | Threshold, Canny/Sobel/Laplacian edges, morphological operations, contour extraction, color segmentation, GrabCut |
| `image-combine` | Alpha composite, blend, paste/overlay, text and image watermarks, pixel diff, background removal |

Skills are invoked using `/cv-skills:<skill-name>` syntax or triggered automatically from your description.

## License

MIT
