# Bring up zunda-llm-gw (+ Zunda-Yaboo only if it is not already running).
# Never stops an existing Zunda-Yaboo workspace container.
$ErrorActionPreference = "Stop"
$starterDir = $PSScriptRoot
$repoRoot = Split-Path -Parent $starterDir
Set-Location $repoRoot

$composeFile = Join-Path $starterDir "docker-compose.yml"
$envFile = Join-Path $starterDir ".env"
if (-not (Test-Path $envFile)) {
  Copy-Item (Join-Path $starterDir ".env.example") $envFile
  Write-Host "Created Starter/.env from .env.example"
}

$composeBase = @("compose", "-f", $composeFile, "--env-file", $envFile)
$zyRunning = (docker inspect -f "{{.State.Running}}" Zunda-Yaboo 2>$null) -eq "true"

if ($zyRunning) {
  Write-Host "Zunda-Yaboo already running — leaving it alone; refreshing gateway only."
  # Recreate gateway by name collision: remove gw only, then up llm-gateway.
  docker rm -f zunda-llm-gw 2>$null | Out-Null
  docker @composeBase up --build -d llm-gateway
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
  Write-Host "Starting llm-gateway + Zunda-Yaboo (fresh)."
  docker @composeBase up --build -d
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "Up. Next:"
Write-Host "  powershell -File .\Starter\start-viewer.ps1"
Write-Host "  powershell -File .\Starter\verify.ps1"
Write-Host "  http://127.0.0.1:8765/  and  http://127.0.0.1:8765/compare.html"
