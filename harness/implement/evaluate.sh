#!/usr/bin/env bash
# Level 1（プログラムによる評価）を実行し、結果を YAML で出す。
#   status: PASS | FAIL | BLOCKED   （PASS 以外は exit 1）
# 結果は .harness/logs/last-eval.yaml、差分は .harness/logs/diff.patch にも保存する（evaluator が読む）。
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2
. harness/implement/lib.sh
. "$H/commands.sh"

LOGS=.harness/logs; STATE=.harness/state
mkdir -p "$LOGS" "$STATE"
findings=$(mktemp); checks=$(mktemp)
trap 'rm -f "$findings" "$checks"' EXIT
status=PASS

q() { printf '%s' "$*" | tr '"\n' "' " ; }
add() { # id check verdict issue evidence
  printf '  - id: %s\n    check: %s\n    verdict: %s\n    issue: "%s"\n    evidence: "%s"\n' \
    "$1" "$2" "$3" "$(q "$4")" "$(q "$5")" >>"$findings"
  case $3 in
    BLOCKED) status=BLOCKED ;;
    FAIL) [ "$status" = PASS ] && status=FAIL ;;
  esac
}

# ---- 比較の基準（main との分岐点。main 上なら HEAD） ----
branch=$(git rev-parse --abbrev-ref HEAD)
base=$(eval_base)
fingerprint=$(worktree_fingerprint "$base")
untracked=$(git ls-files --others --exclude-standard)
changed=$( { git diff --name-only "$base"; printf '%s\n' "$untracked"; } | grep -v '^$' | sort -u)
git diff "$base" >"$LOGS/diff.patch"

# ---- 実装評価（I-*） ----
run_check() { # id name cmd required
  local id=$1 name=$2 cmd=$3 req=$4
  if [ -z "$cmd" ]; then
    echo "  $name: not-configured" >>"$checks"
    [ "$req" = yes ] && add "$id" "$name" BLOCKED "$name のコマンドが未設定（PASS にできない）" "$H/commands.sh"
    return 0
  fi
  if bash -c "$cmd" >"$LOGS/$name.log" 2>&1; then
    echo "  $name: pass" >>"$checks"
  else
    echo "  $name: fail" >>"$checks"
    add "$id" "$name" FAIL "$name が失敗" "$LOGS/$name.log: $(tail -n 3 "$LOGS/$name.log")"
  fi
}
run_check I-1 test       "$TEST_CMD"       yes
run_check I-2 lint       "$LINT_CMD"       no
run_check I-3 type       "$TYPE_CMD"       no
run_check I-4 security   "$SECURITY_CMD"   no
run_check A-1 acceptance "$ACCEPTANCE_CMD" yes

# ---- 行動評価（B-*） ----
if [ ! -f "$H/approved.sha256" ]; then
  add B-1 protected BLOCKED "承認済みハッシュがない" "$H/approve.sh を人間が実行する"
else
  for f in $(unapproved_changes); do
    add B-1 protected BLOCKED "保護対象ファイルが未承認のまま変更されている" "$f"
  done
fi

test_diff=$(git diff "$base" -- tests/)
skip_re='(\.skip\(|@skip|mark\.skip|xfail|\bxit\(|\bxdescribe\(|\.only\(|t\.Skip\()'
skips=$( { printf '%s\n' "$test_diff" | grep -E '^\+[^+]';
           printf '%s\n' "$untracked" | grep '^tests/' | while read -r f; do cat "$f"; done; } | grep -Ec "$skip_re")
[ "$skips" -gt 0 ] && add B-2 test-skip FAIL "テストのスキップ／限定実行が追加されている（$skips 箇所）" "$LOGS/diff.patch"

for f in $(git diff --name-only --diff-filter=D "$base" -- tests/); do
  add B-3 test-delete BLOCKED "テストファイルが削除されている" "$f"
done

assert_re='(assert|expect\(|should|t\.(Error|Fatal))'
removed=$(printf '%s\n' "$test_diff" | grep -E '^-[^-]' | grep -Ec "$assert_re")
added=$(printf '%s\n' "$test_diff" | grep -E '^\+[^+]' | grep -Ec "$assert_re")
[ "$removed" -gt "$added" ] && add B-4 assert-removed BLOCKED "アサーションが減っている（-$removed / +${added}）" "$LOGS/diff.patch"

# ---- リスク判定（設計評価が要るか） ----
risk_re=$(grep -v -e '^#' -e '^[[:space:]]*$' "$H/risk-paths.txt" | paste -sd'|' -)
risky=$(printf '%s\n' "$changed" | grep -E "$risk_re")
if [ -n "$risky" ]; then risk=high; else risk=low; fi

# ---- 停止条件（FAIL の連続回数） ----
cf="$STATE/$(printf '%s' "$branch" | tr '/' '_').fails"
fails=$(cat "$cf" 2>/dev/null || echo 0)
case $status in FAIL) fails=$((fails + 1)) ;; PASS) fails=0 ;; esac
echo "$fails" >"$cf"
if [ "$status" = FAIL ] && [ "$fails" -ge "$MAX_FAILS_BLOCK" ]; then
  add S-1 stop BLOCKED "FAIL が $fails 回連続（上限 ${MAX_FAILS_BLOCK}）" "$cf"
fi

case $status in
  PASS)
    if [ "$risk" = high ]; then next="evaluator で設計評価（design）を受け、人間の承認を得る"
    else next="完了。必要な承認ゲートへ進む"; fi ;;
  FAIL)
    if [ "$fails" -ge "$MAX_FAILS_CRITIC" ]; then next="修正の前に critic で前提を見直す"
    else next="findings を修正して再評価する"; fi ;;
  BLOCKED) next="作業を止めて findings を人間に提示する" ;;
esac

{
  echo "status: $status"
  echo "branch: $branch"
  echo "base: $(git rev-parse --short "$base")"
  echo "fingerprint: $fingerprint"
  echo "consecutive_fails: $fails"
  echo "risk: $risk"
  if [ -n "$risky" ]; then echo "risky_paths:"; printf '  - %s\n' $risky; fi
  echo "checks:"; cat "$checks"
  if [ -s "$findings" ]; then echo "findings:"; cat "$findings"; else echo "findings: []"; fi
  echo "next_action: \"$next\""
} | tee "$LOGS/last-eval.yaml"

[ "$status" = PASS ]
