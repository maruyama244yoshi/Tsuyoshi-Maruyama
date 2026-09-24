"""タイムライン＋グラフィック＋字幕＋音声から動画（初稿）を組み立てる。

  python3 -m tools.akari_news.video episode_001            # 本編 16:9
  python3 -m tools.akari_news.video episode_001 --shorts   # Shorts 9:16

前提: graphics / timeline を先に実行しておくこと。
字幕は画面に焼き込み（オープンキャプション）。YouTube字幕用には subtitles/*.srt を別途アップロード。
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .common import episode_dir, load_json
from .graphics import C, fit_size, hexrgb, text, tw, visual_path

SPEAKER = {"akari": ("燈", "GOLD"), "ooka_m": ("大家M", "BEIGE")}
FPS = 30


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def rewrap(t, n):
    from .build_episode import best_break
    if len(t) <= n:
        return [t]
    i = best_break(t, n) if len(t) <= 2 * n else best_break(t[: 2 * n], n)
    i = min(i, n + 2)
    return [t[:i]] + rewrap(t[i:], n)


def overlay_subtitle(im, cue, vertical, draft_label):
    im = im.convert("RGB").copy()
    d = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    if draft_label:
        s = draft_label
        d.rounded_rectangle([W - tw(d, s, 22, "sans_bold") - 60, 106 if not vertical else 106, W - 24, 144 if not vertical else 144],
                            8, fill=hexrgb(C["ALERT_RED"], 200))
        text(d, (W - 42, 125), s, 22, "WHITE", "sans_bold", "rm")
    if not cue:
        return im
    lines = cue["lines"]
    if vertical:  # 縦型は1行16文字前後で組み直す
        lines = rewrap("".join(lines), 16)
    name, col = SPEAKER[cue["speaker"]]
    if vertical:
        size, lh, y_center, maxw = 62, 84, 1540, W - 100
    else:
        size, lh, y_center, maxw = 54, 72, 968, W - 260
    size = min(fit_size(d, ln, size, maxw) for ln in lines)
    block = lh * len(lines)
    top = y_center - block / 2 - 26
    d.rectangle([0, top, W, top + block + 52], fill=hexrgb(C["NAVY_DEEP"], 205))
    d.rectangle([0, top, W, top + 4], fill=hexrgb(C[col], 230))
    for i, ln in enumerate(lines):
        y = top + 26 + lh * i + lh / 2
        # 縁取りで可読性を確保
        text(d, (W / 2, y), ln, size, "WHITE", "sans_bold", "mm", stroke_width=3, stroke_fill=hexrgb(C["NAVY_DEEP"]))
    # 話者ラベル
    lab_w = tw(d, name, 28) + 36
    if vertical:
        lx, ly = 40, top - 46
    else:
        lx, ly = 40, top - 46
    d.rounded_rectangle([lx, ly, lx + lab_w, ly + 42], 8, fill=hexrgb(C[col]))
    text(d, (lx + lab_w / 2, ly + 21), name, 28, "NAVY_DEEP", "sans_black", "mm")
    return im


def build(ep_id, shorts=False, draft_label="初稿・仮音声"):
    d = episode_dir(ep_id)
    tag = f"{ep_id}_shorts" if shorts else ep_id
    tl = load_json(d / "script" / f"{tag}_timeline_v1.json")
    shots, cues, events = tl["shots"], tl["cues"], tl["events"]
    T = tl["duration"]
    pts = {0.0, T}
    for s in shots:
        pts |= {s["start"], s["display_end"]}
    for c in cues:
        pts |= {c["start"], c["end"]}
    for e in events:
        pts |= {e["start"], e["end"]}
    pts = sorted(p for p in pts if 0 <= p <= T)

    def shot_at(t):
        for e in events:  # ジングル中は次のショット（大家の一手カード）を先出し
            if e["start"] <= t < e["end"]:
                return next(s for s in shots if s["start"] >= e["end"] - 1e-6)
        cur = shots[0]
        for s in shots:
            if s["start"] <= t + 1e-6:
                cur = s
        return cur

    def cue_at(t):
        for i, c in enumerate(cues):
            if c["start"] <= t + 1e-6 < c["end"]:
                return i
        return None

    tmp = Path(tempfile.mkdtemp(prefix=f"{tag}_frames_"))
    cache, entries = {}, []
    for a, b in zip(pts, pts[1:]):
        if b - a < 1 / FPS / 2:
            continue
        m = (a + b) / 2
        s = shot_at(m)
        ci = cue_at(m)
        key = (s["scene"], s["visual"], ci)
        if key not in cache:
            img = Image.open(visual_path(ep_id, s["scene"], s["visual"].replace("vgfx:", "gfx:")))
            fr = overlay_subtitle(img, cues[ci] if ci is not None else None, shorts, draft_label)
            p = tmp / f"f{len(cache):04}.png"
            fr.save(p)
            cache[key] = p
        entries.append((cache[key], b - a))
    lst = tmp / "list.txt"
    with open(lst, "w") as f:
        for p, dur in entries:
            f.write(f"file '{p}'\nduration {dur:.4f}\n")
        f.write(f"file '{entries[-1][0]}'\n")
    out_dir = d / ("shorts" if shorts else "video")
    out_dir.mkdir(exist_ok=True)
    out = out_dir / (f"{ep_id}_shorts_v1.mp4" if shorts else f"{ep_id}_long_v1.mp4")
    cmd = [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
           "-i", str(d / tl["audio"]), "-vsync", "cfr", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
           "-tune", "stillimage", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print(f"wrote {out}  frames={len(cache)} segments={len(entries)} duration={T:.1f}s")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--shorts", action="store_true")
    ap.add_argument("--final", action="store_true", help="「初稿・仮音声」表示を外す（本番音声差し替え後のみ）")
    a = ap.parse_args(argv)
    build(a.episode, a.shorts, None if a.final else "初稿・仮音声")


if __name__ == "__main__":
    main()
