"""The gate: nothing reaches a frame that the source can't prove.

A student watching this video has no way to audit it. The only honest
answer to that is to make the machine audit itself, before it makes
anything — so this module runs first, on every entry point, and the
build dies here rather than shipping a wrong number.

Three loops close, in widening circles of trust:

**Arithmetic.** Every `check` in the lesson spec is evaluated
symbolically — a tiny AST walker over a whitelist, not `eval` — in a
namespace bound from that item's own measurements. `L * D * H == 24`
with `dims: [4, 3, 2]` is a real claim; the tautologies it replaced
(`2 == 2`) were not. A mis-transcribed dimension now fails.

**The document.** The printed page is re-read and must agree with what
the spec says it says: the lesson title, the five multiplication
prompts in order, both vocabulary terms, the rectangle's own unit
labels, and the practice table's column headers in the order the film
fills them. Transcription drift is a silent failure mode, so it gets a
loud one. (The worksheet's serif body copy is outlined vector rather
than text — the definitions and the objective have no string on the
page to compare against, so this file carries them as content and
makes no claim it can't keep.)

**The artwork.** The illustrations are counted straight out of the
PDF's vector data — squares in the flat grids, cube-face triples in the
isometric figures — and compared against the spec's claims. This is the
strong link: the artist drew every cube, occluded ones included, so
`volume` has a witness that was never derived from the arithmetic it
confirms. If the spec says Prism 4 is 40 and the art contains 39 cubes,
one of them is wrong and the build stops. The flat grids are checked
for *shape*, not just total — the narration says "three rows" and "four
in each row", so the art has to actually be 3 by 4.

Finally, the film reports back. `Spec.take()` is the only way a number
gets on screen — the shooting script never names one itself — and
`assert_written` confirms at the end of the build that every declared
answer was written exactly once, and nothing else was.

Coordinates and colors are the page's own; see `page` and `figures`.
"""

from __future__ import annotations

import ast
import operator
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import page as page_mod
from .figures import Figure

SPEC_PATH = Path(__file__).resolve().parent.parent / "lesson" / "volume_cubes.yaml"


class SpecError(AssertionError):
    """The build's stop sign. Carries every failure, not just the first."""


# ---------------------------------------------------------------------------
# symbolic evaluation — a whitelist, so a spec can never execute anything

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.Pow: operator.pow}
_CMP = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
        ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}


def evaluate(expr: str, names: dict[str, int]):
    """Evaluate a spec expression over `names`. Anything unlisted raises."""

    def walk(n):
        if isinstance(n, ast.Expression):
            return walk(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name):
            if n.id not in names:
                raise SpecError(f"{expr!r}: unknown name {n.id!r} "
                                f"(have {sorted(names)})")
            return names[n.id]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = walk(n.operand)
            return v if isinstance(n.op, ast.UAdd) else -v
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](walk(n.left), walk(n.right))
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            op = type(n.ops[0])
            if op in _CMP:
                return _CMP[op](walk(n.left), walk(n.comparators[0]))
        raise SpecError(f"{expr!r}: {type(n).__name__} is not allowed here")

    return walk(ast.parse(expr, mode="eval"))


def _rhs(expr: str, names: dict[str, int]):
    """The value a check asserts — the right side of its comparison."""
    tree = ast.parse(expr, mode="eval").body
    if not isinstance(tree, ast.Compare) or len(tree.ops) != 1:
        raise SpecError(f"{expr!r}: a check must be one comparison")
    return evaluate(ast.unparse(tree.comparators[0]), names)


# ---------------------------------------------------------------------------
# reading the printed page back

_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")


def normalize(s: str) -> str:
    """Page text and spec text, reduced to the same shape: NFKC, one kind
    of dash, whitespace collapsed, lowercase. Line wrapping in the PDF is
    a typesetting fact, not a content difference."""
    s = unicodedata.normalize("NFKC", s).translate(_DASHES)
    return " ".join(s.split()).lower()


def page_text(page_index: int) -> str:
    with page_mod.open_doc() as doc:
        return normalize(doc[page_index].get_text())


def _median(vals: list[float]) -> float:
    s = sorted(vals)
    return s[len(s) // 2] if s else 0.0


_FACT_RE = re.compile(r"(\d+)\s*[×x]\s*(\d+)\s*=")


def printed_facts(page_index: int) -> list[tuple[int, int]]:
    """The multiplication prompts the page prints, in reading order."""
    with page_mod.open_doc() as doc:
        raw = unicodedata.normalize("NFKC", doc[page_index].get_text())
    return [(int(a), int(b)) for a, b in _FACT_RE.findall(raw)]


# ---------------------------------------------------------------------------
# counting the printed artwork

@dataclass(frozen=True)
class ArtCluster:
    """One illustration, as the vector data describes it.

    `kind` is "cubes" when the cluster carries the print's three
    isometric face tones in equal number (a solid, drawn face by face),
    and "squares" when it carries only the lightest tone (a flat grid).
    `count` is cubes or squares accordingly; a flat grid also reports
    the shape its extent and cell size imply.
    """

    kind: str
    count: int
    bbox: tuple[float, float, float, float]
    rows: int = 0
    cols: int = 0


def art_clusters(page_index: int, gap: float = 4.0) -> list[ArtCluster]:
    """Every figure on the page, counted, in reading order.

    Faces are grouped by touching: cube faces of one solid abut, and
    separate figures sit far apart, so growing each face rect by `gap`
    and merging overlaps separates the illustrations without a single
    hand-measured coordinate.
    """
    tiles: list[tuple[tuple[float, float, float, float], tuple[int, ...]]] = []
    with page_mod.open_doc() as doc:
        for d in doc[page_index].get_drawings():
            if not d.get("fill"):
                continue
            tone = tuple(int(v * 255) for v in d["fill"])
            if tone not in Figure.TONES:
                continue
            r = d["rect"]
            if r.width > 60 or r.height > 60:      # a panel, not a face
                continue
            tiles.append(((r.x0, r.y0, r.x1, r.y1), tone))

    groups: list[list[int]] = [[i] for i in range(len(tiles))]

    def touches(a: int, b: int) -> bool:
        (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = tiles[a][0], tiles[b][0]
        return (ax0 - gap <= bx1 and bx0 - gap <= ax1
                and ay0 - gap <= by1 and by0 - gap <= ay1)

    merged = True
    while merged:
        merged = False
        for i in range(len(groups)):
            for j in range(len(groups) - 1, i, -1):
                if any(touches(a, b) for a in groups[i] for b in groups[j]):
                    groups[i] += groups.pop(j)
                    merged = True

    out: list[ArtCluster] = []
    for g in groups:
        tones: dict[tuple[int, ...], int] = {}
        for i in g:
            tones[tiles[i][1]] = tones.get(tiles[i][1], 0) + 1
        n = len(g)
        counts = set(tones.values())
        if len(tones) == 3 and len(counts) == 1:
            kind, count = "cubes", n // 3
        elif len(tones) == 1:
            kind, count = "squares", n
        else:
            kind, count = "mixed", n
        xs = [v for i in g for v in (tiles[i][0][0], tiles[i][0][2])]
        ys = [v for i in g for v in (tiles[i][0][1], tiles[i][0][3])]
        box = (min(xs), min(ys), max(xs), max(ys))
        rows = cols = 0
        if kind == "squares":
            cell_w = _median([tiles[i][0][2] - tiles[i][0][0] for i in g])
            cell_h = _median([tiles[i][0][3] - tiles[i][0][1] for i in g])
            cols = round((box[2] - box[0]) / cell_w) if cell_w else 0
            rows = round((box[3] - box[1]) / cell_h) if cell_h else 0
        out.append(ArtCluster(kind, count, box, rows, cols))
    out.sort(key=lambda c: (c.bbox[1], c.bbox[0]))
    return out


# ---------------------------------------------------------------------------


@dataclass
class Spec:
    """The lesson, loaded — and the only source of numbers the film may use."""

    data: dict
    _ink: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self):
        for item in self.data["do_now"] + self.data["guided_practice"]:
            for ink in item["ink"]:
                self._ink[f"{item['id']}.{ink['field']}"] = {**ink, "_item": item}

    # ---- what the film asks for ------------------------------------------

    def take(self, addr: str) -> str:
        """The captured handwriting that writes this answer."""
        return self._entry(addr)["take"]

    def write(self, addr: str) -> str:
        """What appears on the page, verbatim."""
        return self._entry(addr)["write"]

    def addresses(self) -> list[str]:
        return list(self._ink)

    def _entry(self, addr: str) -> dict:
        if addr not in self._ink:
            raise SpecError(f"no such answer in the spec: {addr!r} "
                            f"(have {sorted(self._ink)})")
        return self._ink[addr]

    def assert_written(self, written: list[str]) -> None:
        """Close the loop the other way: the spec's answers and the film's
        ink are the same set, each written exactly once."""
        seen = {a: written.count(a) for a in set(written)}
        bad = [f"{a} written {n}×" for a, n in sorted(seen.items()) if n != 1]
        bad += [f"{a} declared but never written" for a in self._ink
                if a not in seen]
        if bad:
            raise SpecError("film/spec coverage:\n  " + "\n  ".join(bad))

    # ---- the three loops --------------------------------------------------

    @staticmethod
    def _names(item: dict, ink: dict) -> dict[str, int]:
        n: dict[str, int] = {}
        if "grid" in item:
            n["R"], n["C"] = item["grid"]
        if "dims" in item:
            n["L"], n["D"], n["H"] = item["dims"]
        if "fact" in ink:
            n["A"], n["B"] = ink["fact"]
        return n

    def check_arithmetic(self, fail: list[str]) -> int:
        n = 0
        for addr, ink in self._ink.items():
            names = self._names(ink["_item"], ink)
            expr = ink["check"]
            n += 1
            if not evaluate(expr, names):
                fail.append(f"{addr}: check {expr!r} is false with {names}")
                continue
            # the check must assert the number that gets written: the last
            # integer in `write` ("3 × 4 = 12" → 12, "12" → 12)
            digits = re.findall(r"\d+", ink["write"])
            if digits and _rhs(expr, names) != int(digits[-1]):
                fail.append(f"{addr}: writes {ink['write']!r} but "
                            f"{expr!r} asserts {_rhs(expr, names)}")
            if ink["write"].isdigit() and ink["take"] != f"n{ink['write']}":
                fail.append(f"{addr}: writes {ink['write']!r} "
                            f"with take {ink['take']!r}")
        return n

    # the practice table's columns, as the page heads them, in the order
    # the film fills them left to right
    COLUMNS = [("cubes_per_layer", "cubes per layer"),
               ("num_layers", "number of layers"),
               ("volume", "volume (cubic units)")]

    def check_document(self, fail: list[str]) -> int:
        n = 0
        p1, p2 = page_text(0), page_text(1)

        n += 1
        if normalize(self.data["meta"]["title"]) not in p1:
            fail.append("the lesson title is not the one printed on page 1")

        spec_facts = [tuple(i["fact"]) for i in self._ink.values() if "fact" in i]
        n += 1
        if printed_facts(0) != spec_facts:
            fail.append(f"printed facts {printed_facts(0)} ≠ spec {spec_facts}")

        for v in self.data["vocabulary"]:
            n += 1
            if normalize(v["term"]) not in p1:
                fail.append(f"vocabulary term {v['term']!r} is not printed "
                            f"on page 1")

        # the area rectangle labels its own edges — "5 units", "2 units" —
        # so dn3's grid is witnessed by the page, not just by its picture
        dn3 = next(i for i in self.data["do_now"] if i["id"] == "dn3")
        for u in dn3["grid"]:
            n += 1
            if f"{u} units" not in p1:
                fail.append(f"dn3: the page does not label an edge "
                            f"{u} units")

        # the film writes each row left to right in this field order; the
        # page's own headers have to be in that order too
        n += 1
        heads = [h for _, h in self.COLUMNS]
        at = [p2.find(h) for h in heads]
        if -1 in at or at != sorted(at):
            fail.append(f"page 2 table headers {heads} are missing or out "
                        f"of order (found at {at})")
        gp_fields = [i["field"] for i in self.data["guided_practice"][0]["ink"]]
        n += 1
        if gp_fields != [f for f, _ in self.COLUMNS]:
            fail.append(f"guided practice fields {gp_fields} do not match "
                        f"the table's columns")
        return n

    def check_artwork(self, fail: list[str]) -> int:
        n = 0
        p1 = art_clusters(0)
        p2 = art_clusters(1)

        # page 1, in reading order: the Do Now array, the area rectangle,
        # then the two vocabulary illustrations
        grids = [c for c in p1 if c.kind == "squares"]
        solids = [c for c in p1 if c.kind == "cubes"]
        want_grids = [i for i in self.data["do_now"] if "grid" in i]
        n += 1
        if len(grids) != len(want_grids):
            fail.append(f"page 1: {len(grids)} flat grids in the art, "
                        f"{len(want_grids)} in the spec")
        else:
            for c, item in zip(grids, want_grids):
                r, col = item["grid"]
                n += 1
                if c.count != r * col:
                    fail.append(f"{item['id']}: art has {c.count} squares, "
                                f"spec says {r}×{col} = {r * col}")
                n += 1
                if (c.rows, c.cols) != (r, col):
                    fail.append(f"{item['id']}: art is {c.rows} rows × "
                                f"{c.cols} columns, spec says {r}×{col}")

        vocab = self.data["vocabulary"]
        n += 1
        if len(solids) != len(vocab):
            fail.append(f"page 1: {len(solids)} vocabulary figures, "
                        f"{len(vocab)} terms")
        else:
            for c, v in zip(solids, vocab):
                n += 1
                if c.count != v["example_cubes"]:
                    fail.append(f"vocabulary {v['term']!r}: art has "
                                f"{c.count} cubes, spec says "
                                f"{v['example_cubes']}")

        gp = self.data["guided_practice"]
        prisms = [c for c in p2 if c.kind == "cubes"]
        n += 1
        if len(prisms) != len(gp):
            fail.append(f"page 2: {len(prisms)} prisms drawn, "
                        f"{len(gp)} rows in the spec")
        else:
            for c, item in zip(prisms, gp):
                vol = int(self.write(f"{item['id']}.volume"))
                n += 1
                if c.count != vol:
                    fail.append(f"{item['id']}: art has {c.count} cubes, "
                                f"spec writes volume {vol}")
                n += 1
                if c.count != item["dims"][0] * item["dims"][1] * item["dims"][2]:
                    fail.append(f"{item['id']}: art has {c.count} cubes, "
                                f"dims {item['dims']} give "
                                f"{item['dims'][0] * item['dims'][1] * item['dims'][2]}")
        return n

    def check_takes(self, strokes: dict, fail: list[str]) -> int:
        """Every take the spec names must exist in the capture library."""
        have = strokes.get("prompts", {})
        n = 0
        for addr, ink in self._ink.items():
            n += 1
            if not have.get(ink["take"], {}).get("takes"):
                fail.append(f"{addr}: no captured take {ink['take']!r}")
        return n


def load(path: str | Path = SPEC_PATH) -> Spec:
    return Spec(yaml.safe_load(Path(path).read_text()))


def verify(strokes: dict | None = None, path: str | Path = SPEC_PATH,
           quiet: bool = False) -> Spec:
    """Run the gate. Returns the Spec the film may draw numbers from;
    raises SpecError, listing every failure, if anything disagrees."""
    spec = load(path)
    fail: list[str] = []
    counts = {
        "arithmetic": spec.check_arithmetic(fail),
        "document": spec.check_document(fail),
        "artwork": spec.check_artwork(fail),
    }
    if strokes is not None:
        counts["takes"] = spec.check_takes(strokes, fail)
    if fail:
        raise SpecError(f"{len(fail)} check(s) failed:\n  "
                        + "\n  ".join(fail))
    if not quiet:
        print("verify · " + " · ".join(f"{v} {k}" for k, v in counts.items())
              + " · all pass")
    return spec


if __name__ == "__main__":
    verify()
