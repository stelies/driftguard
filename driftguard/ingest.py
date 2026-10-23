"""`driftguard ingest`: merge agent findings files + poll answers -> ~/.driftguard/findings.json (no LLM)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from . import paths

# Fields holding the user's own words or copied evidence: never rewritten.
VERBATIM = {"user", "quote", "bad", "motivation_evidence", "txt"}

_PAIRS = [  # longest first
    (r"\bhe is\b", "they are"), (r"\bhe was\b", "they were"), (r"\bhe has\b", "they have"), (r"\bhe does\b", "they do"),
    (r"\bhe doesn't\b", "they don't"), (r"\bhe's\b", "they're"), (r"\bhe'd\b", "they'd"), (r"\bhe'll\b", "they'll"),
    (r"\bhimself\b", "themself"), (r"\bhim\b", "them"), (r"\bhis\b", "their"), (r"\bhe\b", "they"),
]
_RX = [(re.compile(p, re.I), r) for p, r in _PAIRS]


def _case(src: str, rep: str) -> str:
    if src.isupper() and len(src) > 1:
        return rep.upper()
    return rep[0].upper() + rep[1:] if src[0].isupper() else rep


def neutral(s: str) -> str:
    """him->them, his->their, he->they, himself->themself (with common verb agreement)."""
    for rx, rep in _RX:
        s = rx.sub(lambda m, rep=rep: _case(m.group(0), rep), s)
    return s


def _walk(v: Any, key: str = "") -> Any:
    if key in VERBATIM:
        return v
    if isinstance(v, str):
        return neutral(v)
    if isinstance(v, list):
        return [_walk(x, key) for x in v]
    if isinstance(v, dict):
        return {k: _walk(x, k) for k, x in v.items()}
    return v


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        print(f"driftguard ingest: cannot read {path}: {e}", file=sys.stderr)
        raise SystemExit(2)
    if isinstance(d, list):  # tolerate a bare projects list
        d = {"projects": d}
    if not isinstance(d, dict):
        print(f"driftguard ingest: {path} is not a findings object", file=sys.stderr)
        raise SystemExit(2)
    return d


def _drift_key(d: dict) -> tuple:
    return (d.get("date"), d.get("to"), d.get("quote"))


def merge(docs: List[dict]) -> dict:
    projects: Dict[str, dict] = {}
    sessions: Dict[str, dict] = {}
    out: Dict[str, Any] = {"example_chats": [], "patterns": [], "coach": [], "improve": []}
    seen_ex, seen_imp = set(), {}
    for d in docs:
        for p in d.get("projects") or []:
            if not isinstance(p, dict) or not p.get("name"):
                continue
            old = projects.get(p["name"], {})
            new = {**old, **p}
            drift, seen = [], set()
            for x in (old.get("drift") or []) + (p.get("drift") or []):
                if isinstance(x, dict) and _drift_key(x) not in seen:
                    seen.add(_drift_key(x))
                    drift.append(x)
            new["drift"] = sorted(drift, key=lambda x: x.get("date") or "")
            projects[p["name"]] = new
        for s in d.get("sessions") or []:
            if isinstance(s, dict) and s.get("session"):
                sessions[s["session"]] = s
        for e in d.get("example_chats") or []:
            k = (e.get("session"), e.get("user"))
            if isinstance(e, dict) and k not in seen_ex:
                seen_ex.add(k)
                out["example_chats"].append(e)
        for pat in d.get("patterns") or []:
            if pat not in out["patterns"]:
                out["patterns"].append(pat)
        out["coach"] += [c for c in d.get("coach") or [] if isinstance(c, dict)]
        for i in d.get("improve") or []:
            if isinstance(i, dict):
                seen_imp[i.get("id") or i.get("title")] = i
        for k, v in d.items():  # keep any extra top-level keys the agent added
            if k not in ("projects", "sessions", "example_chats", "patterns", "coach", "improve", "answers") and k not in out:
                out[k] = v
    out["improve"] = list(seen_imp.values())
    out["projects"] = list(projects.values())
    out["sessions"] = list(sessions.values())
    return out


def apply_answers(f: dict, ans: dict) -> int:
    by = {p["name"]: p for p in f["projects"]}
    n = 0
    for name, o in (ans.get("overrides") or {}).items():
        if not isinstance(o, dict):
            continue
        p = by.get(name)
        if p is None:
            p = {"name": name, "drift": []}
            f["projects"].append(p)
            by[name] = p
        if o.get("category"):
            p["category"] = o["category"]
        if o.get("reason") or o.get("category_reason"):
            p["category_reason"] = o.get("reason") or o.get("category_reason")
        p["user_confirmed"] = True
        n += 1
    f["answers"] = ans
    return n


def run(args) -> int:
    docs = [_load(p) for p in args.findings]
    f = _walk(merge(docs))  # neutralize agent-written text before the user's own words are applied
    out_file = paths.data_dir() / "findings.json"
    ans = None
    if getattr(args, "answers", None):
        ans = _load(args.answers)
    else:  # keep earlier poll answers when only findings are refreshed
        try:
            ans = json.loads(out_file.read_text(encoding="utf-8")).get("answers")
        except (OSError, ValueError, AttributeError):
            ans = None
    n_over = apply_answers(f, ans) if isinstance(ans, dict) else 0
    f["ingested"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out_file.write_text(json.dumps(f, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"ingested {len(f['projects'])} project(s), {len(f['sessions'])} session(s), {len(f['example_chats'])} example chat(s), "
          f"{len(f['coach'])} coach item(s); {n_over} override(s) applied -> {out_file}")
    return 0
