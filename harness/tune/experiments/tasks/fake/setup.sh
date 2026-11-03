#!/usr/bin/env bash
# 偽の課題の初期状態を作る。
set -eu
wd=$1
rm -rf "$wd"; mkdir -p "$wd"
cd "$wd"
git init -q
echo 1000 > speed.txt
cat > README.md <<'MD'
# fake-app
speed.txt の数値がベンチマークのスコアになる（±5% のばらつきあり）。
broken.txt が存在すると正常性検証に失敗する。
MD
git add -A && git -c user.name=runner -c user.email=runner@localhost commit -q -m initial
