#!/usr/bin/env python3
"""Stop Hook。impl/* ブランチで、評価を通さずに作業を終えることを防ぐ。

終了を止める（block）のは次のとき:
  1. 変更後に evaluate.sh を実行していない（最後の評価の指紋が今の作業ツリーと違う）
  2. 最後の評価が FAIL
  3. PASS だが risk: high で、今の作業ツリーに対する evaluator の PASS がない
     （記録がない、FAIL、status が読めない、のいずれも止める）

BLOCKED（人間の判断が必要）は止めない。evaluator が BLOCKED を返した場合も同じ。
evaluator をバックグラウンドで起動して結果待ちの間（RUNNING、RUNNING_TTL 秒以内）は止めない。
同じ理由で続けて MAX_BLOCKS 回止めたら、無限ループを避けるため終了を許し、警告だけ出す。
"""
from __future__ import annotations

import json
import sys
import time

import common

MAX_BLOCKS = 3
RUNNING_TTL = 30 * 60


def reason() -> str | None:
    if not common.has_changes():
        return None
    fp = common.fingerprint()
    ev = common.last_eval()
    if ev.get("fingerprint") != fp:
        return "変更後に `harness/implement/evaluate.sh` を実行していない。実行して next_action に従う。"
    status = ev.get("status")
    if status == "BLOCKED":
        return None
    if status == "FAIL":
        return f"evaluate.sh が FAIL のまま。{ev.get('next_action') or 'findings を修正して再評価する'}"
    if status == "PASS" and ev.get("risk") == "high":
        mine = [r for r in common.reviews() if r["fingerprint"] == fp and r["agent"].endswith("evaluator")]
        if not mine:
            return "高リスクの変更（risk: high）。evaluator サブエージェントで設計評価を受ける（依頼文には機能名と scope だけ書く）。"
        last = mine[-1].get("status")
        if last in ("PASS", "BLOCKED"):
            return None
        if last == "RUNNING":
            if time.time() - started(mine[-1]) < RUNNING_TTL:
                return None
            return (f"evaluator の結果が {RUNNING_TTL // 60} 分たっても記録されていない（RUNNING のまま）。"
                    "SubagentStop Hook が動いているか確認し、evaluator をやり直す。")
        if last == "FAIL":
            return "evaluator が FAIL を返した。指摘を修正し、evaluate.sh と evaluator をやり直す。"
        return (f"evaluator の結果が PASS として記録されていない（status: {last}）。"
                "`.harness/reviews/` を確認し、必要なら evaluator をやり直す。")
    return None


def started(rec: dict) -> float:
    try:
        return time.mktime(time.strptime(rec["ts"], "%Y%m%d-%H%M%S"))
    except (KeyError, ValueError):
        return 0.0


def main() -> None:
    if not common.active():
        return
    json.load(sys.stdin)
    state = common.HARNESS / "state"
    state.mkdir(parents=True, exist_ok=True)
    counter = state / f"stop-blocks-{common.branch().replace('/', '_')}"
    try:
        prev = json.loads(counter.read_text())
    except (FileNotFoundError, ValueError):
        prev = {}
    prev = prev if isinstance(prev, dict) else {}

    r = reason()
    if r is None:
        counter.unlink(missing_ok=True)
        return
    n = prev.get("n", 0) if prev.get("reason") == r else 0  # 理由が変わった = 前進したので数え直す
    if n >= MAX_BLOCKS:
        counter.unlink(missing_ok=True)
        print(json.dumps({"systemMessage": f"Stop Hook: 同じ理由で {MAX_BLOCKS} 回止めても解消しないまま終了します。理由: {r}"},
                         ensure_ascii=False))
        return
    counter.write_text(json.dumps({"reason": r, "n": n + 1}, ensure_ascii=False))
    print(json.dumps({"decision": "block", "reason": r}, ensure_ascii=False))


if __name__ == "__main__":
    main()
