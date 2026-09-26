"""受け取った素材（話している動画・声だけの音声）を機械的に検査する。

  python3 -m tools.akari_news.qa_assets episode_001 [--inbox DIR]

検査：欠損・破損（全フレームをデコードしてエラー検出）・解像度・フレームレート・縦横比・尺・
サンプリングレート・ビット深度・ラウドネス・無音区間・クリッピング（ピーク）・映像と音声の尺の差（音ズレの目安）・
文字数に対する話速（原稿違い・途切れの目安）。
発音・口パク・目線・表情は機械では判定できないため、代表フレームの一覧画像を作り、人間の確認項目として残す。
出力：review/asset_qa.json、review/asset_contact_sheet.png
"""
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

from .common import episode_dir, load_json
from .video import ffmpeg


def run(args):
    return subprocess.run([ffmpeg(), "-hide_banner", *args], capture_output=True, text=True).stderr


def probe(p):
    err = run(["-i", str(p)])
    info = {}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    info["duration"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else None
    v = re.search(r"Stream #\S+: Video: (\w+).*?, (\d{2,5})x(\d{2,5})[, \[].*?([\d.]+) fps", err)
    if v:
        info.update(vcodec=v[1], width=int(v[2]), height=int(v[3]), fps=float(v[4]))
    a = re.search(r"Stream #\S+: Audio: (\w+).*?, (\d+) Hz, (\w+)", err)
    if a:
        info.update(acodec=a[1], sample_rate=int(a[2]), channels=a[3])
        bits = {"pcm_s16le": 16, "pcm_s24le": 24, "pcm_s32le": 32, "pcm_f32le": 32}.get(a[1])
        if bits:
            info["bit_depth"] = bits
    return info


def decode_check(p, stream):
    """全体をデコードしてエラーと実尺を得る。"""
    err = run(["-v", "error", "-stats", "-i", str(p), "-map", f"0:{stream}", "-f", "null", "-"])
    errors = [ln for ln in err.splitlines() if ln and not ln.startswith(("frame=", "size=")) and "time=" not in ln]
    t = re.findall(r"time=(\d+):(\d+):([\d.]+)", err)
    dur = int(t[-1][0]) * 3600 + int(t[-1][1]) * 60 + float(t[-1][2]) if t else None
    fr = re.findall(r"frame=\s*(\d+)", err)
    return {"errors": errors[:5], "decoded_sec": dur, "frames": int(fr[-1]) if fr else None}


def audio_stats(p):
    err = run(["-nostats", "-i", str(p), "-map", "0:a", "-af",
               "ebur128=peak=true,silencedetect=noise=-50dB:d=0.8,astats=metadata=0:reset=0", "-f", "null", "-"])
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    tp = re.findall(r"Peak:\s+(-?[\d.inf]+) dBFS", err)
    sil = [(float(a), float(b)) for a, b in zip(re.findall(r"silence_start: (-?[\d.]+)", err),
                                               re.findall(r"silence_end: ([\d.]+)", err))]
    clip = re.findall(r"Number of samples clipped: (\d+)", err) or re.findall(r"Peak count: (\d+)", err)
    peak = re.findall(r"Peak level dB: (-?[\d.inf]+)", err)
    return {"lufs": float(i[-1]) if i else None, "true_peak": float(tp[-1]) if tp and tp[-1] != "-inf" else None,
            "sample_peak_db": float(peak[-1]) if peak and "inf" not in peak[-1] else None,
            "long_silences": [(round(a, 2), round(b, 2)) for a, b in sil]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--inbox")
    a = ap.parse_args(argv)
    d = episode_dir(a.episode)
    inbox = Path(a.inbox) if a.inbox else d / "inbox"
    ver = load_json(d / "script" / f"{a.episode}.json").get("script_version", "v1")
    rows = {r["id"]: r for r in csv.DictReader(open(d / "production" / f"voice_manifest_{ver}.csv", encoding="utf-8-sig"))}
    clips = {r["id"]: r for r in csv.DictReader(open(d / "production" / f"clip_manifest_{ver}.csv", encoding="utf-8-sig"))}
    results = []
    for rid, r in rows.items():
        is_vo = "_VO_" in rid
        p = inbox / (f"{rid}.wav" if is_vo else f"{rid}.mp4")
        res = {"id": rid, "file": p.name, "kind": "voiceover" if is_vo else "talking", "speaker": r["speaker"],
               "text": r["text"], "exists": p.exists()}
        if not p.exists():
            res["issues"] = ["欠損"]
            results.append(res)
            continue
        res["size_mb"] = round(p.stat().st_size / 1e6, 2)
        res.update(probe(p))
        issues, notes = [], []
        if not is_vo:
            vd = decode_check(p, "v")
            res["video_decode"] = vd
            if vd["errors"]:
                issues.append("映像デコードエラー")
            aspect = clips.get(rid, {}).get("aspect", "16:9")
            res["expected_aspect"] = aspect
            w, h = res.get("width", 0), res.get("height", 0)
            if aspect == "9:16" and not (h > w and w >= 1080):
                issues.append(f"縦型1080x1920以上でない（{w}x{h}）")
            if aspect == "16:9" and not (w > h and h >= 1080):
                issues.append(f"横長1080p以上でない（{w}x{h}）")
        if "sample_rate" not in res:
            issues.append("音声なし")
        else:
            ad = decode_check(p, "a")
            res["audio_decode"] = ad
            if ad["errors"]:
                issues.append("音声デコードエラー")
            st = audio_stats(p)
            res.update(st)
            if st["lufs"] is not None and st["lufs"] < -35:
                issues.append(f"音量が極端に小さい（{st['lufs']} LUFS）")
            if st["true_peak"] is not None and st["true_peak"] > -0.1:
                issues.append(f"クリッピングの疑い（True Peak {st['true_peak']} dBFS）")
            if st["long_silences"]:
                inner = [s for s in st["long_silences"] if s[0] > 0.3 and (res["duration"] or 0) - s[1] > 0.3]
                if inner:
                    notes.append(f"途中に0.8秒以上の無音 {inner}")
            if not is_vo and res.get("video_decode", {}).get("decoded_sec") and ad["decoded_sec"]:
                diff = abs(res["video_decode"]["decoded_sec"] - ad["decoded_sec"])
                res["av_duration_diff"] = round(diff, 3)
                if diff > 0.2:
                    issues.append(f"映像と音声の長さが{diff:.2f}秒ずれている（音ズレの疑い）")
        # 話速（文字数/秒）で原稿違い・途切れを検出
        chars = len(re.sub(r"[、。，．・\s「」？！]", "", r["text"]))
        if res.get("duration"):
            cps = chars / res["duration"]
            res["chars_per_sec"] = round(cps, 2)
            if cps < 3.0 or cps > 11.0:
                issues.append(f"話速が不自然（{cps:.1f}文字/秒）→ 原稿違い・途切れ・余計な無音の可能性")
        res["issues"], res["notes"] = issues, notes
        results.append(res)
    out = d / "review" / "asset_qa.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in results if r.get("exists") and not r["issues"])
    print(f"検査 {len(results)} 本：問題なし {ok} ／ 問題あり {len(results) - ok}")
    for r in results:
        if r["issues"]:
            print(" ", r["id"], "：", "、".join(r["issues"]))
    contact_sheet(d, inbox, [r for r in results if r["kind"] == "talking" and r.get("exists")])


def contact_sheet(d, inbox, talks):
    """各動画の 20%・50%・80% 地点のフレームを並べた確認用の一覧画像。"""
    from PIL import Image, ImageDraw
    from .graphics import font
    tmp = d / "review" / "_frames"
    tmp.mkdir(exist_ok=True)
    cols, tw_, th_ = 3, 320, 180
    sheet = Image.new("RGB", (cols * tw_ + 200, len(talks) * (th_ + 6)), "white")
    dr = ImageDraw.Draw(sheet)
    for i, r in enumerate(talks):
        dr.text((6, i * (th_ + 6) + 80), r["id"], font=font("sans_bold", 26), fill=(20, 30, 60))
        for j, f in enumerate((0.2, 0.5, 0.8)):
            t = (r.get("duration") or 1) * f
            fp = tmp / f"{r['id']}_{j}.png"
            subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i",
                            str(inbox / r["file"]), "-frames:v", "1", str(fp)], check=False)
            if fp.exists():
                im = Image.open(fp).convert("RGB")
                im.thumbnail((tw_, th_))
                sheet.paste(im, (200 + j * tw_ + (tw_ - im.width) // 2, i * (th_ + 6)))
    sheet.save(d / "review" / "asset_contact_sheet.png")


if __name__ == "__main__":
    main()
