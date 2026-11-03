#!/usr/bin/env bash
# tune の1試行を判定する。使い方: harness/tune/bench.sh "仮説（何を変えて、なぜ速くなるか）"
#   1. evaluate.sh が PASS でなければスコア 0 で不採用
#   2. BENCH_CMD を BENCH_RUNS 回実行し、中央値をスコアにする
#   3. 最良スコア（best.txt）より BENCH_MIN_GAIN_PCT% 以上良ければ採用
# 結果は log.md に自動で追記する（手で書き換えない）。
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2
. harness/shared/commands.sh
T=harness/tune; LOGS=.harness/logs; STATE=.harness/state
mkdir -p "$LOGS" "$STATE"

hyp=${1:-}
[ -n "$hyp" ] || { echo "仮説を引数で渡してください" >&2; exit 2; }
[ -z "$(git status --porcelain -- . ":!$T/log.md" ":!$T/best.txt")" ] || { echo "未コミットの変更があります。コミットしてから計測してください（採用時にコミットを特定するため）" >&2; exit 2; }

branch=$(git rev-parse --abbrev-ref HEAD)
rev=$(git rev-parse --short HEAD)
best=$(awk 'NR==1{print $1}' "$T/best.txt" 2>/dev/null); best=${best:-0}
sf="$STATE/tune.stall"; stall=$(cat "$sf" 2>/dev/null || echo 0)

log() { # score verdict
  printf '| %s | %s | %s | %s | %s → %s | %s |\n' \
    "$(date '+%Y-%m-%d %H:%M')" "$branch" "$rev" "$(printf '%s' "$hyp" | tr '|\n' '/ ')" "$best" "$1" "$2" >>"$T/log.md"
}
result() { # verdict score next
  printf 'verdict: %s\nscore: %s\nbest_before: %s\nruns: [%s]\nconsecutive_rejects: %s\nnext_action: "%s"\n' \
    "$1" "$2" "$best" "${scores:-}" "$stall" "$3"
}
reject_next() {
  if [ "$stall" -ge "$TUNE_STALL_CRITIC" ]; then echo "critic で仮説を見直す"; else echo "この変更を取り消し、次の仮説へ"; fi
}

if [ -z "$BENCH_CMD" ]; then
  result BLOCKED - "harness/shared/commands.sh の BENCH_CMD を人間が設定する"; exit 1
fi

if ! harness/shared/evaluate.sh >"$LOGS/bench-eval.yaml"; then
  st=$(awk '/^status:/{print $2}' "$LOGS/bench-eval.yaml")
  stall=$((stall + 1)); echo "$stall" >"$sf"
  log 0 "REJECT（evaluate: ${st}）"
  result REJECT 0 "evaluate が ${st}（$LOGS/bench-eval.yaml）。$(reject_next)"; exit 1
fi

scores=""
for _ in $(seq "$BENCH_RUNS"); do
  s=$(bash -c "$BENCH_CMD" 2>>"$LOGS/bench.log" | tail -n 1)
  printf '%s' "$s" | grep -Eq '^-?[0-9]+(\.[0-9]+)?$' || { echo "BENCH_CMD の最終行が数値ではありません: $s" >&2; exit 2; }
  scores="${scores:+$scores, }$s"
done
median=$(printf '%s\n' ${scores//,/} | sort -n | awk '{a[NR]=$1} END{print (NR%2) ? a[(NR+1)/2] : (a[NR/2]+a[NR/2+1])/2}')

if awk -v m="$median" -v b="$best" -v g="$BENCH_MIN_GAIN_PCT" 'BEGIN{exit !(m > b*(1+g/100))}'; then
  echo "$median $rev $branch" >"$T/best.txt"
  stall=0; echo 0 >"$sf"
  log "$median" ADOPT
  result ADOPT "$median" "log.md と best.txt をコミットし、main へマージする"
else
  stall=$((stall + 1)); echo "$stall" >"$sf"
  log "$median" REJECT
  result REJECT "$median" "$(reject_next)"; exit 1
fi
