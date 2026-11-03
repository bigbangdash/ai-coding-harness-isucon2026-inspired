# tune — ISUCON のように速くするハーネス

1. `tune/<日付>-<連番>` ブランチを切る
2. 計測結果やプロファイルを見て、仮説を1つ立てる
3. 変更してコミット
4. `harness/tune/bench.sh "仮説"` を実行
   - `evaluate.sh` が PASS でなければスコア 0 で不採用（正しさが先）
   - 中央値が最良スコアより `BENCH_MIN_GAIN_PCT`% 以上良ければ **ADOPT**
5. ADOPT → `log.md` と `best.txt` をコミットして main へ / REJECT → `app/` の変更を取り消し（`log.md` は残してコミット）、2 へ
6. REJECT が `TUNE_STALL_CRITIC` 回続いたら critic で仮説を見直す

- `specs/` と `tests/acceptance/` を変えると `evaluate.sh` が BLOCKED を返す（＝不採用）
- `log.md` と `best.txt` は `bench.sh` だけが書く
