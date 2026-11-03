"""Claude Code セッションの起動コマンドを組み立てる。"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core  # noqa: E402

START_PROMPT = "harness/tune/CONDITIONS.md を読み、競技を開始してください。"
RESUME_PROMPT = (
    "セッションが中断され、Runner が再開しました。"
    "`python3 harness/tune/runner/lifecycle.py status` で状況を確認し、続けてください。"
)


def new_session_id() -> str:
    return str(uuid.uuid4())


def build_command(pol: dict, session_id: str, resume: bool) -> list[str]:
    cmd = [
        "claude", "-p", RESUME_PROMPT if resume else START_PROMPT,
        "--output-format", "stream-json", "--verbose",
        "--append-system-prompt-file", str(core.TUNE_DIR / "CLAUDE.md"),
        "--plugin-dir", str(core.TUNE_DIR / "plugin"),
        "--permission-mode", "bypassPermissions",
    ]
    cmd += ["--resume", session_id] if resume else ["--session-id", session_id]
    if model := core.get(pol, "runner.model"):
        cmd += ["--model", model]
    if (budget := core.get(pol, "runner.max_budget_usd", 0)) and budget > 0:
        cmd += ["--max-budget-usd", str(budget)]
    return cmd


def build_env() -> dict:
    env = dict(os.environ)
    env["HARNESS_MODE"] = "tune"
    env["ISUCON_RUNTIME"] = str(core.runtime_dir())
    return env
