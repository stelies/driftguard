"""Claude Code: ~/.claude/projects/<sanitized-cwd>/<session>.jsonl (one JSON event per line)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .. import paths
from ..schema import Session, empty_tokens
from . import common

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Read"}


def discover() -> List[str]:
    return [str(f) for r in paths.claude_roots() for f in sorted(r.glob("*/*.jsonl"))]


def _text(content) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return None


def parse(path: str) -> List[Session]:
    p = Path(path)
    s: Session = {"agent": "claude", "id": p.stem, "source": path, "prompts": [], "tools": 0, "tokens": empty_tokens(),
                  "models": {}, "usage": [], "files": [], "todos": []}
    ts: list = []
    seen_msg = set()
    files: dict = {}
    for line in p.open(encoding="utf-8", errors="ignore"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        t = o.get("type")
        if t == "ai-title":
            s["title"] = o.get("aiTitle")
        if o.get("timestamp"):
            ts.append(o["timestamp"])
        if o.get("cwd") and "cwd" not in s:
            s["cwd"] = o["cwd"]
        msg = o.get("message") or {}
        if t == "assistant":
            c = msg.get("content")
            if isinstance(c, list):
                for b in c:
                    if not isinstance(b, dict) or b.get("type") != "tool_use":
                        continue
                    s["tools"] += 1
                    inp = b.get("input") or {}
                    if b.get("name") in FILE_TOOLS and inp.get("file_path"):
                        files[inp["file_path"]] = files.get(inp["file_path"], 0) + 1
                    if b.get("name") == "TodoWrite" and isinstance(inp.get("todos"), list):
                        s["todos"] = [f"[{x.get('status', '?')}] {x.get('content', '')}" for x in inp["todos"] if isinstance(x, dict)]
            u = msg.get("usage")
            mid = msg.get("id")
            if isinstance(u, dict) and mid not in seen_msg:  # streamed turns repeat the same message id
                seen_msg.add(mid)
                tk = s["tokens"]
                tk["input"] += int(u.get("input_tokens") or 0)
                tk["output"] += int(u.get("output_tokens") or 0)
                tk["cache_read"] += int(u.get("cache_read_input_tokens") or 0)
                tk["cache_write"] += int(u.get("cache_creation_input_tokens") or 0)
                tot = sum(int(u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
                s["usage"].append([o.get("timestamp", ""), tot])
                if msg.get("model"):
                    s["models"][msg["model"]] = s["models"].get(msg["model"], 0) + 1
        if t != "user" or o.get("isMeta") or o.get("isSidechain"):
            continue
        txt = _text(msg.get("content"))
        if not txt:
            continue
        txt = common.clean_prompt(txt)
        if common.is_skip(txt):
            continue
        s["prompts"].append({"t": o.get("timestamp", ""), "txt": txt})
    if not ts:
        return []
    s["start"], s["end"] = min(ts), max(ts)
    s["files"] = [f for f, _ in sorted(files.items(), key=lambda kv: -kv[1])[:30]]
    s["project"] = common.project_name(s.get("cwd"), p.parent.name)
    s["bot"] = common.looks_bot(s["prompts"][0]["txt"] if s["prompts"] else None, path)
    return [s]
