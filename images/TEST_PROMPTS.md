# cv-skills Test Prompts

Test images: `test.png` (santa hat, transparent bg), `test.jpeg` (big sister grinch art, beige bg), `test.svg` (vector graphic).

Copy-paste these into Claude Code one at a time. Each prompt should trigger the correct skill automatically. Expected skill noted in brackets — don't include that part when testing.

---

## image-format

### 1. Basic format conversion
save images/test.png as a jpeg, put it in images/out/

### 2. Get image info
whats the dimensions and format of images/test.jpeg? also check if it has any exif data

### 3. Alpha handling
the test.png has a transparent background, can you remove the transparency and put it on a light blue background? save to images/out/

### 4. Strip EXIF
strip all the metadata from images/test.jpeg and save a clean copy to images/out/hat_clean.jpeg

### 5. Animation frames
take test.png and test.jpeg, assemble them into an animated gif with 500ms delay between frames. save to images/out/animation.gif

---

## svg-convert

### 6. SVG to PNG
convert images/test.svg to a png file, save in images/out/

### 7. SVG render at scale
render images/test.svg at 2x scale as a png, output to images/out/test_2x.png

### 8. SVG info
what are the dimensions and viewbox of images/test.svg?

---

## resize-transform

### 9. Make it smaller
make images/test.jpeg 50% smaller, save to images/out/

### 10. Create thumbnail
i need a thumbnail of test.png, fit it within 200x200 pixels. save to images/out/thumb.png

### 11. Crop to square
crop images/test.jpeg to a 1:1 square, centered. save to images/out/

### 12. Auto-crop whitespace
trim the empty space around the hat in images/test.png, save to images/out/trimmed.png

### 13. Add padding
put images/test.jpeg on a 1000x1000 white canvas, centered. save to images/out/padded.jpeg

### 14. Rotate
flip images/test.jpeg horizontally (mirror it) and save to images/out/mirrored.jpeg

### 15. Montage
put test.png and test.jpeg side by side in a grid, 2 columns. save to images/out/grid.png

---

## color-adjust

### 16. Brighten
images/test.jpeg is kinda dark, can you brighten it up? save to images/out/bright.jpeg

### 17. Boost saturation
make the colors in images/test.jpeg more vivid, really punch up the saturation. save to images/out/vivid.jpeg

### 18. Grayscale
convert images/test.jpeg to black and white, save to images/out/gray.jpeg

### 19. Invert
invert the colors of images/test.jpeg like a photo negative. save images/out/inverted.jpeg

### 20. Histogram
show me the color histogram of images/test.jpeg, save the plot to images/out/hist.png

### 21. Fix exposure
the exposure on images/test.jpeg seems off, try auto-levels on it. save to images/out/leveled.jpeg

---

## image-filters

### 22. Blur
blur images/test.jpeg with a gaussian blur, sigma 3 or so. save to images/out/blurred.jpeg

### 23. Sharpen
images/test.jpeg looks a bit soft, sharpen it up. save to images/out/sharp.jpeg

### 24. Denoise
clean up any noise in images/test.jpeg, save to images/out/clean.jpeg

### 25. Smooth but keep edges
apply a bilateral filter to images/test.jpeg to smooth it but keep the edges crisp. save to images/out/smooth.jpeg

---

## edges-masks

### 26. Find edges
detect the edges in images/test.jpeg, save the edge map to images/out/edges.png

### 27. Create binary mask
threshold images/test.jpeg into a black and white binary image using otsu. save to images/out/binary.png

### 28. Find contours
find and draw the object outlines in images/test.jpeg, draw them in red. save to images/out/contours.png

### 29. Morphology cleanup
i have a noisy binary mask at images/out/binary.png, clean it up with morphological opening. save to images/out/cleaned_mask.png

### 30. Color segmentation
create a mask of just the green colored areas in images/test.jpeg. use HSV space. save to images/out/green_mask.png

### 31. GrabCut foreground
extract the foreground of images/test.jpeg using grabcut. the main content is roughly in the box 50,30,600,550. save the mask to images/out/foreground.png

---

## image-combine

### 32. Overlay / composite
overlay images/test.png (the transparent hat) on top of images/test.jpeg. paste it at position 100,0. save to images/out/composite.png

### 33. Watermark
add a text watermark "SAMPLE" to images/test.jpeg, centered, semi-transparent. save to images/out/watermarked.jpeg

### 34. Image diff
compare images/test.jpeg with images/out/bright.jpeg and show me the differences amplified 5x. save the diff to images/out/diff.png

### 35. Remove background
remove the background from images/test.jpeg. the foreground object is roughly in the bounding box 50,30,600,550. save as images/out/cutout.png

---

## Ambiguous / boundary cases

These test whether Claude routes to the RIGHT skill when the request could go either way.

### 36. "remove background" -> image-combine (not edges-masks)
remove the background from images/test.jpeg and give me a transparent png cutout. foreground box is about 50,30,600,550. save to images/out/nobg.png

### 37. "create a mask" -> edges-masks (not image-combine)
i need a binary mask of images/test.jpeg, just black and white. threshold it for me. save to images/out/mask.png

### 38. "make it black and white" -> color-adjust (not edges-masks)
make images/test.jpeg black and white / grayscale. save to images/out/bw.jpeg

### 39. "combine these images" side-by-side -> resize-transform (not image-combine)
put test.png and test.jpeg next to each other in a row. save to images/out/sidebyside.png

### 40. "combine these images" as layers -> image-combine (not resize-transform)
layer test.png on top of test.jpeg, blend them 50/50. save to images/out/blended.png

### 41. "smooth this out" -> image-filters (not color-adjust)
smooth out images/test.jpeg, reduce the graininess. save to images/out/smoothed.jpeg

### 42. "find the outlines" -> edges-masks (not image-filters)
find the outlines of objects in images/test.jpeg. save to images/out/outlines.png

### 43. Save as different type -> image-format (not resize-transform)
convert images/test.png to webp format. save to images/out/test.webp

### 44. SVG rasterize -> svg-convert (not image-format)
rasterize images/test.svg to a png at 1200px wide. save to images/out/test_wide.png

### 45. Alpha extraction -> image-format (not edges-masks)
extract the alpha channel from images/test.png as a grayscale mask image. save to images/out/alpha_mask.png
