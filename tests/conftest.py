"""Shared fixtures. Every test runs against a throwaway home: the real ~/.claude, ~/.codex, ~/.Projects are never touched."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def work():
    """Scratch dir outside /tmp (driftguard treats sources under /tmp/ as throwaway bot sessions)."""
    base = ROOT / "tests" / ".work"
    base.mkdir(exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix="dg-", dir=base))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def dg(work, monkeypatch):
    tmp_path = work
    """A fake home with a project dir and all four agents' fixture data installed."""
    from driftguard import paths
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(paths, "home", lambda: home)
    monkeypatch.setenv("DRIFTGUARD_HOME", str(tmp_path / "dgdata"))
    for k in ("CLAUDE_CONFIG_DIR", "CODEX_HOME"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(paths, "wsl_windows_homes", lambda: [])
    proj = home / "work" / "demo-app"
    proj.mkdir(parents=True)

    def put(src, dst, text_sub=True):
        dst.parent.mkdir(parents=True, exist_ok=True)
        txt = (FIX / src).read_text(encoding="utf-8")
        # JSON-escape the path: Windows backslashes would otherwise make the fixture lines invalid JSON.
        dst.write_text(txt.replace("__CWD__", json.dumps(str(proj))[1:-1]) if text_sub else txt, encoding="utf-8")
        return dst

    cdir = home / ".claude" / "projects" / "-home-work-demo-app"
    put("claude_session.jsonl", cdir / "sess-1.jsonl")
    put("claude_bot.jsonl", cdir / "sess-bot.jsonl")
    put("codex_rollout.jsonl", home / ".codex" / "sessions" / "2026" / "02" / "01" / "rollout-2026-02-01T08-00-00-cdx-1.jsonl")
    put("gemini_chat.json", home / ".gemini" / "tmp" / "abcdef1234567890" / "chats" / "session-1.json")
    put("gemini_logs.json", home / ".gemini" / "tmp" / "fedcba0987654321" / "logs.json")
    (home / ".gemini" / "GEMINI.md").write_text("# My gemini rules\n\nkeep this line\n", encoding="utf-8")
    return type("DG", (), {"home": home, "proj": proj, "data": tmp_path / "dgdata", "tmp": tmp_path})


def write_findings(dg, findings: dict, scan_sessions=None):
    d = dg.data
    d.mkdir(parents=True, exist_ok=True)
    (d / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    if scan_sessions is not None:
        (d / "scan.json").write_text(json.dumps({"sessions": scan_sessions, "mode": {"frugal": True}, "setup": {"graphify": False}}), encoding="utf-8")
