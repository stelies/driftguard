"""Shared prompt-cleaning and bot-detection rules (ported from the original ClaudeAudit pipeline)."""
from __future__ import annotations

import re

# First-prompt prefixes of machine-generated sessions: summarizers, title jobs, chat relays, harnesses.
BOT_PREFIXES = (
    "Below is a conversation log", "Channel #", "Use the hub_post", "<teammate-message", "Generate a title",
    "say hi in 3 words", "Call docs_list", "You are continuing an in-progress",
    "Use the AskUserQuestion tool to ask me which", "Summarize this conversation", "Please write a 5-10 word title",
)
# Prompts that are bookkeeping, not human intent.
SKIP_PREFIXES = (
    "<local-command", "Caveat:", "/model", "/effort", "/clear", "/exit", "/compact", "[Request interrupted",
    "Another Claude session sent", "This session is being continued",
)
_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
_CMD = re.compile(r"<command-name>/?([^<]+)</command-name>")
_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)


def clean_prompt(t: str) -> str:
    """Strip injected reminders; turn slash-command XML back into '/name args'."""
    t = _REMINDER.sub("", t)
    m = _CMD.search(t)
    if m:
        a = _ARGS.search(t)
        t = "/" + m.group(1).lstrip("/") + (" " + a.group(1) if a and a.group(1).strip() else "")
    return t.strip()


def is_skip(t: str) -> bool:
    return not t or t.startswith(SKIP_PREFIXES)


def looks_bot(first_prompt: str | None, source: str = "") -> bool:
    # Claude names project dirs after the sanitized cwd: sessions started in temp dirs are scripted jobs.
    parent = source.replace("\\", "/").rstrip("/").split("/")[-2:-1]
    if parent and parent[0].startswith(("-tmp-", "-private-var-folders-", "-var-folders-")):
        return True
    return first_prompt is None or first_prompt.startswith(BOT_PREFIXES)


def project_name(cwd: str | None, fallback: str) -> str:
    if not cwd:
        return fallback
    return re.split(r"[\\/]", cwd.rstrip("\\/"))[-1] or fallback
