#!/usr/bin/env bash
# commands.profile を実行し、結果を runtime/profiles/ に保存して表示する。
set -eu
TUNE="$(cd "$(dirname "$0")/.." && pwd)"
cmd=$(python3 "$TUNE/core.py" get commands.profile)
[ -n "$cmd" ] || { echo "commands.profile が未設定。alp / pt-query-digest などを自分で実行する" >&2; exit 2; }
rt="${ISUCON_RUNTIME:-$TUNE/runtime}"; mkdir -p "$rt/profiles"
out="$rt/profiles/$(date +%Y%m%d-%H%M%S).txt"
cd "$TUNE/../.."
bash -c "$cmd" 2>&1 | tee "$out"
echo "保存: $out" >&2
