# 実装評価（Implementation Evaluation）

評価者: `harness/shared/evaluate.sh`（Level 1）。LLM の判断で上書きしない。

| ID | 基準 | コマンド（`commands.sh`） | 必須 |
|---|---|---|---|
| I-1 | 単体・結合テストが成功 | `TEST_CMD` | ✅ |
| I-2 | Lint が成功 | `LINT_CMD` | 設定時 |
| I-3 | 型チェックが成功 | `TYPE_CMD` | 設定時 |
| I-4 | 重大な脆弱性がない | `SECURITY_CMD` | 設定時 |

必須コマンドが未設定なら BLOCKED（「未設定だから PASS」にはしない）。
