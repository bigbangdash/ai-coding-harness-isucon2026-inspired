"""Competition Runner。競技時間・Claude Code の起動・監視・再起動・終了を管理する。

  python3 harness/tune/runner/main.py                       # 本番（competition.toml のまま）
  python3 harness/tune/runner/main.py --task experiments/tasks/fake.toml --variant experiments/variants/B-no-critic.toml --duration 30
  python3 harness/tune/runner/main.py --dry-run             # 起動コマンドだけ表示

--task / --variant を付けると、終了後に runtime/ を experiments/results/<task>/<variant>/<日時>/ に保存する。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402
import lifecycle  # noqa: E402
import session  # noqa: E402


def resolve(p: str | None) -> Path | None:
    if not p:
        return None
    path = Path(p)
    return path if path.is_absolute() else (core.TUNE_DIR / path if (core.TUNE_DIR / path).exists() else Path.cwd() / path)


def init_runtime(pol: dict, fresh: bool) -> None:
    rt = core.runtime_dir()
    if (rt / "state.json").exists():
        if not fresh:
            sys.exit(f"{rt}/state.json が既にあります。続きから再開するなら --resume、作り直すなら --fresh")
        backup = rt.with_name(f"{rt.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.move(str(rt), backup)
        print(f"既存の runtime を {backup} に退避しました")
        rt = core.runtime_dir()
    (rt / "checkpoints").mkdir(exist_ok=True)
    (rt / "policy.json").write_text(json.dumps(pol, ensure_ascii=False, indent=2))
    start = core.now()
    with core.state_tx() as st:
        st.update({
            "started_at": start,
            "deadline": start + core.get(pol, "competition.duration_minutes") * 60,
            "phase": "bootstrap",
            "best": None,
            "best_updated_at": start,
            "critic_requests": [],
            "announced": [],
            "final": {"checks_passed": False, "locked": False},
            "restarts": 0,
            "session_id": session.new_session_id(),
        })
    core.event("start", duration_minutes=core.get(pol, "competition.duration_minutes"))
    if core.get(pol, "features.decision_log", True):
        (rt / "decisions.md").write_text(
            "# 判断履歴\n\nbenchmark.py が試行を 1 行ずつ追記する。理由や気づきはその下に追記する。\n\n")


def run_task_setup(pol: dict) -> None:
    if cmd := core.get(pol, "task.setup"):
        code, out = core.run_shell(cmd, core.runtime_dir() / "task-setup.log")
        if code != 0:
            sys.exit(f"task.setup が失敗しました:\n{out}")


def run_claude(pol: dict, resume: bool) -> str:
    """Claude Code を起動し、終了理由（exited / deadline / locked）を返す。"""
    st = core.read_state()
    rt = core.runtime_dir()
    n = st.get("restarts", 0)
    cmd = session.build_command(pol, st["session_id"], resume)
    core.event("session_start", resume=resume, restart=n)
    with open(rt / f"claude-{n}.jsonl", "a") as out:
        proc = subprocess.Popen(cmd, cwd=core.REPO_ROOT, env=session.build_env(), stdin=subprocess.DEVNULL,
                                stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        interval = core.get(pol, "runner.monitor_interval_seconds", 10)
        while proc.poll() is None:
            time.sleep(interval)
            st = lifecycle.update_phase()
            if st.get("phase") == "shutdown":
                reason = "locked" if st.get("final", {}).get("locked") else "deadline"
                terminate(proc)
                return reason
    core.event("session_exit", code=proc.returncode)
    return "exited"


def terminate(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=30)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def summarize(pol: dict) -> dict:
    benches = core.read_jsonl("benchmarks.jsonl")
    events = core.read_jsonl("events.jsonl")
    st = core.read_state()
    last = benches[-1] if benches else None
    cost = 0.0
    for f in sorted(core.runtime_dir().glob("claude-*.jsonl")):
        for line in f.read_text().splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "result":
                cost += obj.get("total_cost_usd") or 0
    summary = {
        "final_score": last["score"] if last and last["correctness"] == "PASS" else 0,
        "final_correctness": last["correctness"] if last else None,
        "best_median": (st.get("best") or {}).get("median"),
        "benchmarks": len(benches),
        "critic_requests": len(st.get("critic_requests", [])),
        "restarts": st.get("restarts", 0),
        "locked_by_final_run": st.get("final", {}).get("locked", False),
        "cost_usd": round(cost, 4),
        "duration_minutes": round((core.now() - st["started_at"]) / 60, 1),
        "events": len(events),
        "features": core.get(pol, "features"),
    }
    (core.runtime_dir() / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def archive(task: Path | None, variant: Path | None) -> Path | None:
    if not (task or variant):
        return None
    dest = (core.TUNE_DIR / "experiments" / "results" / (task.stem if task else "default")
            / (variant.stem if variant else "baseline") / f"{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copytree(core.runtime_dir(), dest, ignore=shutil.ignore_patterns(".lock"))
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task")
    ap.add_argument("--variant")
    ap.add_argument("--duration", type=float, help="競技時間（分）。終盤の長さも同じ比率で縮める")
    ap.add_argument("--fresh", action="store_true", help="既存の runtime を退避して最初から")
    ap.add_argument("--resume", action="store_true", help="既存の runtime の続きから")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    task, variant = resolve(a.task), resolve(a.variant)
    pol = core.build_policy(task, variant)
    if a.duration:
        base = core.get(pol, "competition.duration_minutes")
        pol["competition"]["finalization_minutes"] = round(
            core.get(pol, "competition.finalization_minutes") * a.duration / base, 1)
        pol["competition"]["duration_minutes"] = a.duration
    if not core.get(pol, "commands.benchmark"):
        sys.exit("commands.benchmark が未設定です（policies/competition.toml か --task）")

    if a.dry_run:
        print(" ".join(session.build_command(pol, "<session-id>", False)))
        core.print_json(pol)
        return

    if not a.resume:
        init_runtime(pol, a.fresh)
        run_task_setup(pol)
    resume = a.resume
    max_restarts = core.get(pol, "runner.max_restarts", 3)
    while True:
        reason = run_claude(pol, resume)
        if reason in ("deadline", "locked"):
            break
        st = lifecycle.update_phase()
        if st.get("phase") == "shutdown":
            break
        if not core.get(pol, "runner.restart_on_failure", True) or st.get("restarts", 0) >= max_restarts:
            core.event("give_up", restarts=st.get("restarts", 0))
            break
        with core.state_tx() as s:
            s["restarts"] = s.get("restarts", 0) + 1
        core.event("restart", restarts=st.get("restarts", 0) + 1)
        resume = True

    with core.state_tx() as s:
        s["phase"] = "shutdown"
    core.event("shutdown")
    summary = summarize(pol)
    core.print_json(summary)
    if dest := archive(task, variant):
        print(f"結果を保存しました: {dest}")


if __name__ == "__main__":
    main()
