"""The full cut: every beat, both pages, one clock.

Eleven beats over two pages: cold open, pause-and-try, the Do Now
(equation, five facts, area), vocabulary with underlines landing on
spoken terms, a cut to page two, four Guided Practice rows with the
teacher's numbers drawn from the take library — no repeated instance
identical — and the close, with one circle around the final answer.

Camera: one constant-scale rostrum drift per page; moves ride
transitional narration and hold while the pen is down. Cut at the page
turn. Captions, audio, and ink all read from the same timing map.

  python -m tools.film            # render everything
  python -m tools.film schedule   # print the timing map, render nothing
"""

from __future__ import annotations

import sys
import time

import soundfile as sf

from rostrum import capture
from rostrum.page import find_blanks
from rostrum.render import MovingRostrum, mux, write_video
from rostrum.timeline import Timeline
from rostrum.tts import SR, Narrator

DATA = "assets/strokes/capture_ted_v3.json"

# ---- camera ---------------------------------------------------------------
VIEW = (536.0, 301.5)                      # 16:9 viewport, page points
X1, X2 = 32.0, 37.0                        # viewport left edge per page
UNION1 = (X1, 60.0, X1 + VIEW[0], 750.0)   # page 1 reachable area
UNION2 = (X2, 108.0, X2 + VIEW[0], 727.0)  # page 2 reachable area

# page-1 camera stops (viewport top y)
Y_OPEN, Y_P1, Y_SOLVE, Y_AREA, Y_VOCAB = 64.0, 130.0, 170.0, 215.0, 444.0
# page-2 camera stops
Y_ROW1, Y_ROW2, Y_ROW3, Y_ROW4 = 118.0, 225.0, 340.0, 420.0

# ---- page geometry --------------------------------------------------------
# Guided Practice table (from the PDF's own vector data)
COL_X = {"cpl": 306.0, "lay": 412.5, "vol": 519.0}      # column centers
ROW_BASE = [230.75, 356.85, 482.95, 609.05]             # writing baselines
CELL_CAP = 13.0

# vocabulary term underlines (from text search rects)
UL_VOLUME = (83.7, 499.0, 49.0)      # x, y, width
UL_UNITCUBE = (83.7, 644.5, 63.5)


def build():
    D = capture.load(DATA)
    lib = capture.Library(D)
    tl = Timeline(Narrator("af_bella", 0.92))
    bs = find_blanks(0)
    eq_b, count_b, fact_bs, area_b = bs[2], bs[3], bs[4:9], bs[9]
    keys1: list[tuple[float, float, float]] = [(0.0, X1, Y_OPEN)]
    keys2: list[tuple[float, float, float]] = []

    def cam1(y, dur=1.4, at=None):
        t = tl.t if at is None else at
        keys1.append((t, X1, keys1[-1][2]))
        keys1.append((t + dur, X1, y))

    def cam2(y, dur=1.4, at=None):
        t = tl.t if at is None else at
        prev_y = keys2[-1][2] if keys2 else y
        keys2.append((t, X2, prev_y))
        keys2.append((t + dur, X2, y))

    def blank_ink(prompt, blank, cap, t0, key, align="center"):
        w = lib.width_pt(prompt, cap, key)
        x = blank.x0 + 8.0 if align == "left" else blank.x0 + (blank.width - w) / 2
        return tl.ink(lib.timed(prompt, (x, blank.y - 1.2), cap, t0, key))

    def cell_ink(prompt, row, col, t0, key):
        w = lib.width_pt(prompt, CELL_CAP, key)
        return tl.ink(lib.timed(prompt, (COL_X[col] - w / 2, ROW_BASE[row]),
                                CELL_CAP, t0, key))

    def width_fit(prompt, target_w, origin, t0, key):
        k = lib.width_pt(prompt, 10.0, key) / 10.0
        return tl.ink(lib.timed(prompt, origin, target_w / k, t0, key))

    # ================= PART A — page 1 =================
    # Beat 0 — cold open
    tl.say("Hi mathematicians — welcome back. Today we're learning how to "
           "measure space — how much room something takes up.", gap=0.4)
    tl.say("By the end of this video, you'll be able to find the volume of a "
           "box, just by counting cubes.", gap=0.5)

    # Beat 1 — pause and try
    tl.say("But first, let's warm up with something you already know. Pause "
           "the video here, and try the Do Now on your own.", gap=0.3)
    tl.say("When you're ready, press play, and we'll go through it together.",
           gap=0.9)

    # Beat 2 — Do Now problem 1
    s = tl.say("Let's check it. Three rows… of four squares.", gap=0.5)
    cam1(Y_P1, at=s.t0 + 0.2)
    tl.say("I could count them one by one — or I can multiply. Three rows, "
           "four in each row:", gap=0.3)
    eq_t0 = tl.t
    eq_end = blank_ink("eq", eq_b, 14, eq_t0, "b2.eq", align="left")
    tl.say("Three times four… is twelve.", at=eq_t0 + 0.45 * (eq_end - eq_t0))
    tl.t = max(tl.t, eq_end) + 0.55
    s = tl.say("Twelve squares in all.", gap=0.0)
    blank_ink("n12", count_b, 12, s.token_start("Twelve") + 0.1, "b2.count")
    tl.pause(0.7)

    # Beat 3 — the five facts
    s = tl.say("Quick practice — say them with me.", gap=0.45)
    cam1(Y_SOLVE, at=s.t0 + 0.1)
    facts = [("Three times four —", "Twelve.", "n12"),
             ("Four times two —", "Eight.", "n8"),
             ("Two times five —", "Ten.", "n10"),
             ("Five times six —", "Thirty.", "n30"),
             ("Four times seven —", "Twenty-eight.", "n28")]
    for i, ((prompt_text, answer, take), blank) in enumerate(zip(facts, fact_bs)):
        tl.say(prompt_text, gap=0.12)
        t_ink = tl.t
        end = blank_ink(take, blank, 11, t_ink, f"b3.f{i + 1}")
        ans = tl.say(answer, at=max(t_ink + 0.15, end - 0.55))
        tl.t = max(end, ans.end) + 0.4

    # Beat 4 — area, the springboard
    s = tl.say("One more warm-up. The area of a rectangle — five units, by "
               "two units.", gap=0.35)
    cam1(Y_AREA, at=s.t0 + 0.2)
    s = tl.say("Area is length times width. Five times two:", gap=0.25)
    t_ink = tl.t
    end = blank_ink("n10", area_b, 12, t_ink, "b4.area")
    ans = tl.say("Ten square units.", at=max(t_ink + 0.15, end - 0.5))
    tl.t = max(end, ans.end) + 0.5
    s = tl.say("Area covers a flat shape. Keep that idea close — we're about "
               "to give it another dimension.", gap=0.7)
    cam1(Y_VOCAB, dur=2.2, at=s.t0 + 0.6)     # the long drift down to vocab

    # Beat 5 — vocabulary
    s = tl.say("Two words for today. Volume — the amount of space a solid "
               "figure takes up. We measure it in cubic units.", gap=0.4)
    width_fit("mUnder", UL_VOLUME[2], (UL_VOLUME[0], UL_VOLUME[1]),
              s.token_start("Volume"), "v.volume")
    tl.say("Look at the picture — this box is packed with twelve unit cubes. "
           "So its volume… is twelve cubic units.", gap=0.45)
    s = tl.say("And a unit cube — a cube one unit long, one unit wide, one "
               "unit tall. The building block we measure with.", gap=0.4)
    width_fit("mUnder", UL_UNITCUBE[2], (UL_UNITCUBE[0], UL_UNITCUBE[1]),
              s.token_start("unit") + 0.05, "v.unitcube")
    tl.say("That's all volume is. Count the cubes.", gap=0.4)
    tl.pause(0.7)

    t_cut = tl.t                              # ---- the page turn ----
    n_ink_a = len(tl.inks)
    keys2.append((t_cut, X2, Y_ROW1))

    # ================= PART B — page 2 =================
    # Beat 6 — practice row 1
    tl.say("Now let's practice together — fill in your table as we go.",
           gap=0.45)
    s = tl.say("Prism one. How many cubes in one layer? Count the top with "
               "me — four rows of three: twelve.", gap=0.15)
    cell_ink("n12", 0, "cpl", s.token_start("twelve") - 0.15, "gp1.cpl")
    tl.pause(0.25)
    s = tl.say("How many layers? Just one.", gap=0.1)
    end = cell_ink("n1", 0, "lay", s.token_start("one") - 0.1, "gp1.lay")
    tl.t = max(tl.t, end) + 0.25
    s = tl.say("So the volume: twelve times one —", gap=0.12)
    end = cell_ink("n12", 0, "vol", tl.t, "gp1.vol")
    ans = tl.say("Twelve cubic units.", at=max(tl.t + 0.1, end - 0.6))
    tl.t = max(end, ans.end) + 0.35
    tl.say("One layer — so the volume matches the area count. Flat… but "
           "already three-D.", gap=0.7)

    # Beat 7 — row 2, the surprise
    s = tl.say("Prism two looks totally different — tall, and thin. Cubes in "
               "one layer? Four.", gap=0.15)
    cam2(Y_ROW2, at=s.t0 + 0.2)
    end = cell_ink("n4", 1, "cpl", s.token_start("Four") - 0.1, "gp2.cpl")
    tl.t = max(tl.t, end) + 0.25
    s = tl.say("Layers? One, two, three.", gap=0.12)
    end = cell_ink("n3", 1, "lay", s.token_start("three") - 0.1, "gp2.lay")
    tl.t = max(tl.t, end) + 0.25
    s = tl.say("Four times three —", gap=0.12)
    end = cell_ink("n12", 1, "vol", tl.t, "gp2.vol")
    ans = tl.say("Twelve again! Different shape — same volume.",
                 at=max(tl.t + 0.1, end - 0.4))
    tl.t = max(end, ans.end) + 0.3
    tl.say("Volume doesn't care what a shape looks like. It counts cubes.",
           gap=0.7)

    # Beat 8 — row 3, the thesis
    s = tl.say("Prism three. Look closely — it's prism one, with a second "
               "layer stacked on top.", gap=0.3)
    cam2(Y_ROW3, at=s.t0 + 0.2)
    s = tl.say("Twelve cubes in a layer.", gap=0.12)
    end = cell_ink("n12", 2, "cpl", s.token_start("Twelve") + 0.1, "gp3.cpl")
    tl.t = max(tl.t, end) + 0.25
    s = tl.say("Two layers.", gap=0.12)
    end = cell_ink("n2", 2, "lay", s.token_start("Two") + 0.1, "gp3.lay")
    tl.t = max(tl.t, end) + 0.3
    s = tl.say("Twelve… twenty-four.", gap=0.12)
    end = cell_ink("n24", 2, "vol", s.t0 + 0.3, "gp3.vol")
    tl.t = max(tl.t, end) + 0.4
    tl.say("Volume is area — stacked.", gap=0.8)

    # Beat 9 — row 4, this one's yours
    s = tl.say("Last one — and this one's yours. Pause here, and try prism "
               "four.", gap=1.6)
    cam2(Y_ROW4, at=s.t0 + 0.2)
    s = tl.say("Ready? Check it with me. Five by four — twenty cubes in a "
               "layer.", gap=0.15)
    end = cell_ink("n20", 3, "cpl", s.token_start("twenty") - 0.1, "gp4.cpl")
    tl.t = max(tl.t, end) + 0.25
    s = tl.say("Two layers.", gap=0.12)
    end = cell_ink("n2", 3, "lay", s.token_start("Two") + 0.1, "gp4.lay")
    tl.t = max(tl.t, end) + 0.3
    s = tl.say("Twenty times two —", gap=0.12)
    end = cell_ink("n40", 3, "vol", tl.t, "gp4.vol")
    ans = tl.say("Forty cubic units.", at=max(tl.t + 0.1, end - 0.5))
    tl.t = max(end, ans.end) + 0.4
    s = tl.say("If you wrote forty — you've got volume.", gap=0.6)
    # one circle around the final answer, landing on "you've got volume"
    circ_w = lib.width_pt("n40", CELL_CAP, "gp4.vol") * 1.9
    width_fit("mCircle", circ_w,
              (COL_X["vol"] - circ_w / 2, ROW_BASE[3] + 4.5),
              s.token_start("you've") - 0.1, "gp4.circle")
    tl.pause(0.5)

    # Beat 10 — close
    tl.say("So: cubes per layer, times the number of layers. That's volume — "
           "space, measured in cubes.", gap=0.35)
    tl.say("Next lesson, we'll find volume when we can't see every cube. "
           "See you there.", gap=0.0)
    tl.pause(1.8)

    return tl, keys1, keys2, t_cut, n_ink_a


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "render"
    tl, keys1, keys2, t_cut, n_ink_a = build()
    total = tl.t
    print(f"total {total:.1f}s ({total/60:.1f} min) · cut at {t_cut:.1f}s · "
          f"{len(tl.segs)} lines · {len(tl.inks)} ink events")

    if mode == "schedule":
        for s in sorted(tl.segs, key=lambda x: x.t0):
            print(f"  {s.t0:6.2f}-{s.end:6.2f}  SAY  {s.text[:64]}")
        for timed in tl.inks:
            t0 = timed[0][0].t
            t1 = max(p.t for st in timed for p in st)
            print(f"  {t0:6.2f}-{t1:6.2f}  INK")
        return

    ink_a = sorted([s for timed in tl.inks[:n_ink_a] for s in timed],
                   key=lambda s: s[0].t)
    ink_b = sorted([s for timed in tl.inks[n_ink_a:] for s in timed],
                   key=lambda s: s[0].t)
    cam_a = MovingRostrum(0, UNION1, VIEW, keys1)
    cam_b = MovingRostrum(1, UNION2, VIEW, keys2)

    fps = 60
    n = int(total * fps)
    t_start = time.time()

    def frames():
        for i in range(n):
            t = i / fps
            if t < t_cut:
                cam_a.ink.draw_until(ink_a, t)
                yield cam_a.frame(t)
            else:
                cam_b.ink.draw_until(ink_b, t)
                yield cam_b.frame(t)
            if i % 900 == 0:
                el = time.time() - t_start
                print(f"  frame {i}/{n}  ({el:.0f}s, "
                      f"{i / max(el, 1):.0f} fps)", flush=True)

    video = write_video("out/film_silent.mp4", frames(), fps=fps)
    sf.write("out/film_audio.wav", tl.mix(), SR)
    out = mux(video, "out/film_audio.wav", "out/volume_cubes_v1.mp4")
    with open("out/volume_cubes_v1.srt", "w") as f:
        f.write(tl.srt())
    print(f"{out}  {total:.1f}s, rendered in {time.time() - t_start:.0f}s")


if __name__ == "__main__":
    main()
