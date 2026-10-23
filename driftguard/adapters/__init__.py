"""Agent adapters: each turns an agent's local history into common Session dicts."""
from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Tuple

from ..schema import Session

# name -> (discover() -> [source paths], parse(path) -> [Session])
REGISTRY: Dict[str, Tuple[Callable[[], List[str]], Callable[[str], List[Session]]]] = {}


def load_all() -> None:
    from . import claude_code, codex, cursor, gemini
    for name, mod in (("claude", claude_code), ("codex", codex), ("gemini", gemini), ("cursor", cursor)):
        REGISTRY[name] = (mod.discover, mod.parse)


def agents() -> Iterable[str]:
    load_all()
    return REGISTRY.keys()
