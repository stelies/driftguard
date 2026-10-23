import json

from driftguard import cache, digest, metrics


def P(t, txt):
    return {"t": t, "txt": txt}


def test_prompt_features_flags():
    ps = [
        P("2026-01-01T10:00:00Z", "please fix the login form validation errors on the signup page"),
        P("2026-01-01T10:02:00Z", "also the login form validation messages look wrong"),
        P("2026-01-01T11:30:00Z", "continue with the validation"),  # 88 min gap -> away
        P("2026-01-01T11:31:00Z", "wtf this is stupid, why is it still broken??"),  # rage
        P("2026-01-01T11:32:00Z", "forget that, build me a database migration pipeline with kafka consumers and grafana dashboards"),  # switch
        P("2026-01-01T11:33:00Z", "/clear"),
    ]
    f = metrics.prompt_features(ps)
    assert "away" in f[2]["kind"]
    assert "rage" in f[3]["kind"]
    assert "switch" in f[4]["kind"]
    assert f[0]["kind"] == [] and f[1]["kind"] == []
    assert f[5]["skill"] is True and "switch" not in f[5]["kind"]


def _sess(i, proj, n, plen=200):
    return {"id": f"s{i}", "agent": "claude", "project": proj, "start": f"2026-01-0{1 + i % 9}T10:00:00Z", "end": f"2026-01-0{1 + i % 9}T11:00:00Z",
            "title": "t", "tools": 0, "bot": False,
            "prompts": [{"t": f"2026-01-0{1 + i % 9}T10:{k % 60:02d}:00Z", "txt": ("word " * (plen // 5)).strip()} for k in range(n)]}


def test_digest_respects_max_tokens(tmp_path):
    ss = [_sess(i, f"proj{i % 3}", 20) for i in range(9)]
    man = digest.build(ss, tmp_path / "d", max_tokens=1500)
    assert len(man) > 1
    for m in man:
        text = open(m["file"], encoding="utf-8").read()
        assert digest.approx_tokens(text) <= 1500 + 20, m
    seen = "".join(open(m["file"], encoding="utf-8").read() for m in man)
    assert all(f"SESSION s{i} " in seen for i in range(9))  # nothing dropped
    # bot sessions are excluded
    ss[0]["bot"] = True
    man2 = digest.build(ss, tmp_path / "d2", max_tokens=100_000)
    assert "SESSION s0 " not in open(man2[0]["file"], encoding="utf-8").read()


def test_cache_reparses_only_changed_files(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("1")
    b.write_text("2")
    calls = []

    def parse(p):
        calls.append(p)
        return [{"id": p}]

    c = {}
    out, n = cache.parse_all([str(a), str(b)], parse, c)
    assert n == 2 and len(out) == 2
    out, n = cache.parse_all([str(a), str(b)], parse, c)
    assert n == 0 and len(calls) == 2
    b.write_text("22")  # size changes
    out, n = cache.parse_all([str(a), str(b)], parse, c)
    assert n == 1 and calls[-1] == str(b)
    b.unlink()
    out, n = cache.parse_all([str(a)], parse, c)
    assert str(b) not in c
