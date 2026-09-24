"""共通設定：パス・フォント・ブランドカラー（色は AKARI_COLOR_PALETTE.json から読む）。"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / "brand"
AKARI = BRAND / "akari"
OOKA_M = BRAND / "ooka_m"
YT = ROOT / "youtube" / "akari_news"

FONT_CANDIDATES = {
    "sans": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"],
    "sans_medium": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"],
    "sans_bold": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"],
    "sans_black": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"],
    "serif_bold": ["/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"],
    "serif_black": ["/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"],
}


def font(kind="sans", size=40):
    from PIL import ImageFont
    for p in FONT_CANDIDATES[kind]:
        if os.path.exists(p):
            # Noto CJK の .ttc は index 0 が JP
            return ImageFont.truetype(p, size, index=0) if p.endswith(".ttc") else ImageFont.truetype(p, size)
    raise FileNotFoundError("日本語フォントがありません: apt-get install fonts-noto-cjk")


def palette():
    d = json.loads((AKARI / "AKARI_COLOR_PALETTE.json").read_text(encoding="utf-8"))
    c = {x["id"]: x["hex"] for x in d["colors"] + d["functional"]}
    # 派生色（ネイビーの濃淡。新しい色相は追加しない）
    c["NAVY_DEEP"] = "#101B35"
    c["NAVY_MID"] = "#24386A"
    c["TEXT_MUTED"] = "#8A93A6"
    return c


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def episode_dir(ep_id):
    return YT / ep_id
