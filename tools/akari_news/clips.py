"""話しているカット（口パク動画）と本番音声の発注リストを作る。

  python3 -m tools.akari_news.clips episode_001

出力: episode_XXX/production/
  clip_manifest_<ver>.csv / .md  … 作る動画クリップ（1発話＝1クリップ）と、そのセリフ・カット種別
  voice_manifest_<ver>.csv       … 本番TTSで作る音声（全発話。話しているカットの音声もここから作る）

納品ファイルの置き場所（このファイル名で置けば timeline / video が自動で使う）:
  clips/<scene>_<nn>_<speaker>.mp4        話しているカット（音声入り・口パク同期済み）
  voice/final/<scene>_<nn>_<speaker>.wav  本番音声（48kHz。話しているカット以外の発話）
"""
import argparse
import csv

from .build_episode import tts_text
from .common import episode_dir, load_json


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    a = ap.parse_args(argv)
    d = episode_dir(a.episode)
    ep = load_json(d / "script" / f"{a.episode}.json")
    ver = ep.get("script_version", "v1")
    cuts = ep.get("talk_cuts", {})
    est = {}
    try:
        for s in load_json(d / "script" / f"{a.episode}_timeline_{ver}.json")["shots"]:
            est[(s["scene"], s["index"])] = s["end"] - s["start"]
        for s in load_json(d / "script" / f"{a.episode}_shorts_timeline_{ver}.json")["shots"]:
            est[("SHORTS", s["index"])] = s["end"] - s["start"]
    except FileNotFoundError:
        pass
    groups = [(sc["id"], sc["title"], sc["shots"]) for sc in ep["scenes"]]
    groups.append(("SHORTS", "Shorts", ep["shorts"]["shots"]))
    clips, voices = [], []
    for sid, title, shots in groups:
        for i, s in enumerate(shots):
            base = f"{sid}_{i:02}_{s['speaker']}"
            row = {"id": base, "scene": f"{sid} {title}", "speaker": "燈" if s["speaker"] == "akari" else "大家M",
                   "text": s["text"], "tts_reading": tts_text(s["text"]), "est_sec": round(est.get((sid, i), 0), 1)}
            voices.append(dict(row, file=f"voice/final/{base}.wav"))
            if s["visual"].startswith("talk:"):
                c = cuts.get(s["visual"][5:], {})
                clips.append(dict(row, file=f"clips/{base}.mp4", cut=s["visual"][5:], video_cut=c.get("video_cut", ""),
                                  camera=c.get("camera", ""), outfit=c.get("outfit", ""), desc=c.get("desc", ""),
                                  aspect="9:16" if c.get("vertical") else "16:9"))
    out = d / "production"
    out.mkdir(exist_ok=True)
    cf = ["id", "file", "scene", "speaker", "cut", "video_cut", "camera", "outfit", "aspect", "desc", "est_sec", "text", "tts_reading"]
    with open(out / f"clip_manifest_{ver}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, cf, extrasaction="ignore"); w.writeheader(); w.writerows(clips)
    vf = ["id", "file", "scene", "speaker", "est_sec", "text", "tts_reading"]
    with open(out / f"voice_manifest_{ver}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, vf, extrasaction="ignore"); w.writeheader(); w.writerows(voices)
    L = [f"# {a.episode} 話しているカット 発注リスト（{ver}）", "",
         f"- クリップ数：{len(clips)}（燈 {sum(c['speaker'] == '燈' for c in clips)} / 大家M {sum(c['speaker'] == '大家M' for c in clips)}）",
         f"- 合計尺（目安）：{sum(c['est_sec'] for c in clips):.0f}秒　※仮音声での目安。本番音声の長さが正",
         "- 作り方：本番音声（voice_manifest）を先に作り、その音声で口パク動画を作る（音声駆動）。",
         "- 置き場所：`clips/<id>.mp4`（音声入り）。置けば `timeline` → `video` で自動的に差し替わる。", "",
         "| id | 話者 | カット | 構図 | 比率 | 目安秒 | セリフ |", "|---|---|---|---|---|---|---|"]
    for c in clips:
        L.append(f"| {c['id']} | {c['speaker']} | {c['video_cut']} | {c['desc']} | {c['aspect']} | {c['est_sec']} | {c['text']} |")
    (out / f"clip_manifest_{ver}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"clips={len(clips)} voices={len(voices)} -> {out}")


if __name__ == "__main__":
    main()
