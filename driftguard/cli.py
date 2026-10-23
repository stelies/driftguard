"""driftguard command line. Every command is deterministic and uses zero LLM tokens.

  scan      read all agent histories (incremental) -> ~/.driftguard/scan.json, prints mode
  digest    prompt-only chunks for the agent's scoring pass -> ~/.driftguard/digests/
  ingest    merge agent findings + your poll answers -> ~/.driftguard/findings.json
  report    build the interactive report (single HTML); --serve hosts it on localhost
  guard     write drift-guard blocks into agent rule files (dry-run diff unless --apply)
  handoff   write a <=40-line HANDOFF.md for the latest session (token-crisis mode)
  pulse     cheap check of new sessions; prints one line only if something needs attention
  budget    token burn by 5-hour block + mode advice
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, adapters, cache, digest, metrics, paths, setup_health


def collect(agents=None, quiet=False):
    adapters.load_all()
    c = cache.load()
    sessions, parsed = [], 0
    for name, (discover, parse) in adapters.REGISTRY.items():
        if agents and name not in agents:
            continue
        ss, n = cache.parse_all(discover(), parse, c)
        sessions += ss
        parsed += n
    cache.save(c)
    sessions.sort(key=lambda s: s.get("start", ""))
    if not quiet:
        print(f"read {parsed} changed file(s), {len(sessions)} session(s) total", file=sys.stderr)
    return sessions


def mode_of(summary: dict) -> dict:
    new = summary["experience"]["level"] == "new"
    frugal = summary["tokens"]["level"] == "high"
    return {
        "diagnostics": "scaled" if new else "compact",
        "frugal": frugal,
        "subagents": {"model": "haiku or sonnet" if frugal else "sonnet", "effort": "low", "max_parallel": 2 if frugal else 3},
        "digest_max_tokens": 25_000 if frugal else 50_000,
        "interview_rounds": 1 if new else 2,
        "why": summary["experience"]["reasons"] + (["token pressure high"] if frugal else []),
    }


def cmd_scan(a):
    sessions = collect(a.agents)
    setup = setup_health.check()
    summary = metrics.summarize(sessions, setup)
    light = [{k: v for k, v in s.items() if k not in ("prompts", "usage")} | {"n": len(s["prompts"])} for s in sessions]
    out = {"version": __version__, "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "setup": setup,
           "mode": mode_of(summary), "summary": summary, "sessions": light,
           "blocks": metrics.five_hour_blocks(sessions)}
    f = paths.data_dir() / "scan.json"
    f.write_text(json.dumps(out), encoding="utf-8")
    c, m = summary["counts"], out["mode"]
    if a.json:
        print(json.dumps({k: out[k] for k in ("version", "generated", "setup", "mode")} | {"counts": c, "experience": summary["experience"],
                          "tokens": summary["tokens"], "projects": summary["projects"], "scan_file": str(f)}, indent=1))
    else:
        print(f"{c['transcripts']} transcripts · {c['real']} real · {c['bot']} auto · {c['prompts']} prompts · agents {c['by_agent']}")
        print(f"mode: diagnostics={m['diagnostics']} frugal={m['frugal']}  ({'; '.join(m['why']) or 'experienced user, normal budget'})")
        print(f"wrote {f}")


def cmd_digest(a):
    sessions = collect(a.agents)
    mt = a.max_tokens
    if not mt:
        try:
            mt = json.loads((paths.data_dir() / "scan.json").read_text(encoding="utf-8"))["mode"]["digest_max_tokens"]
        except (OSError, ValueError, KeyError):
            mt = 50_000
    man = digest.build(sessions, paths.data_dir() / "digests", max_tokens=mt)
    (paths.data_dir() / "digests" / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    for m in man:
        print(f"{m['file']}  ~{m['approx_tokens']} tok  {len(m['projects'])} project(s)")
    print(f"{len(man)} chunk(s), ~{sum(m['approx_tokens'] for m in man)} tokens total (raw transcripts are far larger)")


def cmd_budget(a):
    sessions = collect(a.agents, quiet=True)
    blocks = metrics.five_hour_blocks(sessions)
    tp = metrics.token_pressure(sessions, [p for s in sessions if not s.get("bot") for p in metrics.prompt_features(s["prompts"])])
    for b in blocks[-a.last:]:
        print(f"{b['start'][:16]}  {b['tokens']:>12,} tok  {b['turns']:>4} turns")
    print(f"pressure: {tp['level']} (limit mentions {tp['limit_mentions']}, top-10 sessions = {tp['top10_share']:.0%} of tokens, p90 block {tp['p90_block_tokens']:,})")
    if tp["level"] == "high":
        print("advice: Sonnet/Haiku subagents (<=2), digests not transcripts, `driftguard handoff` + fresh session when context is long.")


def _lazy(mod: str, fn: str):
    def run(a):
        import importlib
        return getattr(importlib.import_module(f"driftguard.{mod}"), fn)(a)
    return run


def main(argv=None):
    ap = argparse.ArgumentParser(prog="driftguard", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"driftguard {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ag = argparse.ArgumentParser(add_help=False)
    ag.add_argument("--agents", nargs="*", choices=["claude", "codex", "gemini", "cursor"], help="limit to these agents")

    p = sub.add_parser("scan", parents=[ag], help="read histories -> scan.json")
    p.add_argument("--json", action="store_true", help="machine-readable summary for agents")
    p.set_defaults(fn=cmd_scan)
    p = sub.add_parser("digest", parents=[ag], help="prompt-only chunks for the LLM pass")
    p.add_argument("--max-tokens", type=int, default=0)
    p.set_defaults(fn=cmd_digest)
    p = sub.add_parser("budget", parents=[ag], help="token burn by 5h block")
    p.add_argument("--last", type=int, default=12)
    p.set_defaults(fn=cmd_budget)
    p = sub.add_parser("ingest", help="merge findings JSON + poll answers")
    p.add_argument("findings", nargs="+", help="findings JSON file(s) from the agent pass")
    p.add_argument("--answers", help="poll answers JSON (overrides findings)")
    p.set_defaults(fn=_lazy("ingest", "run"))
    p = sub.add_parser("report", help="build the interactive report")
    p.add_argument("--out", help="output HTML (default ~/.driftguard/report.html)")
    p.add_argument("--serve", action="store_true", help="host on localhost and open the browser")
    p.add_argument("--port", type=int, default=0, help="default: first free port from 5191")
    p.add_argument("--lan", action="store_true", help="bind 0.0.0.0 instead of 127.0.0.1")
    p.add_argument("--no-open", action="store_true")
    p.set_defaults(fn=_lazy("report", "run"))
    p = sub.add_parser("guard", parents=[ag], help="write drift-guard blocks (dry-run unless --apply)")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--projects", nargs="*", help="project dirs (default: from findings registry)")
    p.add_argument("--global-only", action="store_true")
    p.set_defaults(fn=_lazy("guard", "run"))
    p = sub.add_parser("handoff", help="<=40-line HANDOFF.md, no LLM")
    p.add_argument("--session", default="latest", help="session id or 'latest' (in --dir)")
    p.add_argument("--dir", default=".", help="project dir (default: cwd)")
    p.add_argument("--out", help="default: <dir>/HANDOFF.md")
    p.set_defaults(fn=_lazy("handoff", "run"))
    p = sub.add_parser("pulse", parents=[ag], help="cheap incremental check, silent unless needed")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(fn=_lazy("pulse", "run"))
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
