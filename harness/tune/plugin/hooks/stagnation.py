#!/usr/bin/env python3
"""停滞の検出（共通関数）と、PostToolUse Hook としての通知。

check() は Runner・lifecycle・Stop Hook からも使う。
Hook としては Bash 実行のたびに呼ばれ、次のときだけ Claude に追加コンテキストを返す。
  - 最高スコアが threshold_minutes 更新されていない（同じ最良につき 1 回だけ Critic を促す）
  - 終盤（finalization）・最終走行（final_run）に入った（各 1 回）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runner"))
import core  # noqa: E402


def check(st: dict, pol: dict, t: float | None = None) -> dict:
    t = t or core.now()
    minutes = (t - st.get("best_updated_at", t)) / 60
    threshold = core.get(pol, "stagnation.threshold_minutes", 30)
    best_id = (st.get("best") or {}).get("exp_id")
    already = any(r.get("best_exp_id") == best_id for r in st.get("critic_requests", []))
    return {
        "stagnant": st.get("phase") == "optimization" and minutes >= threshold,
        "minutes_since_best": round(minutes, 1),
        "threshold_minutes": threshold,
        "already_requested": already,
    }


PHASE_NOTICE = {
    "finalization": (
        "【終盤】残り {remaining:.0f} 分。新規の改善は止め、最終検証を優先する。"
        "提出する版（通常は最良コミット）に揃え、全サーバーの再起動と永続データを確認し、"
        "`python3 harness/tune/evaluator/final_run.py check` を通す。"
    ),
    "final_run": (
        "【最終走行】最終検証済み。ここからはコードを変えない。"
        "ベンチを実行するたびに `python3 harness/tune/evaluator/final_run.py decide` を実行し、STOP が出たら終了する。"
    ),
}


def notices() -> list[str]:
    import lifecycle  # noqa: E402

    st = lifecycle.update_phase()
    if not st:
        return []
    pol = core.policy()
    out: list[str] = []
    with core.state_tx() as s:
        phase = s.get("phase")
        announced = s.setdefault("announced", [])
        if phase in PHASE_NOTICE and phase not in announced:
            announced.append(phase)
            out.append(PHASE_NOTICE[phase].format(remaining=core.remaining_minutes(s)))
            core.event("notice", phase=phase)
        stg = check(s, pol)
        if core.feature("critic") and stg["stagnant"] and not stg["already_requested"]:
            best = s.get("best") or {}
            s.setdefault("critic_requests", []).append({"ts": core.now(), "best_exp_id": best.get("exp_id"),
                                                        "minutes_since_best": stg["minutes_since_best"]})
            core.event("critic_requested", **stg)
            out.append(
                f"【停滞】最高スコア {best.get('median', 0):.0f}（{best.get('exp_id')}）が "
                f"{stg['minutes_since_best']:.0f} 分更新されていない。"
                "isucon-tune:critic サブエージェントに判断履歴の監査を依頼し、提案は測定で確かめてから採用する。"
            )
    return out


def main() -> None:
    if not core.is_tune_mode():
        return
    json.load(sys.stdin)
    msgs = notices()
    if msgs:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": "\n".join(msgs)}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
