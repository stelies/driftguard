# driftguard installer (Windows PowerShell): irm https://raw.githubusercontent.com/stelies/driftguard/main/scripts/install.ps1 | iex
$ErrorActionPreference = "Stop"
$repo = "https://raw.githubusercontent.com/stelies/driftguard/main"
if (Get-Command pipx -ErrorAction SilentlyContinue) { pipx install --force driftguard-cli }
elseif (Get-Command uv -ErrorAction SilentlyContinue) { uv tool install --force driftguard-cli }
else { py -m pip install --user --upgrade driftguard-cli }
function Fetch($src, $dst) { New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null; Invoke-WebRequest "$repo/$src" -OutFile $dst }
$h = $env:USERPROFILE
if (Test-Path "$h\.claude") { Fetch "integrations/claude/skills/driftguard/SKILL.md" "$h\.claude\skills\driftguard\SKILL.md"; Fetch "integrations/claude/skills/driftguard/findings-schema.md" "$h\.claude\skills\driftguard\findings-schema.md"; Write-Host "Claude Code: run /driftguard" }
if (Test-Path "$h\.codex")  { Fetch "integrations/codex/skills/driftguard/SKILL.md" "$h\.codex\skills\driftguard\SKILL.md"; Fetch "integrations/codex/skills/driftguard/findings-schema.md" "$h\.codex\skills\driftguard\findings-schema.md"; Write-Host "Codex: ask 'run driftguard'" }
if (Test-Path "$h\.gemini") { Fetch "integrations/gemini/commands/driftguard.toml" "$h\.gemini\commands\driftguard.toml"; Write-Host "Gemini CLI: /driftguard" }
Write-Host "Done. Try: driftguard scan"
