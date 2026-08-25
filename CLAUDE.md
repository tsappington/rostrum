# CLAUDE.md

Guidance for Claude Code sessions working in this repository.

## What this is

**rostrum** — a deterministic pipeline that turns a guided-notes
worksheet into an instructional video: a teacher's voice (local TTS with
word timestamps), captured human handwriting replayed with its real
timing, and a virtual rostrum camera over the actual page. Built for the
Modern Classrooms Project *AI Video Generation Architect* performance
task. Read `docs/treatment.md` for the film's creative spine before
changing what the film *does*.

## Commands

```
python -m rostrum.verify                # the gate alone: spec vs page vs art
python -m tools.film schedule           # timing map, no render (gate runs first)
python -m tools.film captions           # captions only → out/volume_cubes_v3.srt
python -m tools.film                    # full render → out/volume_cubes_*.mp4 + .srt
python -m tools.film audio af_sarah     # narration track only (fast; no frames)
python -m tools.slice                   # Beats 2-3 vertical slice (reference impl)
python -m pytest -q                     # the README's claims, executable
```

Rendering is CPU-only and slow by choice (~10x realtime); TTS is cached
per line in `out/tts_cache/`, so script edits re-synthesize only changed
lines.

## Layout

- `lesson/volume_cubes.yaml` — the content source of truth; every number
  written on screen carries a machine-checkable expression
- `rostrum/` — the package: `verify` (the gate), `page` (PDF plates +
  geometry), `capture`
  (stroke ingestion, take Library, micro-humanization), `ink`
  (timing/pressure/render), `tts`, `timeline`, `render` (cameras, mux),
  `chip` (the glass layer), `brand` (tokens from the worksheet's own
  vector data)
- `tools/` — `film.py` is the movie, beat by beat; `capture/index.html`
  is the iPad stroke recorder (published as a Claude artifact)
- `assets/strokes/` — captured handwriting (see invariants)
- `docs/` — the treatment (the film's creative spine)

## Invariants — do not break

- **Determinism.** Same spec + same seeds → the same film, frame for
  frame. Never introduce wall-clock time or unseeded randomness into
  anything that reaches a frame; variation comes from hashed event keys
  (`capture.Library`).
- **Never hand-edit `assets/strokes/*.json`.** That's captured human
  data with provenance; corrections belong in ingestion code.
- **Verification precedes rendering.** `rostrum.verify` runs before any
  audio or any frame exists, and the build dies there. Four loops close:
  every spec `check` is evaluated symbolically against that item's own
  measurements (never a tautology — `L * D * H == 24`, not `2 == 2`); the
  printed page is re-read and must agree; the illustrations are
  counted out of the PDF's vector data, so `volume` has a witness that
  was never derived from the arithmetic it confirms; and every take the
  spec names must exist in the captured stroke data. The film never names
  a number itself — it asks `Spec.take()`, and `assert_written` confirms
  at wrap that every declared answer went down exactly once. A number no
  source can prove does not reach a frame.
- **Two layers only.** The paper (worksheet + ink) and the glass
  (captions, pause chip, wand). Nothing else ever goes on the glass;
  nothing synthetic goes on the paper except ink and the page's own
  idioms. Glass citizens are gesture, not content — they never write
  or teach. Page light is ink-blue; orange belongs to the glass.
- **Figures: present, clear, build.** A printed figure stays on screen
  exactly as on the student's sheet until the narration reaches it,
  fades clear in one announced reset, then rebuilds by arrival (pack,
  stack) — during the build nothing is ever seen leaving. A finished
  figure retires with no transition because drawn == print.
- **Marks anchor to their own ink.** A take's position always comes from
  its ink bottom; only *scale* may borrow guide geometry
  (`capture._fit`).
- `out/` is disposable and untracked. Renders are reproducible; never
  commit them.

## Conventions

- Python 3.11+, no framework: PyMuPDF, Pillow, NumPy, bundled ffmpeg,
  Kokoro-82M (local). Keep it dependency-light; anything new must run
  offline on CPU.
- Module docstrings explain *why* in prose; keep that voice.
- Coordinates are PDF points (72/inch, y down) unless a name says px.
- Commit messages narrate the reasoning, not the diff.
