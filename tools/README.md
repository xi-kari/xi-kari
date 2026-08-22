# tools

主页视觉资产的生成脚本。横幅与分隔线里的所有文字都已转成 SVG 轮廓路径——GitHub 的图片代理不允许 SVG 引用外部字体，所以不能用 `<text>`。

## 一次性准备

```
pip install fonttools brotli
```

下载两个字体到 `tools/fonts/`（已被 .gitignore 忽略，不入库）：

- `LXGWWenKai-Light.ttf` — https://github.com/lxgw/LxgwWenKai/releases/download/v1.522/LXGWWenKai-Light.ttf
- `SpaceGrotesk.ttf` — https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf

两个字体都是 SIL OFL 1.1 授权。

## 重新生成

```
cd tools
python build_assets.py
```

输出写入 `../assets/`：`dawn-banner-{dark,light}.svg`、`dawn-rule-{dark,light}.svg`。改字、改配色都在 `build_assets.py` 顶部的常量里。

贡献蛇不在这里生成：`.github/workflows/snake.yml` 每天把拂晓配色的蛇渲染到 `output` 分支，改配色直接改该文件里的 `color_snake` / `color_dots`。
