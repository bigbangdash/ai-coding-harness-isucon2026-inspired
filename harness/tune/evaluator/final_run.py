"""終盤の最終検証と、最終走行（最後のベンチ）をどこで止めるかの判断。

  python3 harness/tune/evaluator/final_run.py check                 # 再起動・永続性の確認（終盤に入ったら）
  python3 harness/tune/evaluator/final_run.py check --manual-ok "全台 reboot 後に初期化とログインを確認"
  python3 harness/tune/evaluator/final_run.py decide                # 最終走行を続けるか止めるか
  python3 harness/tune/evaluator/final_run.py lock --reason "..."   # 手動で止める

decide のルール（上から順に判定）:
  1. 最終検証後のベンチがまだない                        → RUN
  2. 残り時間 < 平均ベンチ所要時間 + safety_margin          → STOP（もう 1 回は間に合わない）
  3. 直近が正常性検証に不合格                            → RUN
  4. 同じコミットの有効スコアが min_samples 未満          → RUN（分布が分からない）
  5. 直近スコア >= 同じコミットの分布の stop_quantile 分位 → STOP
  6. それ以外                                            → RUN
STOP になると状態を lock し、以後のベンチ・デプロイ・変更は guard.py が拒否する。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402
import score  # noqa: E402


def lock(reason: str, **extra) -> None:
    with core.state_tx() as st:
        st.setdefault("final", {}).update(locked=True, lock_reason=reason, locked_at=core.now(), **extra)
        st["phase"] = "shutdown"
    core.event("final_lock", reason=reason, **extra)


def cmd_check(manual_ok: str | None) -> int:
    pol = core.policy()
    st = core.read_state()
    wd = core.workdir(pol)
    best = st.get("best")
    if not best:
        core.print_json({"result": "FAIL", "reason": "有効な最良コミットがない"})
        return 1
    if core.git(wd, "status", "--porcelain"):
        core.print_json({"result": "FAIL", "reason": "未コミットの変更がある。最終版をコミットしてから確認する"})
        return 1
    head = core.git(wd, "rev-parse", "--short", "HEAD")
    same_tree = subprocess.run(["git", "-C", str(wd), "diff", "--quiet", best["commit"], "HEAD"]).returncode == 0
    results = {}
    for key in ("reboot_check", "persist_check"):
        cmd = core.get(pol, f"commands.{key}")
        if not cmd:
            results[key] = "MANUAL_OK" if manual_ok else "NOT_CONFIGURED"
            continue
        code, _ = core.run_shell(cmd, core.runtime_dir() / "logs" / f"final-{key}.log", timeout=1800)
        results[key] = "PASS" if code == 0 else "FAIL"
    ok = all(v in ("PASS", "MANUAL_OK") for v in results.values())
    out = {"result": "PASS" if ok else "FAIL", "head": head, "best_commit": best["commit"],
           "head_matches_best": same_tree, **results}
    if not same_tree:
        out["warning"] = "HEAD が最良コミットと異なる。意図した提出版か確認する（最良に戻すなら tools/restore.sh）"
    if "NOT_CONFIGURED" in results.values():
        out["next"] = "確認コマンドが未設定。自分で再起動・永続性を確かめ、--manual-ok \"確認内容\" を付けて再実行する"
    if ok:
        with core.state_tx() as s:
            s.setdefault("final", {}).update(checks_passed=True, checked_commit=head, manual_ok=manual_ok)
        core.event("final_checks_passed", commit=head, **results)
        out["next"] = "最終走行に入る。ベンチを実行し、毎回 final_run.py decide で止めるか判断する"
    core.print_json(out)
    return 0 if ok else 1


def decide() -> dict:
    pol = core.policy()
    st = core.read_state()
    if not st.get("final", {}).get("checks_passed"):
        return {"decision": "NOT_READY", "reason": "先に final_run.py check を通す"}
    commit = st["final"]["checked_commit"]
    checked_at = next((e["ts"] for e in reversed(core.read_jsonl("events.jsonl"))
                       if e["kind"] == "final_checks_passed"), 0)
    benches = core.read_jsonl("benchmarks.jsonl")
    final_runs = [b for b in benches if b["ts"] >= checked_at]
    samples, _ = score.commit_samples(benches, commit)
    durations = [b["duration_seconds"] for b in benches if b.get("duration_seconds")]
    avg_min = (sum(durations) / len(durations) / 60) if durations else 2.0
    remaining = core.remaining_minutes(st)
    margin = core.get(pol, "final_run.safety_margin_minutes", 3)
    q = core.get(pol, "final_run.stop_quantile", 0.75)
    base = {"remaining_minutes": round(remaining, 1), "avg_bench_minutes": round(avg_min, 1),
            "distribution": score.stats(samples)}

    if not final_runs:
        return {"decision": "RUN", "reason": "最終検証後のベンチがまだない", **base}
    last = final_runs[-1]
    base["last"] = {"experiment_id": last["experiment_id"], "score": last["score"], "correctness": last["correctness"]}
    if remaining < avg_min + margin:
        warn = "" if last["correctness"] == "PASS" else "（直近は不合格。このまま終わるとスコア 0 の可能性）"
        return {"decision": "STOP", "reason": f"残り時間ではもう 1 回走らせられない{warn}", **base}
    if last["correctness"] != "PASS":
        return {"decision": "RUN", "reason": "直近が正常性検証に不合格", **base}
    if not core.get(pol, "final_run.use_score_distribution", True):
        return {"decision": "STOP", "reason": "直近が合格（分布は使わない設定）", **base}
    if len(samples) < core.get(pol, "final_run.min_samples", 2):
        return {"decision": "RUN", "reason": "同じコミットの有効スコアが少なく、分布が分からない", **base}
    threshold = score.quantile(samples, q)
    base["threshold"] = threshold
    if last["score"] >= threshold:
        return {"decision": "STOP", "reason": f"直近 {last['score']:.0f} が分布の {q:.0%} 分位 {threshold:.0f} 以上", **base}
    return {"decision": "RUN", "reason": f"直近 {last['score']:.0f} が分布の {q:.0%} 分位 {threshold:.0f} 未満", **base}


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--manual-ok")
    sub.add_parser("decide")
    lk = sub.add_parser("lock")
    lk.add_argument("--reason", required=True)
    a = ap.parse_args()

    if a.cmd == "check":
        return cmd_check(a.manual_ok)
    if a.cmd == "lock":
        lock(a.reason, by="agent")
        core.print_json({"locked": True, "reason": a.reason})
        return 0
    if not core.feature("final_run_tool"):
        core.print_json({"decision": "DISABLED",
                         "reason": "この設定では停止判断ツールは無効。自分で判断し、止めるときは final_run.py lock --reason を実行する"})
        return 0
    result = decide()
    if result["decision"] == "STOP":
        lock(result["reason"], by="final_run.decide", last=result.get("last"))
        result["next"] = "停止した。以後はベンチ・デプロイ・変更をしない。結果を報告して終了する"
    core.event("final_decide", decision=result["decision"], reason=result["reason"])
    core.print_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
