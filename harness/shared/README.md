# shared — 両ハーネス共通の評価

| ファイル | 役割 |
|---|---|
| `evaluate.sh` | Level 1 評価。`status: PASS/FAIL/BLOCKED` の YAML を出す |
| `commands.sh` | test / acceptance / lint などのコマンドとしきい値 |
| `protected-paths.txt` | 承認なしに変えてはいけないパス |
| `risk-paths.txt` | 変更されたら設計評価が必要になるパス |
| `approve.sh` | 人間が保護対象の変更を承認する（`approved.sha256` を更新） |
| `lib.sh` | 上のスクリプトの共通関数 |

詳しいルールはリポジトリ直下の `EVALUATION.md`。
