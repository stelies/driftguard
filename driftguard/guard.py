"""`driftguard guard`: write managed drift-guard blocks into agent rule files.

Dry-run by default (unified diff). `--apply` writes, keeping a `.bak` of any changed existing file.
Blocks sit between `<!-- driftguard:NAME vN ... -->` and `<!-- /driftguard:NAME -->`; text outside is never touched.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from . import paths, setup_health

TEMPLATES = Path(__file__).parent / "templates"
CATEGORY_STATUS = {
    "useful-and-good": "ACTIVE", "stalled": "STALLED", "done-no-updates-needed": "DONE", "moved-elsewhere": "MOVED",
    "dopamine-build": "PARKED", "useful-but-redundant": "PARKED", "abandoned": "DEAD",
}
GATED = {"PARKED", "DEAD", "DONE"}
MDC_FRONTMATTER = "---\ndescription: driftguard purpose & drift guard\nalwaysApply: true\n---\n"
FRUSTRATION = {
    "restate": "**Stop and restate** in one line what you think the user asked, then fix only that. No extras.",
    "screenshot": "Visual/UI complaint: **ask for a screenshot or reference** (or take one yourself) before changing anything.",
    "rule": "Find the cause and **propose a rule** for this file so it never repeats.",
    "break": "If the frustration continues after the fix, suggest a short break or a fresh session with `driftguard handoff`.",
}


# ---------------------------------------------------------------- rendering
def render(name: str, ctx: Dict[str, str]) -> str:
    t = (TEMPLATES / f"{name}.md").read_text(encoding="utf-8")
    t = re.sub(r"\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}", lambda m: m.group(2) if ctx.get(m.group(1)) else "", t, flags=re.S)
    t = re.sub(r"\{\{(\w+)\}\}", lambda m: str(ctx.get(m.group(1), "")), t)
    return re.sub(r"\n{3,}", "\n\n", t).strip("\n")


def _short(p: str) -> str:
    h = str(paths.home())
    return "~" + p[len(h):] if p.startswith(h) else p


def _cell(s) -> str:
    return " ".join(str(s or "").replace("|", "/").split())[:140]


# ---------------------------------------------------------------- data
def load_findings() -> dict:
    try:
        return json.loads((paths.data_dir() / "findings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def load_scan() -> dict:
    try:
        return json.loads((paths.data_dir() / "scan.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def project_dirs(scan: dict) -> Dict[str, str]:
    """project name -> most common existing cwd among its sessions."""
    c: Dict[str, Counter] = {}
    home = str(paths.home())
    for s in scan.get("sessions", []):
        cwd = s.get("cwd")
        if cwd and s.get("project") and cwd.rstrip("/") != home.rstrip("/"):
            c.setdefault(s["project"], Counter())[cwd] += 1
    out = {}
    for name, cnt in c.items():
        for cwd, _ in cnt.most_common():
            if os.path.isdir(cwd):
                out[name] = cwd
                break
    return out


def status_of(name: str, findings: dict, answers: dict) -> str:
    reg = (answers.get("registry") or {}).get(name) or {}
    if reg.get("status"):
        return str(reg["status"]).upper()
    for p in findings.get("projects", []):
        if p.get("name") == name:
            return CATEGORY_STATUS.get(p.get("category", ""), "UNSET")
    return "UNSET"


def registry_rows(findings: dict, answers: dict, dirs: Dict[str, str]) -> List[dict]:
    rows: Dict[str, dict] = {}
    for p in findings.get("projects", []):
        n = p["name"]
        rows[n] = {"name": n, "path": _short(dirs[n]) if n in dirs else "", "status": status_of(n, findings, answers),
                   "purpose": p.get("what_it_is", "")}
    for n, r in (answers.get("registry") or {}).items():
        base = rows.setdefault(n, {"name": n, "path": "", "status": "UNSET", "purpose": ""})
        base["status"] = status_of(n, findings, answers)
        base["path"] = r.get("path") or base["path"] or (_short(dirs[n]) if n in dirs else "")
        base["purpose"] = r.get("purpose") or base["purpose"]
    order = {"ACTIVE": 0, "STALLED": 1, "MOVED": 2, "DONE": 3, "PARKED": 4, "DEAD": 5}
    return sorted(rows.values(), key=lambda r: (order.get(r["status"], 9), r["name"]))


# ---------------------------------------------------------------- blocks
def global_block(findings: dict, scan: dict, dirs: Dict[str, str]) -> str:
    ans = findings.get("answers") or {}
    rows = registry_rows(findings, ans, dirs)
    active = [r["name"] for r in rows if r["status"] == "ACTIVE"]

    who = []
    if ans.get("goals"):
        who.append("- Goals: " + ", ".join(ans["goals"]) + ". Prefer work that serves them.")
    tone = {"brutal": "brutally honest, no sugarcoating", "kind": "kind and encouraging, but still honest",
            "neutral": "neutral and factual"}.get(ans.get("tone", ""))
    if tone:
        who.append(f"- Feedback tone: {tone}.")
    if ans.get("daily_use"):
        who.append("- Tools used daily: " + ", ".join(ans["daily_use"]) + ".")
    pats = [p for p in findings.get("patterns", []) if isinstance(p, str)][:4]
    if pats:
        who.append("- Prompt habits seen in past sessions (treat as hints, not rules):")
        who += [f"  - {_cell(p)}" for p in pats]

    action = ans.get("drift_action", "stop-poll")
    drift = {
        "stop-poll": ("When you detect it, **stop before doing it** and ask one poll:\n"
                      "1. **Park it**: append the idea to the project's `TODO.md` (or `~/IDEAS.md` for a new project) and continue the current ask.\n"
                      "2. **Separate project**: run the new-project gate below.\n"
                      "3. **Do it here anyway**: proceed, and note the drift in STATUS/handoff.\n"
                      "Name the drift in one line first: \"This drifts from <purpose> into <thing>.\" Don't lecture. "
                      "Small, clearly-related follow-ups are not drift."),
        "nudge": ("When you detect it, say so in one line (\"This drifts from <purpose> into <thing>.\") and keep going with the "
                  "current ask unless the user confirms the change of direction. Add the idea to `TODO.md`."),
        "refuse": ("When you detect it, do not start it. Say so in one line, append the idea to the project's `TODO.md`, "
                   "and continue the current ask. Only proceed if the user repeats the request explicitly."),
    }.get(action)
    drift = drift or "When you detect it, say so in one line and ask whether to park it."

    gate = ["Before creating any new project/app/tool, or reopening a PARKED/DEAD one, ask (one poll):",
            "- Who uses it, daily?",
            "- Does an existing tool already do it? Name it.",
            "- Does it earn money or teach a named skill?"]
    g = ans.get("gate", "gate+active")
    if g == "gate+active":
        gate.append(f"Then: \"You have {len(active)} active project(s) ({', '.join(active)}). Which one pauses?\"" if active
                    else "Then ask which active project pauses to make room.")
    if g == "none":
        gate = ["No gate configured. Still mention an existing tool when one already covers the request."]
    else:
        gate.append("Two \"no\" answers on the first three: say so plainly and recommend not starting. "
                    "If the user still wants it, build it and add it to the registry.")

    fr = [f"- {FRUSTRATION[k]}" for k in ans.get("frustration", []) if k in FRUSTRATION]

    mode = scan.get("mode") or {}
    tokens = ""
    if mode.get("frugal"):
        lines = ["- Use Sonnet/Haiku subagents, at most 2 at once, with tight prompts.",
                 "- Read digests (`driftguard digest`), not raw transcripts.",
                 "- When context gets long: `driftguard handoff`, then continue in a fresh session (\"read HANDOFF.md\").",
                 "- Never re-read files you just wrote or already read."]
        if (scan.get("setup") or {}).get("graphify"):
            lines.insert(1, "- If `graphify-out/graph.json` exists, run `graphify query` before grepping or reading source.")
        tokens = "\n".join(lines)

    table = "\n".join(f"| {_cell(r['name'])} | {_cell(r['path'])} | {r['status']} | {_cell(r['purpose'])} |" for r in rows)
    ctx = {"who": "\n".join(who), "registry": table, "wip": _cell(ans.get("wip_limit", "")), "drift": drift,
           "gate": "\n".join(gate), "frustration": "\n".join(fr), "tokens": tokens}
    return render("global", ctx)


def purpose_block(name: str, findings: dict, ans: dict, dirs: Dict[str, str]) -> str:
    proj = next((p for p in findings.get("projects", []) if p.get("name") == name), {})
    reg = (ans.get("registry") or {}).get(name) or {}
    status = status_of(name, findings, ans)

    def bullets(v, empty):
        v = [v] if isinstance(v, str) else (v or [])
        return "\n".join(f"- {x}" for x in v) or empty

    traps = []
    for d in (proj.get("drift") or [])[-6:]:
        traps.append(f"- {d.get('date', '?')}: {_cell(d.get('from'))} -> {_cell(d.get('to'))}")
    ctx = {
        "status": status,
        "purpose": reg.get("purpose") or proj.get("what_it_is") or "Not defined yet: ask the user for a one-line purpose.",
        "done": reg.get("done") or "Not defined yet: ask \"Done = ?\" in one line before starting a large task.",
        "gate_first": "1" if status in GATED else "",
        "in_scope": bullets(reg.get("in_scope"), "- Whatever serves the purpose above."),
        "traps": "\n".join(traps) if traps else bullets(reg.get("out_of_scope"), "- Anything that does not serve the purpose above."),
        "rules": bullets(reg.get("rules"), "- Read STATUS/HANDOFF/TODO.md first; never redo items marked done.\n"
                                           "- Park new ideas in `TODO.md` instead of building them now."),
    }
    if traps and reg.get("out_of_scope"):
        ctx["traps"] += "\n" + bullets(reg["out_of_scope"], "")
    return render("purpose", ctx)


# ---------------------------------------------------------------- file editing
def upsert(text: str, name: str, block: str, title: str, mdc: bool = False) -> str:
    rx = re.compile(r"<!-- driftguard:%s v\d+[^\n]*?-->.*?<!-- /driftguard:%s -->" % (name, name), re.S)
    if rx.search(text):
        return rx.sub(lambda m: block, text, count=1)
    if not text.strip():
        return (MDC_FRONTMATTER + "\n" + block + "\n") if mdc else f"# {title}\n\n{block}\n"
    pre = ""
    body = text
    if body.startswith("---\n"):  # keep YAML frontmatter on top
        end = body.find("\n---", 4)
        if end != -1:
            cut = body.find("\n", end + 1)
            cut = len(body) if cut == -1 else cut + 1
            pre, body = body[:cut], body[cut:]
    m = re.search(r"^# .*$", body, re.M)
    if m:
        head, rest = body[:m.end()], body[m.end():].lstrip("\n")
        return pre + head + "\n\n" + block + ("\n\n" + rest if rest else "\n")
    if pre:
        return pre + "\n" + block + "\n\n" + body.lstrip("\n")
    return block + "\n\n" + body


def plan(path: Path, name: str, block: str, title: str, mdc: bool = False) -> Optional[tuple]:
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    new = upsert(old or "", name, block, title, mdc)
    return None if old == new else (path, old, new)


def show(changes: list) -> None:
    for path, old, new in changes:
        d = difflib.unified_diff((old or "").splitlines(keepends=True), new.splitlines(keepends=True),
                                 fromfile=str(path) if old is not None else "/dev/null", tofile=str(path))
        sys.stdout.writelines(l if l.endswith("\n") else l + "\n" for l in d)


def apply(changes: list) -> None:
    for path, old, new in changes:
        path.parent.mkdir(parents=True, exist_ok=True)
        if old is not None:
            shutil.copy2(path, str(path) + ".bak")
        path.write_text(new, encoding="utf-8")


# ---------------------------------------------------------------- entry
def run(args) -> int:
    findings, scan = load_findings(), load_scan()
    ans = findings.get("answers") or {}
    dirs = project_dirs(scan)
    home = paths.home()
    agents = args.agents or [a for a, ok in setup_health.check()["agents_installed"].items() if ok]
    if not agents:
        print("no supported agent found (looked for ~/.claude ~/.codex ~/.gemini ~/.cursor); pass --agents")
        return 1
    if not findings:
        print("note: no findings.json yet (run the /driftguard pass + `driftguard ingest`); writing a generic block", file=sys.stderr)

    gblock = global_block(findings, scan, dirs)
    glob_files = {"claude": home / ".claude" / "CLAUDE.md", "codex": home / ".codex" / "AGENTS.md", "gemini": home / ".gemini" / "GEMINI.md"}
    proj_files = {"claude": "CLAUDE.md", "codex": "AGENTS.md", "gemini": "GEMINI.md", "cursor": ".cursor/rules/driftguard.mdc"}

    targets: Dict[str, str] = {}  # project name -> dir
    if not args.global_only:
        if args.projects:
            for d in args.projects:
                p = Path(d).expanduser()
                if p.is_dir():
                    targets[p.resolve().name] = str(p.resolve())
                else:
                    print(f"skip {d}: not a directory", file=sys.stderr)
        else:
            for p in findings.get("projects", []):
                if p["name"] in dirs:
                    targets[p["name"]] = dirs[p["name"]]

    changes = []
    for a in agents:
        if a == "cursor":
            print("cursor has no global rules file: paste the block below into Cursor Settings -> Rules (project rules are written to .cursor/rules/driftguard.mdc)")
        else:
            c = plan(glob_files[a], "global", gblock, "Global agent rules")
            if c:
                changes.append(c)
        for name, d in sorted(targets.items()):
            blk = purpose_block(name, findings, ans, dirs)
            c = plan(Path(d) / proj_files[a], "purpose", blk, name, mdc=(a == "cursor"))
            if c:
                changes.append(c)
    if "cursor" in agents:
        print(gblock + "\n")

    if not changes:
        print("up to date: nothing to change")
        return 0
    if args.apply:
        apply(changes)
        print(f"applied {len(changes)} file(s) (originals saved as .bak):")
        for path, _, _ in changes:
            print(f"  {path}")
    else:
        show(changes)
        print(f"\ndry run: {len(changes)} file(s) would change. Re-run with --apply to write them (.bak backups are kept).")
    return 0
