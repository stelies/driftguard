import sqlite3
import json

from driftguard.adapters import claude_code, codex, cursor, gemini


def test_claude(dg):
    files = claude_code.discover()
    assert len(files) == 2
    s = next(x for f in files for x in claude_code.parse(f) if x["id"] == "sess-1")
    assert s["agent"] == "claude" and s["title"] == "Fix the demo widget" and s["project"] == "demo-app"
    assert [p["txt"] for p in s["prompts"]] == ["fix the widget layout in demo app please", "now add tests for the widget",
                                                 "ship it and update the docs"]  # tool_result + reminder stripped
    assert s["tools"] == 2 and s["files"] == [str(dg.proj / "src/widget.py")]
    assert s["tokens"] == {"input": 11, "output": 22, "cache_read": 100, "cache_write": 5}  # duplicate message id counted once
    assert len(s["usage"]) == 2
    assert s["todos"][1] == "[in_progress] add tests" and s["bot"] is False


def test_claude_bot(dg):
    bot = [x for f in claude_code.discover() for x in claude_code.parse(f) if x["id"] == "sess-bot"][0]
    assert bot["bot"] is True


def test_codex(dg):
    (f,) = codex.discover()
    (s,) = codex.parse(f)
    assert s["agent"] == "codex" and s["id"] == "cdx-1" and s["project"] == "demo-app"
    assert [p["txt"] for p in s["prompts"]] == ["build a small parser for csv files", "also handle quoted commas"]
    assert s["tools"] == 1 and s["files"] == ["src/parser.py"]
    assert s["tokens"] == {"input": 150, "output": 60, "cache_read": 100, "cache_write": 0}  # last cumulative value
    assert [u[1] for u in s["usage"]] == [130, 160] and s["bot"] is False and s["models"]


def test_codex_garbage_is_skipped(tmp_path):
    f = tmp_path / "rollout-x.jsonl"
    f.write_text('not json\n{"type":"response_item","payload":"str"}\n[]\n', encoding="utf-8")
    assert codex.parse(str(f)) == []


def test_gemini(dg):
    ss = [x for f in gemini.discover() for x in gemini.parse(f)]
    chat = next(s for s in ss if s["id"] == "gem-1")
    assert chat["agent"] == "gemini" and chat["project"] == "abcdef12"
    assert [p["txt"] for p in chat["prompts"]] == ["explain how the cache works", "and invalidation?"]
    assert chat["tokens"] == {"input": 40, "output": 25, "cache_read": 10, "cache_write": 0}
    logs = next(s for s in ss if s["id"] == "gem-2")
    assert len(logs["prompts"]) == 2 and logs["project"] == "fedcba09"


def _make_cursor_db(path):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE cursorDiskKV (key TEXT PRIMARY KEY, value BLOB)")
    comp = {"composerId": "c1", "name": "Refactor thing", "createdAt": 1767225600000, "lastUpdatedAt": 1767229200000,
            "fullConversationHeadersOnly": [{"bubbleId": "b1", "type": 1}, {"bubbleId": "b2", "type": 2}]}
    con.execute("INSERT INTO cursorDiskKV VALUES (?,?)", ("composerData:c1", json.dumps(comp)))
    con.execute("INSERT INTO cursorDiskKV VALUES (?,?)", ("bubbleId:c1:b1", json.dumps({"type": 1, "text": "refactor the loader"})))
    con.execute("INSERT INTO cursorDiskKV VALUES (?,?)", ("bubbleId:c1:b2", json.dumps({"type": 2, "text": "ok", "tokenCount": {"inputTokens": 7, "outputTokens": 3}})))
    comp2 = {"composerId": "c2", "createdAt": 1767225600000, "conversation": [{"type": 1, "text": "inline prompt"}]}
    con.execute("INSERT INTO cursorDiskKV VALUES (?,?)", ("composerData:c2", json.dumps(comp2)))
    con.commit()
    con.close()


def test_cursor(dg):
    db = dg.home / ".config/Cursor/User/globalStorage/state.vscdb"
    db.parent.mkdir(parents=True)
    _make_cursor_db(db)
    (path,) = cursor.discover()
    ss = {s["id"]: s for s in cursor.parse(path)}
    assert set(ss) == {"c1", "c2"}
    assert ss["c1"]["prompts"][0]["txt"] == "refactor the loader" and ss["c1"]["title"] == "Refactor thing"
    assert ss["c1"]["tokens"]["input"] == 7 and ss["c1"]["start"].startswith("2026-01-01")
    assert ss["c2"]["agent"] == "cursor" and ss["c2"]["bot"] is False


def test_cursor_bad_db_returns_empty(tmp_path, capsys):
    bad = tmp_path / "state.vscdb"
    bad.write_bytes(b"this is not sqlite")
    assert cursor.parse(str(bad)) == []
