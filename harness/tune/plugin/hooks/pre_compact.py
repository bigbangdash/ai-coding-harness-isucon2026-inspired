#!/usr/bin/env python3
"""Compaction 対策。

  PreCompact   : 外部状態のスナップショットを runtime/checkpoints/ に保存する
  SessionStart : Compaction 後・再開後に、外部状態（フェーズ・最良・直近の判断）を Claude に注入する

features.state_restore = false なら注入しない（保存はする）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runner"))
import core  # noqa: E402
import lifecycle  # noqa: E402

RECENT = 12


def snapshot() -> dict:
    st = lifecycle.update_phase()
    benches = core.read_jsonl("benchmarks.jsonl")
    return {"state": st, "recent_experiments": benches[-RECENT:]}


def context_text() -> str:
    st = lifecycle.update_phase()
    if not st:
        return ""
    best = st.get("best") or {}
    lines = [
        "## 外部状態（ハーネスが保存したもの。会話の記憶より優先する）",
        f"- phase: {st['phase']} / 残り {core.remaining_minutes(st):.0f} 分",
        f"- 最良: {best.get('median', 0):.0f}（{best.get('exp_id')} / commit {best.get('commit')} / {best.get('hypothesis')}）"
        if best else "- 最良: まだない",
        f"- Critic 依頼: {len(st.get('critic_requests', []))} 回 / 最終検証: {st.get('final', {})}",
    ]
    if core.feature("decision_log"):
        lines.append(f"\n## 直近 {RECENT} 件の試行（全件は runtime/benchmarks.jsonl と decisions.md）")
        for b in core.read_jsonl("benchmarks.jsonl")[-RECENT:]:
            lines.append(f"- {b['experiment_id']} {b['commit']} {b['hypothesis']} → {b['score']:.0f} "
                         f"{b['correctness']} {b.get('decision')}")
    return "\n".join(lines)


def main() -> None:
    if not core.is_tune_mode():
        return
    data = json.load(sys.stdin)
    event = data.get("hook_event_name")
    if event == "PreCompact":
        path = core.runtime_dir() / "checkpoints" / f"context-{int(core.now())}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(snapshot(), ensure_ascii=False, indent=2))
        core.event("pre_compact", trigger=data.get("trigger"), snapshot=str(path))
    elif event == "SessionStart":
        core.event("session_start_hook", source=data.get("source"))
        if core.feature("state_restore") and (text := context_text()):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                     "additionalContext": text}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
