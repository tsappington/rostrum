"""The timing map: narration and ink on one clock.

A Timeline is assembled beat by beat: `say` places a narration line at
the cursor (or at an explicit time, for speech that rides over ink),
`ink` registers a placed, timed write. Everything downstream reads from
here — the audio master, the ink schedule, and the captions all come
from this one structure, which is what keeps voice and pen locked.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .ink import TimedPoint
from .tts import SR, Narrator


@dataclass
class Seg:
    t0: float
    audio: np.ndarray
    tokens: list[tuple[str, float, float]]
    text: str

    @property
    def dur(self) -> float:
        return len(self.audio) / SR

    @property
    def end(self) -> float:
        return self.t0 + self.dur

    def token_start(self, word_prefix: str) -> float:
        """Absolute time the first token starting with word_prefix begins."""
        for txt, a, _ in self.tokens:
            if txt.lower().startswith(word_prefix.lower()):
                return self.t0 + a
        return self.t0


class Timeline:
    def __init__(self, narrator: Narrator, t0: float = 0.6):
        self.n = narrator
        self.t = t0
        self.segs: list[Seg] = []
        self.inks: list[list[list[TimedPoint]]] = []

    def say(self, text: str, gap: float = 0.35, at: float | None = None) -> Seg:
        audio, toks = self.n.say(text)
        seg = Seg(self.t if at is None else at, audio, toks, text)
        self.segs.append(seg)
        self.t = max(self.t, seg.end) + (gap if at is None else 0.0)
        return seg

    def ink(self, timed: list[list[TimedPoint]]) -> float:
        """Register placed ink; returns its end time and advances the clock."""
        self.inks.append(timed)
        end = max(p.t for s in timed for p in s)
        self.t = max(self.t, end)
        return end

    def pause(self, d: float) -> None:
        self.t += d

    # ---- outputs ----------------------------------------------------------

    def all_ink(self) -> list[list[TimedPoint]]:
        strokes = [s for timed in self.inks for s in timed]
        return sorted(strokes, key=lambda s: s[0].t)

    def mix(self, tail: float = 1.0) -> np.ndarray:
        total = self.t + tail
        buf = np.zeros(int(total * SR), np.float32)
        for s in self.segs:
            i = int(s.t0 * SR)
            buf[i : i + len(s.audio)] += s.audio
        peak = float(np.abs(buf).max())
        if peak > 0:
            buf *= min(0.89 / peak, 1.0)
        return buf

    def srt(self) -> str:
        def fmt(t: float) -> str:
            h, rem = divmod(t, 3600)
            m, s = divmod(rem, 60)
            return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"

        def wrap(text: str, width: int = 42) -> str:
            words, lines, line = text.split(), [], ""
            for w in words:
                if line and len(line) + 1 + len(w) > width:
                    lines.append(line)
                    line = w
                else:
                    line = f"{line} {w}".strip()
            lines.append(line)
            return "\n".join(lines[:2]) if len(lines) <= 2 else "\n".join(
                [lines[0], " ".join(lines[1:])]
            )

        out = []
        segs = sorted(self.segs, key=lambda x: x.t0)
        for i, s in enumerate(segs, 1):
            end = s.end + 0.15
            if i < len(segs):                      # cues never overlap: a clip's
                end = min(end, segs[i].t0 - 0.03)  # silent tail cedes to the next
            out.append(f"{i}\n{fmt(s.t0)} --> {fmt(max(end, s.t0 + 0.3))}\n"
                       f"{wrap(s.text)}\n")
        return "\n".join(out)
