"""HeyGen と Hedra のテスト動画を同条件で比べるための検査と並列比較動画。

  python3 -m tools.akari_news.compare_video akari
  python3 -m tools.akari_news.compare_video ooka_m
  python3 -m tools.akari_news.compare_video akari --vertical

入力：avatar_tests/video_test/heygen/heygen_<char>[_vertical].mp4 と hedra/hedra_<char>[_vertical].mp4
出力：avatar_tests/review/compare_<char>[_vertical].mp4（左右に並べ、音声は左＝HeyGen）
      avatar_tests/review/compare_<char>[_vertical].json（同条件チェックの結果）

同条件チェック（指示書 §21）：
  - 尺の差が 0.3 秒以内
  - 音声が同じ（音量の包絡線の相関が 0.9 以上。ツールごとに声を変えていないか）
  - 解像度・フレームレートの記録
字幕・BGM は付けない（純粋なキャスター品質を見るため）。
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .common import YT
from .graphics import C, hexrgb, text
from .video import ffmpeg, media_duration

BASE = YT / "avatar_tests"


def video_info(p):
    import re
    err = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(p)], capture_output=True, text=True).stderr
    v = re.search(r"Video: .*?, (\d{2,5})x(\d{2,5}).*?, ([\d.]+) fps", err)
    return {"file": p.name, "duration": round(media_duration(p), 3),
            "width": int(v[1]) if v else None, "height": int(v[2]) if v else None, "fps": float(v[3]) if v else None,
            "has_audio": "Audio:" in err}


def envelope(p, sr=16000, hop=0.02):
    raw = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = int(sr * hop)
    x = x[: len(x) // n * n].reshape(-1, n)
    return np.sqrt((x ** 2).mean(axis=1))


def audio_similarity(a, b):
    ea, eb = envelope(a), envelope(b)
    best = -1.0
    for lag in range(-25, 26):  # ±0.5秒のずれまで許容して最大相関
        x, y = (ea[lag:], eb) if lag >= 0 else (ea, eb[-lag:])
        m = min(len(x), len(y))
        if m < 20:
            continue
        c = np.corrcoef(x[:m], y[:m])[0, 1]
        best = max(best, float(c))
    return round(best, 3)


def label_png(w, h, left, right, path):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x, s in ((0, left), (w // 2, right)):
        d.rounded_rectangle([x + 20, 20, x + 40 + len(s) * 22, 70], 8, fill=hexrgb(C["NAVY_DEEP"], 220))
        text(d, (x + 30, 45), s, 30, "WHITE", "sans_bold", "lm")
    im.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("character", choices=["akari", "ooka_m"])
    ap.add_argument("--vertical", action="store_true")
    a = ap.parse_args(argv)
    suf = "_vertical" if a.vertical else ""
    hg = BASE / "video_test" / "heygen" / f"heygen_{a.character}{suf}.mp4"
    hd = BASE / "video_test" / "hedra" / f"hedra_{a.character}{suf}.mp4"
    missing = [str(p.relative_to(BASE)) for p in (hg, hd) if not p.exists()]
    if missing:
        raise SystemExit("未着：" + ", ".join(missing))
    info = {"heygen": video_info(hg), "hedra": video_info(hd)}
    checks = {"duration_diff": round(abs(info["heygen"]["duration"] - info["hedra"]["duration"]), 3),
              "audio_similarity": audio_similarity(hg, hd)}
    checks["same_duration"] = checks["duration_diff"] <= 0.3
    checks["same_audio"] = checks["audio_similarity"] >= 0.9
    out_dir = BASE / "review"
    out_dir.mkdir(exist_ok=True)
    # 並列比較：各 960x540（縦型は 540x960）に揃えて左右に並べる
    cw, ch = (540, 960) if a.vertical else (960, 540)
    lab = out_dir / "_labels.png"
    label_png(cw * 2, ch, "A: HeyGen", "B: Hedra", lab)
    out = out_dir / f"compare_{a.character}{suf}.mp4"
    fc = (f"[0:v]scale={cw}:{ch}:force_original_aspect_ratio=decrease,pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[l];"
          f"[1:v]scale={cw}:{ch}:force_original_aspect_ratio=decrease,pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[r];"
          f"[l][r]hstack=inputs=2[s];[s][2:v]overlay=0:0[v]")
    subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(hg), "-i", str(hd), "-i", str(lab),
                    "-filter_complex", fc, "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    lab.unlink()
    rep = {"character": a.character, "vertical": a.vertical, "videos": info, "checks": checks, "compare_video": out.name}
    (out_dir / f"compare_{a.character}{suf}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    if not (checks["same_duration"] and checks["same_audio"]):
        print("注意：同条件になっていない可能性があります（尺または音声が違う）。採点前に確認してください。")


if __name__ == "__main__":
    main()
