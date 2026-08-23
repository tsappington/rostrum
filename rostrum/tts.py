"""Narration: Kokoro-82M, open weights, local CPU.

The decisive property: Kokoro returns word-level timestamps with the
audio, so the same synthesis that produces the teacher's voice produces
the timing map that drives ink, captions, and sync QA. One artifact,
three consumers, no separate forced-alignment stage.

Synthesis is cached by (voice, speed, text) hash — re-renders of the
video never re-synthesize unchanged lines.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

SR = 24000


class Narrator:
    def __init__(self, voice: str = "af_bella", speed: float = 0.92,
                 cache_dir: str | Path = "out/tts_cache"):
        self.voice = voice
        self.speed = speed
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self._pipe = None

    def _pipeline(self):
        if self._pipe is None:
            from kokoro import KPipeline
            self._pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
        return self._pipe

    def say(self, text: str) -> tuple[np.ndarray, list[tuple[str, float, float]]]:
        """Synthesize one narration line.

        Returns (audio float32 @24kHz, tokens [(word, start_s, end_s)])
        with token times relative to the start of this line's audio.
        """
        key = hashlib.sha256(
            f"{self.voice}|{self.speed}|{text}".encode()
        ).hexdigest()[:24]
        f = self.cache / f"{key}.npz"
        if f.exists():
            z = np.load(f, allow_pickle=True)
            return z["audio"], [tuple(t) for t in z["tokens"].tolist()]

        chunks: list[np.ndarray] = []
        tokens: list[tuple[str, float, float]] = []
        offset = 0.0
        for res in self._pipeline()(text, voice=self.voice, speed=self.speed):
            a = res.audio.numpy()
            for tk in res.tokens or []:
                if tk.start_ts is None or tk.end_ts is None:
                    continue
                tokens.append((tk.text, offset + float(tk.start_ts),
                               offset + float(tk.end_ts)))
            chunks.append(a)
            offset += len(a) / SR
        audio = np.concatenate(chunks) if chunks else np.zeros(0, np.float32)
        np.savez(f, audio=audio, tokens=np.array(tokens, dtype=object))
        return audio, tokens
