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


def _fit(take: dict, data: dict, cap_pt: float) -> tuple[float, float]:
    """Scale and baseline for a take: measured from its own ink.

    Writers drift in size — a take written at half the guide height must
    still land at the target cap. The take's ink is the truth: cap height
    is estimated from its vertical extent (robust percentiles, so a
    stray tail doesn't inflate it), and the baseline from where the ink
    bottom actually sits. Returns (scale px->pt, baseline_px).
    """
    ys = np.array([p[1] for s in take["strokes"] for p in s["points"]])
    top = np.percentile(ys, 4)
    base_y = np.percentile(ys, 94)
    cap_px = base_y - top
    if cap_px < 8.0:                     # a mark (underline, dot): no cap of
        guide = take.get("guide") or data["guide"]   # its own — use the guide
        cap_px = guide["baseline"] - guide["cap"]
        base_y = guide["baseline"]
    return cap_pt / cap_px, float(base_y)


def _smooth(a: np.ndarray, passes: int = 1) -> np.ndarray:
    """Light 1-2-1 smoothing to take digitizer jitter off, nothing more."""
    for _ in range(passes):
        if len(a) < 3:
            return a
        a = a.copy()
        a[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]
    return a


def _dedup(pts: np.ndarray) -> np.ndarray:
    """Keep only strictly-forward-in-time samples.

    Safari's coalesced pointer events can replay runs it already
    delivered; the giveaway is a timestamp that goes backward. Enforcing
    monotonic time removes the duplicates without touching real data.
    """
    keep = [0]
    for i in range(1, len(pts)):
        if pts[i, 2] > pts[keep[-1], 2]:
            keep.append(i)
    return pts[keep]


def _real_pressure(p: np.ndarray) -> np.ndarray | None:
    """Normalize genuine Pencil pressure into the ink model's range.

    A light-handed writer lives around 0.05-0.4, which would render
    anemic ink. Rescale that personal range onto 0.45-0.90 while keeping
    the writer's relative dynamics — the captured humanity — intact.
    Returns None when the channel is dead (constant), so the caller
    falls back to speed-derived pressure.
    """
    if p.max() - p.min() < 0.05:
        return None
    lo, hi = np.percentile(p, 15), np.percentile(p, 92)
    if hi - lo < 1e-3:
        return None
    return 0.45 + 0.45 * np.clip((p - lo) / (hi - lo), 0, 1)


def to_timed(
    data: dict,
    prompt_id: str,
    origin_pt: tuple[float, float],
    cap_pt: float,
    t0: float = 0.0,
    pace: float = 1.0,
    smooth_passes: int = 1,
    max_gap: float = 0.9,
) -> list[list[TimedPoint]]:
    """Place one captured take on the page as renderer-ready timed points.

    origin_pt: page (x, y) where the take's left edge meets the baseline.
    pace > 1 slows the performance down; timing is otherwise verbatim,
    except pen-up pauses longer than max_gap seconds are clamped to it —
    a capture interruption should not replay as a frozen video.
    """
    take = starred_take(data, prompt_id)
    scale, base_y = _fit(take, data, cap_pt)

    x_min = min(p[0] for s in take["strokes"] for p in s["points"])
    t_min = min(p[2] for s in take["strokes"] for p in s["points"])

    out: list[list[TimedPoint]] = []
    t_shift = 0.0
    prev_end: float | None = None
    for s in take["strokes"]:
        pts = _dedup(np.array(s["points"], dtype=float))  # x, y, t_ms, p
        xs = _smooth(pts[:, 0], smooth_passes)
        ys = _smooth(pts[:, 1], smooth_passes)
        ts = (pts[:, 2] - t_min) / 1000.0 * pace + t0 - t_shift
        if prev_end is not None and ts[0] - prev_end > max_gap:
            extra = ts[0] - prev_end - max_gap
            t_shift += extra
            ts = ts - extra
        prev_end = ts[-1]

        n = len(pts)
        p = _real_pressure(pts[:, 3])
        if p is not None:
            p = _smooth(p, 2)
        else:
            # dead channel: derive pressure from real speed instead —
            # slow ink presses harder — and shape entry/exit ourselves
            if n > 1:
                seg = np.hypot(np.diff(xs), np.diff(ys))
                dt = np.maximum(np.diff(ts), 1e-4)
                speed = np.concatenate([[0.0], seg / dt])
                ref = np.percentile(speed[speed > 0], 85) if (speed > 0).any() else 1.0
                speed_norm = np.clip(speed / max(ref, 1e-6), 0, 1)
            else:
                speed_norm = np.zeros(1)
            p = np.clip(0.78 - 0.30 * speed_norm, 0.42, 0.92)
            head = max(n // 12, 1)
            tail = max(n // 14, 1)
            p[:head] *= np.linspace(0.75, 1.0, head)
            p[-tail:] *= np.linspace(1.0, 0.72, tail)

        page_x = origin_pt[0] + (xs - x_min) * scale
        page_y = origin_pt[1] + (ys - base_y) * scale
        out.append([TimedPoint(ts[j], page_x[j], page_y[j], p[j]) for j in range(n)])
    return out


def take_width_pt(data: dict, prompt_id: str, cap_pt: float) -> float:
    take = starred_take(data, prompt_id)
    scale, _ = _fit(take, data, cap_pt)
    xs = [p[0] for s in take["strokes"] for p in s["points"]]
    return (max(xs) - min(xs)) * scale
