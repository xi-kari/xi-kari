"""Outline text to SVG path data.

GitHub serves README images through a proxy that blocks every external reference, web fonts included, so all
lettering in /assets is drawn as paths. A Face is one font file, or a folder of unicode-range slices (the way web
fonts are shipped) with its index.css; a Type is a stack of faces where the first one that has a character sets it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont


def fmt(value: float, digits: int = 1) -> str:
    """A number as short as it can be written: no trailing zeros, no “-0”, no leading zero."""
    text = f"{value:.{digits}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-0"):
        return "0"
    return text.replace("0.", ".", 1) if text.startswith(("0.", "-0.")) else text


class _File:
    def __init__(self, path: Path, weight: float | None):
        self.font = TTFont(str(path))
        if "fvar" in self.font and weight is not None:
            from fontTools.varLib.instancer import instantiateVariableFont

            axes = {axis.axisTag: axis for axis in self.font["fvar"].axes}
            location = {}
            if "wght" in axes:
                location["wght"] = max(axes["wght"].minValue, min(axes["wght"].maxValue, weight))
            for tag, axis in axes.items():
                location.setdefault(tag, axis.defaultValue)
            instantiateVariableFont(self.font, location, inplace=True)
        self.cmap = self.font.getBestCmap()
        self.glyphs = self.font.getGlyphSet()
        self.upm = self.font["head"].unitsPerEm
        self.hmtx = self.font["hmtx"]


@dataclass(frozen=True)
class Glyph:
    outline: tuple  # recorded pen commands, in font units, y up
    advance: float  # in em
    upm: int


class Face:
    def __init__(self, source: str | Path, weight: float | None = None):
        self.source = Path(source)
        self.weight = weight
        self._files: dict[Path, _File] = {}
        self._ranges: list[tuple[list[tuple[int, int]], Path]] = []
        if self.source.is_dir():
            css = (self.source / "index.css").read_text(encoding="utf-8")
            for block in re.findall(r"@font-face\s*{(.*?)}", css, flags=re.S):
                url = re.search(r"url\(['\"]?([^'\")]+)", block)
                spans = re.search(r"unicode-range:\s*([^;]+)", block)
                if not url or not spans:
                    continue
                ranges = []
                for span in spans.group(1).split(","):
                    low, _, high = span.strip()[2:].partition("-")
                    ranges.append((int(low, 16), int(high or low, 16)))
                self._ranges.append((ranges, self.source / Path(url.group(1)).name))

    def _file_for(self, code: int) -> _File | None:
        if not self._ranges:
            path = self.source
        else:
            path = next((file for ranges, file in self._ranges if any(low <= code <= high for low, high in ranges)), None)
            if path is None:
                return None
        if path not in self._files:
            self._files[path] = _File(path, self.weight)
        return self._files[path]

    @lru_cache(maxsize=None)
    def glyph(self, character: str) -> Glyph | None:
        file = self._file_for(ord(character))
        name = file.cmap.get(ord(character)) if file else None
        if name is None:
            return None
        pen = DecomposingRecordingPen(file.glyphs)
        file.glyphs[name].draw(pen)
        return Glyph(tuple(pen.value), file.hmtx[name][0] / file.upm, file.upm)


def _draw(glyph: Glyph, size: float, x: float, y: float, digits: int) -> str:
    pen = SVGPathPen(None, ntos=lambda value: fmt(value, digits))
    scale = size / glyph.upm
    target = TransformPen(pen, (scale, 0, 0, -scale, x, y))
    for operator, points in glyph.outline:
        getattr(target, operator)(*points)
    return pen.getCommands()


@dataclass
class Placed:
    character: str
    glyph: Glyph
    x: float  # left edge, in the run's units


class Run:
    """A line of text set at a size. x runs from 0; the baseline is y = 0; y grows downwards (SVG space)."""

    def __init__(self, placed: list[Placed], width: float, size: float):
        self.placed, self.width, self.size = placed, width, size

    def _digits(self, digits: int | None) -> int:
        return (1 if self.size >= 18 else 2) if digits is None else digits

    def d(self, x: float = 0, y: float = 0, digits: int | None = None) -> str:
        """The whole line as one path, its left end on (x, y)."""
        return "".join(_draw(item.glyph, self.size, x + item.x, y, self._digits(digits)) for item in self.placed)

    def each(self, digits: int | None = None):
        """(character, x, path at the glyph's own origin) for every inked glyph: for <use> and per-glyph motion."""
        for item in self.placed:
            commands = _draw(item.glyph, self.size, 0, 0, self._digits(digits))
            if commands:
                yield item.character, item.x, commands


class Type:
    def __init__(self, *faces: Face):
        self.faces = faces

    def glyph(self, character: str) -> Glyph:
        for face in self.faces:
            glyph = face.glyph(character)
            if glyph is not None:
                return glyph
        raise KeyError(f"no face has U+{ord(character):04X} {character!r}")

    def run(self, text: str, size: float, tracking: float = 0.0) -> Run:
        """tracking is in em, added after every glyph but the last (CSS letter-spacing, minus the trailing gap)."""
        x, placed = 0.0, []
        for character in text:
            glyph = self.glyph(character)
            placed.append(Placed(character, glyph, x))
            x += (glyph.advance + tracking) * size
        return Run(placed, x - tracking * size if placed else 0.0, size)
