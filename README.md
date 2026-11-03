# ai-coding-harness-isucon2026-inspired

> **WIP** — 「要件どおりに作る」と「ISUCON のように速くする」の 2 つのハーネスを 1 リポジトリで回す実験。

評価は 1 つの仕組み（`EVALUATION.md` と `harness/shared/evaluate.sh`）にまとめ、両方で使う。
tune は「implement と同じ評価に PASS したうえでスコアを上げる」もの。

## フォルダー

| パス | 役割 |
|---|---|
| `CLAUDE.md` | メインエージェントへの指示 |
| `EVALUATION.md` | 評価ルール（何を・誰が・どう判定するか） |
| `harness/shared/` | 評価の実行（`evaluate.sh`）、保護と承認（`approve.sh`） |
| `harness/implement/` | 要件どおりに作るハーネス。評価基準は `evals/` |
| `harness/tune/` | 速くするハーネス（`bench.sh`、試行ログ `log.md`） |
| `.claude/agents/` | evaluator（独立評価）、critic（前提の見直し） |
| `app/` | 対象アプリ |
| `specs/` | 要件と受入条件（人間が合意） |
| `tests/acceptance/` | 受け入れテスト（人間が承認） |

## ブランチ

| 接頭辞 | 用途 |
|---|---|
| `impl/` | 実装作業 |
| `tune/` | 最適化作業（効果がなければブランチごと捨てる） |

## 状態

| 項目 | 状態 |
|---|---|
| 評価ルール・評価基準 | ✅ |
| `evaluate.sh`（実装・受入・行動・リスク・停止） | ✅ |
| `bench.sh`（tune の採否） | ✅ |
| 保護と承認（`approve.sh`） | ✅ |
| evaluator / critic | ✅（定義のみ。実運用は未検証） |
| `commands.sh` の設定 | 未（対象アプリ待ち。今は evaluate が BLOCKED を返す） |
| CI・ブランチ保護 | 未着手 |
| 対象アプリ | 未定 |
