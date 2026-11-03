# implement — 要件どおりに作るハーネス

```
specs/<機能>/requirements.md, acceptance.md   ← AI が下書き → 人間が approve.sh で承認
        ↓
tests/acceptance/（テスト名に AC の ID）         ← AI が下書き → 人間が承認
        ↓
app/ を実装 → evaluate.sh
        ├─ FAIL    → 修正して再評価（3 回で critic、5 回で BLOCKED）
        ├─ BLOCKED → 人間に確認
        └─ PASS    → risk high なら evaluator → 人間の承認
```

| ファイル | 役割 |
|---|---|
| `evaluate.sh` | Level 1 評価。`status: PASS/FAIL/BLOCKED` の YAML を出す |
| `commands.sh` | test / acceptance / lint などのコマンドとしきい値 |
| `evals/` | 評価基準（設計・実装・業務受入・AI 行動） |
| `templates/` | 要件・受入条件のテンプレート |
| `hooks/stop.py` | 評価を通さずに作業を終えるのを止める（`impl/*` ブランチだけ） |
| `hooks/record_review.py` | evaluator / critic の出力を `.harness/reviews/` に原文で保存（SubagentStop で最終回答、バックグラウンド起動時は PostToolUse で RUNNING） |
| `protected-paths.txt` | 承認なしに変えてはいけないパス |
| `risk-paths.txt` | 変更されたら evaluator の評価が必要になるパス |
| `approve.sh` | 人間が保護対象の変更を承認する（`approved.sha256` を更新）。`--only spec\|harness` で区分ごとに承認 |
| `selftest.sh` | ハーネス自身のテスト。`evaluate.sh`・`approve.sh`・Hook の判定を使い捨てのリポジトリで確かめる（`-v` で失敗時の出力も表示） |

- 作業ブランチ: `impl/<番号>-<名前>`
- 詳しいルール: リポジトリ直下の `EVALUATION.md`
