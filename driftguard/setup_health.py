"""What the user has customized already (feeds experience level + the 'Setup health' section)."""
from __future__ import annotations

import json
from pathlib import Path

from . import paths


def check() -> dict:
    h = paths.home()
    claude = h / ".claude"
    settings = {}
    for f in (claude / "settings.json", claude / "settings.local.json"):
        try:
            settings.update(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    skills = sorted(p.parent.name for p in (claude / "skills").glob("*/SKILL.md")) if (claude / "skills").is_dir() else []
    agents_dirs = {"codex": h / ".codex", "gemini": h / ".gemini", "cursor": h / ".cursor"}
    return {
        "claude_md": (claude / "CLAUDE.md").is_file(),
        "skills": len(skills),
        "skill_names": skills[:50],
        "hooks": bool(settings.get("hooks")),
        "permissions_allow": len((settings.get("permissions") or {}).get("allow", [])),
        "mcp_servers": len(settings.get("mcpServers", {})),
        "graphify": any((Path(d) / "graphify").exists() for d in ("/usr/local/bin", str(h / ".local/bin"))),
        "agents_installed": {k: v.is_dir() for k, v in agents_dirs.items()} | {"claude": claude.is_dir()},
        "codex_agents_md": (h / ".codex" / "AGENTS.md").is_file(),
        "gemini_md": (h / ".gemini" / "GEMINI.md").is_file(),
    }
