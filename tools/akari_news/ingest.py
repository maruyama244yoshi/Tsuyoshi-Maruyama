"""HeyGen から届いたファイルを検査して、所定の場所に配置する。

  python3 -m tools.akari_news.ingest episode_001 <受け取ったフォルダ>
  python3 -m tools.akari_news.ingest episode_001 <フォルダ> --dry-run   # 検査だけ

受け取るもの（ファイル名は制作シートの id と完全一致）：
  heygen_akari.mp4 / heygen_ooka_m.mp4          → avatar_tests/video_test/heygen/
  AKARI_001〜018.mp4 / M_001〜006.mp4            → episode/clips/
  AKARI_VO_001〜018 / M_VO_001〜002（.wav/.mp4） → episode/voice/final/（.wav は48kHz/24bitに統一）

検査：名前の過不足、音声の有無、解像度（16:9 は 1080p 以上、縦型は 1080x1920 以上）、縦横比、
尺の目安とのずれ（仮音声の尺の 0.5〜2.0 倍）、MP3 の拒否（MP3 経由は禁止）。
"""
import argparse
import csv
import json
import shutil
from pathlib import Path

from .audio_prep import convert
from .common import YT, episode_dir, load_json
from .compare_video import video_info


def expected(ep_id):
    d = episode_dir(ep_id)
    ver = load_json(d / "script" / f"{ep_id}.json").get("script_version", "v1")
    prod = d / "production"
    clips = list(csv.DictReader(open(prod / f"clip_manifest_{ver}.csv", encoding="utf-8-sig")))
    voices = [v for v in csv.DictReader(open(prod / f"voice_manifest_{ver}.csv", encoding="utf-8-sig"))
              if "_VO_" in v["id"]]
    return d, clips, voices


def check_video(p, aspect, est=None):
    info = video_info(p)
    probs = []
    if not info["has_audio"]:
        probs.append("音声なし")
    w, h = info["width"] or 0, info["height"] or 0
    if aspect == "9:16":
        if w > h:
            probs.append(f"縦型のはずが横長（{w}x{h}）")
        if min(w, h) < 1080:
            probs.append(f"解像度不足（{w}x{h}、1080x1920以上）")
    else:
        if h > w:
            probs.append(f"横長のはずが縦型（{w}x{h}）")
        if h < 1080:
            probs.append(f"解像度不足（{w}x{h}、1920x1080以上）")
        if w and h and abs(w / h - 16 / 9) > 0.02:
            probs.append(f"16:9ではない（{w}x{h}）")
    if est and info["duration"] and not (0.5 * est <= info["duration"] <= 2.0 * est + 1.0):
        probs.append(f"尺が目安と大きく違う（{info['duration']:.1f}秒／目安{est:.1f}秒）→ 文章違いの可能性")
    return info, probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("src")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    src = Path(a.src)
    files = {p.stem: p for p in src.rglob("*") if p.is_file()}
    d, clips, voices = expected(a.episode)
    report = {"ok": [], "problems": [], "missing": [], "unexpected": []}

    def place(p, dst_dir, name):
        if a.dry_run:
            return
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst_dir / f"{name}{p.suffix.lower()}")

    # テスト動画
    for name in ("heygen_akari", "heygen_ooka_m"):
        p = files.pop(name, None)
        if p is None:
            report["missing"].append(name)
            continue
        info, probs = check_video(p, "16:9")
        (report["problems"] if probs else report["ok"]).append({"id": name, "info": info, "problems": probs})
        place(p, YT / "avatar_tests" / "video_test" / "heygen", name)
    # 話しているカット
    for c in clips:
        p = files.pop(c["id"], None)
        if p is None:
            report["missing"].append(c["id"])
            continue
        if p.suffix.lower() != ".mp4":
            report["problems"].append({"id": c["id"], "problems": [f"mp4 ではない（{p.suffix}）"]})
            continue
        info, probs = check_video(p, c["aspect"], float(c["est_sec"] or 0))
        (report["problems"] if probs else report["ok"]).append({"id": c["id"], "info": info, "problems": probs})
        place(p, d / "clips", c["id"])
    # 声だけのパート
    for v in voices:
        p = files.pop(v["id"], None)
        if p is None:
            report["missing"].append(v["id"])
            continue
        ext = p.suffix.lower()
        if ext == ".mp3":
            report["problems"].append({"id": v["id"], "problems": ["MP3 は受け付けない（WAV か mp4 で）"]})
            continue
        if ext in (".wav", ".flac"):
            if not a.dry_run:
                rep = convert(p, d / "voice" / "final")
                report["ok"].append({"id": v["id"], "audio": rep})
            else:
                report["ok"].append({"id": v["id"]})
        elif ext == ".mp4":
            info = video_info(p)
            if not info["has_audio"]:
                report["problems"].append({"id": v["id"], "problems": ["音声なし"]})
                continue
            report["ok"].append({"id": v["id"], "info": info})
            place(p, d / "voice" / "final", v["id"])
        else:
            report["problems"].append({"id": v["id"], "problems": [f"未対応の形式（{ext}）"]})
    report["unexpected"] = sorted(files)
    out = d / "review" / "ingest_report.json"
    if not a.dry_run:
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {len(report['ok'])} / 問題 {len(report['problems'])} / 未着 {len(report['missing'])} / 想定外 {len(report['unexpected'])}")
    for x in report["problems"]:
        print("問題", x["id"], "：", "、".join(x["problems"]))
    if report["missing"]:
        print("未着：", " ".join(report["missing"]))
    if report["unexpected"]:
        print("想定外のファイル名：", " ".join(report["unexpected"]))


if __name__ == "__main__":
    main()
