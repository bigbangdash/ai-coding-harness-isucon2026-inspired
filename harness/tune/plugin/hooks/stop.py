#!/usr/bin/env python3
"""Stop Hook。競技時間内に Claude が応答を終えようとしたら止めて、続きを指示する。

shutdown（停止判断済み・時間切れ）のときだけ終了を許す。features.stop_hook = false なら何もしない。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runner"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402
import lifecycle  # noqa: E402
import stagnation  # noqa: E402

REASON = {
    "bootstrap": "まだ有効なベンチ結果がない。環境・ログを調べ、ベースラインを測定する（evaluator/benchmark.py）。",
    "optimization": "競技時間が残っている。計測結果からボトルネックを特定し、次の改善を試す。",
    "finalization": "終盤。新規改善より最終検証を優先し、final_run.py check を通す。",
    "final_run": "最終走行中。ベンチを実行し、final_run.py decide が STOP を出すまで続ける。",
}


def main() -> None:
    if not core.is_tune_mode():
        return
    json.load(sys.stdin)
    if not core.feature("stop_hook"):
        return
    st = lifecycle.update_phase()
    if not st or st.get("phase") == "shutdown":
        return
    best = st.get("best") or {}
    lines = [f"残り {core.remaining_minutes(st):.0f} 分（phase: {st['phase']}）。終了しない。", REASON[st["phase"]]]
    if best:
        lines.append(f"最良: {best.get('median', 0):.0f}（{best.get('exp_id')} / {best.get('commit')}）")
    lines.extend(stagnation.notices())
    core.event("stop_blocked", phase=st["phase"])
    print(json.dumps({"decision": "block", "reason": "\n".join(lines)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
