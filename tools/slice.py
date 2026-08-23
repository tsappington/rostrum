"""The vertical slice: Beats 2-3, end to end.

Do Now problem 1 and the Solve row, taught by bella in Ted's hand —
narration with word timestamps, ink cued off those timestamps onto the
worksheet's real blanks, a rostrum drift between beats, captions from
the same timing map, audio mixed and muxed. This is the whole machine
in miniature; the full video is more beats, not more machinery.

  python -m tools.slice            # render everything
  python -m tools.slice schedule   # print the timing map, render nothing
"""

from __future__ import annotations

import sys
import time

import numpy as np
import soundfile as sf

from rostrum import capture
from rostrum.page import find_blanks
from rostrum.render import MovingRostrum, mux, write_video
from rostrum.timeline import Timeline
from rostrum.tts import SR, Narrator

DATA = "assets/strokes/capture_ted_v2.json"

# ---- the set ---------------------------------------------------------------
UNION = (50.0, 140.0, 530.0, 450.0)      # everything the camera can reach
VIEW = (480.0, 270.0)                    # 16:9 viewport in page points
POS_A = (50.0, 140.0)                    # Do Now problem 1
POS_B = (50.0, 180.0)                    # drifted down to the Solve row


def blank_map():
    bs = find_blanks(0)
    assert abs(bs[2].y - 228.4) < 1 and abs(bs[4].y - 287.6) < 1, "page layout moved"
    return {"eq": bs[2], "count": bs[3],
            "facts": bs[4:9]}


def build():
    D = capture.load(DATA)
    tl = Timeline(Narrator("af_bella", 0.92))
    blanks = blank_map()

    def place(prompt: str, blank, cap: float, t0: float, align="center"):
        w = capture.take_width_pt(D, prompt, cap)
        x = blank.x0 + 8.0 if align == "left" else blank.x0 + (blank.width - w) / 2
        timed = capture.to_timed(D, prompt, (x, blank.y - 1.2), cap, t0=t0)
        return tl.ink(timed)

    # ---- Beat 2: Do Now problem 1 -----------------------------------------
    tl.say("Let's check it. Three rows… of four squares.", gap=0.55)
    tl.say("I could count them one by one — or I can multiply. "
           "Three rows, four in each row:", gap=0.3)
    eq_t0 = tl.t
    eq_end = place("eq", blanks["eq"], 14, eq_t0, align="left")
    tl.say("Three times four… is twelve.",
           at=eq_t0 + 0.45 * (eq_end - eq_t0))
    tl.t = max(tl.t, eq_end) + 0.55
    s = tl.say("Twelve squares in all.", gap=0.0)
    place("n12", blanks["count"], 12, s.token_start("Twelve") + 0.1)
    tl.pause(0.7)

    # ---- Beat 3: the Solve row, quickening --------------------------------
    s5 = tl.say("Quick practice — say them with me.", gap=0.45)
    move = (s5.t0 + 0.1, s5.t0 + 1.5)     # camera drifts during this line

    facts = [
        ("Three times four —", "Twelve.", "n12"),
        ("Four times two —", "Eight.", "n8"),
        ("Two times five —", "Ten.", "n10"),
        ("Five times six —", "Thirty.", "n30"),
        ("Four times seven —", "Twenty-eight.", "n28"),
    ]
    for (prompt_text, answer_text, take), blank in zip(facts, blanks["facts"]):
        tl.say(prompt_text, gap=0.12)
        t_ink = tl.t
        end = place(take, blank, 11, t_ink)
        ans = tl.say(answer_text, at=max(t_ink + 0.15, end - 0.55))
        tl.t = max(end, ans.end) + 0.4

    tl.pause(1.3)
    keys = [(0.0, *POS_A), (move[0], *POS_A), (move[1], *POS_B)]
    return tl, keys


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "render"
    tl, keys = build()
    total = tl.t

    if mode == "schedule":
        print(f"total {total:.1f}s · {len(tl.segs)} lines · "
              f"{sum(len(i) for i in tl.inks)} ink strokes")
        for s in sorted(tl.segs, key=lambda x: x.t0):
            print(f"  {s.t0:6.2f}-{s.end:6.2f}  SAY  {s.text}")
        for timed in tl.inks:
            t0 = timed[0][0].t
            t1 = max(p.t for st in timed for p in st)
            print(f"  {t0:6.2f}-{t1:6.2f}  INK  {len(timed)} strokes")
        return

    cam = MovingRostrum(0, UNION, VIEW, keys)
    ink_all = tl.all_ink()
    fps = 60
    n = int(total * fps)
    t_start = time.time()

    def frames():
        for i in range(n):
            t = i / fps
            cam.ink.draw_until(ink_all, t)
            yield cam.frame(t)
            if i % 600 == 0:
                print(f"  frame {i}/{n}  ({time.time()-t_start:.0f}s)")

    video = write_video("out/slice_silent.mp4", frames(), fps=fps)
    sf.write("out/slice_audio.wav", tl.mix(), SR)
    out = mux(video, "out/slice_audio.wav", "out/slice_beats23.mp4")
    with open("out/slice_beats23.srt", "w") as f:
        f.write(tl.srt())
    print(f"{out}  {total:.1f}s, rendered in {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
