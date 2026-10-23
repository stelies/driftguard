import json
import time
from pathlib import Path
from types import SimpleNamespace

from driftguard import handoff, pulse


def test_handoff_le_40_lines(dg, capsys):
    out = dg.tmp / "HANDOFF.md"
    rc = handoff.run(SimpleNamespace(session="latest", dir=str(dg.proj), out=str(out)))
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert 0 < len(lines) <= 40
    assert lines[0].startswith("## Handoff — 2026-01-05")
    assert "**Goal:** fix the widget layout" in text and "src/widget.py" in text
    assert "[in_progress] add tests" in text and "[completed]" not in text
    assert "Continue: ship it and update the docs" in text
    assert "read HANDOFF.md" in text
    assert str(out) in capsys.readouterr().out


def test_handoff_long_inputs_still_capped():
    s = {"id": "x", "end": "2026-01-01T00:00:00Z", "prompts": [{"t": "", "txt": "word " * 500} for _ in range(30)],
         "files": [f"/p/f{i}.py" for i in range(30)], "todos": [f"[pending] t{i}" for i in range(30)]}
    lines = handoff.build(s, Path("/p"))
    assert len(lines) <= 40 and all(len(l) < 200 for l in lines)


def test_handoff_other_dir_has_no_session(dg, capsys):
    other = dg.home / "elsewhere"
    other.mkdir()
    assert handoff.run(SimpleNamespace(session="latest", dir=str(other), out=None)) == 1
    assert not (other / "HANDOFF.md").exists()


def test_pulse_silent_on_second_run(dg, capsys):
    a = SimpleNamespace(agents=None, verbose=False)
    pulse.run(a)  # baseline
    pulse.run(a)
    assert capsys.readouterr().out == ""
    st = json.loads((dg.data / "pulse.json").read_text(encoding="utf-8"))
    assert "demo-app" in st["known_projects"] and st["last_run"]


def test_pulse_reports_new_and_reopened_projects(dg, capsys):
    from driftguard import paths
    a = SimpleNamespace(agents=None, verbose=False)
    pulse.run(a)
    capsys.readouterr()
    # a brand-new project session appears, and a parked one gets reopened
    st = json.loads((dg.data / "pulse.json").read_text(encoding="utf-8"))
    st["known_projects"] = []
    st["last_run"] = "2020-01-01T00:00:00+00:00"
    (dg.data / "pulse.json").write_text(json.dumps(st))
    (dg.data / "findings.json").write_text(json.dumps({"projects": [{"name": "demo-app", "category": "abandoned"}]}))
    pulse.run(a)
    out = capsys.readouterr().out
    assert "new project detected: demo-app" in out and "reopened parked project demo-app" in out
    pulse.run(a)
    assert capsys.readouterr().out == ""


def test_pulse_verbose_and_fast(dg, capsys):
    a = SimpleNamespace(agents=None, verbose=True)
    pulse.run(a)
    t = time.time()
    pulse.run(a)
    assert time.time() - t < 1
    assert "nothing new" in capsys.readouterr().out
