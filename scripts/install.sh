#!/usr/bin/env sh
# driftguard installer (macOS / Linux / WSL): installs the CLI and the agent integrations it finds.
set -eu
REPO="https://raw.githubusercontent.com/stelies/driftguard/main"
say() { printf '\033[1m%s\033[0m\n' "$*"; }
if command -v pipx >/dev/null 2>&1; then pipx install --force driftguard-cli
elif command -v uv >/dev/null 2>&1; then uv tool install --force driftguard-cli
else python3 -m pip install --user --upgrade driftguard-cli; fi
fetch() { mkdir -p "$(dirname "$2")"; curl -fsSL "$REPO/$1" -o "$2"; }
if [ -d "$HOME/.claude" ]; then fetch integrations/claude/skills/driftguard/SKILL.md "$HOME/.claude/skills/driftguard/SKILL.md"; fetch integrations/claude/skills/driftguard/findings-schema.md "$HOME/.claude/skills/driftguard/findings-schema.md"; say "Claude Code: skill installed → run /driftguard"; fi
if [ -d "$HOME/.codex" ]; then fetch integrations/codex/skills/driftguard/SKILL.md "$HOME/.codex/skills/driftguard/SKILL.md"; fetch integrations/codex/skills/driftguard/findings-schema.md "$HOME/.codex/skills/driftguard/findings-schema.md"; say "Codex: skill installed → ask: run driftguard"; fi
if [ -d "$HOME/.gemini" ]; then fetch integrations/gemini/commands/driftguard.toml "$HOME/.gemini/commands/driftguard.toml"; say "Gemini CLI: /driftguard command installed"; fi
say "Done. Try: driftguard scan"
