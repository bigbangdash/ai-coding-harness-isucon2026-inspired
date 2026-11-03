# 開発ルール

このリポジトリには 2 つのハーネスがある。どちらも評価は `EVALUATION.md` に従う。

- **implement**（`impl/*` ブランチ）: 承認済みの要件を満たす機能を作る
- **tune**（`tune/*` ブランチ）: 正しさを保ったままベンチマークスコアを上げる

## 作業原則

- 実装前に `specs/<機能>/` の要件と受入条件を読む
- 調査・計画・設計・実装・修正は自分で行う
- 不明な業務ルールは推測しない。人間に確認する
- 変更したら `harness/shared/evaluate.sh` を実行し、出力の `next_action` に従う

## implement の流れ

1. 要件・受入条件が足りなければ `specs/<機能>/` に下書きし、人間に承認を依頼する
2. 受入条件に対応するテストを `tests/acceptance/` に下書きし、人間に承認を依頼する
3. 実装して `evaluate.sh` を実行する
4. `risk: high` なら evaluator で設計評価（scope: design）を受ける
5. PASS したら evaluator で最終確認（scope: final）を受け、結果をそのまま人間に報告する

## tune の流れ

`harness/tune/README.md` に従う。スコアの採否は `bench.sh` が決める。

## evaluator / critic の呼び方

依頼文には評価対象（機能名と scope）だけを書く。自分の説明や「問題ない」といった結論は書かない。
evaluator は `.harness/logs/` と `specs/` を自分で読む。

## 制約

- 評価の仕組み（`EVALUATION.md`、`harness/shared/`、`harness/implement/evals/`、`harness/tune/bench.sh`、`.claude/`）を変更しない
- テストを削除・スキップ・弱体化しない
- `harness/shared/approve.sh` は人間が実行する。自分から実行を提案しない
- `.harness/` の中身を変更・削除しない
- 認証・認可を弱めない
- push 前に必ず人間に確認する

## 完了条件

`evaluate.sh` が PASS し、evaluator の最終確認が PASS し、必要な人間の承認を得ていること。
FAIL や BLOCKED のまま「完了」と報告しない。
