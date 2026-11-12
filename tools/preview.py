"""Write ../preview.html: the README as GitHub lays it out, with day and night to switch between and a replay.

The pictures are packed into the page (gzip, then base64), so it stands alone: it can be opened from anywhere, or
shown in a pane that has no access to the folder, and stays small enough for one that limits the size of a page.
It is not part of the profile and is ignored by git.

  python preview.py
"""
import base64
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
TARGET = HERE.parent / "preview.html"

PAGE = """<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitHub 主页预览</title>
<style>
    :root { --bg: #ffffff; --fg: #1f2328; --border: #d1d9e0; --muted: #59636e; }
    :root[data-theme='dark'] { --bg: #0d1117; --fg: #f0f6fc; --border: #3d444d; --muted: #9198a1; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 28px 16px 64px; background: var(--bg); color: var(--fg); font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif; }
    .bar { display: flex; gap: 6px; justify-content: center; margin-bottom: 22px; }
    .bar button { padding: 5px 14px; border: 1px solid var(--border); border-radius: 6px; background: none; color: var(--muted); font: inherit; cursor: pointer; }
    .bar button[aria-pressed='true'] { color: var(--fg); border-color: var(--muted); }
    .box { max-width: 896px; margin: 0 auto; padding: 24px; border: 1px solid var(--border); border-radius: 6px; }
    .label { margin-bottom: 16px; color: var(--muted); font: 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    article p { margin: 0 0 16px; text-align: center; }
    article p:last-child { margin-bottom: 0; }
    article img { max-width: 100%; }
    @media (max-width: 600px) { .box { padding: 16px; } }
</style>
</head>
<body>
<div class="bar">
    <button type="button" data-set="light">日间</button>
    <button type="button" data-set="dark">夜间</button>
    <button type="button" data-replay>重播</button>
</div>
<div class="box">
    <div class="label">xi-kari / README.md</div>
    <article>
        <p><img data-name="cover" width="100%" alt="柊東雲 · Hiiragi Shinonome"></p>
        <p><img data-name="motto" height="136" alt="真理是溶解世界万物的溶剂，因而绝无法在客观上存在"></p>
        <p><img data-name="medallion" width="240" alt="柊東雲 · ひいらぎしののめ / Hiiragi Shinonome"></p>
    </article>
</div>
<script>
    const packed = __PICTURES__;
    const root = document.documentElement;
    const unpack = async (key) => {
        const bytes = Uint8Array.from(atob(packed[key]), (character) => character.charCodeAt(0));
        return new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).blob();
    };
    const show = async (theme) => {
        root.dataset.theme = theme;
        for (const button of document.querySelectorAll('[data-set]')) button.setAttribute('aria-pressed', String(button.dataset.set === theme));
        for (const image of document.querySelectorAll('img[data-name]')) {
            // Each showing gets an address of its own, so the browser loads the picture afresh and its motion starts over.
            const next = URL.createObjectURL(new Blob([await unpack(`${image.dataset.name}-${theme}`)], { type: 'image/svg+xml' }));
            if (image.src.startsWith('blob:')) URL.revokeObjectURL(image.src);
            image.src = next;
        }
    };
    for (const button of document.querySelectorAll('[data-set]')) button.addEventListener('click', () => show(button.dataset.set));
    document.querySelector('[data-replay]').addEventListener('click', () => show(root.dataset.theme));
    show(matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
</script>
</body>
</html>
"""


def main():
    pictures = {
        f"{name}-{theme}": base64.b64encode(gzip.compress((ASSETS / f"{name}-{theme}.svg").read_bytes(), mtime=0)).decode("ascii")
        for name in ("cover", "motto", "medallion") for theme in ("light", "dark")
    }
    TARGET.write_text(PAGE.replace("__PICTURES__", json.dumps(pictures)), encoding="utf-8", newline="\n")
    print(f"{TARGET.name} {TARGET.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
