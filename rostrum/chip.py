"""The glass layer: the pause chip.

The film has exactly two layers. The paper — worksheet, ink, everything
the teacher touches — and the glass: the interface between student and
video, where captions live and where this chip appears. Nothing else is
ever allowed on the glass; that rule is what keeps the frame quiet.

The chip borrows the worksheet's own pill component (the SKILL 1 badge):
brand orange, navy pause bars and Barlow SemiBold caps, full-radius
ends. It eases in on the spoken instruction ("Pause the video here"),
breathes through the hold, and eases out when the teacher resumes.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .brand import NAVY, ORANGE

FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / \
    "BarlowSemiCondensed-SemiBold.ttf"

TEXT = "PAUSE & TRY"


def _hex(c: str) -> tuple[int, int, int]:
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


@lru_cache(maxsize=8)
def chip_asset(height: int = 64) -> Image.Image:
    """Render the chip once at the requested pixel height (RGBA)."""
    h = height
    pad = int(h * 0.42)
    bar_w = max(int(h * 0.11), 3)
    bar_h = int(h * 0.44)
    bar_gap = int(bar_w * 0.9)
    font = ImageFont.truetype(str(FONT), int(h * 0.46))
    tracking = int(h * 0.03)

    # measure text with tracking
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    widths = [probe.textlength(ch, font=font) for ch in TEXT]
    text_w = int(sum(widths)) + tracking * (len(TEXT) - 1)
    icon_w = bar_w * 2 + bar_gap
    w = pad + icon_w + int(h * 0.3) + text_w + pad

    img = Image.new("RGBA", (w + 8, h + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # soft shadow, like the worksheet's own cards
    d.rounded_rectangle([4, 7, 4 + w, 7 + h], radius=h // 2,
                        fill=(56, 70, 82, 46))
    d.rounded_rectangle([4, 4, 4 + w, 4 + h], radius=h // 2,
                        fill=(*_hex(ORANGE), 255))

    navy = (*_hex(NAVY), 255)
    x = 4 + pad
    by = 4 + (h - bar_h) // 2
    for i in range(2):
        bx = x + i * (bar_w + bar_gap)
        d.rounded_rectangle([bx, by, bx + bar_w, by + bar_h],
                            radius=bar_w // 2, fill=navy)
    x += icon_w + int(h * 0.3)

    ty = 4 + h / 2
    for ch, cw in zip(TEXT, widths):
        d.text((x, ty), ch, font=font, fill=navy, anchor="lm")
        x += cw + tracking
    return img


def _ease(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def overlay(frame: Image.Image, t: float,
            windows: list[tuple[float, float]],
            fade: float = 0.35, margin: int = 40, height: int = 64) -> None:
    """Composite the chip onto a frame in place, if any window is live.

    Eases opacity and a slight rise on entry, the reverse on exit.
    """
    alpha = 0.0
    for t_in, t_out in windows:
        if t_in - fade <= t <= t_out + fade:
            a_in = _ease((t - (t_in - fade)) / fade) if t < t_in else 1.0
            a_out = _ease(((t_out + fade) - t) / fade) if t > t_out else 1.0
            alpha = max(alpha, min(a_in, a_out))
    if alpha <= 0.01:
        return
    chip = chip_asset(height)
    if alpha < 1.0:
        chip = chip.copy()
        a = chip.getchannel("A").point(lambda v: int(v * alpha))
        chip.putalpha(a)
    rise = int((1.0 - alpha) * 10)
    x = frame.width - chip.width - margin
    y = frame.height - chip.height - margin + rise
    frame.paste(chip, (x, y), chip)      # alpha-masked; frame may be RGB
