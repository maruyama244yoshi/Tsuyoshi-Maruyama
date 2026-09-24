"""番組グラフィック（16:9 / 9:16）とロゴを描画する。

  python3 -m tools.akari_news.graphics episode_001        # 本編・Shorts用の全グラフィック
  python3 -m tools.akari_news.graphics --logo             # ロゴ・アイコン・バナー案

数値は loan.py から算出し、グラフィックに直書きしない。
キャラクターカットは現在 AKARI_REFERENCE_001 からの切り出し（仮素材）。本番用に AKARI_MASTER
準拠で生成した画像へ差し替える場合は CUTS の参照先を変更する。
"""
import argparse
import math

from PIL import Image, ImageDraw, ImageFilter

from .common import AKARI, BRAND, OOKA_M, episode_dir, font, load_json, palette
from .loan import NOTE, annual_payment, man

C = palette()
W, H = 1920, 1080
SAFE_BOTTOM = 860  # これより下は字幕帯

CUTS = {
    "akari_front": AKARI / "references/cuts/AKARI_REF001_CAM01_front.png",
    "akari_desk": AKARI / "references/cuts/AKARI_REF001_CAM03_desk.png",
    "akari_thumb": AKARI / "references/cuts/AKARI_REF001_CAM05_thumb.png",
    "akari_serious": AKARI / "references/cuts/AKARI_REF001_FACE02_serious.png",
    "ooka_m": OOKA_M / "references/cuts/OOKA_M_REF001_banner.png",
    "ooka_m_think": OOKA_M / "references/cuts/OOKA_M_REF001_face_think.png",
}
PROVISIONAL = "仮素材：AKARI_REFERENCE_001 より切り出し（本番は AKARI_MASTER 準拠の生成画像に差替）"


def hexrgb(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def gradient(w, h, top, bottom):
    t, b = hexrgb(top), hexrgb(bottom)
    col = Image.new("RGB", (1, h))
    for y in range(h):
        k = y / max(1, h - 1)
        col.putpixel((0, y), tuple(int(t[i] + (b[i] - t[i]) * k) for i in range(3)))
    # RGBキャンバスに "RGBA" モードで描くと半透明色が正しくブレンドされる
    return col.resize((w, h))


def base(w=W, h=H):
    im = gradient(w, h, C["NAVY_MID"], C["NAVY_DEEP"])
    d = ImageDraw.Draw(im, "RGBA")
    # 控えめな都市グリッド（背景の質感）
    for x in range(0, w, 80):
        d.line([(x, 0), (x, h)], fill=hexrgb(C["WHITE"], 9))
    for y in range(0, h, 80):
        d.line([(0, y), (w, y)], fill=hexrgb(C["WHITE"], 9))
    return im


def text(d, xy, s, size, color="WHITE", kind="sans_bold", anchor="la", **kw):
    d.text(xy, s, font=font(kind, size), fill=hexrgb(C.get(color, color)), anchor=anchor, **kw)


def tw(d, s, size, kind="sans_bold"):
    b = d.textbbox((0, 0), s, font=font(kind, size))
    return b[2] - b[0]


def fit_size(d, s, size, max_w, kind="sans_bold"):
    while size > 12 and tw(d, s, size, kind) > max_w:
        size -= 2
    return size


def header(im, label, sub=None):
    d = ImageDraw.Draw(im, "RGBA")
    w = im.width
    d.rectangle([0, 0, w, 96], fill=hexrgb(C["NAVY_DEEP"], 235))
    d.rectangle([0, 96, w, 100], fill=hexrgb(C["GOLD"]))
    draw_logo_mark(d, 40, 18, 60)
    text(d, (118, 48), "燈の不動産NEWS", 30, "WHITE", "serif_bold", "lm")
    lx = 118 + tw(d, "燈の不動産NEWS", 30, "serif_bold") + 40
    d.rounded_rectangle([lx, 24, lx + tw(d, label, 32) + 44, 74], 6, fill=hexrgb(C["GOLD"]))
    text(d, (lx + 22, 49), label, 32, "NAVY_DEEP", "sans_bold", "lm")
    if sub:
        text(d, (lx + tw(d, label, 32) + 70, 49), sub, 28, "LIGHT_GRAY", "sans_medium", "lm")


def footer_note(im, s, y=None):
    d = ImageDraw.Draw(im, "RGBA")
    y = y or SAFE_BOTTOM - 18
    text(d, (im.width - 50, y), s, 22, "TEXT_MUTED", "sans", "rs")


def panel(d, box, fill="NAVY_DEEP", alpha=225, outline=None, r=18):
    d.rounded_rectangle(box, r, fill=hexrgb(C[fill], alpha), outline=hexrgb(C[outline]) if outline else None,
                        width=3 if outline else 0)


def draw_logo_mark(d, x, y, s, gold="GOLD"):
    """家（屋根）＋上昇バー＋光。s=サイズ(px)"""
    g = hexrgb(C[gold])
    lw = int(max(2, s // 18))
    # 屋根
    d.line([(x, y + s * 0.52), (x + s * 0.5, y + s * 0.08), (x + s, y + s * 0.52)], fill=g, width=lw, joint="curve")
    # バー
    bw = s * 0.12
    for i, hgt in enumerate((0.18, 0.28, 0.40, 0.52)):
        bx = x + s * 0.2 + i * (bw + s * 0.05)
        d.rectangle([bx, y + s * 0.95 - s * hgt, bx + bw, y + s * 0.95], fill=g)
    # 光（屋根の右上に小さな4点の星）
    cx, cy, r = x + s * 0.80, y + s * 0.02, s * 0.10
    k = r * 0.22
    d.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k),
               (cx, cy + r), (cx - k, cy + k), (cx - r, cy), (cx - k, cy - k)], fill=g)


def paste_cut(im, key, box, radius=22, border="GOLD"):
    """切り出し画像を box に cover で貼る。"""
    src = Image.open(CUTS[key]).convert("RGBA")
    bw, bh = box[2] - box[0], box[3] - box[1]
    k = max(bw / src.width, bh / src.height)
    src = src.resize((math.ceil(src.width * k), math.ceil(src.height * k)), Image.LANCZOS)
    left = (src.width - bw) // 2
    top = 0 if key.startswith("ooka") or key == "akari_desk" else (src.height - bh) // 4
    src = src.crop((left, top, left + bw, top + bh))
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw, bh], radius, fill=255)
    im.paste(src, box[:2], mask)
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle(box, radius, outline=hexrgb(C[border]), width=4)


def blurred_bg(key, w=W, h=H):
    src = Image.open(CUTS[key]).convert("RGBA")
    k = max(w / src.width, h / src.height)
    src = src.resize((math.ceil(src.width * k), math.ceil(src.height * k)), Image.LANCZOS)
    src = src.crop((0, 0, w, h)).filter(ImageFilter.GaussianBlur(28))
    over = Image.new("RGBA", (w, h), hexrgb(C["NAVY_DEEP"], 170))
    return Image.alpha_composite(src, over).convert("RGB")


def provisional_mark(im):
    d = ImageDraw.Draw(im, "RGBA")
    text(d, (24, 112), PROVISIONAL, 18, "TEXT_MUTED", "sans", "la")


# ---------------------------------------------------------------- キャラクターカット（16:9）
def cut_frame(key, title, name, role, keywords=()):
    im = blurred_bg(key)
    header(im, title)
    d = ImageDraw.Draw(im, "RGBA")
    box = (980, 140, 1860, 840)
    paste_cut(im, key, box)
    # ネームプレート
    d.rounded_rectangle([1000, 730, 1000 + tw(d, name, 40) + 60 + tw(d, role, 24, "sans_medium") + 30, 812], 10,
                        fill=hexrgb(C["NAVY_DEEP"], 235))
    d.rectangle([1000, 730, 1008, 812], fill=hexrgb(C["GOLD"]))
    text(d, (1030, 771), name, 40, "WHITE", "sans_bold", "lm")
    text(d, (1030 + tw(d, name, 40) + 26, 773), role, 24, "BEIGE", "sans_medium", "lm")
    # 左側：キーワード
    y = 260
    for i, kw in enumerate(keywords):
        size = fit_size(d, kw, 64 if i == 0 else 44, 820)
        text(d, (90, y), kw, size, "GOLD" if i == 0 else "WHITE", "sans_black" if i == 0 else "sans_bold")
        y += size + 44
    provisional_mark(im)
    return im


# ---------------------------------------------------------------- 各グラフィック（16:9）
def g_rate_change():
    im = base(); header(im, "何が起きた？", "日本銀行 金融政策決定会合（2026年9月18日）")
    d = ImageDraw.Draw(im, "RGBA")
    text(d, (W / 2, 190), "政策金利（無担保コールレート・オーバーナイト物）の誘導目標", 38, "LIGHT_GRAY", "sans_medium", "ma")
    panel(d, (170, 290, 810, 640), "NAVY_DEEP", 200, "TEXT_MUTED")
    text(d, (490, 335), "これまで", 36, "LIGHT_GRAY", "sans_medium", "ma")
    text(d, (490, 470), "1.0％", 150, "WHITE", "sans_black", "mm")
    text(d, (490, 590), "程度", 40, "LIGHT_GRAY", "sans_medium", "mm")
    # 矢印
    d.polygon([(870, 420), (1010, 420), (1010, 380), (1080, 465), (1010, 550), (1010, 510), (870, 510)], fill=hexrgb(C["GOLD"]))
    panel(d, (1110, 290, 1750, 640), "NAVY_DEEP", 235, "GOLD")
    text(d, (1430, 335), "今回", 36, "GOLD", "sans_bold", "ma")
    text(d, (1430, 470), "1.25％", 150, "GOLD", "sans_black", "mm")
    text(d, (1430, 590), "程度", 40, "BEIGE", "sans_medium", "mm")
    d.rounded_rectangle([760, 690, 1160, 780], 45, fill=hexrgb(C["GOLD"]))
    text(d, (960, 735), "＋0.25ポイント", 46, "NAVY_DEEP", "sans_black", "mm")
    footer_note(im, "出典：日本銀行「金融市場調節方針の変更について」（2026年9月18日）")
    return im


def g_effective_date():
    im = base(); header(im, "何が起きた？", "いつから？")
    d = ImageDraw.Draw(im, "RGBA")
    y = 470
    d.line([(220, y), (1700, y)], fill=hexrgb(C["LIGHT_GRAY"]), width=6)
    for x, date, lab, col in ((420, "9月18日（金）", "金融政策決定会合で決定", "LIGHT_GRAY"),
                              (1400, "9月24日（木）", "新しい金利水準の適用開始", "GOLD")):
        d.ellipse([x - 28, y - 28, x + 28, y + 28], fill=hexrgb(C[col]))
        text(d, (x, y - 70), date, 64, col, "sans_black", "md")
        text(d, (x, y + 70), lab, 40, "WHITE", "sans_bold", "ma")
    d.rounded_rectangle([1250, 640, 1550, 710], 35, outline=hexrgb(C["GOLD"]), width=3)
    text(d, (1400, 675), "9月24日から適用", 34, "GOLD", "sans_bold", "mm")
    footer_note(im, "出典：日本銀行「金融市場調節方針の変更について」（2026年9月18日）")
    return im


def g_not_same():
    im = base(); header(im, "ここを勘違いしない")
    d = ImageDraw.Draw(im, "RGBA")
    panel(d, (120, 170, 860, 470), "NAVY_DEEP", 220, "TEXT_MUTED")
    text(d, (490, 215), "日銀の政策金利", 44, "LIGHT_GRAY", "sans_bold", "ma")
    text(d, (490, 360), "＋0.25pt", 110, "WHITE", "sans_black", "mm")
    text(d, (960, 320), "≠", 150, "GOLD", "sans_black", "mm")
    panel(d, (1060, 170, 1800, 470), "NAVY_DEEP", 235, "GOLD")
    text(d, (1430, 215), "あなたの融資金利", 44, "GOLD", "sans_bold", "ma")
    text(d, (1430, 330), "その日に一律", 48, "WHITE", "sans_bold", "mm")
    text(d, (1430, 405), "＋0.25pt ではない", 48, "WHITE", "sans_bold", "mm")
    text(d, (W / 2, 530), "影響は条件によって違う", 40, "LIGHT_GRAY", "sans_medium", "ma")
    chips = ["金融機関", "商品", "固定か変動か", "金利の見直し条件"]
    widths = [tw(d, c, 42) + 80 for c in chips]
    x = (W - sum(widths) - 30 * 3) / 2
    for c, wv in zip(chips, widths):
        d.rounded_rectangle([x, 600, x + wv, 690], 45, fill=hexrgb(C["BEIGE"]))
        text(d, (x + wv / 2, 645), c, 42, "NAVY_DEEP", "sans_bold", "mm")
        x += wv + 30
    text(d, (W / 2, 770), "見るべきは「自分の借入に、いくら影響するか」", 50, "GOLD", "sans_black", "mm")
    return im


def g_three_numbers(active=None):
    im = base(); header(im, "大家が見るべき3つの数字")
    d = ImageDraw.Draw(im, "RGBA")
    items = [("①", "年間返済額", "いくら増える？"), ("②", "返済比率", "余力は残る？"), ("③", "DSCR", "余裕を持って返せる？")]
    for i, (n, t, s) in enumerate(items):
        x0 = 150 + i * 560
        on = active is None or active == i
        panel(d, (x0, 230, x0 + 500, 720), "NAVY_DEEP", 235 if on else 150, "GOLD" if on else "TEXT_MUTED")
        text(d, (x0 + 250, 330), n, 90, "GOLD" if on else "TEXT_MUTED", "sans_black", "mm")
        text(d, (x0 + 250, 480), t, fit_size(d, t, 76, 440, "sans_black"), "WHITE" if on else "TEXT_MUTED", "sans_black", "mm")
        text(d, (x0 + 250, 610), s, 36, "BEIGE" if on else "TEXT_MUTED", "sans_medium", "mm")
    return im


def bar_chart(d, x0, y0, w, h, rows, vmax, fmt, colors, label_size=40):
    """横棒グラフ rows=[(label, value)]"""
    n = len(rows)
    bh = h / n * 0.62
    for i, (lab, v) in enumerate(rows):
        y = y0 + i * h / n + (h / n - bh) / 2
        text(d, (x0 - 30, y + bh / 2), lab, label_size, "WHITE", "sans_bold", "rm")
        L = w * v / vmax
        d.rounded_rectangle([x0, y, x0 + L, y + bh], 8, fill=hexrgb(C[colors[i]]))
        text(d, (x0 + L + 24, y + bh / 2), fmt(v), label_size + 6, colors[i] if colors[i] != "LIGHT_GRAY" else "WHITE",
             "sans_black", "lm")


def g_annual_payment(sim):
    P, Y = sim["principal_yen"], sim["years"]
    a0, a1 = annual_payment(P, 2.00, Y), annual_payment(P, 2.25, Y)
    im = base(); header(im, "見るべき数字① 年間返済額", "参考シミュレーション")
    d = ImageDraw.Draw(im, "RGBA")
    text(d, (110, 170), f"借入{P // 100_000_000}億円・{Y}年・元利均等返済", 44, "BEIGE", "sans_bold")
    bar_chart(d, 400, 280, 1000, 360, [("金利 2.00％", man(a0)), ("金利 2.25％", man(a1))], 520,
              lambda v: f"約{v}万円／年", ["LIGHT_GRAY", "GOLD"], 44)
    d.rounded_rectangle([1360, 660, 1810, 790], 20, fill=hexrgb(C["GOLD"]))
    text(d, (1585, 700), "0.25pt上昇で", 32, "NAVY_DEEP", "sans_bold", "mm")
    text(d, (1585, 752), f"年間 約＋{man(a1 - a0)}万円", 50, "NAVY_DEEP", "sans_black", "mm")
    text(d, (110, 740), f"毎月返済額：{annual_payment(P, 2.00, Y) // 12:,}円 → {annual_payment(P, 2.25, Y) // 12:,}円", 34, "LIGHT_GRAY", "sans_medium")
    footer_note(im, NOTE)
    return im


def g_scale(sim):
    Y = sim["years"]
    im = base(); header(im, "見るべき数字① 年間返済額", "借入額が大きいほど影響も大きい")
    d = ImageDraw.Draw(im, "RGBA")
    text(d, (110, 170), f"金利 2.00％ → 2.25％ のとき（{Y}年・元利均等）年間返済額の増加", 42, "BEIGE", "sans_bold")
    rows = []
    for oku in (1, 3, 5):
        P = oku * 100_000_000
        rows.append((f"借入 {oku}億円", man(annual_payment(P, 2.25, Y) - annual_payment(P, 2.00, Y))))
    bar_chart(d, 420, 260, 1000, 480, rows, rows[-1][1] * 1.25, lambda v: f"＋約{v}万円／年",
              ["LIGHT_GRAY", "BEIGE", "GOLD"], 44)
    footer_note(im, NOTE)
    return im


def g_repayment_ratio(sim):
    P, Y = sim["principal_yen"], sim["years"]
    rent = 8_000_000
    r0, r1 = annual_payment(P, 2.00, Y) / rent * 100, annual_payment(P, 2.25, Y) / rent * 100
    im = base(); header(im, "見るべき数字② 返済比率")
    d = ImageDraw.Draw(im, "RGBA")
    panel(d, (160, 170, 1760, 380), "NAVY_DEEP", 235, "GOLD")
    text(d, (W / 2, 230), "返済比率", 52, "GOLD", "sans_black", "mm")
    text(d, (W / 2, 320), "＝ 年間返済額 ÷ 年間家賃収入", 64, "WHITE", "sans_black", "mm")
    text(d, (W / 2, 450), "家賃収入が同じまま返済額だけ増えると → 経営の余力は小さくなる", 40, "BEIGE", "sans_bold", "mm")
    text(d, (160, 540), f"例）年間家賃収入 {rent // 10000}万円・借入1億円・30年の場合（仮定の数値）", 34, "LIGHT_GRAY", "sans_medium")
    for i, (lab, v, col) in enumerate((("金利 2.00％", r0, "LIGHT_GRAY"), ("金利 2.25％", r1, "GOLD"))):
        cx = 560 + i * 800
        panel(d, (cx - 300, 600, cx + 300, 790), "NAVY_DEEP", 235, col)
        text(d, (cx, 640), lab, 38, "WHITE", "sans_bold", "mm")
        text(d, (cx, 725), f"{v:.1f}％", 84, col, "sans_black", "mm")
    text(d, (W / 2, 695), "→", 80, "GOLD", "sans_black", "mm")
    footer_note(im, "※仮定の数値による単純試算。実際の物件・融資条件とは異なります。")
    return im


def g_cost_pressure():
    im = base(); header(im, "見るべき数字② 返済比率", "金利だけでは判断できない")
    d = ImageDraw.Draw(im, "RGBA")
    items = ["金利", "修繕費", "人件費", "設備費"]
    x = 170
    for it in items:
        wv = tw(d, it, 56) + 150
        panel(d, (x, 260, x + wv, 400), "NAVY_DEEP", 235, "GOLD")
        text(d, (x + 40, 330), it, 56, "WHITE", "sans_black", "lm")
        text(d, (x + wv - 45, 330), "↑", 64, "GOLD", "sans_black", "mm")
        x += wv + 40
    text(d, (W / 2, 520), "同時に上昇すると…", 48, "BEIGE", "sans_bold", "mm")
    d.rounded_rectangle([460, 600, 1460, 740], 30, fill=hexrgb(C["GOLD"]))
    text(d, (W / 2, 670), "物件に余力はどれだけ残る？", 60, "NAVY_DEEP", "sans_black", "mm")
    return im


def g_dscr():
    im = base(); header(im, "見るべき数字③ DSCR")
    d = ImageDraw.Draw(im, "RGBA")
    text(d, (W / 2, 190), "DSCR（借入償還余裕率）", 48, "GOLD", "sans_black", "ma")
    panel(d, (220, 280, 1700, 470), "NAVY_DEEP", 235, "GOLD")
    text(d, (W / 2, 375), "物件が生む利益（NOI） ÷ 年間の借入返済額", 60, "WHITE", "sans_black", "mm")
    text(d, (W / 2, 520), "＝ 借入返済を、どれだけ余裕を持って支払えるか", 42, "BEIGE", "sans_bold", "mm")
    # 目盛り
    y = 680
    d.rounded_rectangle([320, y - 18, 960, y + 18], 18, fill=hexrgb(C["ALERT_RED"]))
    d.rounded_rectangle([960, y - 18, 1600, y + 18], 18, fill=hexrgb(C["POSITIVE_GREEN"]))
    d.line([(960, y - 50), (960, y + 50)], fill=hexrgb(C["WHITE"]), width=5)
    text(d, (960, y - 62), "1.0", 40, "WHITE", "sans_black", "md")
    text(d, (640, y + 40), "1.0未満：利益で返済をまかなえない", 32, "WHITE", "sans_bold", "ma")
    text(d, (1280, y + 40), "高いほど返済に余裕", 32, "WHITE", "sans_bold", "ma")
    footer_note(im, "NOI＝満室想定ではなく、空室・運営費を差し引いた実際の純収益で考える")
    return im


def g_dscr_stress(sim):
    P, Y = sim["principal_yen"], sim["years"]
    noi = 6_000_000
    im = base(); header(im, "見るべき数字③ DSCR", "金利ストレステスト")
    d = ImageDraw.Draw(im, "RGBA")
    text(d, (110, 170), f"例）NOI {noi // 10000}万円・借入1億円・30年（仮定の数値）", 40, "BEIGE", "sans_bold")
    rows = [(f"金利 {r:.2f}％", noi / annual_payment(P, r, Y)) for r in (2.00, 2.25, 2.50, 3.00)]
    bar_chart(d, 420, 250, 1000, 520, rows, 1.6, lambda v: f"DSCR {v:.2f}", ["LIGHT_GRAY", "GOLD", "BEIGE", "BEIGE"], 40)
    x1 = 420 + 1000 * 1.0 / 1.6
    d.line([(x1, 240), (x1, 780)], fill=hexrgb(C["ALERT_RED"]), width=3)
    text(d, (x1, 790), "1.0", 30, "ALERT_RED", "sans_bold", "ma")
    footer_note(im, "※仮定の数値による単純試算。実際の物件・融資条件とは異なります。")
    return im


def g_ippo_card():
    im = base()
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([0, 0, W, H], fill=hexrgb(C["NAVY_DEEP"], 120))
    panel(d, (160, 120, 1760, 820), "NAVY_DEEP", 245, "GOLD", 30)
    draw_logo_mark(d, 880, 160, 160)
    text(d, (W / 2, 400), "大家の一手", 120, "GOLD", "serif_black", "mm")
    text(d, (W / 2, 505), "現役会社員大家M", 38, "BEIGE", "sans_bold", "mm")
    text(d, (W / 2, 610), "現在金利・＋0.5％・＋1.0％ の3パターンで", 50, "WHITE", "sans_black", "mm")
    text(d, (W / 2, 680), "年間返済額を出してみる", 50, "WHITE", "sans_black", "mm")
    text(d, (W / 2, 770), "金利を予想するより、上がっても耐えられる経営を。", 36, "BEIGE", "sans_bold", "mm")
    return im


def g_ippo_table(sim):
    P, Y = sim["principal_yen"], sim["years"]
    im = base(); header(im, "大家の一手", "3パターン試算の例")
    d = ImageDraw.Draw(im, "RGBA")
    text(d, (110, 170), f"例）借入1億円・30年・現在金利2.00％の場合", 44, "BEIGE", "sans_bold")
    base_a = annual_payment(P, 2.00, Y)
    cols = [("現在金利", 2.00, "LIGHT_GRAY"), ("＋0.5％", 2.50, "BEIGE"), ("＋1.0％", 3.00, "GOLD")]
    for i, (lab, r, col) in enumerate(cols):
        x0 = 150 + i * 560
        a = annual_payment(P, r, Y)
        panel(d, (x0, 260, x0 + 500, 760), "NAVY_DEEP", 235, col)
        text(d, (x0 + 250, 320), lab, 50, col, "sans_black", "mm")
        text(d, (x0 + 250, 390), f"（{r:.2f}％）", 36, "WHITE", "sans_medium", "mm")
        text(d, (x0 + 250, 510), f"約{man(a)}万円", 76, "WHITE", "sans_black", "mm")
        text(d, (x0 + 250, 585), "年間返済額", 32, "LIGHT_GRAY", "sans_medium", "mm")
        if i:
            text(d, (x0 + 250, 680), f"＋約{man(a - base_a)}万円／年", 42, col, "sans_black", "mm")
    footer_note(im, NOTE)
    return im


def g_summary():
    im = base(); header(im, "今日のポイント")
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle([150, 150, 1770, 260], 20, fill=hexrgb(C["GOLD"]))
    text(d, (W / 2, 205), "日銀 政策金利 1.0％程度 → 1.25％程度（9月24日から）", 50, "NAVY_DEEP", "sans_black", "mm")
    text(d, (W / 2, 330), "大家が見るべき数字は3つ", 46, "BEIGE", "sans_bold", "mm")
    for i, (t, s) in enumerate((("年間返済額", "自分の借入でいくら増えるか"), ("返済比率", "経費上昇と合わせて余力を確認"),
                                ("DSCR", "金利ストレスをかけて確認"))):
        y = 410 + i * 140
        panel(d, (250, y, 1670, y + 115), "NAVY_DEEP", 235, "TEXT_MUTED")
        d.ellipse([285, y + 27, 345, y + 87], fill=hexrgb(C["GOLD"]))
        text(d, (315, y + 57), "✓", 38, "NAVY_DEEP", "sans_black", "mm")
        text(d, (380, y + 57), t, 52, "WHITE", "sans_black", "lm")
        text(d, (820, y + 60), s, 38, "LIGHT_GRAY", "sans_bold", "lm")
    return im


def g_lending():
    im = base(); header(im, "今日のポイント", "日銀の見方")
    d = ImageDraw.Draw(im, "RGBA")
    panel(d, (200, 200, 1720, 470), "NAVY_DEEP", 235, "GOLD")
    text(d, (260, 250), "日本銀行の認識（金融環境）", 38, "GOLD", "sans_bold")
    text(d, (W / 2, 380), "金融機関の貸出態度は 引き続き積極的", 64, "WHITE", "sans_black", "mm")
    text(d, (W / 2, 580), "利上げ ＝ 融資が止まる", 60, "LIGHT_GRAY", "sans_black", "mm")
    d.line([(560, 580), (1360, 580)], fill=hexrgb(C["GOLD"]), width=6)
    text(d, (W / 2, 690), "と決めつけるのは早い", 56, "GOLD", "sans_black", "mm")
    footer_note(im, "出典：日本銀行「金融市場調節方針の変更について」（2026年9月18日）")
    return im


def g_ending():
    im = base()
    d = ImageDraw.Draw(im, "RGBA")
    logo = render_logo(1100)
    im.paste(logo, ((W - logo.width) // 2, 150), logo)
    text(d, (W / 2, 640), "不動産ニュースを、大家の経営判断に。", 52, "WHITE", "sans_bold", "mm")
    d.rounded_rectangle([710, 720, 1210, 810], 45, fill=hexrgb(C["GOLD"]))
    text(d, (W / 2, 765), "チャンネル登録", 44, "NAVY_DEEP", "sans_black", "mm")
    return im


# ---------------------------------------------------------------- ロゴ
def render_logo(width=1200, dark_bg=True):
    """「燈の不動産NEWS」＋ AKARI REAL ESTATE NEWS（透過PNG）。"""
    h = int(width * 0.42)
    im = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im, "RGBA")
    s = width / 1200
    main = "WHITE" if dark_bg else "NAVY"
    text(d, (40 * s, 250 * s), "燈", int(260 * s), "GOLD", "serif_black", "ls")
    text(d, (320 * s, 250 * s), "の", int(100 * s), "GOLD", "serif_bold", "ls")
    draw_logo_mark(d, 470 * s, 40 * s, 220 * s)
    text(d, (40 * s, 400 * s), "不動産NEWS", int(150 * s), main, "serif_bold", "ls")
    text(d, (48 * s, 470 * s), "A K A R I   R E A L   E S T A T E   N E W S", int(34 * s), main, "sans_medium", "ls")
    bbox = im.getbbox()
    return im.crop((0, 0, max(bbox[2] + int(20 * s), width // 2), bbox[3] + int(10 * s)))


def render_brand_assets():
    out = BRAND / "logo"
    out.mkdir(parents=True, exist_ok=True)
    render_logo(1200).save(out / "logo_main_on_dark.png")
    render_logo(1200, dark_bg=False).save(out / "logo_main_on_light.png")
    # アイコン（サブロゴ）
    ic = Image.new("RGBA", (800, 800), (0, 0, 0, 0))
    d = ImageDraw.Draw(ic, "RGBA")
    d.ellipse([0, 0, 799, 799], fill=hexrgb(C["NAVY"]))
    d.ellipse([22, 22, 777, 777], outline=hexrgb(C["GOLD"]), width=10)
    draw_logo_mark(d, 200, 170, 400)
    ic.save(out / "icon_800.png")
    # YouTubeバナー 2560x1440（全デバイス共通のセーフエリア 1546x423 に要素を収める）
    bw, bh = 2560, 1440
    bn = base(bw, bh)
    bg = blurred_bg("akari_desk", bw, bh)
    bn = Image.blend(bn, bg, 0.45)
    d = ImageDraw.Draw(bn, "RGBA")
    sx, sy = (bw - 1546) // 2, (bh - 423) // 2
    logo = render_logo(720)
    bn.paste(logo, (sx + 20, sy + (423 - logo.height) // 2 - 30), logo)
    text(d, (sx + 800, sy + 150), "不動産ニュースを、", 64, "WHITE", "sans_black", "la")
    text(d, (sx + 800, sy + 235), "大家の経営判断に。", 64, "GOLD", "sans_black", "la")
    text(d, (sx + 800, sy + 330), "金利・融資・家賃・地価・修繕・制度改正", 32, "BEIGE", "sans_bold", "la")
    bn.convert("RGB").save(out / "youtube_banner_2560x1440_draft.png")
    guide = bn.copy()
    ImageDraw.Draw(guide, "RGBA").rectangle([sx, sy, sx + 1546, sy + 423], outline=(255, 0, 0, 255), width=4)
    guide.convert("RGB").resize((1280, 720)).save(out / "youtube_banner_safearea_guide.png")
    print("wrote", out)


# ---------------------------------------------------------------- 縦型（Shorts 1080x1920）
VW, VH = 1080, 1920


def vbase(title, cut_key, speaker_name):
    im = base(VW, VH)
    header(im, title)
    paste_cut(im, cut_key, (90, 150, 990, 820))
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle([110, 740, 110 + tw(d, speaker_name, 40) + 60, 805], 10, fill=hexrgb(C["NAVY_DEEP"], 235))
    d.rectangle([110, 740, 117, 805], fill=hexrgb(C["GOLD"]))
    text(d, (140, 773), speaker_name, 40, "WHITE", "sans_bold", "lm")
    provisional_mark(im)
    return im, d


def v_frames(sim):
    P, Y = sim["principal_yen"], sim["years"]
    a0, a1 = annual_payment(P, 2.00, Y), annual_payment(P, 2.25, Y)
    out = {}
    im, d = vbase("日銀 利上げ", "akari_front", "燈")
    text(d, (VW / 2, 950), "政策金利", 60, "LIGHT_GRAY", "sans_bold", "mm")
    text(d, (VW / 2, 1090), "1.0％ → 1.25％", 110, "GOLD", "sans_black", "mm")
    text(d, (VW / 2, 1210), "（程度）9月24日から適用", 44, "WHITE", "sans_bold", "mm")
    out["V01_hook"] = im
    im, d = vbase("大家が見るべき数字", "akari_front", "燈")
    for i, t in enumerate(("① 年間返済額", "② 返済比率", "③ DSCR")):
        panel(d, (140, 900 + i * 150, 940, 1020 + i * 150), "NAVY_DEEP", 235, "GOLD")
        text(d, (VW / 2, 960 + i * 150), t, 64, "WHITE", "sans_black", "mm")
    out["V02_three"] = im
    im, d = vbase("① 年間返済額", "akari_front", "燈")
    text(d, (VW / 2, 910), "1億円・30年・元利均等", 44, "BEIGE", "sans_bold", "mm")
    text(d, (VW / 2, 1010), f"2.00％：約{man(a0)}万円／年", 60, "WHITE", "sans_black", "mm")
    text(d, (VW / 2, 1100), f"2.25％：約{man(a1)}万円／年", 60, "GOLD", "sans_black", "mm")
    d.rounded_rectangle([200, 1160, 880, 1250], 45, fill=hexrgb(C["GOLD"]))
    text(d, (VW / 2, 1205), f"年間 約＋{man(a1 - a0)}万円", 56, "NAVY_DEEP", "sans_black", "mm")
    text(d, (VW / 2, 1290), NOTE, 26, "TEXT_MUTED", "sans", "mm")
    out["V03_payment"] = im
    im, d = vbase("② 返済比率 ③ DSCR", "akari_front", "燈")
    text(d, (VW / 2, 950), "金利がさらに上がっても", 56, "WHITE", "sans_black", "mm")
    text(d, (VW / 2, 1040), "返済できる？", 72, "GOLD", "sans_black", "mm")
    text(d, (VW / 2, 1150), "返済比率 ・ DSCR で確認", 52, "BEIGE", "sans_bold", "mm")
    out["V04_ratio_dscr"] = im
    im, d = vbase("大家の一手", "ooka_m", "現役会社員大家M")
    text(d, (VW / 2, 920), "大家の一手", 90, "GOLD", "serif_black", "mm")
    for i, t in enumerate(("現在金利", "＋0.5％", "＋1.0％")):
        x = 150 + i * 270
        panel(d, (x, 1000, x + 240, 1100), "NAVY_DEEP", 235, "GOLD")
        text(d, (x + 120, 1050), t, 42, "WHITE", "sans_black", "mm")
    text(d, (VW / 2, 1170), "の3パターンで年間返済額を出す", 46, "WHITE", "sans_bold", "mm")
    out["V05_ippo"] = im
    im = base(VW, VH)
    d = ImageDraw.Draw(im, "RGBA")
    logo = render_logo(900)
    im.paste(logo, ((VW - logo.width) // 2, 500), logo)
    text(d, (VW / 2, 1000), "詳しくは本編で", 70, "WHITE", "sans_black", "mm")
    d.rounded_rectangle([290, 1100, 790, 1200], 50, fill=hexrgb(C["GOLD"]))
    text(d, (VW / 2, 1150), "チャンネル登録", 48, "NAVY_DEEP", "sans_black", "mm")
    out["V06_cta"] = im
    return out


# ---------------------------------------------------------------- エピソード
SCENE_KEYWORDS = {
    "S01": ["日銀 利上げ", "大家への影響は？"],
    "S03": ["ここを勘違いしない", "政策金利 ≠ 自分の融資金利"],
    "S04": ["大切なのは", "自分の年間返済額が", "いくら増えるか"],
    "S05": ["金利上昇 ＋ 経費上昇", "物件の余力を確認"],
    "S07": ["現役会社員大家Mは", "どう見る？"],
    "S09": ["今日のポイント"],
    "S10": ["燈の不動産ニュース", "大家の経営目線で"],
}


def render_episode(ep_id):
    d = episode_dir(ep_id)
    ep = load_json(d / "script" / f"{ep_id}.json")
    sim = ep["simulation"]
    g = d / "graphics"
    g.mkdir(exist_ok=True)
    gf = {
        "G02_rate_change": g_rate_change, "G03_effective_date": g_effective_date, "G04_not_same": g_not_same,
        "G05_three_numbers": g_three_numbers, "G06_annual_payment": lambda: g_annual_payment(sim),
        "G06b_scale": lambda: g_scale(sim), "G07_repayment_ratio": lambda: g_repayment_ratio(sim),
        "G07b_cost_pressure": g_cost_pressure, "G08_dscr": g_dscr, "G08b_dscr_stress": lambda: g_dscr_stress(sim),
        "G09_ippo_card": g_ippo_card, "G09b_ippo_table": lambda: g_ippo_table(sim), "G10_summary": g_summary,
        "G10b_lending": g_lending, "G11_ending": g_ending,
    }
    for k, fn in gf.items():
        fn().convert("RGB").save(g / f"{ep_id}_{k}.png")
    # キャラクターカット（シーンごとにキーワードを変える）
    done = set()
    for sc in ep["scenes"]:
        for s in sc["shots"]:
            v = s["visual"]
            if v.startswith("talk:"):  # 話しているカットの素材待ち用フォールバック
                v = ep.get("talk_cuts", {}).get(v[5:], {}).get("fallback", "cut:akari_front")
            if not v.startswith("cut:"):
                continue
            key = v[4:]
            fn = g / f"{ep_id}_{sc['id']}_{key}.png"
            if fn in done:
                continue
            done.add(fn)
            if key.startswith("akari"):
                img = cut_frame(key, sc["title"], "燈", "不動産ニュース専門AIキャスター", SCENE_KEYWORDS.get(sc["id"], [sc["title"]]))
            else:
                img = cut_frame(key, sc["title"], "現役会社員大家M", "会社員・不動産投資家", SCENE_KEYWORDS.get(sc["id"], [sc["title"]]))
            img.convert("RGB").save(fn)
    # Shorts の話しているカット：素材待ち用の縦型フォールバック
    for s in ep.get("shorts", {}).get("shots", []):
        if not s["visual"].startswith("talk:"):
            continue
        key = ep.get("talk_cuts", {}).get(s["visual"][5:], {}).get("fallback", "cut:akari_front")[4:]
        name = "燈" if key.startswith("akari") else "現役会社員大家M"
        im, _ = vbase("燈の不動産ニュース", key, name)
        im.convert("RGB").save(g / f"{ep_id}_SHORTS_{key}.png")
    for k, im in v_frames(sim).items():
        im.convert("RGB").save(g / f"{ep_id}_{k}.png")
    print("wrote", g)


def visual_path(ep_id, scene_id, visual):
    g = episode_dir(ep_id) / "graphics"
    kind, key = visual.split(":", 1)
    if kind == "cut":
        return g / f"{ep_id}_{scene_id}_{key}.png"
    return g / f"{ep_id}_{key}.png"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--logo", action="store_true")
    a = ap.parse_args(argv)
    if a.logo:
        render_brand_assets()
    if a.episode:
        render_episode(a.episode)


if __name__ == "__main__":
    main()
