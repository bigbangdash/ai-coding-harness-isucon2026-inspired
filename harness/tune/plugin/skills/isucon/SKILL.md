---
name: isucon
description: ISUCON 型の性能改善で使うハーネスの道具（状況確認・ベンチ・プロファイル・デプロイ・最良への復元・最終走行の判断）と記録のルール。ベンチを実行する前、終盤に入るとき、停滞したときに読む。
---

# ISUCON ハーネスの道具

コマンドはすべてリポジトリ直下から実行する。

| 目的 | コマンド |
|---|---|
| 状況確認（phase・残り時間・最良・停滞） | `python3 harness/tune/runner/lifecycle.py status` |
| ベンチ（変更の評価） | `python3 harness/tune/evaluator/benchmark.py --hypothesis "仮説" --change "変更内容"` |
| 同じコミットを再測定 | `python3 harness/tune/evaluator/benchmark.py --remeasure` |
| プロファイル | `harness/tune/tools/profile.sh` |
| デプロイだけ | `harness/tune/tools/deploy.sh` |
| 最良コミットに戻す | `harness/tune/tools/restore.sh` |
| 終盤の最終検証 | `python3 harness/tune/evaluator/final_run.py check` |
| 最終走行の停止判断 | `python3 harness/tune/evaluator/final_run.py decide` |

## benchmark.py の判定

| decision | 意味 | 次の動き |
|---|---|---|
| KEEP | 最良を更新 | 次のボトルネックへ |
| RETEST | 改善幅がノイズ以下 | `--remeasure` で再測定 |
| REVERT | 最良より悪い | 原因を見て、不要なら `restore.sh` |
| INVALID | 正常性検証に不合格 | 失敗理由を直すか `restore.sh` |
| SAME_AS_BEST | 最良と同じコミット | 分布に加わる |

- 未コミットの変更は benchmark.py が自動でコミットする（スコアとコミットを対応させるため）
- 記録（`runtime/benchmarks.jsonl` など）は evaluator だけが書く。手で書き換えない
- 判定に納得できない理由や気づきは `harness/tune/runtime/decisions.md` に追記する

## 記録の書き方（decisions.md）

benchmark.py が 1 行追記するので、その下に次を書く。

- なぜその仮説を立てたか（どの計測・ログが根拠か）
- 結果をどう解釈したか（ばらつきか、本当の改善か）
- 捨てた仮説は、なぜ捨てたか

## 停滞したとき

通知が来たら `isucon-tune:critic` サブエージェントに監査を依頼する。依頼文には自分の結論を書かず、
「直近 N 件の試行が停滞している。判断履歴を監査して」とだけ書く。
Critic の提案は無条件に採用せず、1 つずつ測定で確かめる。
