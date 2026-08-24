"""Living figures: the worksheet's own illustrations, animated.

The illustration panels are windows — the one licensed place the page
comes alive. A figure's cubes are extracted from the PDF's vector art
in the artist's own painter order (each cube is a consecutive
top/left/right face triple), which buys the load-bearing property: any
prefix of that order is a correctly-occluded scene. Assembly replays
the artist's draw order cube by cube; a layer landing floats one
prefix-group above the rest. The final frame retires the patch and the
print itself shows through — registration is guaranteed, not hoped for.
"""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf
from PIL import Image, ImageDraw

from . import page as page_mod


def _ease_out(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return 1 - (1 - u) ** 3


@dataclass
class Face:
    verts: list[tuple[float, float]]      # page points
    fill: tuple[int, int, int]
    stroke: tuple[int, int, int] | None
    width: float


@dataclass
class Figure:
    """One illustration's cubes, in painter order, plus its patch."""

    cubes: list[list[Face]]               # each cube: [left, right, top]
    bbox: tuple[float, float, float, float]
    edge_width: float = 0.8               # the print's own stroke weight

    # a cube face is identified by the print's own three face tones
    TONES = {(207, 196, 180), (230, 222, 208), (250, 246, 241)}

    @classmethod
    def extract(cls, page_index: int, clip: tuple[float, float, float, float]
                ) -> "Figure":
        faces: list[Face] = []
        with page_mod.open_doc() as doc:
            region = pymupdf.Rect(*clip)
            for d in doc[page_index].get_drawings():
                r = d["rect"]
                if not d.get("fill") or not region.intersects(r):
                    continue
                if tuple(int(v * 255) for v in d["fill"]) not in cls.TONES:
                    continue
                verts: list[tuple[float, float]] = []
                for item in d["items"]:
                    if item[0] == "l":
                        p = (item[1].x, item[1].y)
                        if not verts or verts[-1] != p:
                            verts.append(p)
                        verts.append((item[2].x, item[2].y))
                if len(verts) < 3 or r.width > 60 or r.height > 60:
                    continue                       # not a cube face
                fill = tuple(int(v * 255) for v in d["fill"])
                stroke = (tuple(int(v * 255) for v in d["color"])
                          if d.get("color") else None)
                faces.append(Face(verts, fill, stroke, d.get("width") or 1.2))
        assert len(faces) % 3 == 0, f"{len(faces)} faces — not cube triples"
        # the print's own edge weight, measured from its stroke paths
        widths: dict[float, int] = {}
        with page_mod.open_doc() as doc:
            for d in doc[page_index].get_drawings():
                if d.get("color") and not d.get("fill") \
                   and region.intersects(d["rect"]):
                    c = tuple(int(v * 255) for v in d["color"])
                    if c == cls.NAVY:
                        w = d.get("width") or 0.8
                        widths[w] = widths.get(w, 0) + 1
        edge = max(widths, key=widths.get) if widths else 0.8
        cubes = [faces[i:i + 3] for i in range(0, len(faces), 3)]
        xs = [x for f in faces for x, _ in f.verts]
        ys = [y for f in faces for _, y in f.verts]
        return cls(cubes, (min(xs), min(ys), max(xs), max(ys)), edge)

    # ---- rendering --------------------------------------------------------

    NAVY = (56, 70, 82)          # the print strokes edges in separate paths;
                                 # we stroke each face to the same effect

    def _draw_cube(self, d: ImageDraw.ImageDraw, cube: list[Face],
                   to_px, dy_pt: float, scale: float) -> None:
        w = max(int(round(self.edge_width * scale)), 1)
        for f in cube:
            pts = [to_px(x, y + dy_pt) for x, y in f.verts]
            outline = f.stroke if f.stroke else self.NAVY
            d.polygon(pts, fill=(*f.fill, 255), outline=(*outline, 255),
                      width=w)

    def layer_split(self) -> tuple[list[int], list[int]]:
        """(bottom, top) cube indices. A cube is bottom-layer iff its top
        face's center is later overdrawn — honest occlusion, not height
        clustering, which painter order defeats."""

        def center(verts):
            xs = [x for x, _ in verts]
            ys = [y for _, y in verts]
            return sum(xs) / len(xs), sum(ys) / len(ys)

        def inside(pt, verts):
            x, y = pt
            hit = False
            n = len(verts)
            for i in range(n):
                x0, y0 = verts[i]
                x1, y1 = verts[(i + 1) % n]
                if (y0 > y) != (y1 > y) and \
                   x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                    hit = not hit
            return hit

        bottom, top = [], []
        for i, cube in enumerate(self.cubes):
            top_face = min(cube, key=lambda f: center(f.verts)[1])
            c = center(top_face.verts)
            covered = any(inside(c, f.verts)
                          for j in range(i + 1, len(self.cubes))
                          for f in self.cubes[j])
            (bottom if covered else top).append(i)
        return bottom, top

    def render(self, comp: Image.Image, box, scale: float, union,
               t: float, spec: dict) -> None:
        """Draw the figure's animated state under an alpha envelope.

        The whole overlay — patch plus drawn cubes — dissolves IN at the
        lead (the printed art fades away, never pops) and dissolves OUT
        after the settle, resolving into the print beneath. Between cuts
        and dissolves the print itself is the ground truth on screen.
        """
        t0, kind = spec["t0"], spec["kind"]
        if kind == "assemble":
            stag, drop = spec.get("stagger", 0.16), spec.get("drop", 0.32)
            t_end = t0 + (len(self.cubes) - 1) * stag + drop
        else:                                        # "land"
            dur = spec.get("dur", 0.9)
            t_end = t0 + dur
        settle = spec.get("settle", 0.3)
        patch_fade = spec.get("patch_fade", 0.4)
        dissolve = spec.get("dissolve", 0.4)
        lead_start = t0 - spec.get("lead", 2.5)
        if t < lead_start or t > t_end + settle + dissolve:
            return
        env = _ease_out(min((t - lead_start) / patch_fade, 1.0))
        if t > t_end + settle:
            env *= 1.0 - _ease_out((t - t_end - settle) / dissolve)
        if env <= 0.005:
            return

        drop_h = spec.get("drop_h", 16.0)
        b = self.bbox
        pad = 3.0
        # the overlay layer: the patch region plus headroom for the drop
        head = drop_h + 6.0
        ox_pt, oy_pt = b[0] - pad, b[1] - pad - head
        lw = int((b[2] - b[0] + 2 * pad) * scale) + 4
        lh = int((b[3] - b[1] + 2 * pad + head) * scale) + 4

        def on_screen(x_pt, y_pt):
            return ((x_pt - union[0]) * scale - box[0],
                    (y_pt - union[1]) * scale - box[1])

        o_px = on_screen(ox_pt, oy_pt)
        if o_px[0] + lw < 0 or o_px[0] > comp.width or \
           o_px[1] + lh < 0 or o_px[1] > comp.height:
            return

        def to_px(x_pt, y_pt):
            return ((x_pt - ox_pt) * scale, (y_pt - oy_pt) * scale)

        layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        sx = min(max(int(o_px[0]) - 6, 0), comp.width - 1)
        sy = min(max(int(o_px[1] + head * scale), 0), comp.height - 1)
        sample = comp.getpixel((sx, sy))[:3]
        d.rectangle([to_px(b[0] - pad, b[1] - pad),
                     to_px(b[2] + pad, b[3] + pad)], fill=(*sample, 255))

        if kind == "assemble":
            for i, cube in enumerate(self.cubes):
                ti = t0 + i * stag
                if t < ti:
                    continue
                u = _ease_out((t - ti) / drop)
                self._draw_cube(d, cube, to_px, -(1 - u) * drop_h, scale)
        else:
            for i in spec["static"]:
                self._draw_cube(d, self.cubes[i], to_px, 0.0, scale)
            # the arriving layer fades in just before its descent
            appear = spec.get("fade_in", 0.25)
            a = max(0.0, min(1.0, (t - (t0 - appear)) / appear))
            if a > 0.0:
                u = _ease_out((t - t0) / dur) if t >= t0 else 0.0
                dy = -(1 - u) * drop_h
                if a >= 1.0:
                    for i in spec["moving"]:
                        self._draw_cube(d, self.cubes[i], to_px, dy, scale)
                else:
                    sub = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
                    sd = ImageDraw.Draw(sub)
                    for i in spec["moving"]:
                        self._draw_cube(sd, self.cubes[i], to_px, dy, scale)
                    alpha = sub.getchannel("A").point(lambda v: int(v * a))
                    sub.putalpha(alpha)
                    layer.alpha_composite(sub)

        if env < 1.0:
            alpha = layer.getchannel("A").point(lambda v: int(v * env))
            layer.putalpha(alpha)
        comp.alpha_composite(layer, (int(o_px[0]), int(o_px[1])))
