"""ニュース重要度スコア（news_score, 100点満点）と判定。指示書 §18 の配点を固定実装。

  python3 -m tools.akari_news.score path/to/news_item.json
"""
import json
import sys

WEIGHTS = {"landlord_impact": 30, "market_impact": 20, "urgency": 15,
           "data_reliability": 15, "search_demand": 10, "video_fit": 10}
BANDS = [(85, "breaking_candidate", "速報候補"), (70, "video_candidate", "動画候補"),
         (50, "news_candidate", "ニュース候補"), (0, "archive_only", "保存のみ")]


def news_score(sub: dict) -> int:
    """sub: 各項目 0.0〜1.0 の評価値（NEWS YAGURA 側で付与）。"""
    missing = set(WEIGHTS) - set(sub)
    if missing:
        raise ValueError(f"score項目が不足: {sorted(missing)}")
    for k, v in sub.items():
        if k in WEIGHTS and not 0 <= v <= 1:
            raise ValueError(f"{k} は 0〜1: {v}")
    return round(sum(WEIGHTS[k] * sub[k] for k in WEIGHTS))


def judge(score: int):
    for lo, code, ja in BANDS:
        if score >= lo:
            return code, ja


def main():
    item = json.load(open(sys.argv[1], encoding="utf-8"))
    s = news_score(item["score_breakdown"])
    code, ja = judge(s)
    print(json.dumps({"news_id": item.get("news_id"), "news_score": s, "judgement": code, "judgement_ja": ja,
                      "generate_script": s >= 70}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
