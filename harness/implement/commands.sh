# 評価で実行するコマンドとしきい値。対象アプリが決まったら人間が設定する。
# このファイルは保護対象。変更したら approve.sh で承認するまで evaluate.sh は BLOCKED を返す。
# 空のままのコマンドは「未設定」。必須のものが未設定なら PASS にはならない。

LINT_CMD=""
TYPE_CMD=""
SECURITY_CMD=""
TEST_CMD="python3 -m unittest discover -s tests/unit -t ."         # 必須（unit / integration）
ACCEPTANCE_CMD="python3 -m unittest discover -s tests/acceptance -t ."   # 必須（tests/acceptance/）

MAX_FAILS_CRITIC=3  # FAIL がこの回数続いたら critic で前提を見直す
MAX_FAILS_BLOCK=5   # FAIL がこの回数続いたら BLOCKED にして人間に返す
