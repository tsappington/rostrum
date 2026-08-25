# rostrum

**Guided notes in, handwritten walkthrough out.** A deterministic
Python pipeline that teaches a Modern Classrooms guided-notes lesson
the way a teacher at a document camera would: a voice that breathes,
a real hand's ink filling out the actual worksheet, shading that follows
the teacher's attention, and a rostrum camera that moves with the
lesson. Nothing generative ever touches a frame.

**The film:** [Volume with Whole-Number Cubes](https://www.youtube.com/watch?v=iVI2_Lf9GH8) · 4:22 · Grade 6 · Geometry · Lesson 1 · Skill 1 · 1080p60 · captioned

## The idea

A rostrum camera is the rig filmmakers use to shoot flat artwork — the
machine behind every documentary pan across a photograph. This project
rebuilds it as software: the worksheet is the set, the camera drifts
at constant scale like an operator's move (never a digital zoom), it
holds still whenever the pen is down, and the frame never leaves the
page. The film contains exactly one edit — a 0.7-second dissolve at
the page turn, landing on the next section's own headline.

There is no avatar and no hand — deliberately. A generated hand risks
the uncanny where an absent one is neutral, and the warmth budget went
where it compounds: the voice, ink with real human timing, and sync
tight enough that the voice feels like it's writing. The one pointer
in the film is a wand — an orange dot on the "glass" — and it appears
only while counting, only where it can point honestly.

## The world has two layers

Everything on screen lives on one of two surfaces, and the rules are
absolute:

- **The paper** — the worksheet, the ink, the light, and the page's
  own illustrations. The page can be written on and lit, never
  deformed. Highlights wash in the ink's own blue (the teacher's
  attention in the teacher's color). Illustrations animate only inside
  their own panels, rebuilt from the PDF's own vector art in the
  artist's original draw order, pixel-registered to the print — the
  grammar is *present, clear, build*: the printed figure stays exactly
  as it sits on the student's own sheet until the narration reaches
  it, fades clear in one announced reset, then rebuilds by arrival
  (the vocabulary box packs cube by cube; Prism 3 stacks layer on
  layer, each landing on its spoken word).
- **The glass** — the interface between student and video: captions,
  the PAUSE & TRY chip, and the wand. Both chip and wand are gesture,
  not content (one says "you act now," the other says "look here"),
  and both are orange — page-light and interface never speak in the
  same color.

## The handwriting is real

The teacher writes with my hand. I captured ~220 takes of the lesson's
numerals, operators, and marks on an iPad with the Apple Pencil — a
browser capture tool built for this project records strokes with
timestamps and pressure — and the renderer *replays* that humanity
rather than simulating it: real velocity, real hesitations, pressure
mapped to ink width.

- **No two instances are identical.** Repeating numbers (this lesson
  writes 12 five times) draw different takes from the library —
  round-robin, the way drum machines escaped the "machine-gun
  effect" — plus hair's-width seeded jitters of scale, rotation,
  baseline, pace, and pressure. The variation is deterministic: same
  spec, same film, every render, on any machine.
- **The fair trial.** Raw tablet strokes look bad at capture scale and
  good at page scale (a 9× downscale forgives everything but
  character), so the capture tool judges takes with a live page-scale
  preview.

## The voice — and the sync law

Kokoro-82M: open weights (Apache-2.0), local CPU inference, zero API
cost. The decisive property is architectural: **Kokoro returns
word-level timestamps with the audio**, so the same synthesis that
produces the voice produces the timing map that drives the ink, the
light, the camera, the figures, and the captions. One artifact, five
consumers, no forced-alignment stage — and no hand-timed sync
anywhere. Rewrite any line and every cue re-derives on the next build.

Where the narrator's own prosody isn't enough, the timeline directs
it:

- **The metronome count.** TTS rushes an in-sentence count (I measured
  ~0.23s/word at every punctuation), so the count-alongs — "Let's
  check it. One, … two, … three. Three rows." — synthesize each phrase
  whole, keeping its natural counting melody, then slice each word out
  and place the slices on exact ticks, each cueing one square's light
  and a wand hop.
- **The placed breath.** `say(pause_after="five", pause=0.55)`
  splices silence into a sentence at a token boundary and shifts the
  later timestamps — full-sentence prosody with directed pacing
  ("Two times five… *[breath]* ten.").

(edge-tts was evaluated first and rejected: pleasant voices, but an
unofficial WebSocket API to a hosted service, and no word timestamps —
sync would have needed a separate forced-alignment stage.)

## The pipeline

```
lesson/volume_cubes.yaml ──► verify.py — THE GATE: 65 checks (arithmetic ·
    printed page · printed artwork · capture library) run before any audio
    or frame exists; every number the film writes is drawn from Spec.take()
                                            │
                                            ▼
assets/guided_notes.pdf ──► page.py ────────┐ blanks by their vector fill signature
    (true vector)           figures.py ─────┤ cube faces by tone triple, painter order
                            brand.py ───────┤ palette from the PDF's own fills
                                            │
assets/strokes/*.json ────► capture.py ─────┤ take Library: SHA-256(prompt|key) → take,
    (220 human takes)                       │ plus seeded micro-humanization
                                            │
                            tts.py ─────────┤ Kokoro-82M → (audio, word timestamps),
                                            │ cached per line
                                            ▼
                                      timeline.py ── ONE CLOCK
                                            │  say() · ink() · pause_after
                                            │  token_start("twelve") → cue time
                                            ▼
                  ┌───────────┬─────────────┼─────────────┬───────────┐
               ink.py      glow.py      figures.py     chip.py    timeline.srt()
               (paper)     (paper)       (paper)     (glass: chip  (captions)
                                                       + wand)
                  └───────────┴─────────────┼─────────────┴───────────┘
                                            ▼
                                  render.MovingRostrum
                       constant-scale crop over a supersampled plate
                                            ▼
                  2× downscale → ffmpeg H.264 → loudness-normalized AAC mux
                                  → .mp4 + .srt
```

The worksheet is data, not background: it's a vector PDF, so plates
render tack-sharp at any DPI, answer blanks are located by their
vector signature (ink lands on real coordinates, not eyeballed
pixels), table cells come from the table's own rules, figure cubes are
extracted with their fills, strokes, and painter order intact, and the
palette and type of everything added on screen come from the PDF's own
vector data.

Every stage leaves a deterministic, inspectable artifact — the spec,
the timing map (`python -m tools.film schedule` prints it), the stroke
library, the per-line TTS cache, the camera keys. Unchanged narration
never re-synthesizes; a one-line script edit re-voices one line.


## Verification

- **65 checks run before a single second of audio exists**, and the
  build dies there if any fails (`python -m rostrum.verify`). They close
  three loops:
  - **Arithmetic (20).** Every spec `check` is evaluated symbolically —
    a small AST walker over a whitelist, not `eval` — in a namespace
    bound from that item's own measurements. `L * D * H == 24` against
    `dims: [4, 3, 2]` is a real claim; the `2 == 2` it replaced was not.
  - **The printed page (8).** The document is re-read and has to agree:
    the lesson title, the five multiplication prompts in order, both
    vocabulary terms, the rectangle's own "5 units"/"2 units" labels,
    and the practice table's column headers in the order the film fills
    them. (The serif body copy is outlined vector, so the definitions
    have no string to compare against — the spec carries them as content
    and claims nothing it can't keep.)
  - **The printed artwork (17).** The illustrations are counted straight
    out of the PDF's vector data — squares in the flat grids, cube-face
    triples in the isometric solids. The artist drew every cube,
    occluded ones included, so each prism's volume has a witness that
    was never derived from the arithmetic it confirms: 12, 12, 24, 40.
    The grids are checked for *shape*, not just total — the narration
    says "three rows" and "four in each row", so the art has to be 3×4.
  This is what catches the failure that arithmetic alone can't: misread
  a dimension off an isometric drawing and every equation still balances.
  Change `gp3` to 4×3×3 and the checks pass — until the artwork says 24
  cubes and the build stops.
- **The film never names a number.** Every answer on screen comes from
  `Spec.take()`, and `assert_written` confirms at wrap that each declared
  answer was written exactly once and nothing else was.
- Determinism proven cross-platform: the same commit produced
  digit-identical timing maps on an Apple-silicon Mac and an x86 Linux
  container.
- Human screening: watched round by round with a therapist who works
  with children. Several of the film's design laws came directly from
  those screenings (mid-flow fades read as confusion → figures rebuild
  by arrival, *present, clear, build*; a slow spoken count
  promises a pointer → the count-along idiom exists only where the
  wand can point).

## Models and tools — the complete list

| What | Role |
|---|---|
| **Kokoro-82M** (Apache-2.0, local CPU) | narration + the word-level timestamps that drive all sync |
| **PyMuPDF** | vector-true plates, page geometry, figure extraction |
| **Pillow + NumPy** | ink and light rendering, compositing, audio assembly |
| **ffmpeg** (bundled via imageio-ffmpeg) | H.264 encode + AAC mux |
| **PyYAML** | the machine-checkable lesson spec — the gate's input |
| **Python 3.12** | everything; single-process by choice |
| **rostrum ink capture** (built for this) | iPad + Apple Pencil stroke recorder (PointerEvents, pressure, timing) |
| **Claude Code** | Fable 5 for architecture, implementation.  Opus 5 for reviewing, testing. |
| **Gemini** | 3.1 Pro for second-opinion review of the script draft |
| **Barlow Semi Condensed / Lora** | the worksheet's own faces, for the chip and captions |

Evaluated and not used: **edge-tts** (rejected — see above), **Manim**
(no animation framework at all: the worksheet's own vector art is the
animation source), and **generative video/image models** (none — the
absence is the point: nothing on screen can hallucinate).

## Trade-offs, honestly

- **Hand-directed, by design, for now.** `tools/film.py` is a directed
  film — every beat, cue word, and camera stop chosen. That's why this
  video is good, and it's also the scaling bottleneck (see below).
- **Render speed is unoptimized by choice.** ~3.5× realtime on an
  M4 Pro (16 minutes for this film), single-core Python/Pillow. The
  optimization ladder — dirty-rect compositing, multiprocess frame
  ranges, numpy/OpenCV composite — is understood and unneeded at
  current volume.
- **TTS prosody has a ceiling.** Kokoro is warm but occasionally
  flattens a line a teacher would lift. Per-line direction (carrier
  words, placed breaths, interrogative framing) recovers a lot — the
  fact recitation went through three revisions — but a production
  would A/B against premium voices with educator listeners.
- **16:9 over a portrait page** means the camera can never show a full
  page; the constant-scale drift embraces that rather than fighting it.
- **The verification gate is strongest where content is
  machine-checkable.** Math is. Other subjects need their own check
  types (spelling against a dictionary, dates against a source);
  where content can't be asserted, the gate thins to human review.
- **Loudness is capped by the crest, not by choice.** The mix is
  normalized to a broadcast target (two-pass ITU-R BS.1770) rather than
  to a peak, which took it from -23.2 to -15.5 LUFS. It doesn't reach
  -14: unprocessed TTS speech runs a wide crest with hot samples spread
  across the whole film, so the straight +9 dB would breach the
  true-peak ceiling. The ceiling wins, loudness range comes through
  intact (3.8 → 4.6 LU), and every render prints what it actually
  achieved rather than what it asked for.
- **Pencil pressure through Safari** arrives uncalibrated; each
  writer's personal range is normalized into the ink model's dynamic
  range — relative dynamics preserved, absolute weight standardized.
- **This took longer than 90 minutes — on purpose.** The 90-minute
  version exists in this repo: `python -m tools.slice` renders it —
  a two-beat slice of the lesson on the real page, real ink, the word-timestamp
  sync law already working end to end. That was the honest stopping
  point for a proof of pipe, and I kept going deliberately, because the
  interesting problems only appear after the pipe works: does replayed
  handwriting *feel* human? What does a machine-checkable lesson
  actually look like? What does a therapist who works with children
  flag on the fourth screening that I missed on the third? The brief
  says this README anchors a conversation about the job, so I treated
  the task as a pilot of the job. The commit history is the record of
  that choice — every screening note and the design law it became, in
  order.

## Is this scalable?

**Compute: yes, trivially.** ~16 min/lesson on one Mac, CPU-only, no
API costs, no shared state — renders parallelize across machines. One
desktop is a ~90-lesson/day render farm.

**Assets: they amortize.** The handwriting library already covers
digits and operators for every math lesson; a new glyph costs minutes
on the iPad. The voice is synthesized. Plates come free from any
vector PDF. Captions are a by-product.

**QA: scales because of determinism.** 65 checks run before frames
exist; same input, same film; reviewing the spec reviews the video.
Two of the three loops — the printed page and its artwork — need no
per-lesson authoring at all: they read whatever PDF they're given.
There is no hallucination surface to audit.

**Authoring: the honest bottleneck.** Today this is a film crew, not
a film factory — call it a day of skilled direction per lesson. The
architecture anticipates the move from crew to factory in three
steps, none of which changes the renderer:

1. **The worksheets are a design system.** Modern Classrooms guided
   notes repeat their sections and components; the geometry detectors
   are already generic, so a section-grammar pass can scaffold camera
   and beats for any worksheet in the family.
2. **Direction becomes data.** The real output of this build is a
   fixed idiom vocabulary — count-along, box-warm, term-lift,
   assemble, stack, pause chip, page turn. Direction as a per-lesson
   document of (line, cue word, idiom, target) makes authoring a
   lesson writing, not programming.
3. **Generative AI drafts; the deterministic pipeline disposes.** An
   LLM drafts the script and beat document from the worksheet; the
   checks, the schedule, and a human watch-through gate what ships.
   AI proposes specs, the renderer executes them, and nothing
   generative ever touches a frame.

What resists scaling is taste: each new lesson *type* — a new figure
choreography, a new idiom — needs a human architect and a screening
pass, exactly the loop that shaped this film. That's not a limitation
of the system so much as the definition of the role it was built for.

## Reproducing

```
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m tools.film schedule   # checks + timing map, no render
.venv/bin/python -m tools.film            # the full film → out/
.venv/bin/python -m pytest -q             # this README's claims, executable
```

First run downloads Kokoro's weights (~330 MB) and builds the per-line
TTS cache. Same commit, same film, any machine.

## License

© 2026 Ted Sappington. Shared for candidate evaluation only — see
[LICENSE](LICENSE).
