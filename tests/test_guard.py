import json
from types import SimpleNamespace

from conftest import write_findings
from driftguard import guard


def ns(**kw):
    d = dict(agents=None, apply=False, projects=None, global_only=False)
    d.update(kw)
    return SimpleNamespace(**d)


FINDINGS = {
    "projects": [{"name": "demo-app", "what_it_is": "A demo widget app", "category": "dopamine-build",
                  "drift": [{"date": "2026-01-03", "from": "fix widget", "to": "new theme engine", "quote": "q"}]},
                 {"name": "main-site", "what_it_is": "Marketing site", "category": "useful-and-good"}],
    "answers": {"goals": ["money", "learning"], "tone": "brutal", "wip_limit": "1 paid + 1 own", "drift_action": "stop-poll",
                "gate": "gate+active", "frustration": ["restate", "screenshot"],
                "registry": {"demo-app": {"status": "PARKED", "purpose": "Practice project"}}},
}


def setup(dg):
    write_findings(dg, FINDINGS, [{"project": "demo-app", "cwd": str(dg.proj)}] * 3)


def test_dry_run_shows_diff_and_writes_nothing(dg, capsys):
    setup(dg)
    gmd = dg.home / ".gemini" / "GEMINI.md"
    before = gmd.read_text(encoding="utf-8")
    assert guard.run(ns(agents=["gemini"])) == 0
    out = capsys.readouterr().out
    assert "+<!-- driftguard:global v1" in out and "+<!-- driftguard:purpose v1" in out and "dry run" in out
    assert gmd.read_text(encoding="utf-8") == before and not (dg.proj / "GEMINI.md").exists()


def test_apply_idempotent_preserves_and_backs_up(dg, capsys):
    setup(dg)
    gmd = dg.home / ".gemini" / "GEMINI.md"
    original = gmd.read_text(encoding="utf-8")
    guard.run(ns(agents=["gemini"], apply=True))
    new = gmd.read_text(encoding="utf-8")
    assert new.startswith("# My gemini rules\n\n<!-- driftguard:global v1")  # inserted after the first heading
    assert "keep this line" in new and (gmd.parent / "GEMINI.md.bak").read_text(encoding="utf-8") == original
    assert "<!-- /driftguard:global -->" in new and "1 paid + 1 own" in new
    assert "| main-site |" in new and "| demo-app |" in new and "PARKED" in new and "ACTIVE" in new
    assert "You have 1 active project(s) (main-site)" in new
    assert "Stop and restate" in new and "break" not in new.split("Frustration")[1].split("###")[0]
    purpose = (dg.proj / "GEMINI.md").read_text(encoding="utf-8")
    assert purpose.startswith("# demo-app\n") and "new-project gate" in purpose and "new theme engine" in purpose
    capsys.readouterr()
    guard.run(ns(agents=["gemini"]))  # second run: no diff
    assert "up to date" in capsys.readouterr().out
    guard.run(ns(agents=["gemini"], apply=True))
    assert gmd.read_text(encoding="utf-8") == new


def test_edit_outside_markers_survives_reapply(dg):
    setup(dg)
    gmd = dg.home / ".gemini" / "GEMINI.md"
    guard.run(ns(agents=["gemini"], apply=True, global_only=True))
    gmd.write_text(gmd.read_text(encoding="utf-8") + "\n## my own section\nhands off\n", encoding="utf-8")
    f = json.loads((dg.data / "findings.json").read_text(encoding="utf-8"))
    f["answers"]["wip_limit"] = "2 total"
    (dg.data / "findings.json").write_text(json.dumps(f))
    guard.run(ns(agents=["gemini"], apply=True, global_only=True))
    t = gmd.read_text(encoding="utf-8")
    assert "hands off" in t and "2 total" in t and "1 paid + 1 own" not in t and t.count("driftguard:global v1") == 1


def test_claude_and_codex_targets_created(dg):
    setup(dg)
    guard.run(ns(agents=["claude", "codex"], apply=True))
    assert (dg.home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8").startswith("# Global agent rules\n")
    assert "driftguard:global" in (dg.home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
    assert "driftguard:purpose" in (dg.proj / "CLAUDE.md").read_text(encoding="utf-8")
    assert "driftguard:purpose" in (dg.proj / "AGENTS.md").read_text(encoding="utf-8")


def test_cursor_mdc_frontmatter_and_note(dg, capsys):
    setup(dg)
    guard.run(ns(agents=["cursor"], apply=True))
    mdc = (dg.proj / ".cursor" / "rules" / "driftguard.mdc").read_text(encoding="utf-8")
    assert mdc.startswith("---\ndescription: driftguard purpose & drift guard\nalwaysApply: true\n---\n")
    assert "driftguard:purpose" in mdc
    assert "Cursor Settings" in capsys.readouterr().out
    guard.run(ns(agents=["cursor"], apply=True))
    assert (dg.proj / ".cursor" / "rules" / "driftguard.mdc").read_text(encoding="utf-8") == mdc
    assert not (dg.proj / ".cursor" / "rules" / "driftguard.mdc.bak").exists()


def test_global_only_skips_projects_and_default_agents(dg):
    setup(dg)
    guard.run(ns(apply=True, global_only=True))  # default agents: only dirs that exist (.claude/.codex/.gemini created? only gemini+claude via fixtures)
    assert not (dg.proj / "CLAUDE.md").exists()
    assert "driftguard:global" in (dg.home / ".gemini" / "GEMINI.md").read_text(encoding="utf-8")


def test_explicit_projects_dir_and_no_findings(dg, capsys):
    guard.run(ns(agents=["claude"], apply=True, projects=[str(dg.proj)]))
    t = (dg.proj / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Not defined yet" in t and "driftguard:purpose" in t
