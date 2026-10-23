"""`driftguard pulse`: cheap incremental check (uses the parse cache); silent unless something needs attention.

Hook example (Claude Code SessionStart): command `driftguard pulse`.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import List

from . import metrics, paths

PARKED = {"PARKED", "DEAD"}
CATEGORY_PARKED = {"dopamine-build", "useful-but-redundant", "abandoned"}
REFRESH_AFTER = 20


def _load(f) -> dict:
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _parked(findings: dict) -> set:
    out = set()
    ans = (findings.get("answers") or {}).get("registry") or {}
    for n, r in ans.items():
        if str(r.get("status", "")).upper() in PARKED:
            out.add(n)
    for p in findings.get("projects", []):
        if p["name"] not in ans and p.get("category") in CATEGORY_PARKED:
            out.add(p["name"])
    return out


def run(args) -> int:
    from driftguard.cli import collect
    d = paths.data_dir()
    pf = d / "pulse.json"
    state = _load(pf)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sessions = collect(getattr(args, "agents", None), quiet=True)
    real = [s for s in sessions if not s.get("bot") and s.get("prompts")]
    known = set(state.get("known_projects") or [])
    last = state.get("last_run") or ""
    msgs: List[str] = []

    if last:  # first ever run only records a baseline
        fresh = [s for s in real if s.get("end", "") > last]
        new = sorted({s["project"] for s in fresh} - known)
        for n in new:
            msgs.append(f"new project detected: {n} (driftguard gate?)")
        parked = _parked(_load(d / "findings.json"))
        for n in sorted({s["project"] for s in fresh} & parked):
            msgs.append(f"reopened parked project {n}")
        blocks = metrics.five_hour_blocks(sessions)
        vals = sorted(b["tokens"] for b in blocks)
        if len(vals) > 5 and blocks[-1]["tokens"] > vals[int(len(vals) * 0.9)]:
            lb = metrics.parse_ts(blocks[-1]["start"])
            if (datetime.now(timezone.utc) - lb).total_seconds() < 5 * 3600:
                msgs.append("token spike: run `driftguard budget`")
        scan = _load(d / "scan.json")
        base = scan.get("generated", "")
        since = [s for s in real if s.get("end", "") > base] if base else real
        if len(since) >= REFRESH_AFTER:
            msgs.append(f"{len(since)} new sessions since the last scan: run /driftguard to refresh")

    state["known_projects"] = sorted(known | {s["project"] for s in real})
    state["last_run"] = now
    pf.write_text(json.dumps(state), encoding="utf-8")
    if msgs:
        print("driftguard: " + " | ".join(msgs))
    elif getattr(args, "verbose", False):
        print(f"driftguard pulse: nothing new ({len(real)} real sessions, {len(state['known_projects'])} projects, {time.strftime('%H:%M')})")
    return 0
