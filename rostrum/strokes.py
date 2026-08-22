"""Stroke geometry: glyphs as pen paths, laid out and humanized.

Two stroke sources feed the same renderer: captured human writing
(assets/strokes/*.json from the capture tool) and the synthetic library
below. Either way a glyph is a list of strokes; a stroke is a polyline
the pen travels in order. Everything downstream — timing, pressure,
rendering — is source-agnostic.

Glyph space: x right, y UP from the baseline, cap height = 1.0.
Layout output is page space: PDF points, y down.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------
# glyph library — control polylines, Catmull-Rom smoothed at sample time.
# Repeated/close control points tighten a corner. Advance in cap units.


@dataclass(frozen=True)
class GlyphDef:
    strokes: list[list[tuple[float, float]]]
    advance: float


GLYPHS: dict[str, GlyphDef] = {
    "1": GlyphDef(
        strokes=[[(0.14, 0.68), (0.30, 0.96), (0.32, 0.97), (0.33, 0.60), (0.32, 0.22), (0.31, -0.01)]],
        advance=0.46,
    ),
    "2": GlyphDef(
        strokes=[[(0.08, 0.70), (0.16, 0.90), (0.34, 0.99), (0.50, 0.88), (0.52, 0.66),
                  (0.38, 0.42), (0.20, 0.20), (0.07, 0.03), (0.06, 0.01),
                  (0.26, 0.05), (0.44, 0.04), (0.56, 0.06)]],
        advance=0.62,
    ),
    "3": GlyphDef(
        strokes=[[(0.08, 0.83), (0.20, 0.97), (0.40, 0.97), (0.50, 0.80), (0.42, 0.60),
                  (0.27, 0.53), (0.44, 0.47), (0.55, 0.28), (0.46, 0.07),
                  (0.24, -0.02), (0.07, 0.08)]],
        advance=0.62,
    ),
    "4": GlyphDef(
        strokes=[
            [(0.44, 0.96), (0.30, 0.70), (0.16, 0.44), (0.13, 0.36), (0.14, 0.34),
             (0.36, 0.35), (0.58, 0.36)],
            [(0.50, 0.62), (0.51, 0.40), (0.51, 0.16), (0.50, -0.02)],
        ],
        advance=0.66,
    ),
    "5": GlyphDef(
        strokes=[
            [(0.48, 0.95), (0.26, 0.94), (0.17, 0.93), (0.14, 0.70), (0.12, 0.56),
             (0.28, 0.60), (0.44, 0.54), (0.54, 0.32), (0.46, 0.08), (0.22, -0.03), (0.06, 0.08)],
        ],
        advance=0.62,
    ),
    "6": GlyphDef(
        strokes=[[(0.48, 0.92), (0.30, 0.72), (0.16, 0.44), (0.12, 0.20), (0.22, 0.02),
                  (0.42, 0.02), (0.52, 0.18), (0.46, 0.36), (0.28, 0.40), (0.14, 0.30)]],
        advance=0.62,
    ),
    "7": GlyphDef(
        strokes=[[(0.08, 0.90), (0.30, 0.94), (0.54, 0.93), (0.55, 0.91), (0.40, 0.58),
                  (0.28, 0.28), (0.22, -0.01)]],
        advance=0.58,
    ),
    "8": GlyphDef(
        strokes=[[(0.38, 0.97), (0.20, 0.88), (0.16, 0.68), (0.30, 0.53), (0.46, 0.44),
                  (0.54, 0.24), (0.44, 0.04), (0.24, 0.00), (0.10, 0.16), (0.20, 0.38),
                  (0.36, 0.50), (0.50, 0.66), (0.50, 0.86), (0.38, 0.97)]],
        advance=0.64,
    ),
    "9": GlyphDef(
        strokes=[[(0.52, 0.78), (0.40, 0.94), (0.20, 0.92), (0.10, 0.74), (0.16, 0.56),
                  (0.36, 0.52), (0.52, 0.62), (0.52, 0.78), (0.50, 0.46), (0.44, 0.20), (0.36, -0.02)]],
        advance=0.62,
    ),
    "0": GlyphDef(
        strokes=[[(0.32, 0.97), (0.14, 0.84), (0.08, 0.52), (0.14, 0.16), (0.32, 0.00),
                  (0.48, 0.14), (0.55, 0.50), (0.49, 0.84), (0.32, 0.97)]],
        advance=0.64,
    ),
    "×": GlyphDef(
        strokes=[
            [(0.08, 0.58), (0.24, 0.38), (0.42, 0.12)],
            [(0.42, 0.58), (0.25, 0.36), (0.07, 0.12)],
        ],
        advance=0.54,
    ),
    "=": GlyphDef(
        strokes=[
            [(0.06, 0.44), (0.28, 0.46), (0.50, 0.47)],
            [(0.06, 0.24), (0.28, 0.26), (0.50, 0.27)],
        ],
        advance=0.62,
    ),
    " ": GlyphDef(strokes=[], advance=0.34),
}


# ---------------------------------------------------------------------------


@dataclass
class Stroke:
    """A pen path in page space. points: (N, 3) float array [x_pt, y_pt, kappa]
    with kappa a 0..1 normalized curvature estimate used by the timing model."""

    points: np.ndarray
    glyph: str = ""
    pen_down: bool = True

    @property
    def length(self) -> float:
        d = np.diff(self.points[:, :2], axis=0)
        return float(np.hypot(d[:, 0], d[:, 1]).sum())


def _catmull_rom(ctrl: np.ndarray, samples_per_unit: float = 42.0) -> np.ndarray:
    """Sample a Catmull-Rom spline through the control points."""
    if len(ctrl) == 2:
        n = max(6, int(np.hypot(*(ctrl[1] - ctrl[0])) * samples_per_unit))
        t = np.linspace(0, 1, n)[:, None]
        return ctrl[0] + (ctrl[1] - ctrl[0]) * t
    pts = np.vstack([ctrl[0], ctrl, ctrl[-1]])
    out = []
    for i in range(len(pts) - 3):
        p0, p1, p2, p3 = pts[i : i + 4]
        seg_len = np.hypot(*(p2 - p1))
        n = max(4, int(seg_len * samples_per_unit))
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        t2, t3 = t * t, t * t * t
        out.append(
            0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                   + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
        )
    out.append(pts[-2][None, :])
    return np.vstack(out)


def _curvature(pts: np.ndarray) -> np.ndarray:
    """Normalized 0..1 curvature per point (turn angle per unit length)."""
    if len(pts) < 3:
        return np.zeros(len(pts))
    v = np.diff(pts, axis=0)
    ang = np.arctan2(v[:, 1], v[:, 0])
    turn = np.abs(np.diff(np.unwrap(ang)))
    seg = np.hypot(v[:, 0], v[:, 1])
    k = np.zeros(len(pts))
    k[1:-1] = turn / np.maximum(seg[1:] + seg[:-1], 1e-6)
    if k.max() > 0:
        k = np.clip(k / np.percentile(k[k > 0], 92) if (k > 0).any() else k, 0, 1)
    return k


def _smooth_noise(n: int, rng: np.random.Generator, cycles=(1.7, 3.9)) -> np.ndarray:
    """Low-frequency wobble along a stroke: sum of two random-phase sines."""
    u = np.linspace(0, 1, n)
    out = np.zeros(n)
    for c in cycles:
        out += rng.uniform(0.4, 1.0) * np.sin(2 * math.pi * (c * u + rng.uniform(0, 1)))
    return out / len(cycles)


def layout_phrase(
    text: str,
    origin_pt: tuple[float, float],
    cap_pt: float,
    seed: int = 7,
    slant_deg: float = 4.0,
    wobble: float = 0.010,
    jitter: float = 0.020,
) -> list[Stroke]:
    """Lay out synthetic handwriting for `text`.

    origin_pt: page-space (x, y) of the first glyph's baseline-left.
    cap_pt: cap height in points. Returns strokes in writing order.
    """
    rng = np.random.default_rng(seed)
    strokes: list[Stroke] = []
    pen_x = 0.0
    shear = math.tan(math.radians(slant_deg))
    for ch in text:
        g = GLYPHS.get(ch)
        if g is None:
            raise KeyError(f"no glyph for {ch!r}")
        rot = math.radians(rng.normal(0, 1.1))
        scale = 1.0 + rng.normal(0, jitter)
        base_dy = rng.normal(0, jitter * 0.55)
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        for raw in g.strokes:
            ctrl = np.array(raw, dtype=float)
            pts = _catmull_rom(ctrl)
            # smooth wobble perpendicular-ish: apply in y, scaled by arc position
            wob = _smooth_noise(len(pts), rng) * wobble
            pts = pts + np.stack([wob * 0.4, wob], axis=1)
            pts = pts * scale
            # rotation about glyph center
            c = pts.mean(axis=0)
            pts = (pts - c) @ np.array([[cos_r, -sin_r], [sin_r, cos_r]]).T + c
            # italic shear, then place: glyph y-up -> page y-down
            xs = pen_x + pts[:, 0] + pts[:, 1] * shear
            ys = -(pts[:, 1] + base_dy)
            page = np.stack(
                [origin_pt[0] + xs * cap_pt, origin_pt[1] + ys * cap_pt], axis=1
            )
            k = _curvature(page)
            strokes.append(Stroke(np.column_stack([page, k]), glyph=ch))
        pen_x += g.advance * (1.0 + rng.normal(0, jitter * 0.8))
    return strokes


def phrase_advance(text: str) -> float:
    """Nominal width of the phrase in cap units (pre-jitter)."""
    return sum(GLYPHS[ch].advance for ch in text)
