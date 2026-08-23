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
import math
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


class Library:
    """Round-robin take selection plus per-instance micro-humanization.

    A number that appears six times must never appear the same way twice
    — the viewer's repetition detector is sharp even when attention
    isn't. Two defenses, layered: each ink event draws a different
    captured take of its glyph (selection is a hash of the event key, so
    renders are reproducible; adjacent repeats of the same take are
    skipped when the library allows), and every instance is additionally
    micro-humanized — hair's-width jitters of scale, rotation, baseline,
    pace, and pressure, seeded by the same hash. With one take on file
    the second layer still guarantees variation; with five it reads as a
    hand, not a stamp.
    """

    def __init__(self, data: dict):
        self.data = data
        self._last: dict[str, int] = {}
        self._memo: dict[tuple[str, str], tuple[dict, int]] = {}

    def _usable(self, prompt_id: str) -> list[dict]:
        """Takes eligible for selection: interruption outliers excluded.

        A take whose duration is far beyond the prompt's median was
        stalled mid-capture (a pen-down hold survives even the replay
        gap clamp). With ten takes on file we can afford to be choosy.
        """
        takes = self.data["prompts"][prompt_id]["takes"]
        if len(takes) < 3:
            return takes
        durs = sorted(t["duration"] for t in takes)
        med = durs[len(durs) // 2]
        good = [t for t in takes if t["duration"] <= 3 * med]
        return good or takes

    def pick(self, prompt_id: str, event_key: str) -> tuple[dict, int]:
        key = (prompt_id, event_key)
        if key in self._memo:
            return self._memo[key]
        import hashlib
        h = int.from_bytes(
            hashlib.sha256(f"{prompt_id}|{event_key}".encode()).digest()[:8], "big"
        )
        takes = self._usable(prompt_id)
        idx = h % len(takes)
        if len(takes) > 1 and self._last.get(prompt_id) == idx:
            idx = (idx + 1) % len(takes)
        self._last[prompt_id] = idx
        self._memo[key] = (takes[idx], h)
        return self._memo[key]

    def width_pt(self, prompt_id: str, cap_pt: float, event_key: str) -> float:
        take, _ = self.pick(prompt_id, event_key)
        scale, _base = _fit(take, self.data, cap_pt)
        xs = [p[0] for s in take["strokes"] for p in s["points"]]
        return (max(xs) - min(xs)) * scale

    def timed(self, prompt_id: str, origin_pt: tuple[float, float], cap_pt: float,
              t0: float, event_key: str, **kw) -> list[list[TimedPoint]]:
        take, h = self.pick(prompt_id, event_key)
        return to_timed(self.data, prompt_id, origin_pt, cap_pt, t0=t0,
                        take=take, variant_seed=h, **kw)


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
    if cap_px < 8.0:                     # a flat mark (underline, dot) has no
        guide = take.get("guide") or data["guide"]   # cap of its own: borrow
        cap_px = guide["baseline"] - guide["cap"]    # the guide's SCALE only —
    return cap_pt / cap_px, float(base_y)            # position stays the ink's


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
    take: dict | None = None,
    variant_seed: int | None = None,
) -> list[list[TimedPoint]]:
    """Place one captured take on the page as renderer-ready timed points.

    origin_pt: page (x, y) where the take's left edge meets the baseline.
    pace > 1 slows the performance down; timing is otherwise verbatim,
    except pen-up pauses longer than max_gap seconds are clamped to it —
    a capture interruption should not replay as a frozen video.

    variant_seed switches on micro-humanization: hair's-width seeded
    jitters of scale, rotation, baseline, pace, and pressure, so two
    renders of the same take are similar but never identical.
    """
    take = take if take is not None else starred_take(data, prompt_id)
    scale, base_y = _fit(take, data, cap_pt)

    rot = 0.0
    base_j = 0.0
    p_gain = 1.0
    if variant_seed is not None:
        rng = np.random.default_rng(variant_seed)
        scale *= 1 + rng.normal(0, 0.02)
        rot = math.radians(rng.normal(0, 0.7))
        pace *= 1 + rng.normal(0, 0.05)
        # clamped absolutely: width-fit marks carry a fabricated cap, and
        # baseline wander must stay hair's-width regardless of that scale
        base_j = float(np.clip(rng.normal(0, 0.012) * cap_pt, -0.6, 0.6))
        p_gain = 1 + rng.normal(0, 0.05)
    cos_r, sin_r = math.cos(rot), math.sin(rot)

    all_xy = np.array([[p[0], p[1]] for s in take["strokes"] for p in s["points"]])
    cx, cy = all_xy.mean(axis=0)
    if rot:
        rx = cx + (all_xy[:, 0] - cx) * cos_r - (all_xy[:, 1] - cy) * sin_r
        x_min = float(rx.min())
    else:
        x_min = float(all_xy[:, 0].min())
    t_min = min(p[2] for s in take["strokes"] for p in s["points"])

    out: list[list[TimedPoint]] = []
    t_shift = 0.0
    prev_end: float | None = None
    for s in take["strokes"]:
        pts = _dedup(np.array(s["points"], dtype=float))  # x, y, t_ms, p
        xs = _smooth(pts[:, 0], smooth_passes)
        ys = _smooth(pts[:, 1], smooth_passes)
        if rot:
            xs, ys = (cx + (xs - cx) * cos_r - (ys - cy) * sin_r,
                      cy + (xs - cx) * sin_r + (ys - cy) * cos_r)
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

        if p_gain != 1.0:
            p = np.clip(p * p_gain, 0.30, 0.95)
        page_x = origin_pt[0] + (xs - x_min) * scale
        page_y = origin_pt[1] + (ys - base_y) * scale + base_j
        out.append([TimedPoint(ts[j], page_x[j], page_y[j], p[j]) for j in range(n)])
    return out


def take_width_pt(data: dict, prompt_id: str, cap_pt: float) -> float:
    take = starred_take(data, prompt_id)
    scale, _ = _fit(take, data, cap_pt)
    xs = [p[0] for s in take["strokes"] for p in s["points"]]
    return (max(xs) - min(xs)) * scale
