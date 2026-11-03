# ai-coding-harness-isucon2026-inspired

> **WIP** — 2 つの AI コーディングハーネスを 1 リポジトリで試す実験。

| ハーネス | 目的 | 評価の基準 | 人間の関与 |
|---|---|---|---|
| **implement** | 承認済みの要件どおりに作る | 要件・受入条件・テスト（`EVALUATION.md`） | 仕様と受け入れテストを承認 |
| **tune** | ISUCON のように 8 時間自律で速くする | マニュアルとベンチマーカー（`harness/tune/EVALUATION.md`） | 競技中は 0 回 |

## フォルダー

| パス | 役割 |
|---|---|
| `CLAUDE.md` / `EVALUATION.md` | implement のルールと評価 |
| `harness/implement/` | implement 一式（`evaluate.sh`、保護と承認、評価基準 `evals/`、テンプレート、Hook） |
| `.github/workflows/` | CI で `evaluate.sh` を再実行 |
| `.claude/agents/` | implement の evaluator / critic |
| `harness/tune/` | tune 一式（Runner・Evaluator・Hooks・Critic・ハーネス評価）。詳しくは `harness/tune/README.md` |
| `app/` | implement の対象アプリ |
| `specs/` / `tests/acceptance/` | 要件・受入条件と受け入れテスト（人間が承認） |

## ブランチ

| 接頭辞 | 用途 |
|---|---|
| `impl/` | 実装作業 |
| `tune/` | ハーネス評価や競技練習の作業 |

## 状態

| 項目 | 状態 |
|---|---|
| implement: 評価ルール・`evaluate.sh`・保護と承認 | ✅（作業用コピーで動作確認済み） |
| implement: Stop Hook / evaluator 記録 Hook | ✅（Hook 単体で確認） |
| implement: evaluator / critic | 定義のみ（実際の起動は未検証） |
| implement: `commands.sh` の設定・対象アプリ | 未定（今は evaluate が BLOCKED） |
| tune: Runner・Evaluator・Hooks・final_run・experiments | ✅（偽の課題で Claude なしの動作確認） |
| tune: Claude Code を起動した通し実行 | 未検証 |
| tune: 実際の過去問の課題 | 未着手 |
| CI（evaluate.sh の再実行） | ✅（未 push のため未実行） |
| ブランチ保護 | 未設定（public リポジトリなので設定可能） |
