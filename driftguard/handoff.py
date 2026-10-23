"""`driftguard handoff`: write a <=40-line HANDOFF.md for the latest Claude session in a dir. No LLM."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

MAX_LINES = 40


def _one(s: str, n: int = 140) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _same_dir(cwd: Optional[str], d: Path) -> bool:
    if not cwd:
        return False
    try:
        return Path(cwd).expanduser().resolve() == d
    except (OSError, RuntimeError):
        return False


def pick(sessions: List[dict], d: Path, sid: str) -> Optional[dict]:
    if sid and sid != "latest":
        return next((s for s in sessions if s.get("id") == sid or s.get("id", "").startswith(sid)), None)
    cand = [s for s in sessions if s.get("agent") == "claude" and not s.get("bot") and s.get("prompts") and _same_dir(s.get("cwd"), d)]
    return max(cand, key=lambda s: s.get("end", ""), default=None)


def build(s: dict, d: Path) -> List[str]:
    prompts = [p["txt"] for p in s["prompts"]]
    files = []
    for f in s.get("files", [])[:8]:
        try:
            files.append(os.path.relpath(f, d) if f.startswith(str(d)) else f)
        except ValueError:
            files.append(f)
    todo = [t for t in s.get("todos", []) if not t.startswith("[completed]")][:8]
    last = prompts[-3:]
    L = [f"## Handoff — {(s.get('end') or datetime.now().isoformat())[:10]}", "",
         f"**Goal:** {_one(prompts[0], 160)}", "", "**Done** (files touched, most-used first):"]
    L += [f"- {_one(f, 120)}" for f in files] or ["- (no file edits recorded)"]
    L += ["", "**In progress** (open todos):"]
    L += [f"- {_one(t, 120)}" for t in todo] or ["- (no open todos recorded)"]
    L += ["", "**Last asks:**"] + [f"{i}. {_one(p, 120)}" for i, p in enumerate(last, 1)]
    L += ["", f"**Next step:** Continue: {_one(prompts[-1], 140)}", "",
          "**Resume tip:** Start a fresh session and say: read HANDOFF.md"]
    return L[:MAX_LINES]


def run(args) -> int:
    from driftguard.cli import collect  # late import: cli imports this module lazily
    d = Path(args.dir).expanduser().resolve()
    sessions = collect(["claude"], quiet=True)
    s = pick(sessions, d, args.session)
    if not s or not s.get("prompts"):
        print(f"no Claude session found for {d}" + (f" (id {args.session})" if args.session != "latest" else ""))
        return 1
    lines = build(s, d)
    out = Path(args.out).expanduser() if args.out else d / "HANDOFF.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out}  ({len(lines)} lines, from session {s['id'][:8]})")
    return 0
