"""ベンチ前の簡易な正常性確認（commands.regression）。未設定なら何もしない。

  python3 harness/tune/evaluator/regression.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core  # noqa: E402


def run(log_name: str = "regression.log") -> tuple[bool | None, str]:
    """(True=合格 / False=不合格 / None=未設定, ログのパス)"""
    cmd = core.get(core.policy(), "commands.regression")
    if not cmd:
        return None, ""
    log = core.runtime_dir() / "logs" / log_name
    code, _ = core.run_shell(cmd, log, timeout=600)
    return code == 0, str(log)


if __name__ == "__main__":
    ok, log = run()
    core.print_json({"regression": {True: "PASS", False: "FAIL", None: "NOT_CONFIGURED"}[ok], "log": log})
    sys.exit(0 if ok is not False else 1)
