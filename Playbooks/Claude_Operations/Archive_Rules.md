# Archive Rules

終了 Session のアーカイブ規則。

---

## 原則

- 終了した Session は **Archive へ移動** する。
- Archive は **読み取り専用**。
- **更新禁止。**

---

## ルール

1. Session 終了手順（Snapshot.md / HANDOVER.md 作成）を完了してから Archive へ移動する。
2. Archive 内のファイルは一切編集しない。追記も禁止。
3. 新 Session は Archive を読み込まない（**過去 Session 読込禁止**）。
   - 引き継ぎ情報は Snapshot.md / HANDOVER.md のみを使う。
4. Archive から情報が必要になった場合は、その内容を Playbook または SSOT へ昇格させてから使う。Archive を直接参照し続けない。
5. Archive の削除は行わない（2036年まで保全）。

---

## 配置

```
Archive/
  Sessions/
    YYYY-MM-DD_<Session名>/
      Snapshot.md
      HANDOVER.md
      （その他 Session 成果物のコピー）
```

- ディレクトリ名は「日付_Session名」。
- **Session 名へ Version を書かない**（Version は OS 単位で管理）。

---

## Commander 連携

Archive への移動が完了したら、Commander Dashboard の Claude Status を

```
Archive  更新済
```

とする（[Claude_Health.md](Claude_Health.md) 参照）。
