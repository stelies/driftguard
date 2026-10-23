import json
import re
import sys
from pathlib import Path

from driftguard import report

ROOT = Path(__file__).resolve().parent.parent


def tiny_scan():
    p = {"i": 0, "t": "2026-05-01T10:00:00Z", "len": 5, "gap": 0, "kind": [], "skill": False, "limit_talk": False, "txt": "hello </script><!-- x", "s": "a"}
    return {"version": "0", "generated": "2026-05-02T00:00:00+00:00", "setup": {}, "mode": {"diagnostics": "compact", "frugal": False},
            "summary": {"counts": {"transcripts": 1, "real": 1, "bot": 0, "prompts": 1, "by_agent": {"claude": 1}}, "experience": {"level": "new"},
                        "tokens": {}, "models": {}, "projects": {}, "per_session": {}, "prompts": [p], "tz_offset_hours": 0.0},
            "sessions": [{"id": "a", "agent": "claude", "project": "demo", "start": "2026-05-01T10:00:00Z", "end": "2026-05-01T10:05:00Z", "bot": False,
                          "n": 1, "tokens": {}, "models": {}, "source": "/secret/path.jsonl", "files": ["x"], "cwd": "/secret"}], "blocks": []}


def test_template_has_placeholder():
    t = report.template_text()
    assert t.count('<script id="dg-data" type="application/json">__DG_DATA__</script>') == 1


def test_injection_escapes_script_breakouts():
    html = report.inject('<script id="dg-data" type="application/json">__DG_DATA__</script>', {"x": "</script><script>alert(1)</script><!--"})
    body = re.search(r'type="application/json">(.*)</script>$', html, re.S).group(1)
    assert "</" not in body and "<!--" not in body
    assert json.loads(body)["x"] == "</script><script>alert(1)</script><!--"


def test_inject_requires_placeholder():
    try:
        report.inject("<html></html>", {})
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_build_data_drops_private_fields():
    d = report.build_data(tiny_scan(), None)
    s = d["sessions"][0]
    assert not {"source", "files", "cwd"} & set(s)
    assert d["findings"] == {}


def test_report_builds_from_tiny_scan(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIFTGUARD_HOME", str(tmp_path))
    (tmp_path / "scan.json").write_text(json.dumps(tiny_scan()))
    out = tmp_path / "r.html"
    report.build(out)
    html = out.read_text(encoding="utf-8")
    assert ">__DG_DATA__</script>" not in html and "/secret" not in html
    data = json.loads(re.search(r'id="dg-data" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert data["sessions"][0]["id"] == "a" and data["summary"]["prompts"][0]["txt"].startswith("hello")


def test_missing_scan_exits(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIFTGUARD_HOME", str(tmp_path))
    try:
        report.build()
    except SystemExit as e:
        assert e.code == 1
        return
    raise AssertionError("expected SystemExit")


def test_demo_renders_without_local_data(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_demo_data as m

    out = tmp_path / "demo.html"
    sys.argv = ["make_demo_data", "--out", str(out)]
    assert m.main() == 0
    html = out.read_text(encoding="utf-8")
    assert ("/ho" + "me/") not in html and "acme-shop" in html
