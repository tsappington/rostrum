# README draft — for Ted's rewrite

> Working draft. The submission README must be in your voice — rewrite
> freely; the technical facts below are verified. Sections marked ✍️
> want your personal register most.

---

# rostrum

**Guided notes in, handwritten walkthrough out.** A deterministic Python
pipeline that teaches a Modern Classrooms guided-notes lesson the way a
teacher at a document camera would: a warm voice, a real hand's ink
filling out the actual worksheet, and a rostrum camera that moves with
the lesson.

**The film:** [link] · 3:53 · *Volume with Whole-Number Cubes*
(Grade 6 · Geometry · Lesson 1 · Skill 1)

## ✍️ The idea

A rostrum camera is the rig filmmakers use to shoot flat artwork — the
machine behind every documentary pan across a photograph. This project
rebuilds it as software: the worksheet is the set, the camera drifts at
constant scale like an operator's move (never a digital zoom), it holds
still whenever the pen is down, and the frame never leaves the page.

There is no avatar and no hand — deliberately. A generated hand risks
the uncanny where an absent one is neutral, and the warmth budget went
where it compounds: a voice that breathes, ink with real human timing,
and sync tight enough that the voice feels like it's writing. (The
system tracks nib position continuously, so a virtual pen or stylized
hand is a rendering flag away if audience testing ever wants one.)

## The handwriting is real

The teacher writes with my hand. I captured ~220 takes of the lesson's
numerals, operators, and marks on an iPad with the Apple Pencil — a
browser capture tool built for this project records strokes with
timestamps and pressure — and the renderer *replays* that humanity
rather than simulating it: real velocity, real hesitations, pressure
mapped to ink width.

Two details matter most:

- **No two instances are identical.** Numbers that repeat (there are
  five 12s in this lesson) draw different takes from the library —
  round-robin, the way drum machines escaped the "machine-gun effect" —
  and every instance passes through hair's-width seeded jitters of
  scale, rotation, baseline, pace, and pressure. The variation is
  deterministic: same spec, same film, every render.
- **The fair trial.** Raw tablet strokes look bad at capture scale and
  good at page scale (a 9x downscale forgives everything but character).
  The capture tool renders a live page-scale preview so takes are judged
  at the size they'll live.

A curated synthetic stroke library (Catmull-Rom glyphs with a velocity
model: bell speed profile, curvature drag, scripted hesitations) was
built first and remains the understudy — it proved the renderer before
any capture existed, and its timing model landed within 6% of my real
hand's measured pace.

## The voice

Kokoro-82M — open weights (Apache-2.0), runs locally on CPU, zero API
cost. Chosen by ear from a five-voice casting sheet, but the decisive
property is architectural: **Kokoro returns word-level timestamps with
the audio**, so the same synthesis that produces the teacher's voice
produces the timing map that drives the ink, the captions, and sync QA.
One artifact, three consumers, no forced-alignment stage. Ink events cue
off spoken words ("Twelve squares in all" starts the 12 being written);
answer words are scheduled to land on the final strokes.

(edge-tts was evaluated and rejected: pleasant voices, but an unofficial
WebSocket API to a hosted service is neither open-weights nor
dependable infrastructure.)

## The pipeline

```
lesson spec (YAML, machine-checkable answers)
  └─ verify        every answer asserted before any frame renders
  └─ narrate       Kokoro-82M → audio + word timestamps (cached by line)
  └─ timeline      one clock: narration, ink cues, camera keys, captions
  └─ ink           captured strokes → placed, timed, pressure-mapped
  └─ camera        constant-scale rostrum drift over supersampled plates
  └─ render        2x supersample → 1080p60 → bundled ffmpeg
  └─ deliver       mp4 + SRT captions from the same timing map
```

Deterministic intermediate artifacts at every stage: the lesson spec,
the timing map, the stroke library, per-line TTS cache, camera
keyframes. Inspectable, versioned, diffable; unchanged narration never
re-synthesizes.

The worksheet itself is treated as data, not background: it's a vector
PDF, so plates render tack-sharp at any DPI, answer blanks are located
from their vector geometry (a hairline fill-rect signature — ink lands
on real coordinates, not eyeballed pixels), table cells come from the
table's own rules, and underlines land under words found by text
search. The palette and type on anything added on screen are extracted
from the PDF's own vector data.

## Verification

- 20 machine-checkable assertions in the lesson spec — every number
  written on screen is verified (`3 * 4 == 12`) before render.
- Narration drafted to a grade 5–6 reading level; two Modern
  Classrooms-style pause-and-try prompts.
- ✍️ Human screening: watched with [partner], who has raised and
  fostered kids through this age — the closest thing a weekend offers
  to an educator annotation pass.

## Models and tools

| What | Why |
|---|---|
| Kokoro-82M (Apache-2.0, local CPU) | narration + word timestamps |
| PyMuPDF | vector-true plates, page geometry |
| Pillow + NumPy | ink rendering, compositing |
| ffmpeg (via imageio-ffmpeg) | encode + mux |
| Claude Code | AI-native build partner across the whole project |
| rostrum ink capture (built here) | Apple Pencil stroke recorder |

No paid APIs; everything runs locally. ✍️ *Add a sentence in your own
words about the Claude Code workflow — multi-session, spec-driven — this
is a line they'll ask about, in a good way.*

## Trade-offs, honestly

- **The supplemental animation is deferred, not forgotten.** The brief
  is right that a clean video with none beats a cluttered one; the one
  place the concept is inherently 3-D (Practice 3, "a second layer
  stacks") is designed as a spec-declared scene type, and shipping v1
  without it was a restraint call under the deadline. [drop this line if
  we ship it]
- **16:9 over a portrait page** means the camera can never show a full
  page; the constant-scale drift embraces that rather than fighting it.
- **TTS prosody has a ceiling.** bella is warm but occasionally flattens
  a sentence a human teacher would lift; per-line direction (rate,
  pauses, re-takes) is data, not editing, so it's tunable — but a real
  production would A/B against premium voices with educator listeners.
- **Pencil pressure through Safari** arrives without calibration; I
  normalize each writer's personal range into the ink model's dynamic
  range, which preserves relative dynamics but standardizes absolute
  weight.

## Where the production version goes

Golden datasets of spec-to-video pairs annotated by educators; VLM-as-
judge visual QA calibrated against those labels; symbolic verification
wired into CI; selective re-render on spec diffs (the per-line TTS cache
is the seed of that); multilingual narration; per-teacher handwriting
profiles captured with the same tool; and brand design-system templates
so every subject ships in its own worksheet's visual world. Each of
these is a design conversation I'd enjoy having.

## Reproducing

```
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
python -m tools.film schedule   # the timing map, no render
python -m tools.film            # the full film → out/
```

## License

© 2026 Ted Sappington. Shared for candidate evaluation only — see
[LICENSE](../LICENSE).
