"""Incremental parsing: a source file is re-read only when its mtime/size changed."""
from __future__ import annotations

import json
import os
from typing import Callable, Dict, List

from . import paths


def _file() -> str:
    return str(paths.data_dir() / "cache.json")


def load() -> Dict[str, dict]:
    try:
        with open(_file(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(c: Dict[str, dict]) -> None:
    tmp = _file() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f)
    os.replace(tmp, _file())


def parse_all(sources: List[str], parse: Callable[[str], list], cache: Dict[str, dict]) -> tuple[list, int]:
    """Returns (sessions, number_of_files_actually_parsed)."""
    out, parsed = [], 0
    for src in sources:
        try:
            st = os.stat(src)
        except OSError:
            continue
        key = f"{st.st_mtime_ns}:{st.st_size}"
        hit = cache.get(src)
        if hit and hit.get("key") == key:
            out += hit["sessions"]
            continue
        sessions = parse(src)
        parsed += 1
        cache[src] = {"key": key, "sessions": sessions}
        out += sessions
    for gone in set(cache) - set(sources):
        if not os.path.exists(gone):
            cache.pop(gone, None)
    return out, parsed
