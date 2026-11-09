import sys, io, glob, cairosvg
from PIL import Image, ImageOps
d, name, x0, y0, x1, y1, out = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:7]), sys.argv[7]
S = 20  # px/mm
colors = [(200, 60, 40), (240, 240, 240), (230, 200, 0), (120, 120, 255)]
base = None
for i, c in enumerate(colors):
    f = f"{d}/{name}_{i}.svg"
    try: png = cairosvg.svg2png(url=f, output_width=int(297 * S), output_height=int(210 * S), background_color="white")
    except Exception: continue
    im = Image.open(io.BytesIO(png)).convert("L")
    mask = ImageOps.invert(im).point(lambda v: 255 if v > 40 else 0)
    if base is None: base = Image.new("RGB", im.size, (20, 20, 20))
    base.paste(Image.new("RGB", im.size, c), (0, 0), mask)
base.crop((int(x0 * S), int(y0 * S), int(x1 * S), int(y1 * S))).save(out)
