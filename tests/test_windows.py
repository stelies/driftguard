"""Windows-native behaviour, checked on every OS (CI also runs the suite on windows-latest)."""
import os
import subprocess
import sys

from conftest import ROOT
from driftguard.adapters import common


def test_windows_temp_project_dirs_are_bot_sessions():
    src = "C:\\Users\\me\\.claude\\projects\\C--Users-me-AppData-Local-Temp-job1\\abc.jsonl"
    assert common.looks_bot("fix the login bug", src)
    real = "C:\\Users\\me\\.claude\\projects\\C--Users-me-Projects-shop\\abc.jsonl"
    assert not common.looks_bot("fix the login bug", real)


def test_cli_survives_a_non_utf8_pipe(work):
    # A Claude Code hook on Windows may capture stdout through a legacy code page; output with "·" or "→" must not crash.
    env = dict(os.environ, PYTHONIOENCODING="ascii", DRIFTGUARD_HOME=str(work / "dg"),
               HOME=str(work), USERPROFILE=str(work), PYTHONPATH=str(ROOT))
    r = subprocess.run([sys.executable, "-m", "driftguard", "scan"], env=env, capture_output=True, cwd=str(work))
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert "transcripts" in r.stdout.decode("utf-8", "replace")
