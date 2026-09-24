"""仮音声（ガイド音声）を合成してタイムラインと字幕（SRT/VTT）を作る。

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


def read_wav(p):
    with wave.open(str(p)) as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


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


def normalize_rms(x, target_db=-20.0):
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    return x * (10 ** (target_db / 20) / rms)


def ts(sec, sep=","):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"


def build(ep_id, shorts=False, use_existing=False):
    d = episode_dir(ep_id)
    ep = load_json(d / "script" / f"{ep_id}.json")
    tag = f"{ep_id}_shorts" if shorts else ep_id
    scenes = [{"id": "SHORTS", "title": "Shorts", "shots": ep["shorts"]["shots"]}] if shorts else ep["scenes"]
    vdir = d / "voice" / ("guide_shorts" if shorts else "guide")
    vdir.mkdir(parents=True, exist_ok=True)

    audio = [np.zeros(int(SR * LEAD_IN), np.float32)]
    t = LEAD_IN
    shots_out, cues_out, events = [], [], []
    for si, sc in enumerate(scenes):
        if si > 0:
            audio.append(np.zeros(int(SR * GAP_SCENE), np.float32)); t += GAP_SCENE
        if sc.get("jingle_before"):
            events.append({"type": "jingle", "start": t, "end": t + JINGLE_SEC})
            audio.append(jingle()); t += JINGLE_SEC
        for hi, shot in enumerate(sc["shots"]):
            if hi > 0:
                audio.append(np.zeros(int(SR * GAP_SHOT), np.float32)); t += GAP_SHOT
            shot_start = t
            # 文単位で合成→字幕キューは文内の文字数比で配分
            cue_texts = cues_for_shot(shot["text"])
            sentences = split_sentences(shot["text"])
            sent_timing = []
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
            # キュー → 文タイミングへ割付け
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
                              "start": round(shot_start, 3), "end": round(t, 3)})
    audio.append(np.zeros(int(SR * TAIL), np.float32)); t += TAIL
    full = np.concatenate(audio)
    peak = np.abs(full).max()
    if peak > 0.95:
        full *= 0.95 / peak
    wav_out = d / "voice" / f"{tag}_guide_v1.wav"
    write_wav(wav_out, full)

    # ショットの表示区間は次のショット開始まで延長（間で画面が途切れないように）
    for a, b in zip(shots_out, shots_out[1:]):
        a["display_end"] = b["start"]
    shots_out[-1]["display_end"] = round(t, 3)
    shots_out[0]["start_display"] = 0.0

    tl = {"episode": ep_id, "kind": "shorts" if shorts else "long", "duration": round(t, 3),
          "audio": str(wav_out.relative_to(d)), "shots": shots_out, "cues": cues_out, "events": events,
          "note": "仮音声（Open JTalk）による尺。本番音声差し替え後に再計算すること。"}
    (d / "script" / f"{tag}_timeline_v1.json").write_text(json.dumps(tl, ensure_ascii=False, indent=2), encoding="utf-8")

    sub = d / "subtitles"
    sub.mkdir(exist_ok=True)
    srt, vtt = [], ["WEBVTT", ""]
    for i, c in enumerate(cues_out, 1):
        body = "\n".join(c["lines"])
        srt += [str(i), f"{ts(c['start'])} --> {ts(c['end'])}", body, ""]
        vtt += [f"{ts(c['start'], '.')} --> {ts(c['end'], '.')}", body, ""]
    (sub / f"{tag}_v1.srt").write_text("\n".join(srt), encoding="utf-8")
    (sub / f"{tag}_v1.vtt").write_text("\n".join(vtt), encoding="utf-8")

    by = {}
    for s in shots_out:
        k = "akari_cut" if s["visual"].startswith("cut:akari") else "ooka_m_cut" if s["visual"].startswith("cut:ooka") else "graphics"
        by[k] = by.get(k, 0) + s["display_end"] - s.get("start_display", s["start"])
    print(f"{tag}: {t:.1f}s ({int(t // 60)}:{t % 60:04.1f})  cues={len(cues_out)}  shots={len(shots_out)}")
    for k, v in by.items():
        print(f"  {k:10s} {v:6.1f}s  {100 * v / t:5.1f}%")
    return tl


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--shorts", action="store_true")
    ap.add_argument("--use-existing", action="store_true", help="既存の文単位wavを使う（本番音声差し替え時）")
    a = ap.parse_args(argv)
    build(a.episode, a.shorts, a.use_existing)


if __name__ == "__main__":
    main()
