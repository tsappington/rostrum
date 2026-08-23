"""The performance: timing, pressure, and rendered ink.

Writing reads as human because of *when* the pen moves, not just where:
strokes start and end slow, curves slow the hand, straights let it run,
and there are real hesitations — a breath before an answer. This module
assigns every stroke point a timestamp and a pressure, then renders the
ink progressively onto a supersampled layer.

Timing here is the synthetic model; captured takes from the capture tool
carry their own real timestamps and replay verbatim through the same
renderer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw

from .strokes import Stroke

INK_RGB = (45, 95, 168)          # brand.INK


@dataclass
class TimedPoint:
    t: float          # seconds on the performance clock
    x: float          # page pt
    y: float
    p: float          # pressure 0..1


def time_strokes(
    strokes: list[Stroke],
    t0: float = 0.0,
    pace: float = 1.0,
    cap_pt: float = 14.0,
    seed: int = 11,
    hesitate_before: dict[int, float] | None = None,
) -> list[list[TimedPoint]]:
    """Assign timestamps and pressure to every point of every stroke.

    hesitate_before: stroke index -> extra pause in seconds (a beat of
    thought before that stroke — e.g. before writing an answer).
    """
    rng = np.random.default_rng(seed)
    out: list[list[TimedPoint]] = []
    t = t0
    prev_glyph = None
    for i, s in enumerate(strokes):
        # pen-up gap before this stroke
        if i > 0:
            same_glyph = s.glyph == prev_glyph
            gap = rng.uniform(0.07, 0.12) if same_glyph else rng.uniform(0.15, 0.24)
            t += gap * pace
        if hesitate_before and i in hesitate_before:
            t += hesitate_before[i]
        prev_glyph = s.glyph

        pts = s.points
        n = len(pts)
        L_cap = s.length / cap_pt                       # length in cap units
        T = (0.13 + 0.20 * math.sqrt(max(L_cap, 1e-3))) * pace
        T *= 1.0 + rng.normal(0, 0.06)

        # speed profile: bell over the stroke, slowed by curvature
        u = np.linspace(0, 1, n)
        bell = 0.30 + 0.70 * np.sin(np.pi * np.clip(u, 0.02, 0.98)) ** 0.75
        drag = 1.0 + 2.6 * pts[:, 2] ** 1.2             # curvature slows the pen
        seg = np.hypot(*np.diff(pts[:, :2], axis=0).T)
        dt = seg * (drag[1:] + drag[:-1]) * 0.5 / np.maximum(bell[1:], 1e-3)
        if dt.sum() <= 0:
            dt = np.ones(max(n - 1, 1))
        times = np.concatenate([[0.0], np.cumsum(dt)])
        times = times / times[-1] * T + t

        # pressure: settles in, tapers out; heavier where the pen is slow
        speed_norm = np.concatenate([[0], seg / np.maximum(dt, 1e-9)])
        if speed_norm.max() > 0:
            speed_norm = speed_norm / speed_norm.max()
        p = (0.62 + 0.16 * np.sin(np.pi * u) - 0.14 * speed_norm
             + rng.normal(0, 0.02, n))
        p = np.clip(p, 0.30, 0.95)
        # entry/exit taper
        p[: max(n // 12, 1)] *= np.linspace(0.75, 1.0, max(n // 12, 1))
        p[-max(n // 14, 1):] *= np.linspace(1.0, 0.72, max(n // 14, 1))

        out.append([TimedPoint(times[j], pts[j, 0], pts[j, 1], p[j]) for j in range(n)])
        t = times[-1]
    return out


class InkLayer:
    """Progressive ink on a transparent, supersampled layer.

    Page-space pt coordinates map through (origin_pt, scale px/pt). Call
    draw_until(t) each frame; it draws only the newly reached segments.
    """

    def __init__(self, size_px: tuple[int, int], origin_pt: tuple[float, float],
                 scale: float, width_pt: float = 1.9):
        self.img = Image.new("RGBA", size_px, (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)
        self.origin = origin_pt
        self.scale = scale
        self.width_px = width_pt * scale
        self._cursor: tuple[int, int] = (0, 1)   # (stroke, point) progress

    def _xy(self, pt: TimedPoint) -> tuple[float, float]:
        return ((pt.x - self.origin[0]) * self.scale,
                (pt.y - self.origin[1]) * self.scale)

    def draw_until(self, timed: list[list[TimedPoint]], t: float) -> None:
        si, pi = self._cursor
        while si < len(timed):
            stroke = timed[si]
            if len(stroke) == 1:                      # a dot — the pen taps
                if stroke[0].t > t:
                    break
                q = self._xy(stroke[0])
                r = self.width_px * (0.55 + 0.90 * stroke[0].p) * 0.5
                alpha = int(176 + 72 * stroke[0].p)
                self.draw.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r],
                                  fill=(*INK_RGB, alpha))
                si, pi = si + 1, 1
                continue
            while pi < len(stroke) and stroke[pi].t <= t:
                a, b = stroke[pi - 1], stroke[pi]
                pa, pb = self._xy(a), self._xy(b)
                p = (a.p + b.p) * 0.5
                w = self.width_px * (0.55 + 0.90 * p)
                alpha = int(176 + 72 * p)
                self.draw.line([pa, pb], fill=(*INK_RGB, alpha), width=max(int(round(w)), 1))
                for q in (pa, pb):
                    r = w * 0.5
                    self.draw.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r],
                                      fill=(*INK_RGB, alpha))
                pi += 1
            if pi < len(stroke):
                break
            si, pi = si + 1, 1
        self._cursor = (si, pi)

    def done(self, timed: list[list[TimedPoint]]) -> bool:
        return self._cursor[0] >= len(timed)
