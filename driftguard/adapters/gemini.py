"""Gemini CLI: ~/.gemini/tmp/<hash>/chats/*.json (conversations) and <hash>/logs.json (prompt log fallback)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .. import paths
from ..schema import Session, empty_tokens
from . import common


def discover() -> List[str]:
    out: List[str] = []
    for r in paths.gemini_roots():
        out += [str(f) for f in sorted(r.glob("*/chats/*.json"))]
        out += [str(f) for f in sorted(r.glob("*/logs.json"))]
    return out


def _text(c) -> str:
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in c)
    if isinstance(c, dict):
        return str(c.get("text") or "")
    return ""


def _int(d, *keys) -> int:
    for k in keys:
        try:
            v = (d or {}).get(k)
            if v:
                return int(v)
        except (TypeError, ValueError):
            pass
    return 0


def _hash_dir(p: Path) -> str:
    return p.parent.parent.name if p.parent.name == "chats" else p.parent.name


def _finish(s: Session, ts: list, path: str, h: str) -> List[Session]:
    if not ts:
        return []
    s["start"], s["end"] = min(ts), max(ts)
    s["project"] = common.project_name(s.get("cwd"), (h or "gemini")[:8])
    s["bot"] = common.looks_bot(s["prompts"][0]["txt"] if s["prompts"] else None, path)
    return [s]


def _parse_logs(p: Path, data: list) -> List[Session]:
    by: dict = {}
    for e in data:
        if isinstance(e, dict) and e.get("type", "user") == "user" and e.get("sessionId"):
            by.setdefault(e["sessionId"], []).append(e)
    out = []
    for sid, es in by.items():
        s: Session = {"agent": "gemini", "id": sid, "source": str(p), "prompts": [], "tools": 0, "tokens": empty_tokens(),
                      "models": {}, "usage": [], "files": [], "todos": []}
        ts = []
        for e in es:
            txt = common.clean_prompt(_text(e.get("message")))
            if txt and not common.is_skip(txt):
                s["prompts"].append({"t": e.get("timestamp", ""), "txt": txt})
            if e.get("timestamp"):
                ts.append(e["timestamp"])
        out += _finish(s, ts, str(p), _hash_dir(p))
    return out


def parse(path: str) -> List[Session]:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ValueError):
        return []
    if isinstance(data, list):
        return _parse_logs(p, data)
    if not isinstance(data, dict):
        return []
    s: Session = {"agent": "gemini", "id": data.get("sessionId") or p.stem, "source": path, "prompts": [], "tools": 0,
                  "tokens": empty_tokens(), "models": {}, "usage": [], "files": [], "todos": []}
    h = data.get("projectHash") or _hash_dir(p)
    if data.get("cwd"):
        s["cwd"] = data["cwd"]
    ts = [x for x in (data.get("startTime"), data.get("lastUpdated")) if x]
    tk = s["tokens"]
    for m in data.get("messages") or []:
        if not isinstance(m, dict):
            continue
        when = m.get("timestamp", "")
        if when:
            ts.append(when)
        typ = m.get("type")
        if typ == "user":
            txt = common.clean_prompt(_text(m.get("content")))
            if txt and not common.is_skip(txt):
                s["prompts"].append({"t": when, "txt": txt})
        elif typ in ("gemini", "model", "assistant"):
            if m.get("model"):
                s["models"][m["model"]] = s["models"].get(m["model"], 0) + 1
            s["tools"] += len(m.get("toolCalls") or [])
            t = m.get("tokens")
            if isinstance(t, dict):
                cached = _int(t, "cached")
                tk["input"] += max(0, _int(t, "input") - cached)
                tk["output"] += _int(t, "output") + _int(t, "thoughts")
                tk["cache_read"] += cached
                s["usage"].append([when, _int(t, "total") or _int(t, "input") + _int(t, "output")])
    return _finish(s, ts, path, h)
