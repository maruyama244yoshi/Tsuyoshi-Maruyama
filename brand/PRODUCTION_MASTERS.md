# 制作マスター台帳（声・動画エンジン・設定）

指示書 2026-09-25 §11・§28 による。**正式決定後は勝手に変更しない。変更は v2 として比較テストを行い、オーナー承認後に切り替える。**

| マスター | 内容 | 状態 | 決定日 | 根拠（採点・比較） |
|---|---|---|---|---|
| AKARI_VOICE_MASTER_v1 | 燈の声（ElevenLabs の声・モデル・速度・Stability・Style・Speaker Boost） | 未決定（候補 AKARI_VOICE_A/B/C を比較中） | — | `youtube/akari_news/avatar_tests/review/voice_scores.csv` |
| M_VOICE_MASTER_v1 | 大家Mの声（同上） | 未決定（候補 M_VOICE_A/B を比較中） | — | 同上 |
| TALKING_VIDEO_ENGINE_v1 | 話している動画の生成ツール（HeyGen / Hedra） | 未決定 | — | `youtube/akari_news/avatar_tests/review/video_scores.csv`・`compare_*.json` |
| TALKING_VIDEO_SETTINGS_v1 | 採用ツールの設定（アバター方式・動き・表情・頭・手・視線） | 未決定 | — | `youtube/akari_news/avatar_tests/review/settings_log.md` |

## 決定時に記録すること

- 声：サービス名、声の名前とID、ライブラリか Voice Design か、モデル、速度、Stability、Style、Speaker Boost、出力形式（WAV → 48kHz/24bit）
- 動画：ツール名、プラン、アバター方式、全設定値、使用した基本画像（`avatar_tests/base_stills/`）
- 規約：`avatar_tests/review/commercial_terms_check.md` の確認日とURL

## API自動化に進む条件（指示書 §25）

1. 燈の声が固定 2. 大家Mの声が固定 3. 動画ツールが固定 4. 動き設定が固定 5. キャラ崩れ率が低い 6. 5本以上同品質で再現 7. 人間の修正が少ない

満たすまでは画面操作（UI）で制作する。公開は当面、自動化しない。
