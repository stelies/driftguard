#!/usr/bin/env python3
"""Generate a fully SYNTHETIC dataset (fake projects, fake prompts) and render a ready demo report.

    python scripts/make_demo_data.py --out _site/demo/index.html [--dev-json]

Uses the real driftguard.metrics code on fake sessions, so the demo shows exactly what a real scan would. Nothing here
reads this machine's agent histories.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from driftguard import __version__, metrics, report  # noqa: E402
from driftguard.cli import mode_of  # noqa: E402

R = random.Random(7)
NOW = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)

PROJECTS = {  # name -> (weight, agents, topics)
    "acme-shop": (5, ["claude", "claude", "codex"], [
        "add a coupon code field to the checkout page and validate it server side, keep the existing cart totals test passing",
        "the order confirmation email is missing the shipping address, find where the template is built",
        "write a migration that adds a refunded_at column to orders and backfill it from the payments table",
        "extract the pricing rules into a pure function with unit tests, no behavior change",
        "paginate the product list api, 24 per page, return a next cursor",
    ]),
    "pixel-quest": (4, ["claude", "cursor"], [
        "the player jumps twice when I hold space, fix the input buffering in the movement controller",
        "add a save slot menu with three slots and a delete confirmation",
        "enemy pathfinding gets stuck on corners, use the navmesh agent radius properly",
        "make the inventory grid scrollable and keep the selected item highlighted",
    ]),
    "side-browser": (3, ["claude", "gemini"], [
        "start a tiny browser shell with tabs and a url bar in electron",
        "add an ad blocker list parser, I want to replace my daily browser with this",
        "implement a bookmarks sidebar synced to a local json file",
    ]),
    "docs-site": (2, ["codex", "claude"], [
        "update the pricing page copy with the new plan names and fix the broken anchor links",
        "add a dark mode toggle to the docs theme",
        "generate the api reference from the openapi file in CI",
    ]),
}
RAGE = ["why the hell is this still broken?? i asked for this twice already", "WTF this is garbage, you broke the build again!!",
        "seriously?? that is not what i asked, revert it"]
SWITCH = ["ok forget that, new idea: build a whole plugin marketplace with ratings and payments for the editor instead",
          "actually lets also redesign the landing page with a video hero and parallax and a pricing calculator widget",
          "unrelated but can you set up a discord bot that posts weekly analytics summaries from the database"]
FOLLOW = ["continue", "looks good, now the tests", "yes do it", "fix the failing test", "same for the other file", "run the linter and fix it"]
MODELS = ["claude-sonnet-4-6", "claude-opus-4-6", "gpt-5-codex", "gemini-2.5-pro", "cursor-auto"]


def iso(t: datetime) -> str:
    return t.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def make_sessions() -> list[dict]:
    names, weights = list(PROJECTS), [PROJECTS[n][0] for n in PROJECTS]
    out = []
    for i in range(78):
        # activity ramps up toward the end of the window, with a few quiet weeks
        day = int(R.triangular(0, 140, 118))
        start = NOW - timedelta(days=day, hours=R.choice([1, 2, 9, 10, 11, 14, 15, 16, 20, 21, 22, 23]), minutes=R.randint(0, 59))
        proj = R.choices(names, weights)[0]
        _, agents, topics = PROJECTS[proj]
        agent = R.choice(agents)
        n = R.choice([1, 2, 3, 4, 5, 6, 8, 11, 14, 20])
        t, prompts = start, []
        for k in range(n):
            if k == 0:
                txt = R.choice(topics)
            else:
                r = R.random()
                gap = R.choice([1, 2, 3, 5, 8]) if R.random() > 0.15 else R.choice([45, 70, 120, 300])
                t = t + timedelta(minutes=gap, seconds=R.randint(0, 50))
                txt = R.choice(RAGE) if r < 0.07 else R.choice(SWITCH) if r < 0.2 + (0.15 if k == 1 else 0) else R.choice(topics) if r < 0.45 else R.choice(FOLLOW)
            prompts.append({"t": iso(t), "txt": txt})
        turns = n * R.randint(6, 25)
        base = R.choice([40_000, 120_000, 300_000, 800_000])
        usage = [[iso(start + timedelta(minutes=j * max(1, (t - start).seconds // 60 // max(1, turns // 6 + 1)))), int(base * R.uniform(0.3, 1.7))] for j in range(turns)]
        model = {"claude": R.choice(MODELS[:2]), "codex": MODELS[2], "gemini": MODELS[3], "cursor": MODELS[4]}[agent]
        cache = int(sum(u[1] for u in usage) * 0.82)
        out.append({"agent": agent, "id": f"demo-{i:03d}", "tools": turns // 2, "models": {model: turns},
                    "tokens": {"input": int(cache * 0.01), "output": int(cache * 0.07), "cache_read": cache, "cache_write": int(cache * 0.1)},
                    "title": None, "start": prompts[0]["t"], "end": prompts[-1]["t"], "project": proj, "bot": False, "prompts": prompts, "usage": usage})
    for i in range(9):  # auto-generated transcripts the UI excludes
        t = NOW - timedelta(days=R.randint(0, 120))
        out.append({"agent": "claude", "id": f"demo-bot-{i}", "tools": 0, "models": {MODELS[0]: 2}, "tokens": {"input": 10, "output": 50, "cache_read": 0, "cache_write": 0},
                    "title": "Summarize this conversation", "start": iso(t), "end": iso(t), "project": "acme-shop", "bot": True, "prompts": [], "usage": []})
    out.sort(key=lambda s: s["start"])
    return out


TITLES = {"acme-shop": ["Coupon codes at checkout", "Order email fixes", "Refund migration", "Pricing rules refactor", "Paginated product API"],
          "pixel-quest": ["Double jump bug", "Save slots menu", "Pathfinding corners", "Scrollable inventory"],
          "side-browser": ["Browser shell", "Ad blocker parser", "Bookmarks sidebar"], "docs-site": ["Pricing copy", "Dark mode", "API reference CI"]}


def make_findings(sessions: list[dict]) -> dict:
    human = [s for s in sessions if not s["bot"]]
    fs = []
    for s in human:
        bad = any(p["txt"] in RAGE for p in s["prompts"])
        month = int(s["start"][5:7])
        q = max(1, min(5, round(R.gauss(3.6 - (0.5 if month >= 9 else 0) - (0.8 if bad else 0), 0.7))))
        m = max(1, min(5, round(R.gauss(3.8 - (1.1 if bad else 0) - (0.4 if s["project"] == "side-browser" else 0), 0.8))))
        fs.append({"session": s["id"], "project": s["project"], "date": s["start"][:10], "title": R.choice(TITLES[s["project"]]),
                   "motivation": m, "motivation_evidence": "still broken?? i asked for this twice" if bad else "ok nice, now the tests",
                   "prompt_quality": q, "prompt_issues": ["rage", "vague"] if bad else R.choice([["good-spec"], ["multi-ask"], ["no-context"], ["iterative-good"], ["scope-creep"]]),
                   "one_line": "Frustrated loop on a regression." if bad else "Focused change with a clear done condition."})
    projects = [
        {"name": "acme-shop", "what_it_is": "Online store backend and checkout.", "category": "useful-and-good", "category_reason": "Steady weekly progress, clear deliverables.",
         "redundant_with": "", "status_last_seen": "Pagination shipped; refund migration pending.", "drift": [
             {"date": "2026-08-12", "from": "checkout coupons", "to": "a full promotions engine", "quote": "actually lets also add stacking rules and scheduled campaigns"}]},
        {"name": "pixel-quest", "what_it_is": "Small 2D game prototype.", "category": "stalled", "category_reason": "Many bug-fix sessions, no playable build shipped.",
         "redundant_with": "", "status_last_seen": "Inventory UI half done.", "drift": [
             {"date": "2026-07-30", "from": "fix jump bug", "to": "new level editor", "quote": "ok forget that, new idea: build a level editor so anyone can make maps"}]},
        {"name": "side-browser", "what_it_is": "Custom browser shell in Electron.", "category": "dopamine-build", "category_reason": "Replaces a tool the owner already uses daily; no named user or deadline.",
         "redundant_with": "Brave", "status_last_seen": "Bookmarks sidebar started.", "drift": [
             {"date": "2026-09-14", "from": "tiny browser shell", "to": "ad blocker and sync engine", "quote": "I want to replace my daily browser with this"}]},
        {"name": "docs-site", "what_it_is": "Public documentation site.", "category": "done-no-updates-needed", "category_reason": "Shipped; only copy updates.", "redundant_with": "", "status_last_seen": "Copy updated."}]
    chats = [{"session": human[-1]["id"], "project": "acme-shop", "date": human[-1]["start"][:10], "user": "add a coupon code field to the checkout page and validate it server side, keep the existing cart totals test passing",
              "assistant_gist": "Added the field, a validate_coupon service and two tests; cart totals test untouched.", "why_notable": "Best-style prompt: one goal, a constraint and a done condition.", "better_prompt": ""},
             {"session": human[len(human) // 2]["id"], "project": "pixel-quest", "date": human[len(human) // 2]["start"][:10], "user": "why the hell is this still broken?? i asked for this twice already",
              "assistant_gist": "Apologised and re-applied the same fix without finding the cause.", "why_notable": "Frustration spike: no repro or expected behaviour given.",
              "better_prompt": "The jump still triggers twice when I hold space. Repro: hold space on flat ground. Expected: one jump. Find the cause before changing code."}]
    return {"projects": projects, "sessions": fs, "example_chats": chats,
            "patterns": ["Sessions drift right after the first answer: 1 in 3 break focus by prompt #3.", "Frustration prompts cluster on regressions with no repro steps.",
                         "Late-night sessions (22:00+) have the highest topic-switch rate."],
            "coach": [{"date": "2026-08-30", "project": "pixel-quest", "bad": "why the hell is this still broken?? i asked for this twice already",
                       "why": "No repro, no expected result: the agent can only guess.", "better": "Repro: hold space on flat ground. Expected: one jump. Find the cause first, then fix."}],
            "improve": [{"id": "one-goal", "title": "Start every session with one goal and a done condition", "short": "State the outcome and how you will know it works.",
                         "long": "Sessions that began with a concrete deliverable scored higher on both motivation and quality than open-ended ones.", "evidence": ["Focus map"]},
                        {"id": "cap-side-projects", "title": "Pause side-browser until a named user exists", "short": "It duplicates a tool you already use.",
                         "long": "The project drifted twice and its sessions have the lowest motivation scores.", "evidence": ["Projects"]},
                        {"id": "handoff", "title": "Hand off long sessions instead of continuing", "short": "Costliest sessions are 10x the median.", "long": "Run `driftguard handoff` and start fresh.", "evidence": ["Tokens"]}],
            "answers": {"goals": ["learning", "shipping"], "tone": "neutral"}}


def make_scan(sessions: list[dict]) -> dict:
    setup = {"claude_md": True, "skills": 3, "skill_names": ["review", "deploy", "docs"], "hooks": False, "permissions_allow": 4, "mcp_servers": 0,
             "graphify": False, "agents_installed": {"claude": True, "codex": True, "gemini": True, "cursor": True}, "codex_agents_md": False, "gemini_md": False}
    summary = metrics.summarize(sessions, setup)
    summary["tz_offset_hours"] = 2.0
    light = [{k: v for k, v in s.items() if k not in ("prompts", "usage")} | {"n": len(s["prompts"])} for s in sessions]
    return {"version": __version__, "generated": "2026-09-30T18:00:00+00:00", "setup": setup, "mode": mode_of(summary), "summary": summary,
            "sessions": light, "blocks": metrics.five_hour_blocks(sessions)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="site-demo.html", help="rendered demo report (single HTML file)")
    ap.add_argument("--dev-json", action="store_true", help="also write web/static/demo-data.json for `npm run dev`")
    ap.add_argument("--no-findings", action="store_true", help="render the empty-findings state")
    a = ap.parse_args()
    sessions = make_sessions()
    scan = make_scan(sessions)
    findings = None if a.no_findings else make_findings(sessions)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.render(scan, findings), encoding="utf-8")
    if a.dev_json:
        (ROOT / "web" / "static" / "demo-data.json").write_text(json.dumps(report.build_data(scan, findings)), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB): {len(sessions)} synthetic transcripts, mode {scan['mode']['diagnostics']}/frugal={scan['mode']['frugal']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
