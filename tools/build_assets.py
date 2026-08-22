"""Build the 東雲 dawn asset set for the xi-kari profile README.

Outputs (to ../assets/):
  dawn-banner-dark.svg / dawn-banner-light.svg   — hero wordmark over a horizon
  dawn-rule-dark.svg   / dawn-rule-light.svg     — section divider (padded viewBox)

All text is outlined to <path> (no <text>, no external refs, no page-bg fills):
GitHub's image proxy strips external font references from SVGs.
Download the fonts into tools/fonts/ first — see tools/README.md.
"""
from pathlib import Path

from textpath import load_font, text_to_path

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
OUT = HERE.parent / "assets"

wenkai = load_font(str(FONTS / "LXGWWenKai-Light.ttf"), None)
sg300 = load_font(str(FONTS / "SpaceGrotesk.ttf"), 300)


def run(font, text, size, tracking=0.0):
    return text_to_path(font, text, size, tracking)


def centered_path(runinfo, cx, baseline, fill, opacity=None):
    tx = cx - runinfo["width"] / 2
    op = f' fill-opacity="{opacity}"' if opacity is not None else ""
    return (
        f'<path transform="translate({tx:.1f},{baseline})" '
        f'fill="{fill}"{op} d="{runinfo["d"]}"/>'
    )


def stops(pairs):
    return "".join(
        f'<stop offset="{o}%" stop-color="{c}" stop-opacity="{a}"/>'
        for o, c, a in pairs
    )


# ---------------------------------------------------------------- banner ----

KANJI = run(wenkai, "柊東雲", 116, tracking=16)
LATIN = run(sg300, "xi-kari", 32, tracking=13)

BANNER_THEMES = {
    "dark": dict(
        sky=[(0, "#131937", 0), (45, "#131937", 0.28), (76, "#262354", 0.42),
             (90, "#5E4265", 0.50), (97, "#B27478", 0.42), (100, "#DEA36D", 0.30)],
        below=[(0, "#070A19", 0.55), (55, "#070A19", 0.18), (100, "#070A19", 0)],
        amb=("#E8B84B", 0.16),
        glow=("#F0C86E", 0.55),
        breathe=(0.45, 0.95, 0.6),
        hz=[(0, "#F5CE87", 0), (34, "#C4927C", 0.25), (52, "#F0C87E", 0.70),
            (58, "#F5CE87", 1), (64, "#F0C87E", 0.55), (80, "#C4927C", 0.20),
            (100, "#F5CE87", 0)],
        sun="#F7D18C", halo=0.25,
        kanji="#ECEAF4", latin="#A6ACC8",
    ),
    "light": dict(
        sky=[(0, "#F4ECE2", 0), (50, "#F4ECE2", 0.50), (82, "#F0DED2", 0.70),
             (94, "#EBC9BE", 0.70), (100, "#E4B696", 0.55)],
        below=[(0, "#F0E9DE", 0.65), (55, "#F0E9DE", 0.25), (100, "#F0E9DE", 0)],
        amb=("#C99745", 0.14),
        glow=("#C99745", 0.40),
        breathe=(0.35, 0.75, 0.55),
        hz=[(0, "#B8863B", 0), (34, "#A06E50", 0.30), (52, "#C99745", 0.75),
            (58, "#B8863B", 1), (64, "#C99745", 0.55), (80, "#A06E50", 0.22),
            (100, "#B8863B", 0)],
        sun="#B8863B", halo=0.22,
        kanji="#23263B", latin="#6E6B7E",
    ),
}


def banner(theme):
    t = BANNER_THEMES[theme]
    lo, hi, static = t["breathe"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1660 460" role="img" aria-labelledby="bt bd">
<title id="bt">柊東雲 · xi-kari</title>
<desc id="bd">A quiet sky at the hour of 東雲: the name above a thin horizon carrying the first light of dawn, one point of gold beneath the final glyph.</desc>
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">{stops(t["sky"])}</linearGradient>
<linearGradient id="below" x1="0" y1="0" x2="0" y2="1">{stops(t["below"])}</linearGradient>
<radialGradient id="amb">{stops([(0, t["amb"][0], t["amb"][1]), (70, t["amb"][0], 0)])}</radialGradient>
<radialGradient id="glow">{stops([(0, t["glow"][0], t["glow"][1]), (70, t["glow"][0], 0)])}</radialGradient>
<linearGradient id="hz" x1="0" y1="0" x2="1" y2="0">{stops(t["hz"])}</linearGradient>
<style>.breathe{{animation:breathe 10s ease-in-out infinite}}@keyframes breathe{{0%,100%{{opacity:{lo}}}50%{{opacity:{hi}}}}}@media (prefers-reduced-motion:reduce){{.breathe{{animation:none;opacity:{static}}}}}</style>
</defs>
<rect x="0" y="0" width="1660" height="331" fill="url(#sky)"/>
<rect x="0" y="331" width="1660" height="129" fill="url(#below)"/>
<ellipse cx="962" cy="331" rx="360" ry="64" fill="url(#amb)"/>
<ellipse class="breathe" cx="962" cy="331" rx="150" ry="24" fill="url(#glow)"/>
<rect x="0" y="330" width="1660" height="2" fill="url(#hz)"/>
<circle cx="962" cy="331" r="8" fill="{t["sun"]}" fill-opacity="{t["halo"]}"/>
<circle cx="962" cy="331" r="3" fill="{t["sun"]}"/>
{centered_path(KANJI, 830, 198, t["kanji"])}
{centered_path(LATIN, 830, 254, t["latin"])}
</svg>'''


# ------------------------------------------------------------------ rule ----

RULE_THEMES = {
    "dark": [(0, "#5A6EC7", 0), (22, "#5A6EC7", 0.25), (46, "#8A76B5", 0.38),
             (66, "#D89692", 0.45), (80, "#E8B84B", 0.60), (88, "#E8B84B", 0),
             (100, "#E8B84B", 0)],
    "light": [(0, "#6D6A7E", 0), (22, "#6D6A7E", 0.25), (46, "#8F7FB0", 0.35),
              (66, "#C793A0", 0.45), (80, "#B8863B", 0.55), (88, "#B8863B", 0),
              (100, "#B8863B", 0)],
}


def rule(theme):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1660 48" role="presentation">
<defs><linearGradient id="r" x1="0" y1="0" x2="1" y2="0">{stops(RULE_THEMES[theme])}</linearGradient></defs>
<rect x="0" y="22.2" width="1660" height="3.6" fill="url(#r)"/>
</svg>'''


# ------------------------------------------------------------------ emit ----

files = {
    "dawn-banner-dark.svg": banner("dark"),
    "dawn-banner-light.svg": banner("light"),
    "dawn-rule-dark.svg": rule("dark"),
    "dawn-rule-light.svg": rule("light"),
}
for name, content in files.items():
    p = OUT / name
    p.write_text(content, encoding="utf-8", newline="\n")
    print(f"{name:24s} {p.stat().st_size/1024:6.1f} KB")

assert "<text" not in "".join(files.values()), "live <text> leaked into an asset"
print("kanji width", round(KANJI["width"], 1), "| latin width", round(LATIN["width"], 1))
