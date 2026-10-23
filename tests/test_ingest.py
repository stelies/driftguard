import json
from types import SimpleNamespace

from driftguard import ingest


def _write(p, d):
    p.write_text(json.dumps(d), encoding="utf-8")
    return str(p)


def test_neutral():
    assert ingest.neutral("He lost his focus and blamed himself; they told him so.") == "They lost their focus and blamed themself; they told them so."
    assert ingest.neutral("he is tired, he's done") == "they are tired, they're done"
    assert ingest.neutral("the theme here") == "the theme here"  # no partial-word hits


def test_merge_override_and_pronouns(dg):
    w = dg.tmp
    f1 = _write(w / "f1.json", {"projects": [{"name": "app", "what_it_is": "He builds a tool", "category": "stalled", "category_reason": "he stopped",
                                              "drift": [{"date": "2026-01-01", "from": "a", "to": "b", "quote": "he said his plan"}]}],
                                "sessions": [{"session": "s1", "one_line": "He tried", "motivation_evidence": "he was fine"}],
                                "patterns": ["He drifted"]})
    f2 = _write(w / "f2.json", {"projects": [{"name": "app", "what_it_is": "Later wins", "drift": [{"date": "2026-01-09", "from": "b", "to": "c", "quote": "q2"}]},
                                              {"name": "other", "category": "abandoned"}],
                                "sessions": [{"session": "s1", "one_line": "replaced"}, {"session": "s2", "one_line": "new"}],
                                "coach": [{"bad": "he did it", "why": "he rushed", "better": "…"}]})
    ans = _write(w / "ans.json", {"goals": ["money"], "overrides": {"app": {"category": "dopamine-build", "reason": "he says it is fun"}},
                                  "registry": {"app": {"status": "PARKED"}}})
    rc = ingest.run(SimpleNamespace(findings=[f1, f2], answers=ans))
    assert rc == 0
    out = json.loads((dg.data / "findings.json").read_text(encoding="utf-8"))
    app = next(p for p in out["projects"] if p["name"] == "app")
    assert len(out["projects"]) == 2 and len(out["sessions"]) == 2
    assert app["what_it_is"] == "Later wins"
    assert [d["date"] for d in app["drift"]] == ["2026-01-01", "2026-01-09"]
    assert app["drift"][0]["quote"] == "he said his plan"  # verbatim untouched
    assert app["category"] == "dopamine-build" and app["user_confirmed"] is True and app["category_reason"] == "he says it is fun"
    assert app["category_reason"] == "he says it is fun"  # user's own words are not rewritten
    assert next(s for s in out["sessions"] if s["session"] == "s1")["one_line"] == "replaced"
    assert out["patterns"] == ["They drifted"]
    assert out["coach"][0]["bad"] == "he did it" and out["coach"][0]["why"] == "they rushed"
    assert out["answers"]["registry"]["app"]["status"] == "PARKED"


def test_answers_survive_a_findings_only_refresh(dg):
    f = _write(dg.tmp / "f.json", {"projects": [{"name": "a"}]})
    ans = _write(dg.tmp / "a.json", {"tone": "brutal"})
    ingest.run(SimpleNamespace(findings=[f], answers=ans))
    ingest.run(SimpleNamespace(findings=[f], answers=None))
    assert json.loads((dg.data / "findings.json").read_text(encoding="utf-8"))["answers"]["tone"] == "brutal"
