"""Build the three pictures the profile README shows (../assets): the cover, the motto and the medallion.

Two inks on one paper. The cover carries the 柊東雲 lettering and the Hiiragi Shinonome signature, written by
its own pen beside small letters gathered in soft masses, through which a ripple spreads now and then; a pool
of the second ink lies at its foot, cut by three tide lines. Under it the motto, which a drop of solvent takes
apart and lets settle again, and the portrait medallion with its turning ring of names.

Every picture is drawn twice, for GitHub's light and dark pages. Text is outlined to paths (see textpath.py);
only the small letters are live <text>, set in whatever monospace face the reader has. Nothing refers to
anything outside its own file, because GitHub's image proxy would drop it (the portrait is carried inside the
medallion's file). The base state of every picture is
the finished one: motion lives in keyframes only, and stops under prefers-reduced-motion.

  python build_assets.py            (fonts in tools/fonts/, see tools/README.md)
"""
from __future__ import annotations

import base64
import json
import math
import random
import string
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from textpath import Face, Type, fmt

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
OUT = HERE.parent / "assets"

# Day and night: ink, a quieter ink, the second ink, hairlines; then how strongly the cover's wash, its letters
# and a ripple's letters print on each page.
THEMES = {
    "light": dict(ink="#1F3049", muted="#586980", accent="#445B9F", line="#D0DBE9", wash=.17, field=.36, ring=.6),
    "dark": dict(ink="#E5EDFA", muted="#A8BAD2", accent="#B1C1F5", line="#3B4D68", wash=.15, field=.28, ring=.55),
}
MOTTO = ["真理是溶解世界万物的溶剂，", "因而绝无法在客观上存在"]
ORBIT = "柊東雲 · xi-kari · Hiiragi Shinonome · 柊曦光 · ひいらぎしののめ · "  # the names that turn round the medallion
READING = "ひいらぎしののめ / Hiiragi Shinonome"
GLYPHS = string.ascii_letters + string.digits  # what the small letters are drawn from


def face(*names: str, weight: float | None = None) -> Face:
    for name in names:
        if (FONTS / name).exists():
            return Face(FONTS / name, weight)
    raise SystemExit(f"missing font: put one of {', '.join(names)} in tools/fonts/ (see tools/README.md)")


def sans(weight: float) -> Face:
    return face("Figtree[wght].ttf", "figtree-latin.woff2", weight=weight)


KAI = face("LXGWWenKaiGB-Regular.ttf")
KAI_MEDIUM = face("LXGWWenKaiGB-Medium.ttf", "wenkai-gb-medium")
TEXT = Type(sans(400), KAI)  # Latin in the sans, everything else in the kai
RING = Type(sans(500), KAI)  # the ring of names: a firmer Latin, the kana in the regular kai
IDEOGRAPH = Type(KAI_MEDIUM)  # and its ideographs in the medium, so they hold at ten pixels
LETTERING = json.loads((HERE / "lettering.json").read_text(encoding="utf-8"))

STILL = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def svg(width: float, height: float, label: str, body: str, style: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(width)} {fmt(height)}" width="{fmt(width)}" '
            f'height="{fmt(height)}" role="img" aria-label="{label}"><style>{style}{STILL}</style>{body}</svg>\n')


def baseline(top: float, size: float, leading: float) -> float:
    """Where the baseline falls in a line box of the given leading (the metrics the kai is set with: 1.0581 / 0.2617)."""
    return top + (leading / 2 + 0.3982) * size


# ------------------------------------------------------------------------------------------------ cover ----
#
# An animated SVG shown through <img> is painted again, whole, on every frame for as long as any animation in it is
# running, so the cover is built to cost little per frame: the letter masses are worked out here and written as
# plain opacities (no mask), the signature is swapped for its bare outlines once it is written, a ripple's letters
# are painted only while it passes them, and the one mask, the tide, covers only the pool at the foot.

MONO = "ui-monospace,SFMono-Regular,'Cascadia Mono',Menlo,Consolas,'Liberation Mono',monospace"
CELL, LETTER = (10.5, 21), 13.5  # the letter grid and its type size
WAVES = [  # three tide lines: path (two periods of 1440), how much of the foot each takes away, seconds per pass, direction
    ("M0 58C120 14 240 14 360 58S600 102 720 58 960 14 1080 58 1320 102 1440 58 1680 14 1800 58 2040 102 2160 58 2400 14 2520 58 2760 102 2880 58V160H0Z", .3, 29, 1),
    ("M0 74C120 108 240 108 360 74S600 40 720 74 960 108 1080 74 1320 40 1440 74 1680 108 1800 74 2040 40 2160 74 2400 108 2520 74 2760 40 2880 74V160H0Z", .55, 21, -1),
    ("M0 105C120 77 240 77 360 105S600 133 720 105 960 77 1080 105 1320 133 1440 105 1680 77 1800 105 2040 133 2160 105 2400 77 2520 105 2760 133 2880 105V160H0Z", 1, 17, 1),
]


def ramp(distance: float, *stops: tuple[float, float]) -> float:
    """A radial falloff read at a distance from its centre: (offset, value) stops, straight lines between them."""
    for (near, high), (far, low) in zip(stops, stops[1:]):
        if distance <= far:
            return high + (low - high) * (distance - near) / (far - near)
    return stops[-1][1]


def letters(cells: list[tuple[int, int, str, float, float]], levels: int, peak: float, floor: float = .14, least: int = 1) -> dict[str, dict[int, tuple[str, str]]]:
    """Letters on the grid, sorted by strength and by row: {opacity: {row: (x of every glyph, the glyphs)}}.
    Each glyph gets its own x, so any monospace face keeps the columns.
    cells: (column, row, glyph, tint, presence 0..1). A letter prints at tint × presence, rounded to a few levels.
    Where presence falls under the floor nothing prints at all, and a patch of fewer than `least` letters is
    dropped whole, so a mass ends on a soft contour instead of trailing off into loose specks."""
    kept = {(column, row) for column, row, _, _, presence in cells if presence >= floor}
    patch: dict[tuple[int, int], int] = {}
    for cell in kept:  # flood each patch once and remember its size
        if cell in patch:
            continue
        members, edge = {cell}, [cell]
        while edge:
            column, row = edge.pop()
            for beside in ((column - 1, row), (column + 1, row), (column, row - 1), (column, row + 1)):
                if beside in kept and beside not in members:
                    members.add(beside)
                    edge.append(beside)
        patch.update(dict.fromkeys(members, len(members)))
    rows: dict[int, dict[int, list[tuple[int, str]]]] = {}
    for column, row, glyph, tint, presence in cells:
        if patch.get((column, row), 0) >= least:
            rows.setdefault(max(1, round(tint * presence * levels)), {}).setdefault(row, []).append((column, glyph))
    return {
        fmt(level / levels * peak, 3): {row: (" ".join(fmt(column * CELL[0]) for column, _ in line), "".join(glyph for _, glyph in line)) for row, line in sorted(by_row.items())}
        for level, by_row in sorted(rows.items())
    }


def line(row: int) -> str:
    return fmt(row * CELL[1] + CELL[1] * .74)


def signature(x: float, y: float, width: float, colour: str, start: float = .55, pace: float = 1.12) -> tuple[str, str]:
    """(defs, drawing) for the signature at (x, y). While it is written, each stroke is its pen line, drawn along
    its length and clipped to the stroke's outline; once the last one lands, the bare outlines take over."""
    data = LETTERING["signature"]
    vx, vy, vw, vh = data["viewBox"]
    scale = width / vw
    place = f'transform="translate({fmt(x - vx * scale, 2)} {fmt(y - vy * scale, 2)}) scale({fmt(scale, 4)})"'
    defs, pens, outlines, end = [], [], [], start
    for order, stroke in enumerate(data["strokes"] + data["ornaments"]):
        delay, duration = start + stroke["delay"] * pace / 1000, stroke["duration"] * pace / 1000
        end = max(end, delay + duration)
        defs.append(f'<path id="o{order}" d="{stroke.get("outline") or stroke["d"]}"/><clipPath id="k{order}"><use href="#o{order}"/></clipPath>')
        pens.append(
            f'<path class="pen" clip-path="url(#k{order})" style="animation-delay:{fmt(delay, 3)}s;animation-duration:{fmt(duration, 3)}s" '
            f'd="{stroke["pen"]}" stroke-width="{stroke.get("width") or stroke["penWidth"]}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="0"/>'
        )
        outlines.append(f'<use href="#o{order}"/>')
    swap = f'style="animation-duration:{fmt(end + .12, 2)}s"'
    drawing = (
        f'<g {place} class="writing" {swap} visibility="hidden" fill="none" stroke="{colour}" stroke-linecap="round" stroke-linejoin="round">{"".join(pens)}</g>'
        f'<g {place} class="written" {swap} fill="{colour}">{"".join(outlines)}</g>'
    )
    return f'<g {place}>{"".join(defs)}</g>', drawing


def name(x: float, top: float, size: float, tracking: float = .28, start: float = .2) -> str:
    """柊東雲 in its own hand, pressed in one glyph after another."""
    data = LETTERING["name"]
    base = top + .9325 * size
    out = []
    for order, glyph in enumerate(data["glyphs"]):
        place = f'translate({fmt(x + order * (glyph["advance"] + tracking) * size, 2)} {fmt(base, 2)}) scale({fmt(size / data["upm"], 4)})'
        out.append(f'<g transform="{place}"><path class="stamp" style="animation-delay:{fmt(start + order * .08, 2)}s" d="{glyph["d"]}"/></g>')
    return "".join(out)


def cover(theme: dict, seed: int = 3141) -> str:
    W, H, tide = 920, 412, 96
    sig_w = 500
    sig_x, sig_y = (W - sig_w) / 2, 90
    foot = H - tide
    pool = 200  # how high the pool of the second ink rises from the foot
    rng = random.Random(seed)

    # Soft masses the letters gather in, one to each stretch of the width so they neither pile up nor leave half
    # the picture empty: (centre, radii, strength).
    masses = []
    for order in range(11):
        rx = rng.uniform(60, 175)
        masses.append(((order + rng.uniform(.15, .85)) * W / 11, rng.uniform(H * .08, H * .66), rx, rx * rng.uniform(.4, .85), rng.uniform(.4, 1)))

    def gathered(x: float, y: float) -> float:
        clear = 1.0
        for cx, cy, rx, ry, strength in masses:
            clear *= 1 - strength * ramp(math.hypot((x - cx) / rx, (y - cy) / ry), (0, 1), (.55, .5), (1, 0))
        return 1 - clear

    def veil(x: float, y: float) -> float:  # the lettering keeps a clearing around itself
        return 1 - ramp(math.hypot((x - W / 2) / (sig_w * .7), (y - sig_y - 96) / 236), (0, .92), (.7, .8), (1, 0))

    def edge(x: float, y: float) -> float:  # soft at both sides and the top, gone before the tide
        return max(0, min(1, x / (W * .09), (W - x) / (W * .09), y / 70, (foot - 4 - y) / 46))

    # Every cell of the grid gets a glyph and one of three strengths, so neighbours differ and a mass reads as grain.
    grid = [(column, row, rng.choice(GLYPHS), rng.choice((.38, .66, 1)))
            for row in range(math.ceil(foot / CELL[1])) for column in range(math.ceil(W / CELL[0]))]

    def centre(column: int, row: int) -> tuple[float, float]:
        return (column + .5) * CELL[0], row * CELL[1] + CELL[1] * .74 - LETTER * .35

    def presence(column: int, row: int, massed: bool = True) -> float:
        x, y = centre(column, row)
        return (gathered(x, y) if massed else 1) * veil(x, y) * edge(x, y)

    # The still letters: one <text> to a row, its strengths as spans, which paints faster than a <text> per strength.
    still = letters([(column, row, glyph, tint, presence(column, row)) for column, row, glyph, tint in grid], 6, theme["field"], least=40)
    field = "".join(
        f'<text y="{line(row)}">' + "".join(f'<tspan x="{by_row[row][0]}" fill-opacity="{opacity}">{by_row[row][1]}</tspan>' for opacity, by_row in still.items() if row in by_row) + '</text>'
        for row in sorted({row for by_row in still.values() for row in by_row})
    )

    # Drops: now and then a ring spreads through the letters, an echo close behind it. A drop's letters are sorted
    # into rings one row deep; each ring lights as the wave reaches it and fades, weaker the farther out it lies.
    # Nothing is masked, and a ring that is not lit is not painted at all.
    cycle, life, depth = 18, 3.4, CELL[1]
    drops = []
    for cx, cy, reach, at in ((W - 152, 138, 240, 2.6), (150, 232, 215, 11.4)):
        for ring in range(round(reach / depth)):
            far = (ring + .5) * depth / reach
            near = [(column, row, glyph, tint, presence(column, row, massed=False)) for column, row, glyph, tint in grid
                    if ring * depth <= math.dist(centre(column, row), (cx, cy)) < (ring + 1) * depth]
            arrives = at + life * (1 - (1 - far) ** .42)  # quick off the mark, slowing as it spreads
            for opacity, by_row in letters(near, 2, theme["ring"] * (1 - far) ** 1.15).items():
                rows = "".join(f'<text y="{line(row)}" x="{xs}">{glyphs}</text>' for row, (xs, glyphs) in by_row.items())
                drops.append(f'<g class="ring" style="--p:{opacity};animation-delay:{fmt(arrives, 2)}s" visibility="hidden">{rows}</g>')

    waves = "".join(
        f'<g class="tide" style="animation-duration:{seconds}s;animation-delay:-{seconds * .37:.1f}s'
        f'{";animation-direction:reverse" if direction < 0 else ""}"><path transform="scale({fmt(W / 1440, 4)} {fmt(tide / 160, 4)})" '
        f'd="{path}" fill-opacity="{opacity}"/></g>'
        for path, opacity, seconds, direction in WAVES
    )
    sig_defs, sig = signature(sig_x, sig_y, sig_w, theme["accent"])
    glow = "".join(f'<stop offset="{offset}" stop-color="{theme["accent"]}" stop-opacity="{fmt(theme["wash"] * value, 3)}"/>' for offset, value in ((0, 1), (.35, .7), (.7, .26), (1, 0)))
    defs = (
        '<defs>'
        # A pool of the second ink under the lettering, widest at the foot.
        f'<radialGradient id="w" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1" gradientTransform="translate({W / 2} {H - 6}) scale({W * .51} {pool})">{glow}</radialGradient>'
        # The tide: three lines slide past each other and take the foot away in steps.
        f'<mask id="e" maskUnits="userSpaceOnUse" x="0" y="{H - pool - 8}" width="{W}" height="{pool + 8}"><rect y="{H - pool - 8}" width="{W}" height="{pool + 8}" fill="#fff"/>'
        f'<g transform="translate(0 {foot})">{waves}</g></mask>'
        f'{sig_defs}</defs>'
    )
    body = (
        f'{defs}<rect y="{H - pool - 8}" width="{W}" height="{pool + 8}" fill="url(#w)" mask="url(#e)"/>'
        f'<g font-family="{MONO}" font-size="{LETTER}"><g fill="{theme["ink"]}">{field}</g><g fill="{theme["accent"]}">{"".join(drops)}</g></g>'
        f'<g fill="{theme["ink"]}">{name(sig_x + sig_w * .07, 38, 35)}</g>{sig}'
    )
    style = (
        f'.tide{{animation:tide linear infinite}}@keyframes tide{{to{{transform:translateX(-{W}px)}}}}'
        # Writing: the pens show while they write, then give way to the outlines.
        '.writing{animation:shown linear}@keyframes shown{0%,to{visibility:visible}}'
        '.written{animation:held linear}@keyframes held{0%,to{visibility:hidden}}'
        '.pen{animation:pen cubic-bezier(.33,0,.36,1) both}'
        '@keyframes pen{0%{stroke-dashoffset:1;opacity:0}.1%{stroke-dashoffset:1;opacity:1}to{stroke-dashoffset:0;opacity:1}}'
        '.stamp{transform-box:fill-box;transform-origin:50% 85%;animation:stamp .5s cubic-bezier(.16,1,.3,1) both}'
        '@keyframes stamp{0%{opacity:0;transform:scale(1.2)}}'
        # A ring's moment, a little over a second: up, down, the echo's smaller swell, out; then hidden until the next cycle.
        f'.ring{{animation:ring {cycle}s linear infinite}}'
        '@keyframes ring{0%{visibility:visible;fill-opacity:0}.7%{fill-opacity:var(--p)}2.4%{fill-opacity:calc(var(--p)*.22)}'
        '3.3%{fill-opacity:calc(var(--p)*.4)}6.4%{visibility:visible;fill-opacity:0}6.41%,to{visibility:hidden;fill-opacity:0}}'
    )
    return svg(W, H, "柊東雲 · Hiiragi Shinonome", body, style)


# ------------------------------------------------------------------------------------------------ motto ----
#
# 溶字. On the site the pointer is a drop of solvent: where it touches the line, the type comes apart into the small
# letters of the field, which swirl round the drop and settle back when it has gone. A README picture cannot feel
# a pointer, so here the drop falls by itself: the two lines condense out of loose letters when the picture first
# shows, and after that a drop lands on 解 and on 存 in turn, every sixteen seconds.

SPECK = 7  # type size of the loose letters


def blend(low: str, high: str, share: float) -> str:
    """A colour `share` of the way from one hex colour to another."""
    mix = [round(int(low[at:at + 2], 16) + (int(high[at:at + 2], 16) - int(low[at:at + 2], 16)) * share) for at in (1, 3, 5)]
    return "#" + "".join(f"{channel:02X}" for channel in mix)


def ink_points(run, size: float, step: float, rng: random.Random) -> list[tuple[int, float, float]]:
    """Where a line's ink lies: (which glyph, x from the line's left end, y from its baseline) for the points of a
    grid `step` apart that fall on ink, each nudged a little off the grid."""
    fine = 8  # the line is drawn this many times larger and read back, so thin strokes are not missed
    left, top = size, size * 1.3
    width, height = run.width + size * 2, size * 2.2
    font = ImageFont.truetype(str(FONTS / "LXGWWenKaiGB-Regular.ttf"), round(size * fine))
    sheet = Image.new("L", (math.ceil(width * fine), math.ceil(height * fine)), 0)
    pen = ImageDraw.Draw(sheet)
    for item in run.placed:
        pen.text(((left + item.x) * fine, top * fine), item.character, font=font, fill=255, anchor="ls")
    ink = sheet.load()
    starts = [item.x for item in run.placed]
    points = []
    for row in range(int(height / step)):
        for column in range(int(width / step)):
            x, y = (column + .5) * step, (row + .5) * step
            if ink[int(x * fine), int(y * fine)] > 110:
                glyph = max(order for order, start in enumerate(starts) if start <= x - left + .01) if x - left >= 0 else 0
                points.append((glyph, x - left + rng.uniform(-.25, .25) * step, y - top + rng.uniform(-.25, .25) * step))
    return points


def specks(points: list[tuple[float, float]], tones: list[str], rng: random.Random) -> str:
    """Loose letters at the given points, in the field's glyphs and a few tones: one <text>, a span to each tone."""
    by_tone: dict[int, list[tuple[float, float, str]]] = {}
    for x, y in points:
        by_tone.setdefault(rng.randrange(len(tones)), []).append((x, y + SPECK * .34, rng.choice(GLYPHS)))
    return "<text>" + "".join(
        f'<tspan fill="{tones[tone]}" x="{" ".join(fmt(x) for x, _, _ in group)}" y="{" ".join(fmt(y) for _, y, _ in group)}">{"".join(glyph for _, _, glyph in group)}</tspan>'
        for tone, group in sorted(by_tone.items())
    ) + "</text>"


def motto(theme: dict) -> str:
    size, track, leading, pad_x, pad_y = 21, .1, 1.8, 44, 30
    rng = random.Random(4096)
    tones = [blend(theme["ink"], theme["accent"], share / 3) for share in range(4)]
    runs = [TEXT.run(text, size, track) for text in MOTTO]
    inset = 1.2 * size  # the second line is stepped in and a tone lighter
    width = max(runs[0].width, inset + runs[1].width) + pad_x * 2
    height = len(runs) * size * leading + pad_y * 2
    cycle, reach = 16, 30
    drops = {(0, MOTTO[0].index("解")): 6.0, (1, MOTTO[1].index("存")): 14.0}  # (line, glyph): seconds into the cycle

    glyphs, cloud, loose, holes, last = [], [], [], [], 0.0
    for row, run in enumerate(runs):
        left, base = pad_x + row * inset, baseline(pad_y + row * size * leading, size, leading)
        middle, span = run.width / 2, run.width / 2 + 24
        points = ink_points(run, size, 3.2, rng)
        paths = []
        for order, (_, x, d) in enumerate(run.each()):
            # The line is uncovered from both ends towards its middle, as a hole closing on it would: `lands` is when
            # the closing edge reaches this glyph.
            far, low, high = abs(x + size / 2 - middle) / span, 0.0, 1.0
            for _ in range(30):
                turn = (low + high) / 2
                low, high = (turn, high) if 1 - turn * turn * (3 - 2 * turn) > far else (low, turn)
            lands = .9 + row * .35 + .8 * low
            last = max(last, lands)
            paths.append((order, f'<path class="in" style="animation-delay:{fmt(lands - .05, 2)}s" transform="translate({fmt(left + x, 2)} {fmt(base, 2)})" d="{d}"/>'))
            # Its loose letters fly in from where they drifted, in three handfuls, and give way to the glyph as they land.
            mine = [(left + px, base + py) for glyph, px, py in points if glyph == order]
            rng.shuffle(mine)
            for share in range(3):
                handful = mine[share::3]
                if handful:
                    cloud.append(f'<g class="fly" style="--d:{fmt(rng.uniform(-38, 38))}px,{fmt(rng.uniform(-24, 24))}px;animation-delay:{fmt(lands - .78 + rng.uniform(0, .08), 2)}s">{specks(handful, tones, rng)}</g>')
        colour = theme["muted"] if row else theme["ink"]
        touched = set()
        for (line, glyph), at in drops.items():
            if line != row:
                continue
            # A drop: a soft-edged hole opens in the glyphs it covers, and the ink that was there goes round its rim.
            cx, cy = left + run.placed[glyph].x + size / 2, base - size * .36
            number = len(holes)
            holes.append(
                f'<mask id="h{number}" maskUnits="userSpaceOnUse" x="{fmt(cx - size * 1.9)}" y="{fmt(cy - size)}" width="{fmt(size * 3.8)}" height="{fmt(size * 2)}">'
                f'<rect x="{fmt(cx - size * 1.9)}" y="{fmt(cy - size)}" width="{fmt(size * 3.8)}" height="{fmt(size * 2)}" fill="#fff"/>'
                f'<circle class="hole" style="animation-delay:{at}s" cx="{fmt(cx)}" cy="{fmt(cy)}" r="{reach}" fill="url(#q)" opacity="0"/></mask>'
            )
            covered = [order for order, _ in paths if abs(order - glyph) <= 1]
            touched.update(covered)
            glyphs.append(f'<g fill="{colour}" mask="url(#h{number})">{"".join(path for order, path in paths if order in covered)}</g>')
            # Each letter the drop loosens goes its own way: pushed out to the rim, carried some way round it, and
            # home again. How far round and how far out differ from letter to letter, so they spread instead of
            # travelling in a clump; the ones nearest the middle of the drop are let go first.
            for _, px, py in points:
                x, y = left + px, base + py
                away = math.dist((x, y), (cx, cy))
                if away >= reach:
                    continue
                angle, rim, carry = math.atan2(y - cy, x - cx), reach * rng.uniform(1.02, 1.42), rng.uniform(.5, 2.1)
                stops = [f"{fmt(cx + math.cos(angle + carry * share) * (rim + swell) - x)}px,{fmt(cy + math.sin(angle + carry * share) * (rim + swell) - y)}px"
                         for share, swell in ((.22, -3), (.62, 2), (1, 0))]
                loose.append(f'<text class="loose" style="--a:{stops[0]};--b:{stops[1]};--c:{stops[2]};animation-delay:{fmt(at + away / reach * .16, 2)}s" visibility="hidden" '
                             f'x="{fmt(x)}" y="{fmt(y + SPECK * .34)}" fill="{rng.choice(tones)}">{rng.choice(GLYPHS)}</text>')
        glyphs.append(f'<g fill="{colour}">{"".join(path for order, path in paths if order not in touched)}</g>')

    body = (
        '<defs><radialGradient id="q"><stop offset="0"/><stop offset=".76"/><stop offset="1" stop-opacity="0"/></radialGradient>'
        f'{"".join(holes)}</defs>{"".join(glyphs)}'
        f'<g font-family="{MONO}" font-size="{SPECK}" text-anchor="middle">'
        f'<g class="cloud" style="animation-duration:{fmt(last + .4, 2)}s" visibility="hidden">{"".join(cloud)}</g>{"".join(loose)}</g>'
    )
    style = (
        '.in{animation:in .32s ease both}@keyframes in{0%{opacity:0}}'
        # Condensing: each handful flies home, and fades as the glyph it belongs to is uncovered.
        '.cloud{animation:shown linear}@keyframes shown{0%,to{visibility:visible}}'
        '.fly{animation:fly .9s cubic-bezier(.16,1,.3,1) both}'
        '@keyframes fly{0%{transform:translate(var(--d));fill-opacity:0}50%{fill-opacity:.9}82%{transform:none;fill-opacity:.9}to{transform:none;fill-opacity:0}}'
        # A drop, two and a half seconds of the cycle: the hole opens, stays and closes; the letters go out and come home.
        f'.hole{{transform-box:fill-box;transform-origin:center;animation:hole {cycle}s ease-in-out infinite}}'
        '@keyframes hole{0%{opacity:0;transform:scale(.25)}1.9%,11.9%{opacity:1;transform:scale(1)}13.9%,to{opacity:0;transform:scale(.25)}}'
        f'.loose{{animation:loose {cycle}s cubic-bezier(.3,.6,.3,1) infinite}}'
        '@keyframes loose{0%{visibility:visible;fill-opacity:0;transform:none}1.6%{fill-opacity:.9;transform:translate(var(--a))}6.2%{transform:translate(var(--b))}'
        '11.9%{fill-opacity:.9;transform:translate(var(--c))}14.2%{fill-opacity:.7;transform:none}15.2%{visibility:visible;fill-opacity:0}15.21%,to{visibility:hidden;fill-opacity:0}}'
    )
    return svg(width, height, "".join(MOTTO), body, style)


# ------------------------------------------------------------------------------------------------ medallion ----

def medallion(theme: dict) -> str:
    """The portrait medallion: the picture in a double ring, a line of names turning round it one way and a ring of
    ticks the other, a little dust drifting along the rim; under it the name and its reading."""
    W, H, cx, cy, radius = 240, 292, 120, 116, 74
    unit = 1.38 * 2 * radius / 200  # the rings are drawn 200 across, on a square 138% of the medallion
    rng = random.Random(1108)

    # The names, spread evenly round a circle of 86.5.
    size, around = 9.6 * unit, 86.5 * unit
    faces = [IDEOGRAPH if 0x4E00 <= ord(character) <= 0x9FFF else RING for character in ORBIT]
    advances = [face.glyph(character).advance * size for face, character in zip(faces, ORBIT)]
    spacing = (2 * math.pi * around - sum(advances)) / len(ORBIT)
    names, along = [], 0.0
    for face, character, advance in zip(faces, ORBIT, advances):
        d = face.run(character, size).d(-advance / 2, 0, 2)
        if d:
            names.append(f'<path transform="rotate({fmt((along + advance / 2) / around * 180 / math.pi, 2)}) translate(0 {fmt(-around, 2)})" d="{d}"/>')
        along += advance + spacing
    ticks, dash = 100 * unit, .8 * unit

    # Thirty specks of dust in six rings of five, each ring turning at its own pace (one of them backwards); every
    # sixth speck is a four-point glint. The glints and every other speck brighten and dim, each on its own time;
    # the rest hold steady, which keeps down the number of animations the browser has to keep running.
    dust = []
    for ring, pace in enumerate((.07, .1, .13, .16, .2, -.11)):
        motes = []
        for order in range(5):
            away, angle, grain = radius * rng.uniform(1.1, 1.44), rng.uniform(0, 2 * math.pi), rng.uniform(.6, 1.9)
            x, y = math.cos(angle) * away, math.sin(angle) * away
            glint = (ring * 5 + order) % 6 == 0
            blink = f'class="glint" style="animation-duration:{fmt(math.pi / rng.uniform(.6, 2.4), 2)}s;animation-delay:-{fmt(rng.uniform(0, 5), 2)}s" ' if glint or order % 2 else 'opacity=".55" '
            if glint:
                long, short = grain * 2.8, grain * .42
                motes.append(f'<path {blink}fill-opacity=".85" d="M{fmt(x)} {fmt(y - long)}Q{fmt(x + short)} {fmt(y - short)} {fmt(x + long)} {fmt(y)}Q{fmt(x + short)} {fmt(y + short)} {fmt(x)} {fmt(y + long)}'
                             f'Q{fmt(x - short)} {fmt(y + short)} {fmt(x - long)} {fmt(y)}Q{fmt(x - short)} {fmt(y - short)} {fmt(x)} {fmt(y - long)}Z"/>')
            else:
                motes.append(f'<circle {blink}cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(grain, 2)}" fill-opacity=".7"/>')
        turn = f'animation-duration:{fmt(2 * math.pi / abs(pace), 1)}s{";animation-direction:reverse" if pace < 0 else ""}'
        dust.append(f'<g class="turn" style="{turn}">{"".join(motes)}</g>')

    # The name in its own hand, then its reading.
    lettering, letter, track = LETTERING["name"], 30.4, .3
    top = cy + radius + 32
    start = cx - (3 * letter + 2 * track * letter) / 2
    name_base = top + (1.3 * letter - 1.437 * letter) / 2 + 1.151 * letter
    name = "".join(
        f'<g transform="translate({fmt(start + order * (glyph["advance"] + track) * letter, 2)} {fmt(name_base, 2)}) scale({fmt(letter / lettering["upm"], 4)})">'
        f'<path class="rise" style="animation-delay:{fmt(.3 + order * .07, 2)}s" d="{glyph["d"]}"/></g>'
        for order, glyph in enumerate(lettering["glyphs"])
    )
    reading = TEXT.run(READING, 12.5, .08)
    reading_base = baseline(top + 1.3 * letter + 2.4, 12.5, 1.7)
    # avatar.webp is already cut round and toned (see tools/README.md), so nothing clips or filters it here.
    picture = base64.b64encode((HERE / "avatar.webp").read_bytes()).decode("ascii")

    body = (
        f'<g transform="translate({cx} {cy})"><g class="orbit">'
        f'<g class="turn" style="animation-duration:133.3s;animation-direction:reverse"><circle r="{fmt(ticks, 2)}" fill="none" stroke="{theme["accent"]}" stroke-opacity=".55" stroke-width="2.5" '
        f'stroke-dasharray="{fmt(dash, 3)} {fmt(2 * math.pi * ticks / 72 - dash, 3)}"/></g>'
        f'<g class="turn" style="animation-duration:80s" fill="{theme["ink"]}">{"".join(names)}</g>'
        f'<g fill="{theme["accent"]}">{"".join(dust)}</g></g></g>'
        f'<g class="strike"><image href="data:image/webp;base64,{picture}" x="{cx - radius}" y="{cy - radius}" width="{radius * 2}" height="{radius * 2}"/>'
        f'<g fill="none" stroke="{theme["ink"]}"><circle cx="{cx}" cy="{cy}" r="{radius + .5}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{fmt(radius * 1.12 - 4, 2)}"/><circle cx="{cx}" cy="{cy}" r="{fmt(radius * 1.12 - .5, 2)}"/></g></g>'
        f'<g fill="{theme["ink"]}">{name}</g>'
        f'<path class="lift" fill="{theme["muted"]}" d="{reading.d(cx - reading.width / 2, reading_base)}"/>'
    )
    style = (
        '.turn{animation:turn linear infinite}@keyframes turn{to{transform:rotate(360deg)}}'
        '.glint{animation:glint ease-in-out infinite}@keyframes glint{0%,to{opacity:.22}50%{opacity:1}}'
        # Arriving: the medallion is struck like a coin, the rings close in round it, the name comes up glyph by glyph.
        '.strike{transform-box:fill-box;transform-origin:center;animation:strike .9s cubic-bezier(.16,1,.3,1) both}'
        '@keyframes strike{0%{opacity:0;transform:scale(.62) rotate(-18deg)}30%{opacity:1}}'
        '.orbit{animation:orbit 1s cubic-bezier(.16,1,.3,1) .22s both}@keyframes orbit{0%{opacity:0;transform:scale(1.28) rotate(40deg)}}'
        '.rise{transform-box:fill-box;transform-origin:center;animation:rise .7s cubic-bezier(.16,1,.3,1) both}'
        '@keyframes rise{0%{opacity:0;transform:translateY(.7em) rotate(8deg)}}'
        '.lift{animation:lift .7s cubic-bezier(.16,1,.3,1) .6s both}@keyframes lift{0%{opacity:0;transform:translateY(14px)}}'
    )
    return svg(W, H, f"柊東雲 · {READING}", body, style)


# ------------------------------------------------------------------------------------------------ emit ----

def main():
    OUT.mkdir(exist_ok=True)
    for stale in OUT.glob("*.svg"):
        stale.unlink()
    for picture, draw in {"cover": cover, "motto": motto, "medallion": medallion}.items():
        for key, theme in THEMES.items():
            target = OUT / f"{picture}-{key}.svg"
            target.write_text(draw(theme), encoding="utf-8", newline="\n")
        print(f"{picture:10s} {target.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
