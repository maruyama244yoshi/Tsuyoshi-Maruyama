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
import json

from .common import ROOT, episode_dir, load_json


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
    masters = load_json(ROOT / "brand" / "PRODUCTION_MASTERS.json")
    clips, voices, cmap = [], [], {}
    counters = {}

    def next_name(prefix):
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}_{counters[prefix]:03}"

    for sid, title, shots in groups:
        for i, s in enumerate(shots):
            shot_id = f"{sid}_{i:02}_{s['speaker']}"
            talk = s["visual"].startswith("talk:")
            pre = ("AKARI" if s["speaker"] == "akari" else "M") + ("" if talk else "_VO")
            base = next_name(pre)
            cmap[shot_id] = base
            vm = masters["voices"]["akari" if s["speaker"] == "akari" else "ooka_m"]
            row = {"id": base, "shot": shot_id, "scene": f"{sid} {title}",
                   "speaker": "燈" if s["speaker"] == "akari" else "大家M",
                   "text": s["text"], "tts_text": s["text"].replace("燈", "あかり"),
                   "reading_if_misread": tts_text(s["text"]), "voice": vm["name"], "voice_id": vm["heygen_voice_id"],
                   "speed": vm["speed"], "est_sec": round(est.get((sid, i), 0), 1)}
            voices.append(dict(row, file=f"voice/final/{base}.wav"))
            if talk:
                c = cuts.get(s["visual"][5:], {})
                img = masters["images"][c.get("image", "AKARI_TALKING_BASE_16x9_v1" if s["speaker"] == "akari" else "OOKA_M_TALKING_BASE_16x9_v1")]
                clips.append(dict(row, file=f"clips/{base}.mp4", cut=s["visual"][5:], video_cut=c.get("video_cut", ""),
                                  camera=c.get("camera", ""), outfit=c.get("outfit", ""), desc=c.get("desc", ""),
                                  aspect="9:16" if c.get("vertical") else "16:9", image=img["file"],
                                  image_id=c.get("image", ""), settings=masters["talking_video_settings"]["summary"]))
    out = d / "production"
    out.mkdir(exist_ok=True)
    (out / f"clip_map_{ver}.json").write_text(json.dumps(cmap, ensure_ascii=False, indent=2), encoding="utf-8")
    cf = ["id", "file", "shot", "scene", "speaker", "image_id", "image", "aspect", "voice", "voice_id", "speed",
          "settings", "est_sec", "text", "tts_text", "reading_if_misread"]
    with open(out / f"clip_manifest_{ver}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, cf, extrasaction="ignore"); w.writeheader(); w.writerows(clips)
    vf = ["id", "file", "shot", "scene", "speaker", "voice", "voice_id", "speed", "est_sec", "text", "tts_text",
          "reading_if_misread"]
    with open(out / f"voice_manifest_{ver}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, vf, extrasaction="ignore"); w.writeheader(); w.writerows(voices)
    vo = [v for v in voices if "_VO_" in v["id"]]
    L = [f"# {a.episode} HeyGen 制作シート（{ver}）", "",
         f"- 話しているカット：{len(clips)}本（燈 {sum(c['speaker'] == '燈' for c in clips)} / 大家M {sum(c['speaker'] == '大家M' for c in clips)}）",
         f"- 声だけのパート（図表の上に流れるナレーション）：{len(vo)}本",
         f"- 合計尺（目安）：カット {sum(c['est_sec'] for c in clips):.0f}秒 ／ 声だけ {sum(v['est_sec'] for v in vo):.0f}秒（仮音声での目安。本番音声の長さが正）",
         "- 共通設定：" + masters["talking_video_settings"]["summary"],
         "- 声：燈＝" + masters["voices"]["akari"]["name"] + f"（voice_id {masters['voices']['akari']['heygen_voice_id']}、速度 {masters['voices']['akari']['speed']}）"
         + "／大家M＝" + masters["voices"]["ooka_m"]["name"] + f"（voice_id {masters['voices']['ooka_m']['heygen_voice_id']}、速度 {masters['voices']['ooka_m']['speed']}）",
         "- 入力する文章は「HeyGenに入れる文章」列（燈→あかり のみ置換）。読み間違えたときだけ「誤読時の読み」列を使う。",
         "- 字幕・BGM・編集は付けずに書き出す。1発話＝1本。ファイル名は id と完全一致させる。",
         "- 置き場所：話しているカット → `clips/<id>.mp4`、声だけ → `voice/final/<id>.wav`（mp4 のままでも可。音声を取り出して使う）", "",
         "## 話しているカット", "",
         "| id | 話者 | 基本画像 | 比率 | 目安秒 | HeyGenに入れる文章 |", "|---|---|---|---|---|---|"]
    for c in clips:
        L.append(f"| {c['id']} | {c['speaker']} | {c['image_id']} | {c['aspect']} | {c['est_sec']} | {c['tts_text']} |")
    L += ["", "## 声だけのパート（映像は使わない。音声だけ書き出す）", "",
          "| id | 話者 | 目安秒 | HeyGenに入れる文章 |", "|---|---|---|---|"]
    for v in vo:
        L.append(f"| {v['id']} | {v['speaker']} | {v['est_sec']} | {v['tts_text']} |")
    (out / f"clip_manifest_{ver}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"clips={len(clips)} voices={len(voices)} -> {out}")


if __name__ == "__main__":
    main()
