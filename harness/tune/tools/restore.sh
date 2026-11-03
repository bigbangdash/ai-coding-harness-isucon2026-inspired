#!/usr/bin/env bash
# 作業ディレクトリを最良の有効コミットに戻し（git reset --hard）、デプロイする。
set -eu
TUNE="$(cd "$(dirname "$0")/.." && pwd)"
rt="${ISUCON_RUNTIME:-$TUNE/runtime}"
best=$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])).get("best") or {}; print(b.get("commit",""), b.get("exp_id",""))' "$rt/state.json")
set -- $best
[ $# -eq 2 ] || { echo "最良コミットがまだない" >&2; exit 2; }
wd=$(python3 "$TUNE/core.py" workdir)
if [ -n "$(git -C "$wd" status --porcelain)" ]; then
  git -C "$wd" stash push -q -u -m "before restore to $2" && echo "未コミットの変更は stash に退避した"
fi
git -C "$wd" reset -q --hard "$1"
echo "最良（$2 / $1）に戻した。それまでの試行はタグ isu/exp-* で参照できる"
if [ -n "$(python3 "$TUNE/core.py" get commands.deploy)" ]; then "$TUNE/tools/deploy.sh"; fi
