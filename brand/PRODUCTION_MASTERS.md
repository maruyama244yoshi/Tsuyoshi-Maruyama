# 制作マスター台帳（声・画像・動画エンジン・設定）

機械可読版：`brand/PRODUCTION_MASTERS.json`（制作シートの生成に使う）。

音声生成時のみ「燈」→「あかり」。表示・字幕は「燈」のまま。音声の再生成が必要な場合も同一 voice_id・同一速度を維持する。

指示書 2026-09-25 §11・§28 による。**正式決定後は勝手に変更しない。変更は v2 として比較テストを行い、オーナー承認後に切り替える。**

| マスター | 内容 | 状態 | 決定日 | 根拠（採点・比較） |
|---|---|---|---|---|
| AKARI_VOICE_MASTER_v1 | 燈の声：**Jhenny**（HeyGen voice_id `9530fac2d1f148f8b57b51b783b0df13`、速度 0.90、Japanese、元候補 AKARI_VOICE_C） | ✅ 正式採用 | 2026-09-25 | 指示書 2026-09-25（第2稿 完成実行指示書） |
| M_VOICE_MASTER_v1 | 大家Mの声：**Satoshi**（HeyGen voice_id `662e1397965c484e8f65fa58c77effde`、速度 0.95、Japanese、元候補 M_VOICE_A） | ✅ 正式採用 | 2026-09-25 | 同上 |
| AKARI_TALKING_BASE_16x9_v1 ／ _9x16_v1 ／ AKARI_DESK_BASE_v1 | 燈の基本画像（`brand/akari/talking_base/`） | ✅ 正式採用 | 2026-09-25 | 同上 |
| OOKA_M_TALKING_BASE_16x9_v1 | 大家Mの基本画像（`brand/ooka_m/talking_base/`） | ✅ 正式採用 | 2026-09-25 | 同上 |
| TALKING_VIDEO_ENGINE_v1 | 話している動画の生成ツール（第一候補：HeyGen） | 未決定（heygen_akari / heygen_ooka_m のテスト待ち） | — | `youtube/akari_news/avatar_tests/review/video_scores.csv`・`compare_*.json` |
| TALKING_VIDEO_SETTINGS_v1 | 採用ツールの設定（予定：動き Minimal/Subtle、表情 Low、頭 Minimal、手 Minimal、視線 Camera） | 未決定（テストで確定） | — | `youtube/akari_news/avatar_tests/review/settings_log.md` |

## 決定時に記録すること

- 声：サービス名、声の名前とID、ライブラリか Voice Design か、モデル、速度、Stability、Style、Speaker Boost、出力形式（WAV → 48kHz/24bit）
- 動画：ツール名、プラン、アバター方式、全設定値、使用した基本画像（`avatar_tests/base_stills/`）
- 規約：`avatar_tests/review/commercial_terms_check.md` の確認日とURL

## API自動化に進む条件（指示書 §25）

1. 燈の声が固定 2. 大家Mの声が固定 3. 動画ツールが固定 4. 動き設定が固定 5. キャラ崩れ率が低い 6. 5本以上同品質で再現 7. 人間の修正が少ない

満たすまでは画面操作（UI）で制作する。公開は当面、自動化しない。
