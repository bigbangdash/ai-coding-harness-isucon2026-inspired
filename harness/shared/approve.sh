#!/usr/bin/env bash
# 保護対象ファイル（protected-paths.txt）の今の内容を承認する。
# 人間だけが実行する。Claude Code からの実行は .claude/settings.json の ask で確認ダイアログになる。
set -eu
cd "$(git rev-parse --show-toplevel)"
. harness/shared/lib.sh

changes=$(unapproved_changes)
if [ -z "$changes" ]; then echo "承認待ちの変更はありません。"; exit 0; fi
echo "次のファイルを承認します:"; printf '  %s\n' $changes

{
  echo "# approved-by: $(git config user.name || echo unknown)"
  echo "# approved-at: $(date '+%Y-%m-%d %H:%M:%S')"
  protected_hashes
} > "$H/approved.sha256"
echo "承認しました。$H/approved.sha256 をコミットしてください。"
