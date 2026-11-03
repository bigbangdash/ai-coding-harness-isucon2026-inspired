#!/usr/bin/env python3
"""PostToolUse Hook（Agent ツール）。evaluator / critic の出力を .harness/reviews/ に保存する。

メインエージェントの要約ではなく、サブエージェントが返した原文を、その時点の作業ツリーの指紋と一緒に残す。
Stop Hook はこの記録を見て「高リスク変更が evaluator の PASS を得たか」を判定する。
"""
from __future__ import annotations

import json
import sys
import time

import common

TRACKED = ("evaluator", "critic")


def texts(obj) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        if isinstance(obj.get("text"), str):
            return [obj["text"]]
        return [t for v in obj.values() for t in texts(v)]
    if isinstance(obj, list):
        return [t for v in obj for t in texts(v)]
    return []


def main() -> None:
    if not common.active():
        return
    data = json.load(sys.stdin)
    agent = (data.get("tool_input") or {}).get("subagent_type", "")
    if agent.split(":")[-1] not in TRACKED:
        return
    body = "\n".join(texts(data.get("tool_response")))
    ts = time.strftime("%Y%m%d-%H%M%S")
    rec = {
        "ts": ts,
        "agent": agent,
        "branch": common.branch(),
        "fingerprint": common.fingerprint(),
        "status": common.yaml_field(body, "status"),
        "scope": common.yaml_field(body, "scope"),
    }
    d = common.HARNESS / "reviews"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{ts}-{agent.split(':')[-1]}.md").write_text(
        "\n".join(f"<!-- {k}: {v} -->" for k, v in rec.items()) + "\n\n" + body)
    with open(d / "index.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
