#!/usr/bin/env python3
"""PreToolUse Hook。競技中にしてはいけない操作を拒否する。

  - ハーネス自身（harness/tune/ と .claude/）の変更。ただし runtime/decisions.md への追記は許可
  - 評価記録（benchmarks.jsonl / state.json / events.jsonl）の書き換え
  - policies/competition.toml の guard.deny_patterns に一致する Bash
  - 停止判断（lock）後のベンチ・デプロイ・ファイル変更
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import core  # noqa: E402

RECORDS = ("benchmarks.jsonl", "state.json", "events.jsonl", "policy.json")
WRITE_OPS = re.compile(r"(>|\btee\b|\brm\b|\bmv\b|\bcp\b|sed\s+-i|\btruncate\b|perl\s+-i|\bdd\b)")
ALLOWED_WRITE = ("runtime/decisions.md",)


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))
    core.event("guard_deny", reason=reason)
    sys.exit(0)


def protected_path(path: str) -> bool:
    p = Path(path).resolve() if path else None
    if not p:
        return False
    rt = core.runtime_dir().resolve()
    if any(str(p).endswith(a) for a in ALLOWED_WRITE) or (p.is_relative_to(rt) and p.name == "decisions.md"):
        return False
    return p.is_relative_to(core.TUNE_DIR) or p.is_relative_to(rt) or p.is_relative_to(core.REPO_ROOT / ".claude")


def main() -> None:
    if not core.is_tune_mode():
        return
    data = json.load(sys.stdin)
    tool, inp = data.get("tool_name", ""), data.get("tool_input", {})
    st = core.read_state()
    locked = st.get("final", {}).get("locked")

    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = inp.get("file_path") or inp.get("notebook_path", "")
        if protected_path(path):
            deny(f"ハーネスと評価記録は変更できない: {path}")
        if locked:
            deny("最終走行の停止判断が済んでいる。以後ファイルを変更しない")
        return

    if tool != "Bash":
        return
    cmd = inp.get("command", "")
    for pat in core.get(core.policy(), "guard.deny_patterns", []):
        if re.search(pat, cmd):
            deny(f"競技ポリシーで禁止されたコマンド（{pat}）")
    scrubbed = re.sub(r"\d?>&\d|\d?>\s*/dev/null", "", cmd).replace("harness/tune/runtime/decisions.md", "")
    harness_tool = re.match(r"^\s*(python3\s+)?(\./)?harness/tune/(evaluator|runner|tools)/", cmd) \
        and not re.search(r";|&&|\|\|", scrubbed)
    if WRITE_OPS.search(scrubbed) and not harness_tool and (
            any(r in scrubbed for r in RECORDS) or "harness/tune/" in scrubbed or ".claude/" in scrubbed):
        deny("評価記録・ハーネスをシェルから書き換えない（記録は evaluator/*.py だけが書く）")
    if locked and re.search(r"(benchmark\.py|deploy\.sh|restore\.sh|systemctl\s+(restart|stop|start)|git\s+commit)", cmd):
        deny("最終走行の停止判断が済んでいる。ベンチ・デプロイ・変更はしない")


if __name__ == "__main__":
    main()
