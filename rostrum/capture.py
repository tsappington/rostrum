"""Captured handwriting: ingest takes from the capture tool.

A take arrives in canvas space with real timestamps. Placement maps it
through the tool's guide geometry — canvas cap height to page cap height,
canvas baseline to the target baseline — so the writing keeps its own
proportions, spacing, and rhythm. Pressure: iPad Safari reported a
constant 0.5 (no Pencil pressure through pointer events), so pressure is
synthesized from the pen's *real* measured speed — slow ink presses
harder — which preserves the human dynamics we actually captured.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .ink import TimedPoint


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def starred_take(data: dict, prompt_id: str) -> dict:
    takes = data["prompts"][prompt_id]["takes"]
    for t in takes:
        if t.get("starred"):
            return t
    return takes[-1]


def _smooth(a: np.ndarray, passes: int = 1) -> np.ndarray:
    """Light 1-2-1 smoothing to take digitizer jitter off, nothing more."""
    for _ in range(passes):
        if len(a) < 3:
            return a
        a = a.copy()
        a[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]
    return a


def to_timed(
    data: dict,
    prompt_id: str,
    origin_pt: tuple[float, float],
    cap_pt: float,
    t0: float = 0.0,
    pace: float = 1.0,
    smooth_passes: int = 1,
) -> list[list[TimedPoint]]:
    """Place one captured take on the page as renderer-ready timed points.

    origin_pt: page (x, y) where the take's left edge meets the baseline.
    pace > 1 slows the performance down; timing is otherwise verbatim.
    """
    guide = data["guide"]
    cap_px = guide["baseline"] - guide["cap"]
    scale = cap_pt / cap_px
    take = starred_take(data, prompt_id)

    x_min = min(p[0] for s in take["strokes"] for p in s["points"])
    t_min = min(p[2] for s in take["strokes"] for p in s["points"])

    out: list[list[TimedPoint]] = []
    for s in take["strokes"]:
        pts = np.array(s["points"], dtype=float)          # x, y, t_ms, p
        xs = _smooth(pts[:, 0], smooth_passes)
        ys = _smooth(pts[:, 1], smooth_passes)
        ts = (pts[:, 2] - t_min) / 1000.0 * pace + t0

        # pressure from real speed: slow ink presses harder
        if len(pts) > 1:
            seg = np.hypot(np.diff(xs), np.diff(ys))
            dt = np.maximum(np.diff(ts), 1e-4)
            speed = np.concatenate([[0.0], seg / dt])
            ref = np.percentile(speed[speed > 0], 85) if (speed > 0).any() else 1.0
            speed_norm = np.clip(speed / max(ref, 1e-6), 0, 1)
        else:
            speed_norm = np.zeros(1)
        p = np.clip(0.78 - 0.30 * speed_norm, 0.42, 0.92)
        n = len(pts)
        head = max(n // 12, 1)
        tail = max(n // 14, 1)
        p[:head] *= np.linspace(0.75, 1.0, head)
        p[-tail:] *= np.linspace(1.0, 0.72, tail)

        page_x = origin_pt[0] + (xs - x_min) * scale
        page_y = origin_pt[1] + (ys - guide["baseline"]) * scale
        out.append([TimedPoint(ts[j], page_x[j], page_y[j], p[j]) for j in range(n)])
    return out


def take_width_pt(data: dict, prompt_id: str, cap_pt: float) -> float:
    guide = data["guide"]
    scale = cap_pt / (guide["baseline"] - guide["cap"])
    take = starred_take(data, prompt_id)
    xs = [p[0] for s in take["strokes"] for p in s["points"]]
    return (max(xs) - min(xs)) * scale
