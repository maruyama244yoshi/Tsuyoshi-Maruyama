"""テスト／本番音声の受け入れ：48kHz WAV への統一と品質レポート。

  python3 -m tools.akari_news.audio_prep IN.wav [IN2.wav ...] [--out-dir DIR]

- 入力は WAV（または FLAC）のみ。MP3 など非可逆形式は拒否する（MP3 経由の WAV 化は禁止）。
- 44.1kHz などは soxr（高品質リサンプラ）で 48kHz / 24bit に変換。音量は変えない。
- レポート：元のサンプルレート・長さ・ピーク・ラウドネス（LUFS）・先頭/末尾の無音。
  音量はテスト比較では揃えない（ツール本来の出力を聴くため）。本編では timeline.py が揃える。
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from .video import ffmpeg

LOSSLESS = {".wav", ".flac"}
# HeyGen のアバター動画（mp4）の音声トラックは原本そのもの（2026-09-26 形式ルール）。音声だけを1回デコードして使う
AVATAR_VIDEO = {".mp4"}


def probe(path):
    err = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    sr = re.search(r"(\d+) Hz", err)
    codec = re.search(r"Audio: (\w+)", err)
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return {"sample_rate": int(sr[1]) if sr else None, "codec": codec[1] if codec else None,
            "duration": (int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3])) if dur else None}


def loudness(path):
    err = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
    return {"integrated_lufs": float(i[-1]) if i else None, "true_peak_dbfs": float(tp[-1]) if tp else None}


def silence_edges(path, thresh_db=-45):
    err = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af",
                          f"silencedetect=noise={thresh_db}dB:d=0.05", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    lead = ends[0] if starts and starts[0] <= 0.01 and ends else 0.0
    return {"leading_silence": round(lead, 3), "silence_segments": len(starts)}


def convert(src: Path, out_dir: Path):
    if src.suffix.lower() not in LOSSLESS | AVATAR_VIDEO:
        raise SystemExit(f"拒否：{src.name} は非可逆形式です。ElevenLabs から WAV（PCM）で書き出し直してください。")
    before = probe(src)
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / (src.stem + ".wav")
    if dst.resolve() == src.resolve():
        dst = out_dir / (src.stem + "_48k.wav")
    subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-map", "0:a:0", "-vn",
                    "-af", "aresample=resampler=soxr:precision=28:dither_method=triangular", "-ar", "48000",
                    "-c:a", "pcm_s24le", str(dst)], check=True)
    rep = {"file": dst.name, "source": src.name, "source_sample_rate": before["sample_rate"],
           "source_codec": before["codec"], "duration": before["duration"], **loudness(dst), **silence_edges(dst)}
    after = probe(dst)
    rep["out_sample_rate"], rep["out_codec"] = after["sample_rate"], after["codec"]
    warn = []
    if rep["true_peak_dbfs"] is not None and rep["true_peak_dbfs"] > -1.0:
        warn.append("ピークが -1dBFS を超えている（音割れの恐れ）")
    if rep["integrated_lufs"] is not None and not (-26 <= rep["integrated_lufs"] <= -14):
        warn.append("ラウドネスが通常範囲（-26〜-14 LUFS）外")
    rep["warnings"] = warn
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out-dir", help="出力先（省略時は入力と同じ場所の 48k/）")
    a = ap.parse_args(argv)
    reps = []
    for p in map(Path, a.inputs):
        out = Path(a.out_dir) if a.out_dir else p.parent / "48k"
        reps.append(convert(p, out))
    print(json.dumps(reps, ensure_ascii=False, indent=2))
    (Path(a.out_dir) if a.out_dir else Path(a.inputs[0]).parent / "48k").joinpath("audio_report.json").write_text(
        json.dumps(reps, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
