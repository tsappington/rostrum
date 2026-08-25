"""The README's claims, made executable.

Seven tests, one per load-bearing claim. This is not a coverage suite —
the film's content is guarded by `rostrum.verify` at every build, and
these tests point the same idea at the machinery: if the README says
it, something here runs it.

The determinism test builds the full timeline twice and needs the TTS
cache (or a few minutes to create it); everything else runs in seconds
with no model.
"""

import copy
import re

import numpy as np
import pytest
import yaml

# ---------------------------------------------------------------------------
# 1. "The build dies rather than shipping a wrong number."


def test_gate_stops_a_misread_dimension(tmp_path):
    from rostrum.verify import SPEC_PATH, SpecError, verify

    spec = yaml.safe_load(SPEC_PATH.read_text())
    bad = copy.deepcopy(spec)
    gp3 = next(i for i in bad["guided_practice"] if i["id"] == "gp3")
    gp3["dims"] = [4, 3, 3]                    # the prism is 4 × 3 × 2
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.dump(bad))

    with pytest.raises(SpecError) as err:
        verify(path=p, quiet=True)
    msg = str(err.value)
    # the artwork loop is the independent witness: the page draws 24
    # cubes, and no amount of self-consistent arithmetic outvotes it
    assert "art has 24 cubes" in msg
    assert "L * D * H == 24" in msg


# ---------------------------------------------------------------------------
# 2. "65 checks run before a single second of audio exists."


def test_gate_passes_the_real_lesson():
    from rostrum.verify import verify

    spec = verify(quiet=True)
    assert len(spec.addresses()) == 20         # every answer the film writes


# ---------------------------------------------------------------------------
# 3. "Ink lands on real coordinates, not eyeballed pixels."


def test_blanks_found_by_vector_signature():
    from rostrum.page import find_blanks

    bs = find_blanks(0)
    assert len(bs) == 10                       # page 1's ten answer rules
    assert abs(bs[2].y - 228.4) < 1            # the equation line
    assert abs(bs[4].y - 287.6) < 1            # the first fact box


# ---------------------------------------------------------------------------
# 4. "Each prism's volume has a witness that was never derived from the
#    arithmetic it confirms."


def test_artwork_counts_match_the_lesson():
    from rostrum.verify import art_clusters

    p1 = art_clusters(0)
    grids = [c for c in p1 if c.kind == "squares"]
    assert [(c.rows, c.cols) for c in grids] == [(3, 4), (2, 5)]
    solids = [c.count for c in p1 if c.kind == "cubes"]
    assert solids == [12, 1]                   # vocab slab, unit cube

    p2 = art_clusters(1)
    prisms = [c.count for c in p2 if c.kind == "cubes"]
    assert prisms == [12, 12, 24, 40]          # the table's own answers


# ---------------------------------------------------------------------------
# 5. "Captions from the same timing map" — cues never overlap, and a cue
#    is at most two 42-character lines (a long sentence becomes several
#    cues, split over its spoken span).


def test_srt_cues_are_monotonic_and_disjoint():
    from rostrum.timeline import Seg, Timeline
    from rostrum.tts import SR

    long = ("Volume counts the unit cubes that fill a solid figure — "
            "layer by layer by layer — so count one layer, then stack.")
    tl = Timeline.__new__(Timeline)
    # padded clips whose tails overrun the next line — the clamp's job —
    # plus one sentence wide enough to force the multi-cue split
    tl.segs = [Seg(1.0, np.zeros(int(2.0 * SR), np.float32), [], "one"),
               Seg(2.5, np.zeros(int(2.0 * SR), np.float32), [], "two"),
               Seg(4.0, np.zeros(int(1.0 * SR), np.float32), [], "three"),
               Seg(5.5, np.zeros(int(4.0 * SR), np.float32),
                   [("Volume", 0.10, 0.42), ("stack.", 3.30, 3.72)], long)]

    srt = tl.srt()
    cues = [c for c in srt.strip().split("\n\n") if c]
    assert len(cues) > len(tl.segs), "the long sentence never split"
    for cue in cues:
        for line in cue.split("\n")[2:]:
            assert len(line) <= 42, f"caption line too wide: {line!r}"

    stamps = re.findall(r"(\d+):(\d+):(\d+),(\d+)", srt)
    t = [int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
         for h, m, s, ms in stamps]
    starts, ends = t[0::2], t[1::2]
    for a, b in zip(ends, starts[1:]):
        assert a <= b, "cues overlap"
    for a, b in zip(starts, ends):
        assert b - a >= 0.3, "cue too brief to read"


# ---------------------------------------------------------------------------
# 6. "Sound leaves at a broadcast loudness, not a peak."


def test_loudness_normalization_reaches_target(tmp_path):
    import soundfile as sf

    from rostrum.render import _ffmpeg, normalize_loudness

    sr = 24000
    t = np.arange(10 * sr) / sr                # a deliberately quiet voice
    tone = (0.02 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    src, dst = tmp_path / "quiet.wav", tmp_path / "loud.wav"
    sf.write(src, tone, sr)

    normalize_loudness(src, dst, sr)
    out = sf.info(dst)
    assert abs(out.duration - 10.0) < 0.05     # level moves, time never
    assert out.samplerate == sr

    log = _ffmpeg(["-i", str(dst), "-af", "loudnorm=print_format=json",
                   "-f", "null", "-"])
    got = float(re.search(r'"input_i"\s*:\s*"([-\d.]+)"', log).group(1))
    assert -17.0 < got < -12.0                 # at or near the -14 target


# ---------------------------------------------------------------------------
# 7. "Same spec, same film, every render, on any machine."
#    (Needs the TTS cache — first run synthesizes it.)


@pytest.mark.slow
def test_two_builds_are_identical():
    # the same function `python -m tools.film digest` prints — so this
    # test, the README's quoted hash, and a reader's own run are all
    # comparing the same computation
    from tools.film import build, digest

    assert digest(build()) == digest(build())
