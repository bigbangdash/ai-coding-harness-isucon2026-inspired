#!/usr/bin/env python3
"""Stop Hook。impl/* ブランチで、評価を通さずに作業を終えることを防ぐ。

終了を止める（block）のは次のとき:
  1. 変更後に evaluate.sh を実行していない（最後の評価の指紋が今の作業ツリーと違う）
  2. 最後の評価が FAIL
  3. PASS だが risk: high で、今の作業ツリーに対する evaluator の PASS がない
  4. evaluator の結果が FAIL

BLOCKED（人間の判断が必要）は止めない。そのまま人間に返す。
同じブランチで続けて MAX_BLOCKS 回止めたら、無限ループを避けるため終了を許し、警告だけ出す。
"""
from __future__ import annotations

import json
import sys

import common

MAX_BLOCKS = 3


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
        last = mine[-1]["status"]
        if last == "FAIL":
            return "evaluator が FAIL を返した。指摘を修正し、evaluate.sh と evaluator をやり直す。"
    return None


def main() -> None:
    if not common.active():
        return
    json.load(sys.stdin)
    state = common.HARNESS / "state"
    state.mkdir(parents=True, exist_ok=True)
    counter = state / f"stop-blocks-{common.branch().replace('/', '_')}"
    n = int(counter.read_text()) if counter.exists() else 0

    r = reason()
    if r is None:
        counter.write_text("0")
        return
    if n >= MAX_BLOCKS:
        counter.write_text("0")
        print(json.dumps({"systemMessage": f"Stop Hook: {MAX_BLOCKS} 回止めても評価が通らないまま終了します。理由: {r}"},
                         ensure_ascii=False))
        return
    counter.write_text(str(n + 1))
    print(json.dumps({"decision": "block", "reason": r}, ensure_ascii=False))


if __name__ == "__main__":
    main()
