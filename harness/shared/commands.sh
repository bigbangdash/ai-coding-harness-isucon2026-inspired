# 評価で実行するコマンドとしきい値。対象アプリが決まったら人間が設定する。
# このファイルは保護対象。変更したら approve.sh で承認するまで evaluate.sh は BLOCKED を返す。
# 空のままのコマンドは「未設定」。必須のものが未設定なら PASS にはならない。

LINT_CMD=""
TYPE_CMD=""
SECURITY_CMD=""
TEST_CMD=""         # 必須（unit / integration）
ACCEPTANCE_CMD=""   # 必須（tests/acceptance/）

BENCH_CMD=""        # tune 用。標準出力の最終行にスコア（数値・大きいほど良い）を出す
BENCH_RUNS=3        # 計測回数。中央値で判定する
BENCH_MIN_GAIN_PCT=2  # 最良スコアからこれ以上（%）改善したら採用

MAX_FAILS_CRITIC=3  # FAIL がこの回数続いたら critic で前提を見直す
MAX_FAILS_BLOCK=5   # FAIL がこの回数続いたら BLOCKED にして人間に返す
TUNE_STALL_CRITIC=3 # tune で不採用がこの回数続いたら critic で仮説を見直す
