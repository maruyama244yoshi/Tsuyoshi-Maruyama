# Tsuyoshi-Maruyama

## 燈の不動産ニュース（AKARI REAL ESTATE NEWS）

YouTube「燈の不動産ニュース｜現役会社員大家の視点」の制作リポジトリ。
**不動産ニュースを、大家の経営判断に変える。**

- 設計書：[`docs/PHASE1_DESIGN.md`](docs/PHASE1_DESIGN.md)
- 燈 キャラクター仕様：[`brand/akari/AKARI_MASTER_v1.0.md`](brand/akari/AKARI_MASTER_v1.0.md)
- 大家M キャラクター仕様：[`brand/ooka_m/OOKA_M_MASTER_v1.0.md`](brand/ooka_m/OOKA_M_MASTER_v1.0.md)
- NEWS YAGURA 連携：[`docs/NEWS_YAGURA_INTEGRATION.md`](docs/NEWS_YAGURA_INTEGRATION.md)
- 第1回レビュー：[`youtube/akari_news/episode_001/review/REVIEW_SUMMARY.md`](youtube/akari_news/episode_001/review/REVIEW_SUMMARY.md)

```bash
pip install pillow numpy imageio-ffmpeg
sudo apt-get install fonts-noto-cjk open-jtalk open-jtalk-mecab-naist-jdic hts-voice-nitech-jp-atr503-m001
python3 -m tools.akari_news.build_episode episode_001
python3 -m tools.akari_news.graphics episode_001 --logo
python3 -m tools.akari_news.timeline episode_001 && python3 -m tools.akari_news.timeline episode_001 --shorts
python3 -m tools.akari_news.thumbnail episode_001
python3 -m tools.akari_news.video episode_001 && python3 -m tools.akari_news.video episode_001 --shorts
```

公開は必ず人間の最終確認後に YouTube Studio で手動で行う（自動公開はしない）。
