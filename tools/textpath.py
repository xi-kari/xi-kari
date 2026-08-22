"""Convert a text run to outlined SVG path data using a TTF font.

Usage:
  python textpath.py --font FONT.ttf --text "xi-kari" --size 64 [--weight 500]
                     [--tracking 0]

Prints JSON: {"d": "<combined path>", "width": <total advance>, "glyphs": [...]}
The path is drawn with baseline at y=0, origin x=0, y-down (SVG space).
"""
import argparse
import json
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen


def load_font(path: str, weight: float | None):
    font = TTFont(path)
    if "fvar" in font and weight is not None:
        from fontTools.varLib.instancer import instantiateVariableFont

        axes = {a.axisTag: a for a in font["fvar"].axes}
        loc = {}
        if "wght" in axes:
            a = axes["wght"]
            loc["wght"] = max(a.minValue, min(a.maxValue, weight))
        if loc:
            instantiateVariableFont(font, loc, inplace=True)
    return font


def _ntos(n: float) -> str:
    s = f"{n:.1f}".rstrip("0").rstrip(".")
    return s if s else "0"


def text_to_path(font: TTFont, text: str, size: float, tracking: float = 0.0):
    upem = font["head"].unitsPerEm
    scale = size / upem
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]

    x = 0.0
    parts = []
    glyphs = []
    for ch in text:
        code = ord(ch)
        if ch == " ":
            gname = cmap.get(code)
            adv = hmtx[gname][0] * scale if gname else size * 0.28
            x += adv + tracking
            continue
        gname = cmap.get(code)
        if gname is None:
            print(f"warning: no glyph for U+{code:04X} {ch!r}", file=sys.stderr)
            x += size * 0.6 + tracking
            continue
        spen = SVGPathPen(glyph_set, ntos=_ntos)
        tpen = TransformPen(spen, (scale, 0, 0, -scale, x, 0))
        glyph_set[gname].draw(tpen)
        d = spen.getCommands()
        if d:
            parts.append(d)
        adv = hmtx[gname][0] * scale
        glyphs.append({"char": ch, "x": x, "advance": adv})
        x += adv + tracking
    total = x - tracking if text else 0.0
    return {"d": " ".join(parts), "width": total, "glyphs": glyphs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--size", type=float, default=64)
    ap.add_argument("--weight", type=float, default=None)
    ap.add_argument("--tracking", type=float, default=0.0)
    args = ap.parse_args()

    font = load_font(args.font, args.weight)
    out = text_to_path(font, args.text, args.size, args.tracking)
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
