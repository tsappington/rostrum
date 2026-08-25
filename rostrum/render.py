"""Frames to file: plate + ink composited, piped to ffmpeg.

Renders at 2x supersample and downscales per frame, which keeps the ink
edges clean without a vector compositor. The ffmpeg binary comes bundled
with imageio-ffmpeg, so the pipeline has no system dependencies.

Sound leaves here at a broadcast loudness, not a peak. A mix normalized
to its loudest sample can still be far too quiet to sit beside the other
things a student watches — this one measured -23 LUFS, roughly 9 dB under
what a streaming platform expects — and quiet instruction gets turned up,
not leaned into. `normalize_loudness` runs the two-pass ITU-R BS.1770
measurement ffmpeg already implements: measure the whole programme, then
apply one gain, so the teacher's dynamics survive and only the level
moves.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

from . import page as page_mod
from .ink import InkLayer


class Rostrum:
    """A fixed camera over one page region, ink layer on top.

    region_pt: (x0, y0, x1, y1) in page points. out_size: final pixels.
    """

    def __init__(self, page_index: int, region_pt: tuple[float, float, float, float],
                 out_size: tuple[int, int] = (1920, 1080), supersample: int = 2):
        self.region = region_pt
        self.out_size = out_size
        w_pt = region_pt[2] - region_pt[0]
        self.scale = out_size[0] * supersample / w_pt          # px per pt
        w = out_size[0] * supersample
        h = out_size[1] * supersample
        plate = page_mod.render_region(page_index, region_pt, dpi=self.scale * 72.0)
        if plate.size != (w, h):
            plate = plate.resize((w, h), Image.LANCZOS)
        self.plate = plate.convert("RGBA")
        self.ink = InkLayer((w, h), (region_pt[0], region_pt[1]), self.scale)

    def frame(self) -> Image.Image:
        comp = Image.alpha_composite(self.plate, self.ink.img)
        return comp.convert("RGB").resize(self.out_size, Image.LANCZOS)


class MovingRostrum:
    """A rostrum camera that drifts at constant scale over one plate.

    The whole reachable page area renders once as a supersampled plate;
    per frame the viewport crops it. Camera path is keyframes of the
    viewport's top-left in page points — (t, x, y) — held flat between
    duplicate positions and eased with smoothstep between different ones.
    Constant scale keeps one plate DPI and the drift honest: a rostrum
    operator's move, not a digital zoom.
    """

    def __init__(self, page_index: int, union_pt: tuple[float, float, float, float],
                 view_pt: tuple[float, float], keys: list[tuple[float, float, float]],
                 out_size: tuple[int, int] = (1920, 1080), supersample: int = 2):
        self.union = union_pt
        self.view_pt = view_pt
        self.keys = sorted(keys)
        self.out_size = out_size
        self.scale = out_size[0] * supersample / view_pt[0]
        plate = page_mod.render_region(page_index, union_pt, dpi=self.scale * 72.0)
        self.plate = plate.convert("RGBA")
        self.ink = InkLayer(self.plate.size, (union_pt[0], union_pt[1]), self.scale)
        self._w = out_size[0] * supersample
        self._h = out_size[1] * supersample
        for _, x, y in self.keys:
            assert union_pt[0] <= x and union_pt[1] <= y, "keyframe outside plate"
            assert x + view_pt[0] <= union_pt[2] + 0.01, "keyframe outside plate"
            assert y + view_pt[1] <= union_pt[3] + 0.01, "keyframe outside plate"

    def position(self, t: float) -> tuple[float, float]:
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1], ks[0][2]
        for (t0, x0, y0), (t1, x1, y1) in zip(ks, ks[1:]):
            if t <= t1:
                u = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
                u = u * u * (3 - 2 * u)
                return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        return ks[-1][1], ks[-1][2]

    def frame(self, t: float, under=None) -> Image.Image:
        """under(comp, box): draws paper-layer light and living figures
        onto the cropped plate before the ink lands on top."""
        x_pt, y_pt = self.position(t)
        px = int(round((x_pt - self.union[0]) * self.scale))
        py = int(round((y_pt - self.union[1]) * self.scale))
        box = (px, py, px + self._w, py + self._h)
        comp = self.plate.crop(box)
        if under is not None:
            under(comp, box)
        comp = Image.alpha_composite(comp, self.ink.img.crop(box))
        return comp.convert("RGB").resize(self.out_size, Image.LANCZOS)


def write_video(path: str | Path, frames, fps: int = 60, size=(1920, 1080)) -> Path:
    """Consume an iterable of PIL RGB frames into an H.264 mp4."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{size[0]}x{size[1]}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for f in frames:
            proc.stdin.write(f.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg exited {proc.returncode}")
    return path


# -14 LUFS with 1.5 dB of true-peak headroom is where the streaming
# platforms land; 7 LU of range keeps a teacher's quiet aside quiet.
TARGET_I, TARGET_TP, TARGET_LRA = -14.0, -1.5, 7.0


def _ffmpeg(args: list[str]) -> str:
    """Run ffmpeg and hand back stderr — where it says everything."""
    proc = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), *args],
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                          text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
        raise RuntimeError(f"ffmpeg exited {proc.returncode}:\n{tail}")
    return proc.stderr


def normalize_loudness(src: str | Path, dst: str | Path, sample_rate: int,
                       target_i: float = TARGET_I, target_tp: float = TARGET_TP,
                       target_lra: float = TARGET_LRA) -> dict:
    """Bring a finished mix to a loudness target. Returns the measurement.

    Two passes, because one can't be right: the first measures the whole
    programme (integrated loudness, range, true peak, gate threshold),
    the second applies those numbers in one informed correction.
    Measuring and correcting in a single streaming pass would ride the
    level against the narration itself — exactly the pumping a lesson
    can't afford.

    `linear=true` asks for a plain gain and no processing at all. It is a
    request, not a guarantee: this narration measures -23 LUFS with peaks
    already at -1.6 dBTP — unprocessed speech runs a wide crest, and the
    hot samples are spread across the whole film rather than sitting in
    one fixable transient — so the straight +9 dB to reach target would
    breach the ceiling, and ffmpeg falls back to a limited correction
    that lands near -15.5 LUFS. That is the right trade: the ceiling
    wins, loudness range comes through intact (3.8 → 4.6 LU, nothing
    squashed), and the caller prints what was actually achieved rather
    than what was asked for.
    """
    spec = f"I={target_i}:TP={target_tp}:LRA={target_lra}"
    log = _ffmpeg(["-i", str(src), "-af", f"loudnorm={spec}:print_format=json",
                   "-f", "null", "-"])
    blocks = re.findall(r"\{[^{}]*\}", log, re.S)
    if not blocks:
        raise RuntimeError(f"loudnorm reported no measurement:\n{log[-800:]}")
    m = json.loads(blocks[-1])
    _ffmpeg([
        "-y", "-i", str(src),
        "-af", f"loudnorm={spec}"
               f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
               f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
               f":offset={m['target_offset']}:linear=true",
        "-ar", str(sample_rate), str(dst),
    ])
    return m


def mux(video: str | Path, audio_wav: str | Path, out: str | Path) -> Path:
    """Marry picture and sound: copy the video stream, encode audio AAC."""
    out = Path(out)
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y",
        "-i", str(video), "-i", str(audio_wav),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", str(out),
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg mux exited {res.returncode}")
    return out
