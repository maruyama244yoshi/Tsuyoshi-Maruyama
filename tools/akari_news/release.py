"""inbox の素材から、本編・Shorts・報告書を一括で書き出す。

  python3 -m tools.akari_news.release episode_001 --version v3 [--notes production/changes_v3.md] [--skip-render]

手順：
  1. 取り込み：inbox/*.mp4 → clips/、inbox/*_VO_*.wav → voice/final/（48kHz/24bit PCM へ1回だけ変換。原本は inbox に保持）
  2. 素材検査：qa_assets（review/asset_qa.json・asset_contact_sheet.png）
  3. タイミング：本編と shorts_list の全 Shorts
  4. 書き出し：output/EP01_MASTER_<ver>.mp4、EP01_SHORT_0N_<ver>.mp4、同名 .srt
  5. 報告書：output/EP01_ASSET_MANIFEST.json、EP01_QA_REPORT.md、EP01_EDIT_LOG.md

判定ルール（QA）：
  - 縦型素材なのに横長映像が余白付きで入っている → 要再生成
  - 声だけの音声で話速 3.0 文字/秒 未満 → 要確認
  - 技術的な問題（デコードエラー・解像度・音ズレ等） → 要確認
  - review/manual_review.json の目視判定（手振り等）を反映
  - 発音はすべて「未聴取」（人間が確認）
音声形式：HeyGen 原本を正本とし、拡張子が.wavで中身がMP3でも原本はそのまま保存（不要な多重圧縮はしない）。
"""
import argparse
import datetime
import json
import shutil
from pathlib import Path

from .audio_prep import convert
from .common import episode_dir, load_json

PRON = ["燈＝あかり", "大家＝おおや", "DSCR＝でぃーえすしーあーる", "1.25％＝いってんにーごぱーせんと",
        "2.00％＝にてんぜろぜろぱーせんと", "2.25％＝にてんにーごぱーせんと"]


def ingest(d):
    inbox = d / "inbox"
    (d / "clips").mkdir(exist_ok=True)
    (d / "voice" / "final").mkdir(parents=True, exist_ok=True)
    for f in sorted(inbox.glob("*.mp4")):
        shutil.copy2(f, d / "clips" / f.name)
    reps = [convert(f, d / "voice" / "final") for f in sorted(inbox.glob("*_VO_*.wav"))]
    (d / "review" / "vo_conversion_report.json").write_text(json.dumps(reps, ensure_ascii=False, indent=2), encoding="utf-8")


def judge(d, qa, boxes):
    manual = {}
    mp = d / "review" / "manual_review.json"
    if mp.exists():
        manual = load_json(mp)
    out = {}
    for aid, r in qa.items():
        j, notes = "OK", []
        if r["kind"] == "voiceover":
            notes.append(f"原本 {r.get('acodec')} {r.get('sample_rate')}Hz {r.get('channels')}（HeyGen原本を正本として保存。編集用に48kHz/24bit PCMへ1回だけ変換）")
            if (r.get("chars_per_sec") or 9) < 3.0:
                j = "要確認"
                notes.append(f"話速が遅い（{r['chars_per_sec']}文字/秒）。読点ごとの間が多く途切れて聞こえる可能性")
        if r.get("long_silences"):
            inner = [s for s in r["long_silences"] if s[0] > 0.3 and (r["duration"] or 0) - s[1] > 0.3]
            if inner:
                notes.append(f"途中に0.8秒以上の無音 {inner}")
        if aid in boxes and boxes[aid]:
            j = "要再生成"
            notes.append(f"縦型画面の中に横長映像が余白付きで入っている（映像部分 {boxes[aid][2]}x{boxes[aid][3]}）。映像部分を切り出して使用")
        tech = [i for i in r.get("issues", []) if not i.startswith("話速")]
        if tech:
            j = "要確認" if j == "OK" else j
            notes += tech
        if aid in manual:
            m = manual[aid]
            if m.get("judgement"):
                order = {"OK": 0, "要確認": 1, "要再生成": 2}
                j = m["judgement"] if order[m["judgement"]] >= order[j] else j
            notes += m.get("notes", [])
        out[aid] = (j, notes)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--version", required=True)
    ap.add_argument("--notes", help="この版での変更点（Markdown、編集ログに挿入）")
    ap.add_argument("--skip-render", action="store_true")
    a = ap.parse_args(argv)
    d = episode_dir(a.episode)
    O = d / "output"
    O.mkdir(exist_ok=True)
    ver = a.version
    from . import qa_assets, timeline, video
    from .timeline import screen_ratio

    ingest(d)
    qa_assets.main([a.episode])
    qa = {r["id"]: r for r in load_json(d / "review" / "asset_qa.json")}
    # 縦型素材の余白検出
    clips_manifest = {r["id"]: r for r in __import__("csv").DictReader(
        open(d / "production" / "clip_manifest_v2.csv", encoding="utf-8-sig"))}
    boxes = {aid: video.content_box(d / "inbox" / f"{aid}.mp4") for aid, c in clips_manifest.items()
             if c.get("aspect") == "9:16" and (d / "inbox" / f"{aid}.mp4").exists()}

    ep = load_json(d / "script" / f"{a.episode}.json")
    tl_main = timeline.build(a.episode)
    tls = {"master": tl_main}
    names = {"master": f"EP01_MASTER_{ver}"}
    for i, _ in enumerate(ep.get("shorts_list", []), 1):
        tls[f"short{i:02}"] = timeline.build(a.episode, short_no=i)
        names[f"short{i:02}"] = f"EP01_SHORT_{i:02}_{ver}"
    if not a.skip_render:
        bgm = str(d / "voice" / "bgm_auto.wav")
        if not Path(bgm).exists():
            from .bgm import main as bgm_main
            bgm_main([bgm, "--sec", "64"])
        video.build(a.episode, False, None, bgm, None, str(O / f"{names['master']}.mp4"))
        for i, _ in enumerate(ep.get("shorts_list", []), 1):
            video.build(a.episode, True, None, bgm, i, str(O / f"{names[f'short{i:02}']}.mp4"))
    sv = ep.get("script_version", "v2")
    shutil.copy(d / "subtitles" / f"{a.episode}_{sv}.srt", O / f"{names['master']}.srt")
    for i, _ in enumerate(ep.get("shorts_list", []), 1):
        shutil.copy(d / "subtitles" / f"{a.episode}_short{i:02}_{sv}.srt", O / f"{names[f'short{i:02}']}.srt")

    J = judge(d, qa, boxes)
    used = {}
    for k, t in tls.items():
        for s in t["shots"]:
            used.setdefault(s["asset"], []).append(names[k])
    ratio = {k: round(v / tl_main["duration"] * 100, 1) for k, v in screen_ratio(tl_main).items()}
    src = load_json(d / "inbox" / "AKARI_NEWS_EP01_manifest.json")
    vid = {x["id"]: x["heygen_video_id"] for x in src.get("talking_videos", [])}
    man = {"episode": "EP01", "version": ver, "generated": datetime.date.today().isoformat(),
           "voice": {"akari": {"name": "Jhenny", "voice_id": "9530fac2d1f148f8b57b51b783b0df13", "speed": 1.0},
                     "ooka_m": {"name": "Satoshi", "voice_id": "662e1397965c484e8f65fa58c77effde", "speed": 1.0}},
           "source_manifest": "inbox/AKARI_NEWS_EP01_manifest.json",
           "outputs": {f"{names[k]}.mp4": {"duration_sec": t["duration"]} for k, t in tls.items()},
           "master_screen_ratio_pct": ratio, "talking_videos": [], "voiceovers": [], "graphics": {},
           "broll": [], "broll_note": "実写B-rollは今回必須としない（図表主体）",
           "bgm": "自作BGM（tools/akari_news/bgm.py、権利フリー）", "unused_assets": []}
    for aid, r in qa.items():
        e = {"id": aid, "file": f"inbox/{r['file']}", "used_in": used.get(aid, []), "judgement": J[aid][0],
             "notes": J[aid][1], "duration_sec": round(r.get("duration") or 0, 2)}
        if r["kind"] == "talking":
            e.update(heygen_video_id=vid.get(aid), resolution=f"{r.get('width')}x{r.get('height')}", fps=r.get("fps"))
            man["talking_videos"].append(e)
        else:
            e.update(source_codec=r.get("acodec"), source_rate=r.get("sample_rate"),
                     edit_file=f"voice/final/{aid}.wav（48kHz/24bit PCM、原本から再生成可能）")
            man["voiceovers"].append(e)
        if not used.get(aid):
            man["unused_assets"].append(aid)
    for k, t in tls.items():
        for s in t["shots"]:
            if s["visual"].startswith(("gfx:", "vgfx:")):
                man["graphics"].setdefault(s["visual"].split(":")[1], set()).add(names[k])
        for ev in t["events"]:
            man["graphics"].setdefault(ev["visual"].split(":")[1], set()).add(names[k])
    man["graphics"] = {k: sorted(v) for k, v in man["graphics"].items()}
    (O / "EP01_ASSET_MANIFEST.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")

    cnt = {j: sum(1 for x in J.values() if x[0] == j) for j in ("OK", "要確認", "要再生成")}
    L = [f"# EP01 QA_REPORT（{ver}）", "",
         f"作成：{datetime.date.today().isoformat()}　検査：`tools/akari_news/qa_assets.py`（全フレーム・全音声をデコード）＋代表フレームの目視（`review/asset_contact_sheet.png`）", "",
         "**発音は機械で判定できないため全素材「未聴取」。人間確認の対象：" + "／".join(PRON) + "。問題があれば追加再生成候補。**", "",
         f"判定：OK {cnt['OK']}本／要確認 {cnt['要確認']}本／要再生成 {cnt['要再生成']}本（再生成はしていない）", "",
         "## 話している動画", "", "| 素材ID | 再生可否 | 発音 | 口パク | 目線 | 表情・動き | 画質 | 音量 | 使用可否 | 判定 | 備考 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    manual = load_json(d / "review" / "manual_review.json") if (d / "review" / "manual_review.json").exists() else {}
    for aid, r in qa.items():
        if r["kind"] != "talking":
            continue
        j, n = J[aid]
        mv = manual.get(aid, {})
        L.append(f"| {aid} | {'○' if r.get('exists') else '×'} | 未聴取 | 映像と音声の尺差 {r.get('av_duration_diff')}秒 | "
                 f"{mv.get('gaze', 'カメラ目線')} | {mv.get('expression', '自然')} | {r.get('width')}x{r.get('height')} {r.get('fps') or 0:.0f}fps | "
                 f"{r.get('lufs')} LUFS | {'○（切り出し）' if boxes.get(aid) else '○'} | **{j}** | {'<br>'.join(n) or '—'} |")
    L += ["", "## 声だけの音声", "", "| 素材ID | 再生可否 | 発音 | 原本形式 | 尺 | 話速 | 音量 | 使用可否 | 判定 | 備考 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for aid, r in qa.items():
        if r["kind"] != "voiceover":
            continue
        j, n = J[aid]
        L.append(f"| {aid} | {'○' if r.get('exists') else '×'} | 未聴取 | {r.get('acodec')} {r.get('sample_rate')}Hz | "
                 f"{(r.get('duration') or 0):.1f}秒 | {r.get('chars_per_sec')}文字/秒 | {r.get('lufs')} LUFS | ○ | **{j}** | {'<br>'.join(n)} |")
    L += ["", "## 成果物", "", "| 成果物 | 尺 | 備考 |", "|---|---|---|",
          f"| {names['master']}.mp4 | {int(tl_main['duration'] // 60)}分{tl_main['duration'] % 60:.0f}秒 | 燈 {ratio['akari']}％／大家M {ratio['ooka_m']}％／図表 {ratio['graphics']}％ |"]
    for k, t in tls.items():
        if k != "master":
            L.append(f"| {names[k]}.mp4 | {t['duration']:.1f}秒 | " + "＋".join(s["asset"] for s in t["shots"]) + " |")
    (O / "EP01_QA_REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    rows = []
    for s in tl_main["shots"]:
        m, sec = divmod(s["start"], 60)
        rows.append(f"| {int(m)}:{sec:04.1f} | {s['scene']} {s['scene_title']} | {s['asset']} | {s['visual']} | "
                    f"{s['text'][:34]}{'…' if len(s['text']) > 34 else ''} |")
    notes = (d / a.notes).read_text(encoding="utf-8") if a.notes else ""
    E = [f"# EP01 編集ログ（{ver}）", "", notes, "", "## 共通ルール", "",
         "- Voice（Jhenny／Satoshi）・Speed 1.0・Pitch は変更しない。音声の速度変更・無音カットはしない",
         "- 話している動画は動画内の音声をそのまま使用（口パクと同期）。声だけの音声は図表の上にのみ配置し、重ねない",
         "- 字幕は通常表記。重要語を金色で強調。AKARI_VO_015 は修正版＋注記表示",
         "- 名前表示：燈（あかり）／AI不動産ニュースキャスター、現役会社員大家M（実名なし）",
         "- BGM は自作。声のある間は自動で下げる。完成ファイルは -16 LUFS、48kHz ステレオ", "",
         "## 尺と比率", "",
         f"- 本編 {int(tl_main['duration'] // 60)}分{tl_main['duration'] % 60:.0f}秒、燈 {ratio['akari']}％／大家M {ratio['ooka_m']}％／図表 {ratio['graphics']}％", "",
         "## タイムライン（本編）", "", "| 開始 | シーン | 素材 | 画面 | セリフ |", "|---|---|---|---|---|", *rows]
    (O / "EP01_EDIT_LOG.md").write_text("\n".join(E) + "\n", encoding="utf-8")
    print(f"done {ver}: master {tl_main['duration']:.1f}s ratio {ratio} QA {cnt}")


if __name__ == "__main__":
    main()
