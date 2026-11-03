"""ベンチマーカー出力の解釈とスコア分布の計算。"""
from __future__ import annotations

import re
import statistics


def parse_score(output: str, regex: str) -> float | None:
    m = re.search(regex, output) if regex else None
    return float(m.group(1)) if m else None


def is_pass(output: str, exit_code: int, regex: str) -> bool:
    if exit_code != 0:
        return False
    return bool(re.search(regex, output)) if regex else True


def quantile(values: list[float], q: float) -> float:
    s = sorted(values)
    if not s:
        return 0.0
    pos = (len(s) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "median": statistics.median(values),
        "p25": quantile(values, 0.25),
        "p75": quantile(values, 0.75),
        "min": min(values),
        "max": max(values),
        "stdev": round(statistics.stdev(values), 1) if len(values) > 1 else 0.0,
    }


def commit_samples(benches: list[dict], commit: str) -> tuple[list[float], bool]:
    """そのコミットの有効スコア一覧と、1 回でも正常性検証に落ちたか。"""
    rows = [b for b in benches if b.get("commit") == commit]
    valid = [b["score"] for b in rows if b["correctness"] == "PASS"]
    return valid, any(b["correctness"] != "PASS" for b in rows)
