# driftguard installer (Windows PowerShell): irm https://raw.githubusercontent.com/stelies/driftguard/main/scripts/install.ps1 | iex
$ErrorActionPreference = "Stop"
$repo = "https://raw.githubusercontent.com/stelies/driftguard/main"
# Native Windows: no WSL needed. Needs Python 3.9+ (python.org installer or `winget install Python.Python.3.13`).
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { $null }
if (Get-Command pipx -ErrorAction SilentlyContinue) { pipx install --force driftguard-cli }
elseif (Get-Command uv -ErrorAction SilentlyContinue) { uv tool install --force driftguard-cli }
elseif ($py) { & $py -m pip install --user --upgrade driftguard-cli }
else { throw "Python 3.9+ not found. Install it (winget install Python.Python.3.13), reopen PowerShell, and rerun." }
function Fetch($src, $dst) { New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null; Invoke-WebRequest "$repo/$src" -OutFile $dst }
$h = $env:USERPROFILE
if (Test-Path "$h\.claude") { Fetch "integrations/claude/skills/driftguard/SKILL.md" "$h\.claude\skills\driftguard\SKILL.md"; Fetch "integrations/claude/skills/driftguard/findings-schema.md" "$h\.claude\skills\driftguard\findings-schema.md"; Write-Host "Claude Code: run /driftguard" }
if (Test-Path "$h\.codex")  { Fetch "integrations/codex/skills/driftguard/SKILL.md" "$h\.codex\skills\driftguard\SKILL.md"; Fetch "integrations/codex/skills/driftguard/findings-schema.md" "$h\.codex\skills\driftguard\findings-schema.md"; Write-Host "Codex: ask 'run driftguard'" }
if (Test-Path "$h\.gemini") { Fetch "integrations/antigravity/workflows/driftguard.md" "$h\.gemini\antigravity\global_workflows\driftguard.md"; Fetch "integrations/antigravity/commands/driftguard.toml" "$h\.gemini\commands\driftguard.toml"; Write-Host "Antigravity: /driftguard workflow installed" }
if (Get-Command driftguard -ErrorAction SilentlyContinue) { Write-Host "Done. Try: driftguard scan" }
elseif ($py) { Write-Host "Installed, but the Scripts folder is not on PATH yet. Reopen PowerShell, or run: $py -m driftguard scan" }
