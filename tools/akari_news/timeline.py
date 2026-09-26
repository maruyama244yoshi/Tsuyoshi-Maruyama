"""音声を並べてタイムラインと字幕（SRT/VTT）を作る。

ショットごとの音声は次の優先順で使う:
  1. clips/<scene>_<nn>_<speaker>.mp4      … 話しているカットの動画（口パク動画の音声をそのまま使う）
  2. voice/final/<scene>_<nn>_<speaker>.wav … 本番TTS音声（ショット単位）
  3. Open JTalk のガイド音声（文単位で合成。尺合わせ専用・公開不可）

  python3 -m tools.akari_news.timeline episode_001            # 本編
  python3 -m tools.akari_news.timeline episode_001 --shorts   # Shorts

仮音声は Open JTalk（オフライン）で合成する **尺合わせ用のガイド** であり、公開用ではない。
本番音声（燈＝女性AI音声、大家M＝男性AI音声）に差し替えたら、同じ手順で
voice/ 以下の文単位wavを置き換え `--use-existing` で再計算すれば字幕とタイミングが更新される。
"""
import argparse
import json
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from .build_episode import cues_for_shot, split_sentences, tts_text, wrap2
from .common import episode_dir, load_json

SR = 48000
JTALK_DIC = "/var/lib/mecab/dic/open-jtalk/naist-jdic"
JTALK_VOICE = "/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice"
# 話者ごとのガイド音声パラメータ（燈はピッチを上げ、少しゆっくり）
VOICE = {"akari": ["-fm", "5.5", "-r", "1.16", "-a", "0.52"],
         "ooka_m": ["-fm", "-1.0", "-r", "1.14", "-a", "0.55"]}
GAP_SENT, GAP_SHOT, GAP_SCENE, JINGLE_SEC = 0.25, 0.40, 0.75, 2.0
LEAD_IN, TAIL = 0.6, 2.5


def synth(text, speaker, out: Path):
    if not shutil.which("open_jtalk"):
        raise SystemExit("open_jtalk がありません: apt-get install open-jtalk open-jtalk-mecab-naist-jdic hts-voice-nitech-jp-atr503-m001")
    subprocess.run(["open_jtalk", "-x", JTALK_DIC, "-m", JTALK_VOICE, "-s", str(SR), *VOICE[speaker], "-ow", str(out)],
                   input=text.encode("utf-8"), check=True)


def speech_frames(x, hop=0.02, floor_db=-45):
    """20ms ごとの発話有無（True＝声あり）。"""
    f = int(SR * hop)
    n = len(x) // f
    db = 10 * np.log10((x[:n * f].reshape(n, f) ** 2).mean(1) + 1e-12)
    return db > floor_db


def align_cues(x, cues, hop=0.02, min_pause=0.2, snap=0.8):
    """実音声 x の中で各字幕キューの (開始, 終了) 秒を推定する。
    発話区間（無音を除いた時間）に読みのモーラ数比で配分し、境目は ±snap 秒以内の息継ぎ（min_pause 以上の無音）の中央へ寄せる。"""
    from .qa_assets import mora_count
    on = speech_frames(x, hop)
    dur = len(x) / SR
    idx = np.where(on)[0]
    if len(cues) == 0:
        return []
    if not len(idx):
        return [(dur * i / len(cues), dur * (i + 1) / len(cues)) for i in range(len(cues))]
    first, last = idx[0], idx[-1]
    act = np.cumsum(on[first:last + 1])
    pauses, run = [], 0
    for i, v in enumerate(on[first:last + 1]):
        if not v:
            run += 1
        else:
            if run * hop >= min_pause:
                pauses.append(((first + i - run) * hop, (first + i) * hop))
            run = 0
    w = [max(1, mora_count(tts_text(c))) for c in cues]
    tot, acc, bounds = sum(w), 0, []
    for wi in w[:-1]:
        acc += wi
        k = int(np.searchsorted(act, act[-1] * acc / tot))
        b = (first + k) * hop
        near = [p for p in pauses if abs((p[0] + p[1]) / 2 - b) <= snap]
        if near:
            p = min(near, key=lambda p: abs((p[0] + p[1]) / 2 - b))
            b = (p[0] + p[1]) / 2
        bounds.append(max(b, bounds[-1] if bounds else 0))
    start, end = max(0.0, first * hop - 0.05), min(dur, (last + 1) * hop + 0.25)
    edges = [start, *bounds, end]
    return [(edges[i], edges[i + 1]) for i in range(len(cues))]


def read_wav(p):
    """任意の音声ファイル（16/24bit WAV・任意サンプルレート）を 48kHz モノラル float で読む。"""
    from .video import ffmpeg
    raw = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", str(p), "-ac", "1", "-ar", str(SR),
                          "-af", "aresample=resampler=soxr", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def write_wav(p, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def jingle(sec=JINGLE_SEC):
    """自前生成の短いチャイム（権利フリー）。ゴールド＝光のイメージで2音の上行。"""
    t = np.arange(int(SR * sec)) / SR
    out = np.zeros_like(t)
    for start, f in ((0.0, 659.25), (0.18, 987.77)):
        tt = np.clip(t - start, 0, None)
        env = np.where(t >= start, np.exp(-tt * 3.2), 0)
        out += env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt))
    return 0.18 * out / np.abs(out).max()


def tighten_pauses(x, max_pause, edge=0.08, hop=0.02, fade=0.01):
    """声だけの音声の「間」を詰める：max_pause 秒を超える無音を max_pause 秒に、先頭・末尾の無音を edge 秒にする。
    声の部分は一切伸縮・加工しない（無音の真ん中を切り、切り口を 10ms でつなぐ）。"""
    on = speech_frames(x, hop)
    f = int(SR * hop)
    idx = np.where(on)[0]
    if not len(idx):
        return x
    first, last = idx[0], idx[-1]
    keep = [(max(0, first * f - int(SR * edge)), None)]
    run_start = None
    for i in range(first, last + 1):
        if not on[i]:
            run_start = i if run_start is None else run_start
            continue
        if run_start is not None and (i - run_start) * hop > max_pause:
            half = int(SR * max_pause / 2)
            keep[-1] = (keep[-1][0], run_start * f + half)
            keep.append((i * f - half, None))
        run_start = None
    keep[-1] = (keep[-1][0], min(len(x), (last + 1) * f + int(SR * edge)))
    nf = int(SR * fade)
    out = []
    for a, b in keep:
        seg = x[a:b].copy()
        if len(seg) > 2 * nf:
            seg[:nf] *= np.linspace(0, 1, nf, dtype=np.float32)
            seg[-nf:] *= np.linspace(1, 0, nf, dtype=np.float32)
        out.append(seg)
    return np.concatenate(out)


def normalize_rms(x, target_db=-20.0):
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    return x * (10 ** (target_db / 20) / rms)


def names_for(d, ver):
    p = d / "production" / f"clip_map_{ver}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def clip_path(d, scene_id, idx, speaker, names=None):
    shot = f"{scene_id}_{idx:02}_{speaker}"
    name = (names or {}).get(shot)
    if name and (d / "clips" / f"{name}.mp4").exists():
        return d / "clips" / f"{name}.mp4"
    return d / "clips" / f"{shot}.mp4"


def final_voice(d, scene_id, idx, speaker, names=None):
    """本番音声：voice/final/<正式名>.wav（.mp4 も可）→ 旧名。無ければ None。"""
    shot = f"{scene_id}_{idx:02}_{speaker}"
    for n in [x for x in ((names or {}).get(shot), shot) if x]:
        for ext in (".wav", ".mp4", ".flac"):
            p = d / "voice" / "final" / f"{n}{ext}"
            if p.exists():
                return p
    return None


def audio_from_clip(mp4: Path, out_wav: Path):
    from .video import ffmpeg
    subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp4), "-vn", "-ac", "1",
                    "-ar", str(SR), "-c:a", "pcm_s16le", str(out_wav)], check=True)
    return out_wav


def ts(sec, sep=","):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"


def build(ep_id, shorts=False, use_existing=False, short_no=None):
    d = episode_dir(ep_id)
    ep = load_json(d / "script" / f"{ep_id}.json")
    if short_no:
        sh = ep["shorts_list"][short_no - 1]
        shorts = True
        tag = f"{ep_id}_short{short_no:02}"
        scenes = [{"id": sh["id"], "title": sh["title"], "shots": sh["shots"]}]
    else:
        sh = ep.get("shorts", {})
        tag = f"{ep_id}_shorts" if shorts else ep_id
        scenes = [{"id": "SHORTS", "title": "Shorts", "shots": sh["shots"]}] if shorts else ep["scenes"]
    names = names_for(d, "v2")
    # 発話間の「間」は編集側で調整できる（音声そのものは加工しない）
    gap_shot = ep.get("edit", {}).get("gap_shot", GAP_SHOT)
    gap_scene = ep.get("edit", {}).get("gap_scene", GAP_SCENE)
    vdir = d / "voice" / ("guide_shorts" if shorts else "guide")
    vdir.mkdir(parents=True, exist_ok=True)

    audio = [np.zeros(int(SR * LEAD_IN), np.float32)]
    t = LEAD_IN
    shots_out, cues_out, events, sources = [], [], [], {}
    for si, sc in enumerate(scenes):
        if si > 0:
            audio.append(np.zeros(int(SR * gap_scene), np.float32)); t += gap_scene
        if sc.get("jingle_before"):
            events.append({"type": "jingle", "start": t, "end": t + JINGLE_SEC,
                           "visual": sc.get("jingle_visual", "gfx:G09_ippo_card"), "scene": sc["id"]})
            audio.append(jingle()); t += JINGLE_SEC
        for hi, shot in enumerate(sc["shots"]):
            if hi > 0:
                audio.append(np.zeros(int(SR * gap_shot), np.float32)); t += gap_shot
            shot_start = t
            cue_texts = cues_for_shot(shot["text"])
            sentences = split_sentences(shot["text"])
            sent_timing = []
            if shot.get("asset"):  # 素材IDで直接指定（正式ファイル名）
                clip = d / "clips" / f"{shot['asset']}.mp4"
                final = next((p for p in (d / "voice" / "final" / f"{shot['asset']}{e}" for e in (".wav", ".mp4"))
                              if p.exists()), None)
            else:
                clip = clip_path(d, sc["id"], hi, shot["speaker"], names)
                final = final_voice(d, sc["id"], hi, shot["speaker"], names)
            if shot["visual"].startswith("talk:") and clip.exists():
                src = "clip"
                x = normalize_rms(read_wav(audio_from_clip(clip, vdir / f"_clip_{sc['id']}_{hi:02}.wav")))
            elif final is not None:
                src = "final"
                x = normalize_rms(read_wav(final))
                if ep.get("edit", {}).get("vo_max_pause"):
                    x = tighten_pauses(x, ep["edit"]["vo_max_pause"], ep["edit"].get("vo_edge", 0.08))
            else:
                src = "guide"
                x = None
            cue_timing = None
            if x is not None:
                # 実音声：字幕キューは発話区間に読み（モーラ数）比で配分し、境目は近くの息継ぎに合わせる
                audio.append(x)
                cue_timing = [(c, t + a, t + b) for c, (a, b) in zip(cue_texts, align_cues(x, cue_texts))]
                t += len(x) / SR
            else:
                # 文単位で合成→字幕キューは文内の文字数比で配分
                for ni, sent in enumerate(sentences):
                    if ni > 0:
                        audio.append(np.zeros(int(SR * GAP_SENT), np.float32)); t += GAP_SENT
                    wav = vdir / f"{sc['id']}_{hi:02}_{ni:02}_{shot['speaker']}.wav"
                    if not (use_existing and wav.exists()):
                        synth(tts_text(sent), shot["speaker"], wav)
                    x = normalize_rms(read_wav(wav))
                    audio.append(x)
                    sent_timing.append((sent, t, t + len(x) / SR))
                    t += len(x) / SR
            sources[src] = sources.get(src, 0) + 1
            # キュー → 文タイミングへ割付け
            for c, a0, a1 in cue_timing or []:
                cues_out.append({"start": round(a0, 3), "end": round(a1, 3), "speaker": shot["speaker"],
                                 "lines": wrap2(c)})
            ci = 0
            for sent, s0, s1 in sent_timing:
                acc, total = 0, len(sent)
                while ci < len(cue_texts) and acc < total:
                    c = cue_texts[ci]
                    a0 = s0 + (s1 - s0) * acc / total
                    acc += len(c)
                    a1 = s0 + (s1 - s0) * min(acc, total) / total
                    cues_out.append({"start": round(a0, 3), "end": round(a1, 3), "speaker": shot["speaker"],
                                     "lines": wrap2(c)})
                    ci += 1
            shots_out.append({"scene": sc["id"], "scene_title": sc["title"], "index": hi, "speaker": shot["speaker"],
                              "visual": shot["visual"], "face": shot.get("face"), "text": shot["text"],
                              "asset": shot.get("asset"), "vkeywords": shot.get("vkeywords"),
                              "cutaway": ({"at": round(shot_start + shot["cutaway"]["after"], 3),
                                           "visual": shot["cutaway"]["visual"]} if shot.get("cutaway") else None),
                              "audio_source": src, "clip": str(clip.relative_to(d)) if src == "clip" else None,
                              "start": round(shot_start, 3), "end": round(t, 3)})
    audio.append(np.zeros(int(SR * TAIL), np.float32)); t += TAIL
    full = np.concatenate(audio)
    peak = np.abs(full).max()
    if peak > 0.95:
        full *= 0.95 / peak
    wav_out = d / "voice" / f"{tag}_mix_{ep.get('script_version', 'v1')}.wav"
    write_wav(wav_out, full)

    # ショットの表示区間は次のショット開始まで延長（間で画面が途切れないように）
    for a, b in zip(shots_out, shots_out[1:]):
        a["display_end"] = b["start"]
    outro = (sh if shorts else ep).get("outro_visual")
    last_end = shots_out[-1]["end"]
    shots_out[-1]["display_end"] = round(last_end + 0.4, 3) if outro else round(t, 3)
    if outro:
        events.append({"type": "outro", "start": shots_out[-1]["display_end"], "end": round(t, 3), "visual": outro, "scene": "OUTRO"})
    shots_out[0]["start_display"] = 0.0

    ver = ep.get("script_version", "v1")
    tl = {"episode": ep_id, "kind": "shorts" if shorts else "long", "version": ver, "duration": round(t, 3),
          "audio": str(wav_out.relative_to(d)), "audio_sources": sources, "shots": shots_out, "cues": cues_out,
          "events": events,
          "note": "guide=Open JTalk仮音声（公開不可）/ final=本番TTS / clip=話しているカットの音声"}
    (d / "script" / f"{tag}_timeline_{ver}.json").write_text(json.dumps(tl, ensure_ascii=False, indent=2), encoding="utf-8")

    sub = d / "subtitles"
    sub.mkdir(exist_ok=True)
    srt, vtt = [], ["WEBVTT", ""]
    for i, c in enumerate(cues_out, 1):
        body = "\n".join(c["lines"])
        srt += [str(i), f"{ts(c['start'])} --> {ts(c['end'])}", body, ""]
        vtt += [f"{ts(c['start'], '.')} --> {ts(c['end'], '.')}", body, ""]
    (sub / f"{tag}_{ver}.srt").write_text("\n".join(srt), encoding="utf-8")
    (sub / f"{tag}_{ver}.vtt").write_text("\n".join(vtt), encoding="utf-8")

    by = screen_ratio(tl)
    print(f"{tag}: {t:.1f}s ({int(t // 60)}:{t % 60:04.1f})  cues={len(cues_out)}  shots={len(shots_out)}  audio={sources}")
    for k, v in by.items():
        print(f"  {k:10s} {v:6.1f}s  {100 * v / t:5.1f}%")
    return tl


def who_on_screen(visual):
    kind, key = visual.split(":", 1)
    if kind in ("talk", "cut"):
        return "ooka_m" if key.startswith("ooka") else "akari"
    return "graphics"


def visual_at(tl, t):
    """時刻 t に画面に出ている visual（ジングル・アウトロを優先）。video.py と同じ規則。"""
    for e in tl["events"]:
        if e["start"] <= t < e["end"]:
            return e["visual"], e.get("scene"), None
    cur = tl["shots"][0]
    for s in tl["shots"]:
        if s["start"] <= t + 1e-6:
            cur = s
    cw = cur.get("cutaway")
    if cw and t >= cw["at"]:  # 長い発言の途中から図表へ（声は続く）
        return cw["visual"], cur["scene"], dict(cur, visual=cw["visual"], clip=None, start=cw["at"])
    return cur["visual"], cur["scene"], cur


def screen_ratio(tl, step=0.05):
    """画面に燈／大家M／図表が映っている秒数（step秒ごとに判定）。"""
    by = {"akari": 0.0, "ooka_m": 0.0, "graphics": 0.0}
    n = int(tl["duration"] / step)
    for i in range(n):
        by[who_on_screen(visual_at(tl, (i + 0.5) * step)[0])] += step
    return by


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--shorts", action="store_true")
    ap.add_argument("--short", type=int, help="shorts_list の番号（1始まり）")
    ap.add_argument("--use-existing", action="store_true", help="既存の文単位wavを使う（本番音声差し替え時）")
    a = ap.parse_args(argv)
    build(a.episode, a.shorts, a.use_existing, a.short)


if __name__ == "__main__":
    main()
