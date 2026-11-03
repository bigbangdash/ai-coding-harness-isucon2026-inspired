# 業務受入評価（Acceptance Evaluation）

| ID | 基準 | 評価者 |
|---|---|---|
| A-1 | `tests/acceptance/` がすべて成功 | `evaluate.sh`（Level 1） |
| A-2 | `specs/<機能>/acceptance.md` の各条件に対応する受け入れテストがある | evaluator（Level 2） |
| A-3 | 未解決の業務仕様が残っていない | `evaluate.sh`（requirements.md の `未回答`）→ evaluator → 人間 |
| A-4 | 業務担当が実際に運用できる | 人間（Level 3） |

`specs/` と `tests/acceptance/` は AI が下書きしてよいが、人間が `approve.sh` で承認するまで `evaluate.sh` は BLOCKED を返す。
