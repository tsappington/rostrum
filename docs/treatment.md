# Treatment — "Volume with Whole-Number Cubes"

*Grade 6 · Geometry · Lesson 1 · Skill 1 — an instructional video for the
Modern Classrooms Project performance task. Target runtime ~4:15 (brief
allows 2–5:00).*

## The film

A rostrum-camera documentary of a worksheet being taught. The frame never
leaves the page: the camera moves over the guided notes the student is
holding in their own hands, while a teacher's voice and blue ink fill it
in, together, in real time. No avatars, no hands, no cutaway world —
presence comes from performance: a voice that breathes, ink that
hesitates before the hard number and runs through the easy ones, sync
tight enough that the voice feels like it's writing.

The lesson's own structure is the dramatic arc, and the worksheet hands
us a motif: **12**. The Do Now's array is 12. The vocabulary example is a
box of 12 cubes. Practice 1 and Practice 2 are both 12 — in completely
different shapes. The video's argument, stated once and proven three
times: **volume is a count, not an appearance — area, stacked.**

## Grammar

- **Camera:** one continuous instrument, and a single transition. Slow
  pushes into each region as it becomes the subject; lateral pans
  between problems; the camera settles and holds still whenever the pen
  is down. The one edit in the film is the page turn — a 0.7s dissolve
  in the silence between Vocabulary and Guided Practice, landing on the
  new section's own headline. Movement between beats, stillness during
  writing.
- **Ink:** one voice of blue (`#2D5FA8`) over the printed navy world.
  Answers on blanks; light annotation marks — always on the page's own
  artwork, never floating chrome.
- **Light:** the highlight wash is the ink's own blue — the teacher's
  attention in the teacher's color, and legible where a warm wash
  disappears into warm paper. Counting lights exactly ONE square per
  spoken count (count a thing, light a thing — a full-row wash reads
  as "which thing did I just count?"), cumulatively, so three lit
  squares down a column *are* "three rows". The wash also warms the
  active fact box, lifts labels and terms, and picks out the unit
  cube's faces on "long / wide / tall". Orange belongs to the glass
  alone.
- **The equation writes itself in tandem:** the captured "3×4=12" take
  replays in stages — "3" lands on the third count, "× 4" on the
  fourth column, "= 12" at the multiply — split at the take's own
  glyph gaps, so the equation builds with the count that proves it.
- **Figures (arrival-only):** the illustration panels are the one place
  the page comes alive, and their grammar is a single verb — *arrive*.
  The vocabulary box starts blank and cubes pack it as she says
  "packed"; Prism 3 sits as prism one until its second layer descends
  on "stacked". Nothing on the page ever fades out — disappearance
  means nothing in this lesson, while packing and stacking are the
  lesson. Drawn cubes are pixel-registered to the print, so a finished
  figure retires with no transition at all.
- **The glass:** two citizens, both gesture, both orange. The pause
  chip ("you act now") and the wand ("look here") — a dot that pops in,
  hops with each spoken count, double-pulses on the last one like a
  visual period, and pops out. The count-along idiom exists only where
  the wand can point honestly — the flat grid. A metronome count is a
  pointing gesture in audio; beside a foreshortened isometric solid,
  where no pointer can truthfully mark the layers, the film doesn't
  count at all — it just asks and answers.
- **Sound:** a single close-mic teacher voice (Kokoro-82M, open weights,
  word-timestamped). Room-tone silence between beats — the pauses are
  part of the instruction. No music.
- **Pacing for a 6th grader:** script at grade 5–6 reading level;
  narration ≈145 wpm with real pauses; two explicit Modern
  Classrooms-style pause-and-try prompts (Do Now, and Practice 4 as
  "this one's yours").
- **Captions:** an SRT emitted from the same timing map that drives the
  ink — one cue per spoken line, so the caption and the pen change
  together. (Kokoro's word timestamps would support word-level cues too;
  not emitted.)

## Beat sheet

| # | Beat | Camera | Runtime | Cumulative |
|---|------|--------|---------|-----------|
| 0 | Cold open — the promise | full page 1, slow push | 0:14 | 0:14 |
| 1 | Pause & try the Do Now | hold on Do Now block | 0:16 | 0:30 |
| 2 | Do Now 1 — array → equation | push to problem 1 | 0:30 | 1:00 |
| 3 | Do Now 2 — five facts, quickening | pan to Solve row | 0:25 | 1:25 |
| 4 | Do Now 3 — area, the springboard | pan to problem 3 | 0:20 | 1:45 |
| 5 | Vocabulary — volume, unit cube | push to vocab panel | 0:35 | 2:20 |
| 6 | Practice 1 — one layer = the area | page 2, table row 1 | 0:30 | 2:50 |
| 7 | Practice 2 — different shape, same 12 | row 2 | 0:25 | 3:15 |
| 8 | Practice 3 — area, stacked (+ the one supplemental) | row 3 | 0:25 | 3:40 |
| 9 | Practice 4 — "this one's yours" | row 4 | 0:25 | 4:05 |
| 10 | Close — the formula in one breath | pull back, full page 2 | 0:12 | 4:17 |

## Script v0 (historical)

The shooting script now lives in `tools/film.py` (v3: one vocabulary
spine — squares → cubes → prism; metronome-placed count-alongs; carrier
words on answers; connective reasoning modeled on the strongest
exemplar screencast). `python -m tools.film schedule` prints it with
live timings. v0 below is kept as the record of the first draft.

All numbers below are verified by `rostrum.verify` against
`lesson/volume_cubes.yaml`, the printed page, and the page's own artwork.
`[INK: …]` marks writing; `[MARK: …]` marks annotation on the page art.

**0 — Cold open.** "Hi mathematicians — welcome back. Today we're
learning how to measure *space* — how much room something takes up. By
the end of this video, you'll be able to find the volume of a box just by
counting cubes."

**1 — Pause.** "But first, let's warm up with something you already
know. Pause the video here, and try the Do Now on your own. When you're
ready, press play, and we'll go through it together."

**2 — Do Now 1.** "Let's check it. Three rows… of four squares.
[MARK: pulse each row] I could count them one by one — or I can
multiply. Three rows, four in each row: [INK: 3 × 4 = 12] three times
four is twelve. [INK: 12] Twelve squares in all."

**3 — Do Now 2.** "Quick practice — say them with me. Three times four —
[INK: 12] twelve. Four times two — [INK: 8] eight. Two times five —
[INK: 10] ten. Five times six — [INK: 30] thirty. Four times seven —
[INK: 28] twenty-eight."

**4 — Do Now 3.** "One more warm-up. The area of a rectangle, five units
by two units. Area is length times width — five times two: [INK: 10] ten
square units. Area covers a *flat* shape. Keep that idea close — we're
about to give it another dimension."

**5 — Vocabulary.** "Two words for today. *Volume* — the amount of space
a solid figure takes up. We measure it in cubic units. [MARK: underline
'cubic units'] And a *unit cube* — a cube one unit long, one unit wide,
one unit tall. The building block we measure with. Look at the picture:
this box is packed with twelve unit cubes — [MARK: quick counting pulses]
so its volume is twelve cubic units. That's all volume is. Count the
cubes."

**6 — Practice 1.** "Now let's fill in the table together. Prism one.
First question: how many cubes in *one layer*? Count the top with me —
[MARK: pulse the top faces] four rows of three: twelve. How many layers?
Just one. So the volume: twelve times one — [INK: 12 | 1 | 12] twelve
cubic units. One layer, so the volume matches the area count. Flat — but
already three-D."

**7 — Practice 2.** "Prism two looks totally different — tall and thin.
Cubes in one layer? Four. Layers? One, two, three. [MARK: count the
layers] Four times three — [INK: 4 | 3 | 12] *twelve again!* Different
shape — same volume. Volume doesn't care what a shape looks like. It
counts cubes."

**8 — Practice 3.** "Prism three. Look closely — it's prism one, with a
second layer stacked on top. [SUPPLEMENTAL: the layer stacks, in the
page's own isometric style] Twelve cubes in a layer. Two layers. [INK:
12 | 2 | 24] Twelve… twenty-four. Volume is area — *stacked*."

**9 — Practice 4.** "Last one — and this one's yours. Pause here, and
try prism four." (beat) "Ready? Check it with me: five by four — twenty
cubes in a layer. Two layers. Twenty times two — [INK: 20 | 2 | 40]
*forty* cubic units. If you wrote forty — you've got volume."

**10 — Close.** "So: cubes per layer, times the number of layers.
That's volume — space, measured in cubes. Next lesson, we'll find volume
when we *can't* see every cube. See you there."

## Considered and parked

- **Visible/virtual hand** — rejected for this piece: a generated hand
  risks the uncanny where an absent one is neutral; the pipeline tracks
  nib position continuously, so a hand or pen layer remains a rendering
  flag, not a redesign.
- **Floating pen nib** — superseded by the **wand** (shipped): a
  glass-layer pointer for counting moments only, per the reference
  screencast's pen-nib pointer. A nib that rides the ink full-time
  remains a rendering flag if MCP wants it.
- **Music bed** — rejected: silence is where a 6th grader thinks.
- **Prism 1 → Prism 2 rotation** (screening suggestion) — the right
  visual for "different prism, same volume": prism 2's print fades,
  prism 1 appears and rotates upright into prism 2's exact pose. Parked
  because a true rotation needs a small 3-D re-projection of the page's
  isometric convention — the first film element not derived directly
  from the page's own 2-D art (endpoints would still register to
  print). Designed, estimated, and deferred under the deadline.
- **Fade transitions on figures** — tried (v2), rejected in screening:
  a viewer reads fade-out as "what just happened?"; replaced by the
  arrival-only grammar above.
