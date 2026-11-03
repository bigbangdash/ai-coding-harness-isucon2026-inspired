# tune — ISUCON 型の自律性能改善ハーネス

ISUCON2026 の優勝事例に着想を得た、8 時間自律稼働する性能改善ハーネス。
仕様承認ゲートは使わない。評価基準はマニュアルとベンチマーカー。

## 構成

```
Runner (runner/main.py)  競技時間・Claude Code の起動・監視・再起動・終了
  └─ Claude Code（メインエージェント。調査・設計・実装・改善をすべて担う）
       ├─ plugin/            --plugin-dir で読み込む Claude Code プラグイン
       │   ├─ hooks/         stop（早期終了の防止）/ stagnation（停滞・フェーズ通知）
       │   │                 pre_compact（Compaction 前後の状態保存と注入）/ guard（禁止操作）
       │   ├─ agents/critic  停滞時だけ呼ぶ監査役（コードは変えない）
       │   └─ skills/isucon  道具の使い方
       ├─ evaluator/         benchmark（実行・記録・採否）/ final_run（終盤の検証と停止判断）
       └─ tools/             deploy / profile / restore（最良へ戻す）
runtime/                     実行時に生成（Git 管理外）。state / benchmarks / events / decisions / checkpoints
experiments/                 ハーネス自体の評価（課題 × variant を比較）
```

| ファイル | 役割 |
|---|---|
| `CLAUDE.md` | 自律改善の基本原則（system prompt に追記される） |
| `CONDITIONS.md` | 競技時間・レギュレーション・接続先（大会ごとに書き換え） |
| `EVALUATION.md` | スコア評価・改善の採否基準 |
| `policies/competition.toml` | 時間・コマンド・しきい値・機能の on/off |

## ライフサイクル

| phase | 条件 | 主な動き |
|---|---|---|
| bootstrap | 有効なベンチ結果がない | 環境調査・ベースライン測定 |
| optimization | 通常 | ボトルネック特定 → 変更 → `benchmark.py` の反復。30 分停滞で Critic を促す |
| finalization | 残り 40 分 | 最良版に揃え、再起動・永続性を確認して `final_run.py check` |
| final_run | 最終検証済み | ベンチごとに `final_run.py decide`。STOP で lock |
| shutdown | lock / 時間切れ | 変更禁止。Runner が結果を保存して終了 |

フェーズは状態であって手順ではない。各フェーズで何をどの順にやるかは Claude が決める。

## 使い方

```sh
# 1. CONDITIONS.md と policies/competition.toml（[commands] など）を大会に合わせて書く
# 2. 起動（8 時間）
python3 harness/tune/runner/main.py
# 中断から再開
python3 harness/tune/runner/main.py --resume
```

## ハーネス自体の評価（experiments）

```sh
# 偽の課題で 30 分、Critic なしの variant を走らせる
python3 harness/tune/runner/main.py --task experiments/tasks/fake.toml \
  --variant experiments/variants/B-no-critic.toml --duration 30 --fresh
# 集計
python3 harness/tune/experiments/compare.py
```

| variant | 比較する内容 |
|---|---|
| A-no-stop-hook | Stop Hook なし／あり |
| B-no-critic | Critic なし／あり |
| C-critic-60 | Critic 起動 30 分／60 分 |
| D-no-decision-log | 判断履歴の保存なし／あり |
| E-no-final-run-tool | 最終ベンチ停止判断なし／あり |
| F-no-state-restore | 標準 Compaction／外部状態復元あり |

同じ課題・同じモデル・同じ制約で複数回ずつ走らせ、スコアだけでなく成功率とコストも比べる。
