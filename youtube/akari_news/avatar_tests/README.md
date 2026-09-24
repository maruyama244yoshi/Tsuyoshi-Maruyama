# 燈・大家M 音声選定＋HeyGen/Hedra 比較テスト（指示書 2026-09-25）

目的：燈と大家Mの正式な声と、自然に話す動画の方式を決める。
進め方：**品質比較 → 方式決定 → 標準化 → API自動化**。今回は画面操作（UI）で作り、API自動化はしない（§24）。

## 進捗

| 工程 | 状態 |
|---|---|
| 0. 基本画像 | ✅ 2026-09-24 受領 → `base_stills/`。燈は仮採点24/25で採用（オーナー確認待ち）。大家Mは本人非類似の確認待ち |
| 1. 声の候補5本（燈3・大家M2） | 未着 → `voice_test/` |
| 2. 声の採点・決定 | 未 → `review/voice_scores.csv` |
| 3. 動画テスト（HeyGen/Hedra × 燈・大家M） | 未着 → `video_test/heygen/`・`video_test/hedra/` |
| 4. 動画の採点・方式決定 | 未 → `review/video_scores.csv` |
| 5. 規約確認 | 未 → `review/commercial_terms_check.md` |
| 6. 正式決定の記録 | 未 → `brand/PRODUCTION_MASTERS.md` |

## フォルダ

```
avatar_tests/
  base_stills/          基本画像（燈：正面・縦型・デスク／大家M：正面）
  test_lines.json       音声テスト原稿・動画テスト原稿・ElevenLabs設定の目安・ファイル名
  voice_test/           AKARI_VOICE_A/B/C.wav、M_VOICE_A/B.wav（WAVで。MP3経由は不可）
    48k/                受け入れ後の48kHz版（audio_prepが作る）
  video_test/heygen/    heygen_akari.mp4、heygen_ooka_m.mp4（任意：heygen_akari_vertical.mp4）
  video_test/hedra/     hedra_akari.mp4、hedra_ooka_m.mp4（任意：hedra_akari_vertical.mp4）
  review/
    voice_scores.csv            声の採点（7項目×5点＝35点）
    video_scores.csv            動画の採点（6項目×5点＝30点）
    commercial_terms_check.md   規約の確認記録（確認日とURL）
    settings_log.md             生成時の設定記録
    compare_*.mp4 / .json       HeyGen と Hedra の並列比較（compare_video が作る）
```

## 1. 声の候補を作る（ElevenLabs）

- 原稿：`test_lines.json` の `voice_test`（燈・大家Mとも**完全に同じ文章**で）
- 設定の目安
  - 燈：速度 0.88〜0.94／Stability 中（高すぎると棒読み）／Style 低〜中／Speaker Boost は自然さが良くなるときだけ ON
  - 大家M：速度 0.92〜0.98／感情 低〜中
  - モデルは Eleven v3 と Multilingual v2 を比べる
- 禁止：本人や著名人に似せる、ボイスクローン
- 書き出しは WAV。設定は `review/settings_log.md` に記録

受け入れ（48kHz / 24bit に統一、MP3は拒否、ラウドネス等を記録）：

```bash
python3 -m tools.akari_news.audio_prep youtube/akari_news/avatar_tests/voice_test/*.wav
```

## 2. 声を採点して決める（`review/voice_scores.csv`）

7項目×5点＝35点：人間らしさ／日本語のイントネーション／知性／柔らかさ／間／長時間聞けるか／見た目との一致。
**28点以上が採用候補**。点数に関係なく不採用：アニメ声、男性っぽい燈、棒読み、不自然な日本語、本人の声に似た大家M、聞き疲れする声。
決まったら `AKARI_VOICE_MASTER_v1`・`M_VOICE_MASTER_v1` として固定する。

## 3. 動画テストを作る（HeyGen / Hedra）

- **同じ音声（決まった声で作った動画テスト原稿）＋同じ基本画像**で、両ツールを作る（映像エンジンの差だけを比べる）
- 原稿：`test_lines.json` の `video_test`（10〜20秒）
- 設定はすべて控えめ：動き Subtle/Low、表情 Low、頭の動き Minimal、手の動き Minimal、視線はカメラ
- 字幕・BGM・編集は付けない

並列比較（尺と音声が同じかを自動チェック）：

```bash
python3 -m tools.akari_news.compare_video akari
python3 -m tools.akari_news.compare_video ooka_m
```

## 4. 動画を採点して方式を決める（`review/video_scores.csv`）

6項目×5点＝30点：同一人物性／口の自然さ／目線／表情／日本語との一致／ニュース番組らしさ。
**24点以上＝採用候補、20〜23点＝保留、19点以下＝不採用**。
点数に関係なく不採用：商用利用不可、燈が別人、大家Mが本人に似すぎ、頭が揺れすぎ、口が不自然、同期の大きなずれ、視線が頻繁に外れる、不自然な笑顔、不気味さ。
「動かない」より「**動きすぎる**」ほうを強く警戒する。

## 5. 決まったあと

1. `brand/PRODUCTION_MASTERS.md` に AKARI_VOICE_MASTER_v1／M_VOICE_MASTER_v1／TALKING_VIDEO_ENGINE_v1／TALKING_VIDEO_SETTINGS_v1 を記録（以後は勝手に変えない。変更は v2 として比較テスト）
2. 第1回の話しているカット24本＋本番音声を作る（発注リスト：`episode_001/production/`）
3. `clips/` と `voice/final/` に置き、`timeline` → `video --bgm` で第2稿を組む
