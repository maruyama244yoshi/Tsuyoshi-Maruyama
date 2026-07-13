# Claude_Operations

MS本陣 Claude Code 永続運用 Playbook（〜2036年運用）

## 基本思想

```
Never grow Sessions.
Always grow Systems.
```

- Session は使い捨て。OS / Playbook / SSOT が永続。
- Session を育てるのではなく、OS を育てる。
- 既存 OS は変更しない。運用ルールのみ追加する。

## 収録ドキュメント

| ファイル | 内容 |
|---|---|
| [Session_Reset_Protocol.md](Session_Reset_Protocol.md) | Session リセット運用の本体プロトコル（v1.0） |
| [Snapshot_Template.md](Snapshot_Template.md) | Session 終了時に作成する Snapshot のテンプレート |
| [Handover_Template.md](Handover_Template.md) | Session 終了時に生成する Handover のテンプレート |
| [Claude_Health.md](Claude_Health.md) | Commander Dashboard / Morning Brief に追加する Claude Health 表示仕様 |
| [Archive_Rules.md](Archive_Rules.md) | 終了 Session のアーカイブ規則 |

## 運用フロー（概要）

1. **Session 開始** — CLAUDE.md → Snapshot.md → 必要な Playbook のみ読み込む。過去 Session は読み込まない。
2. **Session 運用** — Context 肥大・利用率 50% 以上・品質低下を検知したら Session 終了を提案。
3. **Session 終了** — Snapshot.md と HANDOVER.md を作成し、Session を Archive へ移動。
4. **新 Session 開始** — Snapshot.md から継続。Session ではなく OS 単位で Version 管理。

詳細は [Session_Reset_Protocol.md](Session_Reset_Protocol.md) を参照。
