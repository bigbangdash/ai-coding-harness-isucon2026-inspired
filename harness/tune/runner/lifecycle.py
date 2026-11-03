"""実行フェーズの管理。フェーズは Runner と Hook が共有する「状態」で、作業手順ではない。

  bootstrap     有効なベンチ結果がまだない（環境構築・接続確認・ベースライン測定）
  optimization  改善の反復
  finalization  残り finalization_minutes 以下。新規改善より再起動・永続性の確認
  final_run     最終検証済み。停止判断ツールで最後のベンチをどこで止めるか決める
  shutdown      停止判断済み、または時間切れ。以後は変更しない

CLI:
  python3 harness/tune/runner/lifecycle.py status   # 現在の状況を JSON で出す
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core  # noqa: E402

PHASES = ["bootstrap", "optimization", "finalization", "final_run", "shutdown"]


def compute_phase(st: dict, pol: dict, t: float | None = None) -> str:
    final = st.get("final", {})
    if final.get("locked") or core.remaining_minutes(st, t) <= 0:
        return "shutdown"
    if final.get("checks_passed"):
        return "final_run"
    if core.remaining_minutes(st, t) <= core.get(pol, "competition.finalization_minutes", 40):
        return "finalization"
    if not st.get("best"):
        return "bootstrap"
    return "optimization"


def update_phase(t: float | None = None) -> dict:
    """フェーズを再計算し、変わっていればイベントを記録する。更新後の state を返す。"""
    pol = core.policy()
    with core.state_tx() as st:
        if not st:
            return st
        new = compute_phase(st, pol, t)
        old = st.get("phase")
        if new != old:
            st["phase"] = new
            st.setdefault("phase_history", []).append({"phase": new, "ts": t or core.now()})
            core.event("phase", old=old, new=new)
        return dict(st)


def status() -> dict:
    st = update_phase()
    if not st:
        return {"error": "runtime/state.json がありません（Runner が起動していない）"}
    sys.path.insert(0, str(core.TUNE_DIR / "plugin" / "hooks"))
    from stagnation import check as stagnation  # noqa: E402

    best = st.get("best") or {}
    return {
        "phase": st["phase"],
        "remaining_minutes": round(core.remaining_minutes(st), 1),
        "best": {k: best.get(k) for k in ("median", "commit", "exp_id", "hypothesis")} if best else None,
        "benchmarks": len(core.read_jsonl("benchmarks.jsonl")),
        "stagnation": stagnation(st, core.policy()),
        "final": st.get("final", {}),
    }


if __name__ == "__main__":
    if sys.argv[1:] == ["status"]:
        core.print_json(status())
    else:
        sys.exit("usage: lifecycle.py status")
