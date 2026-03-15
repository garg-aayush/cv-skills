# Future Version Candidates

Operations deferred from v1, could be added based on demand.

## Geometry & Transforms
- **Affine transformation** — general 2D transform via warpAffine (OpenCV)
- **Perspective warp** — 4-point perspective correction, e.g. document straightening (OpenCV)
- **Tiling** — split image into NxM grid tiles (Pillow)

## Color & Artistic Effects
- **White balance** — gray-world or manual temperature/tint correction (OpenCV)
- **Posterize** — reduce bit depth per channel (Pillow)
- **Solarize** — invert pixels above threshold (Pillow)
- **Color quantization** — reduce to N colors via k-means (OpenCV)

## Filters & Effects
- **Emboss** — 3D relief effect (Pillow)
- **Detail enhance** — bring out fine details (OpenCV)
- **Vignette** — darken edges, bright center (numpy)

## Segmentation & Morphology
- **Image masking** — apply geometric/arbitrary mask to extract ROI via bitwise ops (OpenCV)
- **Flood fill** — fill connected region from seed point (OpenCV)
- **Watershed** — marker-based region segmentation (OpenCV)
- **Skeletonize** — thin shapes to 1px skeleton (scikit-image)
- **Distance transform** — distance of each pixel to nearest edge (OpenCV)
- **Connected components** — label and count blobs (OpenCV)
- **Convex hull** — convex shape around objects (OpenCV)

## Compositing & Advanced
- **Seamless clone** — Poisson blending, paste without visible seams (OpenCV)
- **Image inpainting** — fill missing/damaged regions (OpenCV)

## Detection & Analysis
- **Hough line/circle detection** — detect geometric shapes (OpenCV)
- **Template matching** — find pattern in image (OpenCV)
- **Image registration** — align multiple images (OpenCV)
- **Background subtraction** — isolate foreground from static bg (OpenCV)
- **Image pyramids** — multi-scale representations (OpenCV)
- **Feature detection** — SIFT, ORB, corner detection (OpenCV)
