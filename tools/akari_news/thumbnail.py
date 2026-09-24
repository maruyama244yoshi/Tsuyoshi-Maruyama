"""サムネイル（1280x720）テンプレート。燈は右、文字は左（AKARI_MASTER §9）。

  python3 -m tools.akari_news.thumbnail episode_001

文字は画像生成AIに書かせず、ここで後乗せする。煽り禁止ワードを含む場合は停止する。
"""
import argparse
import math

from PIL import Image, ImageDraw, ImageFilter

from .common import AKARI, ROOT, episode_dir, load_json
from .graphics import C, CUTS, draw_logo_mark, fit_size, gradient, hexrgb, text, tw

TW, TH = 1280, 720


# 高解像度の正式基本画像（AKARI_TALKING_BASE_16x9_v1）から顔まわりを切り出して使う
HIRES = {"akari_talking": (ROOT / "brand/akari/talking_base/AKARI_TALKING_BASE_16x9_v1.png", (520, 60, 1190, 900))}


def akari_panel(im, key, x0, fade=True):
    """燈の顔を右側に配置し、左端をグラデーションで背景になじませる。"""
    if key in HIRES:
        path, box = HIRES[key]
        src = Image.open(path).convert("RGB").crop(box)
    else:
        src = Image.open(CUTS[key]).convert("RGB")
    h = TH
    k = h / src.height * 1.05
    src = src.resize((math.ceil(src.width * k), math.ceil(src.height * k)), Image.LANCZOS)
    src = src.crop((0, 0, min(src.width, TW - x0), h))
    mask = Image.new("L", src.size, 255)
    if fade:
        md = ImageDraw.Draw(mask)
        for x in range(160):
            md.line([(x, 0), (x, h)], fill=int(255 * x / 160))
    im.paste(src, (x0, 0), mask)


def rate_line(d, box, color):
    """背景の控えめな上昇線（装飾。実データではない）。"""
    x0, y0, x1, y1 = box
    pts = [(x0 + (x1 - x0) * i / 7, y1 - (y1 - y0) * v) for i, v in enumerate((0.05, 0.08, 0.12, 0.2, 0.3, 0.45, 0.62, 0.8))]
    d.line(pts, fill=color, width=6, joint="curve")


def check_words(words):
    banned = load_json(AKARI / "AKARI_MASTER_v1.0.json")["thumbnail"]["banned_words"]
    for w in words:
        for b in banned:
            if b in w:
                raise SystemExit(f"サムネ文言に禁止ワード「{b}」が含まれます: {w}")


def compose(variant, top, main, sub, face_key="akari_talking"):
    check_words([top, main, sub])
    if variant == "C":
        im = gradient(TW, TH, C["WHITE"], C["LIGHT_GRAY"])
        ink, accent, subc = "NAVY", "NAVY", "NAVY_MID"
    else:
        im = gradient(TW, TH, C["NAVY_MID"], C["NAVY_DEEP"])
        ink, accent, subc = "WHITE", "GOLD", "WHITE"
    d = ImageDraw.Draw(im, "RGBA")
    if variant == "A":
        for y in range(120, 700, 90):
            d.line([(0, y), (760, y)], fill=hexrgb(C["WHITE"], 14))
        rate_line(d, (40, 330, 720, 660), hexrgb(C["GOLD"], 70))
    if variant == "B":
        bg = Image.open(CUTS["akari_desk"]).convert("RGB").resize((TW, TH)).filter(ImageFilter.GaussianBlur(18))
        im.paste(Image.blend(bg, im, 0.62))
        d = ImageDraw.Draw(im, "RGBA")
    akari_panel(im, face_key, 700 if variant != "C" else 720)
    d = ImageDraw.Draw(im, "RGBA")
    # 上部小見出し
    d.rounded_rectangle([50, 60, 60 + tw(d, top, 52, "sans_black") + 50, 140], 12, fill=hexrgb(C["GOLD"] if variant != "C" else C["NAVY"]))
    text(d, (80, 100), top, 52, "NAVY_DEEP" if variant != "C" else "WHITE", "sans_black", "lm")
    # メイン（大きな数字）
    size = fit_size(d, main, 230, 630, "sans_black")
    for off in ((5, 5),):
        text(d, (48 + off[0], 390 + off[1]), main, size, "NAVY_DEEP" if variant != "C" else "LIGHT_GRAY", "sans_black", "ls")
    text(d, (48, 390), main, size, accent, "sans_black", "ls")
    # 補助
    ssize = fit_size(d, sub, 92, 630, "sans_black")
    text(d, (54, 540), sub, ssize, subc, "sans_black", "ls")
    # ロゴ
    draw_logo_mark(d, 54, 610, 58, "GOLD")
    text(d, (124, 648), "燈の不動産NEWS", 32, ink if variant == "C" else "WHITE", "serif_bold", "lm")
    return im


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    a = ap.parse_args(argv)
    d = episode_dir(a.episode) / "thumbnail"
    d.mkdir(exist_ok=True)
    spec = [("A", "日銀 利上げ", "1.25％へ", "大家はどうする？"),
            ("B", "日銀 利上げ", "1.25％へ", "大家が見る3つの数字"),
            ("C", "日銀 利上げ", "1.25％へ", "大家はどうする？")]
    tiles = []
    for v, top, main_, sub in spec:
        im = compose(v, top, main_, sub)
        p = d / f"{a.episode}_thumbnail_{v.lower()}.png"
        im.save(p)
        tiles.append(im)
        print("wrote", p)
    # 一覧（小サイズでの視認性確認用：YouTube一覧は幅320px前後）
    sheet = Image.new("RGB", (3 * 330 + 10, 200), "white")
    for i, im in enumerate(tiles):
        sheet.paste(im.resize((320, 180)), (10 + i * 330, 10))
    sheet.save(d / f"{a.episode}_thumbnail_preview_small.png")


if __name__ == "__main__":
    main()
