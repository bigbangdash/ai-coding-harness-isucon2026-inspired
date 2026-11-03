"""Benchmark Evaluator。1 回の試行を実行・記録し、採否の判定を返す。

  python3 harness/tune/evaluator/benchmark.py --hypothesis "DB アクセスが遅延の主因" --change "読み取りをインメモリ化"
  python3 harness/tune/evaluator/benchmark.py --remeasure     # 同じコミットを再測定（RETEST のとき）

やること:
  1. 作業ディレクトリの未コミット変更を自動コミット（スコアとコミットを必ず対応させる）
  2. deploy → regression → ベンチマーカー
  3. benchmarks.jsonl に記録し、最良の有効コミットと比べて verdict を出す
     KEEP（最良を更新）/ RETEST（差がノイズ以下。再測定）/ REVERT（悪化）/ INVALID（正常性検証に不合格）
     SAME_AS_BEST（最良と同じコミットの再測定）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402
import regression  # noqa: E402
import score  # noqa: E402


def next_exp_id() -> str:
    return f"exp-{len(core.read_jsonl('benchmarks.jsonl')) + 1:03d}"


def commit_workdir(wd: Path, exp_id: str, hypothesis: str) -> str:
    if core.git(wd, "status", "--porcelain"):
        core.git(wd, "add", "-A")
        core.git(wd, "commit", "-q", "-m", f"{exp_id}: {hypothesis or 'remeasure'}")
    commit = core.git(wd, "rev-parse", "--short", "HEAD")
    core.git(wd, "tag", "-f", f"isu/{exp_id}", commit)  # restore.sh で reset しても辿れるように
    return commit


def judge(benches: list[dict], commit: str, best: dict | None, noise_pct: float) -> tuple[str, dict]:
    samples, ever_failed = score.commit_samples(benches, commit)
    info = {"commit_samples": len(samples), "commit_median": score.stats(samples).get("median")}
    if ever_failed or not samples:
        return "INVALID", info
    median = info["commit_median"]
    if not best:
        return "KEEP", info
    if commit == best["commit"]:
        return "SAME_AS_BEST", info
    gain = (median - best["median"]) / best["median"] * 100 if best["median"] else float("inf")
    info["gain_pct"] = round(gain, 2)
    if gain > noise_pct:
        return "KEEP", info
    if gain > 0:
        return ("KEEP" if len(samples) >= 2 else "RETEST"), info
    return "REVERT", info


HINTS = {
    "KEEP": "最良を更新した。次のボトルネックを探す",
    "RETEST": "改善幅がノイズ以下。--remeasure で再測定してから判断する",
    "REVERT": "最良より悪い。原因を確認し、不要なら restore.sh で最良に戻す",
    "INVALID": "正常性検証に不合格。ログで失敗理由を確認して直すか、restore.sh で最良に戻す",
    "SAME_AS_BEST": "最良と同じコミットの再測定。分布に加えた",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hypothesis", default="")
    ap.add_argument("--change", default="")
    ap.add_argument("--remeasure", action="store_true")
    ap.add_argument("--no-deploy", action="store_true")
    a = ap.parse_args()
    if not a.remeasure and not a.hypothesis:
        sys.exit("--hypothesis を指定してください（再測定なら --remeasure）")

    pol = core.policy()
    st = core.read_state()
    if st.get("final", {}).get("locked") or st.get("phase") == "shutdown":
        sys.exit("最終走行の停止判断が済んでいる（shutdown）。これ以上ベンチマークを実行しない")

    rt = core.runtime_dir()
    exp_id = next_exp_id()
    wd = core.workdir(pol)
    commit = commit_workdir(wd, exp_id, a.hypothesis)
    log_dir = rt / "logs" / exp_id
    t0 = core.now()

    deploy_ok = True
    if core.get(pol, "benchmark.deploy_before", True) and not a.no_deploy and (cmd := core.get(pol, "commands.deploy")):
        code, _ = core.run_shell(cmd, log_dir / "deploy.log", timeout=600)
        deploy_ok = code == 0

    reg_ok, _ = regression.run(f"{exp_id}/regression.log") if deploy_ok else (False, "")

    bench_score, passed, out = 0.0, False, ""
    if deploy_ok and reg_ok is not False:
        code, out = core.run_shell(core.get(pol, "commands.benchmark"), log_dir / "benchmark.log",
                                   timeout=core.get(pol, "benchmark.timeout_seconds", 300))
        passed = score.is_pass(out, code, core.get(pol, "benchmark.pass_regex", ""))
        bench_score = score.parse_score(out, core.get(pol, "benchmark.score_regex", "")) or 0.0
    correctness = "PASS" if passed else "FAIL"

    best = st.get("best")
    record = {
        "experiment_id": exp_id,
        "ts": t0,
        "duration_seconds": round(core.now() - t0, 1),
        "phase": st.get("phase"),
        "hypothesis": a.hypothesis or ("(remeasure)" if a.remeasure else ""),
        "change": a.change,
        "commit": commit,
        "deploy": "PASS" if deploy_ok else "FAIL",
        "regression": {True: "PASS", False: "FAIL", None: "NOT_CONFIGURED"}[reg_ok],
        "correctness": correctness,
        "score": bench_score if passed else 0.0,
        "raw_score": bench_score,
        "score_before": best["median"] if best else None,
        "log": str(log_dir),
    }
    benches = core.read_jsonl("benchmarks.jsonl") + [record]
    verdict, info = judge(benches, commit, best, core.get(pol, "evaluation.noise_pct", 3.0))
    record.update(info, decision=verdict)
    core.append_jsonl("benchmarks.jsonl", record)

    with core.state_tx() as s:
        if verdict == "KEEP":
            s["best"] = {"commit": commit, "median": info["commit_median"], "exp_id": exp_id,
                         "hypothesis": record["hypothesis"]}
            s["best_updated_at"] = core.now()
            (rt / "checkpoints" / f"{exp_id}.json").write_text(
                json.dumps(s["best"], ensure_ascii=False, indent=2))
            core.event("best_updated", **s["best"])
        elif verdict == "SAME_AS_BEST" and s.get("best"):
            s["best"]["median"] = info["commit_median"]

    if core.get(pol, "features.decision_log", True):
        with open(rt / "decisions.md", "a") as f:
            before = f"{best['median']:.0f}" if best else "-"
            f.write(f"- {exp_id} `{commit}` {record['hypothesis']} / {a.change or '-'} : "
                    f"{before} → {record['score']:.0f}（{correctness}）→ **{verdict}**\n")

    core.print_json({
        "experiment_id": exp_id,
        "commit": commit,
        "correctness": correctness,
        "score": record["score"],
        "best_before": best,
        **info,
        "decision": verdict,
        "next": HINTS[verdict],
        "log": str(log_dir),
    })
    return 0 if correctness == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
