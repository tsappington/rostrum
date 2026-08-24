"""Light on paper: the highlight idiom.

The page can be written on (ink) and it can be lit — this module is the
light. One cool wash in the ink's own blue, eased in and out; the
same voice whether it sweeps the rows of an array, warms the active
fact box, or lifts one face of the unit cube. Blue because the teacher's
pen is blue: the light is her attention, the ink is her commitment.
Glows render on the paper layer, beneath the ink, because light falls
on the page and writing sits on top of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from .brand import INK


def _hex(c: str) -> tuple[int, int, int]:
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _ease(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


@dataclass
class Glow:
    shape: list[tuple[float, float]]      # polygon in page points
    t_in: float
    t_out: float
    fade_in: float = 0.28
    fade_out: float = 0.4
    max_alpha: int = 90
    radius: float = 0.0                   # >0: shape treated as rect corners
    color: str = INK

    def alpha(self, t: float) -> float:
        if t < self.t_in or t > self.t_out + self.fade_out:
            return 0.0
        a_in = _ease((t - self.t_in) / self.fade_in) if self.fade_in else 1.0
        a_out = (_ease((self.t_out + self.fade_out - t) / self.fade_out)
                 if t > self.t_out else 1.0)
        return min(a_in, a_out)


def rect(x0: float, y0: float, x1: float, y1: float, pad: float = 0.0
         ) -> list[tuple[float, float]]:
    return [(x0 - pad, y0 - pad), (x1 + pad, y1 + pad)]


@dataclass
class GlowTrack:
    events: list[Glow] = field(default_factory=list)

    def add(self, shape, t_in, t_out, **kw) -> Glow:
        g = Glow(shape, t_in, t_out, **kw)
        self.events.append(g)
        return g

    def sweep(self, shapes: list, t0: float, step: float,
              hold: float = 0.55, **kw) -> float:
        """Staggered glows — rows lighting one after another."""
        for i, s in enumerate(shapes):
            self.add(s, t0 + i * step, t0 + i * step + hold, **kw)
        return t0 + (len(shapes) - 1) * step + hold

    def render(self, comp: Image.Image, box, scale: float,
               union, t: float) -> None:
        for g in self.events:
            a = g.alpha(t)
            if a <= 0.01:
                continue
            color = _hex(g.color)
            # a shape is one polygon (list of points) or many (list of
            # polygons — e.g. every face of one layer of cubes); many are
            # drawn into one layer so the wash composites exactly once
            groups = (g.shape if isinstance(g.shape[0][0], (tuple, list))
                      else [g.shape])
            mapped = [[((x - union[0]) * scale - box[0],
                        (y - union[1]) * scale - box[1]) for x, y in gp]
                      for gp in groups]
            xs = [p[0] for gp in mapped for p in gp]
            ys = [p[1] for gp in mapped for p in gp]
            if max(xs) < 0 or min(xs) > comp.width or \
               max(ys) < 0 or min(ys) > comp.height:
                continue
            x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
            x1, y1 = int(max(xs)) + 3, int(max(ys)) + 3
            layer = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            fill = (*color, int(g.max_alpha * a))
            if g.radius > 0 and len(groups) == 1 and len(mapped[0]) == 2:
                local = [(p[0] - x0, p[1] - y0) for p in mapped[0]]
                d.rounded_rectangle([*local[0], *local[1]],
                                    radius=g.radius * scale, fill=fill)
            else:
                for gp in mapped:
                    d.polygon([(p[0] - x0, p[1] - y0) for p in gp],
                              fill=fill)
            comp.alpha_composite(layer, (x0, y0))
