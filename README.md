# ai-coding-harness-isucon2026-inspired

> **WIP** — 2 つの AI コーディングハーネスを 1 リポジトリで試す実験。

| ハーネス | 目的 | 評価の基準 | 人間の関与 |
|---|---|---|---|
| **implement** | 承認済みの要件どおりに作る | 要件・受入条件・テスト（[`EVALUATION.md`](EVALUATION.md)） | 仕様・受け入れテスト・評価の仕組みを承認 |
| **tune** | ISUCON のように 8 時間自律で速くする | マニュアルとベンチマーカー（[`harness/tune/EVALUATION.md`](harness/tune/EVALUATION.md)） | 競技中は 0 回 |

## 重要ファイル

| ファイル | 内容 |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | implement の作業ルール（Claude Code が読む） |
| [`EVALUATION.md`](EVALUATION.md) | implement の評価ルール・判定・止まる条件・既知の限界 |
| [`harness/implement/README.md`](harness/implement/README.md) | implement の流れとファイル一覧 |
| [`harness/implement/evaluate.sh`](harness/implement/evaluate.sh) | Level 1 評価（PASS / FAIL / BLOCKED） |
| [`harness/implement/approve.sh`](harness/implement/approve.sh) | 人間が保護対象を承認する |
| [`harness/implement/commands.sh`](harness/implement/commands.sh) | テストコマンドとしきい値 |
| [`harness/implement/evals/`](harness/implement/evals/) | 評価基準（[設計](harness/implement/evals/design.md)・[実装](harness/implement/evals/implementation.md)・[業務受入](harness/implement/evals/acceptance.md)・[AI 行動](harness/implement/evals/behavior.md)） |
| [`.claude/settings.json`](.claude/settings.json) | 権限（deny / ask）と Hook の配線 |
| [`.claude/agents/evaluator.md`](.claude/agents/evaluator.md) / [`critic.md`](.claude/agents/critic.md) | implement のサブエージェント |
| [`harness/tune/README.md`](harness/tune/README.md) | tune の構成・ライフサイクル・使い方 |
| [`harness/tune/CLAUDE.md`](harness/tune/CLAUDE.md) | tune セッションの基本原則 |
| [`harness/tune/policies/competition.toml`](harness/tune/policies/competition.toml) | 競技時間・コマンド・しきい値・機能の on/off |

## implement — 要件どおりに作る

```
specs/<機能>/requirements.md, acceptance.md   ← AI が下書き → 人間が approve.sh で承認
        ↓
tests/acceptance/（テスト名に AC の ID）         ← AI が下書き → 人間が承認
        ↓
app/ を実装 → evaluate.sh
        ├─ FAIL    → 修正して再評価（3 回で critic、5 回で BLOCKED）
        ├─ BLOCKED → 人間に確認
        └─ PASS    → risk high なら evaluator（design / final）→ 人間の承認
```

### 機能

| 機能 | 内容 | 実体 |
|---|---|---|
| Level 1 評価 | テスト・受け入れテスト・lint などを実行し、結果を YAML で出す。`.harness/logs/` に結果と差分を保存 | [`evaluate.sh`](harness/implement/evaluate.sh) |
| 保護と承認（B-1） | 評価基準・評価の仕組み・仕様・受け入れテストが、人間の承認時のハッシュと食い違うと BLOCKED | [`protected-paths.txt`](harness/implement/protected-paths.txt) / [`approved.sha256`](harness/implement/approved.sha256) / [`lib.sh`](harness/implement/lib.sh) |
| 区分ごとの承認 | 差分を「仕様・受け入れテスト」と「評価の仕組み」に分け、追加・変更・削除を示す。`approve.sh --only spec\|harness` で区分ごとに承認 | [`approve.sh`](harness/implement/approve.sh) |
| 未回答の質問の検出（A-3） | 作業中の機能の requirements.md に `未回答` が残っていたら BLOCKED | [`evaluate.sh`](harness/implement/evaluate.sh) / [`lib.sh`](harness/implement/lib.sh) |
| テストの弱体化の検出（B-2〜B-4） | スキップ・限定実行の追加（FAIL）、テストファイルの削除・アサーションの減少（BLOCKED） | [`evaluate.sh`](harness/implement/evaluate.sh) |
| リスク判定 | 変更パスが一致したら `risk: high`（evaluator と人間の承認が必要） | [`risk-paths.txt`](harness/implement/risk-paths.txt) |
| 停止条件 | FAIL が 3 回連続で critic、5 回連続で BLOCKED | [`commands.sh`](harness/implement/commands.sh) |
| Stop Hook | `impl/*` ブランチで、評価なし・FAIL のまま・高リスクで evaluator の PASS がないまま終わるのを止める。BLOCKED と evaluator の実行待ち（30 分）は止めない | [`hooks/stop.py`](harness/implement/hooks/stop.py) |
| 評価の記録 Hook | evaluator / critic の出力を原文で `.harness/reviews/` に保存。バックグラウンド起動は RUNNING、終了時に SubagentStop で結果を記録 | [`hooks/record_review.py`](harness/implement/hooks/record_review.py) |
| evaluator | 承認済みの仕様と評価基準で、設計（design）・完了前（final）を独立に評価。コードは変えない | [`.claude/agents/evaluator.md`](.claude/agents/evaluator.md) |
| critic | FAIL が続いたときに前提と方針を疑う。コードは変えない | [`.claude/agents/critic.md`](.claude/agents/critic.md) |
| テンプレート | 要件（未確定事項は状態・回答・回答者を記録）と受入条件 | [`requirements.md`](harness/implement/templates/requirements.md) / [`acceptance.md`](harness/implement/templates/acceptance.md) |
| 権限 | 評価の仕組みと `.harness/` の編集を deny、`approve.sh` と `git push` を ask | [`.claude/settings.json`](.claude/settings.json) |
| CI | PR と main への push で `evaluate.sh` を再実行（ローカルの `.harness/` は信用しない） | [`.github/workflows/evaluate.yml`](.github/workflows/evaluate.yml) |

### 使い方

```sh
git switch -c impl/002-<機能>                 # 作業ブランチ（Hook はここでだけ動く）
# Claude Code に依頼 → specs/ と tests/acceptance/ の下書き → 人間が確認
bash harness/implement/approve.sh --only spec  # 仕様と受け入れテストを承認（人間）
bash harness/implement/evaluate.sh             # 評価（AI が変更のたびに実行）
```

### 評価の仕組みを変えるとき

評価の仕組み（`harness/implement/`、`.claude/`、`EVALUATION.md` など）は、実装ブランチで直さない。
評価を受ける側が基準を変えた形になり、evaluator に BLOCKED で指摘される。

1. `main` から `harness/<名前>` ブランチを切って直す
2. そのブランチで人間が `approve.sh --only harness` で承認してコミット
3. `main` に入れてから、実装ブランチに `main` を取り込む

## tune — ISUCON 型の自律性能改善

ISUCON2026 の優勝事例に着想を得た、8 時間自律稼働する性能改善ハーネス。仕様承認ゲートは使わない。
詳しくは [`harness/tune/README.md`](harness/tune/README.md)。

| 機能 | 内容 | 実体 |
|---|---|---|
| Runner | 競技時間の管理、Claude Code の起動・監視・再起動・終了、中断からの再開 | [`runner/main.py`](harness/tune/runner/main.py) / [`lifecycle.py`](harness/tune/runner/lifecycle.py) / [`session.py`](harness/tune/runner/session.py) |
| フェーズ | bootstrap → optimization → finalization → final_run → shutdown | [`runner/lifecycle.py`](harness/tune/runner/lifecycle.py) |
| ベンチと採否 | ベンチ実行・記録・スコア評価・回帰判定 | [`evaluator/benchmark.py`](harness/tune/evaluator/benchmark.py) / [`score.py`](harness/tune/evaluator/score.py) / [`regression.py`](harness/tune/evaluator/regression.py) |
| 最終検証 | 終盤の検証とベンチごとの停止判断 | [`evaluator/final_run.py`](harness/tune/evaluator/final_run.py) |
| Hook | 早期終了の防止、停滞・フェーズの通知、Compaction 前後の状態保存と注入、禁止操作のガード | [`plugin/hooks/`](harness/tune/plugin/hooks/) |
| critic | 停滞時だけ呼ぶ監査役 | [`plugin/agents/critic.md`](harness/tune/plugin/agents/critic.md) |
| 道具 | デプロイ・プロファイル・最良版への復元。使い方はスキル | [`tools/`](harness/tune/tools/) / [`plugin/skills/isucon/SKILL.md`](harness/tune/plugin/skills/isucon/SKILL.md) |
| 競技条件 | 競技時間・レギュレーション・接続先 | [`CONDITIONS.md`](harness/tune/CONDITIONS.md) / [`policies/competition.toml`](harness/tune/policies/competition.toml) |
| ハーネス自体の評価 | 課題 × variant（Stop Hook・critic・判断履歴・最終判断・状態復元の有無）で比較 | [`experiments/`](harness/tune/experiments/) / [`compare.py`](harness/tune/experiments/compare.py) |

```sh
python3 harness/tune/runner/main.py            # 起動（8 時間）
python3 harness/tune/runner/main.py --resume   # 中断から再開
```

## 実装済みのアプリ機能

| 機能 | 入った PR | 仕様 | 実装 | テスト |
|---|---|---|---|---|
| 請求書の消費税計算（税率ごとに 1 回だけ切り捨て） | [#1](https://github.com/bigbangdash/ai-coding-harness-isucon2026-inspired/pull/1) | [要件](specs/invoice-tax/requirements.md) / [受入条件](specs/invoice-tax/acceptance.md) | [`app/invoice/tax.py`](app/invoice/tax.py) | [`tests/acceptance/test_invoice_tax.py`](tests/acceptance/test_invoice_tax.py) |

## フォルダー

| パス | 役割 |
|---|---|
| [`harness/implement/`](harness/implement/) | implement 一式 |
| [`harness/tune/`](harness/tune/) | tune 一式 |
| [`.claude/`](.claude/) | implement の権限・Hook・サブエージェント |
| [`.github/workflows/`](.github/workflows/) | CI |
| `app/` | implement の対象アプリ |
| `specs/` / `tests/acceptance/` | 要件・受入条件と受け入れテスト（人間が承認） |
| `.harness/` | implement の評価結果・evaluator の記録（Git 管理外） |
| `runtime/` | tune の実行時データ（Git 管理外） |

## ブランチ

| 接頭辞 | 用途 |
|---|---|
| `impl/` | 実装作業（Stop Hook が動く） |
| `harness/` | 評価の仕組みの変更（承認してから `main` へ） |
| `tune/` | ハーネス評価や競技練習の作業 |

## 状態

| 項目 | 状態 |
|---|---|
| implement: 評価ルール・`evaluate.sh`・保護と承認 | ✅ 実セッションで確認（PR #1 の `impl/001-invoice-tax`） |
| implement: 区分ごとの承認・A-3 の未回答検出 | ✅ 実セッションで確認 |
| implement: Stop Hook / evaluator 記録 Hook | ✅ 実セッションで確認（SubagentStop で PASS を記録し、Stop Hook が終了を許可） |
| implement: evaluator | ✅ design / final を実行済み |
| implement: critic | 定義のみ（FAIL 連続が起きておらず未起動） |
| implement: lint / type / security | 未設定 |
| implement: ハーネス自身のテスト | なし（次の改善候補） |
| tune: Runner・Evaluator・Hooks・final_run・experiments | ✅（偽の課題で Claude なしの動作確認） |
| tune: Claude Code を起動した通し実行 | 未検証 |
| tune: 実際の過去問の課題 | 未着手 |
| CI（evaluate.sh の再実行） | ✅ PR #1 と `main` へのマージ後で PASS |
| ブランチ保護 | 未設定 |
