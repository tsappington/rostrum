"""The glass layer: the pause chip and the wand.

The film has exactly two layers. The paper — worksheet, ink, everything
the teacher touches — and the glass: the interface between student and
video, where captions live and where the chip and the wand appear.
Nothing else is ever allowed on the glass; that rule is what keeps the
frame quiet. Both citizens are gesture, not content: the chip says
"you act now", the wand says "look here" — neither ever writes,
teaches, or leaves a mark.

The chip borrows the worksheet's own pill component (the SKILL 1 badge):
brand orange, navy pause bars and Barlow SemiBold caps, full-radius
ends. It eases in on the spoken instruction ("Pause the video here"),
breathes through the hold, and eases out when the teacher resumes.

The wand is the teacher's pointer — an orange dot that pops in, hops
with each spoken count, gives a two-beat pulse on the final count (a
visual period), and pops out. It exists only while counting; it
appears and leaves by scale, never by fade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .brand import NAVY, ORANGE, PAPER

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


@lru_cache(maxsize=64)
def _dot(r: float) -> Image.Image:
    """The wand's dot, drawn 4x and downscaled so its edge stays soft."""
    ss = 4
    R = int(r * ss)
    ring = max(int(2.2 * ss), ss)
    size = 2 * (R + ring) + 2 * ss
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size // 2
    d.ellipse([c - R - ring, c - R - ring, c + R + ring, c + R + ring],
              fill=(*_hex(PAPER), 255))
    d.ellipse([c - R, c - R, c + R, c + R], fill=(*_hex(ORANGE), 255))
    return img.resize((size // ss, size // ss), Image.LANCZOS)


@dataclass
class Wand:
    """The counting pointer. Holds at a stop, hops to arrive at each
    stop's time, pulses twice at a flourish, pops in and out by scale."""

    page: int
    stops: list[tuple[float, float, float]]   # arrive-by (t, x_pt, y_pt)
    t_in: float
    t_out: float
    flourish: list[float] = field(default_factory=list)
    hop: float = 0.28
    radius: float = 11.0                       # final-frame px
    pop: float = 0.18

    def _pos(self, t: float) -> tuple[float, float]:
        st = self.stops
        if t <= st[0][0]:
            return st[0][1], st[0][2]
        for (_, x0, y0), (t1, x1, y1) in zip(st, st[1:]):
            if t <= t1:
                m0 = t1 - self.hop
                if t <= m0:
                    return x0, y0
                u = _ease((t - m0) / self.hop)
                return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        return st[-1][1], st[-1][2]

    def draw(self, frame: Image.Image, t: float, cam,
             supersample: int = 2) -> None:
        if t < self.t_in or t > self.t_out:
            return
        sc = min(_ease((t - self.t_in) / self.pop),
                 _ease((self.t_out - t) / self.pop))
        if sc <= 0.02:
            return
        r = self.radius * sc
        for tf in self.flourish:
            u = (t - tf) / 0.55
            if 0.0 <= u <= 1.0:
                r *= 1.0 + 0.38 * abs(math.sin(u * math.pi * 2))
        x_pt, y_pt = self._pos(t)
        cx, cy = cam.position(t)
        bx = int(round((cx - cam.union[0]) * cam.scale))
        by = int(round((cy - cam.union[1]) * cam.scale))
        x = ((x_pt - cam.union[0]) * cam.scale - bx) / supersample
        y = ((y_pt - cam.union[1]) * cam.scale - by) / supersample
        if not (-30 <= x <= frame.width + 30 and
                -30 <= y <= frame.height + 30):
            return
        dot = _dot(round(r * 2) / 2)
        frame.paste(dot, (int(x - dot.width / 2), int(y - dot.height / 2)),
                    dot)
