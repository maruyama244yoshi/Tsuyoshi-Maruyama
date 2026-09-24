"""燈／大家M の画像生成プロンプトを定義ファイルから組み立てる。

コード内にプロンプト本文を書かない。必ず brand/<char>/prompts/*.txt を読む。
組み立て順（AKARI_MASTER §12 固定）:
  IDENTITY + OUTFIT + FACE + CAMERA + STUDIO + LIGHTING + news theme  / negative は分離

例:
  python3 -m tools.akari_news.prompt_builder --outfit AKARI_OUTFIT_01 --face AKARI_FACE_02 \
      --camera AKARI_CAMERA_04 --theme "large screen displaying a Bank of Japan interest-rate chart"
  python3 -m tools.akari_news.prompt_builder --test-set      # 標準テストセット8件
"""
import argparse
import json
import sys

from .common import AKARI, OOKA_M

CHAR = {
    "akari": dict(dir=AKARI / "prompts", identity="AKARI_IDENTITY_MASTER", studio="AKARI_STUDIO_01",
                  lighting="AKARI_LIGHTING", negative="AKARI_NEGATIVE", no_text="AKARI_RULE_NO_TEXT"),
    "ooka_m": dict(dir=OOKA_M / "prompts", identity="OOKA_M_IDENTITY_MASTER", studio=None,
                   lighting=None, negative="OOKA_M_NEGATIVE", no_text=None),
}

TEST_SET = [
    ("T1", "AKARI_OUTFIT_01", "AKARI_FACE_01", "AKARI_CAMERA_01", False, "16:9"),
    ("T2", "AKARI_OUTFIT_01", "AKARI_FACE_02", "AKARI_CAMERA_01", False, "16:9"),
    ("T3", "AKARI_OUTFIT_01", "AKARI_FACE_03", "AKARI_CAMERA_01", False, "16:9"),
    ("T4", "AKARI_OUTFIT_02", "AKARI_FACE_01", "AKARI_CAMERA_02", False, "16:9"),
    ("T5", "AKARI_OUTFIT_03", "AKARI_FACE_02", "AKARI_CAMERA_04", False, "16:9"),
    ("T6", "AKARI_OUTFIT_01", "AKARI_FACE_01", "AKARI_CAMERA_03", False, "16:9"),
    ("T7", "AKARI_OUTFIT_01", "AKARI_FACE_02", "AKARI_CAMERA_05", True, "16:9"),
    ("T8", "AKARI_OUTFIT_04", "AKARI_FACE_01", "AKARI_CAMERA_01", False, "9:16"),
]


def read(d, name):
    p = d / f"{name}.txt"
    if not p.exists():
        raise SystemExit(f"定義ファイルがありません: {p}")
    return " ".join(p.read_text(encoding="utf-8").split())


def build(char="akari", outfit=None, face=None, camera=None, theme=None, no_text=False, studio=True):
    c = CHAR[char]
    d = c["dir"]
    parts = [read(d, c["identity"])]
    for name in (outfit, face, camera):
        if name:
            parts.append(read(d, name))
    if studio and c["studio"]:
        parts.append(read(d, c["studio"]))
    if c["lighting"]:
        parts.append(read(d, c["lighting"]))
    if theme:
        parts.append(theme.strip())
    neg = (d / f"{c['negative']}.txt").read_text(encoding="utf-8").strip().splitlines()
    if no_text and c["no_text"]:
        parts.append(read(d, c["no_text"]))
    return {"char": char, "outfit": outfit, "face": face, "camera": camera, "theme": theme,
            "prompt": "\n\n".join(parts), "negative_prompt": " ".join(neg)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--char", default="akari", choices=CHAR)
    ap.add_argument("--outfit"); ap.add_argument("--face"); ap.add_argument("--camera")
    ap.add_argument("--theme")
    ap.add_argument("--no-text", action="store_true", help="サムネ等：画像内に文字を描かせない")
    ap.add_argument("--single", action="store_true", help="negative欄のないツール用に1本へ連結")
    ap.add_argument("--test-set", action="store_true")
    a = ap.parse_args(argv)
    if a.test_set:
        out = []
        for tid, o, f, cam, nt, ar in TEST_SET:
            r = build("akari", o, f, cam, None, nt)
            r.update(test_id=tid, aspect_ratio=ar, reference_image="brand/akari/references/cuts/AKARI_REF001_CAM01_front.png")
            out.append(r)
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        return
    r = build(a.char, a.outfit, a.face, a.camera, a.theme, a.no_text)
    if a.single:
        print(r["prompt"] + "\n\nConstraints: " + r["negative_prompt"])
    else:
        json.dump(r, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
