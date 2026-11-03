"""tune ハーネスの共通処理（パス・ポリシー・状態・ログ・git）。標準ライブラリだけで動く。

CLI:
  python3 harness/tune/core.py get commands.deploy   # 実効ポリシーの値を出す
"""
from __future__ import annotations

import contextlib
import copy
import fcntl
import json
import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path

TUNE_DIR = Path(__file__).resolve().parent
REPO_ROOT = TUNE_DIR.parent.parent
POLICY_FILE = TUNE_DIR / "policies" / "competition.toml"


# ---------- パス ----------

def runtime_dir() -> Path:
    d = Path(os.environ.get("ISUCON_RUNTIME") or TUNE_DIR / "runtime")
    d.mkdir(parents=True, exist_ok=True)
    return d


def is_tune_mode() -> bool:
    return os.environ.get("HARNESS_MODE") == "tune"


# ---------- ポリシー ----------

def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_toml(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def build_policy(task: Path | None = None, variant: Path | None = None) -> dict:
    """competition.toml に task → variant の順で上書きした実効ポリシー。"""
    policy = load_toml(POLICY_FILE)
    for p in (task, variant):
        if p:
            policy = deep_merge(policy, load_toml(p))
    return policy


def policy() -> dict:
    """Runner が runtime/policy.json に書いた実効ポリシー。なければ competition.toml。"""
    p = runtime_dir() / "policy.json"
    if p.exists():
        return json.loads(p.read_text())
    return build_policy()


def get(pol: dict, dotted: str, default=None):
    cur = pol
    for key in dotted.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def feature(name: str) -> bool:
    return bool(get(policy(), f"features.{name}", True))


def workdir(pol: dict | None = None) -> Path:
    wd = Path(get(pol or policy(), "app.workdir", "app"))
    return wd if wd.is_absolute() else REPO_ROOT / wd


# ---------- 状態（state.json） ----------

def now() -> float:
    return time.time()


def read_state() -> dict:
    p = runtime_dir() / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


@contextlib.contextmanager
def state_tx():
    """state.json をロックして読み書きする。with の中で dict を変更すると保存される。"""
    rt = runtime_dir()
    with open(rt / ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        st = read_state()
        yield st
        tmp = rt / "state.json.tmp"
        tmp.write_text(json.dumps(st, ensure_ascii=False, indent=2))
        tmp.replace(rt / "state.json")


def remaining_minutes(st: dict, t: float | None = None) -> float:
    if not st.get("deadline"):
        return float("inf")
    return (st["deadline"] - (t or now())) / 60


# ---------- ログ（jsonl） ----------

def append_jsonl(name: str, obj: dict) -> None:
    with open(runtime_dir() / name, "a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(name: str) -> list[dict]:
    p = runtime_dir() / name
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def event(kind: str, **kw) -> None:
    append_jsonl("events.jsonl", {"ts": now(), "kind": kind, **kw})


# ---------- git ----------

def git(wd: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(wd), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def run_shell(cmd: str, log_path: Path, timeout: int | None = None, cwd: Path | None = None) -> tuple[int, str]:
    """シェルコマンドを実行し、出力をログに保存して (exit code, 出力) を返す。"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd or REPO_ROOT)
        out, code = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        out += f"\n[timeout after {timeout}s]"
        code = 124
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(out)
    return code, out


def print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "get":
        v = get(policy(), sys.argv[2], "")
        print(v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False))
    elif len(sys.argv) == 2 and sys.argv[1] == "workdir":
        print(workdir())
    else:
        sys.exit("usage: core.py get <key> | core.py workdir")
