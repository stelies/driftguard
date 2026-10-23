"""Where things live, on every OS (Linux, macOS, Windows, WSL)."""
from __future__ import annotations

import os
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("USERPROFILE") or os.path.expanduser("~")) if os.name == "nt" else Path.home()


def data_dir() -> Path:
    """driftguard's own state: scan.json, digests/, findings.json, report.html, state.json."""
    d = Path(os.environ.get("DRIFTGUARD_HOME") or home() / ".driftguard")
    d.mkdir(parents=True, exist_ok=True)
    return d


def wsl_windows_homes() -> list[Path]:
    """On WSL, Windows-side agent data lives under /mnt/c/Users/*."""
    base = Path("/mnt/c/Users")
    if not base.is_dir() or "microsoft" not in os.uname().release.lower():
        return []
    return [p for p in base.iterdir() if p.is_dir() and p.name not in ("Public", "Default", "All Users", "Default User")]


def claude_roots() -> list[Path]:
    roots = []
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        roots.append(Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects")
    roots.append(home() / ".claude" / "projects")
    roots += [h / ".claude" / "projects" for h in wsl_windows_homes()]
    return [r for r in dict.fromkeys(roots) if r.is_dir()]


def codex_roots() -> list[Path]:
    roots = []
    if os.environ.get("CODEX_HOME"):
        roots.append(Path(os.environ["CODEX_HOME"]) / "sessions")
    roots.append(home() / ".codex" / "sessions")
    roots += [h / ".codex" / "sessions" for h in wsl_windows_homes()]
    return [r for r in dict.fromkeys(roots) if r.is_dir()]


def gemini_roots() -> list[Path]:
    roots = [home() / ".gemini" / "tmp"] + [h / ".gemini" / "tmp" for h in wsl_windows_homes()]
    return [r for r in dict.fromkeys(roots) if r.is_dir()]


def cursor_dbs() -> list[Path]:
    """Cursor keeps chats in VS Code-style SQLite state DBs."""
    h = home()
    cands = [
        h / ".config/Cursor/User/globalStorage/state.vscdb",
        h / "Library/Application Support/Cursor/User/globalStorage/state.vscdb",
        Path(os.environ.get("APPDATA", h / "AppData/Roaming")) / "Cursor/User/globalStorage/state.vscdb",
    ]
    cands += [w / "AppData/Roaming/Cursor/User/globalStorage/state.vscdb" for w in wsl_windows_homes()]
    return [p for p in dict.fromkeys(cands) if p.is_file()]
