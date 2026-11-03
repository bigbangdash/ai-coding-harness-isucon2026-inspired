#!/usr/bin/env bash
# ハーネス自身のテスト。evaluate.sh・approve.sh・Hook の判定を、使い捨ての Git リポジトリで確かめる。
#
#   bash harness/implement/selftest.sh       すべて実行（失敗が 1 件でもあれば exit 1）
#   bash harness/implement/selftest.sh -v    失敗したケースの出力も表示する
#
# 対象アプリには依存しない。毎回、一時ディレクトリに小さなリポジトリ（このリポジトリの
# evaluate.sh / approve.sh / lib.sh / hooks と、ダミーの仕様・テスト）を作ってから試す。
# approve.sh もその一時リポジトリの中でだけ実行する。このリポジトリの approved.sha256 は変えない。
set -u
SRC=$(cd "$(dirname "$0")/../.." && pwd)
VERBOSE=0; [ "${1:-}" = -v ] && VERBOSE=1
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0; failed=()
export HARNESS_MODE=""   # tune から起動されていても Hook を動かす

# ---------- 小道具 ----------
ok()  { pass=$((pass + 1)); printf '  ok    %s\n' "$1"; }
ng()  { fail=$((fail + 1)); failed+=("$CASE: $1"); printf '  NG    %s\n' "$1"
        [ "$VERBOSE" = 1 ] && [ -n "${OUT:-}" ] && printf '%s\n' "$OUT" | sed 's/^/        | /'; }
check() { if eval "$2"; then ok "$1"; else ng "$1"; fi; }   # 説明 条件
has()   { printf '%s\n' "$OUT" | grep -qE -- "$1"; }
case_() { CASE=$1; printf '%s\n' "$1"; }

# ダミーのリポジトリを作り、main に承認済みの状態でコミットする。
#   fixture [TEST_CMD] [ACCEPTANCE_CMD]
fixture() {
  R=$(mktemp -d "$TMP/repo.XXXX"); cd "$R" || exit 2
  git init -q -b main
  git config user.name selftest; git config user.email selftest@example.invalid
  mkdir -p harness/implement/hooks specs/foo tests/acceptance tests/unit app
  cp "$SRC"/harness/implement/{lib.sh,evaluate.sh,approve.sh,protected-paths.txt,risk-paths.txt} harness/implement/
  cp "$SRC"/harness/implement/hooks/*.py harness/implement/hooks/
  printf '.harness/\n__pycache__/\n' > .gitignore
  cat > harness/implement/commands.sh <<EOF
LINT_CMD=""; TYPE_CMD=""; SECURITY_CMD=""
TEST_CMD="${1-true}"
ACCEPTANCE_CMD="${2-true}"
MAX_FAILS_CRITIC=3
MAX_FAILS_BLOCK=5
EOF
  cat > specs/foo/requirements.md <<'EOF'
# foo
| ID | 質問 | 状態 | 回答 | 回答者・日付 |
|---|---|---|---|---|
| Q-1 | 端数は？ | 回答済み | 切り捨て | selftest |
EOF
  printf 'AC-1: 動く\n' > specs/foo/acceptance.md
  printf 'def test_ac1():\n    assert 1 == 1\n    assert 2 == 2\n' > tests/acceptance/test_foo.py
  printf 'def test_u():\n    assert True\n' > tests/unit/test_u.py
  touch tests/acceptance/.gitkeep specs/.gitkeep
  printf 'x = 1\n' > app/main.py
  git add -A; git commit -qm init
  bash harness/implement/approve.sh >/dev/null || exit 2
  git add -A; git commit -qm approve
  export CLAUDE_PROJECT_DIR=$R
}
ev()      { OUT=$(bash harness/implement/evaluate.sh 2>&1); RC=$?; }
status()  { printf '%s\n' "$OUT" | sed -n 's/^status: //p' | head -1; }
approve() { OUT=$(bash harness/implement/approve.sh "$@" 2>&1); RC=$?; }
stop()    { OUT=$(echo '{"hook_event_name":"Stop"}' | python3 harness/implement/hooks/stop.py 2>&1); RC=$?; }
hook()    { OUT=$(printf '%s' "$1" | python3 harness/implement/hooks/record_review.py 2>&1); RC=$?; }
fp()      { bash -c '. harness/implement/lib.sh; worktree_fingerprint $(eval_base)'; }
review()  { # status [ts]  —  今の指紋で evaluator の記録を足す
  mkdir -p .harness/reviews
  printf '{"ts":"%s","agent":"evaluator","agent_id":"x%s","fingerprint":"%s","status":%s}\n' \
    "${2:-$(date +%Y%m%d-%H%M%S)}" "$RANDOM" "$(fp)" "$([ "$1" = null ] && echo null || echo "\"$1\"")" \
    >> .harness/reviews/index.jsonl; }
n_reviews() { [ -f .harness/reviews/index.jsonl ] && wc -l < .harness/reviews/index.jsonl | tr -d ' ' || echo 0; }

# ---------- evaluate.sh ----------
case_ "evaluate: 承認済みでテストが通る → PASS"
fixture; ev
check "status: PASS" '[ "$(status)" = PASS ]'
check "exit 0" '[ $RC = 0 ]'
check "risk: low" 'has "^risk: low"'

case_ "evaluate: テストコマンド未設定 → BLOCKED（I-1）"
fixture ""; ev
check "status: BLOCKED" '[ "$(status)" = BLOCKED ]'
check "I-1 が出る" 'has "id: I-1"'
check "exit 1" '[ $RC = 1 ]'

case_ "evaluate: テスト失敗 → FAIL（I-1）"
fixture false; ev
check "status: FAIL" '[ "$(status)" = FAIL ]'
check "I-1 が出る" 'has "id: I-1"'

case_ "evaluate: 受け入れテスト失敗 → FAIL（A-1）"
fixture true false; ev
check "status: FAIL" '[ "$(status)" = FAIL ]'
check "A-1 が出る" 'has "id: A-1"'

case_ "evaluate: 仕様を承認なしで変更 → BLOCKED（B-1 仕様・受け入れテスト）"
fixture; git switch -qc impl/001-foo; echo 'AC-2: 追加' >> specs/foo/acceptance.md; ev
check "status: BLOCKED" '[ "$(status)" = BLOCKED ]'
check "B-1 は仕様の区分" 'has "仕様・受け入れテスト が未承認"'
check "評価の仕組みの B-1 は出ない" '! has "評価の仕組み が未承認"'
check "変更として列挙" 'has "変更: specs/foo/acceptance.md"'

case_ "evaluate: 評価の仕組みの追加・削除 → BLOCKED（B-1 評価の仕組み）"
fixture; echo 'x' > harness/implement/new.txt; git rm -q harness/implement/risk-paths.txt; ev
check "status: BLOCKED" '[ "$(status)" = BLOCKED ]'
check "B-1 は評価の仕組みの区分" 'has "評価の仕組み が未承認"'
check "追加として列挙" 'has "追加: harness/implement/new.txt"'
check "削除として列挙" 'has "削除: harness/implement/risk-paths.txt"'

case_ "evaluate: 承認ファイルがない → BLOCKED（B-1）"
fixture; git rm -q harness/implement/approved.sha256; ev
check "status: BLOCKED" '[ "$(status)" = BLOCKED ]'
check "承認済みハッシュがない" 'has "承認済みハッシュがない"'

case_ "evaluate: 作業中の機能に未回答の質問 → BLOCKED（A-3）"
fixture; git switch -qc impl/001-foo
echo '| Q-2 | 丸めは？ | 未回答 |  |  |' >> specs/foo/requirements.md
bash harness/implement/approve.sh --only spec >/dev/null; ev
check "status: BLOCKED" '[ "$(status)" = BLOCKED ]'
check "A-3 に Q-2" 'has "未回答の業務仕様が残っている（Q-2）"'
check "承認済みなので B-1 は出ない" '! has "id: B-1"'
sed -i.bak 's/| 未回答 |/| 回答済み |/' specs/foo/requirements.md; rm specs/foo/requirements.md.bak
bash harness/implement/approve.sh --only spec >/dev/null; ev
check "回答済みにすると PASS" '[ "$(status)" = PASS ]'

case_ "evaluate: ブランチ名だけで作業中の機能を決める（specs を変えていなくても A-3）"
fixture; echo '| Q-2 | 丸めは？ | 未回答 |  |  |' >> specs/foo/requirements.md
bash harness/implement/approve.sh >/dev/null; git commit -qam 'q2'; git switch -qc impl/002-foo; ev
check "A-3 が出る" 'has "id: A-3"'
git switch -qc impl/003-bar; ev
check "別の機能のブランチでは A-3 は出ない" '! has "id: A-3"'

case_ "evaluate: テストのスキップを追加 → FAIL（B-2）"
fixture; printf 'import pytest\n@pytest.mark.skip\ndef test_s():\n    assert True\n' > tests/unit/test_skip.py; ev
check "status: FAIL" '[ "$(status)" = FAIL ]'
check "B-2 が出る" 'has "id: B-2"'

case_ "evaluate: テストファイルの削除 → BLOCKED（B-3）"
fixture; git switch -qc impl/001-foo; git rm -q tests/unit/test_u.py; ev
check "status: BLOCKED" '[ "$(status)" = BLOCKED ]'
check "B-3 が出る" 'has "id: B-3"'

case_ "evaluate: アサーションの削減 → BLOCKED（B-4）"
fixture; git switch -qc impl/001-foo
printf 'def test_ac1():\n    assert 1 == 1\n' > tests/acceptance/test_foo.py
bash harness/implement/approve.sh --only spec >/dev/null; ev
check "status: BLOCKED" '[ "$(status)" = BLOCKED ]'
check "B-4 が出る" 'has "id: B-4"'

case_ "evaluate: リスク判定"
fixture; git switch -qc impl/001-foo; mkdir -p app/invoice; echo 'y = 1' > app/invoice/tax.py; ev
check "invoice/ の変更は risk: high" 'has "^risk: high"'
check "next_action は evaluator" 'has "next_action: .*evaluator"'
fixture; git switch -qc impl/001-foo; echo 'y = 1' >> app/main.py; ev
check "それ以外は risk: low" 'has "^risk: low"'

case_ "evaluate: FAIL の連続（3 回で critic、5 回で BLOCKED、PASS で 0 に戻る）"
fixture false; git switch -qc impl/001-foo
for _ in 1 2 3; do ev; done
check "3 回目は critic" 'has "next_action: .*critic"'
ev; ev
check "5 回目は BLOCKED（S-1）" '[ "$(status)" = BLOCKED ] && has "id: S-1"'
sed -i.bak 's/^TEST_CMD=.*/TEST_CMD="true"/' harness/implement/commands.sh; rm harness/implement/commands.sh.bak
bash harness/implement/approve.sh >/dev/null; ev
check "PASS で連続回数が 0 に戻る" '[ "$(status)" = PASS ] && has "^consecutive_fails: 0"'

# ---------- approve.sh ----------
case_ "approve: --only harness は仕様の承認を残す"
fixture; echo 'AC-2' >> specs/foo/acceptance.md; echo 'z' > harness/implement/new.txt
approve --only harness
check "評価の仕組みだけを列挙" 'has "評価の仕組み" && has "追加  harness/implement/new.txt" && ! has "specs/foo"'
check "残りの件数を表示" 'has "ほかの区分の 1 件は承認しません"'
check "approved-only を記録" 'grep -q "^# approved-only: harness" harness/implement/approved.sha256'
ev
check "仕様の B-1 だけ残る" 'has "仕様・受け入れテスト が未承認" && ! has "評価の仕組み が未承認"'
check ".gitkeep の承認が消えない（回帰）" 'grep -q " specs/.gitkeep$" harness/implement/approved.sha256 && grep -q " tests/acceptance/.gitkeep$" harness/implement/approved.sha256'

case_ "approve: --only spec は評価の仕組みの承認を残す"
fixture; echo 'AC-2' >> specs/foo/acceptance.md; echo 'z' > harness/implement/new.txt
approve --only spec; ev
check "評価の仕組みの B-1 だけ残る" 'has "評価の仕組み が未承認" && ! has "仕様・受け入れテスト が未承認"'
check "評価の仕組みのファイルの承認が消えない" '[ "$(grep -c " harness/implement/" harness/implement/approved.sha256)" -ge 8 ]'

case_ "approve: 引数なしはすべて承認し、削除も反映する"
fixture; git rm -q specs/foo/acceptance.md; echo 'AC' > specs/foo/new.md
approve
check "削除を列挙" 'has "削除  specs/foo/acceptance.md"'
check "承認ファイルから消える" '! grep -q "specs/foo/acceptance.md" harness/implement/approved.sha256'
ev
check "承認後は B-1 が出ない" '! has "id: B-1"'

case_ "approve: 変更なし・不正な引数"
fixture; approve
check "承認待ちなし" 'has "承認待ちの変更はありません" && [ $RC = 0 ]'
approve --only foo
check "不正な区分は exit 2" '[ $RC = 2 ]'
approve --bogus
check "不正な引数は exit 2" '[ $RC = 2 ]'

# ---------- hooks/stop.py ----------
case_ "stop: impl/* 以外では何もしない"
fixture; echo 'y = 2' >> app/main.py; stop
check "出力なし" '[ -z "$OUT" ]'

case_ "stop: 変更後に評価していない → 止める"
fixture; git switch -qc impl/001-foo; echo 'y = 2' >> app/main.py; stop
check "block" 'has "\"decision\": \"block\"" && has "evaluate.sh"'
ev; echo 'y = 3' >> app/main.py; stop
check "評価後に変更しても止める" 'has "\"decision\": \"block\""'

case_ "stop: 変更なしなら止めない"
fixture; git switch -qc impl/001-foo; stop
check "出力なし" '[ -z "$OUT" ]'

case_ "stop: FAIL のまま → 止める / BLOCKED・PASS(low) → 止めない"
fixture false; git switch -qc impl/001-foo; echo 'y = 2' >> app/main.py; ev; stop
check "FAIL は block" 'has "FAIL のまま"'
fixture; git switch -qc impl/001-foo; git rm -q tests/unit/test_u.py; ev; stop
check "BLOCKED は止めない" '[ -z "$OUT" ]'
fixture; git switch -qc impl/001-foo; echo 'y = 2' >> app/main.py; ev; stop
check "PASS(low) は止めない" '[ -z "$OUT" ]'

case_ "stop: risk high と evaluator の記録"
fixture; git switch -qc impl/001-foo; mkdir -p app/invoice; echo 'y = 1' > app/invoice/tax.py; ev
stop;                check "記録なし → 止める" 'has "高リスクの変更"'
review RUNNING;      stop; check "RUNNING（30 分以内）→ 止めない" '[ -z "$OUT" ]'
review RUNNING "$(date -r $(( $(date +%s) - 3600 )) +%Y%m%d-%H%M%S 2>/dev/null || date -d @$(( $(date +%s) - 3600 )) +%Y%m%d-%H%M%S)"
stop;                check "RUNNING（30 分超）→ 止める" 'has "30 分たっても"'
review FAIL;         stop; check "FAIL → 止める" 'has "evaluator が FAIL"'
review null;         stop; check "status なし → 止める" 'has "PASS として記録されていない"'
review BLOCKED;      stop; check "BLOCKED → 止めない" '[ -z "$OUT" ]'
review PASS;         stop; check "PASS → 止めない" '[ -z "$OUT" ]'
echo 'z = 1' >> app/invoice/tax.py; ev; stop
check "変更後は前の PASS を使わない" 'has "高リスクの変更"'

case_ "stop: 同じ理由で 3 回止めたら 4 回目は終了を許す"
fixture; git switch -qc impl/001-foo; echo 'y = 2' >> app/main.py
stop; stop; stop
check "3 回目まで block" 'has "\"decision\": \"block\""'
stop
check "4 回目は警告だけ" 'has "systemMessage" && ! has "\"decision\""'

# ---------- hooks/record_review.py ----------
case_ "record_review: バックグラウンド起動 → RUNNING、SubagentStop → 結果"
fixture; git switch -qc impl/001-foo; mkdir -p app/invoice; echo 'y = 1' > app/invoice/tax.py; ev
hook '{"hook_event_name":"PostToolUse","tool_input":{"subagent_type":"evaluator"},"tool_response":{"content":[{"type":"text","text":"async_launched"}],"agentId":"agent-abc123"}}'
check "RUNNING を記録" 'grep -q "\"status\": \"RUNNING\"" .harness/reviews/index.jsonl'
check "ファイル名に -running" 'ls .harness/reviews | grep -q -- "-running.md$"'
stop; check "Stop Hook は待つ" '[ -z "$OUT" ]'
hook '{"hook_event_name":"SubagentStop","agent_type":"evaluator","agent_id":"agent-abc123","last_assistant_message":"status: PASS\nscope: final"}'
check "PASS を記録" 'tail -1 .harness/reviews/index.jsonl | grep -q "\"status\": \"PASS\""'
check "scope を記録" 'tail -1 .harness/reviews/index.jsonl | grep -q "\"scope\": \"final\""'
stop; check "Stop Hook は終了を許す" '[ -z "$OUT" ]'

case_ "record_review: transcript と meta.json から読む"
fixture; git switch -qc impl/001-foo
mkdir -p "$TMP/tr"; T="$TMP/tr/agent-def456.jsonl"
printf '%s\n' '{"type":"assistant","message":{"content":[{"type":"text","text":"途中"}]}}' \
              '{"type":"user","message":{"content":"x"}}' \
              '{"type":"assistant","message":{"content":[{"type":"text","text":"status: FAIL\nscope: design"}]}}' > "$T"
echo '{"agentType":"evaluator"}' > "$TMP/tr/agent-def456.meta.json"
hook "{\"hook_event_name\":\"SubagentStop\",\"agent_id\":\"agent-def456\",\"agent_transcript_path\":\"$T\"}"
check "meta.json から evaluator と判定" 'grep -q "\"agent\": \"evaluator\"" .harness/reviews/index.jsonl'
check "最後の回答（FAIL）を記録" 'grep -q "\"status\": \"FAIL\"" .harness/reviews/index.jsonl'

case_ "record_review: 同じ agent_id は二重に記録しない・対象外のエージェントは記録しない"
fixture; git switch -qc impl/001-foo
hook '{"hook_event_name":"SubagentStop","agent_type":"evaluator","agent_id":"agent-same","last_assistant_message":"status: PASS"}'
hook '{"hook_event_name":"PostToolUse","tool_input":{"subagent_type":"evaluator"},"tool_response":{"content":[{"type":"text","text":"status: PASS"}],"agentId":"agent-same"}}'
check "1 件だけ" '[ "$(n_reviews)" = 1 ]'
hook '{"hook_event_name":"SubagentStop","agent_type":"Explore","agent_id":"agent-other","last_assistant_message":"status: PASS"}'
check "Explore は記録しない" '[ "$(n_reviews)" = 1 ]'
hook '{"hook_event_name":"SubagentStop","agent_type":"critic","agent_id":"agent-c","last_assistant_message":"status: FAIL"}'
check "critic は記録する" '[ "$(n_reviews)" = 2 ]'

case_ "record_review: impl/* 以外では記録しない"
fixture
hook '{"hook_event_name":"SubagentStop","agent_type":"evaluator","agent_id":"agent-main","last_assistant_message":"status: PASS"}'
check "記録なし" '[ "$(n_reviews)" = 0 ]'

# ---------- 結果 ----------
echo
echo "selftest: $pass passed, $fail failed"
if [ "$fail" -gt 0 ]; then printf '  - %s\n' "${failed[@]}"; exit 1; fi
