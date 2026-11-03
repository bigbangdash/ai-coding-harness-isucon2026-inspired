# evaluate.sh / approve.sh で共有する関数。

H=harness/implement

# 保護対象ファイルを1行1パスで出す（.gitignore 対象と approved.sha256 自身は除く）。
protected_files() {
  grep -v -e '^#' -e '^[[:space:]]*$' "$H/protected-paths.txt" | while read -r p; do
    git ls-files --cached --others --exclude-standard -- "$p"
  done | while read -r f; do [ -f "$f" ] && echo "$f"; done | grep -vx "$H/approved.sha256" | sort -u
}

# 保護対象ファイルの現在のハッシュ一覧。
protected_hashes() {
  protected_files | while read -r f; do shasum -a 256 "$f"; done
}

# 保護対象の区分。spec = 人間が合意する仕様と受け入れテスト、harness = 評価の仕組み。
protected_category() {
  case $1 in specs/*|tests/acceptance/*) echo spec ;; *) echo harness ;; esac
}

# 承認時からの差分を「<区分> <added|modified|removed> <パス>」で出す。
approval_diff() {
  awk 'NR==FNR { if ($0 !~ /^#/ && NF) o[$NF] = $1; next }
       { n[$NF] = $1 }
       END {
         for (p in n) if (!(p in o)) print "added", p; else if (o[p] != n[p]) print "modified", p
         for (p in o) if (!(p in n)) print "removed", p
       }' <(cat "$H/approved.sha256" 2>/dev/null) <(protected_hashes) |
    while read -r kind f; do echo "$(protected_category "$f") $kind $f"; done | sort -k3
}

# 承認時から変わった保護対象ファイルのパス。
unapproved_changes() {
  approval_diff | awk '{print $3}'
}

# 作業中の機能の requirements.md。変更された specs/<機能>/ と、ブランチ名 impl/<番号>-<機能> から決める。
feature_requirements() { # base
  local slug
  slug=$(git rev-parse --abbrev-ref HEAD | sed -n 's#^impl/\([0-9]*-\)\{0,1\}##p')
  { git diff --name-only "$1" -- specs/; git ls-files --others --exclude-standard -- specs/
    [ -n "$slug" ] && echo "specs/$slug/"; } |
    awk -F/ 'NF >= 2 && $2 != "" { print "specs/" $2 "/requirements.md" }' | sort -u |
    while read -r f; do [ -f "$f" ] && echo "$f"; done
}

# requirements.md の未確定事項の表で、状態が「未回答」の行の ID。
unanswered_questions() { # requirements.md
  awk -F'|' '$2 ~ /^[[:space:]]*Q-[0-9]+[[:space:]]*$/ && $4 ~ /未回答/ { gsub(/[[:space:]]/, "", $2); print $2 }' "$1"
}

# 比較の基準。main との分岐点（main 上なら HEAD）。
eval_base() {
  local b; b=$(git rev-parse --abbrev-ref HEAD)
  if [ "$b" != main ] && git rev-parse -q --verify main >/dev/null; then
    git merge-base HEAD main
  else
    git rev-parse HEAD
  fi
}

# 作業ツリーの指紋（基準からの差分 + 未追跡ファイル）。コミットしても変わらず、内容を変えると変わる。
# 「最後の評価のあとに変更したか」の判定に使う。
worktree_fingerprint() {
  { git diff "$1"
    git ls-files --others --exclude-standard | while read -r f; do echo "== $f"; cat "$f"; done
  } | shasum -a 256 | cut -c1-16
}
