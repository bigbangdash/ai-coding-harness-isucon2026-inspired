# 評価ルール（implement）

tune（ISUCON 型の性能改善）の評価は `harness/tune/EVALUATION.md`。

評価は「誰が評価するか」ではなく「何を基準に、どの仕組みで判定するか」で決める。
プログラムで判定できるものはプログラムに任せ、LLM と人間はそれ以外を見る。

## 評価の種類と評価者

| 種類 | 基準 | Level 1 プログラム | Level 2 LLM | Level 3 人間 |
|---|---|---|---|---|
| 設計 | `harness/implement/evals/design.md` | — | evaluator | 高リスク時に承認 |
| 実装 | `harness/implement/evals/implementation.md` | `evaluate.sh` | — | — |
| 業務受入 | `harness/implement/evals/acceptance.md` | `evaluate.sh` | evaluator | 運用可否を確認 |
| AI 行動 | `harness/implement/evals/behavior.md` | `evaluate.sh` | evaluator | 完了報告を照合 |

Level 1 が PASS でないとき、Level 2 の判定で PASS に上書きしない。

## 判定

| status | 意味 | 次の動き |
|---|---|---|
| PASS | 必須条件をすべて満たす | 承認ゲートへ |
| FAIL | 条件未達。AI が直せる | 修正して再評価 |
| BLOCKED | 仕様不足・未承認・上限到達。AI だけでは決められない | 止まって人間に確認 |

複数の結果が出たときは BLOCKED > FAIL > PASS の順で優先する。

## リスクによる切り替え

`harness/implement/risk-paths.txt` に一致するファイルを変更したら `risk: high`。
高リスクでは evaluator の設計評価と人間の承認が必要。判定は AI の自己申告ではなくパスで決める。

## 止まる条件

| 状況 | 動き |
|---|---|
| FAIL が `MAX_FAILS_CRITIC` 回連続 | critic で前提を見直してから修正 |
| FAIL が `MAX_FAILS_BLOCK` 回連続 | BLOCKED。人間に返す |

しきい値は `harness/implement/commands.sh` にある。

## 評価基準の保護

`harness/implement/protected-paths.txt` のファイル（評価基準・評価スクリプト・仕様・受け入れテスト）は、
人間が `approve.sh` で承認した内容（`approved.sha256`）と食い違うと BLOCKED になる。
B-1 は「仕様・受け入れテスト」と「評価の仕組み」の区分ごとにまとめて出し、追加・変更・削除を分けて示す。
`approve.sh --only spec|harness` で区分ごとに承認できる（実装の作業中に評価の仕組みの変更を一緒に承認しないため）。

- 予防: `.claude/settings.json` の deny で評価の仕組みの編集を禁止し、`approve.sh` は ask で人間の確認を必須にする
- 検出: どんな手段で変えても、`evaluate.sh` がハッシュの不一致で BLOCKED にする

## 既知の限界

- AI がシェル経由でハッシュを再計算して `approved.sha256` を書き換えることは、ローカルでは完全には防げない。最終的には CI とブランチ保護（承認ファイルの変更に人間のレビューを必須にする）で担保する
- B-2 / B-4 は正規表現による検出なので、見逃しや誤検出がある
- evaluator に渡す依頼文から推論を除くのは運用ルールで、仕組みでは強制していない
- Stop Hook は同じ理由で 3 回続けて止めたら、無限ループを避けるため終了を許す（警告は出る）
- evaluator / critic の結果は SubagentStop Hook で記録する。バックグラウンドで起動した直後は RUNNING として記録され、Stop Hook は 30 分間それを待ちとみなして終了を許す。SubagentStop が来なければ、30 分後から再び止める
- A-3 の未回答検出は、作業中の機能（変更された `specs/<機能>/` とブランチ名 `impl/<番号>-<機能>`）の requirements.md の表だけを見る
- `.harness/`（評価結果・evaluator の記録）は Edit を禁止しているが、シェルからは書き換えられる。CI で evaluate.sh を再実行して担保する
