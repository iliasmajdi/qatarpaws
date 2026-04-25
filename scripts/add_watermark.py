#!/usr/bin/env python3
"""
Stamp every image in images/*.jpg with a small QatarPaws branding watermark
(paw logo + qatarpaws.com text on a semi-transparent dark pill), bottom-right
corner. Overwrites in place. Does NOT resize the image.

Run once after dropping freshly fetched photos into images/. Re-running double-
stamps the same image, so don't unless you've replaced the source jpgs.

  pip install Pillow
  python scripts/add_watermark.py
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "images"

INK     = (20, 18, 16)        # #141210
CREAM   = (246, 241, 232)     # #F6F1E8
CRIMSON = (123, 30, 30)       # #7B1E1E
PILL_BG = (20, 18, 16, 200)   # ~78% opaque

PAW_PX  = 36
PAD_X   = 12
PAD_Y   = 6
GAP     = 8


def draw_paw(canvas: Image.Image, x: int, y: int, size: int) -> None:
    """Draw the QatarPaws paw-print at (x, y), `size` px square.
    Coords mirror /favicon.svg (40x40 viewBox)."""
    s = size / 40.0
    d = ImageDraw.Draw(canvas)

    def circle(cx, cy, r, fill):
        d.ellipse(
            (x + (cx - r) * s, y + (cy - r) * s,
             x + (cx + r) * s, y + (cy + r) * s),
            fill=fill,
        )

    def ellipse(cx, cy, rx, ry, fill):
        d.ellipse(
            (x + (cx - rx) * s, y + (cy - ry) * s,
             x + (cx + rx) * s, y + (cy + ry) * s),
            fill=fill,
        )

    circle(20, 20, 19, INK)                              # background disc
    ellipse(13,   15.5, 2.6, 3.4, CREAM)                 # toe 1
    ellipse(20,   12.5, 2.6, 3.4, CREAM)                 # toe 2
    ellipse(27,   15.5, 2.6, 3.4, CREAM)                 # toe 3
    ellipse(30.5, 22,   2.3, 3,   CREAM)                 # toe 4
    ellipse(20,   25.5, 8.5, 6,   CREAM)                 # main pad
    circle(30,    11,   1.4, CRIMSON)                    # red highlight


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for cand in (
        "C:/Windows/Fonts/segoeuib.ttf",   # Segoe UI Bold (Windows)
        "C:/Windows/Fonts/arialbd.ttf",    # Arial Bold (Windows)
        "/Library/Fonts/Arial Bold.ttf",   # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_watermark() -> Image.Image:
    """Render the watermark composite at a fixed base size (RGBA).
    Caller resizes to fit a given image."""
    font = load_font(16)
    text = "qatarpaws.com"
    tmp = Image.new("RGBA", (1, 1))
    bb = ImageDraw.Draw(tmp).textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]

    pill_w = PAD_X + PAW_PX + GAP + tw + PAD_X
    pill_h = PAD_Y + max(PAW_PX, th) + PAD_Y

    out = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, 0, pill_w, pill_h), radius=pill_h // 2, fill=PILL_BG)

    paw_x = PAD_X
    paw_y = (pill_h - PAW_PX) // 2
    draw_paw(out, paw_x, paw_y, PAW_PX)

    text_x = paw_x + PAW_PX + GAP - bb[0]
    text_y = (pill_h - th) // 2 - bb[1]
    d.text((text_x, text_y), text, font=font, fill=CREAM)
    return out


def main() -> int:
    if not IMAGES_DIR.exists():
        raise SystemExit(f"Images dir not found: {IMAGES_DIR}")

    jpgs = sorted(IMAGES_DIR.glob("*.jpg"))
    if not jpgs:
        raise SystemExit("No .jpg files in images/")

    print(f"Watermarking {len(jpgs)} images in {IMAGES_DIR.relative_to(ROOT)}")

    base = make_watermark()
    base_w, base_h = base.size

    n_done = 0
    n_fail = 0
    for src in jpgs:
        try:
            img = Image.open(src).convert("RGBA")
            iw, ih = img.size

            # Watermark width: about 28% of image width, clamped 110-220 px
            target_w = max(110, min(220, int(iw * 0.28)))
            scale = target_w / base_w
            wm = base.resize((int(base_w * scale), int(base_h * scale)),
                             Image.Resampling.LANCZOS)

            margin = max(8, min(24, int(iw * 0.04)))
            pos = (iw - wm.width - margin, ih - wm.height - margin)

            img.alpha_composite(wm, dest=pos)
            img.convert("RGB").save(src, "JPEG", quality=92, optimize=True)
            n_done += 1
        except Exception as e:
            print(f"  ! {src.name}: {type(e).__name__}: {e}")
            n_fail += 1

    print(f"Done: {n_done} watermarked, {n_fail} failed")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
