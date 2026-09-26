"""エピソード定義（script/<ep>.json）を検証し、台本・字幕用セグメントを生成する。

  python3 -m tools.akari_news.build_episode episode_001            # 検証＋台本md
  python3 -m tools.akari_news.build_episode episode_001 --check    # 検証のみ

検証内容:
  - 大家Mの発話は approved の comment_ref に紐づき、文面が approved_comment に含まれること
    （approved が無ければ停止：AIの下書き suggested_comment は台本に使わない）
  - 台本中の試算数値が loan.py の計算結果と一致すること
  - 煽り禁止ワードが含まれないこと
"""
import argparse
import re
import sys

from .common import AKARI, episode_dir, load_json
from .loan import annual_payment, man

SPEAKER_JA = {"akari": "燈", "ooka_m": "大家M"}

# 読み上げ用の読み（字幕表記はそのまま、TTSだけ置換）。長いものから順に置換する。
READINGS = {
    "1.25％": "いってんにーごパーセント",
    "1.0％": "いってんぜろパーセント",
    "2.00％": "にてんぜろぜろパーセント",
    "2.25％": "にてんにーごパーセント",
    "0.5％": "れいてんごパーセント",
    "1％": "いちパーセント",
    "0.25ポイント": "れいてんにーごポイント",
    "DSCR": "ディーエスシーアール",
    "大家M": "おおやエム",
    "燈": "あかり",
    "日銀": "にちぎん",
    "大家": "おおや",
    "1億円": "いちおくえん",
    "30年": "さんじゅうねん",
    "444万円": "よんひゃくよんじゅうよんまんえん",
    "459万円": "よんひゃくごじゅうきゅうまんえん",
    "15万円": "じゅうごまんえん",
    "9月18日": "くがつじゅうはちにち",
    "9月24日": "くがつにじゅうよっか",
    "借入": "かりいれ",
    "3つ": "みっつ",
    "2つ目": "ふたつめ",
    "3つ目": "みっつめ",
    "1つ目": "ひとつめ",
    "表面利回り": "ひょうめんりまわり",
    "数億円": "すうおくえん",
    "足元": "あしもと",
    "・": "、",
}


def tts_text(text):
    for k in sorted(READINGS, key=len, reverse=True):
        text = text.replace(k, READINGS[k])
    return text


def split_sentences(text):
    return [s for s in re.findall(r"[^。？！]+[。？！]?", text) if s.strip()]


def validate(ep):
    errors, warns = [], []
    comments = {c["id"]: c for c in ep.get("ooka_m_comments", [])}
    shots = [(sc["id"], s) for sc in ep["scenes"] for s in sc["shots"]]
    shots += [("SHORTS", s) for s in ep.get("shorts", {}).get("shots", [])]
    for sh in ep.get("shorts_list", []):
        shots += [(sh["id"], s) for s in sh["shots"]]
    for sid, s in shots:
        if s["speaker"] == "ooka_m":
            ref = s.get("comment_ref")
            c = comments.get(ref)
            if not c:
                errors.append(f"{sid}: 大家Mの発話に comment_ref がありません")
                continue
            if c.get("status") != "approved" or not c.get("approved_comment") or not c.get("approved_by"):
                errors.append(f"{sid}: {ref} が未承認です（approved_comment のみ台本に使用可）")
                continue
            for sent in split_sentences(s["text"]):
                if sent.rstrip("。") not in c["approved_comment"]:
                    errors.append(f"{sid}: 大家Mの文面が承認済みコメント{ref}に含まれません: {sent}")
    banned = load_json(AKARI / "AKARI_MASTER_v1.0.json")["thumbnail"]["banned_words"]
    alltext = "".join(s["text"] for _, s in shots) + ep.get("working_title", "")
    for w in banned:
        if w in alltext:
            errors.append(f"禁止ワード: {w}")
    sim = ep.get("simulation")
    if sim:
        a0 = annual_payment(sim["principal_yen"], 2.00, sim["years"])
        a1 = annual_payment(sim["principal_yen"], 2.25, sim["years"])
        expect = {f"{man(a0)}万円", f"{man(a1)}万円", f"{man(a1 - a0)}万円"}
        sim_text = "".join(s["text"] for _, s in shots if s.get("sim"))
        for e in expect:
            if e not in sim_text:
                errors.append(f"試算数値 {e} が台本にありません（loan.py と不一致の可能性）")
    for f in ep.get("facts", []):
        if f.get("verified") != "primary":
            warns.append(f"事実 {f['id']} は一次資料で未照合（{f.get('verified')}）: {f['claim']}")
    return errors, warns


def cues_for_shot(text, max_line=28):
    """字幕キュー（文単位、長文は分割）。各キューは最大2行。"""
    cues = []
    for sent in split_sentences(text):
        cues += cues_split(sent, max_line)
    return cues


BREAK_AFTER = "はがをにでともへや"


def best_break(text, max_line):
    """行分割位置：読点の後を最優先、次に助詞の後。中央に近い位置を選ぶ。"""
    mid = len(text) / 2
    cands = []
    for i in range(4, len(text) - 3):
        ch, nx = text[i - 1], text[i]
        if ch in "、。，？":
            pen = 0
        elif (ch in BREAK_AFTER and nx not in "、。ょゃゅっー" and not text[i - 2].isascii()
              and text[i:i + 2] not in ("いっ", "いう", "なく", "して", "する", "なる")):
            pen = 3
        else:
            continue
        a, b = i, len(text) - i
        if max(a, b) > max_line:
            pen += 50
        cands.append((abs(i - mid) + pen, i))
    return min(cands)[1] if cands else int(round(mid))


def wrap2(text, max_line=28):
    """1キューを最大2行に。読点・助詞の直後で、なるべく均等に折る。"""
    if len(text) <= max_line:
        return [text]
    i = best_break(text, max_line)
    return [text[:i], text[i:]]


def cues_split(sent, max_line=28):
    """2行に収まらない長文を、読点→助詞の順で区切って複数キューにする。"""
    if len(sent) <= max_line * 2:
        return [sent]
    i = best_break(sent, max_line * 2)
    return cues_split(sent[:i], max_line) + cues_split(sent[i:], max_line)


def render_markdown(ep):
    L = [f"# {ep['episode_id']} 台本 {ep['script_version']}", "",
         f"- タイトル（仮）：{ep['working_title']}", f"- テーマ：{ep['theme']}",
         f"- 目標尺：{ep['target_duration_sec'][0]}〜{ep['target_duration_sec'][1]}秒",
         f"- 燈：{ep['cast']['akari']['master']} / {ep['cast']['akari']['outfit']} / 基調 {ep['cast']['akari']['default_face']}",
         f"- 大家M：{ep['cast']['ooka_m']['master']} / {ep['cast']['ooka_m']['outfit']}", "",
         "> 大家Mの発話は承認済みコメント（approved_comment）のみ使用。", ""]
    for sc in ep["scenes"]:
        L += [f"## {sc['id']} {sc['title']}（計画 {sc['planned']}）", ""]
        if sc.get("jingle_before"):
            L += ["*（「大家の一手」ジングル）*", ""]
        for s in sc["shots"]:
            meta = [s["visual"]]
            if s.get("face"):
                meta.append(s["face"])
            if s.get("comment_ref"):
                meta.append(f"承認済み{s['comment_ref']}")
            if s.get("facts"):
                meta.append("事実:" + ",".join(s["facts"]))
            L += [f"**{SPEAKER_JA[s['speaker']]}**：{s['text']}  ", f"<sub>{' / '.join(meta)}</sub>", ""]
    L += ["---", "", "## Shorts版", ""]
    for s in ep["shorts"]["shots"]:
        L += [f"**{SPEAKER_JA[s['speaker']]}**：{s['text']}  ", f"<sub>{s['visual']}</sub>", ""]
    L += ["---", "", f"注記：{ep['simulation']['note']}", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    d = episode_dir(a.episode)
    ep = load_json(d / "script" / f"{a.episode}.json")
    errors, warns = validate(ep)
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    if errors:
        sys.exit(1)
    print("OK   検証通過")
    if a.check:
        return
    out = d / "script" / f"{a.episode}_script_{ep['script_version']}.md"
    out.write_text(render_markdown(ep), encoding="utf-8")
    print("wrote", out.relative_to(d.parents[2]))


if __name__ == "__main__":
    main()
