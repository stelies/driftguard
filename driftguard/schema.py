"""The common Session shape every adapter returns (plain dicts, JSON-serializable)."""
from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class Prompt(TypedDict):
    t: str      # ISO-8601 UTC timestamp
    txt: str    # what the human typed (no tool results, no system text)


class Tokens(TypedDict):
    input: int
    output: int
    cache_read: int
    cache_write: int


class Session(TypedDict, total=False):
    agent: str            # claude | codex | gemini | cursor
    id: str
    source: str           # file path it came from
    project: str          # human-friendly project name (cwd basename)
    cwd: str
    title: str
    start: str
    end: str
    bot: bool             # auto-generated (summarizer, title job, channel relay, test harness)
    prompts: List[Prompt]
    tools: int
    tokens: Tokens
    models: Dict[str, int]          # model -> assistant turns
    usage: List[List[Any]]          # [ts, tokens_total] per assistant turn (for 5h-block burn rate)
    files: List[str]                # files touched by tools (for handoff)
    todos: List[str]                # last todo list (for handoff)


def empty_tokens() -> Tokens:
    return {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
