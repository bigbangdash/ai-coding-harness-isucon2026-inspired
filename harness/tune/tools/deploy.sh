#!/usr/bin/env bash
# commands.deploy を実行する（競技サーバーへ反映）。
set -eu
TUNE="$(cd "$(dirname "$0")/.." && pwd)"
cmd=$(python3 "$TUNE/core.py" get commands.deploy)
[ -n "$cmd" ] || { echo "commands.deploy が未設定" >&2; exit 2; }
cd "$TUNE/../.."
bash -c "$cmd"
