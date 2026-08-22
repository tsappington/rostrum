"""Track A spike: does synthetic ink read as writing?

Writes "3 × 4 = 12" on the actual Do Now equation blank of the guided
notes, with the full timing/pressure model. Still mode for fast visual
iteration, video mode for the real judgment call.

  python -m tools.spike_ink still
  python -m tools.spike_ink video
"""

from __future__ import annotations

import sys
import time

from rostrum.ink import time_strokes
from rostrum.render import Rostrum, write_video
from rostrum.strokes import layout_phrase

# 16:9 camera on the Do Now block, full content width (page points)
REGION = (40.0, 132.0, 564.0, 426.75)
OUT = (1920, 1080)
PHRASE = "3 × 4 = 12"
ORIGIN = (212.0, 227.2)     # baseline-left on the Equation blank (y line = 228.4)
CAP_PT = 14.0


def build():
    strokes = layout_phrase(PHRASE, ORIGIN, CAP_PT, seed=7)
    # a beat of thought before the answer "12", a small settle before "="
    hesitations = {}
    seen_eq = False
    for i, s in enumerate(strokes):
        if s.glyph == "=" and not seen_eq:
            hesitations[i] = 0.18
            seen_eq = True
        if s.glyph == "1":
            hesitations[i] = 0.42
            break
    timed = time_strokes(strokes, t0=0.8, cap_pt=CAP_PT, seed=11,
                         hesitate_before=hesitations)
    return timed


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "still"
    timed = build()
    end_t = timed[-1][-1].t
    cam = Rostrum(0, REGION, OUT)

    if mode == "still":
        cam.ink.draw_until(timed, end_t + 1)
        cam.frame().save("out/spike_ink_still.png")
        print(f"out/spike_ink_still.png  (write time {end_t - 0.8:.2f}s)")
        return

    fps = 60
    total = end_t + 1.4
    n = int(total * fps)
    t_start = time.time()

    def frames():
        for i in range(n):
            cam.ink.draw_until(timed, i / fps)
            yield cam.frame()

    path = write_video("out/spike_ink.mp4", frames(), fps=fps, size=OUT)
    print(f"{path}  {n} frames, {total:.1f}s clip, rendered in {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
