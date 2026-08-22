"""The set: the guided notes PDF as camera-ready plates.

The worksheet is true vector, which buys three things a scan never could:
plates render tack-sharp at any DPI the camera asks for, every answer
blank is a real line segment with exact coordinates (ink lands on
geometry, not guesswork), and the page's own art carries exact positions
for annotation.

Coordinates: PDF points (72/inch), origin top-left, page is 612x792.
`to_px(...)` maps page-space to plate pixels for a given DPI.
"""

from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image

ASSET = Path(__file__).resolve().parent.parent / "assets" / "guided_notes.pdf"


@dataclass(frozen=True)
class Blank:
    """A horizontal answer rule on the page, in PDF points."""

    page: int          # 0-based page index
    x0: float
    x1: float
    y: float           # the baseline the handwriting sits on

    @property
    def width(self) -> float:
        return self.x1 - self.x0


def open_doc() -> pymupdf.Document:
    return pymupdf.open(ASSET)


def render_plate(page_index: int, dpi: int = 300) -> Image.Image:
    """Render one full page to an RGB plate at the given DPI."""
    with open_doc() as doc:
        pix = doc[page_index].get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def to_px(value: float, dpi: int = 300) -> float:
    """Map PDF points to plate pixels at the given DPI."""
    return value * dpi / 72.0


# The document draws every answer blank the same way: a hairline filled
# rect (~0.75pt tall) in this exact warm gray. That's our anchor signature.
_BLANK_FILL = (0.7254902, 0.6901961, 0.6391852)


def find_blanks(page_index: int, min_len: float = 20.0) -> list[Blank]:
    """Locate the answer blanks: hairline filled rects in the blank-gray."""
    blanks: list[Blank] = []
    with open_doc() as doc:
        for d in doc[page_index].get_drawings():
            fill = d.get("fill")
            if fill is None:
                continue
            if max(abs(a - b) for a, b in zip(fill, _BLANK_FILL)) > 0.02:
                continue
            r = d["rect"]
            if r.height > 2.0 or r.width < min_len:
                continue
            blanks.append(Blank(page_index, r.x0, r.x1, (r.y0 + r.y1) / 2))
    blanks.sort(key=lambda b: (b.y, b.x0))
    return blanks
