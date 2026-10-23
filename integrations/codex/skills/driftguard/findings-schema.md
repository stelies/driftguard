# findings.json contract (agent pass → `driftguard ingest`)

Written by the agent's subagents after reading `~/.driftguard/digests/chunk-*.txt`. One file per chunk is fine; `ingest` merges them.

```jsonc
{
  "projects": [{
    "name": "my-app",                 // must match a project name from scan.json (cwd basename)
    "what_it_is": "one sentence",
    "category": "useful-and-good | useful-but-redundant | done-no-updates-needed | stalled | dopamine-build | moved-elsewhere | abandoned | unclear",
    "category_reason": "one sentence",
    "redundant_with": "existing tool name or ''",
    "status_last_seen": "one sentence",
    "drift": [{"date": "YYYY-MM-DD", "from": "original goal", "to": "what it became", "quote": "user's words <=200 chars"}]
  }],
  "sessions": [{
    "session": "<session id>", "project": "my-app", "date": "YYYY-MM-DD", "title": "…",
    "motivation": 1, "motivation_evidence": "short quote",          // 1-5
    "prompt_quality": 1,                                             // 1-5
    "prompt_issues": ["vague","no-goal","scope-creep","typo-heavy","contradicts-earlier","rage","multi-ask","no-context","good-spec","clear-constraints","iterative-good"],
    "one_line": "…"
  }],
  "example_chats": [{"session": "…", "project": "…", "date": "YYYY-MM-DD", "user": "verbatim <=400 chars", "assistant_gist": "<=200 chars", "why_notable": "…", "better_prompt": "optional rewrite"}],
  "patterns": ["observation backed by a date/session"],
  "coach": [{"date": "YYYY-MM-DD", "project": "…", "bad": "verbatim prompt", "why": "…", "better": "rewrite"}],
  "improve": [{"id": "slug", "title": "…", "short": "…", "long": "…", "evidence": ["…"]}]
}
```

## answers.json (poll answers, override findings)

```jsonc
{
  "goals": ["money", "learning"],
  "tone": "brutal | kind | neutral",
  "daily_use": ["project-a"],
  "overrides": {"<project name>": {"category": "…", "reason": "user's words"}},
  "registry": {"<project name>": {"status": "ACTIVE|STALLED|DONE|MOVED|PARKED|DEAD", "kind": "money|own|learning|tool|team", "purpose": "…", "path": "~/…"}},
  "wip_limit": "1 paid + 1 own",
  "drift_action": "stop-poll | nudge | refuse",
  "gate": "gate+active | gate | none",
  "frustration": ["restate", "screenshot", "rule", "break"],
  "notes": {"<question>": "<answer>"}
}
```
Overrides set `user_confirmed: true` on the project. Pronouns: agents must write "they/them" or "you".
