#!/usr/bin/env python3
"""evaluator / critic の出力を .harness/reviews/ に保存する Hook。

メインエージェントの要約ではなく、サブエージェントが返した原文を、その時点の作業ツリーの指紋と一緒に残す。
Stop Hook はこの記録を見て「高リスク変更が evaluator の PASS を得たか」を判定する。

2 つのイベントで呼ばれる:
  - SubagentStop: サブエージェントが終わったとき。最終回答を記録する（主経路）
  - PostToolUse（Agent ツール）: 同期実行なら結果をその場で記録する。
    バックグラウンド起動（async_launched）ならまだ結果がないので、RUNNING として起動だけ記録する
同じ agent_id は二重に記録しない（status が RUNNING の記録は上書き扱い）。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

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


def find_key(obj, key: str):
    if isinstance(obj, dict):
        if isinstance(obj.get(key), str):
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r:
                return r
    if isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r:
                return r
    return None


def is_async(resp) -> bool:
    return "async_launched" in texts(resp)


def last_assistant_text(transcript: Path) -> str:
    """サブエージェントの JSONL から、最後に返したテキストを取り出す。"""
    last = ""
    for line in transcript.read_text().splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") != "assistant":
            continue
        t = "\n".join(c.get("text", "") for c in (e.get("message") or {}).get("content") or []
                      if isinstance(c, dict) and c.get("type") == "text")
        if t.strip():
            last = t
    return last


def agent_type_from_meta(transcript: Path) -> str:
    meta = transcript.with_suffix(".meta.json")
    try:
        return json.loads(meta.read_text()).get("agentType", "")
    except (FileNotFoundError, ValueError):
        return ""


def record(agent: str, agent_id: str | None, body: str, source: str, status: str | None = None) -> None:
    name = agent.split(":")[-1]
    if name not in TRACKED:
        return
    d = common.HARNESS / "reviews"
    if agent_id and any(r.get("agent_id") == agent_id and r.get("status") != "RUNNING"
                        for r in common.reviews()):
        return  # 同期実行で PostToolUse と SubagentStop の両方から来た場合
    ts = time.strftime("%Y%m%d-%H%M%S")
    rec = {
        "ts": ts,
        "agent": agent,
        "agent_id": agent_id,
        "source": source,
        "branch": common.branch(),
        "fingerprint": common.fingerprint(),
        "status": status or common.yaml_field(body, "status"),
        "scope": common.yaml_field(body, "scope"),
    }
    d.mkdir(parents=True, exist_ok=True)
    suffix = f"-{agent_id[:12]}" if agent_id else ""
    suffix += "-running" if rec["status"] == "RUNNING" else ""
    (d / f"{ts}-{name}{suffix}.md").write_text(
        "\n".join(f"<!-- {k}: {v} -->" for k, v in rec.items()) + "\n\n" + body)
    with open(d / "index.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def on_post_tool_use(data: dict) -> None:
    agent = (data.get("tool_input") or {}).get("subagent_type", "")
    resp = data.get("tool_response")
    agent_id = find_key(resp, "agentId")
    if is_async(resp):
        record(agent, agent_id, "（バックグラウンドで実行中。結果は SubagentStop で記録する）",
               "PostToolUse", status="RUNNING")
        return
    record(agent, agent_id, "\n".join(texts(resp)), "PostToolUse")


def on_subagent_stop(data: dict) -> None:
    tp = data.get("agent_transcript_path")
    transcript = Path(tp) if tp else None
    agent = data.get("agent_type") or (agent_type_from_meta(transcript) if transcript else "")
    body = data.get("last_assistant_message") or ""
    if not body and transcript and transcript.exists():
        body = last_assistant_text(transcript)
    record(agent, data.get("agent_id"), body, "SubagentStop")


def main() -> None:
    if not common.active():
        return
    data = json.load(sys.stdin)
    if data.get("hook_event_name") == "SubagentStop":
        on_subagent_stop(data)
    else:
        on_post_tool_use(data)


if __name__ == "__main__":
    main()
