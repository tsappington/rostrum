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
python -m tools.film schedule           # timing map, no render (spec checks run)
python -m tools.film                    # full render → out/volume_cubes_*.mp4 + .srt
python -m tools.film audio af_sarah     # narration track only (fast; no frames)
python -m tools.slice                   # Beats 2-3 vertical slice (reference impl)
```

Rendering is CPU-only and slow by choice (~10x realtime); TTS is cached
per line in `out/tts_cache/`, so script edits re-synthesize only changed
lines.

## Layout

- `lesson/volume_cubes.yaml` — the content source of truth; every number
  written on screen carries a machine-checkable expression
- `rostrum/` — the package: `page` (PDF plates + geometry), `capture`
  (stroke ingestion, take Library, micro-humanization), `ink`
  (timing/pressure/render), `tts`, `timeline`, `render` (cameras, mux),
  `chip` (the glass layer), `brand` (tokens from the worksheet's own
  vector data)
- `tools/` — `film.py` is the movie, beat by beat; `capture/index.html`
  is the iPad stroke recorder (published as a Claude artifact)
- `assets/strokes/` — captured handwriting (see invariants)
- `docs/` — treatment, README draft, submission checklist

## Invariants — do not break

- **Determinism.** Same spec + same seeds → the same film, frame for
  frame. Never introduce wall-clock time or unseeded randomness into
  anything that reaches a frame; variation comes from hashed event keys
  (`capture.Library`).
- **Never hand-edit `assets/strokes/*.json`.** That's captured human
  data with provenance; corrections belong in ingestion code.
- **Verification precedes rendering.** A number that appears on screen
  must exist in the lesson spec with a passing `check`. If a check
  fails, the build must fail.
- **Two layers only.** The paper (worksheet + ink) and the glass
  (captions, pause chip, wand). Nothing else ever goes on the glass;
  nothing synthetic goes on the paper except ink and the page's own
  idioms. Glass citizens are gesture, not content — they never write
  or teach. Page light is ink-blue; orange belongs to the glass.
- **Arrival-only figures.** Inside the illustration windows, cubes only
  ever arrive (pack, stack); nothing printed is ever seen fading out.
  The patch covers a figure's print from frame one, and a finished
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
