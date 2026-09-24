# 燈の不動産ニュース — Phase 1 設計書

作成：2026-09-24　／　対象：YouTube「燈の不動産ニュース｜現役会社員大家の視点」立ち上げ

> コンセプト：**不動産ニュースを、大家の経営判断に変える。**
> 最重要方針：本人の顔・本名・勤務先を出さない。公開は必ず人間承認後（自動公開しない）。
> 既存 YAGURA 等には一切書き込まない（読み取り専用の疎結合）。

---

## 1. Phase 1 成果物と状況

| # | 成果物 | 場所 | 状態 |
|---|---|---|---|
| ① | 燈 正式キャラクター設定 | `brand/akari/AKARI_MASTER_v1.0.md` / `.json` / `prompts/` | ✅ 作成 |
| ② | 大家M 正式キャラクター設定 | `brand/ooka_m/OOKA_M_MASTER_v1.0.md` / `.json` / `prompts/` | ✅ 作成（本人非類似の確認待ち） |
| ③ | チャンネルロゴ案 | `brand/logo/logo_main_on_dark.png` ほか、`icon_800.png` | ✅ たたき台 |
| ④ | YouTubeバナー案 | `brand/logo/youtube_banner_2560x1440_draft.png`（セーフエリア確認用あり） | ✅ たたき台 |
| ⑤ | 動画テンプレート | `youtube/akari_news/templates/` ＋ `tools/akari_news/` | ✅ |
| ⑥ | サムネイルテンプレート | `tools/akari_news/thumbnail.py`（3バリエーション） | ✅ |
| ⑦ | NEWS YAGURA 連携仕様 | `docs/NEWS_YAGURA_INTEGRATION.md` / `schemas/` | ✅ 仕様のみ（実接続はPhase 2） |
| ⑧ | 第1回動画の完成台本 | `youtube/akari_news/episode_001/script/` | ✅ ＋長尺・Shorts初稿動画 |

## 2. キャラクター仕様（要約）

| | 燈（あかり） | 現役会社員大家M |
|---|---|---|
| 役割 | メインキャスター：ニュース整理・事実・データ・一般的影響・まとめ | 実戦コメント：経営判断・「大家の一手」 |
| 見た目 | 実写寄り日本人女性、28〜32歳、ダークブラウンのセミロング、ネイビー等のジャケット | 40代男性AIアバター、黒フレーム眼鏡、ジャケット（**本人に寄せない**） |
| 声 | 落ち着いた女性AI音声、やや ゆっくり | 落ち着いた男性AI音声（本人の声は使わない） |
| 出演比率 | 30〜50％ | 10〜20％ |
| 固定化 | 基準画像 AKARI_REFERENCE_001＋プロンプト定義ファイル＋25点一致度判定 | 同左＋本人非類似チェック |
| 発言管理 | 固定フレーズ・煽らない・断定しない | **suggested → 本人承認 → approved のみ台本使用**（ツールで強制） |

## 3. 動画構成（基本フォーマット）

```
燈：オープニング → 本日のニュース → 何が起きたか（事実・データ）→ 大家への影響
大家M：実戦コメント → 「大家の一手」（20〜60秒、原則毎回）
燈：まとめ → CTA
```

| カテゴリ | 尺 | 本数 |
|---|---|---|
| A 今日の不動産ニュース | 3〜5分 | ニュース1〜3本 |
| B 不動産ニュース深掘り | 8〜15分 | 1テーマ |
| C 今週の大家ニュース | 週1 | 3〜5本 |
| D Shorts | 30〜60秒 | 長尺への導線 |

画面構成比の目安：燈 30〜50％ ／ 大家M 10〜20％ ／ 図表・チャート・写真・テロップ 30〜50％。
**AI量産動画にしない**：毎回、一次資料の事実整理・自社図表・数値比較・大家Mコメント・大家の一手のうち複数を必須とする。

## 4. ファイル構成

```
brand/
  akari/      AKARI_MASTER_v1.0.{md,json}, AKARI_*.json, prompts/*.txt, references/, CHANGELOG.md
  ooka_m/     OOKA_M_MASTER_v1.0.{md,json}, prompts/*.txt, references/, CHANGELOG.md
  logo/       ロゴ・アイコン・バナー（tools で再生成可能）
docs/         PHASE1_DESIGN.md, NEWS_YAGURA_INTEGRATION.md
schemas/      news_item.schema.json, script_package.schema.json, examples/
tools/akari_news/
  common.py          パス・フォント・ブランドカラー
  prompt_builder.py  画像生成プロンプト組み立て（定義ファイルから読む）
  loan.py            元利均等返済の試算（動画内の数値はここで算出）
  score.py           news_score 計算・判定
  build_episode.py   台本検証（大家M承認ゲート・数値照合・禁止ワード）→ 台本md
  timeline.py        ガイド音声合成 → タイムライン・SRT/VTT
  graphics.py        図表・キャラカット・縦型・ロゴ/バナー
  thumbnail.py       サムネイル
  video.py           長尺/Shorts の組み立て（ffmpeg）
youtube/akari_news/
  templates/         エピソード雛形・動画/サムネテンプレート説明
  episode_001/       script/ voice/ video/ graphics/ thumbnail/ shorts/ subtitles/ references/ review/
```

エピソードの**唯一の正**は `episode_XXX/script/episode_XXX.json`（シーン・発話・画面・事実・承認コメント・Shorts）。台本md・字幕・動画はすべてここから生成する。

## 5. 制作パイプライン（コマンド）

```bash
python3 -m tools.akari_news.build_episode episode_001          # 検証＋台本md（未承認の大家M発話があれば停止）
python3 -m tools.akari_news.graphics episode_001 [--logo]      # 図表・キャラカット
python3 -m tools.akari_news.timeline episode_001 [--shorts]    # ガイド音声・タイムライン・字幕
python3 -m tools.akari_news.thumbnail episode_001              # サムネ3案
python3 -m tools.akari_news.video episode_001 [--shorts]       # 動画初稿
python3 -m unittest tools.akari_news.test_loan tools.akari_news.test_score
```

依存：Python 3.11、Pillow、numpy、imageio-ffmpeg（または ffmpeg）、`fonts-noto-cjk`、ガイド音声用 `open-jtalk open-jtalk-mecab-naist-jdic hts-voice-nitech-jp-atr503-m001`。

## 6. NEWS YAGURA との連携（概要）

詳細は `docs/NEWS_YAGURA_INTEGRATION.md`。

- **一方向・読み取りのみ**：NEWS YAGURA → JSONエクスポート（`news_item.schema.json`）→ 本リポジトリ。YAGURA側のコード・DBは変更しない。
- NEWS YAGURA：収集・重複除去・カテゴリ分類・スコア項目付与。
- 本リポジトリ：`news_score ≥ 70` を対象に台本パッケージ（`script_package.schema.json`）を生成 → 一次資料確認 → 大家Mコメント承認 → 制作。
- KAGURA（知識化）へは、公開済み台本と一次資料メモを後日エクスポート（Phase 3）。

## 7. 必要サービス・API

| 用途 | 最小構成（Phase 1） | 推奨候補（比較して選定） | 備考 |
|---|---|---|---|
| 燈／大家Mの画像 | 手動で画像生成サービスを使用＋基準画像参照 | Midjourney（キャラ参照機能）、GPT系画像生成、Flux Kontext／LoRA学習 | 同一人物維持には**画像参照**が必須。LoRA学習が最も安定 |
| 音声（TTS） | Azure／Google のニューラルTTS（従量課金） | ElevenLabs、にじボイス、CoeFont、VOICEVOX（各キャラの商用規約要確認） | 「機械っぽすぎる音声は禁止」→ 聴き比べで決定 |
| 口パク・動き | なし（静止画＋図表中心、燈30〜50％） | HeyGen、Hedra 等 | Phase 2で検討。なくても成立する構成にしてある |
| 台本ドラフト | Claude（本セッション／API） | Claude API | ニュース1本あたりの費用は小さい |
| BGM・SE | YouTube オーディオライブラリ（無料） | Epidemic Sound、Artlist | 現在は自前生成のジングルのみ |
| 編集・合成 | 本リポジトリのツール（ffmpeg） | DaVinci Resolve（無料版）で仕上げも可 | |
| 公開 | YouTube Studio で**手動**アップロード | YouTube Data API（予約投稿の下書きまで） | 自動公開はしない |

## 8. 想定月額費用（参考）

> 価格は各社の改定が多いため **2026-09 時点で未確認の目安**。契約前に必ず公式価格を確認すること。1ドル≒150円換算。

| 構成 | 内訳（目安） | 月額目安 |
|---|---|---|
| **最小構成**（週2〜3本） | ニューラルTTS従量（数百円以下）＋画像生成ベーシック（約1,500〜2,000円）＋BGM無料 | **約2,000〜3,000円** |
| 標準構成（週5本＋Shorts） | 上記＋高品質TTS（ElevenLabs等 約3,000〜5,000円）＋BGMサブスク（約1,500〜2,500円）＋Claude API（数百〜千円程度） | **約7,000〜12,000円** |
| 拡張（口パク動画あり） | 上記＋アバター動画サービス（約4,000〜15,000円） | **約15,000〜30,000円** |

## 9. 最小構成での開始方法

1. **今週**：本リポジトリの第1回素材をレビュー（`episode_001/review/REVIEW_SUMMARY.md`）。一次資料PDFを人が開いて4つの事実を照合。
2. 燈の本番画像を作成：`prompt_builder.py --test-set` の8プロンプト＋基準画像参照で生成 → 25点採点 → AKARI_VIDEO_A〜E を確保。
3. TTSを2〜3社で聴き比べ（燈・大家M各1声）→ 決定した音声で文単位wavを差し替え → `timeline.py --use-existing` → `video.py --final`。
4. YouTubeチャンネル作成（ブランドアカウント。**本人の個人アカウント・会社関連情報と紐づけない**）、アイコン・バナー設定。
5. 第1回を**手動で限定公開 → 本人最終確認 → 公開**。
6. 以後、週2〜3本（カテゴリA中心）＋Shortsで運用し、2本目以降で NEWS YAGURA からのJSON受け取りを試行。

## 10. 将来の本人登場への設計

- 「大家M」「大家の一手」は名称・コーナーとして独立させてあり、出演者を本人に切り替えても番組構造は変わらない。
- `OOKA_M_MASTER` の `display_mode` を `ai_avatar → real_person` に変更するだけで、テンプレート側（ネームプレート等）は共通。
- 移行時は「これまで大家Mとして出演していた本人が登場」回を特別編として企画可能。**現段階では本人公開は行わない。**
