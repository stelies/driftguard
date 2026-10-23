"""Deterministic metrics: disconnects, tokens, experience level, token pressure. No LLM.

Heuristics (ported from the ClaudeAudit pipeline, documented in the report's Diagnostics):
  away         gap >= 40 min since the previous prompt in the same session
  switch       >= 8 content words, < 4% Jaccard overlap with the previous 3 prompts, not a slash command
  frustration  >= 2 rage words, or 1 rage word + caps word, or dense caps, or "??" in a short prompt
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List

RAGE = re.compile(r"\b(wtf|ass|stupid|seriously|why the hell|lazy|useless|garbage|trash|dumb|fuck\w*|shit|bullshit|insane|refuse)\b|\?\?|!!", re.I)
CAPS_OK = {"UI", "API", "CSS", "GPU", "PDF", "HTML", "URL", "JSON", "MCP", "CLI", "TUI", "RAM", "SSD", "PWA", "GUI", "LLM", "CPU", "VPN", "SEO", "NOT", "README", "TODO", "AI", "MD", "JS", "TS", "SQL", "HTTP", "SSH", "USB"}
STOP = set("the a an to and or of in on for is it i you me my this that be do with just like can not no so are was what how make it's im i'm dont don't your at as if but then also all from have has get".split())
WORD = re.compile(r"[a-zA-Z']+")
LIMIT_TALK = re.compile(r"\b((usage|rate|session|weekly|5[- ]?hour) limits?|hit(ting)? (the |my )?limit|burn(ed|ing|t)? (my |the )?(tokens|usage)|out of (tokens|usage)|token usage|waste (of )?tokens)\b", re.I)


def parse_ts(t: str) -> datetime:
    return datetime.fromisoformat(t.replace("Z", "+00:00")) if t else datetime.fromtimestamp(0, timezone.utc)


def local_offset_hours() -> float:
    off = datetime.now().astimezone().utcoffset() or timedelta(0)
    return off.total_seconds() / 3600


def prompt_features(prompts: List[dict]) -> List[dict]:
    """Annotate each prompt with gap, length and disconnect kinds."""
    out, hist, prev = [], [], None
    for i, p in enumerate(prompts):
        x, tt = p["txt"], parse_ts(p["t"])
        gap = (tt - prev).total_seconds() / 60 if prev else 0.0
        prev = tt
        words = WORD.findall(x.lower())
        cw = {w for w in words if w not in STOP and len(w) > 2}
        ctx = set().union(*hist[-3:]) if hist else set()
        jac = len(cw & ctx) / max(1, len(cw | ctx)) if ctx else 1.0
        r = len(RAGE.findall(x))
        caps = sum(1 for w in re.findall(r"\b[A-Z]{3,}\b", x) if w not in CAPS_OK)
        if x.startswith(("PLEASE IMPLEMENT THIS PLAN",)) or "$ sudo" in x or re.match(r"^\S+@\S+[:~]", x):
            caps, r = 0, min(r, 1)  # pasted plans / terminal output are not shouting
        kind = []
        if gap >= 40:
            kind.append("away")
        if r >= 2 or (r >= 1 and caps >= 1) or (caps >= 4 and caps / max(1, len(words)) > 0.06) or ("??" in x and len(x) < 600):
            kind.append("rage")
        if i > 0 and len(cw) >= 8 and jac < 0.04 and not x.startswith("/"):
            kind.append("switch")
        out.append({"i": i, "t": p["t"], "len": len(x), "gap": round(gap, 1), "kind": kind, "skill": x.startswith("/"),
                    "limit_talk": bool(LIMIT_TALK.search(x)), "txt": x[:420]})
        hist.append(cw)
    return out


def total_tokens(tk: dict) -> int:
    return sum(tk.values())


def five_hour_blocks(sessions: List[dict]) -> List[dict]:
    """Group assistant-turn token usage into 5-hour billing-style windows (start at first turn of each window)."""
    ev = sorted((parse_ts(t), n) for s in sessions for t, n in s.get("usage", []) if t)
    blocks, cur = [], None
    for t, n in ev:
        if not cur or t >= cur["start"] + timedelta(hours=5):
            cur = {"start": t, "tokens": 0, "turns": 0}
            blocks.append(cur)
        cur["tokens"] += n
        cur["turns"] += 1
    return [{"start": b["start"].isoformat(), "tokens": b["tokens"], "turns": b["turns"]} for b in blocks]


def experience(human: List[dict], setup: dict) -> dict:
    """'new' when there's little history or no customization yet: scales up diagnostics."""
    n = len(human)
    span = 0
    if human:
        span = (parse_ts(max(s["end"] for s in human)) - parse_ts(min(s["start"] for s in human))).days
    customized = setup.get("claude_md") or setup.get("skills") or setup.get("hooks")
    level = "new" if n < 15 or span < 21 or not customized else "experienced"
    return {"level": level, "real_sessions": n, "span_days": span, "customized": bool(customized),
            "reasons": [r for r, c in (("fewer than 15 real sessions", n < 15), ("under 3 weeks of history", span < 21),
                                       ("no CLAUDE.md/skills/hooks yet", not customized)) if c]}


def token_pressure(sessions: List[dict], prompts: List[dict]) -> dict:
    blocks = five_hour_blocks(sessions)
    vals = sorted(b["tokens"] for b in blocks)
    p90 = vals[int(len(vals) * 0.9)] if vals else 0
    recent = [b for b in blocks if parse_ts(b["start"]) > datetime.now(timezone.utc) - timedelta(days=7)]
    talk = sum(p["limit_talk"] for p in prompts)
    tot = sum(total_tokens(s["tokens"]) for s in sessions)
    top = sorted(sessions, key=lambda s: -total_tokens(s["tokens"]))[:10]
    top_share = sum(total_tokens(s["tokens"]) for s in top) / tot if tot else 0
    score = (talk >= 3) + (top_share > 0.5) + (bool(recent) and max(b["tokens"] for b in recent) >= p90 and len(blocks) > 5)
    return {"level": "high" if score >= 2 else "low", "score": int(score), "limit_mentions": talk, "top10_share": round(top_share, 3),
            "blocks": len(blocks), "p90_block_tokens": p90, "recent_blocks_7d": len(recent), "total_tokens": tot}


def summarize(sessions: List[dict], setup: dict) -> dict:
    """Everything the report and the skill need, computed once."""
    human = [s for s in sessions if not s.get("bot")]
    prompts, per_session = [], {}
    for s in human:
        feats = prompt_features(s["prompts"])
        for f in feats:
            f["s"] = s["id"]
        prompts += feats
        per_session[s["id"]] = {"aways": sum("away" in f["kind"] for f in feats), "rage": sum("rage" in f["kind"] for f in feats),
                                "switches": sum("switch" in f["kind"] for f in feats)}
    by_proj: Dict[str, dict] = defaultdict(lambda: {"sessions": 0, "prompts": 0, "tokens": 0, "first": None, "last": None, "agents": Counter()})
    for s in human:
        b = by_proj[s["project"]]
        b["sessions"] += 1
        b["prompts"] += len(s["prompts"])
        b["tokens"] += total_tokens(s["tokens"])
        b["first"] = min(filter(None, [b["first"], s["start"]]))
        b["last"] = max(filter(None, [b["last"], s["end"]]))
        b["agents"][s["agent"]] += 1
    models: Counter = Counter()
    for s in sessions:
        models.update(s.get("models", {}))
    return {
        "counts": {"transcripts": len(sessions), "real": len(human), "bot": len(sessions) - len(human), "prompts": len(prompts),
                   "by_agent": dict(Counter(s["agent"] for s in sessions))},
        "experience": experience(human, setup),
        "tokens": token_pressure(sessions, prompts),
        "models": dict(models),
        "projects": {k: {**v, "agents": dict(v["agents"])} for k, v in by_proj.items()},
        "per_session": per_session,
        "prompts": prompts,
        "tz_offset_hours": local_offset_hours(),
    }
