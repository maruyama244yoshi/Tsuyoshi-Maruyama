# 制作マスター台帳（声・画像・動画エンジン・設定）

機械可読版：`brand/PRODUCTION_MASTERS.json`（制作シートの生成に使う）。

音声は読み間違い防止用のひらがな原稿、字幕は通常の漢字・数字表記（完全に分離）。

**音声形式（2026-09-26 改定）**：HeyGen 原本を正本とする。拡張子が.wavで中身がMP3でも原本はそのまま保存し、編集用のみ 48kHz/24bit PCM WAV へ1回変換してよい。旧「MP3経由禁止」は「不要な多重圧縮禁止」と読み替える。音声がおかしい場合も **Voice・Speed・Pitch は変更禁止**。読み上げ原稿のひらがな・句読点・分割位置で調整する。

指示書 2026-09-25 §11・§28 による。**正式決定後は勝手に変更しない。変更は v2 として比較テストを行い、オーナー承認後に切り替える。**

| マスター | 内容 | 状態 | 決定日 | 根拠（採点・比較） |
|---|---|---|---|---|
| AKARI_VOICE_MASTER_v1 | 燈の声：**Jhenny**（HeyGen voice_id `9530fac2d1f148f8b57b51b783b0df13`、**速度 1.0**（2026-09-25 に 0.90 から変更）、Japanese、元候補 AKARI_VOICE_C） | ✅ 正式採用 | 2026-09-25 | 指示書 2026-09-25（第2稿 完成実行指示書） |
| M_VOICE_MASTER_v1 | 大家Mの声：**Satoshi**（HeyGen voice_id `662e1397965c484e8f65fa58c77effde`、**速度 1.0**（2026-09-25 に 0.95 から変更）、Japanese、元候補 M_VOICE_A） | ✅ 正式採用 | 2026-09-25 | 同上 |
| AKARI_TALKING_BASE_16x9_v1 ／ _9x16_v1 ／ AKARI_DESK_BASE_v1 | 燈の基本画像（`brand/akari/talking_base/`） | ✅ 正式採用 | 2026-09-25 | 同上 |
| OOKA_M_TALKING_BASE_16x9_v1 | 大家Mの基本画像（`brand/ooka_m/talking_base/`） | ✅ 正式採用 | 2026-09-25 | 同上 |
| HeyGen アバター（燈） | 名前 **AKARI_MASTER_v1**（画像 AKARI_TALKING_BASE_16x9_v1、Photo Avatar 等） | 手動登録待ち（avatar_id 未記録） | — | 指示書 2026-09-25「HeyGen手動登録後の生成フロー」 |
| HeyGen アバター（大家M） | 名前 **OOKA_M_MASTER_v1**（画像 OOKA_M_TALKING_BASE_16x9_v1）。本人登録（デジタルツイン）ではない | 手動登録待ち（avatar_id 未記録） | — | 同上 |
| TALKING_VIDEO_ENGINE_v1 | 話している動画の生成ツール（第一候補：HeyGen） | 未決定（heygen_akari / heygen_ooka_m のテスト待ち） | — | `youtube/akari_news/avatar_tests/review/video_scores.csv`・`compare_*.json` |
| TALKING_VIDEO_SETTINGS_v1 | 採用ツールの設定（予定：動き Minimal/Subtle、表情 Low、頭 Minimal、手 Minimal、視線 Camera） | 未決定（テストで確定） | — | `youtube/akari_news/avatar_tests/review/settings_log.md` |

## 決定時に記録すること

- 声：サービス名、声の名前とID、ライブラリか Voice Design か、モデル、速度、Stability、Style、Speaker Boost、出力形式（WAV → 48kHz/24bit）
- 動画：Avatar方式、Avatar ID、Voice ID、Speed、Motion、Expression、Head Movement、Hand Movement、Eye Contact、Resolution、Aspect Ratio、生成日、プラン名（`avatar_tests/review/settings_log.md` の表）
- 規約：`avatar_tests/review/commercial_terms_check.md` の確認日とURL

## API自動化に進む条件（指示書 §25）

1. 燈の声が固定 2. 大家Mの声が固定 3. 動画ツールが固定 4. 動き設定が固定 5. キャラ崩れ率が低い 6. 5本以上同品質で再現 7. 人間の修正が少ない

満たすまでは画面操作（UI）で制作する。公開は当面、自動化しない。
