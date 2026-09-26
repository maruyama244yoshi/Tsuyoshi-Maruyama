"""タイムライン＋図表＋話しているカット（動画クリップ）＋字幕＋音声から動画を組み立てる。

  python3 -m tools.akari_news.video episode_001                    # 本編 16:9
  python3 -m tools.akari_news.video episode_001 --shorts           # Shorts 9:16
  python3 -m tools.akari_news.video episode_001 --bgm path/to.mp3  # BGM（声の下で自動的に下げる）

前提: graphics / timeline を先に実行しておくこと。

visual の種類:
  gfx:/vgfx:  図表（静止）
  talk:<cut>  燈／大家Mが話しているカット。clips/<scene>_<nn>_<speaker>.mp4 があれば動画を使い、
              無ければ仮の静止カットに「動画素材待ち」を表示する（本番には使わない）
  cut:<key>   旧形式の静止カット
字幕・話者名・ネームプレートは透過レイヤーで重ねる（オープンキャプション）。
"""
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .common import episode_dir, load_json
import re

from .graphics import ANIMATED, C, fit_size, font, hexrgb, render_graphic, text, tw, visual_path

SPEAKER = {"akari": ("燈", "GOLD"), "ooka_m": ("大家M", "BEIGE")}
NAMEPLATE = {"akari": ("燈", "不動産ニュース専門AIキャスター"), "ooka_m": ("現役会社員大家M", "会社員・不動産投資家")}
FPS = 30
BGM_DB = -24  # BGM（-16 LUFSに揃えたもの）をさらに下げる量。声がある間はサイドチェインでもっと下がる
ANIM_SEC = 1.0  # 図表が出てから動く時間（そのあとは静止）
# 字幕で金色に強調する重要語（指示書 2026-09-25 §15）
KEYWORDS = ["1.25％", "444万円", "459万円", "15万円", "返済比率", "DSCR", "0.5％", "1.0％", "年間返済額"]
KW_RE = re.compile("(" + "|".join(re.escape(k) for k in sorted(KEYWORDS, key=len, reverse=True)) + ")")


def draw_rich(d, center, line, size):
    """重要語だけ金色にして1行を中央に描く。"""
    f = font("sans_bold", size)
    segs = [x for x in KW_RE.split(line) if x]
    widths = [d.textbbox((0, 0), x, font=f)[2] - d.textbbox((0, 0), x, font=f)[0] for x in segs]
    x = center[0] - sum(widths) / 2
    for seg, w in zip(segs, widths):
        col = C["GOLD"] if KW_RE.fullmatch(seg) else C["WHITE"]
        d.text((x, center[1]), seg, font=f, fill=hexrgb(col), anchor="lm", stroke_width=3,
               stroke_fill=hexrgb(C["NAVY_DEEP"]))
        x += w


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which("ffmpeg") or "ffmpeg"


def media_duration(path):
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def run(cmd):
    subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", *cmd], check=True)


def rewrap(t, n):
    from .build_episode import best_break
    if len(t) <= n:
        return [t]
    i = best_break(t, n) if len(t) <= 2 * n else best_break(t[: 2 * n], n)
    i = min(i, n + 2)
    return [t[:i]] + rewrap(t[i:], n)


def overlay_layer(size, cue, vertical, draft_label, nameplate=None, missing=None):
    """透過レイヤー：字幕・話者ラベル・ネームプレート・下書き表示。"""
    W, H = size
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if draft_label:
        s = draft_label
        d.rounded_rectangle([W - tw(d, s, 22, "sans_bold") - 60, 106, W - 24, 144], 8, fill=hexrgb(C["ALERT_RED"], 200))
        text(d, (W - 42, 125), s, 22, "WHITE", "sans_bold", "rm")
    if missing:
        s = f"動画素材待ち：{missing}"
        d.rounded_rectangle([24, 160, 60 + tw(d, s, 28, "sans_bold"), 210], 8, fill=hexrgb(C["ALERT_RED"], 220))
        text(d, (42, 185), s, 28, "WHITE", "sans_bold", "lm")
    if nameplate:
        name, role = nameplate
        x, y = (60, H - 560) if vertical else (70, 690)
        w = tw(d, name, 40) + 60 + tw(d, role, 24, "sans_medium") + 30
        d.rounded_rectangle([x, y, x + w, y + 80], 10, fill=hexrgb(C["NAVY_DEEP"], 225))
        d.rectangle([x, y, x + 8, y + 80], fill=hexrgb(C["GOLD"]))
        text(d, (x + 30, y + 40), name, 40, "WHITE", "sans_bold", "lm")
        text(d, (x + 30 + tw(d, name, 40) + 26, y + 42), role, 24, "BEIGE", "sans_medium", "lm")
    if not cue:
        return im
    lines = cue["lines"]
    if vertical:  # 縦型は1行16文字前後で組み直す
        lines = rewrap("".join(lines), 16)
    name, col = SPEAKER[cue["speaker"]]
    if vertical:
        size_, lh, y_center, maxw = 62, 84, 1540, W - 100
    else:
        size_, lh, y_center, maxw = 54, 72, 968, W - 260
    size_ = min(fit_size(d, ln, size_, maxw) for ln in lines)
    block = lh * len(lines)
    top = y_center - block / 2 - 26
    d.rectangle([0, top, W, top + block + 52], fill=hexrgb(C["NAVY_DEEP"], 205))
    d.rectangle([0, top, W, top + 4], fill=hexrgb(C[col], 230))
    for i, ln in enumerate(lines):
        y = top + 26 + lh * i + lh / 2
        draw_rich(d, (W / 2, y), ln, size_)
    lab_w = tw(d, name, 28) + 36
    lx, ly = 40, top - 46
    d.rounded_rectangle([lx, ly, lx + lab_w, ly + 42], 8, fill=hexrgb(C[col]))
    text(d, (lx + lab_w / 2, ly + 21), name, 28, "NAVY_DEEP", "sans_black", "mm")
    return im


def still_for(ep_id, ep, scene, visual):
    """静止画のパス。talk: は素材待ち用のフォールバック静止カット。"""
    kind, key = visual.split(":", 1)
    if kind == "talk":
        fb = ep.get("talk_cuts", {}).get(key, {}).get("fallback", "cut:akari_front")
        return visual_path(ep_id, scene, fb)
    return visual_path(ep_id, scene, visual.replace("vgfx:", "gfx:"))


def content_box(clip):
    """縦長キャンバスの中に横長映像が入っている素材から、映像部分（余白を除く）の範囲を得る。"""
    import numpy as np
    fr = Path(tempfile.mkdtemp()) / "f.png"
    run(["-ss", "1", "-i", str(clip), "-frames:v", "1", str(fr)])
    x = np.asarray(Image.open(fr).convert("RGB")).astype(int)
    bg = x[3, 3]
    ys, xs = np.where(np.abs(x - bg).sum(axis=2) > 30)
    if len(xs) == 0:
        return None
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    if (x1 - x0) * (y1 - y0) > 0.9 * x.shape[0] * x.shape[1]:
        return None  # 余白なし
    return int(x0) // 2 * 2, int(y0) // 2 * 2, int(x1 - x0) // 2 * 2, int(y1 - y0) // 2 * 2


def vertical_talk_bg(title, keywords, speaker_name):
    """Shorts の話しているカット用の背景（上：人物パネル枠、中：キーワード）。"""
    from .graphics import VW, VH, base, header, panel
    im = base(VW, VH)
    header(im, title)
    d = ImageDraw.Draw(im, "RGBA")
    d.rounded_rectangle([0, 150, VW, 150 + 608 + 8], 0, fill=hexrgb(C["GOLD"]))
    y = 900
    for i, kw in enumerate(keywords or []):
        size = fit_size(d, kw, 84 if i == 0 else 60, VW - 120, "sans_black")
        if i == 0:
            text(d, (VW / 2, y), kw, size, "GOLD", "sans_black", "mm")
        else:
            panel(d, (90, y - 55, VW - 90, y + 55), "NAVY_DEEP", 235, "GOLD")
            text(d, (VW / 2, y), kw, size, "WHITE", "sans_black", "mm")
        y += 150
    return im


def build(ep_id, shorts=False, draft_label="第2稿・仮音声", bgm=None, short_no=None, out_path=None):
    d = episode_dir(ep_id)
    ep = load_json(d / "script" / f"{ep_id}.json")
    ver = ep.get("script_version", "v1")
    global NAMEPLATE
    NAMEPLATE = {k: tuple(v) for k, v in ep.get("nameplates", {}).items()} or NAMEPLATE
    tag = f"{ep_id}_shorts" if shorts else ep_id
    sh_title = "Shorts"
    if short_no:
        shorts, tag = True, f"{ep_id}_short{short_no:02}"
        sh_title = ep["shorts_list"][short_no - 1]["title"]
    tl = load_json(d / "script" / f"{tag}_timeline_{ver}.json")
    from .timeline import visual_at
    W, H = (1080, 1920) if shorts else (1920, 1080)
    shots, cues, events = tl["shots"], tl["cues"], tl["events"]
    T = tl["duration"]
    pts = {0.0, T}
    for s in shots:
        pts |= {s["start"], s["display_end"]}
        if s.get("cutaway"):
            pts.add(s["cutaway"]["at"])
    for c in cues:
        pts |= {c["start"], c["end"]}
    for e in events:
        pts |= {e["start"], e["end"]}
    pts = sorted(p for p in pts if 0 <= p <= T)

    def cue_at(t):
        for i, c in enumerate(cues):
            if c["start"] <= t + 1e-6 < c["end"]:
                return i
        return None

    tmp = Path(tempfile.mkdtemp(prefix=f"{tag}_parts_"))
    parts, missing, used_clips, clip_dur, shown_before, boxes = [], set(), set(), {}, {}, {}
    for n, (a, b) in enumerate(zip(pts, pts[1:])):
        dur = b - a
        if dur < 1 / FPS / 2:
            continue
        visual, scene, shot = visual_at(tl, (a + b) / 2)
        ci = cue_at((a + b) / 2)
        cue = cues[ci] if ci is not None else None
        is_talk = visual.startswith("talk:")
        clip = d / shot["clip"] if (is_talk and shot and shot.get("clip")) else None
        if is_talk and not clip:
            missing.add(visual[5:])
        plate = NAMEPLATE[shot["speaker"]] if (is_talk and shot) else None
        ov = tmp / f"ov{n:04}.png"
        overlay_layer((W, H), cue, shorts, draft_label, plate if (clip and not shorts) else None,
                      visual[5:] if (is_talk and not clip) else None).save(ov)
        out = tmp / f"p{n:04}.mp4"
        # 部品ごとに時間の刻み（timescale）とフレームレートを揃えないと concat で尺が崩れる
        enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
               "-fps_mode", "cfr", "-video_track_timescale", "15360", "-an"]
        if clip:
            used_clips.add(str(clip))
            # 発話後の「間」はクリップの最後のフレームで埋める（クリップ終端を越えて読まない）
            cdur = clip_dur.setdefault(clip, media_duration(clip))
            # 音声トラックの方がわずかに長い素材があるため、映像の最終フレームより手前で止める
            off = min(max(0.0, a - shot["start"]), max(0.0, cdur - 0.3))
            # 画面いっぱいに拡大して中央を切り出す（縦型にも対応）。動きは元動画のまま
            if shorts:
                # 縦型：人物映像（余白を除いた横長部分）を上部パネルに、下にキーワードと字幕
                box = boxes.setdefault(clip, content_box(clip))
                crop = f"crop={box[2]}:{box[3]}:{box[0]}:{box[1]}," if box else ""
                bgp = tmp / f"bg{n:04}.png"
                bgim = vertical_talk_bg(sh_title, shot.get("vkeywords"), NAMEPLATE[shot["speaker"]][0])
                pl = ImageDraw.Draw(bgim, "RGBA")
                name = NAMEPLATE[shot["speaker"]][0]
                pl.rounded_rectangle([40, 150 + 608 + 24, 40 + tw(pl, name, 40) + 60, 150 + 608 + 94], 10,
                                     fill=hexrgb(C["NAVY_DEEP"], 235))
                pl.rectangle([40, 150 + 608 + 24, 47, 150 + 608 + 94], fill=hexrgb(C["GOLD"]))
                text(pl, (70, 150 + 608 + 59), name, 40, "WHITE", "sans_bold", "lm")
                bgim.save(bgp)
                vf = (f"[0:v]{crop}scale={W}:-2,setsar=1,fps={FPS},tpad=stop_mode=clone:stop_duration={dur + 1:.3f}[p];"
                      f"[1:v][p]overlay=0:154[b];[b][2:v]overlay=0:0")
                run(["-ss", f"{off:.3f}", "-i", str(clip), "-loop", "1", "-i", str(bgp), "-i", str(ov),
                     "-filter_complex", vf, "-t", f"{dur:.3f}", *enc, str(out)])
            else:
                vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},"
                      f"tpad=stop_mode=clone:stop_duration={dur + 1:.3f}[v];[v][1:v]overlay=0:0")
                run(["-ss", f"{off:.3f}", "-i", str(clip), "-i", str(ov),
                     "-filter_complex", vf, "-t", f"{dur:.3f}", *enc, str(out)])
        else:
            key = visual.split(":", 1)[1]
            ovl = Image.open(ov)
            # 図表が新しく出た最初の区間だけ、ANIM_SEC 秒アニメーションさせる
            anim = (visual.startswith("gfx:") and key in ANIMATED and shot is not None
                    and abs(a - shot["start"]) < 1e-3 and shown_before.get(shot["scene"], {}).get(key) is None
                    and not shorts)
            shown_before.setdefault(shot["scene"] if shot else "_", {})[key] = True
            if anim:
                na = int(min(ANIM_SEC, dur) * FPS)
                fdir = tmp / f"anim{n:04}"
                fdir.mkdir()
                for i in range(na):
                    fr_im = render_graphic(ep["simulation"], key, (i + 1) / na)
                    Image.alpha_composite(fr_im.convert("RGBA"), ovl).convert("RGB").save(fdir / f"{i:04}.png")
                run(["-framerate", str(FPS), "-i", str(fdir / "%04d.png"), "-frames:v", str(na), *enc, str(out)])
                rest = dur - na / FPS
                if rest > 1 / FPS / 2:
                    out2 = tmp / f"p{n:04}b.mp4"
                    img = Image.alpha_composite(render_graphic(ep["simulation"], key, 1.0).convert("RGBA"), ovl).convert("RGB")
                    fr = tmp / f"f{n:04}.png"
                    img.save(fr)
                    run(["-loop", "1", "-framerate", str(FPS), "-t", f"{rest:.3f}", "-i", str(fr), "-tune", "stillimage", *enc, str(out2)])
                    for pp, dd in ((out, na / FPS), (out2, rest)):
                        if abs(media_duration(pp) - dd) > 0.1:
                            raise RuntimeError(f"部品の尺が不正: {pp.name}")
                        parts.append(pp)
                    continue
            else:
                img = Image.open(still_for(ep_id, ep, scene, visual)).convert("RGB")
                if img.size != (W, H):
                    img = img.resize((W, H))
                img = Image.alpha_composite(img.convert("RGBA"), ovl).convert("RGB")
                fr = tmp / f"f{n:04}.png"
                img.save(fr)
                run(["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(fr), "-tune", "stillimage", *enc, str(out)])
        pd = media_duration(out)
        if abs(pd - dur) > 0.1:
            raise RuntimeError(f"部品の尺が不正: {out.name} 期待{dur:.2f}s 実際{pd:.2f}s ({visual})")
        parts.append(out)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    silent = tmp / "video.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent)])
    vd = media_duration(silent)
    if abs(vd - T) > 0.5:
        raise RuntimeError(f"連結後の尺が不正: 期待{T:.1f}s 実際{vd:.1f}s")

    out_dir = d / ("shorts" if shorts else "video")
    out_dir.mkdir(exist_ok=True)
    out = out_dir / (f"{ep_id}_shorts_{ver}.mp4" if shorts else f"{ep_id}_long_{ver}.mp4")
    if out_path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
    voice = d / tl["audio"]
    if bgm:
        # BGMはループさせ、声がある間は自動で下げる（サイドチェイン）
        fc = (f"[2:a]aloop=loop=-1:size=2e9,atrim=0:{T:.3f},volume={BGM_DB}dB[bg];"
              f"[1:a]asplit=2[vo][sc];[bg][sc]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[duck];"
              f"[vo][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000:resampler=soxr,aformat=channel_layouts=stereo[a]")
        run(["-i", str(silent), "-i", str(voice), "-i", str(bgm), "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)])
    else:
        run(["-i", str(silent), "-i", str(voice), "-map", "0:v", "-map", "1:a", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000:resampler=soxr,aformat=channel_layouts=stereo",
             "-c:v", "copy", "-c:a", "aac",
             "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)])
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote {out}  parts={len(parts)} duration={T:.1f}s clips_used={len(used_clips)}"
          + (f"  動画素材待ち={sorted(missing)}" if missing else ""))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--shorts", action="store_true")
    ap.add_argument("--bgm", help="BGM音源ファイル（wav 等）。auto なら自作BGM（tools/akari_news/bgm.py）を使う")
    ap.add_argument("--final", action="store_true", help="下書き表示を外す（本番音声・本番クリップ差し替え後のみ）")
    ap.add_argument("--short", type=int, help="shorts_list の番号（1始まり）")
    ap.add_argument("--out", help="書き出し先のファイルパス")
    a = ap.parse_args(argv)
    bgm = a.bgm
    if bgm == "auto":
        from .bgm import main as bgm_main
        bgm = str(episode_dir(a.episode) / "voice" / "bgm_auto.wav")
        if not Path(bgm).exists():
            bgm_main([bgm, "--sec", "64"])
    build(a.episode, a.shorts, None if a.final else "第2稿・仮音声", bgm, a.short, a.out)


if __name__ == "__main__":
    main()
