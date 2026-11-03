# evaluate.sh / approve.sh で共有する関数。

H=harness/implement

# 保護対象ファイルを1行1パスで出す（approved.sha256 自身は除く）。
protected_files() {
  grep -v -e '^#' -e '^[[:space:]]*$' "$H/protected-paths.txt" | while read -r p; do
    [ -e "$p" ] && find "$p" -type f
  done | grep -vx "$H/approved.sha256" | sort -u
}

# 保護対象ファイルの現在のハッシュ一覧。
protected_hashes() {
  protected_files | while read -r f; do shasum -a 256 "$f"; done
}

# 承認時から変わった保護対象ファイルのパス。
unapproved_changes() {
  comm -3 \
    <(grep -v '^#' "$H/approved.sha256" 2>/dev/null | sort) \
    <(protected_hashes | sort) |
    awk '{print $NF}' | sort -u
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
