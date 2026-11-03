"""implement の Hook の共通処理。"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])
HARNESS = ROOT / ".harness"
LIB = "harness/implement/lib.sh"


def sh(cmd: str) -> str:
    return subprocess.run(["bash", "-c", cmd], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def active() -> bool:
    """implement の作業ブランチ（impl/*）でだけ動く。tune の Runner から起動されたセッションでは動かない。"""
    return os.environ.get("HARNESS_MODE") != "tune" and branch().startswith("impl/")


def branch() -> str:
    return sh("git rev-parse --abbrev-ref HEAD")


def fingerprint() -> str:
    return sh(f". {LIB}; worktree_fingerprint $(eval_base)")


def has_changes() -> bool:
    return bool(sh(f". {LIB}; b=$(eval_base); git diff --name-only $b; git ls-files --others --exclude-standard"))


def yaml_field(text: str, key: str) -> str | None:
    m = re.search(rf"^\s*{key}:\s*\"?([^\"\n]+)\"?", text, re.M)
    return m.group(1).strip() if m else None


def last_eval() -> dict:
    p = HARNESS / "logs" / "last-eval.yaml"
    if not p.exists():
        return {}
    t = p.read_text()
    return {k: yaml_field(t, k) for k in ("status", "fingerprint", "risk", "next_action")}


def reviews() -> list[dict]:
    p = HARNESS / "reviews" / "index.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
