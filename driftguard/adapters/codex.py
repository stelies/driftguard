"""Codex CLI: ~/.codex/sessions/**/rollout-*.jsonl lines of {timestamp,type,payload}."""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path
from typing import List

from .. import paths
from ..schema import Session, empty_tokens
from . import common

_TOOL_TYPES = ("function_call", "local_shell_call", "custom_tool_call")
_SKIP_PREFIXES = ("<environment_context>", "<user_instructions>")
_PATCH_FILE = re.compile(r"^\*\*\* (?:Update|Add|Delete) File:\s*(.+?)\s*$", re.M)
_warned = False


def _has_zstd() -> bool:
    global _warned
    try:
        import zstandard  # noqa: F401
        return True
    except ImportError:
        if not _warned:
            _warned = True
            print("driftguard: skipping codex *.jsonl.zst (pip install zstandard to read them)", file=sys.stderr)
        return False


def discover() -> List[str]:
    out: List[str] = []
    for r in paths.codex_roots():
        out += [str(f) for f in sorted(r.glob("**/rollout-*.jsonl"))]
        zst = sorted(r.glob("**/rollout-*.jsonl.zst"))
        if zst and _has_zstd():
            out += [str(f) for f in zst]
    return out


def _lines(path: str):
    if path.endswith(".zst"):
        import zstandard
        fh = open(path, "rb")
        return io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(fh), encoding="utf-8", errors="ignore")
    return open(path, encoding="utf-8", errors="ignore")


def _user_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") in ("input_text", "text") and isinstance(b.get("text"), str))
    return ""


def _int(d, k) -> int:
    try:
        return int((d or {}).get(k) or 0)
    except (TypeError, ValueError):
        return 0


def parse(path: str) -> List[Session]:
    p = Path(path)
    sid = p.name.split(".")[0]
    s: Session = {"agent": "codex", "id": sid, "source": path, "prompts": [], "tools": 0, "tokens": empty_tokens(),
                  "models": {}, "usage": [], "files": [], "todos": []}
    ts: list = []
    files: dict = {}
    last_total = None
    model = None
    turns = 0
    try:
        fh = _lines(path)
    except Exception:
        return []
    with fh:
        for line in fh:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if not isinstance(o, dict):
                continue
            t, pl, when = o.get("type"), o.get("payload"), o.get("timestamp", "")
            if not isinstance(pl, dict):
                continue
            if when:
                ts.append(when)
            if t == "session_meta":
                s["id"] = pl.get("id") or s["id"]
                if pl.get("cwd"):
                    s["cwd"] = pl["cwd"]
                if pl.get("timestamp"):
                    ts.append(pl["timestamp"])
            elif t == "turn_context":
                if pl.get("cwd") and "cwd" not in s:
                    s["cwd"] = pl["cwd"]
                model = pl.get("model") or model
            elif t == "response_item":
                pt = pl.get("type")
                if pt == "message":
                    if pl.get("role") == "user":
                        txt = common.clean_prompt(_user_text(pl.get("content")))
                        if txt and not txt.startswith(_SKIP_PREFIXES) and not common.is_skip(txt):
                            s["prompts"].append({"t": when, "txt": txt})
                    elif pl.get("role") == "assistant":
                        turns += 1
                elif pt in _TOOL_TYPES:
                    s["tools"] += 1
                    blob = " ".join(str(pl.get(k) or "") for k in ("arguments", "input", "action"))
                    for f in _PATCH_FILE.findall(blob.replace("\\n", "\n")):
                        files[f] = files.get(f, 0) + 1
            elif t == "event_msg" and pl.get("type") == "token_count":
                info = pl.get("info")
                if not isinstance(info, dict):
                    continue
                if isinstance(info.get("total_token_usage"), dict):
                    last_total = info["total_token_usage"]
                lt = info.get("last_token_usage")
                if isinstance(lt, dict):
                    s["usage"].append([when, _int(lt, "total_tokens") or _int(lt, "input_tokens") + _int(lt, "output_tokens")])
    if not ts:
        return []
    if last_total:
        cached = _int(last_total, "cached_input_tokens")
        s["tokens"] = {"input": max(0, _int(last_total, "input_tokens") - cached), "output": _int(last_total, "output_tokens"),
                       "cache_read": cached, "cache_write": 0}
    if turns:
        s["models"][model or "codex"] = turns
    s["start"], s["end"] = min(ts), max(ts)
    s["files"] = [f for f, _ in sorted(files.items(), key=lambda kv: -kv[1])[:30]]
    s["project"] = common.project_name(s.get("cwd"), "codex")
    s["bot"] = common.looks_bot(s["prompts"][0]["txt"] if s["prompts"] else None, path)
    return [s]
