# tools

主页三幅图（`assets/` 里的封面、题词、头像字章，各有日间与夜间两份）的生成脚本。

GitHub 通过图片代理显示 README 里的 SVG，脚本、外部字体和外部链接都不会生效，图片也收不到鼠标事件，所以：

- 没有交互。博客上跟着鼠标走的效果（溶字）在这里改成自己播放：题词先由散字凝成，之后每十六秒各有一滴「溶剂」落在「解」和「存」上。
- 姓名、签名、题词、字章的文字全部转成轮廓路径；只有封面的小字母和溶字的散字是活的 `<text>`，用读者机器上的等宽字体。
- 头像直接嵌在字章的 SVG 里（外链图片会被拦掉）。
- 动效只用 SVG 内的 CSS 动画，默认状态就是完成后的画面；系统开启「减少动态效果」时不播放。
- 日夜两套靠 README 里的 `<picture>` 切换，不靠 SVG 内部的媒体查询（那只认系统设置，不认 GitHub 的主题）。

## 一次性准备

```
pip install fonttools brotli pillow
```

把字体放进 `tools/fonts/`（已被 .gitignore 忽略，不入库），都是 SIL OFL 1.1 授权：

- `LXGWWenKaiGB-Regular.ttf`、`LXGWWenKaiGB-Medium.ttf`：霞鹜文楷 GB，<https://github.com/lxgw/LxgwWenKaiGB/releases>
- `Figtree[wght].ttf`：<https://github.com/google/fonts/tree/main/ofl/figtree>

已经入库、一般不用动的两份素材：

- `lettering.json`：「柊東雲」三字与 Hiiragi Shinonome 签名的轮廓和笔画中心线。字样本身改了才需要用 `import_lettering.py` 重新导入。
- `avatar.webp`：字章里的头像，296×296，已经裁成圆形（取原图正中的 1/1.1，让原图自带的细环落在圈外），并降了一点饱和度（0.82）、提了一点对比度（1.04）。换头像时按同样的办法处理后覆盖这个文件。

## 重新生成

```
cd tools
python build_assets.py
```

输出写入 `../assets/`。配色、题词、字章上转动的名字在 `build_assets.py` 顶部；封面的构图在 `cover()` 里，溶字的时刻与落点在 `motto()` 里，字章在 `medallion()` 里。

```
python preview.py
```

写出仓库根目录的 `preview.html`（不入库）：按 GitHub 的版心摆好三幅图，可切日间 / 夜间、可重播，推送前先在这里看。

## 改动时留意

带动画的 SVG 只要里面还有动画在跑，浏览器每一帧都会把整幅图重画一遍。所以封面不用遮罩叠字母、签名写完就换成静态轮廓、没亮起的字不画；字章的头像预先裁圆，不在运行时裁切。加新效果前先量一下占用，别让它比现在重。
