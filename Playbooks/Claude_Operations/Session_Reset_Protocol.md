# MS本陣 Session Reset Protocol v1.0
（永続運用設計）

## 目的

MS本陣は今後2036年まで運用する。

Claude Code は Session 単位で Context を保持するため、一つの Session を育て続けると以下が発生する。

- Context 肥大化
- Session Limit
- レスポンス低下
- 品質低下

今後は「Session を育てる」のではなく「OS を育てる」運用へ変更する。

既存 OS は変更しない。運用ルールのみ追加する。

---

## 基本思想

- Session は使い捨て。
- OS は永続。
- Playbook は永続。
- SSOT は永続。
- Session だけ更新する。

```
Never grow Sessions.
Always grow Systems.
```

---

## Session 寿命

以下のいずれかで Session 終了。これ以上続けない。

- Version 完成
- Playbook 完成
- Commander 更新
- 大機能完成
- Context 肥大
- 利用率 50% 以上
- Session Limit 警告

---

## Session 終了手順

終了時、必ず **Snapshot** を作成する。

### Snapshot.md の内容

```
====================
Mission
現在Version
North Star
成果物
更新内容
未完了
次Action
重要決定事項
注意事項
====================
```

これだけ。**長文禁止。1〜2ページ以内。**

テンプレート: [Snapshot_Template.md](Snapshot_Template.md)

---

## 新 Session 開始

新 Session では以下 **のみ** 読み込む。

1. CLAUDE.md
2. Snapshot.md
3. 必要な Playbook

以上。**過去 Session 読込禁止。**

---

## Context 削減

読込優先順位:

1. CLAUDE.md
2. Snapshot.md
3. Commander
4. 対象 Playbook
5. 対象 OS

それ以外は読まない。

---

## Handover

Session 終了時、**HANDOVER.md** も生成する。

内容（これのみ）:

- Mission
- Version
- 成果物
- 残Task
- 次Action
- Risk

テンプレート: [Handover_Template.md](Handover_Template.md)

---

## Archive

終了 Session は **Archive** へ移動。

- 読み取り専用。
- 更新禁止。

規則: [Archive_Rules.md](Archive_Rules.md)

---

## Version 管理

Version 管理は Session ではなく **OS 単位** で行う。

例:

| OS | Version |
|---|---|
| Commander | v1.3 |
| Bank | v1.2 |
| Acquisition | v1.0 |

**Session 名へ Version を書かない。**

---

## Improvement

- 改善案は **Improvement Backlog** のみに記録。
- **Session 途中変更禁止。**

---

## Commander 追加

Commander Dashboard へ **Claude Status** を追加。

表示項目:

- Session: 正常
- Snapshot: 最新
- Archive: 更新済
- Context: Healthy
- Session 利用率: ○%

仕様: [Claude_Health.md](Claude_Health.md)

---

## Morning Brief 追加

毎朝 **Claude Health** を表示する。

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

仕様: [Claude_Health.md](Claude_Health.md)

---

## 自動切替条件

AI は以下を検知したら Session 終了を提案する。

- Context 肥大
- 回答品質低下
- Session 利用率 50%
- Session 利用率 70%
- Session 利用率 90%
- Session Limit 警告

---

## 新しい原則

```
====================
Never grow Sessions.
Always grow Systems.
====================
```

Session は育てない。OS を育てる。
