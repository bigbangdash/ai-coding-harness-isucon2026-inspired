#!/usr/bin/env bash
# 保護対象ファイル（protected-paths.txt）の今の内容を承認する。
# 人間だけが実行する。Claude Code からの実行は .claude/settings.json の ask で確認ダイアログになる。
#
#   approve.sh                 すべて承認する
#   approve.sh --only spec     仕様と受け入れテスト（specs/, tests/acceptance/）だけ承認する
#   approve.sh --only harness  評価の仕組みだけ承認する
# --only を付けたとき、対象外の区分は承認済みの内容（変更前のハッシュ）をそのまま残す。
set -eu
cd "$(git rev-parse --show-toplevel)"
. harness/implement/lib.sh

only=""
case "${1:-}" in
  "") ;;
  --only) only=${2:-}; case $only in spec|harness) ;; *) echo "使い方: $0 [--only spec|harness]" >&2; exit 2 ;; esac ;;
  *) echo "使い方: $0 [--only spec|harness]" >&2; exit 2 ;;
esac

diff=$(approval_diff)
target=$(printf '%s\n' "$diff" | awk -v c="$only" 'NF && (c == "" || $1 == c)')
if [ -z "$target" ]; then echo "承認待ちの変更はありません。"; exit 0; fi

label() { case $1 in spec) echo "仕様・受け入れテスト" ;; harness) echo "評価の仕組み" ;; esac; }
kind() { case $1 in added) echo "追加" ;; modified) echo "変更" ;; removed) echo "削除" ;; esac; }
echo "次の変更を承認します:"
for c in spec harness; do
  rows=$(printf '%s\n' "$target" | awk -v c="$c" '$1 == c')
  [ -z "$rows" ] && continue
  echo "  [$(label "$c")]"
  printf '%s\n' "$rows" | while read -r _ k f; do echo "    $(kind "$k")  $f"; done
done
rest=$(printf '%s\n' "$diff" | awk -v c="$only" 'NF && c != "" && $1 != c' | wc -l | tr -d ' ')
if [ "$rest" -gt 0 ]; then echo "（--only $only のため、ほかの区分の $rest 件は承認しません）"; fi

new=$(mktemp); trap 'rm -f "$new"' EXIT
{
  echo "# approved-by: $(git config user.name || echo unknown)"
  echo "# approved-at: $(date '+%Y-%m-%d %H:%M:%S')"
  [ -n "$only" ] && echo "# approved-only: $only"
  # 承認する区分は今のハッシュ、それ以外は承認済みのハッシュを残す
  # （set -e の下なので、ループ本体を && でつながない。最後の行が偽だとループが失敗扱いになり、後続が走らない）
  { protected_hashes | while read -r h f; do
      if [ -z "$only" ] || [ "$(protected_category "$f")" = "$only" ]; then echo "$h  $f"; fi
    done
    if [ -n "$only" ]; then
      grep -v '^#' "$H/approved.sha256" 2>/dev/null | while read -r h f; do
        if [ -n "$f" ] && [ "$(protected_category "$f")" != "$only" ]; then echo "$h  $f"; fi
      done
    fi
  } | sort -k2
} > "$new"
mv "$new" "$H/approved.sha256"; trap - EXIT
echo "承認しました。$H/approved.sha256 をコミットしてください。"
