# NEWS YAGURA × 燈の不動産ニュース 台本生成連携仕様 v0.1

## 原則

1. **疎結合・一方向**：NEWS YAGURA → 本リポジトリ。本リポジトリから YAGURA／YAGURA本体／融資ずかん／KAGURA へ書き込まない。
2. **既存システム無変更**：YAGURA側に必要なのは「JSONを1ファイル出力する」機能のみ（既存の出力があれば変換スクリプトをこちら側に置く）。
3. **一次資料優先**：`primary_sources` が空、または `sns_only: true` の項目は台本化しない。
4. **AIは下書きまで**：大家Mのコメントは `suggested_comment` として作り、本人承認で `approved_comment` になったものだけ台本に入る（`build_episode.py` が強制）。
5. **公開は人間**：アップロード・公開は YouTube Studio で手動。

## データフロー

```
NEWS YAGURA                         本リポジトリ（akari_news）                         人間
─────────────                       ───────────────────────────                      ─────
収集 → 重複除去 → 分類
→ score_breakdown 付与
→ news_item.json 出力 ──────────→ inbox/YYYYMMDD/*.json
                                    ↓ schemas/news_item.schema.json で検証
                                    ↓ score.py で news_score 再計算・判定
                                    ↓ news_score ≥ 70 のみ
                                    台本パッケージ生成（Claude）
                                      = script_package.schema.json
                                    ↓ fact_check：一次資料照合 ─────────────────→ 一次資料確認
                                    ↓ ooka_m_comments: suggested ───────────────→ 本人承認
                                    episode_XXX.json 作成（approved のみ）
                                    ↓ build_episode → graphics → timeline(本番TTS) → video
                                    review/ にレビュー一式 ─────────────────────→ 最終確認 → 手動公開
```

## ニュース重要度スコア（§18）

| 項目 | キー | 配点 |
|---|---|---|
| 大家への影響 | `landlord_impact` | 30 |
| 市場インパクト | `market_impact` | 20 |
| 緊急性 | `urgency` | 15 |
| データ信頼性 | `data_reliability` | 15 |
| 検索需要 | `search_demand` | 10 |
| 動画化適性 | `video_fit` | 10 |

YAGURA側は各項目を 0.0〜1.0 で付与。`news_score = Σ 配点 × 評価値`（四捨五入）。
判定：0〜49 保存のみ／50〜69 ニュース候補／70〜84 動画候補／85〜100 速報候補。
YAGURA側の `news_score` と本側の再計算が異なる場合は本側を採用し、差分をログに残す。

## 受け渡しファイル

- `schemas/news_item.schema.json`：YAGURA → 本側（例：`schemas/examples/news_item.example.json`）
- `schemas/script_package.schema.json`：台本生成結果。§19 の生成項目
  （タイトル5案／サムネ文言3案／冒頭10秒／燈の概要／数字・データ／大家への影響／大家Mコメント候補／大家の一手／まとめ／CTA／概要欄／Shorts版）を網羅。

受け渡し方法（どちらか。YAGURAの現状に合わせて選択）：
- A. ファイル：YAGURAがJSONを共有フォルダ（例：Google Drive の `akari_inbox/`）に出力 → 本側が取り込み
- B. API：YAGURAに読み取り専用エンドポイントがあれば `GET /news?since=...&min_score=70` を本側から呼ぶ

## 台本生成ルール（Claudeへのプロンプト要件）

- 入力は news_item と一次資料本文（取得できたもの）のみ。記事本文の丸読み・言い換えのみは禁止。
- 数値は `key_figures` と一次資料からのみ。試算は `tools/akari_news/loan.py` 等の関数で算出し、`figures[].calc` に関数と引数を記録。
- 燈の文体は `AKARI_MASTER` §5 の固定フレーズ・話し方に従う。煽り語は `AKARI_MASTER_v1.0.json` の banned_words で機械チェック。
- 大家Mは `suggested_comment` のみ生成し、`status: suggested` で出力（承認は人間）。

## 未確定事項（要確認）

- NEWS YAGURA の現在の出力形式（DB／CSV／API）とカテゴリ体系 → 変換マッピングを本側に作成
- 受け渡し方法 A/B の選択
- 融資ずかん・YAGURA（物件情報）の参照範囲（Phase 3）
