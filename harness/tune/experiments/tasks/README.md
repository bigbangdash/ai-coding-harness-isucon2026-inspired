# tasks — ハーネス評価に使う課題

1 課題 = 1 つの toml。`policies/competition.toml` を上書きする（`[app]`、`[commands]`、`[task].setup` など）。

| 課題 | 内容 |
|---|---|
| `fake.toml` | ハーネスの動作確認用。数値ファイルがスコアになる |
| （追加予定） | 過去問（ISUCON の公開リポジトリ）や自作問題 |

過去問を追加するときは、`task.setup` で初期状態に戻せるようにする（毎回同じ条件で走らせるため）。
