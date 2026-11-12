"""Copy the lettering into lettering.json: the name 柊東雲 (the three-glyph Xikari Name font) and the Hiiragi
Shinonome signature (outlines plus the pen centre lines that write it), from the checkout where they are drawn.

  python import_lettering.py <path to that checkout>

Run it again only when the lettering itself changes; build_assets.py reads lettering.json.
"""
import json
import re
import sys
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from textpath import fmt

HERE = Path(__file__).resolve().parent


def name_glyphs(font_path: Path) -> dict:
    font = TTFont(str(font_path))
    cmap, glyphs, upm = font.getBestCmap(), font.getGlyphSet(), font["head"].unitsPerEm
    out = []
    for character in "柊東雲":
        recording = DecomposingRecordingPen(glyphs)
        glyphs[cmap[ord(character)]].draw(recording)
        pen = SVGPathPen(None, ntos=lambda value: fmt(value, 0))
        recording.replay(TransformPen(pen, (1, 0, 0, -1, 0, 0)))  # y down, baseline on 0
        out.append({"char": character, "d": pen.getCommands(), "advance": font["hmtx"][cmap[ord(character)]][0] / upm})
    return {"upm": upm, "glyphs": out}


def signature(paths_ts: Path) -> dict:
    source = paths_ts.read_text(encoding="utf-8")

    def export(name: str):
        return json.loads(re.search(rf"export const {name} = (.*?) as const;", source, flags=re.S).group(1))

    bounds = export("signatureBounds")
    keep = ("id", "outline", "d", "pen", "width", "penWidth", "delay", "duration")
    return {
        "viewBox": [bounds["x"], bounds["y"], bounds["width"], bounds["height"]],
        "strokes": [{key: stroke[key] for key in keep if key in stroke} for stroke in export("signatureStrokes")],
        "ornaments": [{key: mark[key] for key in keep if key in mark} for mark in export("signatureOrnaments")],
    }


def main():
    site = Path(sys.argv[1])
    data = {
        "source": "src/assets/fonts/xikari-name/xikari-name.woff2, src/components/signature/paths.ts",
        "name": name_glyphs(site / "src/assets/fonts/xikari-name/xikari-name.woff2"),
        "signature": signature(site / "src/components/signature/paths.ts"),
    }
    target = HERE / "lettering.json"
    target.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(f"{target.name}: {target.stat().st_size / 1024:.1f} KB, {len(data['signature']['strokes'])} strokes, {len(data['signature']['ornaments'])} ornaments")


if __name__ == "__main__":
    main()
