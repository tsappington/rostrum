"""Frames to file: plate + ink composited, piped to ffmpeg.

Renders at 2x supersample and downscales per frame, which keeps the ink
edges clean without a vector compositor. The ffmpeg binary comes bundled
with imageio-ffmpeg, so the pipeline has no system dependencies.
"""

from __future__ import annotations

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
