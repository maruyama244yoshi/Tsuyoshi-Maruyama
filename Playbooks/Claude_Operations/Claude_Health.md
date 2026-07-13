# Claude Health 表示仕様

Commander Dashboard および Morning Brief へ Claude の運用状態を表示する。

既存 OS は変更しない。表示の追加のみ。

---

## 1. Commander Dashboard: Claude Status

Commander Dashboard へ以下の **Claude Status** ブロックを追加する。

```
Claude Status
Session      正常
Snapshot     最新
Archive      更新済
Context      Healthy
Session利用率 ○%
```

### 項目定義

| 項目 | 正常値 | 異常時の対応 |
|---|---|---|
| Session | 正常 | 品質低下・肥大を検知したら「要リセット」表示 → Session 終了を提案 |
| Snapshot | 最新 | 前回 Session 終了時に未作成なら「未作成」→ 即作成 |
| Archive | 更新済 | 終了 Session が未移動なら「未更新」→ Archive へ移動 |
| Context | Healthy | 肥大時は「Bloated」→ Session 終了を提案 |
| Session利用率 | 50%未満 | 50% / 70% / 90% で段階的に Session 終了を提案 |

---

## 2. Morning Brief: Claude Health

毎朝、Morning Brief へ以下を表示する。

```
====================
Claude Health
Snapshot   最新
Session    正常
Context    Healthy
Playbook   16冊
Commander  最新
====================
```

### 項目定義

| 項目 | 内容 |
|---|---|
| Snapshot | 直近 Session 終了時の Snapshot が存在し最新か |
| Session | 現行 Session の状態（正常 / 要リセット） |
| Context | Context の健全性（Healthy / Bloated） |
| Playbook | 現在の Playbook 冊数 |
| Commander | Commander が最新 Version か |

---

## 3. 自動切替条件（検知 → 提案）

AI は以下を検知したら **Session 終了を提案** する。

- Context 肥大
- 回答品質低下
- Session 利用率 50%
- Session 利用率 70%
- Session 利用率 90%
- Session Limit 警告

提案時は Snapshot.md / HANDOVER.md の作成 → Archive 移動 → 新 Session 開始、の手順へ誘導する（[Session_Reset_Protocol.md](Session_Reset_Protocol.md) 参照）。
