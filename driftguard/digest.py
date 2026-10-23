"""Prompt-only digests for the LLM pass: the main token saver.

Agents read these instead of raw transcripts (often 1000x smaller). Chunks are capped by an
approximate token budget (chars/4) so each subagent gets one bounded file.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import List


def approx_tokens(s: str) -> int:
    return len(s) // 4 + 1


def build(sessions: List[dict], out_dir: Path, max_tokens: int = 50_000, max_prompt_chars: int = 1200) -> List[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("chunk-*.txt"):
        old.unlink()
    by_proj = defaultdict(list)
    for s in sessions:
        if not s.get("bot") and s["prompts"]:
            by_proj[s["project"]].append(s)
    blocks = []
    for proj, ss in sorted(by_proj.items(), key=lambda kv: -sum(len(x["prompts"]) for x in kv[1])):
        lines = [f"##### PROJECT {proj} ({len(ss)} sessions)"]
        for s in sorted(ss, key=lambda x: x["start"]):
            lines.append(f"=== SESSION {s['id']} | {s['agent']} | {s['start'][:16]} -> {s['end'][:16]} | title: {s.get('title')} | prompts={len(s['prompts'])} tools={s.get('tools', 0)}")
            for p in s["prompts"]:
                x = p["txt"] if len(p["txt"]) <= max_prompt_chars else p["txt"][: max_prompt_chars - 200] + f" …[+{len(p['txt']) - max_prompt_chars + 200} chars]"
                lines.append(f"[{p['t'][:16]}] USER: {x}")
        blocks.append((proj, "\n".join(lines)))
    chunks, cur, cur_tok, cur_proj = [], [], 0, []
    for proj, text in blocks:
        t = approx_tokens(text)
        if cur and cur_tok + t > max_tokens:
            chunks.append((cur_proj, "\n\n".join(cur)))
            cur, cur_tok, cur_proj = [], 0, []
        if t > max_tokens:  # one huge project: hard-split by lines
            buf, bt = [], 0
            for ln in text.split("\n"):
                lt = approx_tokens(ln)
                if buf and bt + lt > max_tokens:
                    chunks.append(([proj], "\n".join(buf)))
                    buf, bt = [f"##### PROJECT {proj} (continued)"], 10
                buf.append(ln)
                bt += lt
            cur, cur_tok, cur_proj = ["\n".join(buf)], bt, [proj]
            continue
        cur.append(text)
        cur_tok += t
        cur_proj.append(proj)
    if cur:
        chunks.append((cur_proj, "\n\n".join(cur)))
    manifest = []
    for i, (projs, text) in enumerate(chunks, 1):
        f = out_dir / f"chunk-{i:02d}.txt"
        f.write_text(text, encoding="utf-8")
        manifest.append({"file": str(f), "projects": projs, "approx_tokens": approx_tokens(text)})
    return manifest
