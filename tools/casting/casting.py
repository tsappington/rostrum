"""Track B: casting the teacher.

Renders the same ~25-second script excerpt in several candidate voices so
the voice is chosen by ear, like casting — not by default. The excerpt is
the video's opening beat: greeting, promise, and a Modern Classrooms
pause-and-try prompt.

Engine: Kokoro-82M — open weights (Apache-2.0), runs locally on CPU, and
returns word-level timestamps with the audio, which is exactly the timing
map the ink renderer needs. (edge-tts was evaluated and parks: decent
voices, but it is an unofficial network API behind a WebSocket, so it is
neither open-weights nor dependable infrastructure.)

  python -m tools.casting.casting
"""

from pathlib import Path

import numpy as np
import soundfile as sf

EXCERPT = (
    "Hi mathematicians — welcome back. Today, we're learning how to measure "
    "space: how much room something takes up. By the end of this video, "
    "you'll be able to find the volume of a box, just by counting cubes. "
    "But first, let's warm up with something you already know. Pause the "
    "video here, and try the Do Now on your own. When you're ready, press "
    "play, and we'll go through it together."
)

CANDIDATES = [
    ("heart",   "af_heart",   "warm, settled — the default American female"),
    ("bella",   "af_bella",   "more expressive, a little brighter"),
    ("sarah",   "af_sarah",   "clear and even, younger read"),
    ("nicole",  "af_nicole",  "soft, close-mic intimacy"),
    ("michael", "am_michael", "the male option — easygoing, warm"),
]

SPEED = 0.92          # a teacher's pace, not an announcer's
SR = 24000
GAP = 0.30            # seconds between synthesis chunks

OUT = Path(__file__).resolve().parent.parent.parent / "out" / "casting"


def main() -> None:
    from kokoro import KPipeline

    OUT.mkdir(parents=True, exist_ok=True)
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    silence = np.zeros(int(GAP * SR), dtype=np.float32)
    for name, voice, note in CANDIDATES:
        chunks: list[np.ndarray] = []
        for res in pipe(EXCERPT, voice=voice, speed=SPEED):
            if chunks:
                chunks.append(silence)
            chunks.append(res.audio.numpy())
        audio = np.concatenate(chunks)
        path = OUT / f"voice_{name}.wav"
        sf.write(path, audio, SR)
        print(f"  {path.name}  {len(audio)/SR:5.1f}s  ({voice} — {note})")


if __name__ == "__main__":
    main()
