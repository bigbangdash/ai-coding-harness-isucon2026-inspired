"""ハーネスの variant を比較する。experiments/results/<task>/<variant>/<日時>/summary.json を集計する。

  python3 harness/tune/experiments/compare.py              # 全課題
  python3 harness/tune/experiments/compare.py --task fake

同じ課題・同じモデル・同じ制約で、variant ごとに複数回走らせてから比べる。
「成功」= 最終走行が正常性検証に合格したこと（最終スコア > 0）。
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"


def fmt(v: float | None, digits: int = 0) -> str:
    return "-" if v is None else f"{v:,.{digits}f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task")
    a = ap.parse_args()

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for f in sorted(RESULTS.glob("*/*/*/summary.json")):
        task, variant = f.parts[-4], f.parts[-3]
        if a.task and task != a.task:
            continue
        groups[(task, variant)].append(json.loads(f.read_text()))
    if not groups:
        print(f"結果がありません: {RESULTS}")
        return

    print("| 課題 | variant | 回数 | 成功率 | 最終スコア（中央値） | 最良（中央値） | ベンチ回数 | Critic | 再起動 | コスト $ |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for (task, variant), runs in sorted(groups.items()):
        med = lambda key: statistics.median([r[key] for r in runs if r.get(key) is not None] or [0])  # noqa: E731
        success = sum(1 for r in runs if r["final_score"] > 0) / len(runs)
        print(f"| {task} | {variant} | {len(runs)} | {success:.0%} | {fmt(med('final_score'))} | "
              f"{fmt(med('best_median'))} | {fmt(med('benchmarks'))} | {fmt(med('critic_requests'))} | "
              f"{fmt(med('restarts'))} | {fmt(med('cost_usd'), 2)} |")


if __name__ == "__main__":
    main()
