"""The full cut: every beat, both pages, one clock.

Three kinds of life on the page, each with its own law. Ink writes on
the paper. Light falls on it — the glow idiom: row sweeps as the teacher
counts, the active fact box warming, labels and terms lifting, the unit
cube's three faces lighting on "long / wide / tall". And inside the
illustration panels — the windows — figures live: twelve unit cubes
pack the vocabulary box while she says so, and Prism 3's second layer
descends onto the first at "stacked on top". Nothing printed ever
deforms; everything on the student's physical page stays on ours.

  python -m tools.film                 # render everything
  python -m tools.film schedule        # print the timing map
  python -m tools.film audio af_sarah  # narration track only
  python -m tools.film clip A|B|C      # preview clips: A sweeps,
                                       # B vocabulary, C the landing
"""

from __future__ import annotations

import sys
import time
from types import SimpleNamespace

import soundfile as sf

from rostrum import capture, chip
from rostrum.chip import Wand
from rostrum.figures import Figure
from rostrum.glow import GlowTrack, rect
from rostrum.page import find_blanks
from rostrum.render import MovingRostrum, mux, write_video
from rostrum.timeline import Timeline
from rostrum.tts import SR, Narrator

DATA = "assets/strokes/capture_ted_v3.json"

# ---- camera ---------------------------------------------------------------
VIEW = (536.0, 301.5)
X1, X2 = 32.0, 37.0
UNION1 = (X1, 60.0, X1 + VIEW[0], 750.0)
UNION2 = (X2, 108.0, X2 + VIEW[0], 727.0)
Y_OPEN, Y_P1, Y_SOLVE, Y_AREA, Y_VOCAB = 64.0, 130.0, 170.0, 215.0, 444.0
Y_ROW1, Y_ROW2, Y_ROW3, Y_ROW4 = 118.0, 225.0, 340.0, 420.0

# ---- page geometry (from the PDF's own vector data) -----------------------
COL_X = {"cpl": 306.0, "lay": 412.5, "vol": 519.0}
ROW_BASE = [230.75, 356.85, 482.95, 609.05]
CELL_CAP = 13.0
TABLE_ROWS = [(161.2, 287.3), (287.3, 413.4), (413.4, 539.5), (539.5, 665.6)]
TABLE_X = (39.8, 572.2)

DN1 = (80.25, 204.75, 12.0, 4, 3)           # x0, y0, cell, cols, rows
DN3 = (125.25, 356.25, 12.0, 5, 2)
DN2_BOXES = [(118.5, 266.2, 201.0, 300.0), (208.5, 266.2, 291.8, 300.0),
             (299.2, 266.2, 381.8, 300.0), (389.2, 266.2, 471.8, 300.0),
             (479.2, 266.2, 561.8, 300.0)]
LABEL_5U = (142.2, 385.5, 168.2, 397.2)
LABEL_2U = (91.6, 361.0, 117.7, 372.7)
TERM_VOLUME = (83.7, 475.5, 132.7, 495.3)
TERM_UNITCUBE = (83.7, 621.0, 147.2, 640.8)

FIG_SLAB = (0, (425.0, 490.0, 526.0, 570.0))
FIG_UCUBE = (0, (440.0, 630.0, 510.0, 705.0))
FIG_PRISM3 = (1, (60.0, 415.0, 320.0, 545.0))

P2_ART = (127.0, 309.9, 191.7, 392.1)       # prism 2's cubes, page 2
WAND_DN1_X = DN1[0] - 11.0                  # the wand waits left of the grid
WAND_P2_X = P2_ART[2] + 13.0                # …and right of prism 2


def _row_y(g, i):
    return g[1] + g[2] * (i + 0.5)


def _p2_layers():
    """Prism 2's three layers as the art's own face polygons (bottom-up).
    A rectangular band overhangs a leaning isometric prism; lighting the
    faces themselves colors the cubes and nothing else."""
    fig = Figure.extract(1, (120.0, 303.0, 200.0, 400.0))
    tops = [min(sum(y for _, y in f.verts) / len(f.verts) for f in cube)
            for cube in fig.cubes]
    order = sorted(range(len(fig.cubes)), key=lambda i: -tops[i])
    per = len(fig.cubes) // 3
    return [[f.verts for i in order[k * per:(k + 1) * per]
             for f in fig.cubes[i]] for k in range(3)]


def _grid_rows(g):
    x0, y0, c, cols, rows = g
    return [rect(x0, y0 + r * c, x0 + cols * c, y0 + (r + 1) * c)
            for r in range(rows)]


def _grid_cols(g):
    x0, y0, c, cols, rows = g
    return [rect(x0 + k * c, y0, x0 + (k + 1) * c, y0 + rows * c)
            for k in range(cols)]


def build(voice: str = "af_sarah", speed: float = 0.88):
    D = capture.load(DATA)
    lib = capture.Library(D)
    tl = Timeline(Narrator(voice, speed))
    bs = find_blanks(0)
    eq_b, count_b, fact_bs, area_b = bs[2], bs[3], bs[4:9], bs[9]

    keys1 = [(0.0, X1, Y_OPEN)]
    keys2: list[tuple[float, float, float]] = []
    glow1, glow2 = GlowTrack(), GlowTrack()
    figs: list[tuple[int, Figure, dict]] = []
    wands: list[Wand] = []
    marks: dict[str, float] = {}

    def cam1(y, dur=1.4, at=None):
        t = tl.t if at is None else at
        keys1.append((t, X1, keys1[-1][2]))
        keys1.append((t + dur, X1, y))
        return t + dur                        # when the camera settles

    def cam2(y, dur=1.4, at=None):
        t = tl.t if at is None else at
        prev_y = keys2[-1][2] if keys2 else y
        keys2.append((t, X2, prev_y))
        keys2.append((t + dur, X2, y))
        return t + dur

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

    def row_glow(track, row_band, t_in, t_out):
        track.add(rect(TABLE_X[0], row_band[0], TABLE_X[1], row_band[1]),
                  t_in, t_out, max_alpha=38, radius=6, fade_out=0.8)

    def count_along(after_end, words=("One,", "Two,", "Three."),
                    cad=1.5, lead_gap=0.55):
        """Speak a count with the timeline as metronome. Each word is its
        own segment, placed so the SPOKEN words tick every `cad` seconds
        (Kokoro pads short clips with silence — clip starts don't count).
        Returns the moments the words actually sound."""
        times: list[float] = []
        for w in words:
            _, toks = tl.n.say(w)               # cached probe: word's own lead
            lead = next(a for txt, a, _ in toks if txt[0].isalnum())
            at = (after_end + lead_gap - lead) if not times \
                else times[-1] + cad - lead
            tl.say(w, at=at)
            times.append(at + lead)
        return times

    # ================= PART A — page 1 =================
    # Beat 0 — cold open
    tl.say("Hi mathematicians — welcome back. Today we're learning how to "
           "measure space — how much room something takes up.", gap=0.4)
    tl.say("By the end of this video, you'll be able to find the volume of "
           "a solid figure, just by counting cubes.", gap=0.5)

    # Beat 1 — pause and try
    s_pause = tl.say("But first, let's warm up with something you already "
                     "know. Pause the video here, and try the Do Now on "
                     "your own.", gap=0.3)
    s_resume = tl.say("When you're ready, press play, and we'll go through "
                      "it together.", gap=0.9)
    chips = [(s_pause.token_start("Pause"), s_resume.end + 0.5)]

    # Beat 2 — Do Now problem 1: count the rows out loud, then multiply.
    # The counts are separate segments spaced by the timeline, not by the
    # narrator's own prosody — Kokoro rushes an in-sentence count, and a
    # count-along has to breathe.
    s = tl.say("Let's check it. Count the rows with me:", gap=0.0)
    marks["A"] = s.t0 - 0.4
    cam1(Y_P1, at=s.t0 + 0.2)
    rows = _grid_rows(DN1)
    counts = count_along(s.end, cad=1.5)
    s = tl.say("Three rows.", at=counts[2] + 1.15, gap=0.5)
    row_hold = s.end + 0.6
    for t_c, shape in zip(counts, rows):
        glow1.add(shape, t_c, row_hold, radius=2)  # cumulative: rows stay lit
    # the flourish: the last-counted row blinks twice — a visual period
    for tb in (counts[2] + 0.15, counts[2] + 0.55):
        glow1.add(rows[2], tb, tb + 0.2, fade_in=0.1, fade_out=0.12,
                  max_alpha=70, radius=2)
    wands.append(Wand(0, [(counts[i], WAND_DN1_X, _row_y(DN1, i))
                          for i in range(3)],
                      t_in=counts[0] - 0.4, t_out=counts[2] + 0.9,
                      flourish=[counts[2] + 0.12]))
    # …and the columns get the same treatment: count, light, hop
    s = tl.say("And how many squares in each row? Count with me:", gap=0.0)
    cols = _grid_cols(DN1)
    col_counts = count_along(s.end, words=("One,", "Two,", "Three,", "Four."),
                             cad=1.15, lead_gap=0.45)
    s = tl.say("Four in each row.", at=col_counts[3] + 1.05, gap=0.4)
    col_hold = s.end + 0.5
    for t_c, shape in zip(col_counts, cols):
        glow1.add(shape, t_c, col_hold, radius=2)
    for tb in (col_counts[3] + 0.15, col_counts[3] + 0.55):
        glow1.add(cols[3], tb, tb + 0.2, fade_in=0.1, fade_out=0.12,
                  max_alpha=70, radius=2)
    wands.append(Wand(0, [(col_counts[k], DN1[0] + DN1[2] * (k + 0.5),
                           DN1[1] - 7.0) for k in range(4)],
                      t_in=col_counts[0] - 0.4, t_out=col_counts[3] + 0.9,
                      flourish=[col_counts[3] + 0.12]))
    tl.t = max(tl.t, col_hold - 0.15)
    s = tl.say("Now, I could count every square, one by one — or I can "
               "multiply: three rows of four.", gap=0.3)
    g = DN1
    glow1.add(rect(g[0], g[1], g[0] + g[3] * g[2], g[1] + g[4] * g[2]),
              s.token_start("multiply"), s.end, max_alpha=60, radius=2)
    eq_t0 = tl.t
    eq_end = blank_ink("eq", eq_b, 14, eq_t0, "b2.eq", align="left")
    tl.say("Three times four… is twelve.", at=eq_t0 + 0.45 * (eq_end - eq_t0))
    tl.t = max(tl.t, eq_end) + 0.55
    s = tl.say("Twelve squares in all.", gap=0.0)
    blank_ink("n12", count_b, 12, s.token_start("Twelve") + 0.1, "b2.count")
    tl.pause(0.7)
    marks["A_end"] = tl.t

    # Beat 3 — the five facts, each box warming as it's worked
    s = tl.say("Quick practice — say them with me.", gap=0.45)
    cam1(Y_SOLVE, at=s.t0 + 0.1)
    facts = [("Three times four —", "is twelve.", "n12"),
             ("Four times two —", "is eight.", "n8"),
             ("Two times five —", "is ten.", "n10"),
             ("Five times six —", "is thirty.", "n30"),
             ("Four times seven —", "is twenty-eight.", "n28")]
    for i, ((prompt_text, answer, take), blank) in enumerate(zip(facts, fact_bs)):
        sp = tl.say(prompt_text, gap=0.12)
        t_ink = tl.t
        end = blank_ink(take, blank, 11, t_ink, f"b3.f{i + 1}")
        ans = tl.say(answer, at=max(t_ink + 0.15, end - 0.55))
        b = DN2_BOXES[i]
        glow1.add(rect(*b), sp.t0 + 0.05, ans.end + 0.15, max_alpha=50,
                  radius=8)
        tl.t = max(end, ans.end) + 0.4

    # Beat 4 — area: labels lift, the grid sweeps again
    s = tl.say("One more warm-up: area. This rectangle is five units long… "
               "and two units wide.", gap=0.35)
    cam1(Y_AREA, at=s.t0 + 0.2)
    t5 = s.token_start("five")
    glow1.add(rect(*LABEL_5U, pad=2.5), t5, t5 + 1.2, radius=3, max_alpha=75)
    glow1.sweep(_grid_cols(DN3), t5 + 0.1, step=0.22, hold=0.5, radius=2)
    t2 = s.token_start("two")
    glow1.add(rect(*LABEL_2U, pad=2.5), t2, t2 + 1.2, radius=3, max_alpha=75)
    glow1.sweep(_grid_rows(DN3), t2 + 0.1, step=0.3, hold=0.5, radius=2)
    s = tl.say("Area is length times width. Five times two:", gap=0.25)
    t_ink = tl.t
    end = blank_ink("n10", area_b, 12, t_ink, "b4.area")
    ans = tl.say("Ten square units.", at=max(t_ink + 0.15, end - 0.5))
    tl.t = max(end, ans.end) + 0.5
    s = tl.say("So area counts the squares that cover a flat shape. Keep "
               "that idea close — we're about to give it a third dimension.",
               gap=0.7)
    cam1(Y_VOCAB, dur=2.2, at=s.t0 + 0.6)

    # Beat 5 — vocabulary: terms lift, the box packs, the cube's faces light
    s = tl.say("Two words for today. Volume — the amount of space a solid "
               "figure takes up. We measure it in cubic units.", gap=0.4)
    marks["B"] = s.t0 - 0.4
    tv = s.token_start("Volume")
    glow1.add(rect(*TERM_VOLUME, pad=3), tv, tv + 2.0, radius=3, max_alpha=70)
    s2 = tl.say("Now watch the example — a box, packed with twelve unit "
                "cubes.", gap=0.15)
    slab = Figure.extract(*FIG_SLAB)
    t_pack = s2.token_start("packed")
    figs.append((0, slab, {"kind": "assemble", "t0": t_pack, "stagger": 0.16,
                           "drop": 0.32, "drop_h": 14.0,
                           "cover_from": 0.0, "settle": 0.4}))
    t_packed = t_pack + (len(slab.cubes) - 1) * 0.16 + 0.32
    tl.t = max(tl.t, t_packed + 0.25)          # let the last cube land
    tl.say("Twelve cubes fit inside — so its volume is twelve cubic units.",
           gap=0.45)
    s3 = tl.say("And a unit cube — a cube one unit long, one unit wide, one "
                "unit tall. The building block we measure with.", gap=0.4)
    tu = s3.token_start("unit")
    glow1.add(rect(*TERM_UNITCUBE, pad=3), tu, tu + 2.0, radius=3,
              max_alpha=70)
    ucube = Figure.extract(*FIG_UCUBE)
    faces = {f.fill: f.verts for f in ucube.cubes[0]}
    for word, tone in (("long", (207, 196, 180)), ("wide", (230, 222, 208)),
                       ("tall", (250, 246, 241))):
        tw = s3.token_start(word)
        glow1.add(faces[tone][:4], tw, tw + 0.75, max_alpha=95, fade_in=0.18)
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
               "me — four rows of three… is twelve.", gap=0.15)
    r1_t0 = s.t0
    cell_ink("n12", 0, "cpl", s.token_start("twelve") - 0.15, "gp1.cpl")
    tl.pause(0.25)
    s = tl.say("How many layers? Just one.", gap=0.1)
    end = cell_ink("n1", 0, "lay", s.token_start("one") - 0.1, "gp1.lay")
    tl.t = max(tl.t, end) + 0.25
    s = tl.say("So the volume: twelve times one —", gap=0.12)
    end = cell_ink("n12", 0, "vol", tl.t, "gp1.vol")
    ans = tl.say("Twelve cubic units.", at=max(tl.t + 0.1, end - 0.6))
    tl.t = max(end, ans.end) + 0.35
    row_glow(glow2, TABLE_ROWS[0], r1_t0, tl.t)
    tl.say("Just one layer — so counting the cubes felt like counting the "
           "squares. Flat… but already three-D.", gap=0.7)

    # Beat 7 — row 2, the surprise
    s = tl.say("Prism two looks totally different — tall, and thin. Cubes in "
               "one layer? Four.", gap=0.15)
    r2_t0 = s.t0
    marks["C"] = s.t0 - 0.4
    cam2(Y_ROW2, at=s.t0 + 0.2)
    end = cell_ink("n4", 1, "cpl", s.token_start("Four") - 0.1, "gp2.cpl")
    tl.t = max(tl.t, end) + 0.25
    s = tl.say("Layers? Count them with me:", gap=0.0)
    lc = count_along(s.end, cad=1.35, lead_gap=0.45)
    tl.t = max(tl.t, lc[2] + 1.0)
    layer_hold = lc[2] + 1.0
    for t_c, shape in zip(lc, _p2_layers()):
        glow2.add(shape, t_c, layer_hold, max_alpha=55)
    wands.append(Wand(1, [(lc[i], WAND_P2_X,
                           P2_ART[3] - (P2_ART[3] - P2_ART[1]) / 3.0
                           * (i + 0.5)) for i in range(3)],
                      t_in=lc[0] - 0.4, t_out=lc[2] + 0.9,
                      flourish=[lc[2] + 0.12]))
    end = cell_ink("n3", 1, "lay", lc[2] - 0.05, "gp2.lay")
    tl.t = max(tl.t, end, layer_hold) + 0.25
    s = tl.say("Four times three —", gap=0.12)
    end = cell_ink("n12", 1, "vol", tl.t, "gp2.vol")
    ans = tl.say("Twelve again! A different prism — the same volume.",
                 at=max(tl.t + 0.1, end - 0.4))
    tl.t = max(end, ans.end) + 0.3
    row_glow(glow2, TABLE_ROWS[1], r2_t0, tl.t)
    tl.say("Volume doesn't care what a prism looks like. It counts the "
           "cubes inside.", gap=0.7)

    # Beat 8 — row 3: the thesis, and the layer lands
    s = tl.say("Prism three. Look closely — it's prism one, with a second "
               "layer stacked on top.", gap=0.3)
    r3_t0 = s.t0
    arrive = cam2(Y_ROW3, at=s.t0 + 0.2)
    prism3 = Figure.extract(*FIG_PRISM3)
    bottom, top = prism3.layer_split()
    # arrival-only: prism 3 shows just its bottom layer — prism one —
    # from the page turn onward; the second layer descends on "stacked",
    # after the camera has settled on the row
    t_stack = max(s.token_start("stacked") - 0.55, arrive + 1.0)
    figs.append((1, prism3, {"kind": "land", "t0": t_stack, "dur": 0.9,
                             "drop_h": 22.0, "static": bottom, "moving": top,
                             "cover_from": t_cut, "fade_in": 0.15,
                             "settle": 0.4}))
    s = tl.say("We already counted this layer — twelve cubes.", gap=0.12)
    end = cell_ink("n12", 2, "cpl", s.token_start("twelve") + 0.1, "gp3.cpl")
    tl.t = max(tl.t, end) + 0.25
    s = tl.say("Now there are two layers.", gap=0.12)
    end = cell_ink("n2", 2, "lay", s.token_start("two") + 0.1, "gp3.lay")
    tl.t = max(tl.t, end) + 0.3
    s = tl.say("Twelve times two — twenty-four cubic units.", gap=0.12)
    end = cell_ink("n24", 2, "vol", s.token_start("twenty") - 0.1, "gp3.vol")
    tl.t = max(tl.t, end) + 0.4
    row_glow(glow2, TABLE_ROWS[2], r3_t0, tl.t)
    tl.say("Volume is area — stacked.", gap=0.8)
    marks["C_end"] = tl.t

    # Beat 9 — row 4, this one's yours
    s9 = tl.say("Last one — and this one's yours. Pause here, and try prism "
                "four.", gap=1.6)
    r4_t0 = s9.t0
    cam2(Y_ROW4, at=s9.t0 + 0.2)
    s = tl.say("Ready? Check it with me. Five by four — twenty cubes in a "
               "layer.", gap=0.15)
    chips.append((s9.token_start("Pause"), s.t0 - 0.15))
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
    circ_w = lib.width_pt("n40", CELL_CAP, "gp4.vol") * 1.9
    width_fit("mCircle", circ_w,
              (COL_X["vol"] - circ_w / 2, ROW_BASE[3] + 4.5),
              s.token_start("you've") - 0.1, "gp4.circle")
    row_glow(glow2, TABLE_ROWS[3], r4_t0, tl.t)
    tl.pause(0.5)

    # Beat 10 — close
    tl.say("So: cubes per layer, times the number of layers. That's volume — "
           "space, measured in cubic units.", gap=0.35)
    tl.say("Next lesson, we'll find volume when we can't see every cube. "
           "See you there.", gap=0.0)
    tl.pause(1.8)

    return SimpleNamespace(tl=tl, keys1=keys1, keys2=keys2, t_cut=t_cut,
                           n_ink_a=n_ink_a, chips=chips, glow1=glow1,
                           glow2=glow2, figs=figs, wands=wands, marks=marks)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "render"
    if mode == "clip":
        voice, speed = "af_sarah", 0.88
    else:
        voice = sys.argv[2] if len(sys.argv) > 2 else "af_sarah"
        speed = float(sys.argv[3]) if len(sys.argv) > 3 else 0.88
    f = build(voice, speed)
    tl, t_cut = f.tl, f.t_cut
    total = tl.t
    print(f"total {total:.1f}s ({total/60:.1f} min) · cut at {t_cut:.1f}s · "
          f"{len(tl.segs)} lines · {len(tl.inks)} ink events · "
          f"{len(f.glow1.events) + len(f.glow2.events)} glows · "
          f"{len(f.figs)} figures · {len(f.wands)} wands · {voice} @{speed}")

    if mode == "schedule":
        for s in sorted(tl.segs, key=lambda x: x.t0):
            print(f"  {s.t0:6.2f}-{s.end:6.2f}  SAY  {s.text[:64]}")
        return
    if mode == "audio":
        path = f"out/narration_{voice.replace('af_', '').replace('am_', '')}.wav"
        sf.write(path, tl.mix(), SR)
        print(path)
        return

    ink_a = sorted([s for timed in tl.inks[:f.n_ink_a] for s in timed],
                   key=lambda s: s[0].t)
    ink_b = sorted([s for timed in tl.inks[f.n_ink_a:] for s in timed],
                   key=lambda s: s[0].t)
    cam_a = MovingRostrum(0, UNION1, VIEW, f.keys1)
    cam_b = MovingRostrum(1, UNION2, VIEW, f.keys2)
    figs1 = [(fig, spec) for pg, fig, spec in f.figs if pg == 0]
    figs2 = [(fig, spec) for pg, fig, spec in f.figs if pg == 1]

    def under_for(cam, track, page_figs, t):
        def under(comp, box):
            # figures first, light after: the glow washes a drawn figure
            # exactly as it washes the print, so a dissolve never shifts
            # the cubes' tint under an active row highlight
            for fig, spec in page_figs:
                fig.render(comp, box, cam.scale, cam.union, t, spec)
            track.render(comp, box, cam.scale, cam.union, t)
        return under

    fps = 60
    if mode == "clip":
        which = sys.argv[2] if len(sys.argv) > 2 else "A"
        t0 = f.marks[which]
        t1 = {"A": f.marks["A_end"], "B": t_cut,
              "C": f.marks["C_end"]}[which]
        name = f"out/preview_{which}"
    else:
        t0, t1, name = 0.0, total, "out/volume_cubes_v3"

    i0, i1 = int(t0 * fps), int(t1 * fps)
    cam_a.ink.draw_until(ink_a, t0)          # fast-forward to the window
    cam_b.ink.draw_until(ink_b, t0)
    t_start = time.time()

    def frames():
        for i in range(i0, i1):
            t = i / fps
            if t < t_cut:
                cam_a.ink.draw_until(ink_a, t)
                fr = cam_a.frame(t, under_for(cam_a, f.glow1, figs1, t))
            else:
                cam_b.ink.draw_until(ink_b, t)
                fr = cam_b.frame(t, under_for(cam_b, f.glow2, figs2, t))
            chip.overlay(fr, t, f.chips)
            for wd in f.wands:
                if (wd.page == 0) == (t < t_cut):
                    wd.draw(fr, t, cam_a if wd.page == 0 else cam_b)
            yield fr
            if (i - i0) % 900 == 0:
                el = time.time() - t_start
                print(f"  frame {i - i0}/{i1 - i0}  ({el:.0f}s)", flush=True)

    video = write_video(f"{name}_silent.mp4", frames(), fps=fps)
    audio = tl.mix()[int(t0 * SR):int(t1 * SR)]
    sf.write(f"{name}_audio.wav", audio, SR)
    out = mux(video, f"{name}_audio.wav", f"{name}.mp4")
    if mode != "clip":
        with open(f"{name}.srt", "w") as fh:
            fh.write(tl.srt())
    print(f"{out}  {t1 - t0:.1f}s, rendered in {time.time() - t_start:.0f}s")


if __name__ == "__main__":
    main()
